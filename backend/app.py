"""The API server. Run locally with:  python app.py   (then open http://localhost:5000)

It also serves the web app (../web), so the website and the API share one
address and one deployment.
"""
import hashlib
import hmac
import json
import os
import re
import secrets
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timezone

from flask import Flask, jsonify, request, send_from_directory, abort, g
from werkzeug.security import generate_password_hash, check_password_hash

import config
import db
from services import geocode, weather, flood, risk, checklist, resources, news, ai_plan, gemini, photo_ai, scan as scan_svc, region as regions_svc
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
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, X-Device-Id, X-Org-Key, X-Admin-Token"
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
ROLES = ("household", "farmer")
FARM_GROWS = ("vegetables", "field", "orchard", "livestock", "nursery")


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
    role = d.get("role") if d.get("role") in ROLES else "household"
    farm = None
    if role == "farmer":
        f = d.get("farm") or {}
        farm = {"grows": [g for g in (f.get("grows") or []) if g in FARM_GROWS],
                "workers": bool(f.get("workers")), "creek": bool(f.get("creek"))}
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
    reg = regions_svc.for_place(place)
    r = risk.score(flood=live["flood"], elevation=live["elevation"], alerts=live["alerts"], rain=live["rain"],
                   county=place.get("county"), state=place.get("state"), tides=TIDES, region=reg, role=role)
    help_ = resources.for_place(place, lat, lon)
    items = checklist.build(r, household, county=place.get("county"), alert_system=help_["alert_system"],
                            nearest_sandbags=(help_["sandbags"] or [None])[0], role=role, farm=farm, region=reg)
    household = {**household, "role": role, "farm": farm}
    if place.get("country") and place.get("country") != "US":
        missing = [m for m in missing if m not in ("alerts", "forecast", "flood", "elevation")]
    place_name = ", ".join(x for x in [place.get("city"), place.get("state"), place.get("country") if place.get("country") not in (None, "US") else None] if x) or "your area"
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
                place.get("state"), language, json.dumps({**household, "country": place.get("country") or "US"}), json.dumps({**r, "summary": summary}),
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
    hh = json.loads(row["household"])
    place = {"county": row["county"], "city": geocode.clean_city(row["city"]), "state": row["state"], "country": hh.get("country", "US")}
    if live is None and place["country"] != "US":
        live, missing = {"alerts": [], "forecast": [], "rain": None}, []
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
        "household": hh, "role": hh.get("role", "household"), "farm": hh.get("farm"), "risk": r, "summary": r.get("summary"),
        "checklist": items, "progress": {"done": len(done & {i["id"] for i in items}), "total": len(items)},
        "alerts": live["alerts"], "forecast": live["forecast"][:6], "rain": live["rain"],
        "help": help_, "enso": ENSO, "missing": missing or [], "translated": translated,
        "created_at": row["created_at"],
    }


@app.get("/api/plans")
def list_plans():
    device = need_device()
    rows = db.query("SELECT id, label, address, city, state, risk, created_at FROM plans WHERE device_id = ? ORDER BY created_at DESC", (device,))
    for r in rows:
        r["city"] = geocode.clean_city(r["city"])
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
    """Reports for the map: official updates from county and city communities
    near you, plus posts from the family and neighborhood groups you're in."""
    lat, lon = coords(request.args)
    try:
        radius = max(0.5, min(float(request.args.get("miles", 15)), 60))
    except ValueError:
        radius = 15
    dlat = radius / 69.0
    a = current_account()
    mine = set()
    if a:
        mine = {r["community_id"] for r in db.query("SELECT community_id FROM community_members WHERE account_id = ?", (a["id"],))}
    rows = db.query("""SELECT r.id, r.kind, r.title, r.note, r.severity, r.lat, r.lon, r.ai_checked, r.confirmations, r.status,
                       r.created_at, r.community_id, c.kind AS community_kind, c.name AS community_name,
                       CASE WHEN r.photo IS NULL THEN 0 ELSE 1 END AS has_photo
                       FROM reports r JOIN communities c ON c.id = r.community_id
                       WHERE r.lat BETWEEN ? AND ? AND r.status = 'open' ORDER BY r.created_at DESC LIMIT 300""",
                    (lat - dlat, lat + dlat))
    out = []
    for r in rows:
        official = r["community_kind"] in OFFICIAL_KINDS
        if (official or r["community_id"] in mine) and resources.miles(lat, lon, r["lat"], r["lon"]) <= radius:
            out.append(_report_out(r))
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
    """Post a storm report to one of your communities. In county and city
    communities only verified officials can post. In family and neighborhood
    groups, every member can."""
    need_device()
    a = current_account()
    if not a:
        raise BadRequest("Create a free account and join a group to post reports")
    rate_limit("report", 30)
    d = body()
    c = db.one("SELECT * FROM communities WHERE id = ?", (str(d.get("community_id") or ""),))
    m = _membership(c["id"], a["id"]) if c else None
    if not m:
        raise BadRequest("Pick one of your groups to post to")
    if not _can_post(c, m):
        raise BadRequest("Only verified officials can post in county and city communities. Post in your neighborhood or family group instead.")
    lat, lon = coords(d)
    kind = d.get("kind") if d.get("kind") in REPORT_KINDS else "other"
    try:
        sev = max(1, min(3, int(d.get("severity", 2))))
    except (TypeError, ValueError):
        sev = 2
    title = (str(d.get("title") or "").strip() or REPORT_KINDS[kind])[:60]
    rid = uuid.uuid4().hex[:12]
    db.execute("""INSERT INTO reports (id, device_id, kind, title, note, severity, lat, lon, county, photo, ai_checked, created_at, community_id)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
               (rid, g.device, kind, title, str(d.get("note") or "")[:300], sev, lat, lon, c["county"],
                valid_photo(d.get("photo")), 1 if d.get("ai_checked") else 0, now_iso(), c["id"]))
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


# ---------------- AI Scan

@app.post("/api/plan/<plan_id>/scan")
def scan_photo(plan_id):
    own_plan(plan_id)
    rate_limit("scan", 20)
    photo = valid_photo(body().get("photo"))
    if not photo:
        raise BadRequest("Add a photo to scan")
    if not gemini.available():
        raise BadRequest("AI Scan needs the server's AI key")
    row = db.one("SELECT * FROM plans WHERE id = ?", (plan_id,))
    r, hh = json.loads(row["risk"]), json.loads(row["household"])
    place = ", ".join(x for x in [row["city"], row["state"], hh.get("country") if hh.get("country") != "US" else None] if x) or "their area"
    try:
        result = scan_svc.scan(photo, hazard=r.get("hazard", "flood"), role=hh.get("role", "household"),
                               place=place, language=row["language"])
    except ServiceError as e:
        raise BadRequest(f"AI couldn't check that photo ({e}). Try another one.")
    items = json.loads(row["checklist"])
    have = {i["id"] for i in items}
    added = [f for f in result["findings"] if f["id"] not in have]
    items = added + items
    db.execute("UPDATE plans SET checklist = ?, updated_at = ? WHERE id = ?", (json.dumps(items), now_iso(), plan_id))
    return jsonify({"seen": result["seen"], "added": added, "good": result["good"],
                    "next_photo": result["next_photo"], "plan": plan_payload(plan_id)})


# ---------------- organizations and help requests

SERVICES = {
    "sandbags": "Sandbags or sandbagging help",
    "rides": "Rides or help leaving",
    "checks": "Check-in calls and visits",
    "shelter": "A place to stay",
    "food": "Food and water",
    "translation": "Translation",
    "farm": "Help on farms (animals, equipment)",
    "cleanup": "Volunteers for cleanup",
    "supplies": "Supplies (batteries, tarps, masks)",
}


def _hash(key):
    return hashlib.sha256(key.encode()).hexdigest()


def org_public(o, lat=None, lon=None):
    out = {k: o[k] for k in ("id", "name", "about", "area", "email", "phone", "website", "radius_miles", "lat", "lon")}
    out["services"] = json.loads(o["services"])
    out["verified"] = bool(o["verified"])
    out["example"] = bool(o["example"])
    if lat is not None:
        out["miles"] = round(resources.miles(lat, lon, o["lat"], o["lon"]), 1)
    return out


def own_org(org_id):
    key = request.headers.get("X-Org-Key", "")
    o = db.one("SELECT * FROM orgs WHERE id = ?", (org_id,))
    if not o or not key or not hmac.compare_digest(o["key_hash"], _hash(key)):
        abort(404)
    return o


@app.get("/api/services")
def list_services():
    return jsonify(SERVICES)


@app.get("/api/orgs")
def list_orgs():
    lat, lon = coords(request.args)
    rows = db.query("SELECT * FROM orgs ORDER BY verified DESC, created_at")
    out = [org_public(o, lat, lon) for o in rows]
    out = [o for o in out if o["miles"] <= o["radius_miles"]]
    out.sort(key=lambda o: (not o["verified"], o["miles"]))
    return jsonify(out)


def create_org_row(d, lat, lon, example=False):
    name = str(d.get("name") or "").strip()[:80]
    if len(name) < 2:
        raise BadRequest("Organization name is required")
    services = [s for s in (d.get("services") or []) if s in SERVICES]
    if not services:
        raise BadRequest("Pick at least one kind of help you offer")
    email = str(d.get("email") or "").strip()[:120]
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise BadRequest("That email doesn't look right")
    website = str(d.get("website") or "").strip()[:200]
    if website and not website.startswith(("http://", "https://")):
        website = "https://" + website
    try:
        radius = max(1.0, min(float(d.get("radius_miles") or 25), 200.0))
    except (TypeError, ValueError):
        radius = 25.0
    key = secrets.token_urlsafe(18)
    oid = uuid.uuid4().hex[:12]
    db.execute("""INSERT INTO orgs (id, name, about, services, area, lat, lon, radius_miles, email, phone, website, verified, example, key_hash, created_at)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
               (oid, name, str(d.get("about") or "")[:400], json.dumps(services), str(d.get("area") or "")[:80] or None,
                lat, lon, radius, email or None, str(d.get("phone") or "")[:40] or None, website or None,
                0, 1 if example else 0, _hash(key), now_iso()))
    return oid, key


@app.post("/api/orgs")
def create_org():
    rate_limit("org", 10)
    d = body()
    try:
        if d.get("address"):
            g = geocode.geocode(str(d["address"])[:200])
            lat, lon = g["lat"], g["lon"]
            d.setdefault("area", ", ".join(x for x in [g.get("city"), f"{g['county']} County" if g.get("county") else None] if x))
        else:
            lat, lon = coords(d)
    except ServiceError as e:
        raise BadRequest(str(e))
    oid, key = create_org_row(d, lat, lon)
    o = db.one("SELECT * FROM orgs WHERE id = ?", (oid,))
    return jsonify({"org": org_public(o), "key": key}), 201


@app.post("/api/orgs/<org_id>/verify")
def verify_org(org_id):
    token = request.headers.get("X-Admin-Token", "")
    if not config.ADMIN_TOKEN or not hmac.compare_digest(token, config.ADMIN_TOKEN):
        abort(404)
    db.execute("UPDATE orgs SET verified = 1 WHERE id = ?", (org_id,))
    return jsonify({"ok": True})


def request_for_org(r, org_id):
    mine = r["org_id"] == org_id
    return {
        "id": r["id"], "need": r["need"], "need_label": SERVICES.get(r["need"], r["need"]), "details": r["details"],
        "status": r["status"], "area": r["area"], "created_at": r["created_at"],
        # Exact location and contact only for the organization that accepted it.
        "lat": r["lat"] if mine else round(r["lat"], 2), "lon": r["lon"] if mine else round(r["lon"], 2),
        "contact": r["contact"] if mine else None, "mine": mine,
    }


@app.get("/api/orgs/<org_id>/dashboard")
def org_dashboard(org_id):
    o = own_org(org_id)
    services = set(json.loads(o["services"]))
    rows = db.query("SELECT * FROM help_requests WHERE status IN ('open', 'accepted') ORDER BY created_at DESC LIMIT 300")
    reqs = [request_for_org(r, org_id) for r in rows
            if (r["status"] == "open" and r["need"] in services and resources.miles(o["lat"], o["lon"], r["lat"], r["lon"]) <= o["radius_miles"])
            or r["org_id"] == org_id]
    done = db.one("SELECT COUNT(*) AS n FROM help_requests WHERE org_id = ? AND status = 'done'", (org_id,))["n"]
    return jsonify({"org": org_public(o), "requests": reqs, "helped": done})


@app.post("/api/orgs/<org_id>/requests/<rid>/<action>")
def org_act(org_id, rid, action):
    own_org(org_id)
    r = db.one("SELECT * FROM help_requests WHERE id = ?", (rid,))
    if not r:
        abort(404)
    if action == "accept":
        if r["status"] != "open":
            raise BadRequest("Someone else already took this request")
        db.execute("UPDATE help_requests SET status = 'accepted', org_id = ?, updated_at = ? WHERE id = ? AND status = 'open'", (org_id, now_iso(), rid))
    elif action == "done":
        if r["org_id"] != org_id:
            abort(404)
        db.execute("UPDATE help_requests SET status = 'done', updated_at = ? WHERE id = ?", (now_iso(), rid))
    elif action == "release":
        if r["org_id"] != org_id:
            abort(404)
        db.execute("UPDATE help_requests SET status = 'open', org_id = NULL, updated_at = ? WHERE id = ?", (now_iso(), rid))
    else:
        abort(404)
    return jsonify(request_for_org(db.one("SELECT * FROM help_requests WHERE id = ?", (rid,)), org_id))


def my_requests(plan_id):
    rows = db.query("SELECT * FROM help_requests WHERE plan_id = ? AND status != 'cancelled' ORDER BY created_at DESC", (plan_id,))
    out = []
    for r in rows:
        org = db.one("SELECT * FROM orgs WHERE id = ?", (r["org_id"],)) if r["org_id"] else None
        out.append({"id": r["id"], "need": r["need"], "need_label": SERVICES.get(r["need"], r["need"]), "details": r["details"],
                    "status": r["status"], "created_at": r["created_at"], "updated_at": r["updated_at"],
                    "org": org_public(org) if org else None})
    return out


@app.get("/api/plan/<plan_id>/help")
def get_help_requests(plan_id):
    own_plan(plan_id)
    return jsonify(my_requests(plan_id))


@app.post("/api/plan/<plan_id>/help")
def ask_for_help(plan_id):
    own_plan(plan_id)
    rate_limit("help", 15)
    d = body()
    need = d.get("need")
    if need not in SERVICES:
        raise BadRequest("Pick what kind of help you need")
    contact = str(d.get("contact") or "").strip()[:120]
    if len(contact) < 5:
        raise BadRequest("Add a phone number or email so a helper can reach you")
    row = db.one("SELECT lat, lon, city, county FROM plans WHERE id = ?", (plan_id,))
    rid = uuid.uuid4().hex[:12]
    ts = now_iso()
    db.execute("""INSERT INTO help_requests (id, plan_id, device_id, need, details, contact, lat, lon, area, status, created_at, updated_at)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
               (rid, plan_id, g.device, need, str(d.get("details") or "")[:500], contact, row["lat"], row["lon"],
                ", ".join(x for x in [row["city"], f"{row['county']} County" if row["county"] else None] if x) or None, "open", ts, ts))
    return jsonify(my_requests(plan_id)), 201


@app.post("/api/plan/<plan_id>/help/<rid>/cancel")
def cancel_help(plan_id, rid):
    own_plan(plan_id)
    db.execute("UPDATE help_requests SET status = 'cancelled', updated_at = ? WHERE id = ? AND plan_id = ?", (now_iso(), rid, plan_id))
    return jsonify(my_requests(plan_id))


# ---------------------------------------------------------------- accounts
#
# The app has always given each phone a private random device id, and every
# plan belongs to that id. An account ties a name, email and password to one
# device id, so logging in on another phone or browser brings your plans with
# you. Passwords are stored only as salted scrypt hashes.

EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


def account_public(a):
    return {"id": a["id"], "name": a["name"], "email": a["email"]} if a else None


def current_account():
    return db.one("SELECT * FROM accounts WHERE device_id = ?", (g.device,)) if g.device else None


def need_account():
    need_device()
    a = current_account()
    if not a:
        raise BadRequest("Create an account or log in first")
    return a


def _move_device_data(old, new):
    """Bring plans, reports and help requests made before logging in into the account."""
    if old and new and old != new:
        for table in ("plans", "reports", "help_requests"):
            db.execute(f"UPDATE {table} SET device_id = ? WHERE device_id = ?", (new, old))


@app.get("/api/account")
def get_account():
    return jsonify({"account": account_public(current_account())})


@app.post("/api/account/signup")
def signup():
    device = need_device()
    rate_limit("signup", 10)
    d = body()
    name = str(d.get("name") or "").strip()[:40]
    email = str(d.get("email") or "").strip().lower()[:120]
    pw = str(d.get("password") or "")
    if len(name) < 1:
        raise BadRequest("Add your first name")
    if not EMAIL_RE.fullmatch(email):
        raise BadRequest("That email doesn't look right")
    if len(pw) < 8:
        raise BadRequest("Use a password with at least 8 characters")
    if db.one("SELECT id FROM accounts WHERE email = ?", (email,)):
        raise BadRequest("There's already an account with that email. Log in instead.")
    if current_account():
        raise BadRequest("You're already logged in")
    aid = uuid.uuid4().hex[:12]
    db.execute("INSERT INTO accounts (id, name, email, pw_hash, device_id, created_at) VALUES (?,?,?,?,?,?)",
               (aid, name, email, generate_password_hash(pw), device, now_iso()))
    a = db.one("SELECT * FROM accounts WHERE id = ?", (aid,))
    _auto_join(a)
    return jsonify({"account": account_public(a), "device_id": device}), 201


@app.post("/api/account/login")
def login():
    need_device()
    rate_limit("login", 20)
    d = body()
    email = str(d.get("email") or "").strip().lower()
    a = db.one("SELECT * FROM accounts WHERE email = ?", (email,))
    if not a or not check_password_hash(a["pw_hash"], str(d.get("password") or "")):
        raise BadRequest("Wrong email or password")
    if d.get("keep_plans", True) and not current_account():
        _move_device_data(g.device, a["device_id"])
    _auto_join(a)
    return jsonify({"account": account_public(a), "device_id": a["device_id"]})


# ---------------------------------------------------------------- communities
#
# County and city communities are official channels. Everyone with an account
# joins the ones for the places they have plans for automatically, and only
# verified officials (like the county's emergency office or the city) can post
# there. Family and neighborhood groups are private, joined with an invite
# code, and any member can post reports in them.

OFFICIAL_KINDS = ("county", "city")
GROUP_KINDS = ("family", "neighborhood")
CODE_CHARS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O or 1/I mix-ups


def _place_communities(device):
    """County and city communities for every place this person has a plan for."""
    out = {}
    for p in db.query("SELECT id, lat, lon, county, city, state, household FROM plans WHERE device_id = ? ORDER BY created_at", (device,)):
        region = p["state"] or json.loads(p["household"]).get("country") or ""
        if p["county"]:
            k = f"county:{region}:{p['county']}"
            out.setdefault(k, {"key": k, "kind": "county", "name": f"{p['county']} County" if region and len(region) == 2 else p["county"],
                               "county": p["county"], "lat": p["lat"], "lon": p["lon"]})
        city = geocode.clean_city(p["city"])
        if city:
            k = f"city:{region}:{city}"
            out.setdefault(k, {"key": k, "kind": "city", "name": city, "county": p["county"], "lat": p["lat"], "lon": p["lon"]})
    return out


def _place_community(s):
    c = db.one("SELECT * FROM communities WHERE place_key = ?", (s["key"],))
    if not c:
        cid = uuid.uuid4().hex[:12]
        db.execute("""INSERT INTO communities (id, kind, name, place_key, county, lat, lon, created_at)
                      VALUES (?,?,?,?,?,?,?,?)""", (cid, s["kind"], s["name"], s["key"], s["county"], s["lat"], s["lon"], now_iso()))
        c = db.one("SELECT * FROM communities WHERE id = ?", (cid,))
    return c


def _add_member(cid, account_id, role="member"):
    if not _membership(cid, account_id):
        db.execute("INSERT INTO community_members (community_id, account_id, role, joined_at) VALUES (?,?,?,?)",
                   (cid, account_id, role, now_iso()))


def _auto_join(a):
    """Join the county and city communities for every place on this account."""
    if a:
        for s in _place_communities(a["device_id"]).values():
            _add_member(_place_community(s)["id"], a["id"])


def _can_post(c, m):
    return bool(m) and (c["kind"] in GROUP_KINDS or m["role"] == "official")


def _report_out(r):
    r = dict(r)
    ck = r.pop("community_kind", None)
    for k in ("county", "status"):
        r.pop(k, None)
    out = {**r, "kind_label": REPORT_KINDS.get(r["kind"], "Storm problem")}
    if ck is not None:
        out["official"] = ck in OFFICIAL_KINDS
    return out


def _community_reports(c):
    rows = db.query("""SELECT r.id, r.kind, r.title, r.note, r.severity, r.lat, r.lon, r.ai_checked, r.confirmations, r.created_at,
                       r.community_id, c.name AS community_name, c.kind AS community_kind,
                       CASE WHEN r.photo IS NULL THEN 0 ELSE 1 END AS has_photo
                       FROM reports r JOIN communities c ON c.id = r.community_id
                       WHERE r.community_id = ? AND r.status = 'open' ORDER BY r.created_at DESC LIMIT 100""", (c["id"],))
    return [_report_out(r) for r in rows]


def _community_summary(c, account_id):
    n = db.one("SELECT COUNT(*) AS n FROM community_members WHERE community_id = ?", (c["id"],))["n"]
    m = _membership(c["id"], account_id)
    name = geocode.clean_city(c["name"]) if c["kind"] == "city" else c["name"]
    return {"id": c["id"], "kind": c["kind"], "name": name, "members": n,
            "owner": c["owner_id"] == account_id, "role": m["role"] if m else None, "can_post": _can_post(c, m)}


def _membership(cid, account_id):
    return db.one("SELECT * FROM community_members WHERE community_id = ? AND account_id = ?", (cid, account_id))


@app.get("/api/communities")
def list_communities():
    need_device()
    a = current_account()
    mine = []
    if a:
        _auto_join(a)
        rows = db.query("""SELECT c.* FROM communities c JOIN community_members m ON m.community_id = c.id
                           WHERE m.account_id = ? ORDER BY c.kind, c.name""", (a["id"],))
        order = {"county": 0, "city": 1, "neighborhood": 2, "family": 3}
        mine = sorted((_community_summary(c, a["id"]) for c in rows), key=lambda x: (order.get(x["kind"], 9), x["name"]))
    return jsonify({"account": account_public(a), "mine": mine, "suggested": []})


@app.post("/api/communities/join")
def join_community():
    """Join a family or neighborhood group with its invite code."""
    a = need_account()
    rate_limit("join", 30)
    code = re.sub(r"[^A-Z0-9]", "", str(body().get("code") or "").upper())
    c = db.one("SELECT * FROM communities WHERE invite_code = ?", (code,)) if code else None
    if not c:
        raise BadRequest("That invite code didn't match a group")
    _add_member(c["id"], a["id"])
    return jsonify(_community_summary(c, a["id"])), 201


@app.post("/api/communities")
def create_group():
    """Start a private family group or neighborhood group."""
    a = need_account()
    rate_limit("family", 10)
    d = body()
    kind = d.get("kind") if d.get("kind") in GROUP_KINDS else "family"
    default = f"{a['name']}'s family" if kind == "family" else f"{a['name']}'s neighborhood"
    name = str(d.get("name") or "").strip()[:40] or default
    owned = db.one("SELECT COUNT(*) AS n FROM communities WHERE kind = ? AND owner_id = ?", (kind, a["id"]))["n"]
    if owned >= 3:
        raise BadRequest("You can make up to 3 groups of each kind")
    home = db.one("SELECT lat, lon, county FROM plans WHERE device_id = ? ORDER BY created_at", (a["device_id"],))
    cid = uuid.uuid4().hex[:12]
    code = "".join(secrets.choice(CODE_CHARS) for _ in range(6))
    db.execute("""INSERT INTO communities (id, kind, name, county, lat, lon, owner_id, invite_code, created_at) VALUES (?,?,?,?,?,?,?,?,?)""",
               (cid, kind, name, home["county"] if home else None, round(home["lat"], 2) if home else None,
                round(home["lon"], 2) if home else None, a["id"], code, now_iso()))
    _add_member(cid, a["id"], "owner")
    return jsonify(_community_summary(db.one("SELECT * FROM communities WHERE id = ?", (cid,)), a["id"])), 201


@app.post("/api/communities/<cid>/officials")
def add_official(cid):
    """Mark someone as a verified official of a county or city community.
    Only the Swell team can do this (admin token), after checking who they are."""
    token = request.headers.get("X-Admin-Token", "")
    if not config.ADMIN_TOKEN or not hmac.compare_digest(token, config.ADMIN_TOKEN):
        abort(404)
    c = db.one("SELECT * FROM communities WHERE id = ?", (cid,))
    acct = db.one("SELECT * FROM accounts WHERE email = ?", (str(body().get("email") or "").strip().lower(),))
    if not c or c["kind"] not in OFFICIAL_KINDS or not acct:
        raise BadRequest("Unknown community or account")
    _add_member(cid, acct["id"])
    db.execute("UPDATE community_members SET role = 'official' WHERE community_id = ? AND account_id = ?", (cid, acct["id"]))
    return jsonify({"ok": True})


def own_community(cid):
    a = need_account()
    c = db.one("SELECT * FROM communities WHERE id = ?", (cid,))
    if not c or not _membership(cid, a["id"]):
        abort(404)
    return a, c


@app.get("/api/communities/<cid>")
def get_community(cid):
    a, c = own_community(cid)
    out = _community_summary(c, a["id"])
    if c["kind"] in GROUP_KINDS:
        out["invite_code"] = c["invite_code"]
    if c["kind"] == "family":
        people = []
        for m in db.query("""SELECT m.role, m.safe_at, m.joined_at, ac.id, ac.name, ac.device_id FROM community_members m
                             JOIN accounts ac ON ac.id = m.account_id WHERE m.community_id = ? ORDER BY m.joined_at""", (cid,)):
            places = []
            for p in db.query("SELECT id, label, city, state, lat, lon, risk FROM plans WHERE device_id = ? ORDER BY created_at", (m["device_id"],)):
                total = len(json.loads(db.one("SELECT checklist FROM plans WHERE id = ?", (p["id"],))["checklist"]))
                done = db.one("SELECT COUNT(*) AS n FROM checklist_done WHERE plan_id = ?", (p["id"],))["n"]
                r = json.loads(p["risk"])
                places.append({"label": p["label"], "city": geocode.clean_city(p["city"]), "level": r["level"], "score": r["score"],
                               "done": min(done, total), "total": total})
                # Family sees roughly where each place is (about 1 km), never the exact address.
                out.setdefault("places", []).append({"who": m["name"], "label": p["label"] or "Home",
                                                     "lat": round(p["lat"], 2), "lon": round(p["lon"], 2)})
            people.append({"name": m["name"], "role": m["role"], "you": m["id"] == a["id"], "safe_at": m["safe_at"], "places": places})
        out["people"] = people
    if c["lat"] is not None:
        out["center"] = {"lat": c["lat"], "lon": c["lon"]}
    out["reports"] = _community_reports(c)
    return jsonify(out)


@app.post("/api/communities/<cid>/leave")
def leave_community(cid):
    a, c = own_community(cid)
    if c["kind"] in OFFICIAL_KINDS:
        raise BadRequest("You stay in your county and city communities while you have a plan there")
    db.execute("DELETE FROM community_members WHERE community_id = ? AND account_id = ?", (cid, a["id"]))
    if c["kind"] in GROUP_KINDS and not db.one("SELECT 1 AS x FROM community_members WHERE community_id = ?", (cid,)):
        db.execute("DELETE FROM communities WHERE id = ?", (cid,))
    return jsonify({"ok": True})


@app.post("/api/communities/<cid>/safe")
def mark_safe(cid):
    a, c = own_community(cid)
    if c["kind"] != "family":
        raise BadRequest("Check-ins are for family groups")
    db.execute("UPDATE community_members SET safe_at = ? WHERE community_id = ? AND account_id = ?",
               (now_iso() if body().get("safe", True) else None, cid, a["id"]))
    return get_community(cid)


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
