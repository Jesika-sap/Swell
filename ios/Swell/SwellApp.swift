import SwiftUI
import Observation

@main
struct SwellApp: App {
    @State private var store = AppStore()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(store)
                .tint(Theme.sea)
        }
    }
}

/// App-wide state: the plan on screen and the user's language.
@MainActor
@Observable
final class AppStore {
    var plan: Plan?
    var error: String?
    var addingPlace = false
    var account: Account?
    private(set) var language: String = UserDefaults.standard.string(forKey: "swell.lang") ?? "en"
    private(set) var currentId: String? = UserDefaults.standard.string(forKey: "swell.current")

    var isLoadingSaved: Bool { currentId != nil && plan == nil && error == nil }

    func setLanguage(_ code: String) {
        language = code
        UserDefaults.standard.set(code, forKey: "swell.lang")
    }

    private func setCurrent(_ id: String?) {
        currentId = id
        UserDefaults.standard.set(id, forKey: "swell.current")
    }

    func loadSaved() async {
        guard let id = currentId else { return }
        do {
            plan = try await APIClient.shared.plan(id)
            error = nil
        } catch {
            if error.localizedDescription.lowercased().contains("not found") { setCurrent(nil) }
            self.error = error.localizedDescription
        }
    }

    func open(_ id: String) async {
        setCurrent(id)
        plan = nil
        error = nil
        await loadSaved()
    }

    func build(address: String, label: String, household: Set<Household>,
               role: Role, grows: Set<FarmGrow>, workers: Bool, creek: Bool) async throws {
        let p = try await APIClient.shared.buildPlan(address: address, label: label, language: language, household: household,
                                                     role: role, grows: grows, workers: workers, creek: creek)
        plan = p
        setCurrent(p.id)
        addingPlace = false
        error = nil
    }

    /// Log in or sign up. Logging in switches this phone to the account's id and opens its first plan.
    func signIn(name: String?, email: String, password: String) async throws {
        if let name {
            account = try await APIClient.shared.signup(name: name, email: email, password: password).account
        } else {
            let r = try await APIClient.shared.login(email: email, password: password)
            if let id = r.deviceId { APIClient.shared.useDevice(id) }
            account = r.account
            let plans = try await APIClient.shared.plans()
            if let first = plans.first, !plans.contains(where: { $0.id == currentId }) { await open(first.id) }
        }
    }

    func signOut() {
        APIClient.shared.useDevice(UUID().uuidString)
        account = nil
        setCurrent(nil)
        plan = nil
    }

    func refreshAccount() async {
        account = try? await APIClient.shared.account().account
    }

    /// AI Scan: send a photo, get new tasks added to the top of the checklist.
    func scan(photo: String) async throws -> ScanResult {
        guard let p = plan else { throw APIError(message: "Make a plan first") }
        let result = try await APIClient.shared.scan(plan: p.id, photo: photo)
        plan = result.plan
        return result
    }

    /// Check a task off right away, then save it on the server (and undo if that fails).
    func toggle(_ task: PlanTask) async {
        guard var p = plan, let i = p.checklist.firstIndex(where: { $0.id == task.id }) else { return }
        let newValue = !(p.checklist[i].done ?? false)
        p.checklist[i].done = newValue
        p.progress.done += newValue ? 1 : -1
        plan = p
        do {
            try await APIClient.shared.setDone(plan: p.id, item: task.id, done: newValue)
        } catch {
            p.checklist[i].done = !newValue
            p.progress.done += newValue ? -1 : 1
            plan = p
            self.error = "Couldn't save that. Check your connection."
        }
    }
}

struct RootView: View {
    @Environment(AppStore.self) private var store

    var body: some View {
        Group {
            if store.isLoadingSaved {
                ProgressView("Loading your plan…")
            } else if store.plan == nil || store.addingPlace {
                OnboardingView()
            } else {
                MainTabs()
            }
        }
        .task { await store.loadSaved() }
    }
}

struct MainTabs: View {
    var body: some View {
        TabView {
            NavigationStack { PlanView() }
                .tabItem { Label("My plan", systemImage: "shield.lefthalf.filled") }
            NavigationStack { ChecklistView() }
                .tabItem { Label("Checklist", systemImage: "checklist") }
            NavigationStack { CommunityView() }
                .tabItem { Label("Community", systemImage: "person.3") }
            NavigationStack { HelpView() }
                .tabItem { Label("Help", systemImage: "lifepreserver") }
            NavigationStack { NewsView() }
                .tabItem { Label("News", systemImage: "newspaper") }
        }
    }
}

enum Theme {
    static let ocean = Color(red: 11 / 255, green: 51 / 255, blue: 73 / 255)
    static let ocean2 = Color(red: 18 / 255, green: 80 / 255, blue: 110 / 255)
    static let sea = Color(red: 14 / 255, green: 116 / 255, blue: 134 / 255)

    static func level(_ level: String) -> Color {
        switch level {
        case "high": return Color(red: 1, green: 0.54, blue: 0.45)
        case "elevated": return Color(red: 1, green: 0.75, blue: 0.38)
        default: return Color(red: 0.39, green: 0.84, blue: 0.61)
        }
    }

    static func levelText(_ level: String) -> String {
        switch level {
        case "high": return "High risk"
        case "elevated": return "Elevated risk"
        default: return "Lower risk"
        }
    }
}
