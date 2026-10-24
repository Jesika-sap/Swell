"""AI Scan: look at a photo of your home, yard, street or field and find the
El Nino risks you can actually see, then turn each one into a checklist task.

Example: a photo of a front door shows a downspout emptying against the wall
and leaves in the gutter, so the plan gets "Point the downspout away from the
house" and "Clear the gutter above the front door", each with where it is in
the photo, why it matters, how to fix it and how much work that is.

How it stays trustworthy:
  * It uses Gemini's strongest image model first (Pro) and falls back to the
    faster Flash models if Pro is busy or out of free quota.
  * The AI gets a hazard-specific list of things to inspect (flood or drought,
    home or farm), so it looks where an expert would look.
  * It must say how sure it is. Anything it isn't sure about is dropped.
  * It may only report what is visible, never people, and its tasks are
    added as extras marked "From your photo". They never replace or change
    the rule-based safety steps, and never touch the risk score.
"""
import hashlib

from services import gemini
from services.ai_plan import LANGUAGES

MAX_FINDINGS = 8
SCAN_MODELS = ["gemini-pro-latest", "gemini-2.5-pro"]

LOOK_FOR = {
    ("flood", "household"): [
        "gutters and downspouts: clogged, broken, or emptying next to the wall",
        "storm drains or ditches nearby: blocked by leaves, trash or dirt",
        "ground sloping toward the house, low doorways, garage doors or basement windows",
        "valuables, papers, electronics or chemicals stored on the floor or in a garage",
        "trees or branches over the roof, cars or power lines",
        "loose items outside that wind or water could carry away",
        "hillside: cracks, bare soil, leaning fences or retaining walls (mudslide signs)",
        "roof damage, missing shingles, or tarps",
        "no visible place for sandbags, or sandbags placed wrong",
    ],
    ("flood", "farmer"): [
        "drainage ditches and culverts: blocked or too small",
        "equipment, fuel, feed, fertilizer or chemicals stored on low ground",
        "animals or pens on low ground or near a creek",
        "bare soil or slopes with no cover crop (erosion)",
        "barn or greenhouse roofs, plastic and doors that wind could tear",
        "creek or canal banks that look worn or close to the field",
        "farm roads that will turn to mud or wash out",
    ],
    ("drought", "household"): [
        "water storage: uncovered, too small, dirty or leaking",
        "leaking taps, pipes or hoses",
        "dry grass, dead plants or brush close to the house (fire risk)",
        "no shade, or rooms that will get very hot",
        "roof and gutters that could collect rain but don't",
    ],
    ("drought", "farmer"): [
        "water storage tanks, ponds or wells: uncovered, low, leaking or dirty",
        "irrigation channels or pipes: leaking, cracked or losing water to evaporation",
        "bare soil with no mulch, straw or cover",
        "crop rows that look dry, yellow or wilted",
        "animals without shade or a steady water source",
        "dry brush, straw or crop waste piled near buildings (fire risk)",
        "rooftops or slopes that could catch rainwater but don't",
    ],
}

EFFORT = {"easy": "Easy, under an hour", "medium": "Half a day or a few supplies", "hard": "Needs help or a professional"}


def scan(photo_data_url, *, hazard, role, place, language="en"):
    lang = LANGUAGES.get(language, "English")
    role = "farmer" if role == "farmer" else "household"
    hazard = "drought" if hazard == "drought" else "flood"
    what = "farm field, barn or farm equipment" if role == "farmer" else "home, yard, building or street"
    danger = ("drought and extreme heat (a weak or late monsoon or a long dry season)" if hazard == "drought"
              else "heavy rain, flooding, high tides, mudslides, high winds and power outages")
    checklist = "\n".join(f"- {x}" for x in LOOK_FOR[(hazard, role)])
    prompt = f"""You are a disaster-preparedness inspector helping a {'farmer' if role == 'farmer' else 'family'} in {place} get ready for a strong El Niño, which there usually means {danger}.
Look carefully at this photo of their {what}. Ignore any people and never describe them.

Check the photo for these things an inspector would look for:
{checklist}

Report up to {MAX_FINDINGS} specific problems you can SEE that make El Niño damage more likely, most important first.
For each one, say exactly where it is in the photo, why it matters, and how they can fix it in 1 or 2 simple steps.
Also name up to 3 things in the photo that are already done right, so they know what to keep.
If something important is cut off or hard to see, suggest one more photo they should take.
Only report what is visible. Do not guess about things you can't see. If the photo doesn't show a home, yard, street, building or farm, return no findings.
Write in {lang}, in plain words a 12-year-old could follow.
Reply with ONLY JSON:
{{"seen": "one sentence: what the photo shows",
  "findings": [{{"title": "short task, starting with a verb",
                 "where": "where in the photo, e.g. 'left side, above the front door'",
                 "why": "1 sentence: what you see and why it matters",
                 "fix": "1-2 short steps to fix it",
                 "effort": "easy" | "medium" | "hard",
                 "urgency": 1 to 3 (1 = do first),
                 "confidence": "high" | "medium" | "low"}}],
  "good": ["short phrase"],
  "next_photo": "one more photo to take, or empty"}}"""
    b64 = photo_data_url.split(",", 1)[1]
    text, _ = gemini.generate([{"text": prompt}, {"inline_data": {"mime_type": "image/jpeg", "data": b64}}],
                              json_mode=True, temperature=0.2, models=SCAN_MODELS)
    data = gemini.parse_json(text)
    tag = hashlib.sha1(b64[:4000].encode()).hexdigest()[:6]
    findings = []
    for n, f in enumerate(data.get("findings") or []):
        if len(findings) >= MAX_FINDINGS:
            break
        if not isinstance(f, dict) or not f.get("title"):
            continue
        if str(f.get("confidence", "high")).lower() == "low":
            continue  # not sure -> don't put it on someone's checklist
        try:
            urgency = max(1, min(3, int(f.get("urgency", 2))))
        except (TypeError, ValueError):
            urgency = 2
        why = " ".join(x for x in [
            f"{str(f['where']).strip().rstrip('.')}:" if f.get("where") else "",
            str(f.get("why") or "").strip(),
            f"Fix: {str(f['fix']).strip()}" if f.get("fix") else "",
            f"({EFFORT[f['effort']]})" if f.get("effort") in EFFORT else "",
        ] if x)
        findings.append({"id": f"scan_{tag}_{n}", "group": "now", "title": str(f["title"])[:90],
                         "why": why[:400], "priority": urgency, "link": None, "source": "scan"})
    findings.sort(key=lambda f: f["priority"])
    good = [str(g)[:80] for g in (data.get("good") or []) if isinstance(g, str) and g.strip()][:3]
    return {"seen": str(data.get("seen") or "")[:200], "findings": findings, "good": good,
            "next_photo": str(data.get("next_photo") or "")[:160]}
