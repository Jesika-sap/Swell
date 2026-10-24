import SwiftUI

struct OnboardingView: View {
    @Environment(AppStore.self) private var store
    @State private var step = 1
    @State private var address = ""
    @State private var label = ""
    @State private var household = Set<Household>()
    @State private var building = false
    @State private var buildStep = 0
    @State private var errorText: String?

    private let buildSteps = [
        ("Finding your address", "U.S. Census Geocoder"),
        ("Checking the official flood map", "FEMA National Flood Hazard Layer"),
        ("Measuring how high your ground is", "USGS elevation data"),
        ("Checking live weather alerts", "National Weather Service"),
        ("Finding sandbags and help nearby", "County and city sources"),
        ("Writing your checklist", "Made for your household"),
    ]

    var body: some View {
        Group {
        if building { buildingView } else {
            switch step {
            case 1: welcome
            case 2: whereView
            default: whoView
            }
        }
        }
        .onAppear { if store.addingPlace { step = 2; address = ""; label = ""; household = [] } }
    }

    // MARK: step 1
    private var welcome: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 12) {
                    Label(Config.appName, systemImage: "water.waves").font(.headline).foregroundStyle(.white)
                    Text("A strong El Niño is coming. Let’s get your home ready.")
                        .font(.system(size: 32, weight: .heavy, design: .rounded)).foregroundStyle(.white)
                    Text("See your home’s storm risk, get a checklist made for your family, in your language, and find help nearby.")
                        .foregroundStyle(.white.opacity(0.85))
                }
                .padding(22)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(LinearGradient(colors: [Theme.ocean, Theme.ocean2], startPoint: .top, endPoint: .bottom), in: RoundedRectangle(cornerRadius: 24))

                fact("83%+", "chance of a strong to very strong El Niño this winter", "NOAA, Oct 2026")
                fact("1–2 ft", "higher ocean levels than tide tables predict in San Mateo County", "San Mateo County, Oct 2026")
                fact("2", "emergencies declared: California (Sept 21) and San Mateo County (Oct 20)", "State of California · San Mateo County")

                Text("Language for your plan").font(.subheadline.bold())
                Picker("Language", selection: Binding(get: { store.language }, set: { store.setLanguage($0) })) {
                    ForEach(languages, id: \.code) { Text($0.name).tag($0.code) }
                }
                .pickerStyle(.menu)

                Button { step = 2 } label: { Text("Get started").frame(maxWidth: .infinity) }
                    .buttonStyle(.borderedProminent).controlSize(.large)
                Text("No account needed. Your plan is linked to this phone only.")
                    .font(.footnote).foregroundStyle(.secondary).frame(maxWidth: .infinity)
            }
            .padding()
        }
    }

    private func fact(_ big: String, _ text: String, _ source: String) -> some View {
        HStack(spacing: 14) {
            Text(big).font(.system(size: 26, weight: .heavy, design: .rounded)).foregroundStyle(Theme.sea).frame(minWidth: 70, alignment: .leading)
            VStack(alignment: .leading, spacing: 2) {
                Text(text).font(.subheadline)
                Text(source).font(.caption).foregroundStyle(.secondary)
            }
        }
        .padding(14)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.background, in: RoundedRectangle(cornerRadius: 16))
        .overlay(RoundedRectangle(cornerRadius: 16).stroke(.quaternary))
    }

    // MARK: step 2
    private var whereView: some View {
        NavigationStack { whereForm }
    }

    private var whereForm: some View {
        Form {
            Section {
                TextField("e.g. 100 Murchison Dr, Millbrae, CA", text: $address)
                    .textContentType(.fullStreetAddress)
                    .autocorrectionDisabled()
            } header: { Text("Home address") } footer: {
                Text("We check the official flood map, ground height and live weather alerts for this exact spot.")
            }
            Section {
                TextField("Home", text: $label)
            } header: { Text("Name this place (optional)") } footer: {
                Text("Making a plan for a grandparent? Use their address and call it “Grandma’s house.”")
            }
            if let errorText { Text(errorText).foregroundStyle(.red) }
            Button("Continue") {
                if address.trimmingCharacters(in: .whitespaces).count < 5 { errorText = "Type your full address, with the city." } else { errorText = nil; step = 3 }
            }
            .bold()
        }
        .navigationTitle("Where do you live?")
        .safeAreaInset(edge: .top) {
            HStack {
                Button("← Back") { if store.addingPlace && store.plan != nil { store.addingPlace = false } else { step = 1 } }
                Spacer()
                Text("Step 1 of 2").font(.footnote.bold()).foregroundStyle(.secondary)
            }
            .padding(.horizontal).padding(.top, 8)
        }
    }

    // MARK: step 3
    private var whoView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    Button("← Back") { step = 2 }
                    Spacer()
                    Text("Step 2 of 2").font(.footnote.bold()).foregroundStyle(.secondary)
                }
                Text("Who lives here?").font(.system(size: 28, weight: .heavy, design: .rounded))
                Text("Pick everything that fits. It changes what goes on your checklist.").foregroundStyle(.secondary)
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                    ForEach(Household.allCases) { h in
                        let on = household.contains(h)
                        Button {
                            if on { household.remove(h) } else { household.insert(h) }
                        } label: {
                            VStack(alignment: .leading, spacing: 8) {
                                Image(systemName: h.symbol).font(.title2).foregroundStyle(Theme.sea)
                                Text(h.title).font(.subheadline.bold()).foregroundStyle(.primary).multilineTextAlignment(.leading)
                            }
                            .frame(maxWidth: .infinity, minHeight: 74, alignment: .leading)
                            .padding(12)
                            .background(on ? Theme.sea.opacity(0.12) : Color.clear, in: RoundedRectangle(cornerRadius: 14))
                            .overlay(RoundedRectangle(cornerRadius: 14).stroke(on ? Theme.sea : Color.secondary.opacity(0.3), lineWidth: on ? 2 : 1))
                        }
                        .accessibilityAddTraits(on ? .isSelected : [])
                    }
                }
                if let errorText { Text(errorText).foregroundStyle(.red) }
                Button { Task { await build() } } label: { Text("Build my plan").frame(maxWidth: .infinity) }
                    .buttonStyle(.borderedProminent).controlSize(.large)
            }
            .padding()
        }
    }

    // MARK: building
    private var buildingView: some View {
        VStack(spacing: 22) {
            ProgressView().controlSize(.large).tint(Theme.sea)
            Text("Building your plan").font(.title2.bold())
            VStack(alignment: .leading, spacing: 12) {
                ForEach(Array(buildSteps.enumerated()), id: \.offset) { i, s in
                    HStack(alignment: .top, spacing: 10) {
                        Image(systemName: i < buildStep ? "checkmark.circle.fill" : "circle")
                            .foregroundStyle(i < buildStep ? Theme.sea : .secondary)
                        VStack(alignment: .leading) {
                            Text(s.0)
                            Text(s.1).font(.caption).foregroundStyle(.secondary)
                        }
                    }
                    .foregroundStyle(i < buildStep ? .primary : .secondary)
                }
            }
        }
        .padding(30)
    }

    private func build() async {
        building = true
        buildStep = 0
        let ticker = Task {
            while !Task.isCancelled && buildStep < buildSteps.count - 1 {
                try? await Task.sleep(for: .milliseconds(650))
                buildStep += 1
            }
        }
        do {
            try await store.build(address: address, label: label.isEmpty ? "Home" : label, household: household)
            ticker.cancel()
        } catch {
            ticker.cancel()
            building = false
            step = 2
            errorText = error.localizedDescription
        }
    }
}
