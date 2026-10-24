"""Turn an address into coordinates, county and city.

1st choice: the U.S. Census Bureau Geocoder. Free, no key, official, and it
   returns the county directly, which we need to pick the right alert system
   and sandbag sites.
2nd choice: OpenStreetMap Nominatim, for places the Census can't match
   (landmarks, partial addresses, places outside the U.S.).
"""
import db
import config
from services.http import get_json, ServiceError

CENSUS = "https://geocoding.geo.census.gov/geocoder/geographies"
NOMINATIM = "https://nominatim.openstreetmap.org"


def _clean_county(name):
    return (name or "").replace(" County", "").strip() or None


_SUFFIXES = (" city and borough", " city", " town", " village", " borough", " CCD", " CDP", " municipality")


def clean_city(name):
    """The Census calls places "San Bruno city" or "Half Moon Bay CCD". People just say "San Bruno"."""
    name = (name or "").strip()
    for s in _SUFFIXES:
        if name.endswith(s):
            return name[: -len(s)].strip() or None
    return name or None


def _from_census_geo(geos):
    counties = geos.get("Counties") or []
    places = geos.get("Incorporated Places") or geos.get("County Subdivisions") or []
    states = geos.get("States") or []
    return {
        "county": _clean_county(counties[0]["NAME"]) if counties else None,
        "city": clean_city(places[0].get("BASENAME") or places[0]["NAME"]) if places else None,
        "state": states[0].get("STUSAB") if states else None,
    }


def geocode(address):
    key = "geo:" + address.strip().lower()
    hit = db.cache_get(key)
    if hit:
        return hit
    result = None
    try:
        data = get_json(f"{CENSUS}/onelineaddress", {
            "address": address, "benchmark": "Public_AR_Current",
            "vintage": "Current_Current", "format": "json"})
        matches = data.get("result", {}).get("addressMatches") or []
        if matches:
            m = matches[0]
            result = {"lat": m["coordinates"]["y"], "lon": m["coordinates"]["x"],
                      "address": m.get("matchedAddress", address), "source": "U.S. Census Geocoder",
                      **_from_census_geo(m.get("geographies", {}))}
    except (ServiceError, KeyError, IndexError, TypeError):
        result = None
    if result is None:
        result = _nominatim(address)
    if result is None:
        raise ServiceError("We couldn't find that address. Try adding the city and state.")
    db.cache_set(key, result, config.CACHE_TTL["geocode"])
    return result


def _nominatim(address):
    try:
        data = get_json(f"{NOMINATIM}/search", {"q": address, "format": "jsonv2", "limit": 1, "addressdetails": 1})
    except ServiceError:
        return None
    if not data:
        return None
    d = data[0]
    a = d.get("address", {})
    return {"lat": float(d["lat"]), "lon": float(d["lon"]), "address": d.get("display_name", address),
            "county": _clean_county(a.get("county")), "city": a.get("city") or a.get("town") or a.get("village"),
            "state": a.get("ISO3166-2-lvl4", "").replace("US-", "") or a.get("state"),
            "country": (a.get("country_code") or "").upper() or None, "source": "OpenStreetMap"}


def reverse(lat, lon):
    """Coordinates (from 'use my location') to county and city."""
    key = f"rev:{lat:.3f},{lon:.3f}"
    hit = db.cache_get(key)
    if hit:
        return hit
    result = None
    try:
        data = get_json(f"{CENSUS}/coordinates", {
            "x": lon, "y": lat, "benchmark": "Public_AR_Current",
            "vintage": "Current_Current", "format": "json"})
        geos = data.get("result", {}).get("geographies", {})
        if geos.get("Counties"):
            result = {"lat": lat, "lon": lon, "address": None, "source": "U.S. Census Geocoder", **_from_census_geo(geos)}
    except ServiceError:
        result = None
    if result is None:
        try:
            d = get_json(f"{NOMINATIM}/reverse", {"lat": lat, "lon": lon, "format": "jsonv2", "zoom": 14, "addressdetails": 1})
            a = d.get("address", {})
            result = {"lat": lat, "lon": lon, "address": d.get("display_name"),
                      "county": _clean_county(a.get("county")), "city": a.get("city") or a.get("town") or a.get("village"),
                      "state": a.get("ISO3166-2-lvl4", "").replace("US-", "") or a.get("state"),
                      "country": (a.get("country_code") or "").upper() or None, "source": "OpenStreetMap"}
        except ServiceError:
            result = {"lat": lat, "lon": lon, "address": None, "county": None, "city": None, "state": None, "source": None}
    db.cache_set(key, result, config.CACHE_TTL["geocode"])
    return result
