# Swell for iPhone (Swift + SwiftUI)

The iPhone app uses the same Python server as the website, so plans, checklist progress and neighbor reports are shared.

Requires a Mac with **Xcode 16 or newer** and runs on **iOS 17+**.

## Set it up in Xcode (about 5 minutes)

1. Open Xcode → **File → New → Project… → iOS → App** → Next.
2. Fill in **Product Name:** `Swell`, **Interface:** SwiftUI, **Language:** Swift. Leave Storage as None and uncheck tests. Save it inside this `ios` folder.
3. In the left sidebar, **delete** the two files Xcode made: `ContentView.swift` and `SwellApp.swift`. Choose **Move to Trash**.
4. Drag every `.swift` file from `ios/Swell/` (in Finder) into the yellow **Swell** folder in Xcode's sidebar. When asked, check **Copy items if needed** and make sure the **Swell** target is checked.
5. Let the app talk to the server on your Mac: click the blue **Swell** project at the top of the sidebar → the **Swell** target → **Info** tab. Hover over any row, click **+**, type `App Transport Security Settings`, and press Enter. Click its arrow, click **+** inside it, choose **Allow Arbitrary Loads**, and set it to **YES**. (Only needed while the server runs on your Mac at `http://localhost:5050`, which is what `Config.swift` uses.)
6. Start the server in Terminal (see the main README, "Run it on your Mac").
7. Pick an iPhone simulator at the top (for example iPhone 16) and press **▶ Run** (Cmd+R).

If you put the server online later, change `apiBase` in `Config.swift` to that address.

**Tip for the demo video:** in the Simulator, drag a photo from Finder onto the phone to add it to Photos, so you can use it in AI Scan.

To run it on your own iPhone, plug it in, choose it at the top, and set **Signing & Capabilities → Team** to your Apple ID.

## Files

| File | What it does |
|---|---|
| `SwellApp.swift` | App entry point, shared state (`AppStore`), tabs, colors |
| `APIClient.swift` | Every call to the Python server, with the device id |
| `Models.swift` | Swift versions of the server's JSON |
| `OnboardingView.swift` | Language → home or farm → address → farm details → household → "Building your plan" |
| `PlanView.swift` | Risk score ring, what El Niño means in this region, AI Scan, alerts, next steps, why this score, forecast, king tides |
| `ChecklistView.swift` | Checklist by section, synced to the server |
| `MapScreen.swift` | Apple Maps with home, sandbag sites and neighbor reports, plus photo reporting with AI labels |
| `HelpView.swift` | Ask for help, your requests and who accepted them, groups near you, alert sign-up, sandbag sites, official resources |
| `OrgView.swift` | For organizations: sign up, then accept and finish help requests. The group's key is saved in the Keychain |
| `NewsView.swift` | El Niño news with sources, and "Around the world" |
