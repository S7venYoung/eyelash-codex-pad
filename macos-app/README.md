# Eyelash Codex Bridge for macOS

A native macOS 13+ menu-bar host for the Eyelash Codex Pad. It discovers both
the experimental pad (`4C4B:4643`) and the official Codex Micro identity
(`303A:8360`), listens to Vendor HID Report ID 6, parses `v.oai.hid` events,
and shows the latest events without a terminal window. Version 0.2 also reads
the pad's existing standard keyboard reports, so no firmware flash is required.

## Install

Download the architecture matching the Mac from the latest GitHub Actions run:

- `Eyelash-Codex-Bridge-arm64` for Apple silicon (M1/M2/M3/M4 and newer)
- `Eyelash-Codex-Bridge-x86_64` for Intel Macs

Unzip the artifact, move the app to `/Applications`, then right-click the app
and choose **Open** the first time. This development build is ad-hoc signed,
not Apple-notarized.

For the no-flash Vial mode, configure Layer 1 as:

```text
F13 F14 F15 TRNS
F16 F17 F18 F19
F20 F21 F22 F23
F24 M0  M1  M2
```

Set `M0 = Shift+F13`, `M1 = Shift+F14`, and `M2 = Shift+F15`. Hold the Layer 0
key that activates Layer 1, then press another key. The corresponding `AGxx`,
`ACTxx`, or encoder event should appear with source **Vial**. Grant Input
Monitoring permission if macOS requests it.

The app can register itself as a login item. It also publishes each decoded
event through `DistributedNotificationCenter` under:

```text
com.s7venyoung.eyelash-codex-bridge.event
```

with `key` and `pressed` fields for a later Codex/Claude adapter.

## Current milestone

The app supports both the no-flash Vial keyboard mapping and the experimental
Vendor HID firmware. Direct control of the ChatGPT desktop
app is not claimed yet: that requires either official app support for the
custom identity or a separate, explicitly defined action adapter. Device
status and lighting output are also not implemented yet.
