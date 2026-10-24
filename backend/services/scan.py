"""AI Scan: look at a photo of your home, yard, street or field and find the
El Nino risks you can actually see, then turn each one into a checklist task.

Example: a photo of a front door shows a downspout emptying against the wall
and leaves in the gutter, so the plan gets "Point the downspout away from the
house" and "Clear the gutter above the front door".

Guardrails: the AI may only report things visible in the photo, never people,
and its findings are added as extra tasks marked "From your photo", never
replacing the rule-based safety steps.
"""
import hashlib

from services import gemini
from services.ai_plan import LANGUAGES


def scan(photo_data_url, *, hazard, role, place, language="en"):
    lang = LANGUAGES.get(language, "English")
    what = "farm field, barn or farm equipment" if role == "farmer" else "home, yard, building or street"
    danger = ("drought and extreme heat (a weak monsoon or dry season)" if hazard == "drought"
              else "heavy rain, flooding, high tides, mudslides, high winds and power outages")
    prompt = f"""You are helping a {'farmer' if role == 'farmer' else 'family'} in {place} get ready for a strong El Niño, which there usually means {danger}.
Look at this photo of their {what}. Ignore any people and never describe them.
Find up to 5 specific things you can SEE in the photo that make El Niño damage more likely, and a fix they can do themselves soon.
Only report what is visible. If the photo doesn't show a home, yard, street, building or farm, return no findings.
Write in {lang}, in plain words.
Reply with ONLY JSON: {{"seen": "one sentence: what the photo shows", "findings": [{{"title": "short task, starting with a verb", "why": "1 sentence: what you see and why it matters", "urgency": 1 to 3 (1 = do first)}}]}}"""
    b64 = photo_data_url.split(",", 1)[1]
    text, _ = gemini.generate([{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": b64}}],
                              json_mode=True, temperature=0.2)
    data = gemini.parse_json(text)
    tag = hashlib.sha1(b64[:4000].encode()).hexdigest()[:6]
    findings = []
    for n, f in enumerate((data.get("findings") or [])[:5]):
        if not isinstance(f, dict) or not f.get("title"):
            continue
        try:
            urgency = max(1, min(3, int(f.get("urgency", 2))))
        except (TypeError, ValueError):
            urgency = 2
        findings.append({"id": f"scan_{tag}_{n}", "group": "now", "title": str(f["title"])[:90],
                         "why": str(f.get("why") or "")[:240], "priority": urgency, "link": None, "source": "scan"})
    return {"seen": str(data.get("seen") or "")[:200], "findings": findings}
