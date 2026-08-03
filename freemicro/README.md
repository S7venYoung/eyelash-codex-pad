# FreeMicro compatibility

This directory contains a small, fail-closed compatibility patch for
[FreeMicro](https://github.com/eliBenven/freemicro). It retains support for the
official Codex Micro (`303A:8360`) and adds this firmware's own BLE identity
(`4C4B:4643`).

## Install on macOS

From the repository root, run:

```bash
bash freemicro/setup.sh
```

The script downloads the reviewed upstream revision
`64258eb6cc3312a43f9f9f86d87e55e0b609ccc5`, applies the patch, and installs it
into `.venv-freemicro`. It deliberately stops instead of guessing if the
upstream source no longer matches.

After flashing and pairing the Codex firmware, grant the terminal application
**System Settings → Privacy & Security → Input Monitoring**, then test discovery:

```bash
./.venv-freemicro/bin/freemicro keys --dry-run
```

The current pad firmware can send key events, but does not yet implement
FreeMicro's host-to-device `device.status` RPC. Consequently, `freemicro doctor`
is expected to fail its round-trip check at this milestone.

To verify an existing patched checkout:

```bash
python3 freemicro/patch_freemicro.py --check .freemicro-src
```
