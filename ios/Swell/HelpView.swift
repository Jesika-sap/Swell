import SwiftUI

struct HelpView: View {
    @Environment(AppStore.self) private var store
    @State private var requests: [HelpRequest] = []
    @State private var orgs: [Org] = []
    @State private var asking = false

    var body: some View {
        if let plan = store.plan {
            List {
                Section {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Need a hand?").font(.headline)
                        Text("Ask local groups for sandbags, a ride, a check-in call, translation or farm help. Only the group that says yes sees your exact location and contact.")
                            .font(.subheadline).foregroundStyle(.secondary)
                        Button { asking = true } label: { Label("Ask for help", systemImage: "hand.raised.fill").frame(maxWidth: .infinity) }
                            .buttonStyle(.borderedProminent)
                    }
                    .padding(.vertical, 6)
                }

                if !requests.isEmpty {
                    Section("Your requests") {
                        ForEach(requests) { r in RequestRow(r: r) { await cancel(r, plan) } }
                    }
                }

                Section("Groups that help near you") {
                    if orgs.isEmpty {
                        Text("No groups have signed up near here yet. Know one? Send them to “For organizations.”").foregroundStyle(.secondary)
                    }
                    ForEach(orgs) { o in OrgRow(o: o) }
                }

                if let a = plan.help.alertSystem, let url = URL(string: a.url) {
                    Section {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("STEP ONE FOR EVERYONE").font(.caption.bold()).foregroundStyle(.secondary)
                            Text("Sign up for \(a.name)").font(.headline)
                            Text("\(plan.place.county ?? "Your") County’s official emergency alerts: evacuations, road closures and shelters.").font(.subheadline)
                            SwiftUI.Link(destination: url) { Text("Sign up").bold().frame(maxWidth: .infinity) }
                                .buttonStyle(.borderedProminent)
                        }
                        .padding(.vertical, 6)
                    }
                }

                if plan.inUS && !plan.isDrought {
                Section("Sandbags, closest first") {
                    let sites = plan.help.sandbags ?? []
                    if !sites.isEmpty {
                        ForEach(sites) { s in
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text(s.name).bold()
                                    Spacer()
                                    Text(String(format: "%.1f mi", s.miles)).font(.subheadline.bold()).foregroundStyle(Theme.sea)
                                }
                                Text(s.address).font(.subheadline)
                                Text(s.notes).font(.caption).foregroundStyle(.secondary)
                                HStack(spacing: 16) {
                                    if let url = mapsURL(s.address) { SwiftUI.Link("Directions", destination: url) }
                                    if let p = s.phone, let url = URL(string: "tel:" + p.filter(\.isNumber)) { SwiftUI.Link("Call", destination: url) }
                                    if let url = URL(string: s.source) { SwiftUI.Link("Source", destination: url) }
                                }
                                .font(.subheadline.bold())
                                .buttonStyle(.borderless)
                            }
                            .padding(.vertical, 4)
                        }
                    } else if let ai = plan.help.ai, !ai.sites.isEmpty {
                        ForEach(ai.sites) { s in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(s.name).bold()
                                Text("Found by AI search: confirm before you go").font(.caption.bold()).foregroundStyle(.orange)
                                if !s.address.isEmpty { Text(s.address).font(.subheadline) }
                                if !s.notes.isEmpty { Text(s.notes).font(.caption).foregroundStyle(.secondary) }
                            }
                        }
                        ForEach(ai.sources) { src in
                            if let url = URL(string: src.url) { SwiftUI.Link(src.title, destination: url).font(.caption) }
                        }
                    } else {
                        Text("We haven’t checked sandbag sites here yet. Call 211 or check your city’s public works page.").foregroundStyle(.secondary)
                    }
                }
                }

                if let c = plan.help.country, !c.isEmpty {
                    Section(countryTitle(plan)) { ForEach(c) { ResourceRow(r: $0) } }
                }

                if let county = plan.help.county, !county.isEmpty {
                    Section("\(plan.place.county ?? "") County") { ForEach(county) { ResourceRow(r: $0) } }
                }
                if let state = plan.help.statewide, !state.isEmpty {
                    Section(plan.place.state?.uppercased() == "CA" ? "Anywhere in California" : "Anywhere in the U.S.") { ForEach(state) { ResourceRow(r: $0) } }
                }
                Section { Text(plan.inUS ? "In an emergency, call 911." : "In an emergency, call your local emergency number.").font(.footnote).foregroundStyle(.secondary) }
            }
            .navigationTitle("Help near \(plan.place.city ?? "you")")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    NavigationLink { OrgView() } label: { Label("For organizations", systemImage: "building.2") }
                }
            }
            .sheet(isPresented: $asking, onDismiss: { Task { await load(plan) } }) { AskHelpSheet(planId: plan.id) }
            .task(id: plan.id) { await load(plan) }
            .refreshable { await load(plan) }
        }
    }

    private func load(_ plan: Plan) async {
        requests = (try? await APIClient.shared.myRequests(plan: plan.id)) ?? []
        orgs = (try? await APIClient.shared.orgs(lat: plan.lat, lon: plan.lon)) ?? []
    }

    private func cancel(_ r: HelpRequest, _ plan: Plan) async {
        if let list = try? await APIClient.shared.cancelHelp(plan: plan.id, request: r.id) { requests = list }
    }

    private func countryTitle(_ plan: Plan) -> String {
        (plan.place.country ?? "").uppercased() == "NP" ? "Official help in Nepal" : "Official help in this country"
    }

    private func mapsURL(_ address: String) -> URL? {
        let q = address.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
        return URL(string: "http://maps.apple.com/?daddr=\(q)")
    }
}

struct ResourceRow: View {
    let r: Resource
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(r.name).bold()
            Text(r.what).font(.subheadline).foregroundStyle(.secondary)
            HStack(spacing: 16) {
                if let p = r.phone, let url = URL(string: "tel:\(p)") { SwiftUI.Link("Call \(p)", destination: url) }
                if let u = r.url, let url = URL(string: u) { SwiftUI.Link("Open", destination: url) }
            }
            .font(.subheadline.bold())
            .buttonStyle(.borderless)
        }
        .padding(.vertical, 4)
    }
}


struct RequestRow: View {
    let r: HelpRequest
    let cancel: () async -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(r.needLabel).bold()
                Spacer()
                Text(statusText).font(.caption.weight(.heavy))
                    .padding(.horizontal, 8).padding(.vertical, 3)
                    .background(statusColor.opacity(0.15), in: Capsule()).foregroundStyle(statusColor)
            }
            if let d = r.details, !d.isEmpty { Text(d).font(.subheadline).foregroundStyle(.secondary) }
            if let o = r.org {
                Text(r.status == "done" ? "Helped by \(o.name)" : "Help is on the way from \(o.name)").font(.subheadline.bold())
                HStack(spacing: 16) {
                    if let p = o.phone, let url = URL(string: "tel:" + p.filter(\.isNumber)) { SwiftUI.Link("Call", destination: url) }
                    if let e = o.email, let url = URL(string: "mailto:\(e)") { SwiftUI.Link("Email", destination: url) }
                }
                .font(.subheadline.bold()).buttonStyle(.borderless)
            } else if r.status == "open" {
                Text("Waiting for a nearby group to say yes.").font(.subheadline).foregroundStyle(.secondary)
                Button("Cancel request", role: .destructive) { Task { await cancel() } }.font(.subheadline).buttonStyle(.borderless)
            }
        }
        .padding(.vertical, 4)
    }

    private var statusText: String {
        switch r.status {
        case "accepted": return "ON THE WAY"
        case "done": return "DONE"
        default: return "WAITING"
        }
    }
    private var statusColor: Color {
        switch r.status {
        case "accepted": return Theme.sea
        case "done": return .green
        default: return .orange
        }
    }
}

struct OrgRow: View {
    let o: Org
    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text(o.name).bold()
                if o.verified { Image(systemName: "checkmark.seal.fill").foregroundStyle(Theme.sea).accessibilityLabel("Verified") }
                Spacer()
                if let m = o.miles { Text(String(format: "%.1f mi", m)).font(.subheadline.bold()).foregroundStyle(Theme.sea) }
            }
            if o.example { Text("Example group for testing").font(.caption.bold()).foregroundStyle(.orange) }
            if let a = o.about, !a.isEmpty { Text(a).font(.subheadline).foregroundStyle(.secondary) }
            Text(o.services.compactMap { id in services.first { $0.id == id }?.name }.joined(separator: " · ")).font(.caption)
        }
        .padding(.vertical, 4)
    }
}

struct AskHelpSheet: View {
    let planId: String
    @Environment(\.dismiss) private var dismiss
    @State private var need = "sandbags"
    @State private var details = ""
    @State private var contact = ""
    @State private var sending = false
    @State private var errorText: String?

    var body: some View {
        NavigationStack {
            Form {
                Section("What do you need?") {
                    Picker("Kind of help", selection: $need) {
                        ForEach(services, id: \.id) { s in Label(s.name, systemImage: s.symbol).tag(s.id) }
                    }
                    .pickerStyle(.inline).labelsHidden()
                }
                Section {
                    TextField("e.g. I can’t lift sandbags. Front door faces the street.", text: $details, axis: .vertical).lineLimit(2...5)
                } header: { Text("Details (optional)") }
                Section {
                    TextField("Phone or email", text: $contact).textContentType(.telephoneNumber)
                } header: { Text("How can a helper reach you?") } footer: {
                    Text("Groups nearby see your request and a rough area. Your exact location and contact are shared only with the group that accepts.")
                }
                if let errorText { Text(errorText).foregroundStyle(.red) }
            }
            .navigationTitle("Ask for help")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button(sending ? "Sending…" : "Send") { Task { await send() } }.bold().disabled(sending)
                }
            }
        }
    }

    private func send() async {
        sending = true
        defer { sending = false }
        do {
            _ = try await APIClient.shared.askForHelp(plan: planId, need: need, details: details, contact: contact)
            dismiss()
        } catch {
            errorText = error.localizedDescription
        }
    }
}
