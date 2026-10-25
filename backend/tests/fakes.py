"""Fake versions of every outside service, so tests run offline and the
same way every time. The shapes match the real services' JSON."""
import json

CALLS = []
FAIL = set()        # hosts to pretend are down
GEMINI_MODE = {"plan": "ok"}

SITES = {
    "1949 pacific blvd": (37.5487, -122.3001),
    "2720 alameda de las pulgas": (37.5326, -122.3299),
    "anchor rd": (37.5779, -122.3036),
    "1400 broadway": (37.4885, -122.2185),
    "752 chestnut": (37.4783, -122.2287),
    "burgess dr": (37.4567, -122.1820),
    "1467 chilco": (37.4776, -122.1715),
    "150 tara": (37.4623, -122.1306),
    "203 cornell": (37.5042, -122.4949),
    "59 entrada": (37.3191, -122.2735),
    "1000 pescadero": (37.2551, -122.3810),
}


def census_match(address):
    a = address.lower()
    for k, (lat, lon) in SITES.items():
        if k in a:
            return lat, lon, "San Mateo"
    if "millbrae" in a or "murchison" in a:
        return 37.5985, -122.3872, "San Mateo"
    if "foster city" in a:
        return 37.5585, -122.2711, "San Mateo"
    if "sacramento" in a:
        return 38.5816, -121.4944, "Sacramento"
    return None


def fake(method, url, **kw):
    CALLS.append((method, url))
    host = url.split("/")[2]
    if host in FAIL:
        return 503, {}
    params = kw.get("params") or {}

    if "geocoding.geo.census.gov" in url and "onelineaddress" in url:
        m = census_match(params["address"])
        if not m:
            return 200, {"result": {"addressMatches": []}}
        lat, lon, county = m
        city = "Foster City" if lat == 37.5585 else "Sacramento" if county == "Sacramento" else "Millbrae"
        return 200, {"result": {"addressMatches": [{"matchedAddress": params["address"].upper(),
                     "coordinates": {"x": lon, "y": lat},
                     "geographies": {"Counties": [{"NAME": f"{county} County"}], "Incorporated Places": [{"NAME": city}], "States": [{"STUSAB": "CA"}]}}]}}
    if "geocoding.geo.census.gov" in url and "coordinates" in url:
        return 200, {"result": {"geographies": {"Counties": [{"NAME": "San Mateo County"}], "Incorporated Places": [{"NAME": "Millbrae"}], "States": [{"STUSAB": "CA"}]}}}
    if "nominatim" in url:
        q = (params.get("q") or "").lower()
        if "nepal" in q or "chitwan" in q:
            return 200, [{"lat": "27.5291", "lon": "84.3542", "display_name": "Bharatpur, Chitwan, Nepal",
                          "address": {"city": "Bharatpur", "county": "Chitwan", "state": "Bagmati Province", "country_code": "np"}}]
        return 200, []

    if "api.weather.gov/alerts" in url:
        lat = float(params["point"].split(",")[0])
        feats = []
        if lat < 37.57:  # Foster City: on the Bay, under a coastal flood warning in tests
            feats.append({"properties": {"event": "Coastal Flood Warning", "headline": "Coastal Flood Warning until Saturday 2 PM",
                                         "severity": "Moderate", "urgency": "Expected", "onset": "2026-11-21T08:00:00-08:00",
                                         "ends": "2026-11-22T14:00:00-08:00", "description": "Flooding of low-lying shoreline roads.",
                                         "instruction": "Avoid flooded roads.", "areaDesc": "San Francisco Bay Shoreline"}})
        return 200, {"features": feats}
    if "api.weather.gov/points" in url:
        return 200, {"properties": {"forecast": "https://api.weather.gov/gridpoints/MTR/85,105/forecast", "cwa": "MTR"}}
    if "api.weather.gov/gridpoints" in url:
        periods = [{"name": n, "startTime": "2026-10-24T06:00:00-07:00", "isDaytime": True, "temperature": 62, "temperatureUnit": "F",
                    "windSpeed": "10 mph", "shortForecast": s, "probabilityOfPrecipitation": {"value": p}}
                   for n, s, p in [("Today", "Mostly Sunny", 5), ("Tonight", "Cloudy", 20), ("Sunday", "Rain", 80), ("Sunday Night", "Heavy Rain", 90)]]
        return 200, {"properties": {"periods": periods}}

    if "hazards.fema.gov" in url:
        lon, lat = [float(x) for x in params["geometry"].split(",")]
        if lat < 37.57:
            return 200, {"features": [{"attributes": {"FLD_ZONE": "AE", "ZONE_SUBTY": None, "SFHA_TF": "T"}}]}
        return 200, {"features": [{"attributes": {"FLD_ZONE": "X", "ZONE_SUBTY": "AREA OF MINIMAL FLOOD HAZARD", "SFHA_TF": "F"}}]}
    if "epqs.nationalmap.gov" in url:
        lat = float(params["y"])
        return 200, {"value": "6.2" if lat < 37.57 else "48.0"}

    if "generativelanguage.googleapis.com" in url and method == "GET":
        return 200, {"models": [{"name": "models/gemini-flash-latest", "supportedGenerationMethods": ["generateContent"]}]}
    if "generativelanguage.googleapis.com" in url:
        body = kw.get("json") or {}
        prompt = body["contents"][0]["parts"][0]["text"]
        meta = {}
        if GEMINI_MODE.get("plan") == "down":
            return 503, {}
        if "Rewrite every task" in prompt:
            start = prompt.index("Tasks: ") + 7
            end = prompt.index("\nReply with ONLY JSON")
            import ast
            tasks = ast.literal_eval(prompt[start:end])
            lang_es = "Write in Spanish" in prompt
            if GEMINI_MODE.get("plan") == "drop":
                tasks = tasks[1:]
            items = [{"id": t["id"], "title": ("ES: " if lang_es else "") + t["title"], "why": t["why"]} for t in tasks]
            text = json.dumps({"summary": "Tu riesgo es alto. Consigue sacos de arena hoy." if lang_es else "Your risk is high. Get sandbags today.", "items": items})
        elif "sandbags" in prompt and "official places" in prompt:
            text = json.dumps({"sites": [{"name": "Sacramento City Corporation Yard", "address": "5730 24th St, Sacramento, CA", "notes": "Free sandbags while supplies last", "kind": "sandbags"}]})
            meta = {"groundingChunks": [{"web": {"uri": "https://example.gov/sandbags", "title": "cityofsacramento.gov"}}]}
        elif "news updates" in prompt:
            text = "```json\n" + json.dumps({"headline": "San Mateo County declared an El Niño emergency.", "items": [
                {"title": "County declares El Niño emergency", "date": "Oct 20, 2026", "summary": "The board created a task force.", "action": "Sign up for SMC Alert."}]}) + "\n```"
            meta = {"groundingChunks": [{"web": {"uri": "https://example.org/a", "title": "smcgov.org"}}, {"web": {"uri": "https://example.org/b", "title": "almanacnews.com"}}]}
        elif "disaster-preparedness inspector" in prompt:
            text = json.dumps({"seen": "The front of a one-story house with a gutter and a downspout.", "findings": [
                {"title": "Clear leaves out of the gutter", "where": "top of the photo, above the door", "why": "Leaves are piled in the gutter, so water will spill over in heavy rain.", "fix": "Scoop the leaves out and rinse with a hose.", "effort": "easy", "urgency": 2, "confidence": "high"},
                {"title": "Point the downspout away from the house", "where": "right corner of the house", "why": "The downspout empties right against the wall, so rain will pool by the foundation.", "fix": "Add a downspout extension that ends 4 feet from the wall.", "effort": "easy", "urgency": 1, "confidence": "high"},
                {"title": "Check the roof for loose shingles", "why": "Something on the roof might be loose.", "urgency": 2, "confidence": "low"}],
                "good": ["Doormat area is raised above the walkway"], "next_photo": "The roof gutters from below"})
        elif "reported during a storm" in prompt:
            text = json.dumps({"is_storm_problem": True, "kind": "drain", "title": "Clogged storm drain on corner", "severity": 2, "advice": "Don't clear it during the storm."})
        else:
            text = "{}"
        return 200, {"candidates": [{"content": {"parts": [{"text": text}]}, "groundingMetadata": meta}]}

    return 404, {}
