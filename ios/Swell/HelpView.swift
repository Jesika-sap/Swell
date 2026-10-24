import SwiftUI

struct HelpView: View {
    @Environment(AppStore.self) private var store

    var body: some View {
        if let plan = store.plan {
            List {
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

                if let county = plan.help.county, !county.isEmpty {
                    Section("\(plan.place.county ?? "") County") { ForEach(county) { ResourceRow(r: $0) } }
                }
                if let state = plan.help.statewide, !state.isEmpty {
                    Section("Anywhere in California") { ForEach(state) { ResourceRow(r: $0) } }
                }
                Section { Text("In an emergency, call 911.").font(.footnote).foregroundStyle(.secondary) }
            }
            .navigationTitle("Help near \(plan.place.city ?? "you")")
        }
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
