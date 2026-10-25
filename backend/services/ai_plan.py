"""Use AI to put the checklist into the household's own language.

The rules in checklist.py decide WHAT is on the list. The AI only changes HOW
it is said: plain words, the family's language, and a short personal summary.
We check its answer: every task id must come back, nothing new is added to
the safety steps, and if anything is off we keep the original English.
"""
from services import gemini
from services.http import ServiceError

LANGUAGES = {
    "en": "English", "es": "Spanish", "ne": "Nepali",
    "zh": "Simplified Chinese, the way Mandarin speakers in mainland China write",
    "zh-Hant": "Traditional Chinese, the way Mandarin speakers in Taiwan write",
    "yue": "Traditional Chinese as written in Hong Kong, the standard written Chinese that Cantonese speakers read",
    "tl": "Tagalog", "vi": "Vietnamese", "ko": "Korean", "hi": "Hindi", "ar": "Arabic", "ru": "Russian",
}


def personalize(items, risk, place, household, language):
    lang = LANGUAGES.get(language, "English")
    slim = [{"id": i["id"], "title": i["title"], "why": i["why"]} for i in items]
    factors = "; ".join(f"{f['label']}: {f['detail']}" for f in risk["factors"] if f["points"] > 0)
    h = household or {}
    who = ", ".join(k.replace("_", " ") for k, v in h.items() if v is True) or "not given"
    if h.get("role") == "farmer":
        grows = ", ".join((h.get("farm") or {}).get("grows") or []) or "a farm"
        who = f"a farmer ({grows}); household: {who}"
    prompt = f"""You help families get ready for a strong El Niño winter. Write in {lang}, in plain words a 12-year-old understands.
Place: {place}. Storm risk: {risk['level']} ({risk['score']}/100). Why: {factors or 'no special risks found'}.
Household: {who}.
1. Write "summary": 2 short sentences telling this household what matters most for them and the first thing to do.
2. Rewrite every task below in {lang}. Keep the meaning and every safety number exactly (gallons, inches, days, phone numbers, program names, website names). Do not add or remove tasks.
Tasks: {slim}
Reply with ONLY JSON: {{"summary": "...", "items": [{{"id": "...", "title": "...", "why": "..."}}]}}"""
    text, _ = gemini.generate([{"text": prompt}], json_mode=True, temperature=0.2)
    data = gemini.parse_json(text)
    got = {i.get("id"): i for i in data.get("items", []) if isinstance(i, dict)}
    if set(got) != {i["id"] for i in items}:
        raise ServiceError("AI changed the task list")
    out = []
    for i in items:
        g = got[i["id"]]
        title, why = str(g.get("title") or "").strip(), str(g.get("why") or "").strip()
        out.append({**i, "title": title or i["title"], "why": why or i["why"]})
    return str(data.get("summary") or "").strip(), out


def fallback_summary(risk, place):
    top = next((f for f in risk["factors"] if f["points"] > 0 and f["key"] != "el_nino"), None)
    if risk.get("hazard") == "drought":
        lead = {"high": "Your drought risk is high.", "elevated": "Your drought risk is elevated.",
                "lower": "Your drought risk is lower than many places, but El Niño can still bring a late or weak monsoon."}[risk["level"]]
    else:
        lead = {"high": "Your storm risk is high.", "elevated": "Your storm risk is elevated.",
                "lower": "Your storm risk is lower than many places, but El Niño storms can still cut power and close roads."}[risk["level"]]
    why = f" The biggest reason: {top['label'].lower()}." if top else ""
    return f"{lead}{why} Start with the tasks marked first, and sign up for emergency alerts today."
