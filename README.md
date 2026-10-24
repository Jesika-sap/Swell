# Tideline: get ready for El Niño

A strong El Niño is forecast for winter 2026–27. California declared a state of emergency on Sept 21, 2026, and San Mateo County declared a local emergency on Oct 20, 2026. Tideline helps any household get ready:

- **Your storm risk, from official data.** It checks the FEMA flood map, USGS ground elevation, live National Weather Service alerts and king tide dates for your exact address, then shows a 0–100 score where every point names its source.
- **A checklist made for your household,** in 10 languages including Spanish, Nepali, Chinese and Tagalog. It changes for older adults, people without a car, powered medical devices, pets, renters and hillside homes.
- **Help nearby.** The closest sandbag sites, your county's alert system, shelters and 211.
- **A neighbor map.** Report flooding or a clogged drain with a photo, and AI labels it.
- **El Niño news** for your area with real sources, plus how El Niño affects other parts of the world.

Built by Jesika Sapkota for the 2026 Congressional App Challenge (CA-15).

## Project layout

```
backend/            Python server (Flask): the API, risk engine, checklist rules, AI, database
  app.py            all API routes; also serves the web app
  services/         one file per job: geocode, weather, flood, risk, checklist, resources, news, AI
  data/             hand-checked data: sandbag sites, alert systems, king tides, El Niño status
  schema.sql        database tables
  tests/            20 automated tests with fake outside services
  demo_server.py    runs the app offline with fake data (for demos and tests)
web/                the web app (HTML, CSS, JavaScript), installable on phones
ios/                the iPhone app (Swift, SwiftUI)
docs/               ARCHITECTURE.md and the architecture diagram
render.yaml         one-click hosting on Render (server + PostgreSQL)
```

## Run it on your computer (VS Code)

1. In VS Code, open the Command Palette (Cmd+Shift+P) → **Git: Clone** → paste this repository's link → choose a folder → **Open**.
2. Open the terminal in VS Code (Ctrl+`) and run:
   ```
   cd backend
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Add your Gemini key (free from https://aistudio.google.com/apikey). Run this in the same terminal:
   ```
   export GEMINI_API_KEY=your-key-here
   python app.py
   ```
4. Open http://localhost:5000.

Want to try it with no internet and no key? Run `python demo_server.py` and open http://localhost:5050.

Run the tests:
```
cd backend
python -m unittest discover tests -v
```

## Put it online (Render)

1. Sign in to https://render.com with GitHub.
2. Click **New → Blueprint** and pick this repository. Render reads `render.yaml` and creates the server and the PostgreSQL database.
3. When it asks for `GEMINI_API_KEY`, paste your key.
4. Wait for the deploy, then open the address Render shows (something like `https://tideline.onrender.com`).

The free plan sleeps after 15 minutes without visitors, so the first visit can take about 30 seconds. Open it a minute before recording or presenting.

## How it's built

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
