"""Where to get help: sandbag sites, alert systems, shelters, hotlines.

Two layers:
  1. A hand-checked list (data/resources.json), each entry with its source.
     Sandbag addresses are turned into map points with the same geocoder
     and sorted by real distance from the household.
  2. For counties we haven't checked by hand yet, an AI web search finds
     local sandbag sites and help, and every result keeps its source link
     and an "AI found this, confirm before you go" label.
"""
import json
import math
import os

import config
import db
from services import gemini, geocode
from services.http import ServiceError

_DATA = None


def data():
    global _DATA
    if _DATA is None:
        with open(os.path.join(os.path.dirname(__file__), "..", "data", "resources.json"), encoding="utf-8") as f:
            _DATA = json.load(f)
    return _DATA


def miles(a_lat, a_lon, b_lat, b_lon):
    """Great-circle distance (haversine formula)."""
    r = 3958.8
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lon - a_lon)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def alert_system(county):
    return data()["alert_systems"].get(county or "")


def sandbag_sites(county, lat, lon, limit=4):
    sites = [s for s in data()["sandbag_sites"] if s["county"] == county]
    out = []
    for s in sites:
        try:
            g = geocode.geocode(s["address"])
        except ServiceError:
            continue
        out.append({**s, "lat": g["lat"], "lon": g["lon"], "miles": round(miles(lat, lon, g["lat"], g["lon"]), 1), "verified": True})
    out.sort(key=lambda s: s["miles"])
    return out[:limit]


def ai_local_help(county, city, state):
    """AI web search for counties without a hand-checked list."""
    key = f"aihelp:{county}:{city}:{state}"
    hit = db.cache_get(key)
    if hit is not None:
        return hit
    place = ", ".join(x for x in [city, f"{county} County" if county else None, state] if x)
    prompt = f"""Use Google Search to find official places to get free sandbags and official storm/flood help for residents of {place} for the 2026-27 El Niño winter.
Only include places from official city, county or agency websites you found. Never guess an address.
Reply with ONLY JSON: {{"sites": [{{"name": "...", "address": "street address or empty", "notes": "hours, limits or rules if listed", "kind": "sandbags or help"}}]}}"""
    text, meta = gemini.generate([{"text": prompt}], search=True, temperature=0.1)
    found = gemini.parse_json(text).get("sites", [])[:6]
    srcs = gemini.sources(meta)
    out = {"sites": [{"name": str(s.get("name", ""))[:90], "address": str(s.get("address", ""))[:140],
                      "notes": str(s.get("notes", ""))[:240], "kind": s.get("kind") if s.get("kind") in ("sandbags", "help") else "help",
                      "verified": False} for s in found if s.get("name")],
           "sources": srcs[:6]}
    db.cache_set(key, out, config.CACHE_TTL["aihelp"])
    return out


def for_place(place, lat, lon):
    county = place.get("county")
    d = data()
    result = {
        "alert_system": alert_system(county),
        "county": d["county"].get(county or "", []),
        "statewide": d["statewide"] if (place.get("state") or "").upper() in ("CA", "CALIFORNIA") else [d["statewide"][0], d["statewide"][1]],
        "sandbags": sandbag_sites(county, lat, lon),
        "ai": None,
        "checked": d["checked"],
    }
    if not result["sandbags"] and gemini.available():
        try:
            result["ai"] = ai_local_help(county, place.get("city"), place.get("state"))
        except ServiceError:
            result["ai"] = None
    return result
