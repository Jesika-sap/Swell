"""Translate the app's own words (buttons, headings, weather, risk reasons...)
into the plan's language, so the whole screen matches, not just the checklist.

Each phrase is translated once per language and saved for 60 days, so after
the first time a screen appears in Nepali it loads instantly for everyone.
"""
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor

import db
from services import gemini
from services.http import ServiceError

TTL = 60 * 24 * 3600
CHUNK = 25  # phrases per AI call; several calls run at once


def _key(lang, text):
    return f"tr:{lang}:{hashlib.sha1(text.encode()).hexdigest()}"


def _ask(lang_name, texts):
    numbered = {str(i): t for i, t in enumerate(texts)}
    prompt = f"""Translate each phrase from a family emergency-preparedness app into {lang_name}.
Use plain, everyday words a 12-year-old understands. Keep it short, like app buttons and labels.
Keep exactly as written: numbers, dates' digits, percentages, phone numbers, website names, and names of people,
places, organizations, programs and agencies (for example FEMA, NOAA, USGS, SMC Alert, Swell).
If a phrase is only a name or a number, return it unchanged.
Phrases (JSON, keyed by number): {json.dumps(numbered, ensure_ascii=False)}
Reply with ONLY JSON with the same keys: {{"0": "...", "1": "..."}}"""
    text, _ = gemini.generate([{"text": prompt}], json_mode=True, temperature=0.1)
    data = gemini.parse_json(text)
    out = {}
    for i, t in enumerate(texts):
        v = data.get(str(i)) if isinstance(data, dict) else None
        if isinstance(v, str) and v.strip():
            out[t] = v.strip()
    return out


def translate(texts, lang, lang_name):
    """Returns ({english: translated}, failed). Missing phrases stay English."""
    found, todo = {}, []
    for t in texts:
        hit = db.cache_get(_key(lang, t))
        if hit is not None:
            found[t] = hit
        elif t not in todo:
            todo.append(t)
    failed = False
    if todo:
        chunks = [todo[i:i + CHUNK] for i in range(0, len(todo), CHUNK)]
        print(f"[Swell] Translating {len(todo)} bits of screen text into {lang_name.split(',')[0]}...", flush=True)
        with ThreadPoolExecutor(max_workers=6) as pool:
            for res in pool.map(lambda c: _safe(lang_name, c), chunks):
                if res is None:
                    failed = True
                    continue
                for en, tr in res.items():
                    db.cache_set(_key(lang, en), tr, TTL)
                    found[en] = tr
    return found, failed


def _safe(lang_name, chunk):
    try:
        return _ask(lang_name, chunk)
    except (ServiceError, ValueError) as e:
        print(f"[Swell] Couldn't translate screen text ({lang_name}): {e}", flush=True)
        return None
