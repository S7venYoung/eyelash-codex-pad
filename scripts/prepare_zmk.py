#!/usr/bin/env python3
"""Apply the BLE Studio MTU fix only to the pinned DYA core."""
import argparse
import hashlib
from pathlib import Path
import subprocess

REVISION = "e5c9b6915b56801193e359dd9bad4a167ce0d1b8"
ORIGINAL_SHA256 = "be32ba871d87568edb9b44536840dabc93dda53fbe65e9d847e942b154405e5b"
NEW_FUNCTION = """static uint16_t get_notify_size_for_conn(struct bt_conn *conn) {
    // GATT indication payload is ATT MTU minus three, not LL data length.
    uint16_t mtu = conn ? bt_gatt_get_mtu(conn) : 23;
    return mtu > 3 ? mtu - 3 : 20;
}"""


def patched_source(original):
    original = original.replace("\r\n", "\n").rstrip() + "\n"
    if hashlib.sha256(original.encode()).hexdigest() != ORIGINAL_SHA256:
        raise ValueError("Unexpected DYA BLE transport source; refusing to patch")
    start = original.index("static uint16_t get_notify_size_for_conn(")
    opening = original.index("{", start)
    depth = 1
    closing = opening + 1
    while depth:
        if original[closing] == "{":
            depth += 1
        elif original[closing] == "}":
            depth -= 1
        closing += 1
    result = original[:start] + NEW_FUNCTION + original[closing:]
    # Keep chunks bounded on 64 KiB nRF52832 RAM while avoiding 27-byte chunks.
    return result.replace("static uint8_t indicate_buffer[27];",
                          "static uint8_t indicate_buffer[128];", 1)


def prepare(path):
    path = Path(path)
    head = subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()
    if head != REVISION:
        raise ValueError("ZMK revision does not match pinned DYA core")
    relative = "app/src/studio/gatt_rpc_transport.c"
    original = subprocess.check_output(["git", "-C", str(path), "show", f"HEAD:{relative}"], text=True)
    candidate = patched_source(original)
    target = path / relative
    current = target.read_text()
    if current not in (original, candidate):
        raise ValueError("BLE transport has unrelated local edits; refusing to overwrite")
    target.write_text(candidate)
    print("DYA BLE transport: ATT_MTU - 3, maximum 128-byte indications")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("zmk", type=Path)
    prepare(parser.parse_args().zmk)
