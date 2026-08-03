import AppKit
import IOKit.hid
import ServiceManagement
import SwiftUI

struct PadEvent: Identifiable {
    let id = UUID()
    let key: String
    let pressed: Bool
    let timestamp: Date
}

final class BridgeModel: ObservableObject {
    @Published var connected = false
    @Published var productName = "Eyelash Codex Pad"
    @Published var events: [PadEvent] = []
    @Published var lastError: String?

    private let manager: IOHIDManager
    private let reportBuffer = UnsafeMutablePointer<UInt8>.allocate(capacity: 64)

    init() {
        manager = IOHIDManagerCreate(kCFAllocatorDefault, IOOptionBits(kIOHIDOptionsTypeNone))
        reportBuffer.initialize(repeating: 0, count: 64)

        let devices: [[String: Int]] = [
            [
                kIOHIDVendorIDKey as String: 0x4C4B,
                kIOHIDProductIDKey as String: 0x4643,
            ],
            [
                kIOHIDVendorIDKey as String: 0x303A,
                kIOHIDProductIDKey as String: 0x8360,
            ],
        ]
        IOHIDManagerSetDeviceMatchingMultiple(manager, devices as CFArray)

        let context = Unmanaged.passUnretained(self).toOpaque()
        IOHIDManagerRegisterDeviceMatchingCallback(manager, { context, _, _, device in
            guard let context else { return }
            let model = Unmanaged<BridgeModel>.fromOpaque(context).takeUnretainedValue()
            model.attach(device)
        }, context)
        IOHIDManagerRegisterDeviceRemovalCallback(manager, { context, _, _, _ in
            guard let context else { return }
            let model = Unmanaged<BridgeModel>.fromOpaque(context).takeUnretainedValue()
            DispatchQueue.main.async {
                model.connected = false
            }
        }, context)

        IOHIDManagerScheduleWithRunLoop(manager, CFRunLoopGetMain(), CFRunLoopMode.defaultMode.rawValue)
        let result = IOHIDManagerOpen(manager, IOOptionBits(kIOHIDOptionsTypeNone))
        if result != kIOReturnSuccess {
            lastError = String(format: "无法打开 HID 管理器：0x%08X", result)
        }
    }

    deinit {
        IOHIDManagerUnscheduleFromRunLoop(manager, CFRunLoopGetMain(), CFRunLoopMode.defaultMode.rawValue)
        IOHIDManagerClose(manager, IOOptionBits(kIOHIDOptionsTypeNone))
        reportBuffer.deinitialize(count: 64)
        reportBuffer.deallocate()
    }

    private func attach(_ device: IOHIDDevice) {
        if let name = IOHIDDeviceGetProperty(device, kIOHIDProductKey as CFString) as? String {
            productName = name
        }
        connected = true
        lastError = nil

        IOHIDDeviceRegisterInputReportCallback(
            device,
            reportBuffer,
            64,
            { context, result, _, _, reportID, report, reportLength in
                guard let context else { return }
                let model = Unmanaged<BridgeModel>.fromOpaque(context).takeUnretainedValue()
                guard result == kIOReturnSuccess else {
                    DispatchQueue.main.async {
                        model.lastError = String(format: "读取 HID 报告失败：0x%08X", result)
                    }
                    return
                }
                model.receive(reportID: reportID, bytes: report, count: reportLength)
            },
            Unmanaged.passUnretained(self).toOpaque()
        )
    }

    private func receive(reportID: UInt32, bytes: UnsafeMutablePointer<UInt8>, count: CFIndex) {
        guard reportID == 6, count >= 3 else { return }
        let data = Data(bytes: bytes, count: count)
        var offset = 0
        if data.first == 6 { offset = 1 }
        guard data.count > offset + 2, data[offset] == 0x02 else { return }

        let length = Int(data[offset + 1])
        let start = offset + 2
        guard length > 0, start + length <= data.count else { return }
        let payload = data.subdata(in: start..<(start + length))

        do {
            guard
                let object = try JSONSerialization.jsonObject(with: payload) as? [String: Any],
                object["m"] as? String == "v.oai.hid",
                let params = object["p"] as? [String: Any],
                let key = params["k"] as? String,
                let action = params["act"] as? Int
            else { return }

            DispatchQueue.main.async {
                let event = PadEvent(key: key, pressed: action != 0, timestamp: Date())
                self.events.insert(event, at: 0)
                if self.events.count > 20 { self.events.removeLast() }
                DistributedNotificationCenter.default().postNotificationName(
                    Notification.Name("com.s7venyoung.eyelash-codex-bridge.event"),
                    object: nil,
                    userInfo: ["key": key, "pressed": action != 0],
                    deliverImmediately: true
                )
            }
        } catch {
            DispatchQueue.main.async { self.lastError = "无法解析设备事件：\(error.localizedDescription)" }
        }
    }

    func clearEvents() {
        events.removeAll()
    }
}

struct BridgeMenu: View {
    @ObservedObject var model: BridgeModel
    @State private var launchAtLogin = SMAppService.mainApp.status == .enabled

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Circle()
                    .fill(model.connected ? Color.green : Color.orange)
                    .frame(width: 10, height: 10)
                VStack(alignment: .leading) {
                    Text(model.connected ? "Pad 已连接" : "等待 Pad")
                        .font(.headline)
                    Text(model.productName)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
            }

            if let error = model.lastError {
                Text(error).font(.caption).foregroundStyle(.red)
            }

            Divider()
            Text("最近事件").font(.subheadline).fontWeight(.semibold)

            if model.events.isEmpty {
                Text("按下 Codex 层按键后，事件会显示在这里。")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            } else {
                ForEach(model.events.prefix(8)) { event in
                    HStack {
                        Text(event.key).font(.system(.body, design: .monospaced))
                        Spacer()
                        Text(event.pressed ? "按下" : "松开")
                            .foregroundColor(event.pressed ? .primary : .secondary)
                        Text(event.timestamp, style: .time)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
            }

            Divider()
            Toggle("登录时启动", isOn: Binding(
                get: { launchAtLogin },
                set: { enabled in
                    do {
                        if enabled {
                            try SMAppService.mainApp.register()
                        } else {
                            try SMAppService.mainApp.unregister()
                        }
                        launchAtLogin = enabled
                    } catch {
                        model.lastError = "无法修改登录项：\(error.localizedDescription)"
                    }
                }
            ))

            HStack {
                Button("清除记录") { model.clearEvents() }
                Button("输入监控设置") {
                    NSWorkspace.shared.open(URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_ListenEvent")!)
                }
                Spacer()
                Button("退出") { NSApplication.shared.terminate(nil) }
            }
        }
        .padding(14)
        .frame(width: 390)
    }
}

@main
struct EyelashCodexBridgeApp: App {
    @StateObject private var model = BridgeModel()

    var body: some Scene {
        MenuBarExtra {
            BridgeMenu(model: model)
        } label: {
            Image(systemName: model.connected ? "keyboard.badge.ellipsis" : "keyboard")
        }
        .menuBarExtraStyle(.window)
    }
}
