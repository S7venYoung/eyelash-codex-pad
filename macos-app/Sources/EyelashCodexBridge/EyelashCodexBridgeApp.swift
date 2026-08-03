import AppKit
import IOKit.hid
import ServiceManagement
import SwiftUI

struct PadEvent: Identifiable {
    let id = UUID()
    let key: String
    let pressed: Bool
    let source: String
    let timestamp: Date
}

enum KeyboardActionMap {
    static let shiftMask: UInt8 = 0x02 | 0x20

    static func action(usage: UInt8, modifiers: UInt8) -> String? {
        let shifted = modifiers & shiftMask != 0
        if shifted {
            switch usage {
            case 0x68: return "ACT12"  // Shift + F13
            case 0x69: return "ENC_CC" // Shift + F14
            case 0x6A: return "ENC_CW" // Shift + F15
            default: return nil
            }
        }

        let actions = [
            "AG00", "AG01", "AG02", "AG03", "AG04", "AG05",
            "ACT06", "ACT07", "ACT08", "ACT09", "ACT10", "ACT11",
        ]
        let index = Int(usage) - 0x68 // HID keyboard usages F13 ... F24
        guard actions.indices.contains(index) else { return nil }
        return actions[index]
    }
}

final class BridgeModel: ObservableObject {
    @Published var connected = false
    @Published var productName = "Eyelash Codex Pad"
    @Published var events: [PadEvent] = []
    @Published var lastError: String?
    @Published var inputMode = "等待输入"

    private let manager: IOHIDManager
    private let reportBuffer = UnsafeMutablePointer<UInt8>.allocate(capacity: 64)
    private var keyboardPressed: [UInt8: String] = [:]
    private var keyboardModifiers: UInt8 = 0

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
        IOHIDManagerRegisterInputValueCallback(manager, { context, result, _, value in
            guard let context, result == kIOReturnSuccess else { return }
            let model = Unmanaged<BridgeModel>.fromOpaque(context).takeUnretainedValue()
            model.receiveKeyboardValue(value)
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
                self.inputMode = "Vendor HID"
                self.publish(key: key, pressed: action != 0, source: "Vendor HID")
            }
        } catch {
            DispatchQueue.main.async { self.lastError = "无法解析设备事件：\(error.localizedDescription)" }
        }
    }

    private func receiveKeyboardValue(_ value: IOHIDValue) {
        let element = IOHIDValueGetElement(value)
        guard IOHIDElementGetUsagePage(element) == 0x07 else { return }
        let usage = UInt8(truncatingIfNeeded: IOHIDElementGetUsage(element))
        let pressed = IOHIDValueGetIntegerValue(value) != 0

        // Keyboard usages E1/E5 are left/right Shift. Vial macros send these
        // as ordinary HID element changes, independently of the F-key value.
        if usage == 0xE1 || usage == 0xE5 {
            let mask: UInt8 = usage == 0xE1 ? 0x02 : 0x20
            if pressed {
                keyboardModifiers |= mask
            } else {
                keyboardModifiers &= ~mask
            }
            return
        }

        guard (0x68...0x73).contains(usage) else { return }
        if pressed {
            guard keyboardPressed[usage] == nil,
                  let action = KeyboardActionMap.action(
                    usage: usage,
                    modifiers: keyboardModifiers
                  ) else { return }
            keyboardPressed[usage] = action
            DispatchQueue.main.async {
                self.inputMode = "Vial 键盘"
                self.publish(key: action, pressed: true, source: "Vial")
            }
        } else if let action = keyboardPressed.removeValue(forKey: usage) {
            // Encoder turns are protocol ticks and intentionally have no release.
            if !action.hasPrefix("ENC_") {
                DispatchQueue.main.async {
                    self.inputMode = "Vial 键盘"
                    self.publish(key: action, pressed: false, source: "Vial")
                }
            }
        }
    }

    private func publish(key: String, pressed: Bool, source: String) {
        let event = PadEvent(key: key, pressed: pressed, source: source, timestamp: Date())
        events.insert(event, at: 0)
        if events.count > 20 { events.removeLast() }
        DistributedNotificationCenter.default().postNotificationName(
            Notification.Name("com.s7venyoung.eyelash-codex-bridge.event"),
            object: nil,
            userInfo: ["key": key, "pressed": pressed, "source": source],
            deliverImmediately: true
        )
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
                    Text("输入：\(model.inputMode)")
                        .font(.caption2)
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
                        Text(event.source)
                            .font(.caption2)
                            .foregroundStyle(.secondary)
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
