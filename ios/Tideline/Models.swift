import Foundation

// These match the JSON the Python server sends (backend/app.py).
// Keys arrive in snake_case and are converted to camelCase automatically.

struct Plan: Codable, Identifiable {
    let id: String
    var label: String?
    var address: String?
    let lat: Double
    let lon: Double
    let place: Place
    var language: String?
    var risk: Risk
    var summary: String?
    var checklist: [PlanTask]
    var progress: PlanProgress
    var alerts: [WeatherAlert]?
    var forecast: [ForecastPeriod]?
    var help: Help
    var enso: Enso?
    var missing: [String]?
    var translated: Bool?
}

struct Place: Codable {
    var county: String?
    var city: String?
    var state: String?
    var line: String { [city, county.map { "\($0) County" }, state].compactMap { $0 }.joined(separator: ", ") }
}

struct Risk: Codable {
    let score: Int
    let level: String          // high, elevated, lower
    let factors: [Factor]
    var kingTides: [TideWindow]?
}

struct Factor: Codable, Identifiable {
    var id: String { key }
    let key: String
    let points: Int
    let label: String
    let detail: String
    let source: String
}

struct TideWindow: Codable, Identifiable {
    var id: String { start }
    let start: String
    let end: String
    var active: Bool?
}

struct PlanTask: Codable, Identifiable {
    let id: String
    let group: String          // now, kit, storm
    var title: String
    var why: String
    let priority: Int
    var link: String?
    var done: Bool?
}

struct PlanProgress: Codable {
    var done: Int
    var total: Int
}

struct WeatherAlert: Codable, Identifiable {
    var id: String { event + (starts ?? "") }
    let event: String
    let headline: String?
    let kind: String
    let stormRelated: Bool?
    let starts: String?
    let description: String?
    let instruction: String?
}

struct ForecastPeriod: Codable, Identifiable {
    var id: String { (name ?? "") + (short ?? "") }
    let name: String?
    let short: String?
    let rainChance: Int?
}

struct Help: Codable {
    var alertSystem: AlertSystem?
    var county: [Resource]?
    var statewide: [Resource]?
    var sandbags: [SandbagSite]?
    var ai: AIHelp?
    var checked: String?
}

struct AlertSystem: Codable { let name: String; let url: String }

struct Resource: Codable, Identifiable {
    let id: String
    let name: String
    let what: String
    var url: String?
    var phone: String?
}

struct SandbagSite: Codable, Identifiable {
    let id: String
    let name: String
    let address: String
    let notes: String
    var phone: String?
    let source: String
    let lat: Double
    let lon: Double
    let miles: Double
}

struct AIHelp: Codable {
    let sites: [AISite]
    let sources: [Source]
}

struct AISite: Codable, Identifiable {
    var id: String { name }
    let name: String
    let address: String
    let notes: String
}

struct Source: Codable, Identifiable {
    var id: String { url }
    let title: String
    let url: String
}

struct Enso: Codable {
    let status: String
    let detail: String
    let events: [EnsoEvent]
}

struct EnsoEvent: Codable, Identifiable {
    var id: String { date }
    let date: String
    let text: String
    let source: String
    let url: String
}

struct PlanSummary: Codable, Identifiable {
    let id: String
    let label: String?
    let city: String?
    let state: String?
    let level: String
    let score: Int
}

struct StormReport: Codable, Identifiable {
    let id: String
    let kind: String
    let title: String
    let note: String?
    let severity: Int
    let lat: Double
    let lon: Double
    let confirmations: Int
    let hasPhoto: Int?
    let createdAt: String
}

struct PhotoAnalysis: Codable {
    let ai: Bool
    var kind: String?
    var title: String?
    var severity: Int?
    var advice: String?
}

struct News: Codable {
    var headline: String?
    var items: [NewsItem]
    var sources: [Source]
    var enso: Enso?
}

struct NewsItem: Codable, Identifiable {
    var id: String { title }
    let title: String
    let date: String?
    let summary: String
    let action: String?
}

struct Regions: Codable {
    let note: String
    let regions: [Region]
}

struct Region: Codable, Identifiable {
    let id: String
    let name: String
    let season: String
    let effect: String
    let impact: String
    let prepare: String
}

enum Household: String, CaseIterable, Identifiable {
    case kids, olderAdult = "older_adult", disability, medicalDevice = "medical_device", pets
    case noCar = "no_car", renter, livesAlone = "lives_alone", hillside
    var id: String { rawValue }
    var title: String {
        switch self {
        case .kids: "Kids"
        case .olderAdult: "Older adult (65+)"
        case .disability: "Disability or health need"
        case .medicalDevice: "Powered medical device"
        case .pets: "Pets"
        case .noCar: "No car"
        case .renter: "We rent"
        case .livesAlone: "Lives alone"
        case .hillside: "On a hillside"
        }
    }
    var symbol: String {
        switch self {
        case .kids: "figure.and.child.holdinghands"
        case .olderAdult: "figure.walk"
        case .disability: "figure.roll"
        case .medicalDevice: "bolt.heart"
        case .pets: "pawprint"
        case .noCar: "car.side"
        case .renter: "building.2"
        case .livesAlone: "person"
        case .hillside: "mountain.2"
        }
    }
}

let languages: [(code: String, name: String)] = [
    ("en", "English"), ("es", "Español"), ("ne", "नेपाली (Nepali)"), ("zh", "中文 (Chinese)"), ("tl", "Tagalog"),
    ("vi", "Tiếng Việt"), ("ko", "한국어 (Korean)"), ("hi", "हिन्दी (Hindi)"), ("ar", "العربية (Arabic)"), ("ru", "Русский"),
]
