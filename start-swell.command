#!/bin/bash
# Double-click this file on a Mac to start Swell's server.
# The first time, it sets everything up and asks for your Gemini API key.
cd "$(dirname "$0")" || exit 1
echo "Getting the latest version of Swell..."
git pull --quiet 2>/dev/null || echo "(Could not check for updates. Using the version on this Mac.)"
cd backend || exit 1

if [ ! -d .venv ]; then
  echo "Setting up Swell for the first time (about a minute)..."
  python3 -m venv .venv || { echo "Python 3 is missing. Install it from https://www.python.org/downloads/ and try again."; read -r; exit 1; }
  ./.venv/bin/pip install --quiet -r requirements.txt || { echo "Couldn't install packages. Check your internet and try again."; read -r; exit 1; }
fi

if [ ! -f .env ]; then
  echo ""
  echo "Paste your Gemini API key (from https://aistudio.google.com/apikey) and press Enter."
  echo "It's saved only on this Mac, in backend/.env, which never goes to GitHub."
  read -r -s KEY
  echo "GEMINI_API_KEY=$KEY" > .env
  chmod 600 .env
fi

set -a; . ./.env; set +a
export PORT=5050
echo ""
echo "Swell is running at http://localhost:5050"
echo "Leave this window open while you use the app. Close it to stop the server."
( sleep 2; open "http://localhost:5050" ) &
./.venv/bin/python app.py
