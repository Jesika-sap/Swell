"""Look at a neighbor's photo and label the storm problem in it.

People report from their phones, often in the rain, so the AI fills in the
category, a short title and how dangerous it looks. The person can change any
of it before posting. Photos showing people are never described.
"""
from services import gemini

KINDS = {
    "flooding": "Flooded street or sidewalk",
    "drain": "Clogged storm drain",
    "landslide": "Landslide or mudslide",
    "tree": "Fallen tree or branches",
    "power": "Downed power line",
    "road": "Road damage or closure",
    "other": "Other storm problem",
}


def classify(data_url, note=""):
    b64 = data_url.split(",", 1)[1]
    prompt = f"""This photo was reported during a storm.{f' Note from the person: "{note}".' if note else ''}
Ignore any people and never describe them.
Reply with ONLY JSON: {{"is_storm_problem": true or false, "kind": one of {list(KINDS)}, "title": "under 7 words", "severity": 1 to 3 (3 = dangerous, keep away), "advice": "one short safety sentence"}}"""
    text, _ = gemini.generate([{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": b64}}], json_mode=True, temperature=0.1)
    r = gemini.parse_json(text)
    kind = r.get("kind") if r.get("kind") in KINDS else "other"
    try:
        sev = max(1, min(3, int(r.get("severity", 2))))
    except (TypeError, ValueError):
        sev = 2
    return {"is_storm_problem": r.get("is_storm_problem") is not False, "kind": kind,
            "title": str(r.get("title") or KINDS[kind])[:60], "severity": sev, "advice": str(r.get("advice", ""))[:200]}
