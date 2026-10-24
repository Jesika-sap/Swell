import SwiftUI
import UIKit
import MapKit

/// Communities: your county, your city, and private family groups (up to 5 people).
/// Inside one you see storm reports from that area. You need an account to join.
struct CommunityView: View {
    @Environment(AppStore.self) private var store
    @State private var list: CommunityList?
    @State private var errorText: String?
    @State private var accountMode: AccountMode?
    @State private var showNewFamily = false
    @State private var showJoinCode = false
    @State private var reporting = false
    @State private var confirmLogout = false

    var body: some View {
        List {
            if let list {
                if list.account == nil {
                    signedOut
                } else {
                    signedIn(list)
                }
            } else if let errorText {
                Text(errorText).foregroundStyle(.secondary)
            } else {
                ProgressView()
            }
        }
        .navigationTitle("Community")
        .navigationDestination(for: CommunitySummary.self) { c in CommunityDetailView(summary: c) }
        .task { await load() }
        .refreshable { await load() }
        .sheet(item: $accountMode, onDismiss: { Task { await load() } }) { mode in AccountSheet(mode: mode) }
        .sheet(isPresented: $showNewFamily, onDismiss: { Task { await load() } }) { NewFamilySheet(max: list?.familyMax ?? 5) }
        .sheet(isPresented: $showJoinCode, onDismiss: { Task { await load() } }) { JoinCodeSheet() }
        .sheet(isPresented: $reporting) {
            if let plan = store.plan {
                ReportSheet(lat: plan.lat, lon: plan.lon, county: plan.place.county)
            }
        }
        .confirmationDialog("Log out?", isPresented: $confirmLogout, titleVisibility: .visible) {
            Button("Log out", role: .destructive) { store.signOut() }
        } message: {
            Text("Your plans and communities stay in your account. Log in again on any device to get them back.")
        }
    }

    private var signedOut: some View {
        Section {
            VStack(alignment: .leading, spacing: 10) {
                Text("Join your county and your city to see storm reports from people near you, and start a private group to check on your family.")
                    .foregroundStyle(.secondary)
                Button { accountMode = .signup } label: { Text("Create a free account").bold().frame(maxWidth: .infinity) }
                    .buttonStyle(.borderedProminent).controlSize(.large)
                Button { accountMode = .login } label: { Text("Log in").frame(maxWidth: .infinity) }
                    .buttonStyle(.bordered).controlSize(.large)
                Text("Your plans on this phone come with you.").font(.caption).foregroundStyle(.secondary)
            }
            .padding(.vertical, 6)
        }
    }

    @ViewBuilder
    private func signedIn(_ list: CommunityList) -> some View {
        Section {
            HStack {
                Text("Signed in as **\(list.account?.name ?? "")**").font(.subheadline)
                Spacer()
                Button("Log out") { confirmLogout = true }.font(.subheadline)
            }
        }
        Section("Your communities") {
            if list.mine.isEmpty {
                Text("You haven’t joined any yet. Join your county or city below.").foregroundStyle(.secondary)
            }
            ForEach(list.mine) { c in
                NavigationLink(value: c) { CommunityRow(kind: c.kind, name: c.name, detail: "\(CommunityKind.label(c.kind)) · \(c.members) \(c.members == 1 ? "member" : "members")") }
            }
        }
        if !list.suggested.isEmpty {
            Section("Join near your places") {
                ForEach(list.suggested) { s in
                    HStack {
                        CommunityRow(kind: s.kind, name: s.name, detail: CommunityKind.label(s.kind))
                        Spacer()
                        Button("Join") { Task { await join(s.key) } }
                            .buttonStyle(.borderedProminent).controlSize(.small).clipShape(Capsule())
                    }
                }
            }
        }
        Section {
            VStack(alignment: .leading, spacing: 10) {
                Text("Family group").font(.headline)
                Text("A private group for up to \(list.familyMax) people. See each other’s places and checklist progress, and tap “I’m safe” after a storm.")
                    .font(.subheadline).foregroundStyle(.secondary)
                HStack {
                    Button { showNewFamily = true } label: { Text("Start a group").frame(maxWidth: .infinity) }
                        .buttonStyle(.borderedProminent)
                    Button { showJoinCode = true } label: { Text("Join with a code").frame(maxWidth: .infinity) }
                        .buttonStyle(.bordered)
                }
            }
            .padding(.vertical, 6)
        }
        Section {
            Button { reporting = true } label: { Label("Report a storm problem", systemImage: "camera") }
        }
        if let errorText { Text(errorText).foregroundStyle(.red) }
    }

    private func load() async {
        do {
            list = try await APIClient.shared.communities()
            store.account = list?.account
            errorText = nil
        } catch {
            errorText = error.localizedDescription
        }
    }

    private func join(_ key: String) async {
        do {
            _ = try await APIClient.shared.joinCommunity(key: key)
            await load()
        } catch {
            errorText = error.localizedDescription
        }
    }
}

struct CommunityRow: View {
    let kind: String
    let name: String
    let detail: String

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: CommunityKind.symbol(kind))
                .foregroundStyle(kind == "family" ? Color.orange : Theme.sea)
                .frame(width: 36, height: 36)
                .background((kind == "family" ? Color.orange : Theme.sea).opacity(0.12), in: RoundedRectangle(cornerRadius: 10))
            VStack(alignment: .leading, spacing: 2) {
                Text(name).bold()
                Text(detail).font(.caption).foregroundStyle(.secondary)
            }
        }
    }
}

struct CommunityDetailView: View {
    let summary: CommunitySummary
    @Environment(AppStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var detail: CommunityDetail?
    @State private var errorText: String?
    @State private var selected: StormReport?
    @State private var reporting = false

    var body: some View {
        List {
            if let d = detail {
                Section {
                    CommunityMap(detail: d, home: store.plan) { selected = $0 }
                        .frame(height: 230)
                        .listRowInsets(EdgeInsets())
                }
                if d.kind == "family" { familySection(d) }
                Section {
                    if d.reports.isEmpty {
                        Text(d.kind == "family"
                             ? "No storm reports near your family’s places right now."
                             : "No storm reports here right now. If you see flooding, a clogged drain or a fallen tree, report it so your neighbors know.")
                            .foregroundStyle(.secondary)
                    }
                    ForEach(d.reports) { r in
                        Button { selected = r } label: { reportRow(r) }.buttonStyle(.plain)
                    }
                } header: {
                    HStack {
                        Text("Storm reports")
                        Spacer()
                        Button("+ Report") { reporting = true }.font(.subheadline.bold()).textCase(nil)
                    }
                }
                Section {
                    Button(d.kind == "family" ? "Leave this group" : "Leave this community", role: .destructive) {
                        Task {
                            try? await APIClient.shared.leaveCommunity(d.id)
                            dismiss()
                        }
                    }
                }
            } else if let errorText {
                Text(errorText).foregroundStyle(.secondary)
            } else {
                ProgressView()
            }
        }
        .navigationTitle(summary.name)
        .task { await load() }
        .refreshable { await load() }
        .sheet(item: $selected, onDismiss: { Task { await load() } }) { r in ReportDetail(report: r).presentationDetents([.medium]) }
        .sheet(isPresented: $reporting, onDismiss: { Task { await load() } }) {
            if let plan = store.plan {
                ReportSheet(lat: plan.lat, lon: plan.lon, county: plan.place.county)
            }
        }
    }

    @ViewBuilder
    private func familySection(_ d: CommunityDetail) -> some View {
        Section("Members · \(d.members) of \(d.maxMembers ?? 5)") {
            ForEach(d.people ?? []) { p in
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text(String(p.name.prefix(1)).uppercased()).bold().foregroundStyle(.white)
                            .frame(width: 32, height: 32).background(Theme.ocean, in: Circle())
                        VStack(alignment: .leading, spacing: 2) {
                            Text(p.you ? "\(p.name) (you)" : p.name).bold()
                            if let safe = p.safeAt {
                                Text("Safe · checked in \(Self.when(safe))").font(.caption.bold()).foregroundStyle(.green)
                            } else {
                                Text("No check-in yet").font(.caption).foregroundStyle(.secondary)
                            }
                        }
                    }
                    ForEach(p.places, id: \.self) { pl in
                        HStack(spacing: 6) {
                            Circle().fill(Theme.level(pl.level)).frame(width: 8, height: 8)
                            Text("\(pl.label ?? "Home")\(pl.city.map { ", \($0)" } ?? "") · \(pl.done)/\(pl.total) done")
                                .font(.caption)
                        }
                    }
                }
                .padding(.vertical, 4)
            }
            Button {
                Task {
                    if let d2 = try? await APIClient.shared.markSafe(d.id) { detail = d2 }
                }
            } label: { Label("I’m safe", systemImage: "checkmark.shield").bold().frame(maxWidth: .infinity) }
                .buttonStyle(.borderedProminent).controlSize(.large)
            if let code = d.inviteCode, d.members < (d.maxMembers ?? 5) {
                HStack {
                    Text("Invite code").font(.caption).foregroundStyle(.secondary)
                    Text(code).font(.title3.monospaced().bold())
                    Spacer()
                    Button("Copy") { UIPasteboard.general.string = code }
                }
                Text("Send this code to family. They create an account and tap “Join with a code.”")
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
    }

    private func reportRow(_ r: StormReport) -> some View {
        HStack(spacing: 12) {
            Circle().fill(r.severity >= 3 ? Color.red : r.severity == 2 ? Color.orange : Color.green).frame(width: 12, height: 12)
            VStack(alignment: .leading, spacing: 2) {
                Text(r.title).bold()
                Text([r.kindLabel, Self.when(r.createdAt), r.confirmations > 0 ? "\(r.confirmations) confirmed" : nil]
                        .compactMap { $0 }.joined(separator: " · "))
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
        .contentShape(Rectangle())
    }

    private func load() async {
        do {
            detail = try await APIClient.shared.community(summary.id)
        } catch {
            errorText = error.localizedDescription
        }
    }

    static func when(_ iso: String) -> String {
        let f = ISO8601DateFormatter()
        guard let d = f.date(from: iso) else { return iso }
        return d.formatted(.dateTime.month(.abbreviated).day().hour().minute())
    }
}

enum AccountMode: String, Identifiable {
    case signup, login
    var id: String { rawValue }
}

struct AccountSheet: View {
    let mode: AccountMode
    @Environment(AppStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var email = ""
    @State private var password = ""
    @State private var working = false
    @State private var errorText: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    if mode == .signup {
                        TextField("First name", text: $name).textContentType(.givenName)
                    }
                    TextField("Email", text: $email)
                        .textContentType(.emailAddress).keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never).autocorrectionDisabled()
                    SecureField("Password", text: $password)
                        .textContentType(mode == .signup ? .newPassword : .password)
                } footer: {
                    Text(mode == .signup
                         ? "At least 8 characters. We store only a scrambled version of your password. Plans on this phone move into your account."
                         : "Plans you made on this phone move into your account.")
                }
                if let errorText { Text(errorText).foregroundStyle(.red) }
                Button {
                    Task { await submit() }
                } label: {
                    if working { ProgressView() } else { Text(mode == .signup ? "Create account" : "Log in").bold() }
                }
                .disabled(working)
            }
            .navigationTitle(mode == .signup ? "Create your account" : "Log in")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } } }
        }
    }

    private func submit() async {
        working = true
        defer { working = false }
        do {
            try await store.signIn(name: mode == .signup ? name.trimmingCharacters(in: .whitespaces) : nil,
                                   email: email.trimmingCharacters(in: .whitespaces), password: password)
            dismiss()
        } catch {
            errorText = error.localizedDescription
        }
    }
}

struct NewFamilySheet: View {
    let max: Int
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var errorText: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Group name, e.g. Sapkota family", text: $name)
                } footer: { Text("Up to \(max) people. You’ll get a code to share with them.") }
                if let errorText { Text(errorText).foregroundStyle(.red) }
                Button("Create group") {
                    Task {
                        do { _ = try await APIClient.shared.createFamily(name: name); dismiss() } catch { errorText = error.localizedDescription }
                    }
                }.bold()
            }
            .navigationTitle("Start a family group")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } } }
        }
    }
}

struct JoinCodeSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var code = ""
    @State private var errorText: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Invite code, e.g. K7Q2MX", text: $code)
                        .textInputAutocapitalization(.characters).autocorrectionDisabled()
                } footer: { Text("Ask the person who made the group for its 6-letter code.") }
                if let errorText { Text(errorText).foregroundStyle(.red) }
                Button("Join") {
                    Task {
                        do { _ = try await APIClient.shared.joinFamily(code: code); dismiss() } catch { errorText = error.localizedDescription }
                    }
                }.bold()
            }
            .navigationTitle("Join a family group")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } } }
        }
    }
}


/// A map of just this community: its storm reports, plus your family's places for family groups.
struct CommunityMap: View {
    let detail: CommunityDetail
    let home: Plan?
    let onSelect: (StormReport) -> Void

    private var region: MKCoordinateRegion {
        var pts: [CLLocationCoordinate2D] = detail.reports.map { .init(latitude: $0.lat, longitude: $0.lon) }
        pts += (detail.places ?? []).map { .init(latitude: $0.lat, longitude: $0.lon) }
        if let c = detail.center { pts.append(.init(latitude: c.lat, longitude: c.lon)) }
        if pts.isEmpty, let home { pts.append(.init(latitude: home.lat, longitude: home.lon)) }
        guard let first = pts.first else {
            return MKCoordinateRegion(center: .init(latitude: 37.56, longitude: -122.32), latitudinalMeters: 20000, longitudinalMeters: 20000)
        }
        let lats = pts.map(\.latitude), lons = pts.map(\.longitude)
        let minSpan = detail.kind == "county" ? 0.35 : 0.04
        let span = MKCoordinateSpan(latitudeDelta: max((lats.max()! - lats.min()!) * 1.5, minSpan),
                                    longitudeDelta: max((lons.max()! - lons.min()!) * 1.5, minSpan))
        let center = pts.count == 1 ? first : .init(latitude: (lats.max()! + lats.min()!) / 2, longitude: (lons.max()! + lons.min()!) / 2)
        return MKCoordinateRegion(center: center, span: span)
    }

    var body: some View {
        Map(initialPosition: .region(region)) {
            ForEach(detail.places ?? []) { p in
                Marker("\(p.who): \(p.label)", systemImage: "house.fill", coordinate: .init(latitude: p.lat, longitude: p.lon))
                    .tint(Theme.ocean)
            }
            if detail.kind != "family", let home {
                Marker(home.label ?? "Home", systemImage: "house.fill", coordinate: .init(latitude: home.lat, longitude: home.lon))
                    .tint(Theme.ocean)
            }
            ForEach(detail.reports) { r in
                Annotation(r.title, coordinate: .init(latitude: r.lat, longitude: r.lon)) {
                    Button { onSelect(r) } label: {
                        Image(systemName: "drop.fill").foregroundStyle(.white).padding(7)
                            .background(r.severity >= 3 ? Color.red : r.severity == 2 ? Color.orange : Theme.sea, in: Circle())
                            .overlay(Circle().stroke(.white, lineWidth: 2))
                    }
                }
            }
        }
    }
}
