# Tideline for iPhone (Swift + SwiftUI)

The iPhone app uses the same Python server as the website, so plans, checklist progress and neighbor reports are shared.

Requires a Mac with **Xcode 16 or newer** and runs on **iOS 17+**.

## Set it up in Xcode (about 5 minutes)

1. Open Xcode → **File → New → Project… → iOS → App** → Next.
2. Fill in **Product Name:** `Tideline`, **Interface:** SwiftUI, **Language:** Swift. Leave Storage as None and uncheck tests. Save it inside this `ios` folder.
3. In the left sidebar, **delete** the two files Xcode made: `ContentView.swift` and `TidelineApp.swift`. Choose **Move to Trash**.
4. Drag every `.swift` file from `ios/Tideline/` (in Finder) into the yellow **Tideline** folder in Xcode's sidebar. When asked, check **Copy items if needed** and make sure the **Tideline** target is checked.
5. Open `Config.swift` and set `apiBase` to your Render address, for example `https://tideline.onrender.com`. To use a server running on your own Mac in the Simulator, use `http://localhost:5000`. For that, also add **App Transport Security Settings → Allow Arbitrary Loads = YES** in the target's **Info** tab (only for local testing).
6. Pick an iPhone simulator at the top and press **▶ Run** (Cmd+R).

To run it on your own iPhone, plug it in, choose it at the top, and set **Signing & Capabilities → Team** to your Apple ID.

## Files

| File | What it does |
|---|---|
| `TidelineApp.swift` | App entry point, shared state (`AppStore`), tabs, colors |
| `APIClient.swift` | Every call to the Python server, with the device id |
| `Models.swift` | Swift versions of the server's JSON |
| `OnboardingView.swift` | Language → address → household → "Building your plan" |
| `PlanView.swift` | Risk score ring, alerts, next steps, why this score, forecast, king tides, El Niño status |
| `ChecklistView.swift` | Checklist by section, synced to the server |
| `MapScreen.swift` | Apple Maps with home, sandbag sites and neighbor reports, plus photo reporting with AI labels |
| `HelpView.swift` | County alert sign-up, sandbag sites by distance, county and state resources |
| `NewsView.swift` | El Niño news with sources, and "Around the world" |
