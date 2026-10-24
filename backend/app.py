"""The API server. Run locally with:  python app.py   (then open http://localhost:5000)

It also serves the web app (../web), so the website and the API share one
address and one deployment.
"""
import json
import os
import re
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory, abort, g

import config
import db
from services import geocode, weather, flood, risk, checklist, resources, news, ai_plan, gemini, photo_ai
from services.http import ServiceError

WEB_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "web"))
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # 2 MB per request


def _load(name):
    with open(os.path.join(DATA_DIR, name), encoding="utf-8") as f:
        return json.load(f)


ENSO, TIDES, REGIONS = _load("enso.json"), _load("tides.json"), _load("regions.json")


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------- plumbing

class BadRequest(Exception):
    pass


@app.errorhandler(BadRequest)
def _bad(e):
    return jsonify({"error": str(e)}), 400


@app.errorhandler(404)
def _nf(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "not found"}), 404
    return e


@app.errorhandler(413)
def _big(e):
    return jsonify({"error": "That photo is too large. Try a smaller one."}), 413


@app.before_request
def _before():
    g.device = None
    dev = request.headers.get("X-Device-Id", "")
    if re.fullmatch(r"[A-Za-z0-9-]{8,64}", dev):
        g.device = dev


@app.after_request
def _cors(resp):
    origin = request.headers.get("Origin")
    if origin and ("*" in config.ALLOWED_ORIGINS or origin in config.ALLOWED_ORIGINS):
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Device-Id"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
    resp.headers["X-Content-Type-Options"] = "nosniff"
    return resp


@app.route("/api/<path:_any>", methods=["OPTIONS"])
def _preflight(_any):
    return ("", 204)


@app.teardown_appcontext
def _teardown(_exc):
    pass  # connections are reused per thread (see db.py)


# Simple rate limit for the AI and outside-data routes: protects the free API quotas.
_hits = defaultdict(deque)


def rate_limit(bucket, per_hour):
    ip = (request.headers.get("X-Forwarded-For") or request.remote_addr or "?").split(",")[0].strip()
    q = _hits[(bucket, ip)]
    now = time.time()
    while q and now - q[0] > 3600:
        q.popleft()
    if len(q) >= per_hour:
        abort(429)
    q.append(now)


@app.errorhandler(429)
def _slow(e):
    return jsonify({"error": "Too many requests. Please wait a few minutes."}), 429


def need_device():
    if not g.device:
        raise BadRequest("missing device id")
    return g.device


def body():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise BadRequest("send JSON")
    return data


def coords(d):
    try:
        lat, lon = float(d["lat"]), float(d["lon"])
    except (KeyError, TypeError, ValueError):
        raise BadRequest("lat and lon are required")
    if not (-90 <= lat <= 90 and -180 <= lon <= 180):
        raise BadRequest("lat/lon out of range")
    return lat, lon


# ---------------------------------------------------------------- routes

@app.get("/api/health")
def health():
    return jsonify({"ok": True, "app": config.APP_NAME, "ai": gemini.available(), "time": now_iso()})


@app.get("/api/enso")
def enso():
    return jsonify(ENSO)


@app.get("/api/regions")
def regions():
    return jsonify(REGIONS)


HOUSEHOLD_KEYS = ("kids", "older_adult", "disability", "medical_device", "pets", "no_car", "renter", "lives_alone", "hillside")


def gather(lat, lon, place):
    """Collect live data for one spot. Each source can fail on its own;
    the plan is still built from whatever succeeded, and we say what's missing."""
    missing = []
    out = {"alerts": [], "forecast": [], "rain": None, "flood": None, "elevation": None}
    us = (place.get("country") in (None, "US"))
    if us:
        for name, fn in (("alerts", lambda: weather.alerts(lat, lon)),
                         ("forecast", lambda: weather.forecast(lat, lon)),
                         ("flood", lambda: flood.flood_zone(lat, lon)),
                         ("elevation", lambda: flood.elevation_ft(lat, lon))):
            try:
                out[name] = fn()
            except ServiceError:
                missing.append(name)
        out["rain"] = weather.rain_outlook(out["forecast"])
    else:
        missing += ["alerts", "forecast", "flood", "elevation"]
    return out, missing


@app.post("/api/plan")
def make_plan():
    device = need_device()
    rate_limit("plan", 40)
    d = body()
    language = d.get("language") if d.get("language") in ai_plan.LANGUAGES else "en"
    household = {k: bool((d.get("household") or {}).get(k)) for k in HOUSEHOLD_KEYS}
    label = str(d.get("label") or "Home")[:40]

    try:
        if d.get("address"):
            address = str(d["address"])[:200]
            place = geocode.geocode(address)
            lat, lon = place["lat"], place["lon"]
        else:
            lat, lon = coords(d)
            place = geocode.reverse(lat, lon)
    except ServiceError as e:
        raise BadRequest(str(e))

    live, missing = gather(lat, lon, place)
    r = risk.score(flood=live["flood"], elevation=live["elevation"], alerts=live["alerts"], rain=live["rain"],
                   county=place.get("county"), state=place.get("state"), tides=TIDES)
    help_ = resources.for_place(place, lat, lon)
    items = checklist.build(r, household, county=place.get("county"), alert_system=help_["alert_system"],
                            nearest_sandbags=(help_["sandbags"] or [None])[0])
    place_name = ", ".join(x for x in [place.get("city"), place.get("state")] if x) or "your area"
    summary, translated = None, False
    if gemini.available():
        try:
            summary, items = ai_plan.personalize(items, r, place_name, household, language)
            translated = language != "en"
        except ServiceError:
            missing.append("ai")
    if not summary:
        summary = ai_plan.fallback_summary(r, place_name)

    plan_id = uuid.uuid4().hex[:12]
    ts = now_iso()
    db.execute("""INSERT INTO plans (id, device_id, label, address, lat, lon, county, city, state, language,
                  household, risk, checklist, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
               (plan_id, device, label, place.get("address"), lat, lon, place.get("county"), place.get("city"),
                place.get("state"), language, json.dumps(household), json.dumps({**r, "summary": summary}),
                json.dumps(items), ts, ts))
    return jsonify(plan_payload(plan_id, live=live, help_=help_, missing=missing, translated=translated)), 201


def plan_payload(plan_id, live=None, help_=None, missing=None, translated=False):
    row = db.one("SELECT * FROM plans WHERE id = ?", (plan_id,))
    if not row:
        abort(404)
    done = {r["item_id"] for r in db.query("SELECT item_id FROM checklist_done WHERE plan_id = ?", (plan_id,))}
    items = json.loads(row["checklist"])
    for i in items:
        i["done"] = i["id"] in done
    place = {"county": row["county"], "city": row["city"], "state": row["state"]}
    if live is None:  # reopening a saved plan: refresh only the fast-changing parts
        live = {"alerts": [], "forecast": [], "rain": None}
        missing = []
        try:
            live["alerts"] = weather.alerts(row["lat"], row["lon"])
        except ServiceError:
            missing.append("alerts")
        try:
            live["forecast"] = weather.forecast(row["lat"], row["lon"])
            live["rain"] = weather.rain_outlook(live["forecast"])
        except ServiceError:
            missing.append("forecast")
    if help_ is None:
        help_ = resources.for_place(place, row["lat"], row["lon"])
    r = json.loads(row["risk"])
    return {
        "id": row["id"], "label": row["label"], "address": row["address"],
        "lat": row["lat"], "lon": row["lon"], "place": place, "language": row["language"],
        "household": json.loads(row["household"]), "risk": r, "summary": r.get("summary"),
        "checklist": items, "progress": {"done": len(done & {i["id"] for i in items}), "total": len(items)},
        "alerts": live["alerts"], "forecast": live["forecast"][:6], "rain": live["rain"],
        "help": help_, "enso": ENSO, "missing": missing or [], "translated": translated,
        "created_at": row["created_at"],
    }


@app.get("/api/plans")
def list_plans():
    device = need_device()
    rows = db.query("SELECT id, label, address, city, state, risk, created_at FROM plans WHERE device_id = ? ORDER BY created_at DESC", (device,))
    return jsonify([{**{k: r[k] for k in ("id", "label", "address", "city", "state", "created_at")},
                     "level": json.loads(r["risk"])["level"], "score": json.loads(r["risk"])["score"]} for r in rows])


def own_plan(plan_id):
    device = need_device()
    row = db.one("SELECT device_id FROM plans WHERE id = ?", (plan_id,))
    if not row or row["device_id"] != device:
        abort(404)


@app.get("/api/plan/<plan_id>")
def get_plan(plan_id):
    own_plan(plan_id)
    return jsonify(plan_payload(plan_id))


@app.delete("/api/plan/<plan_id>")
def delete_plan(plan_id):
    own_plan(plan_id)
    db.execute("DELETE FROM checklist_done WHERE plan_id = ?", (plan_id,))
    db.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
    return jsonify({"ok": True})


@app.post("/api/plan/<plan_id>/check")
def check_item(plan_id):
    own_plan(plan_id)
    d = body()
    item = str(d.get("item_id", ""))[:40]
    if d.get("done"):
        db.execute("DELETE FROM checklist_done WHERE plan_id = ? AND item_id = ?", (plan_id, item))
        db.execute("INSERT INTO checklist_done (plan_id, item_id, done_at) VALUES (?, ?, ?)", (plan_id, item, now_iso()))
    else:
        db.execute("DELETE FROM checklist_done WHERE plan_id = ? AND item_id = ?", (plan_id, item))
    n = db.one("SELECT COUNT(*) AS n FROM checklist_done WHERE plan_id = ?", (plan_id,))["n"]
    return jsonify({"ok": True, "done": n})


@app.get("/api/news")
def get_news():
    rate_limit("news", 60)
    county, state = request.args.get("county", "")[:60], request.args.get("state", "CA")[:30]
    lang = request.args.get("lang", "en")
    if lang not in ai_plan.LANGUAGES:
        lang = "en"
    base = {"enso": ENSO}
    if not gemini.available():
        return jsonify({**base, "headline": None, "items": [], "sources": [], "ai": False})
    try:
        return jsonify({**base, **news.region_news(county, state, lang)})
    except ServiceError as e:
        return jsonify({**base, "headline": None, "items": [], "sources": [], "ai": False, "error": str(e)})


# ---------------- community storm reports

REPORT_KINDS = photo_ai.KINDS


@app.get("/api/reports")
def list_reports():
    lat, lon = coords(request.args)
    try:
        radius = max(0.5, min(float(request.args.get("miles", 15)), 60))
    except ValueError:
        radius = 15
    dlat = radius / 69.0
    rows = db.query("""SELECT id, kind, title, note, severity, lat, lon, ai_checked, confirmations, status, created_at,
                       CASE WHEN photo IS NULL THEN 0 ELSE 1 END AS has_photo
                       FROM reports WHERE lat BETWEEN ? AND ? AND status = 'open' ORDER BY created_at DESC LIMIT 300""",
                    (lat - dlat, lat + dlat))
    out = [r for r in rows if resources.miles(lat, lon, r["lat"], r["lon"]) <= radius]
    return jsonify(out)


@app.get("/api/reports/<rid>/photo")
def report_photo(rid):
    row = db.one("SELECT photo FROM reports WHERE id = ?", (rid,))
    if not row or not row["photo"]:
        abort(404)
    return jsonify({"photo": row["photo"]})


def valid_photo(p):
    if not p:
        return None
    if not isinstance(p, str) or not p.startswith("data:image/jpeg;base64,") or len(p) > config.MAX_PHOTO_BYTES * 4 // 3 + 64:
        raise BadRequest("photo must be a compressed JPEG")
    return p


@app.post("/api/reports/analyze")
def analyze_report():
    need_device()
    rate_limit("photo", 30)
    d = body()
    photo = valid_photo(d.get("photo"))
    if not photo:
        raise BadRequest("photo required")
    if not gemini.available():
        return jsonify({"ai": False})
    try:
        return jsonify({"ai": True, **photo_ai.classify(photo, str(d.get("note", ""))[:300])})
    except ServiceError as e:
        return jsonify({"ai": False, "error": str(e)})


@app.post("/api/reports")
def create_report():
    device = need_device()
    rate_limit("report", 30)
    d = body()
    lat, lon = coords(d)
    kind = d.get("kind") if d.get("kind") in REPORT_KINDS else "other"
    try:
        sev = max(1, min(3, int(d.get("severity", 2))))
    except (TypeError, ValueError):
        sev = 2
    title = (str(d.get("title") or "").strip() or REPORT_KINDS[kind])[:60]
    rid = uuid.uuid4().hex[:12]
    db.execute("""INSERT INTO reports (id, device_id, kind, title, note, severity, lat, lon, county, photo, ai_checked, created_at)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
               (rid, device, kind, title, str(d.get("note") or "")[:300], sev, lat, lon, str(d.get("county") or "")[:60] or None,
                valid_photo(d.get("photo")), 1 if d.get("ai_checked") else 0, now_iso()))
    return jsonify({"id": rid}), 201


@app.post("/api/reports/<rid>/confirm")
def confirm_report(rid):
    device = need_device()
    if not db.one("SELECT id FROM reports WHERE id = ?", (rid,)):
        abort(404)
    if not db.one("SELECT 1 AS x FROM report_confirms WHERE report_id = ? AND device_id = ?", (rid, device)):
        db.execute("INSERT INTO report_confirms (report_id, device_id) VALUES (?, ?)", (rid, device))
        db.execute("UPDATE reports SET confirmations = confirmations + 1 WHERE id = ?", (rid,))
    n = db.one("SELECT confirmations FROM reports WHERE id = ?", (rid,))["confirmations"]
    return jsonify({"confirmations": n})


@app.post("/api/reports/<rid>/clear")
def clear_report(rid):
    need_device()
    if not db.one("SELECT id FROM reports WHERE id = ?", (rid,)):
        abort(404)
    db.execute("UPDATE reports SET status = 'cleared' WHERE id = ?", (rid,))
    return jsonify({"ok": True})


# ---------------------------------------------------------------- web app

@app.get("/")
def index():
    return send_from_directory(WEB_DIR, "index.html")


@app.get("/<path:path>")
def static_files(path):
    if path.startswith("api/"):
        abort(404)
    full = os.path.join(WEB_DIR, path)
    if os.path.isfile(full):
        resp = send_from_directory(WEB_DIR, path)
        if path == "sw.js":
            resp.headers["Cache-Control"] = "no-cache"
        return resp
    return send_from_directory(WEB_DIR, "index.html")


with app.app_context():
    db.init()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=os.environ.get("DEBUG") == "1")
