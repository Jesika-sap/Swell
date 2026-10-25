"""If Google retires every model name Swell knows, Swell should ask Google
which models exist and use one of those instead."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config  # noqa: E402
from services import gemini, http  # noqa: E402


class RetiredModels(unittest.TestCase):
    def setUp(self):
        self.calls = []
        gemini._live = None
        gemini._good = None
        self.old_key, config.GEMINI_API_KEY = config.GEMINI_API_KEY, "AIzaTEST"

        def fake(method, url, **kw):
            self.calls.append(url)
            if method == "GET" and url.endswith("/models?pageSize=1000"):
                return 200, {"models": [
                    {"name": "models/gemini-3.5-flash", "supportedGenerationMethods": ["generateContent"]},
                    {"name": "models/gemini-3.5-flash-lite", "supportedGenerationMethods": ["generateContent"]},
                    {"name": "models/gemini-3.5-flash-image", "supportedGenerationMethods": ["generateContent"]},
                    {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
                ]}
            if "gemini-3.5-flash:generateContent" in url:
                return 200, {"candidates": [{"content": {"parts": [{"text": "नमस्ते"}]}}]}
            return 404, {}
        self.old_fake, http.fake = http.fake, fake

    def tearDown(self):
        http.fake = self.old_fake
        config.GEMINI_API_KEY = self.old_key
        gemini._live = None
        gemini._good = None

    def test_uses_a_model_google_still_lists(self):
        text, _ = gemini.generate([{"text": "hi"}])
        self.assertEqual(text, "नमस्ते")
        self.assertEqual(gemini.live_models()[:2], ["gemini-3.5-flash", "gemini-3.5-flash-lite"])
        self.assertNotIn("gemini-3.5-flash-image", gemini.live_models())


class TooManyRequests(unittest.TestCase):
    def test_rests_after_quota_is_used_up(self):
        calls = []

        def fake(method, url, **kw):
            calls.append(url)
            return 429, {}
        old_fake, http.fake = http.fake, fake
        old_key, config.GEMINI_API_KEY = config.GEMINI_API_KEY, "AIzaTEST"
        gemini._good, gemini._live, gemini._cool_until = None, [], 0
        try:
            with self.assertRaises(http.ServiceError):
                gemini.generate([{"text": "hi"}])
            n = len(calls)
            with self.assertRaises(http.ServiceError):
                gemini.generate([{"text": "hi"}])
            self.assertEqual(len(calls), n)  # resting: no new calls to Google
        finally:
            http.fake, config.GEMINI_API_KEY = old_fake, old_key
            gemini._cool_until, gemini._live = 0, None


if __name__ == "__main__":
    unittest.main()
