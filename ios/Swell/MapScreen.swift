import SwiftUI
import MapKit
import PhotosUI
import UIKit

struct MapScreen: View {
    @Environment(AppStore.self) private var store
    @State private var position: MapCameraPosition = .automatic
    @State private var center: CLLocationCoordinate2D?
    @State private var reports: [StormReport] = []
    @State private var selected: StormReport?
    @State private var reporting = false

    var body: some View {
        if let plan = store.plan {
            Map(position: $position) {
                Marker(plan.label ?? "Home", systemImage: "house.fill", coordinate: .init(latitude: plan.lat, longitude: plan.lon))
                    .tint(Theme.ocean)
                ForEach(plan.isDrought ? [SandbagSite]() : (plan.help.sandbags ?? [])) { s in
                    Marker("Sandbags: \(s.name)", systemImage: "bag.fill", coordinate: .init(latitude: s.lat, longitude: s.lon))
                        .tint(.orange)
                }
                ForEach(reports) { r in
                    Annotation(r.title, coordinate: .init(latitude: r.lat, longitude: r.lon)) {
                        Button { selected = r } label: {
                            Image(systemName: "drop.fill").foregroundStyle(.white).padding(7)
                                .background(r.severity >= 3 ? Color.red : r.severity == 2 ? Color.orange : Theme.sea, in: Circle())
                                .overlay(Circle().stroke(.white, lineWidth: 2))
                        }
                    }
                }
            }
            .onMapCameraChange { ctx in center = ctx.region.center }
            .overlay(alignment: .bottomTrailing) {
                Button { reporting = true } label: { Label("Report a problem", systemImage: "camera.fill").bold() }
                    .buttonStyle(.borderedProminent).controlSize(.large).clipShape(Capsule()).padding()
            }
            .navigationTitle("Map")
            .navigationBarTitleDisplayMode(.inline)
            .task {
                position = .region(MKCoordinateRegion(center: .init(latitude: plan.lat, longitude: plan.lon), latitudinalMeters: 3500, longitudinalMeters: 3500))
                await loadReports(plan)
            }
            .sheet(item: $selected) { r in ReportDetail(report: r).presentationDetents([.medium]) }
            .sheet(isPresented: $reporting, onDismiss: { Task { await loadReports(plan) } }) {
                ReportSheet(lat: center?.latitude ?? plan.lat, lon: center?.longitude ?? plan.lon)
            }
        }
    }

    private func loadReports(_ plan: Plan) async {
        reports = (try? await APIClient.shared.reports(lat: plan.lat, lon: plan.lon)) ?? []
    }
}

struct ReportDetail: View {
    let report: StormReport
    @State private var confirmed = false
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(report.title).font(.title2.bold())
            if let name = report.communityName {
                Text(report.official == true ? "Official update from \(name)" : "Posted in \(name)").font(.subheadline.bold())
            }
            Text("\(report.confirmations + (confirmed ? 1 : 0)) people confirmed this").foregroundStyle(.secondary)
            if let note = report.note, !note.isEmpty { Text(note) }
            Button {
                Task { try? await APIClient.shared.confirm(report: report.id); confirmed = true; dismiss() }
            } label: { Text("I see this too").frame(maxWidth: .infinity) }
                .buttonStyle(.borderedProminent).controlSize(.large)
            Spacer()
        }
        .padding(22)
    }
}

/// Neighbors report flooding with a photo. AI suggests the label; the person can change it.
/// Reports go to a group you can post in: any neighborhood or family group you're in,
/// or a county or city community if you're a verified official there.
struct ReportSheet: View {
    let lat: Double
    let lon: Double
    var communityId: String? = nil
    @Environment(\.dismiss) private var dismiss
    @State private var groups: [CommunitySummary] = []
    @State private var signedIn = true
    @State private var loaded = false
    @State private var groupId = ""
    @State private var item: PhotosPickerItem?
    @State private var image: UIImage?
    @State private var photoData: String?
    @State private var kind = "flooding"
    @State private var title = ""
    @State private var severity = 2
    @State private var aiNote: String?
    @State private var analyzing = false
    @State private var aiChecked = false
    @State private var sending = false
    @State private var errorText: String?

    private let kinds = [("flooding", "Flooded street"), ("drain", "Clogged storm drain"), ("landslide", "Landslide or mudslide"),
                         ("tree", "Fallen tree"), ("power", "Downed power line"), ("road", "Road damage"), ("other", "Other storm problem")]

    var body: some View {
        NavigationStack {
            Form {
                if loaded && !signedIn {
                    Text("Create a free account in the Community tab to post. Storm reports go to a neighborhood or family group, so the people near you see them.")
                        .foregroundStyle(.secondary)
                } else if loaded && groups.isEmpty {
                    Text("County and city communities are for official updates. To post a storm report, start or join a neighborhood or family group in the Community tab.")
                        .foregroundStyle(.secondary)
                } else {
                    form
                }
            }
            .navigationTitle("Report a storm problem")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Cancel") { dismiss() } } }
            .onChange(of: item) { _, newItem in Task { await loadPhoto(newItem) } }
            .task { await loadGroups() }
        }
    }

    @ViewBuilder
    private var form: some View {
                Section("Post to") {
                    Picker("Group", selection: $groupId) {
                        ForEach(groups) { g in Text(g.name).tag(g.id) }
                    }
                }
                Section {
                    PhotosPicker(selection: $item, matching: .images) {
                        if let image {
                            Image(uiImage: image).resizable().scaledToFill().frame(height: 200).clipped().clipShape(RoundedRectangle(cornerRadius: 12))
                        } else {
                            Label("Add a photo (AI will label it)", systemImage: "camera")
                        }
                    }
                    if analyzing { HStack { ProgressView(); Text("AI is looking at your photo…") } }
                    if let aiNote { Label(aiNote, systemImage: "sparkles").foregroundStyle(Theme.sea) }
                } footer: { Text("Everyone in the group you pick will see it. Don’t take photos in dangerous spots.") }

                Section("What is it?") {
                    Picker("Kind", selection: $kind) { ForEach(kinds, id: \.0) { Text($0.1).tag($0.0) } }
                    TextField("Short title, e.g. Water across Main St", text: $title)
                    Picker("How bad?", selection: $severity) {
                        Text("Minor").tag(1); Text("Avoid it").tag(2); Text("Dangerous").tag(3)
                    }
                    .pickerStyle(.segmented)
                }
                if let errorText { Text(errorText).foregroundStyle(.red) }
                Button { Task { await send() } } label: {
                    if sending { ProgressView() } else { Text("Post report").bold() }
                }
                .disabled(sending || groupId.isEmpty)
    }

    private func loadGroups() async {
        if let list = try? await APIClient.shared.communities() {
            signedIn = list.account != nil
            groups = list.mine.filter { $0.canPost == true }
            if let communityId, groups.contains(where: { $0.id == communityId }) {
                groupId = communityId
            } else {
                groupId = groups.first?.id ?? ""
            }
        }
        loaded = true
    }

    private func loadPhoto(_ newItem: PhotosPickerItem?) async {
        guard let newItem, let data = try? await newItem.loadTransferable(type: Data.self), let ui = UIImage(data: data) else { return }
        let small = ui.resized(maxSide: 1280)
        image = small
        guard let jpeg = small.jpegData(compressionQuality: 0.7) else { return }
        photoData = "data:image/jpeg;base64," + jpeg.base64EncodedString()
        analyzing = true
        defer { analyzing = false }
        if let a = try? await APIClient.shared.analyze(photo: photoData!), a.ai {
            kind = a.kind ?? kind
            title = a.title ?? title
            severity = a.severity ?? severity
            aiNote = a.advice ?? "AI filled this in. Change anything that’s wrong."
            aiChecked = true
        }
    }

    private func send() async {
        sending = true
        defer { sending = false }
        do {
            try await APIClient.shared.postReport(communityId: groupId, lat: lat, lon: lon, kind: kind, title: title, severity: severity,
                                                  photo: photoData, aiChecked: aiChecked)
            dismiss()
        } catch {
            errorText = error.localizedDescription
        }
    }
}

extension UIImage {
    func resized(maxSide: CGFloat) -> UIImage {
        let scale = min(1, maxSide / max(size.width, size.height))
        if scale >= 1 { return self }
        let newSize = CGSize(width: size.width * scale, height: size.height * scale)
        return UIGraphicsImageRenderer(size: newSize).image { _ in draw(in: CGRect(origin: .zero, size: newSize)) }
    }
}
