import SwiftUI

struct OnboardingView: View {
    @Environment(AppStore.self) private var store
    @State private var step = 1
    @State private var address = ""
    @State private var label = ""
    @State private var household = Set<Household>()
    @State private var role: Role = .household
    @State private var grows = Set<FarmGrow>()
    @State private var workers = false
    @State private var creek = false
    @State private var building = false
    @State private var buildStep = 0
    @State private var errorText: String?

    private var buildSteps: [(String, String)] {
        let world = !looksUS
        if world {
            return [
                ("Finding the place", "OpenStreetMap"),
                ("Checking what El Niño means here", "NOAA Climate Prediction Center"),
                ("Looking up local help", "National disaster and farm agencies"),
                ("Writing your checklist", role == .farmer ? "Made for your farm" : "Made for your household"),
            ]
        }
        return [
        ("Finding your address", "U.S. Census Geocoder"),
        ("Checking the official flood map", "FEMA National Flood Hazard Layer"),
        ("Measuring how high your ground is", "USGS elevation data"),
        ("Checking live weather alerts", "National Weather Service"),
        ("Finding sandbags and help nearby", "County and city sources"),
        ("Writing your checklist", role == .farmer ? "Made for your farm" : "Made for your household"),
        ]
    }

    /// A rough guess so the "building" screen names the right sources. The server decides for real.
    private var looksUS: Bool {
        let a = address.lowercased()
        let other = ["nepal", "india", "bangladesh", "pakistan", "sri lanka", "peru", "ecuador", "philippines", "indonesia", "australia", "mexico", "kenya"]
        return !other.contains { a.contains($0) }
    }

    var body: some View {
        Group {
        if building { buildingView } else {
            switch step {
            case 1: welcome
            case 2: roleView
            case 3: whereView
            case 4: farmView
            default: whoView
            }
        }
        }
        .onAppear { if store.addingPlace { step = 2; address = ""; label = ""; household = []; grows = [] } }
    }

    // MARK: step 1
    private var welcome: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 12) {
                    Label(Config.appName, systemImage: "water.waves").font(.headline).foregroundStyle(.white)
                    Text("A strong El Niño is coming. Let’s get you ready.")
                        .font(.system(size: 32, weight: .heavy, design: .rounded)).foregroundStyle(.white)
                    Text("Floods in California, drought in Nepal. Get a plan made for your home or farm, in your language, and find people who can help.")
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

    // MARK: role
    private var roleView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    Button("← Back") { if store.addingPlace && store.plan != nil { store.addingPlace = false } else { step = 1 } }
                    Spacer()
                    Text("Step 1 of \(totalSteps)").font(.footnote.bold()).foregroundStyle(.secondary)
                }
                Text("Who is this plan for?").font(.system(size: 28, weight: .heavy, design: .rounded))
                Text("El Niño hits homes and farms differently. Your plan changes with your answer.").foregroundStyle(.secondary)
                roleCard(.household, "My home and family", "Flooding, power outages, getting out safely, and help for the people you live with.", "house.fill")
                roleCard(.farmer, "My farm or ranch", "Protect crops, animals, water and income, and find farm aid programs.", "leaf.fill")
            }
            .padding()
        }
    }

    private var totalSteps: Int { role == .farmer ? 4 : 3 }

    private func roleCard(_ r: Role, _ title: String, _ text: String, _ symbol: String) -> some View {
        Button { role = r; step = 3 } label: {
            HStack(alignment: .top, spacing: 14) {
                Image(systemName: symbol).font(.title).foregroundStyle(Theme.sea).frame(width: 40)
                VStack(alignment: .leading, spacing: 4) {
                    Text(title).font(.headline).foregroundStyle(.primary)
                    Text(text).font(.subheadline).foregroundStyle(.secondary).multilineTextAlignment(.leading)
                }
                Spacer()
                Image(systemName: "chevron.right").foregroundStyle(.tertiary)
            }
            .padding(16)
            .background(role == r ? Theme.sea.opacity(0.1) : Color.clear, in: RoundedRectangle(cornerRadius: 16))
            .overlay(RoundedRectangle(cornerRadius: 16).stroke(role == r ? Theme.sea : Color.secondary.opacity(0.3), lineWidth: role == r ? 2 : 1))
        }
        .buttonStyle(.plain)
    }

    // MARK: farm
    private var farmView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    Button("← Back") { step = 3 }
                    Spacer()
                    Text("Step 3 of 4").font(.footnote.bold()).foregroundStyle(.secondary)
                }
                Text("About your farm").font(.system(size: 28, weight: .heavy, design: .rounded))
                Text("What do you grow or raise?").foregroundStyle(.secondary)
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                    ForEach(FarmGrow.allCases) { g in
                        chip(on: grows.contains(g), title: g.title, symbol: g.symbol) {
                            if grows.contains(g) { grows.remove(g) } else { grows.insert(g) }
                        }
                    }
                }
                Toggle("People work on the farm with us", isOn: $workers)
                Toggle("There is a creek, river or canal nearby", isOn: $creek)
                Button { step = 5 } label: { Text("Continue").frame(maxWidth: .infinity) }
                    .buttonStyle(.borderedProminent).controlSize(.large)
            }
            .padding()
        }
    }

    private func chip(on: Bool, title: String, symbol: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 8) {
                Image(systemName: symbol).font(.title2).foregroundStyle(Theme.sea)
                Text(title).font(.subheadline.bold()).foregroundStyle(.primary).multilineTextAlignment(.leading)
            }
            .frame(maxWidth: .infinity, minHeight: 74, alignment: .leading)
            .padding(12)
            .background(on ? Theme.sea.opacity(0.12) : Color.clear, in: RoundedRectangle(cornerRadius: 14))
            .overlay(RoundedRectangle(cornerRadius: 14).stroke(on ? Theme.sea : Color.secondary.opacity(0.3), lineWidth: on ? 2 : 1))
        }
        .accessibilityAddTraits(on ? .isSelected : [])
    }

    // MARK: address
    private var whereView: some View {
        NavigationStack { whereForm }
    }

    private var whereForm: some View {
        Form {
            Section {
                TextField(role == .farmer ? "e.g. Bharatpur, Chitwan, Nepal" : "e.g. 100 Murchison Dr, Millbrae, CA", text: $address)
                    .textContentType(.fullStreetAddress)
                    .autocorrectionDisabled()
            } header: { Text(role == .farmer ? "Farm address or village" : "Home address") } footer: {
                Text("In the U.S., we check the official flood map, ground height and live weather alerts for this exact spot. Anywhere else, we plan for what El Niño brings to that region, like drought in Nepal.")
            }
            Section {
                TextField(role == .farmer ? "Farm" : "Home", text: $label)
            } header: { Text("Name this place (optional)") } footer: {
                Text("Making a plan for family far away? Use their address and call it “Grandma’s farm.”")
            }
            if let errorText { Text(errorText).foregroundStyle(.red) }
            Button("Continue") {
                if address.trimmingCharacters(in: .whitespaces).count < 5 { errorText = "Type the full address or village, with the city or district." } else { errorText = nil; step = role == .farmer ? 4 : 5 }
            }
            .bold()
        }
        .navigationTitle("Where do you live?")
        .safeAreaInset(edge: .top) {
            HStack {
                Button("← Back") { step = 2 }
                Spacer()
                Text("Step 2 of \(totalSteps)").font(.footnote.bold()).foregroundStyle(.secondary)
            }
            .padding(.horizontal).padding(.top, 8)
        }
    }

    // MARK: step 3
    private var whoView: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    Button("← Back") { step = role == .farmer ? 4 : 3 }
                    Spacer()
                    Text("Step \(totalSteps) of \(totalSteps)").font(.footnote.bold()).foregroundStyle(.secondary)
                }
                Text(role == .farmer ? "Who lives on the farm?" : "Who lives here?").font(.system(size: 28, weight: .heavy, design: .rounded))
                Text("Pick everything that fits. It changes what goes on your checklist.").foregroundStyle(.secondary)
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                    ForEach(Household.allCases) { h in
                        chip(on: household.contains(h), title: h.title, symbol: h.symbol) {
                            if household.contains(h) { household.remove(h) } else { household.insert(h) }
                        }
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
            try await store.build(address: address, label: label.isEmpty ? (role == .farmer ? "Farm" : "Home") : label,
                                  household: household, role: role, grows: grows, workers: workers, creek: creek)
            ticker.cancel()
        } catch {
            ticker.cancel()
            building = false
            step = 3
            errorText = error.localizedDescription
        }
    }
}
