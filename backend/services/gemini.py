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

import config
from services.http import post_json, ServiceError

BASE = "https://generativelanguage.googleapis.com/v1beta/models"
FALLBACK_MODELS = ["gemini-flash-latest", "gemini-2.5-flash", "gemini-2.5-flash-lite"]


def available():
    return bool(config.GEMINI_API_KEY)


def _models():
    out = [config.GEMINI_MODEL] + [m for m in FALLBACK_MODELS if m != config.GEMINI_MODEL]
    return out


def generate(parts, *, json_mode=False, temperature=0.3, search=False):
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
    last = None
    for model in _models():
        try:
            data = post_json(f"{BASE}/{model}:generateContent", body, headers)
        except ServiceError as e:
            last = e
            continue
        cand = (data.get("candidates") or [{}])[0]
        text = "".join(p.get("text", "") for p in cand.get("content", {}).get("parts", []))
        if text.strip():
            return text, cand.get("groundingMetadata") or {}
        last = ServiceError("AI returned an empty answer")
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
