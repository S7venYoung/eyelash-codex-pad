#!/usr/bin/env bash
set -euo pipefail
project_dir="$(cd "$(dirname "$0")/.." && pwd)"
upstream_dir="$project_dir/.deps/adafruit-bootloader"
python3 "$project_dir/scripts/prepare_bootloader.py" "$upstream_dir"
# Deliberately do not invoke upstream 'all': it produces irrelevant UF2/SD updates.
# The fixed release layout is required; DEBUG=1 changes reserved addresses.
make -C "$upstream_dir" BOARD=eyelash_numpad DEBUG=0 \
  SIGNED_FW=0 DUALBANK_FW=0 GIT_VERSION=0.1.0-eyelash1 \
  _build/build-eyelash_numpad/eyelash_numpad_bootloader-0.1.0-eyelash1.hex
mkdir -p "$project_dir/dist/bootloader"
python3 "$project_dir/scripts/merge_bootloader.py" \
  --bootloader "$upstream_dir/_build/build-eyelash_numpad/eyelash_numpad_bootloader-0.1.0-eyelash1.hex" \
  --softdevice "$upstream_dir/lib/softdevice/s132_nrf52_6.1.1/s132_nrf52_6.1.1_softdevice.hex" \
  --output "$project_dir/dist/bootloader/eyelash-numpad-bootloader-s132.hex"
