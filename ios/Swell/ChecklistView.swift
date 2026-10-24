import SwiftUI

struct ChecklistView: View {
    @Environment(AppStore.self) private var store
    @State private var group = "now"
    private let groups = [("now", "This week"), ("kit", "At home"), ("storm", "In a storm")]

    var body: some View {
        if let plan = store.plan {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    HStack(spacing: 14) {
                        ProgressRing(done: plan.progress.done, total: plan.progress.total)
                        Text("Made for \(plan.label ?? "your home"). Tap a box when it’s done.").font(.subheadline).foregroundStyle(.secondary)
                    }
                    Picker("Section", selection: $group) {
                        ForEach(groups, id: \.0) { g in
                            let items = plan.checklist.filter { $0.group == g.0 }
                            Text("\(g.1) \(items.filter { $0.done ?? false }.count)/\(items.count)").tag(g.0)
                        }
                    }
                    .pickerStyle(.segmented)
                    ForEach(plan.checklist.filter { $0.group == group }) { t in TaskRow(task: t) }
                }
                .padding()
            }
            .background(Color(.systemGroupedBackground))
            .navigationTitle("Checklist")
        }
    }
}
