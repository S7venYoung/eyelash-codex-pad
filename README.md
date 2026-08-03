# Eyelash Codex Pad

Experimental Codex Micro-compatible firmware for the 4×4 Eyelash nRF52832
macropad, built on RMK.

## Repository layout

- `firmware/original`: untouched firmware baseline supplied with the pad.
- `firmware/codex`: experimental BLE Vendor HID build.
- `rmk-overrides`: the small RMK fork surface used by the Codex build.
- `freemicro`: one-command FreeMicro compatibility installer and verifier.
- `macos-app`: native menu-bar HID host, built entirely by GitHub Actions.
- `.github/workflows/build-firmware.yml`: builds both variants and uploads
  `.hex` and `.uf2` artifacts.

## Codex layer

Hold the bottom-left `LT(1, KpEnter)` key. The other fifteen switches emit
Report ID 6 `v.oai.hid` notifications:

```text
AG00   AG01   AG02   AG03
AG04   AG05   ACT06  ACT07
ACT08  ACT09  ACT10  ACT11
MODE   ACT12  ENC_CC ENC_CW
```

Layer 0 remains the original numpad. `ENC_CC` and `ENC_CW` are virtual encoder
ticks and therefore emit one event per press, without a release event.

## Protocol milestone

The experimental build adds the BLE HID vendor collection on Usage Page
`0xFF00`, Report ID `6`, with 63-byte Input, Output and Feature reports. Input
notifications use FreeMicro's framing:

```text
[0x02][length][compact JSON + CRLF][zero padding]
```

Host-to-device RPC is accepted by GATT but not parsed yet, so this revision is
an **input-only prototype**. It does not impersonate OpenAI's VID/PID and is not
claimed to be recognized directly by the ChatGPT desktop app. A bridge must be
configured to accept this firmware's own VID/PID.

## FreeMicro compatibility

The included compatibility patch keeps support for the official Codex Micro
and adds the Eyelash firmware's `4C4B:4643` identity. On macOS, run:

```bash
bash freemicro/setup.sh
./.venv-freemicro/bin/freemicro keys --dry-run
```

See [`freemicro/README.md`](freemicro/README.md) for permissions, limitations,
and patch verification details.

## Native macOS app

The repository also includes **Eyelash Codex Bridge**, a macOS 13+ menu-bar
app that discovers the pad, decodes Report ID 6 events, shows recent activity,
and can launch at login. Download the Apple-silicon or Intel artifact from the
latest **Build macOS app** workflow run. See
[`macos-app/README.md`](macos-app/README.md) for installation and the precise
scope of this first milestone.

## Downloading firmware

Open the latest GitHub Actions run, then download either:

- `eyelash-original-firmware`
- `eyelash-codex-firmware`

Each artifact contains an Intel HEX file and an nRF52832 UF2 file.

## Safety notes

- The Codex build reserves `0x70000..0x7FFFF` for RMK storage and limits the
  linked application region to 448 KiB.
- The original build is preserved exactly, including its original memory map.
- Keep a hardware recovery/programming method available when testing
  experimental firmware.

## Upstream projects

- [RMK](https://github.com/HaoboGu/rmk)
- [FreeMicro](https://github.com/eliBenven/freemicro)
