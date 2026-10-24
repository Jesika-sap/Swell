"""The storm risk score: an explainable 0-100 number for one address.

Why not just ask the AI? Because a risk number for someone's home must be
consistent and checkable. The same address always gets the same score, and
every point comes from a named public data source the user can see. The AI
is only used later, to explain the plan in plain language and other languages.

Points (capped at 100):
  FEMA flood zone       high +40, moderate +20, unknown/unmapped +5
  Ground elevation      under 10 ft +25, under 25 ft +12
  King tide exposure    low ground in a Bay Area county during the season +10
  Live NWS alerts       storm warning +30, watch +15, advisory +8 (highest one)
  Rain in the forecast  70%+ chance in the next 7 days +10, 50%+ +5
  El Nino season        strong event forecast for California +5 baseline
Levels: 55+ High, 30-54 Elevated, under 30 Lower.
"""
from datetime import date

HIGH, ELEVATED = 55, 30
US_STATES = {"AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
             "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
             "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "PR", "CALIFORNIA"}


def _span(a, b):
    """'2026-11-21', '2026-11-28' -> 'Nov 21-28, 2026'"""
    da, db_ = date.fromisoformat(a), date.fromisoformat(b)
    if da.month == db_.month:
        return f"{da:%b} {da.day}–{db_.day}, {da.year}"
    return f"{da:%b} {da.day}–{db_:%b} {db_.day}, {db_.year}"


def king_tide_windows(tides, today=None):
    today = today or date.today()
    out = []
    for w in tides["windows"]:
        end = date.fromisoformat(w["end"])
        if end >= today:
            out.append({**w, "active": date.fromisoformat(w["start"]) <= today <= end})
    return out


def score(*, flood=None, elevation=None, alerts=None, rain=None, county=None, state=None, tides=None, today=None,
          region=None, role="household"):
    factors = []

    def add(key, points, label, detail, source):
        factors.append({"key": key, "points": points, "label": label, "detail": detail, "source": source})

    # 1. FEMA flood zone (U.S. only: FEMA maps don't cover other countries)
    in_us = (state or "").upper() in US_STATES
    if not in_us and not flood:
        pass
    elif flood:
        pts = {"high": 40, "moderate": 20, "unknown": 5}.get(flood["level"], 0)
        add("flood_zone", pts, "Flood zone", flood["text"] + (f" (zone {flood['zone']})" if flood.get("zone") else ""), flood["source"])
    else:
        add("flood_zone", 5, "Flood zone", "Couldn't check the FEMA flood map right now", "FEMA National Flood Hazard Layer")

    # 2. Elevation
    if elevation is not None:
        if elevation < 10:
            add("elevation", 25, "Low ground", f"About {elevation:g} ft above sea level. Low ground floods first in storm surge and king tides.", "USGS Elevation Point Query Service")
        elif elevation < 25:
            add("elevation", 12, "Low-lying ground", f"About {elevation:g} ft above sea level.", "USGS Elevation Point Query Service")
        else:
            add("elevation", 0, "Elevation", f"About {elevation:g} ft above sea level.", "USGS Elevation Point Query Service")

    # 3. King tides (Bay Area counties, low ground only)
    tide_windows = []
    if tides and county in tides["counties"]:
        tide_windows = king_tide_windows(tides, today)
        if tide_windows and elevation is not None and elevation < 25:
            nxt = tide_windows[0]
            add("king_tides", 10, "King tides", f"Extra-high tides {_span(nxt['start'], nxt['end'])}. Ocean levels are running 1 to 2 ft above tide tables this winter.", tides["source"]["title"])

    # 4. Live alerts
    storm = [a for a in (alerts or []) if a.get("storm_related")]
    if storm:
        top = storm[0]
        pts = {"warning": 30, "watch": 15, "advisory": 8}[top["kind"]]
        add("alerts", pts, "Active alert", top["event"], "National Weather Service")

    # 5. Rain coming
    if rain and rain.get("peak_chance") is not None:
        c = rain["peak_chance"]
        pts = 10 if c >= 70 else 5 if c >= 50 else 0
        add("rain", pts, "Rain forecast", rain["summary"], "National Weather Service")

    # 6. El Nino season baseline for California
    if (state or "").upper() in ("CA", "CALIFORNIA"):
        add("el_nino", 5, "El Niño winter", "A strong El Niño is forecast, which usually means more and stronger storms in California.", "NOAA Climate Prediction Center")
    elif region:
        # Outside California we usually can't get local flood maps, so the
        # regional El Nino pattern carries more of the score.
        add("el_nino", 20, "El Niño where you live",
            f"{region['name']} is usually {region['effect']} in El Niño years ({region['season']}). {region['impact']}",
            "NOAA Climate.gov")

    # 7. Farms: income and food depend on the weather
    haz = "drought" if region and "drier" in region["effect"] else "flood"
    if role == "farmer":
        detail = ("A weak or late monsoon can mean lost harvests, less water for animals and lost income."
                  if haz == "drought" else
                  "Flooded fields, washed-out soil and stranded animals hit farms first, and recovery takes longer.")
        add("livelihood", 10, "Your farm depends on the weather", detail, "Your answers")

    total = min(100, sum(f["points"] for f in factors))
    level = "high" if total >= HIGH else "elevated" if total >= ELEVATED else "lower"
    factors.sort(key=lambda f: -f["points"])
    return {"score": total, "level": level, "factors": factors, "king_tides": tide_windows, "hazard": haz,
            "region": {k: region[k] for k in ("id", "name", "effect", "season")} if region else None}
