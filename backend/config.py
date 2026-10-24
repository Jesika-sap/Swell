"""App settings, read from environment variables.

Secrets (the Gemini API key, the database password) live only on the server,
never in the browser or the iPhone app. On Render they are set in the
dashboard; locally they can go in a .env file that git ignores.
"""
import os

APP_NAME = os.environ.get("APP_NAME", "Swell")

# Google Gemini (AI): one key, used only by this server.
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")

# Database: Postgres in production (DATABASE_URL from Render), SQLite file locally.
DATABASE_URL = os.environ.get("DATABASE_URL", "")
SQLITE_PATH = os.environ.get("SQLITE_PATH", os.path.join(os.path.dirname(__file__), "local.db"))

# Which websites may call this API from a browser (comma separated). "*" allows all.
ALLOWED_ORIGINS = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",") if o.strip()]

# The National Weather Service asks every app to identify itself.
USER_AGENT = os.environ.get("USER_AGENT", f"{APP_NAME} El Nino readiness app (student project; contact via GitHub)")

# How long to reuse answers from outside services, in seconds.
CACHE_TTL = {
    "geocode": 30 * 86400,
    "flood": 30 * 86400,
    "elevation": 30 * 86400,
    "points": 7 * 86400,
    "alerts": 5 * 60,
    "forecast": 60 * 60,
    "news": 6 * 3600,
    "aihelp": 3 * 86400,
}

# Secret for the app owner to mark organizations as verified (set on Render).
ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "")

HTTP_TIMEOUT = float(os.environ.get("HTTP_TIMEOUT", "12"))
MAX_PHOTO_BYTES = 700_000  # after the app compresses it
