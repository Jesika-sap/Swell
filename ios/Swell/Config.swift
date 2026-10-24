import Foundation

enum Config {
    /// The Python server.
    /// Running the server on this Mac (Terminal: `PORT=5050 python3 app.py`) and using the Simulator: keep "http://localhost:5050".
    /// After putting the server online (for example on Render), paste that address here instead.
    static let apiBase = URL(string: "http://localhost:5050")!
    static let appName = "Swell"
}
