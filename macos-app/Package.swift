// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "EyelashCodexBridge",
    platforms: [.macOS(.v13)],
    products: [
        .executable(name: "EyelashCodexBridge", targets: ["EyelashCodexBridge"])
    ],
    targets: [
        .executableTarget(name: "EyelashCodexBridge")
    ],
    swiftLanguageVersions: [.v5]
)
