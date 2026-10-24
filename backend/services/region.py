"""Which El Nino region a place is in, and what El Nino usually does there.

The same El Nino floods California and dries out the monsoon in Nepal, so the
plan has to know the region before it knows what to prepare for.
"""
import json
import os

_REGIONS = None

US_STATES = {
    "CA": "california",
    "WA": "pacific-northwest", "OR": "pacific-northwest", "ID": "pacific-northwest",
    "TX": "us-south", "LA": "us-south", "MS": "us-south", "AL": "us-south", "GA": "us-south",
    "FL": "us-south", "SC": "us-south", "NC": "us-south",
}
COUNTRIES = {
    "NP": "south-asia", "IN": "south-asia", "BD": "south-asia", "PK": "south-asia", "LK": "south-asia", "BT": "south-asia",
    "PE": "peru-ecuador", "EC": "peru-ecuador",
    "ID": "indonesia-australia", "AU": "indonesia-australia", "PG": "indonesia-australia",
    "ZA": "southern-africa", "ZW": "southern-africa", "ZM": "southern-africa", "MW": "southern-africa", "MZ": "southern-africa", "BW": "southern-africa",
    "KE": "east-africa", "TZ": "east-africa", "UG": "east-africa", "ET": "east-africa", "SO": "east-africa",
    "GT": "central-america", "HN": "central-america", "SV": "central-america", "NI": "central-america",
    "BR": "southern-south-america", "UY": "southern-south-america", "AR": "southern-south-america",
}


def regions():
    global _REGIONS
    if _REGIONS is None:
        with open(os.path.join(os.path.dirname(__file__), "..", "data", "regions.json"), encoding="utf-8") as f:
            _REGIONS = json.load(f)
    return _REGIONS


def for_place(place):
    country = (place.get("country") or "US").upper()
    rid = US_STATES.get((place.get("state") or "").upper()) if country == "US" else COUNTRIES.get(country)
    if not rid:
        return None
    return next((r for r in regions()["regions"] if r["id"] == rid), None)


def hazard(region):
    """The main El Nino danger to plan for: 'flood' or 'drought'."""
    if not region:
        return "flood"
    return "drought" if "drier" in region["effect"] else "flood"
