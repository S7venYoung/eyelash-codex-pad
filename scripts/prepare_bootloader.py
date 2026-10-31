#!/usr/bin/env python3
"""Fetch a pinned upstream and apply the Eyelash patch. Does not build/flash."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "bootloader/upstream.json").read_text())


def prepare(destination, fetch=True):
    destination = Path(destination).resolve()
    if not destination.exists():
        if not fetch:
            raise ValueError("Missing upstream source; omit --no-fetch to download it")
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout",
                        LOCK["repository"], str(destination)], check=True)
        subprocess.run(["git", "-C", str(destination), "checkout", "--detach",
                        LOCK["revision"]], check=True)
    head = subprocess.check_output(
        ["git", "-C", str(destination), "rev-parse", "HEAD"], text=True).strip()
    if head != LOCK["revision"]:
        raise ValueError(f"Upstream revision mismatch: {head}")
    # Normalize the two upstream CRLF files before applying the small patch.
    for relative in ("Makefile", "src/main.c", "src/boards/boards.c"):
        path = destination / relative
        path.write_bytes(path.read_bytes().replace(b"\r\n", b"\n"))
    patch = str(ROOT / "bootloader/eyelash.patch")
    cmd = ["git", "-C", str(destination), "apply"]
    already = subprocess.run(cmd + ["--reverse", "--check", patch],
                             capture_output=True).returncode == 0
    if not already:
        subprocess.run(cmd + ["--check", patch], check=True)
        subprocess.run(cmd + [patch], check=True)
    source = ROOT / "bootloader/boards" / LOCK["board"]
    target = destination / "src/boards" / LOCK["board"]
    target.mkdir(parents=True, exist_ok=True)
    for path in source.iterdir():
        shutil.copyfile(path, target / path.name)
    if fetch:
        # nRF52832 does not use TinyUSB, UF2 conversion or signature libraries.
        subprocess.run(["git", "-C", str(destination), "submodule", "update",
                        "--init", "lib/nrfx"], check=True)
    print(f"Prepared {LOCK['board']} at {head}; no firmware built or flashed")
    return destination


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", nargs="?", default=ROOT / ".deps/adafruit-bootloader")
    parser.add_argument("--no-fetch", action="store_true")
    args = parser.parse_args()
    prepare(args.destination, not args.no_fetch)
