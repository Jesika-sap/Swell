"""Google Gemini, called only from the server so the API key stays secret.

Three uses:
  1. Rewrite a household's checklist in their language (Spanish, Nepali,
     Chinese, Tagalog, Vietnamese...) and add local tips.
  2. Search the web (Google Search grounding) for El Nino news and local help,
     returning the real source links so users can check them.
  3. Look at a photo of a flooded street or clogged drain and label it.

If the first model is busy or retired, we fall back to the next one.
"""
import json
import re
import time

import config
from services.http import get_json, post_json, ServiceError

BASE = "https://generativelanguage.googleapis.com/v1beta/models"
FALLBACK_MODELS = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-2.5-flash-lite"]
AI_TIMEOUT = 90  # seconds; translating a whole checklist can take a while
_good = None     # the last model that answered, tried first next time
_cool_until = 0  # when Google says the free quota is used up, rest instead of asking again and again


def available():
    return bool(config.GEMINI_API_KEY)


_live = None  # models this key can actually use, asked from Google once


def _version(name):
    m = re.search(r"gemini-(\d+(?:\.\d+)?)", name)
    return float(m.group(1)) if m else 0.0


def live_models():
    """Ask Google which Flash models this key can use right now. Google retires
    model names over time; this keeps translation working when that happens."""
    global _live
    if _live is not None:
        return _live
    try:
        data = get_json(f"{BASE}?pageSize=1000", headers={"x-goog-api-key": config.GEMINI_API_KEY})
    except ServiceError:
        return []  # try again next time
    names = []
    for m in data.get("models", []) or []:
        name = (m.get("name") or "").split("/")[-1]
        if "generateContent" not in (m.get("supportedGenerationMethods") or []):
            continue
        if "flash" not in name or re.search(r"image|tts|audio|live|embed|robotics|computer|thinking", name):
            continue
        names.append(name)
    unstable = lambda n: bool(re.search(r"preview|exp", n))
    names.sort(key=lambda n: ("lite" in n, unstable(n), -_version(n), n))
    _live = names[:4]
    return _live


def _models(first=None):
    out = []
    for m in list(first or []) + ([_good] if _good else []) + [config.GEMINI_MODEL] + FALLBACK_MODELS:
        if m not in out:
            out.append(m)
    return out


def generate(parts, *, json_mode=False, temperature=0.3, search=False, models=None):
    """`models` puts stronger models first for one call (AI Scan uses Pro);
    the usual Flash models stay behind them as a fallback."""
    """Returns (text, grounding_metadata)."""
    if not available():
        raise ServiceError("AI is not set up on this server")
    body = {"contents": [{"role": "user", "parts": parts}],
            "generationConfig": {"temperature": temperature}}
    if json_mode and not search:  # Gemini can't force JSON while searching
        body["generationConfig"]["responseMimeType"] = "application/json"
    if search:
        body["tools"] = [{"google_search": {}}]
    headers = {"x-goog-api-key": config.GEMINI_API_KEY}
    global _cool_until
    if time.time() < _cool_until:
        raise ServiceError("Gemini's free limit is used up for now (Google answered 429). Swell will try again in a few minutes.")
    last, tried = None, []

    def attempt(model):
        nonlocal last
        global _good
        tried.append(model)
        try:
            data = post_json(f"{BASE}/{model}:generateContent", body, headers, timeout=AI_TIMEOUT)
        except ServiceError as e:
            last = e
            if "404" not in str(e):
                print(f"[Swell] {model}: {e}", flush=True)
            if model == _good:
                _good = None
            return None
        cand = (data.get("candidates") or [{}])[0]
        text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
        if text.strip():
            _good = model
            return text, cand.get("groundingMetadata") or {}
        last = ServiceError("AI returned an empty answer")
        print(f"[Swell] {model}: empty answer", flush=True)
        return None

    for model in _models(models):
        got = attempt(model)
        if got:
            return got
    # Every name we know failed (often because Google retired it): use what Google lists today.
    for model in live_models():
        if model not in tried:
            got = attempt(model)
            if got:
                return got
    if last and "429" in str(last):
        _cool_until = time.time() + 300
        print("[Swell] Gemini's free limit is used up for now (429 from every model). Resting 5 minutes. "
              "Screen text still shows in your language from Swell's built-in translations.", flush=True)
    if last and tried:
        last = ServiceError(f"{last} (tried {', '.join(tried)})")
    raise last or ServiceError("AI unavailable")


def parse_json(text):
    """Models sometimes wrap JSON in ```fences``` or add a sentence. Recover it."""
    try:
        return json.loads(text)
    except ValueError:
        pass
    m = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if m:
        try:
            return json.loads(m.group(1))
        except ValueError:
            pass
    a, b = text.find("{"), text.rfind("}")
    if a >= 0 and b > a:
        return json.loads(text[a:b + 1])
    raise ServiceError("AI answer wasn't readable")


def sources(meta):
    """Real links Google Search used, from the grounding metadata."""
    seen, out = set(), []
    for ch in meta.get("groundingChunks", []) or []:
        web = ch.get("web") or {}
        uri, title = web.get("uri"), web.get("title") or ""
        if uri and title not in seen:
            seen.add(title)
            out.append({"title": title or uri, "url": uri})
    return out
