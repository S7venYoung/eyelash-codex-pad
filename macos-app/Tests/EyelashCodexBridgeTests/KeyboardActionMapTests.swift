import XCTest
@testable import EyelashCodexBridge

final class KeyboardActionMapTests: XCTestCase {
    func testF13ThroughF24() {
        let expected = [
            "AG00", "AG01", "AG02", "AG03", "AG04", "AG05",
            "ACT06", "ACT07", "ACT08", "ACT09", "ACT10", "ACT11",
        ]
        for (index, action) in expected.enumerated() {
            XCTAssertEqual(
                KeyboardActionMap.action(usage: UInt8(0x68 + index), modifiers: 0),
                action
            )
        }
    }

    func testShiftedMacroKeys() {
        XCTAssertEqual(KeyboardActionMap.action(usage: 0x68, modifiers: 0x02), "ACT12")
        XCTAssertEqual(KeyboardActionMap.action(usage: 0x69, modifiers: 0x20), "ENC_CC")
        XCTAssertEqual(KeyboardActionMap.action(usage: 0x6A, modifiers: 0x02), "ENC_CW")
        XCTAssertNil(KeyboardActionMap.action(usage: 0x6B, modifiers: 0x02))
    }
}
