#!/usr/bin/env python3
"""Validate nRF52832 images, package application-only BLE DFU and merge SWD HEX."""
import argparse
import binascii
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
LAYOUT = json.loads((ROOT / "bootloader/upstream.json").read_text())
APP_START = LAYOUT["application_start"]
APP_END = LAYOUT["application_end"]


def read_hex(path):
    memory = {}
    base = 0
    ended = False
    for number, line in enumerate(Path(path).read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        if ended or not line.startswith(":"):
            raise ValueError(f"Invalid HEX line {number}")
        try:
            record = bytes.fromhex(line[1:])
        except ValueError as exc:
            raise ValueError(f"Invalid HEX encoding at line {number}") from exc
        if len(record) < 5 or len(record) != record[0] + 5 or sum(record) & 255:
            raise ValueError(f"Invalid HEX checksum/length at line {number}")
        length, address, kind = record[0], int.from_bytes(record[1:3], "big"), record[3]
        data = record[4:4 + length]
        if kind == 0:
            if address + length > 0x10000:
                raise ValueError("HEX data crosses a 64 KiB boundary")
            for offset, value in enumerate(data):
                absolute = base + address + offset
                if absolute in memory and memory[absolute] != value:
                    raise ValueError(f"Conflicting HEX bytes at {absolute:#x}")
                memory[absolute] = value
        elif kind == 1 and length == 0 and address == 0:
            ended = True
        elif kind in (2, 4) and length == 2 and address == 0:
            base = int.from_bytes(data, "big") << (4 if kind == 2 else 16)
        elif kind in (3, 5) and length == 4 and address == 0:
            pass  # Start-address metadata; reset vector is validated separately.
        else:
            raise ValueError(f"Unsupported/malformed HEX record {kind}")
    if not ended or not memory:
        raise ValueError("HEX must contain data and an EOF record")
    return memory


def hex_record(address, kind, data):
    body = bytes([len(data)]) + address.to_bytes(2, "big") + bytes([kind]) + data
    return ":" + (body + bytes([(-sum(body)) & 255])).hex().upper()


def write_hex(memory, path):
    lines = []
    upper = None
    addresses = sorted(memory)
    index = 0
    while index < len(addresses):
        start = addresses[index]
        if start >> 16 != upper:
            upper = start >> 16
            lines.append(hex_record(0, 4, upper.to_bytes(2, "big")))
        chunk = bytearray([memory[start]])
        index += 1
        while (index < len(addresses) and len(chunk) < 16
               and addresses[index] == start + len(chunk)
               and addresses[index] >> 16 == upper):
            chunk.append(memory[addresses[index]])
            index += 1
        lines.append(hex_record(start & 0xFFFF, 0, bytes(chunk)))
    lines.append(hex_record(0, 1, b""))
    Path(path).write_text("\n".join(lines) + "\n")


def word(memory, address):
    try:
        return int.from_bytes(bytes(memory[address + i] for i in range(4)), "little")
    except KeyError as exc:
        raise ValueError(f"Missing word at {address:#x}") from exc


def validate_application(memory):
    if not memory or min(memory) != APP_START or max(memory) >= APP_END:
        raise ValueError(f"Application must be wholly within {APP_START:#x}..{APP_END - 1:#x}")
    sp, reset = word(memory, APP_START), word(memory, APP_START + 4)
    if not (0x20000000 < sp <= 0x20010000) or sp & 7:
        raise ValueError("Application stack pointer does not match 64 KiB nRF52832 RAM")
    if not (reset & 1 and APP_START <= (reset & ~1) < APP_END
            and (reset & ~1) in memory):
        raise ValueError("Application reset vector is outside its executable image")
    # nrfutil pads to a four-byte boundary with erased-flash bytes.
    end = (max(memory) + 4) & ~3
    if end > APP_END:
        raise ValueError("Padded application overlaps settings storage")
    return bytes(memory.get(address, 255) for address in range(APP_START, end))


def validate_bootloader(memory):
    if word(memory, 0x3004) != 0x51B1E5DB:
        raise ValueError("Bootloader HEX does not contain a SoftDevice")
    if word(memory, 0x3008) != APP_START or word(memory, 0x300C) & 0xFFFF != LAYOUT["softdevice_id"]:
        raise ValueError("Bootloader must contain S132 6.1.1 (ID 0x00B7, size 0x26000)")
    if word(memory, 0x10001014) != LAYOUT["bootloader_start"]:
        raise ValueError("UICR bootloader address mismatch")
    if word(memory, 0x10001018) != LAYOUT["mbr_params"]:
        raise ValueError("UICR MBR parameter address mismatch")
    start, end = LAYOUT["bootloader_start"], LAYOUT["mbr_params"]
    sp, reset = word(memory, start), word(memory, start + 4)
    if not (0x20008000 < sp <= 0x20010000) or sp & 7:
        raise ValueError("Bootloader stack pointer mismatch")
    if not (reset & 1 and start <= (reset & ~1) < end and (reset & ~1) in memory):
        raise ValueError("Bootloader reset vector mismatch")
    for address in memory:
        if not (0 <= address < APP_START or start <= address < end
                or 0x10001014 <= address < 0x1000101C):
            raise ValueError(f"Bootloader writes an unexpected address: {address:#x}")


def verify_dfu(package, expected):
    with zipfile.ZipFile(package) as archive:
        manifest = json.loads(archive.read("manifest.json"))["manifest"]
        if set(manifest) != {"application", "dfu_version"} or manifest["dfu_version"] != 0.5:
            raise ValueError("OTA ZIP must contain an application-only update")
        application = manifest["application"]
        binary = archive.read(application["bin_file"])
        init = archive.read(application["dat_file"])
    if binary != expected:
        raise ValueError("DFU binary differs from the validated application")
    # Adafruit legacy DFU init packet, not Nordic Secure DFU protobuf format.
    if len(init) != 14:
        raise ValueError("Unexpected legacy DFU init packet length")
    device, revision, version, count, sd_id, crc = struct.unpack("<HHIHHH", init)
    if (device, revision, count, sd_id) != (0x0052, 0xADAF, 1, LAYOUT["softdevice_id"]):
        raise ValueError("DFU target/SoftDevice requirement mismatch")
    if crc != binascii.crc_hqx(binary, 0xFFFF):
        raise ValueError("DFU CRC16 mismatch")


def package_application(application_path, output, nrfutil="adafruit-nrfutil"):
    memory = read_hex(application_path)
    binary = validate_application(memory)
    output = Path(output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    # Normalize the HEX, excluding start-address metadata before nrfutil reads it.
    with tempfile.TemporaryDirectory() as temporary:
        normalized = Path(temporary) / "eyelash-numpad.hex"
        candidate = Path(temporary) / "ota.zip"
        write_hex(memory, normalized)
        subprocess.run([nrfutil, "dfu", "genpkg", "--dev-type", "0x0052",
                        "--dev-revision", "0xADAF", "--sd-req", "0x00B7",
                        "--application", str(normalized), str(candidate)], check=True)
        verify_dfu(candidate, binary)
        output.write_bytes(candidate.read_bytes())
    return binary


def release(application_path, bootloader_path, destination, nrfutil="adafruit-nrfutil"):
    app = read_hex(application_path)
    binary = validate_application(app)
    boot = read_hex(bootloader_path)
    validate_bootloader(boot)
    if app.keys() & boot.keys():
        raise ValueError("Application and Bootloader overlap")
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    package_application(application_path, destination / "eyelash-numpad-ota.zip", nrfutil)
    write_hex(app, destination / "eyelash-numpad-zmk.hex")
    write_hex(boot, destination / "eyelash-numpad-bootloader-s132.hex")
    write_hex({**boot, **app}, destination / "eyelash-numpad-first-install-swd.hex")
    report = {"layout": LAYOUT, "application_bytes": len(binary),
              "application_limit_bytes": APP_END - APP_START,
              "validation": "image boundaries, vectors, S132 ID, UICR and DFU CRC; not hardware validation",
              "files": {path.name: hashlib.sha256(path.read_bytes()).hexdigest()
                        for path in sorted(destination.iterdir())
                        if path.suffix in (".hex", ".zip")}}
    (destination / "manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--application", type=Path, required=True)
    parser.add_argument("--bootloader", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/release")
    parser.add_argument("--nrfutil", default="adafruit-nrfutil")
    args = parser.parse_args()
    release(args.application, args.bootloader, args.output, args.nrfutil)
