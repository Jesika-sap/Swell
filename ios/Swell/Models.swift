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
    var role: String?
    var farm: Farm?

    var isFarm: Bool { role == "farmer" }
    var isDrought: Bool { risk.hazard == "drought" }
    var inUS: Bool { (place.country ?? "US") == "US" }
}

struct Farm: Codable {
    var grows: [String]
    var workers: Bool
    var creek: Bool
}

struct Place: Codable {
    var county: String?
    var city: String?
    var state: String?
    var country: String?
    var line: String {
        let c = (country ?? "US") == "US" ? nil : country
        return [city, county.map { c == nil ? "\($0) County" : $0 }, state, c].compactMap { $0 }.joined(separator: ", ")
    }
}

struct Risk: Codable {
    let score: Int
    let level: String          // high, elevated, lower
    let factors: [Factor]
    var kingTides: [TideWindow]?
    var hazard: String?        // flood or drought
    var region: RegionInfo?
}

struct RegionInfo: Codable {
    let id: String
    let name: String
    let effect: String
    let season: String
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
    var source: String?        // "scan" when AI Scan added it
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
    var country: [Resource]?
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
    var kindLabel: String?
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

// MARK: AI Scan

struct ScanResult: Codable {
    let seen: String
    let added: [PlanTask]
    let good: [String]?
    let nextPhoto: String?  // "next_photo" (the decoder converts snake_case)
    let plan: Plan
}

// MARK: organizations and help requests

/// Kinds of help, in the same order and with the same ids as the server's SERVICES.
let services: [(id: String, name: String, symbol: String)] = [
    ("sandbags", "Sandbags or sandbagging help", "square.stack.3d.up"),
    ("rides", "Rides or help leaving", "car"),
    ("checks", "Check-in calls and visits", "phone"),
    ("shelter", "A place to stay", "house"),
    ("food", "Food and water", "drop"),
    ("translation", "Translation", "character.bubble"),
    ("farm", "Help on farms (animals, equipment)", "leaf"),
    ("cleanup", "Volunteers for cleanup", "person.3"),
    ("supplies", "Supplies (batteries, tarps, masks)", "shippingbox"),
]

struct Org: Codable, Identifiable {
    let id: String
    let name: String
    var about: String?
    var area: String?
    var email: String?
    var phone: String?
    var website: String?
    let radiusMiles: Double
    let services: [String]
    let verified: Bool
    let example: Bool
    var miles: Double?
}

struct HelpRequest: Codable, Identifiable {
    let id: String
    let need: String
    let needLabel: String
    var details: String?
    let status: String         // open, accepted, done
    var org: Org?
    let createdAt: String
}

struct OrgRequest: Codable, Identifiable {
    let id: String
    let need: String
    let needLabel: String
    var details: String?
    let status: String
    var area: String?
    var contact: String?
    let mine: Bool
    let createdAt: String
}

struct OrgDashboard: Codable {
    let org: Org
    let requests: [OrgRequest]
    let helped: Int
}

struct NewOrg: Codable {
    let org: Org
    let key: String
}

enum Role: String, CaseIterable, Identifiable {
    case household, farmer
    var id: String { rawValue }
}

enum FarmGrow: String, CaseIterable, Identifiable {
    case vegetables, field, orchard, livestock, nursery
    var id: String { rawValue }
    var title: String {
        switch self {
        case .vegetables: "Vegetables"
        case .field: "Rice, wheat or field crops"
        case .orchard: "Fruit trees or vines"
        case .livestock: "Animals"
        case .nursery: "Greenhouse or nursery"
        }
    }
    var symbol: String {
        switch self {
        case .vegetables: "carrot"
        case .field: "laurel.leading"
        case .orchard: "tree"
        case .livestock: "hare"
        case .nursery: "house.lodge"
        }
    }
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


// MARK: accounts and communities

struct Account: Codable, Equatable {
    let id: String
    let name: String
    let email: String
}

struct AccountReply: Codable {
    let account: Account?
    let deviceId: String?
}

struct CommunitySummary: Codable, Identifiable, Hashable {
    let id: String
    let kind: String          // county, city, family
    let name: String
    let members: Int
    let maxMembers: Int?
    let owner: Bool
}

struct SuggestedCommunity: Codable, Identifiable {
    let key: String
    let kind: String
    let name: String
    var id: String { key }
}

struct CommunityList: Codable {
    let account: Account?
    let mine: [CommunitySummary]
    let suggested: [SuggestedCommunity]
    let familyMax: Int
}

struct MemberPlace: Codable, Hashable {
    let label: String?
    let city: String?
    let level: String
    let score: Int
    let done: Int
    let total: Int
}

struct Member: Codable, Identifiable {
    let name: String
    let role: String
    let you: Bool
    let safeAt: String?
    let places: [MemberPlace]
    var id: String { name + role + (safeAt ?? "") }
}

struct CommunityDetail: Codable {
    let id: String
    let kind: String
    let name: String
    let members: Int
    let maxMembers: Int?
    let owner: Bool
    let inviteCode: String?
    let people: [Member]?
    let reports: [StormReport]
    let center: Coord?
    let places: [FamilyPin]?
}

struct Coord: Codable {
    let lat: Double
    let lon: Double
}

/// Roughly where a family member's place is (rounded to about 1 km).
struct FamilyPin: Codable, Identifiable {
    let who: String
    let label: String
    let lat: Double
    let lon: Double
    var id: String { "\(who)-\(label)-\(lat)-\(lon)" }
}

enum CommunityKind {
    static func label(_ kind: String) -> String {
        switch kind {
        case "county": return "County"
        case "city": return "City"
        default: return "Private family group"
        }
    }

    static func symbol(_ kind: String) -> String {
        switch kind {
        case "county": return "mountain.2"
        case "city": return "building.2"
        default: return "person.3"
        }
    }
}
