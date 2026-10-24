import SwiftUI
import PhotosUI

struct PlanView: View {
    @Environment(AppStore.self) private var store
    @State private var places: [PlanSummary] = []
    @State private var scanning = false

    var body: some View {
        if let plan = store.plan {
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    RiskCard(plan: plan)

                    if let r = plan.risk.region, !plan.inUS {
                        RegionCard(region: r, drought: plan.isDrought)
                    }

                    ScanCard { scanning = true }

                    let storm = (plan.alerts ?? []).filter { $0.stormRelated ?? false }
                    if !plan.inUS {
                        EmptyView()
                    } else if storm.isEmpty {
                        AlertBox(title: "No storm alerts right now", text: "We check the National Weather Service every time you open the app.", color: .green, symbol: "checkmark.circle")
                    } else {
                        ForEach(storm) { a in
                            AlertBox(title: a.event, text: a.headline ?? "", color: a.kind == "warning" ? .red : .orange, symbol: "exclamationmark.triangle.fill", more: a.instruction ?? a.description)
                        }
                    }

                    VStack(alignment: .leading, spacing: 10) {
                        HStack(spacing: 14) {
                            ProgressRing(done: plan.progress.done, total: plan.progress.total)
                            VStack(alignment: .leading) {
                                Text(plan.progress.done == 0 ? "Start here" : "Keep going").font(.headline)
                                Text("\(plan.progress.done) of \(plan.progress.total) steps done").font(.subheadline).foregroundStyle(.secondary)
                            }
                        }
                        ForEach(plan.checklist.filter { !($0.done ?? false) }.prefix(3)) { t in TaskRow(task: t) }
                    }
                    .card()

                    VStack(alignment: .leading, spacing: 0) {
                        Text("Why this score").font(.headline).padding(.bottom, 8)
                        ForEach(plan.risk.factors) { f in
                            HStack(alignment: .top, spacing: 12) {
                                Text("+\(f.points)").font(.subheadline.weight(.heavy)).frame(width: 44, height: 28)
                                    .background(f.points >= 25 ? Color.red.opacity(0.15) : f.points >= 10 ? Color.orange.opacity(0.15) : Color.secondary.opacity(0.12), in: RoundedRectangle(cornerRadius: 8))
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(f.label).bold()
                                    Text(f.detail).font(.subheadline)
                                    Text(f.source).font(.caption).foregroundStyle(.secondary)
                                }
                            }
                            .padding(.vertical, 10)
                            Divider()
                        }
                    }
                    .card()

                    if let fc = plan.forecast, !fc.isEmpty {
                        Text("Next few days").font(.headline)
                        ScrollView(.horizontal, showsIndicators: false) {
                            HStack(spacing: 8) {
                                ForEach(fc) { p in
                                    VStack(alignment: .leading, spacing: 4) {
                                        Text(p.name ?? "").font(.caption.bold())
                                        Text(p.short ?? "").font(.caption)
                                        Text("\(p.rainChance ?? 0)% rain").font(.caption.bold()).foregroundStyle(Theme.sea)
                                    }
                                    .frame(width: 96, alignment: .leading)
                                    .padding(10)
                                    .background((p.rainChance ?? 0) >= 50 ? Theme.sea.opacity(0.12) : Color.secondary.opacity(0.08), in: RoundedRectangle(cornerRadius: 12))
                                }
                            }
                        }
                    }

                    if let tides = plan.risk.kingTides, !tides.isEmpty {
                        Text("King tides").font(.headline)
                        HStack(spacing: 8) {
                            ForEach(tides) { w in
                                VStack {
                                    Text(dayRange(w.start, w.end)).font(.subheadline.bold())
                                    Text(w.active == true ? "Happening now" : String(w.start.prefix(4))).font(.caption).foregroundStyle(.secondary)
                                }
                                .frame(maxWidth: .infinity).padding(10)
                                .background((w.active == true ? Color.orange : Theme.sea).opacity(0.12), in: RoundedRectangle(cornerRadius: 12))
                            }
                        }
                        Text("Low streets near the Bay can flood even on sunny days. Source: San Mateo County Parks.").font(.caption).foregroundStyle(.secondary)
                    }

                    if let e = plan.enso {
                        VStack(alignment: .leading, spacing: 8) {
                            Text("EL NIÑO 2026–27").font(.caption.bold()).foregroundStyle(.secondary)
                            Text(e.status).font(.headline)
                            Text(e.detail).font(.subheadline)
                            ForEach(e.events) { ev in
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(ev.text).font(.subheadline)
                                    if let url = URL(string: ev.url) { SwiftUI.Link(ev.source, destination: url).font(.caption) }
                                }
                                .padding(.leading, 10)
                                .overlay(alignment: .leading) { Rectangle().fill(Theme.sea).frame(width: 3) }
                            }
                        }
                        .card()
                    }
                    Text("This plan helps you prepare. In an emergency, follow official orders and call 911.")
                        .font(.caption).foregroundStyle(.secondary).frame(maxWidth: .infinity)
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle(plan.label ?? "My plan")
            .navigationBarTitleDisplayMode(.inline)
            .refreshable { await store.loadSaved() }
            .sheet(isPresented: $scanning) { ScanSheet() }
            .toolbar {
                ToolbarItem(placement: .topBarLeading) {
                    Menu {
                        ForEach(places) { p in
                            Button("\(p.label ?? "Place") · \(p.score)") { Task { await store.open(p.id) } }
                        }
                        Divider()
                        Button("Add another place", systemImage: "plus") { store.addingPlace = true }
                    } label: { Label("Places", systemImage: "mappin.and.ellipse") }
                }
            }
            .task { places = (try? await APIClient.shared.plans()) ?? [] }
        }
    }

    private func dayRange(_ a: String, _ b: String) -> String {
        let f = DateFormatter(); f.dateFormat = "yyyy-MM-dd"
        let out = DateFormatter(); out.dateFormat = "MMM d"
        guard let da = f.date(from: a), let db = f.date(from: b) else { return a }
        let day = DateFormatter(); day.dateFormat = "d"
        return "\(out.string(from: da))–\(day.string(from: db))"
    }
}

struct RiskCard: View {
    let plan: Plan
    @State private var shown = 0.0

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(spacing: 16) {
                ZStack {
                    Circle().stroke(.white.opacity(0.15), lineWidth: 10)
                    Circle().trim(from: 0, to: shown)
                        .stroke(Theme.level(plan.risk.level), style: StrokeStyle(lineWidth: 10, lineCap: .round))
                        .rotationEffect(.degrees(-90))
                    VStack(spacing: 0) {
                        Text("\(plan.risk.score)").font(.system(size: 32, weight: .heavy, design: .rounded))
                        Text("out of 100").font(.caption2).opacity(0.7)
                    }
                }
                .frame(width: 100, height: 100)
                VStack(alignment: .leading, spacing: 6) {
                    Text(Theme.levelText(plan.risk.level)).font(.caption.weight(.heavy))
                        .padding(.horizontal, 10).padding(.vertical, 4)
                        .background(Theme.level(plan.risk.level).opacity(0.9), in: Capsule()).foregroundStyle(.black.opacity(0.75))
                    Text("\(plan.isDrought ? "Drought" : "Storm") risk for \(plan.label ?? (plan.isFarm ? "this farm" : "this home"))").font(.title3.bold())
                    Text(plan.place.line).font(.subheadline).opacity(0.75)
                }
            }
            if let s = plan.summary { Text(s).font(.callout) }
            if plan.translated == true { Text("Plan written in your language").font(.caption).opacity(0.7) }
        }
        .foregroundStyle(.white)
        .padding(20)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(LinearGradient(colors: [Theme.ocean, Theme.ocean2], startPoint: .topLeading, endPoint: .bottomTrailing), in: RoundedRectangle(cornerRadius: 22))
        .onAppear { withAnimation(.easeOut(duration: 1)) { shown = Double(plan.risk.score) / 100 } }
        .accessibilityElement(children: .combine)
    }
}

struct AlertBox: View {
    let title: String
    let text: String
    let color: Color
    let symbol: String
    var more: String? = nil

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: symbol).font(.title3).foregroundStyle(color)
            VStack(alignment: .leading, spacing: 4) {
                Text(title).bold()
                Text(text).font(.subheadline)
                if let more, !more.isEmpty {
                    DisclosureGroup("What to do") { Text(more).font(.subheadline) }.font(.subheadline.bold())
                }
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(color.opacity(0.12), in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(color.opacity(0.4)))
    }
}

struct ProgressRing: View {
    let done: Int
    let total: Int
    var body: some View {
        ZStack {
            Circle().stroke(Color.secondary.opacity(0.15), lineWidth: 7)
            Circle().trim(from: 0, to: total == 0 ? 0 : CGFloat(done) / CGFloat(total))
                .stroke(Theme.sea, style: StrokeStyle(lineWidth: 7, lineCap: .round)).rotationEffect(.degrees(-90))
            Text("\(done)/\(total)").font(.caption.bold())
        }
        .frame(width: 56, height: 56)
        .animation(.easeOut, value: done)
    }
}

struct TaskRow: View {
    @Environment(AppStore.self) private var store
    let task: PlanTask

    var body: some View {
        let done = task.done ?? false
        HStack(alignment: .top, spacing: 12) {
            Button { Task { await store.toggle(task) } } label: {
                Image(systemName: done ? "checkmark.square.fill" : "square").font(.title2).foregroundStyle(done ? Theme.sea : .secondary)
            }
            .buttonStyle(.plain)
            .accessibilityLabel(done ? "Mark not done" : "Mark done")
            VStack(alignment: .leading, spacing: 3) {
                HStack(spacing: 6) {
                    if task.priority == 1 && !done { Text("DO FIRST").font(.caption2.weight(.heavy)).foregroundStyle(.red) }
                    if task.source == "scan" {
                        Label("Found by AI Scan", systemImage: "camera.viewfinder").font(.caption2.weight(.heavy)).foregroundStyle(Theme.sea)
                    }
                }
                Text(task.title).bold().strikethrough(done).foregroundStyle(done ? .secondary : .primary)
                Text(task.why).font(.subheadline).foregroundStyle(.secondary)
                if let link = task.link, let url = URL(string: link) { SwiftUI.Link("Open link", destination: url).font(.subheadline.bold()) }
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 16))
    }
}

extension View {
    func card() -> some View {
        padding(16)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Color(.secondarySystemGroupedBackground), in: RoundedRectangle(cornerRadius: 18))
    }
}


struct RegionCard: View {
    let region: RegionInfo
    let drought: Bool

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label(drought ? "El Niño here means drought" : "El Niño here means heavy rain", systemImage: drought ? "sun.max.trianglebadge.exclamationmark" : "cloud.heavyrain")
                .font(.headline).foregroundStyle(drought ? .orange : Theme.sea)
            Text(region.name).font(.subheadline.bold())
            Text(region.effect).font(.subheadline)
            Text("When: \(region.season)").font(.caption).foregroundStyle(.secondary)
            Text("Source: NOAA Climate Prediction Center").font(.caption).foregroundStyle(.secondary)
        }
        .card()
    }
}

struct ScanCard: View {
    let action: () -> Void
    var body: some View {
        Button(action: action) {
            HStack(spacing: 14) {
                Image(systemName: "camera.viewfinder").font(.largeTitle).foregroundStyle(.white)
                    .frame(width: 58, height: 58).background(Theme.sea, in: RoundedRectangle(cornerRadius: 14))
                VStack(alignment: .leading, spacing: 3) {
                    Text("AI Scan").font(.headline).foregroundStyle(.primary)
                    Text("Take a photo of your home, yard or farm. AI spots risks you can see and adds them to your checklist.")
                        .font(.subheadline).foregroundStyle(.secondary).multilineTextAlignment(.leading)
                }
                Spacer(minLength: 0)
            }
            .card()
        }
        .buttonStyle(.plain)
    }
}

struct ScanSheet: View {
    @Environment(AppStore.self) private var store
    @Environment(\.dismiss) private var dismiss
    @State private var item: PhotosPickerItem?
    @State private var preview: UIImage?
    @State private var working = false
    @State private var result: ScanResult?
    @State private var errorText: String?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    if let preview {
                        Image(uiImage: preview).resizable().scaledToFill()
                            .frame(maxWidth: .infinity, maxHeight: 240).clipShape(RoundedRectangle(cornerRadius: 16))
                    }
                    if working {
                        HStack(spacing: 10) { ProgressView(); Text("Looking for risks…") }
                    } else if let result {
                        Text("What AI sees").font(.caption.bold()).foregroundStyle(.secondary)
                        Text(result.seen).font(.subheadline)
                        if result.added.isEmpty {
                            Text("No new risks spotted in this photo. Try another angle, like gutters, drains, doors or water storage.").foregroundStyle(.secondary)
                        } else {
                            Text("Added \(result.added.count) to the top of your checklist").font(.headline)
                            ForEach(result.added) { t in TaskRow(task: t) }
                        }
                        if let good = result.good, !good.isEmpty {
                            Text("Already done right").font(.headline)
                            ForEach(good, id: \.self) { g in
                                Label(g, systemImage: "checkmark.circle").font(.subheadline)
                            }
                        }
                        if let next = result.nextPhoto, !next.isEmpty {
                            Label("Next, take a photo of: \(next)", systemImage: "camera")
                                .font(.subheadline).foregroundStyle(.secondary)
                        }
                    } else {
                        Text("Point your camera at the outside of your home, a drain, your roof gutters, a water tank or a field. AI looks for risks you can see and turns them into checklist steps.")
                            .foregroundStyle(.secondary)
                    }
                    if let errorText { Text(errorText).foregroundStyle(.red) }
                    PhotosPicker(selection: $item, matching: .images) {
                        Label(result == nil ? "Choose a photo" : "Scan another photo", systemImage: "photo.on.rectangle")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent).controlSize(.large).disabled(working)
                    Text("AI can miss things. Your checklist from official data still comes first.").font(.caption).foregroundStyle(.secondary)
                }
                .padding()
            }
            .navigationTitle("AI Scan")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
            .onChange(of: item) { _, newItem in Task { await run(newItem) } }
        }
    }

    private func run(_ newItem: PhotosPickerItem?) async {
        guard let newItem, let data = try? await newItem.loadTransferable(type: Data.self), let img = UIImage(data: data) else { return }
        let small = img.resized(maxSide: 1024)
        guard let jpeg = small.jpegData(compressionQuality: 0.7) else { return }
        preview = small
        working = true
        errorText = nil
        do {
            result = try await store.scan(photo: "data:image/jpeg;base64," + jpeg.base64EncodedString())
        } catch {
            errorText = error.localizedDescription
        }
        working = false
    }
}
