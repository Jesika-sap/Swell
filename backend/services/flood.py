"""Is this spot in a flood zone, and how high above sea level is it?

- FEMA's National Flood Hazard Layer (NFHL): the official flood maps used for
  flood insurance. We ask which flood zone contains the point.
- USGS Elevation Point Query Service: ground elevation in feet. Low ground
  near the Bay is what floods during king tides and storm surge, even
  outside a mapped FEMA zone.
Both are free public services with no key.
"""
import db
import config
from services.http import get_json, ServiceError

NFHL = "https://hazards.fema.gov/arcgis/rest/services/public/NFHL/MapServer/28/query"
EPQS = "https://epqs.nationalmap.gov/v1/json"


def describe_zone(zone, subtype, sfha):
    """FEMA zone codes into plain language."""
    zone = (zone or "").upper()
    subtype = (subtype or "").upper()
    if zone.startswith("V"):
        return "high", "Coastal high-risk flood zone (waves and storm surge)"
    if zone.startswith("A") or sfha == "T":
        return "high", "High-risk flood zone (1% or more chance of flooding each year)"
    if zone == "X" and "0.2" in subtype:
        return "moderate", "Moderate flood risk (0.2% chance each year)"
    if zone == "X" and "LEVEE" in subtype:
        return "moderate", "Protected by a levee, which can fail or be overtopped"
    if zone == "D":
        return "unknown", "Flood risk not yet studied here"
    if zone == "X":
        return "minimal", "Outside FEMA's mapped flood zones"
    return "unknown", "No FEMA flood map for this spot"


def flood_zone(lat, lon):
    key = f"nfhl:{lat:.4f},{lon:.4f}"
    hit = db.cache_get(key)
    if hit:
        return hit
    data = get_json(NFHL, {
        "geometry": f"{lon},{lat}", "geometryType": "esriGeometryPoint", "inSR": 4326,
        "spatialRel": "esriSpatialRelIntersects", "outFields": "FLD_ZONE,ZONE_SUBTY,SFHA_TF",
        "returnGeometry": "false", "f": "json"})
    if "error" in data:
        raise ServiceError("FEMA flood map is unavailable right now")
    feats = data.get("features") or []
    if feats:
        a = feats[0].get("attributes", {})
        level, text = describe_zone(a.get("FLD_ZONE"), a.get("ZONE_SUBTY"), a.get("SFHA_TF"))
        result = {"zone": a.get("FLD_ZONE"), "level": level, "text": text}
    else:
        result = {"zone": None, "level": "minimal", "text": "Outside FEMA's mapped flood zones"}
    result["source"] = "FEMA National Flood Hazard Layer"
    db.cache_set(key, result, config.CACHE_TTL["flood"])
    return result


def elevation_ft(lat, lon):
    key = f"elev:{lat:.4f},{lon:.4f}"
    hit = db.cache_get(key)
    if hit is not None:
        return hit
    data = get_json(EPQS, {"x": lon, "y": lat, "units": "Feet", "wkid": 4326, "includeDate": "false"})
    try:
        value = float(data.get("value"))
    except (TypeError, ValueError):
        raise ServiceError("no elevation for this spot")
    if value < -1000:  # the service's "no data" marker
        raise ServiceError("no elevation for this spot")
    value = round(value, 1)
    db.cache_set(key, value, config.CACHE_TTL["elevation"])
    return value
