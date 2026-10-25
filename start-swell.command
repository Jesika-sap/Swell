#!/bin/bash
# Double-click this file on a Mac (or run ./start-swell.command) to start Swell's server.
# The first time, it sets everything up and asks for your Gemini API key.
# To change the key later, run:  ./start-swell.command --new-key
cd "$(dirname "$0")" || exit 1
echo "Getting the latest version of Swell..."
git pull --quiet 2>/dev/null || echo "(Could not check for updates. Using the version on this Mac.)"
cd backend || exit 1

if [ ! -d .venv ]; then
  echo "Setting up Swell for the first time (about a minute)..."
  python3 -m venv .venv || { echo "Python 3 is missing. Install it from https://www.python.org/downloads/ and try again."; read -r; exit 1; }
fi
./.venv/bin/pip install --quiet --disable-pip-version-check -r requirements.txt || { echo "Couldn't install packages. Check your internet and try again."; read -r; exit 1; }

[ "$1" = "--new-key" ] && rm -f .env

# Load the saved key, if there is one.
GEMINI_API_KEY=""
[ -f .env ] && GEMINI_API_KEY="$(grep -m1 '^GEMINI_API_KEY=' .env | cut -d= -f2- | tr -d "[:space:]'\"")"

# Ask until we get a key that isn't empty.
while [ -z "$GEMINI_API_KEY" ]; do
  echo ""
  echo "Paste your Gemini API key (from https://aistudio.google.com/apikey) and press Enter."
  echo "Nothing shows while you paste. That's normal. Type 'skip' to run without AI."
  read -r -s KEY
  KEY="$(echo "$KEY" | tr -d "[:space:]'\"")"
  if [ "$KEY" = "skip" ]; then break; fi
  if [ -z "$KEY" ]; then echo "That was empty. Copy the key again and paste it with Cmd+V."; continue; fi
  echo "GEMINI_API_KEY=$KEY" > .env
  chmod 600 .env
  GEMINI_API_KEY="$KEY"
done
export GEMINI_API_KEY

# Check the key with Google before starting.
if [ -n "$GEMINI_API_KEY" ]; then
  RESP=$(curl -s -w "\n%{http_code}" -H "x-goog-api-key: $GEMINI_API_KEY" \
    "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1")
  CODE="$(echo "$RESP" | tail -n1)"
  if [ "$CODE" = "200" ]; then
    echo "AI is ON (Gemini key works, ends in ...${GEMINI_API_KEY: -4})."
  else
    echo ""
    echo "Google didn't accept that Gemini key (error $CODE). Swell will run, but AI Scan and translation won't work."
    MSG="$(echo "$RESP" | grep -m1 '"message"' | sed 's/.*"message": *"//; s/",* *$//')"
    [ -n "$MSG" ] && echo "Google says: $MSG"
    case "$GEMINI_API_KEY" in AIza*) ;; *) echo "Note: Gemini keys start with AIza. The one saved here starts with ${GEMINI_API_KEY:0:4}, so it may not be the key.";; esac
    echo "Saved key is ${#GEMINI_API_KEY} characters long (a real one is 39)."
    echo "To fix it: copy the key again from aistudio.google.com/apikey, then run:  ./start-swell.command --new-key"
  fi
else
  echo "AI is OFF. To turn it on, run:  ./start-swell.command --new-key"
fi

export PORT=5050
echo ""
echo "Swell is running at http://localhost:5050"
echo "Leave this window open while you use the app. Press Control+C to stop."
( sleep 2; open "http://localhost:5050" ) &
./.venv/bin/python app.py
