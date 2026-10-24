"""Runs the API with fake outside services (the same ones the tests use),
so the app can be demoed or tested with no internet and no API keys.
    python demo_server.py   ->  http://localhost:5050
"""
import os
import sys
import tempfile

os.environ.setdefault("SQLITE_PATH", os.path.join(tempfile.mkdtemp(), "demo.db"))
os.environ.setdefault("GEMINI_API_KEY", "demo")
sys.path.insert(0, os.path.dirname(__file__))
from services import http  # noqa: E402
from tests import fakes  # noqa: E402

http.fake = fakes.fake
import app  # noqa: E402

if __name__ == "__main__":
    app.app.run(port=int(os.environ.get("PORT", 5050)), threaded=True)
