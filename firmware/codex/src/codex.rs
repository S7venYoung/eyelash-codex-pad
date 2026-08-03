//! Codex Micro-compatible input layer.
//!
//! Hold the bottom-left `LT(1, KpEnter)` key to enter this layer. The other
//! fifteen switches emit Report ID 6 `v.oai.hid` notifications; layer 0 stays
//! an ordinary numpad so the device always has a recovery path.

use rmk::event::{KeyboardEvent, KeyboardEventPos, LayerChangeEvent};
use rmk::macros::processor;

#[processor(subscribe = [KeyboardEvent, LayerChangeEvent])]
pub struct CodexProcessor {
    layer: u8,
}

impl CodexProcessor {
    pub const fn new() -> Self {
        Self { layer: 0 }
    }

    async fn on_layer_change_event(&mut self, event: LayerChangeEvent) {
        self.layer = event.0;
    }

    async fn on_keyboard_event(&mut self, event: KeyboardEvent) {
        if self.layer != 1 {
            return;
        }

        let KeyboardEventPos::Key(pos) = event.pos else {
            return;
        };

        // Bottom-left (3,0) is the momentary layer key. The remaining fifteen
        // switches cover all six Agent keys, all seven Action keys, and both
        // virtual encoder directions.
        let key = match (pos.row, pos.col) {
            (0, 0) => "AG00",
            (0, 1) => "AG01",
            (0, 2) => "AG02",
            (0, 3) => "AG03",
            (1, 0) => "AG04",
            (1, 1) => "AG05",
            (1, 2) => "ACT06",
            (1, 3) => "ACT07",
            (2, 0) => "ACT08",
            (2, 1) => "ACT09",
            (2, 2) => "ACT10",
            (2, 3) => "ACT11",
            (3, 1) => "ACT12",
            (3, 2) => "ENC_CC",
            (3, 3) => "ENC_CW",
            _ => return,
        };

        // Encoder rotations are momentary ticks in the Codex protocol; unlike
        // physical keys they do not have a matching release notification.
        if key.starts_with("ENC_") && !event.pressed {
            return;
        }

        rmk::codex::send_key_event(key, event.pressed).await;
    }
}
