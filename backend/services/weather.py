"""Live weather from the U.S. National Weather Service (api.weather.gov).

Free and official, no key needed. We use two parts of it:
- active alerts for an exact point (flood warnings, high surf, wind...)
- the 7-day forecast, to spot heavy rain coming
"""
import db
import config
from services.http import get_json, ServiceError

NWS = "https://api.weather.gov"
HEADERS = {"Accept": "application/geo+json"}

# Alerts that matter most during an El Nino winter in California.
STORM_EVENTS = ("Flood", "Flash Flood", "Coastal Flood", "High Surf", "Storm", "Wind", "Rain",
                "Debris Flow", "Winter", "Tsunami", "Hydrologic")


def alerts(lat, lon):
    key = f"alerts:{lat:.3f},{lon:.3f}"
    hit = db.cache_get(key)
    if hit is not None:
        return hit
    data = get_json(f"{NWS}/alerts/active", {"point": f"{lat:.4f},{lon:.4f}"}, HEADERS)
    out = []
    for f in data.get("features", []):
        p = f.get("properties", {})
        event = p.get("event", "")
        out.append({
            "event": event,
            "headline": p.get("headline") or event,
            "severity": p.get("severity"),          # Extreme, Severe, Moderate, Minor, Unknown
            "urgency": p.get("urgency"),
            "kind": "warning" if "Warning" in event else "watch" if "Watch" in event else "advisory",
            "storm_related": any(w in event for w in STORM_EVENTS),
            "starts": p.get("onset") or p.get("effective"),
            "ends": p.get("ends") or p.get("expires"),
            "description": (p.get("description") or "")[:1200],
            "instruction": (p.get("instruction") or "")[:800],
            "area": p.get("areaDesc"),
            "source": "National Weather Service",
        })
    order = {"warning": 0, "watch": 1, "advisory": 2}
    out.sort(key=lambda a: order[a["kind"]])
    db.cache_set(key, out, config.CACHE_TTL["alerts"])
    return out


def forecast(lat, lon):
    key = f"fc:{lat:.2f},{lon:.2f}"
    hit = db.cache_get(key)
    if hit is not None:
        return hit
    pkey = f"pt:{lat:.3f},{lon:.3f}"
    point = db.cache_get(pkey)
    if point is None:
        p = get_json(f"{NWS}/points/{lat:.4f},{lon:.4f}", None, HEADERS).get("properties", {})
        point = {"forecast": p.get("forecast"), "office": p.get("cwa")}
        db.cache_set(pkey, point, config.CACHE_TTL["points"])
    if not point.get("forecast"):
        raise ServiceError("no forecast for this spot")
    periods = get_json(point["forecast"], None, HEADERS).get("properties", {}).get("periods", [])
    out = []
    for p in periods[:14]:
        pop = (p.get("probabilityOfPrecipitation") or {}).get("value")
        out.append({
            "name": p.get("name"), "start": p.get("startTime"), "is_day": p.get("isDaytime"),
            "temp": p.get("temperature"), "temp_unit": p.get("temperatureUnit"),
            "wind": p.get("windSpeed"), "short": p.get("shortForecast"),
            "rain_chance": pop if pop is not None else 0,
        })
    db.cache_set(key, out, config.CACHE_TTL["forecast"])
    return out


def rain_outlook(periods):
    """Summarize the forecast into one line the app can show."""
    if not periods:
        return None
    wet = [p for p in periods if (p["rain_chance"] or 0) >= 50]
    peak = max(periods, key=lambda p: p["rain_chance"] or 0)
    return {
        "wet_periods": len(wet),
        "peak_chance": peak["rain_chance"] or 0,
        "peak_when": peak["name"],
        "summary": (f"Rain likely {peak['name']} ({peak['rain_chance']}% chance)" if wet
                    else "No heavy rain in the 7-day forecast"),
    }
