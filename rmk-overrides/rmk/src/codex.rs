//! Minimal Codex Micro vendor-HID notification support.

use core::fmt::Write;

use heapless::String;

use crate::channel::send_hid_report;
use crate::hid::{CodexReport, Report};

/// Send one short `v.oai.hid` notification on BLE Report ID 6.
///
/// The HID-over-GATT Report Reference carries the report id, so this function
/// builds the 63-byte characteristic payload only: `[0x02, len, json..., 0]`.
pub async fn send_key_event(key: &str, pressed: bool) {
    let agent = key
        .strip_prefix("AG")
        .and_then(|n| n.parse::<u8>().ok())
        .unwrap_or(0);
    let act = u8::from(pressed);

    let mut json: String<61> = String::new();
    if write!(
        json,
        "{{\"m\":\"v.oai.hid\",\"p\":{{\"k\":\"{}\",\"act\":{},\"ag\":{}}}}}\r\n",
        key, act, agent
    )
    .is_err()
    {
        return;
    }

    let mut data = [0u8; 63];
    data[0] = 0x02;
    data[1] = json.len() as u8;
    data[2..2 + json.len()].copy_from_slice(json.as_bytes());
    send_hid_report(Report::CodexReport(CodexReport { data })).await;
}
