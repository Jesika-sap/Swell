# Swell: get ready for El Niño

A strong El Niño is forecast for winter 2026–27. In California it means storms and floods: the state declared an emergency on Sept 21, 2026, and San Mateo County on Oct 20, 2026. In Nepal and much of South Asia it means drought. Swell turns El Niño into a plan for your home or your farm, wherever you are:

- **Pick who the plan is for:** a home and family, or a farm or ranch.
- **Your risk, from official data.** In the U.S. it checks the FEMA flood map, USGS ground height, live National Weather Service alerts and king tide dates for your exact address, then shows a 0–100 score where every point names its source. Elsewhere it plans for what El Niño brings to that region, like drought in Nepal.
- **A checklist made for you,** in 10 languages including Spanish, Nepali, Chinese and Tagalog. It changes for older adults, people without a car, powered medical devices, pets, renters, hillside homes, crops, animals and farm workers.
- **AI Scan.** Take a photo of your home, yard or farm. AI spots risks it can see and adds them to your checklist.
- **Ask for help.** Request sandbags, a ride, a check-in call, translation or farm help. Local organizations sign up, see requests near them, and say yes. Only the group that accepts sees your exact location and contact.
- **A neighbor map** of storm problems with photos, and **El Niño news** with real sources.

Built by Jesika Sapkota for the 2026 Congressional App Challenge (CA-15).

## Project layout

```
backend/            Python server (Flask): the API, risk engine, checklist rules, AI, database
  app.py            all API routes; also serves the web app
  services/         one file per job: geocode, weather, flood, risk, checklist, resources, news, AI
  data/             hand-checked data: sandbag sites, alert systems, king tides, El Niño status
  schema.sql        database tables
  tests/            26 automated tests with fake outside services
  demo_server.py    runs the app offline with fake data (for demos and tests)
web/                the web app (HTML, CSS, JavaScript), installable on phones
ios/                the iPhone app (Swift, SwiftUI)
docs/               ARCHITECTURE.md and the architecture diagram
render.yaml         one-click hosting on Render (server + PostgreSQL)
```

## Run it on your Mac (3 steps)

**1. Get the code (one time).** Open Terminal and paste:
```
git clone https://github.com/Jesika-sap/Swell ~/Desktop/Swell
```
(If your Mac asks to install developer tools, click Install, then paste the line again.)

**2. Start the server.** In Finder, open Desktop → Swell and double-click **start-swell.command**. The first time, it sets itself up and asks for your Gemini API key (free at https://aistudio.google.com/apikey). Paste it and press Enter. It's saved only on your Mac. The website opens at http://localhost:5050. Leave the Terminal window open.

If your Mac says it can't open the file, right-click it, choose **Open**, then **Open** again.

**3. Open the iPhone app.** Double-click **ios/Swell.xcodeproj**. At the top of Xcode, pick an iPhone simulator, then press **▶** (Cmd+R).

Want to try it with no internet and no key? In Terminal: `cd ~/Desktop/Swell/backend && python3 demo_server.py`, then open http://localhost:5050.

Run the tests:
```
cd backend
python3 -m unittest discover tests -v
```

## Put it online (optional, Render)

Only needed if you want a public link people can open on their own phones.

1. Go to https://render.com and click **Get Started**. Choose **Sign in with GitHub**.
2. Click **New** (top right) → **Blueprint** → pick the **swell** repository. Render reads `render.yaml` and makes the server and a free PostgreSQL database.
3. Render shows a box for `GEMINI_API_KEY`. Paste your key there and click **Apply**. That box is the "secret setting": the key lives on Render's server, never in the code.
4. Wait for the deploy, then open the address Render shows (something like `https://swell.onrender.com`). To use it in the iPhone app, paste that address into `ios/Swell/Config.swift`.

The free plan sleeps after 15 minutes without visitors, so the first visit can take about 30 seconds.

## How it's built

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).
