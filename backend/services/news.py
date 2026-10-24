"""El Nino news for a region, with the real sources, refreshed every 6 hours.

Uses Gemini with Google Search grounding. The model must only use what it
found, and each story keeps links from the search results so people can
read the original reporting.
"""
import config
import db
from services import gemini
from services.ai_plan import LANGUAGES


def region_news(county, state, language="en"):
    key = f"news:{county}:{state}:{language}"
    hit = db.cache_get(key)
    if hit is not None:
        return hit
    lang = LANGUAGES.get(language, "English")
    place = ", ".join(x for x in [f"{county} County" if county else None, state] if x) or "California"
    prompt = f"""Use Google Search to find 4 to 6 recent, real news updates about the 2026-27 El Niño and winter storm preparation that matter to people in {place}: official forecasts, emergency declarations, storm warnings, sandbag and shelter announcements, road or power impacts, and new help programs. Prefer the last 30 days and official or local news sources.
Never invent facts, dates or numbers. Write in {lang}, in plain words.
Reply with ONLY JSON: {{"headline": "one sentence: the most important thing to know this week", "items": [{{"title": "under 12 words", "date": "date if known or empty", "summary": "2 sentences", "action": "1 short sentence: what a household can do about it, or empty"}}]}}"""
    text, meta = gemini.generate([{"text": prompt}], search=True, temperature=0.2)
    data = gemini.parse_json(text)
    srcs = gemini.sources(meta)
    out = {
        "headline": str(data.get("headline", ""))[:300],
        "items": [{"title": str(i.get("title", ""))[:120], "date": str(i.get("date", ""))[:40],
                   "summary": str(i.get("summary", ""))[:500], "action": str(i.get("action", ""))[:200]}
                  for i in data.get("items", [])[:6] if isinstance(i, dict) and i.get("title")],
        "sources": srcs[:10],
        "ai": True,
    }
    db.cache_set(key, out, config.CACHE_TTL["news"])
    return out
