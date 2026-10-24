import SwiftUI
import UIKit
import MapKit

/// Communities. With an account you're added to your county and city, where only
/// verified officials post updates. Neighborhood and family groups are private,
/// joined with an invite code, and everyone in them can post storm reports.
struct CommunityView: View {
    @Environment(AppStore.self) private var store
    @State private var list: CommunityList?
    @State private var errorText: String?
    @State private var accountMode: AccountMode?
    @State private var newGroupKind: GroupKind?
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
        .sheet(item: $newGroupKind, onDismiss: { Task { await load() } }) { kind in NewGroupSheet(kind: kind) }
        .sheet(isPresented: $showJoinCode, onDismiss: { Task { await load() } }) { JoinCodeSheet() }
        .sheet(isPresented: $reporting) {
            if let plan = store.plan {
                ReportSheet(lat: plan.lat, lon: plan.lon)
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
                Text("With a free account, you’re added to your county and city, where officials post updates. Then start or join a neighborhood or family group, where everyone can post storm reports.")
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
        Section {
            if list.mine.isEmpty {
                Text("Make a plan for your home first, and you’ll be added to your county and city.").foregroundStyle(.secondary)
            }
            ForEach(list.mine) { c in
                NavigationLink(value: c) { CommunityRow(kind: c.kind, name: c.name, detail: "\(CommunityKind.label(c.kind)) · \(c.members) \(c.members == 1 ? "member" : "members")") }
            }
        } header: {
            Text("Your communities")
        } footer: {
            Text("Officials post updates in your county and city. In neighborhood and family groups, everyone can post.")
        }
        Section {
            VStack(alignment: .leading, spacing: 10) {
                Text("Start a group").font(.headline)
                Text("**Neighborhood group:** for your street or block. Everyone in it can post storm reports, like a flooded corner or a blocked drain.")
                    .font(.subheadline).foregroundStyle(.secondary)
                Text("**Family group:** private, as big as you want. See each other’s places and checklist progress, and tap “I’m safe” after a storm.")
                    .font(.subheadline).foregroundStyle(.secondary)
                HStack {
                    Button { newGroupKind = .neighborhood } label: { Text("Neighborhood").frame(maxWidth: .infinity) }
                        .buttonStyle(.borderedProminent)
                    Button { newGroupKind = .family } label: { Text("Family").frame(maxWidth: .infinity) }
                        .buttonStyle(.borderedProminent)
                }
                Button { showJoinCode = true } label: { Text("Join with a code").frame(maxWidth: .infinity) }
                    .buttonStyle(.bordered)
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

}

struct CommunityRow: View {
    let kind: String
    let name: String
    let detail: String

    private var color: Color {
        switch kind {
        case "family": return .orange
        case "neighborhood": return .green
        default: return Theme.sea
        }
    }

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: CommunityKind.symbol(kind))
                .foregroundStyle(color)
                .frame(width: 36, height: 36)
                .background(color.opacity(0.12), in: RoundedRectangle(cornerRadius: 10))
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
                if let code = d.inviteCode { inviteSection(code, family: d.kind == "family") }
                Section {
                    if d.reports.isEmpty {
                        Text(isGroup(d)
                             ? "No storm reports yet. If you see flooding, a clogged drain or a fallen tree, post it so \(d.kind == "family" ? "your family knows" : "your neighbors know")."
                             : "No official updates right now.")
                            .foregroundStyle(.secondary)
                    }
                    ForEach(d.reports) { r in
                        Button { selected = r } label: { reportRow(r) }.buttonStyle(.plain)
                    }
                } header: {
                    HStack {
                        Text(isGroup(d) ? "Storm reports from this group" : "Official updates")
                        Spacer()
                        if d.canPost == true {
                            Button("+ Post") { reporting = true }.font(.subheadline.bold()).textCase(nil)
                        }
                    }
                } footer: {
                    if !isGroup(d) {
                        Text(d.canPost == true
                             ? "You’re a verified official here, so you can post updates everyone in the area will see."
                             : "Only verified officials, like the county’s emergency office or the city, can post here. To share what you see, post in a neighborhood or family group.")
                    }
                }
                if isGroup(d) {
                    Section {
                        Button("Leave this group", role: .destructive) {
                            Task {
                                try? await APIClient.shared.leaveCommunity(d.id)
                                dismiss()
                            }
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
                ReportSheet(lat: plan.lat, lon: plan.lon, communityId: summary.id)
            }
        }
    }

    private func isGroup(_ d: CommunityDetail) -> Bool { d.kind == "family" || d.kind == "neighborhood" }

    @ViewBuilder
    private func inviteSection(_ code: String, family: Bool) -> some View {
        Section {
            HStack {
                Text("Invite code").font(.caption).foregroundStyle(.secondary)
                Text(code).font(.title3.monospaced().bold())
                Spacer()
                Button("Copy") { UIPasteboard.general.string = code }
            }
        } footer: {
            Text("Send this code to \(family ? "family" : "neighbors"). They create a free account and tap “Join with a code.”")
        }
    }

    @ViewBuilder
    private func familySection(_ d: CommunityDetail) -> some View {
        Section("Members · \(d.members)") {
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

enum GroupKind: String, Identifiable {
    case neighborhood, family
    var id: String { rawValue }
}

struct NewGroupSheet: View {
    let kind: GroupKind
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var errorText: String?

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField(kind == .family ? "Group name, e.g. Sapkota family" : "Group name, e.g. Murchison Drive neighbors", text: $name)
                } footer: {
                    Text(kind == .family
                         ? "Add as many people as you want. You’ll get a code to share with them."
                         : "Invite the neighbors on your street or block. Everyone in the group can post storm reports.")
                }
                if let errorText { Text(errorText).foregroundStyle(.red) }
                Button("Create group") {
                    Task {
                        do { _ = try await APIClient.shared.createGroup(kind: kind.rawValue, name: name); dismiss() } catch { errorText = error.localizedDescription }
                    }
                }.bold()
            }
            .navigationTitle(kind == .family ? "Start a family group" : "Start a neighborhood group")
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
                } footer: { Text("Ask the person who made the neighborhood or family group for its 6-letter code.") }
                if let errorText { Text(errorText).foregroundStyle(.red) }
                Button("Join") {
                    Task {
                        do { _ = try await APIClient.shared.joinGroup(code: code); dismiss() } catch { errorText = error.localizedDescription }
                    }
                }.bold()
            }
            .navigationTitle("Join a group")
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
