# Swell for iPhone (Swift + SwiftUI)

The iPhone app uses the same Python server as the website, so plans, checklist progress and neighbor reports are shared.

Requires a Mac with **Xcode 16 or newer** and runs on **iOS 17+**.

## Open it in Xcode

1. Start the server first: double-click **start-swell.command** in the main Swell folder.
2. Double-click **Swell.xcodeproj** in this folder.
3. Pick an iPhone simulator at the top (for example iPhone 16) and press **▶** (Cmd+R).

The project already includes every Swift file and lets the app talk to the server on your Mac (`Swell-Info.plist`). To run it on your own iPhone, plug it in, choose it at the top, and set **Signing & Capabilities → Team** to your Apple ID.

**Tip for the demo video:** drag a photo from Finder onto the Simulator to add it to Photos, so you can use it in AI Scan.

If you put the server online later, change `apiBase` in `Config.swift` to that address.

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
