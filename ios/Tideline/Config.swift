import Foundation

enum Config {
    /// The Python server. After deploying on Render, paste its address here.
    /// For the iPhone Simulator with the server running on your Mac, use "http://localhost:5000".
    static let apiBase = URL(string: "https://tideline.onrender.com")!
    static let appName = "Tideline"
}
