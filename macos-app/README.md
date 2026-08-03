# Eyelash Codex Bridge for macOS

A native macOS 13+ menu-bar host for the Eyelash Codex Pad. It discovers both
the experimental pad (`4C4B:4643`) and the official Codex Micro identity
(`303A:8360`), listens to Vendor HID Report ID 6, parses `v.oai.hid` events,
and shows the latest events without a terminal window.

## Install

Download the architecture matching the Mac from the latest GitHub Actions run:

- `Eyelash-Codex-Bridge-arm64` for Apple silicon (M1/M2/M3/M4 and newer)
- `Eyelash-Codex-Bridge-x86_64` for Intel Macs

Unzip the artifact, move the app to `/Applications`, then right-click the app
and choose **Open** the first time. This development build is ad-hoc signed,
not Apple-notarized.

Pair the pad in macOS Bluetooth settings and flash the Codex firmware. Hold the
pad's bottom-left layer key and press another key; the corresponding `AGxx`,
`ACTxx`, or encoder event should appear in the menu-bar window.

The app can register itself as a login item. It also publishes each decoded
event through `DistributedNotificationCenter` under:

```text
com.s7venyoung.eyelash-codex-bridge.event
```

with `key` and `pressed` fields for a later Codex/Claude adapter.

## Current milestone

This first native build replaces the terminal-based device monitor and proves
the complete BLE HID → macOS event path. Direct control of the ChatGPT desktop
app is not claimed yet: that requires either official app support for the
custom identity or a separate, explicitly defined action adapter. Device
status and lighting output are also not implemented yet.
