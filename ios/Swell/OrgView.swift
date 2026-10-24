import SwiftUI
import Security

/// The organization side of Swell: a group signs up once, gets a private key,
/// and then sees help requests near them that match what they offer.
struct OrgView: View {
    @State private var saved = OrgLogin.load()

    var body: some View {
        Group {
            if let saved {
                OrgDashboardView(login: saved) { OrgLogin.clear(); self.saved = nil }
            } else {
                OrgSignupView { self.saved = $0 }
            }
        }
        .navigationTitle(saved == nil ? "For organizations" : "Requests")
        .navigationBarTitleDisplayMode(.inline)
    }
}

// MARK: sign up

struct OrgSignupView: View {
    let done: (OrgLogin) -> Void
    @State private var name = ""
    @State private var about = ""
    @State private var address = ""
    @State private var radius = 25.0
    @State private var picked = Set<String>()
    @State private var email = ""
    @State private var phone = ""
    @State private var website = ""
    @State private var sending = false
    @State private var errorText: String?

    var body: some View {
        Form {
            Section {
                Text("Volunteer groups, nonprofits, mutual aid networks, farm co-ops and city teams can join Swell to see who near them needs help, and say yes.")
                    .font(.subheadline)
            }
            Section("Your group") {
                TextField("Name", text: $name)
                TextField("What you do (one or two sentences)", text: $about, axis: .vertical).lineLimit(2...4)
                TextField("Address or city you work from", text: $address)
                VStack(alignment: .leading) {
                    Text("Help people within \(Int(radius)) miles")
                    Slider(value: $radius, in: 5...100, step: 5)
                }
            }
            Section("What can you help with?") {
                ForEach(services, id: \.id) { s in
                    Toggle(isOn: Binding(get: { picked.contains(s.id) }, set: { if $0 { picked.insert(s.id) } else { picked.remove(s.id) } })) {
                        Label(s.name, systemImage: s.symbol)
                    }
                }
            }
            Section {
                TextField("Email", text: $email).keyboardType(.emailAddress).textInputAutocapitalization(.never)
                TextField("Phone", text: $phone).keyboardType(.phonePad)
                TextField("Website", text: $website).keyboardType(.URL).textInputAutocapitalization(.never)
            } header: { Text("How people can reach you") } footer: {
                Text("New groups show as unverified until the Swell team confirms them.")
            }
            if let errorText { Text(errorText).foregroundStyle(.red) }
            Button(sending ? "Signing up…" : "Sign up my group") { Task { await send() } }
                .bold().disabled(sending)
        }
    }

    private func send() async {
        sending = true
        defer { sending = false }
        do {
            let made = try await APIClient.shared.createOrg([
                "name": name, "about": about, "address": address, "radius_miles": radius,
                "services": Array(picked), "email": email, "phone": phone, "website": website,
            ])
            let login = OrgLogin(id: made.org.id, key: made.key, name: made.org.name)
            login.save()
            done(login)
        } catch {
            errorText = error.localizedDescription
        }
    }
}

// MARK: dashboard

struct OrgDashboardView: View {
    let login: OrgLogin
    let signOut: () -> Void
    @State private var data: OrgDashboard?
    @State private var errorText: String?

    var body: some View {
        List {
            if let d = data {
                Section {
                    VStack(alignment: .leading, spacing: 4) {
                        HStack {
                            Text(d.org.name).font(.headline)
                            if d.org.verified { Image(systemName: "checkmark.seal.fill").foregroundStyle(Theme.sea) }
                        }
                        Text(d.org.verified ? "Verified" : "Waiting to be verified").font(.caption).foregroundStyle(.secondary)
                        Text("\(d.helped) people helped").font(.title3.bold()).foregroundStyle(Theme.sea).padding(.top, 4)
                    }
                }
                let mine = d.requests.filter(\.mine)
                let open = d.requests.filter { !$0.mine }
                Section("You said yes") {
                    if mine.isEmpty { Text("Nothing yet.").foregroundStyle(.secondary) }
                    ForEach(mine) { r in row(r) }
                }
                Section("Open requests near you") {
                    if open.isEmpty { Text("No open requests right now. Pull down to refresh.").foregroundStyle(.secondary) }
                    ForEach(open) { r in row(r) }
                }
            } else if let errorText {
                Text(errorText).foregroundStyle(.red)
            } else {
                ProgressView()
            }
            Section {
                Button("Sign out of this group", role: .destructive, action: signOut)
            } footer: {
                Text("Your group's private key is saved in this iPhone's Keychain.")
            }
        }
        .task { await load() }
        .refreshable { await load() }
    }

    private func row(_ r: OrgRequest) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(r.needLabel).bold()
                Spacer()
                if let a = r.area { Text(a).font(.caption).foregroundStyle(.secondary) }
            }
            if let d = r.details, !d.isEmpty { Text(d).font(.subheadline) }
            if r.mine, let c = r.contact { Text("Contact: \(c)").font(.subheadline.bold()) }
            HStack(spacing: 12) {
                if r.mine {
                    if r.status == "accepted" {
                        Button("Mark done") { Task { await act(r, "done") } }.buttonStyle(.borderedProminent)
                        Button("Can't help after all") { Task { await act(r, "release") } }.buttonStyle(.bordered)
                    }
                } else {
                    Button("I can help") { Task { await act(r, "accept") } }.buttonStyle(.borderedProminent)
                }
            }
            .font(.subheadline)
        }
        .padding(.vertical, 4)
    }

    private func load() async {
        do {
            data = try await APIClient.shared.dashboard(org: login.id, key: login.key)
            errorText = nil
        } catch {
            errorText = error.localizedDescription
        }
    }

    private func act(_ r: OrgRequest, _ action: String) async {
        do {
            try await APIClient.shared.orgAct(org: login.id, key: login.key, request: r.id, action: action)
        } catch {
            errorText = error.localizedDescription
        }
        await load()
    }
}

// MARK: saving the org key safely

struct OrgLogin: Codable {
    let id: String
    let key: String
    let name: String

    private static let account = "swell.org"

    static func load() -> OrgLogin? {
        let q: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrAccount as String: account,
                                kSecReturnData as String: true, kSecMatchLimit as String: kSecMatchLimitOne]
        var out: AnyObject?
        guard SecItemCopyMatching(q as CFDictionary, &out) == errSecSuccess, let data = out as? Data else { return nil }
        return try? JSONDecoder().decode(OrgLogin.self, from: data)
    }

    func save() {
        OrgLogin.clear()
        guard let data = try? JSONEncoder().encode(self) else { return }
        let q: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrAccount as String: OrgLogin.account,
                                kSecValueData as String: data, kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlock]
        SecItemAdd(q as CFDictionary, nil)
    }

    static func clear() {
        let q: [String: Any] = [kSecClass as String: kSecClassGenericPassword, kSecAttrAccount as String: account]
        SecItemDelete(q as CFDictionary)
    }
}
