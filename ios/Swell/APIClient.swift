import Foundation

/// Talks to the Python server. Every request carries this phone's anonymous device id,
/// so each phone only ever sees its own plans.
struct APIError: LocalizedError {
    let message: String
    var errorDescription: String? { message }
}

final class APIClient {
    static let shared = APIClient()

    let deviceId: String = {
        let key = "swell.deviceId"
        if let id = UserDefaults.standard.string(forKey: key) { return id }
        let id = UUID().uuidString
        UserDefaults.standard.set(id, forKey: key)
        return id
    }()

    private let decoder: JSONDecoder = {
        let d = JSONDecoder()
        d.keyDecodingStrategy = .convertFromSnakeCase
        return d
    }()

    private func request(_ path: String, method: String = "GET", body: [String: Any]? = nil) async throws -> Data {
        guard let url = URL(string: path, relativeTo: Config.apiBase) else { throw APIError(message: "Bad address") }
        var req = URLRequest(url: url)
        req.httpMethod = method
        req.timeoutInterval = 45 // the free server can take a moment to wake up
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.setValue(deviceId, forHTTPHeaderField: "X-Device-Id")
        if let body { req.httpBody = try JSONSerialization.data(withJSONObject: body) }
        let (data, resp) = try await URLSession.shared.data(for: req)
        let status = (resp as? HTTPURLResponse)?.statusCode ?? 0
        if status >= 400 {
            let msg = (try? JSONSerialization.jsonObject(with: data) as? [String: Any])?["error"] as? String
            throw APIError(message: msg ?? "Server error (\(status))")
        }
        return data
    }

    func get<T: Decodable>(_ path: String) async throws -> T {
        try decoder.decode(T.self, from: try await request(path))
    }

    func post<T: Decodable>(_ path: String, _ body: [String: Any]) async throws -> T {
        try decoder.decode(T.self, from: try await request(path, method: "POST", body: body))
    }

    // MARK: endpoints

    func buildPlan(address: String, label: String, language: String, household: Set<Household>) async throws -> Plan {
        var hh: [String: Bool] = [:]
        for h in Household.allCases { hh[h.rawValue] = household.contains(h) }
        return try await post("/api/plan", ["address": address, "label": label, "language": language, "household": hh])
    }

    func plan(_ id: String) async throws -> Plan { try await get("/api/plan/\(id)") }
    func plans() async throws -> [PlanSummary] { try await get("/api/plans") }

    func setDone(plan: String, item: String, done: Bool) async throws {
        _ = try await request("/api/plan/\(plan)/check", method: "POST", body: ["item_id": item, "done": done])
    }

    func reports(lat: Double, lon: Double) async throws -> [StormReport] {
        try await get("/api/reports?lat=\(lat)&lon=\(lon)&miles=10")
    }

    func analyze(photo: String) async throws -> PhotoAnalysis {
        try await post("/api/reports/analyze", ["photo": photo])
    }

    func postReport(lat: Double, lon: Double, kind: String, title: String, severity: Int, photo: String?, aiChecked: Bool, county: String?) async throws {
        var body: [String: Any] = ["lat": lat, "lon": lon, "kind": kind, "title": title, "severity": severity, "ai_checked": aiChecked]
        if let photo { body["photo"] = photo }
        if let county { body["county"] = county }
        _ = try await request("/api/reports", method: "POST", body: body)
    }

    func confirm(report: String) async throws {
        _ = try await request("/api/reports/\(report)/confirm", method: "POST")
    }

    func news(county: String, state: String, lang: String) async throws -> News {
        let c = county.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? ""
        return try await get("/api/news?county=\(c)&state=\(state)&lang=\(lang)")
    }

    func regions() async throws -> Regions { try await get("/api/regions") }
}
