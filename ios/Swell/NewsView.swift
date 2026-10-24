import SwiftUI

struct NewsView: View {
    @Environment(AppStore.self) private var store
    @State private var tab = "local"
    @State private var news: News?
    @State private var regions: Regions?
    @State private var errorText: String?

    var body: some View {
        if let plan = store.plan {
            List {
                Picker("Show", selection: $tab) {
                    Text("Near \(plan.place.county ?? "you")").tag("local")
                    Text("Around the world").tag("world")
                }
                .pickerStyle(.segmented)
                .listRowBackground(Color.clear)

                if let errorText { Text(errorText).foregroundStyle(.secondary) }

                if tab == "local" {
                    if let n = news {
                        if let h = n.headline, !h.isEmpty {
                            Section { Text(h).font(.headline) }
                        }
                        Section {
                            ForEach(n.items) { i in
                                VStack(alignment: .leading, spacing: 4) {
                                    if let d = i.date, !d.isEmpty { Text(d).font(.caption.bold()).foregroundStyle(.secondary) }
                                    Text(i.title).font(.headline)
                                    Text(i.summary).font(.subheadline)
                                    if let a = i.action, !a.isEmpty { Text(a).font(.subheadline.bold()).foregroundStyle(Theme.sea) }
                                }
                                .padding(.vertical, 4)
                            }
                        } footer: {
                            Text("Summaries are written by AI from the sources below and can contain mistakes.")
                        }
                        Section("Sources") {
                            ForEach(n.sources) { s in if let url = URL(string: s.url) { SwiftUI.Link(s.title, destination: url) } }
                        }
                    } else {
                        ProgressView()
                    }
                } else if let r = regions {
                    Section {
                        Text("The same El Niño brings different dangers to different places. \(r.note)").font(.subheadline)
                    }
                    ForEach(r.regions) { reg in
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text(reg.name).font(.headline)
                                Spacer()
                                Text(reg.effect).font(.caption.bold())
                                    .padding(.horizontal, 8).padding(.vertical, 3)
                                    .background((reg.effect.contains("wet") ? Color.blue : Color.orange).opacity(0.15), in: Capsule())
                            }
                            Text(reg.season).font(.caption).foregroundStyle(.secondary)
                            Text(reg.impact).font(.subheadline)
                            Text("Get ready: \(reg.prepare)").font(.subheadline.bold())
                        }
                        .padding(.vertical, 4)
                    }
                } else {
                    ProgressView()
                }
            }
            .navigationTitle("El Niño news")
            .task(id: tab) { await load(plan) }
        }
    }

    private func load(_ plan: Plan) async {
        errorText = nil
        do {
            if tab == "local", news == nil {
                news = try await APIClient.shared.news(county: plan.place.county ?? "", state: plan.place.state ?? "CA", lang: plan.language ?? "en")
            } else if tab == "world", regions == nil {
                regions = try await APIClient.shared.regions()
            }
        } catch {
            errorText = error.localizedDescription
        }
    }
}
