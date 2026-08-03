#!/usr/bin/env python3
"""Patch a pinned FreeMicro checkout to recognize the Eyelash Codex Pad."""

from __future__ import annotations

import argparse
from pathlib import Path


OFFICIAL_IDS = "VENDOR_ID = 0x303A\nPRODUCT_ID = 0x8360"
DEVICE_IDS = """VENDOR_ID = 0x303A
PRODUCT_ID = 0x8360

# Eyelash Codex Pad (this repository's experimental firmware).
EYELASH_VENDOR_ID = 0x4C4B
EYELASH_PRODUCT_ID = 0x4643
SUPPORTED_DEVICES = {
    (VENDOR_ID, PRODUCT_ID),
    (EYELASH_VENDOR_ID, EYELASH_PRODUCT_ID),
}"""

OFFICIAL_MATCH = """        matched = (
            _prop_int(candidate, \"VendorID\") == VENDOR_ID
            and _prop_int(candidate, \"ProductID\") == PRODUCT_ID
        )"""
MULTI_DEVICE_MATCH = """        matched = (
            _prop_int(candidate, \"VendorID\"),
            _prop_int(candidate, \"ProductID\"),
        ) in SUPPORTED_DEVICES"""


def source_file(checkout: Path) -> Path:
    return checkout / "src" / "freemicro" / "device" / "codex_micro.py"


def is_patched(text: str) -> bool:
    return DEVICE_IDS in text and MULTI_DEVICE_MATCH in text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("checkout", type=Path, help="path to a FreeMicro checkout")
    parser.add_argument(
        "--check", action="store_true", help="verify the compatibility patch only"
    )
    args = parser.parse_args()

    path = source_file(args.checkout.resolve())
    if not path.is_file():
        raise SystemExit(f"FreeMicro source file not found: {path}")

    text = path.read_text(encoding="utf-8")
    if args.check:
        if not is_patched(text):
            raise SystemExit("FreeMicro compatibility patch is missing or incomplete")
        print(f"Patch verified: {path}")
        return 0

    if is_patched(text):
        print(f"Already patched: {path}")
        return 0

    if text.count(OFFICIAL_IDS) != 1 or text.count(OFFICIAL_MATCH) != 1:
        raise SystemExit(
            "Unsupported FreeMicro source. Use the pinned revision from setup.sh; "
            "no files were changed."
        )

    patched = text.replace(OFFICIAL_IDS, DEVICE_IDS).replace(
        OFFICIAL_MATCH, MULTI_DEVICE_MATCH
    )
    if not is_patched(patched):
        raise SystemExit("Internal error: generated patch did not pass verification")

    path.write_text(patched, encoding="utf-8")
    print(f"Patched: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
