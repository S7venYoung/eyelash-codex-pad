#!/usr/bin/env python3
"""Merge the compiled bootloader and pinned S132, refusing any overlap."""
import argparse
from firmware_artifacts import read_hex, validate_bootloader, write_hex


def merge(bootloader, softdevice, output):
    boot, sd = read_hex(bootloader), read_hex(softdevice)
    if boot.keys() & sd.keys():
        raise ValueError("Bootloader and SoftDevice images overlap")
    merged = {**boot, **sd}
    validate_bootloader(merged)
    write_hex(merged, output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bootloader", required=True)
    parser.add_argument("--softdevice", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    merge(args.bootloader, args.softdevice, args.output)
