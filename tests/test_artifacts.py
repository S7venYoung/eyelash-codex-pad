"""Host tests use synthetic vectors/images, never hardware or firmware builds."""
import binascii
import json
import os
from pathlib import Path
import shutil
import struct
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import firmware_artifacts as fw


def put(memory, address, data):
    memory.update(enumerate(data, address))


def application():
    memory = {}
    put(memory, fw.APP_START, struct.pack("<II", 0x20010000, fw.APP_START + 9) + b"\x00\xbf" * 12)
    return memory


def bootloader():
    memory = {}
    put(memory, 0, struct.pack("<II", 0x20008000, 0x1001))
    put(memory, 0x3004, struct.pack("<III", 0x51B1E5DB, fw.APP_START, 0xFFFF00B7))
    put(memory, 0x74000, struct.pack("<II", 0x20010000, 0x74009) + b"\x00\xbf")
    put(memory, 0x10001014, struct.pack("<II", 0x74000, 0x7E000))
    return memory


class ImageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_hex_roundtrip_sparse_and_uicr(self):
        memory = {**application(), **bootloader()}
        path = self.root / "image.hex"
        fw.write_hex(memory, path)
        self.assertEqual(fw.read_hex(path), memory)

    def test_hex_checksum_and_eof(self):
        path = self.root / "bad.hex"
        for data in (":0100000000FE\n:00000001FF\n", ":0100000000FF\n",
                     ":00000001FF\n:0100000000FF\n"):
            path.write_text(data)
            with self.assertRaises(ValueError):
                fw.read_hex(path)

    def test_conflicting_records(self):
        path = self.root / "bad.hex"
        path.write_text("\n".join([fw.hex_record(0, 0, b"a"), fw.hex_record(0, 0, b"b"),
                                  fw.hex_record(0, 1, b"")]) + "\n")
        with self.assertRaises(ValueError):
            fw.read_hex(path)

    def test_application_vectors(self):
        for sp, reset in [(0x20020000, fw.APP_START + 9), (0x20010004, fw.APP_START + 9),
                          (0x20010000, fw.APP_START + 8), (0x20010000, 0x74001),
                          (0x20010000, fw.APP_START + 0x101)]:
            memory = application()
            put(memory, fw.APP_START, struct.pack("<II", sp, reset))
            with self.subTest(sp=sp, reset=reset), self.assertRaises(ValueError):
                fw.validate_application(memory)

    def test_application_rejects_rmk_zero_address_storage_and_uicr(self):
        for extra in (0, fw.APP_END, 0x74000, 0x10001014):
            memory = application()
            memory[extra] = 0
            with self.subTest(address=extra), self.assertRaises(ValueError):
                fw.validate_application(memory)

    def test_maximum_application_does_not_cross_storage(self):
        memory = application()
        memory[fw.APP_END - 1] = 0
        self.assertEqual(len(fw.validate_application(memory)), 0x47000)

    def test_bootloader_layout_and_id(self):
        fw.validate_bootloader(bootloader())
        for address, value in [(0x300C, 0xFFFF0123), (0x3008, 0x27000),
                               (0x10001014, 0xF4000), (0x10001018, 0xFE000),
                               (0x74004, 0x6D001)]:
            memory = bootloader()
            put(memory, address, struct.pack("<I", value))
            with self.subTest(address=address), self.assertRaises(ValueError):
                fw.validate_bootloader(memory)

    def test_bootloader_must_not_write_settings_or_application(self):
        for address in (fw.APP_START, 0x6D000, 0x7E000, 0x7F000, 0x10001200):
            memory = bootloader()
            memory[address] = 0
            with self.subTest(address=address), self.assertRaises(ValueError):
                fw.validate_bootloader(memory)

    def test_legacy_package_verifier_and_crc(self):
        binary = fw.validate_application(application())
        init = struct.pack("<HHIHHH", 0x52, 0xADAF, 0xFFFFFFFF, 1, 0xB7,
                           binascii.crc_hqx(binary, 0xFFFF))
        manifest = {"manifest": {"dfu_version": 0.5, "application": {
            "bin_file": "app.bin", "dat_file": "app.dat"}}}
        path = self.root / "ota.zip"
        for bad in (False, True):
            with zipfile.ZipFile(path, "w") as archive:
                archive.writestr("manifest.json", json.dumps(manifest))
                archive.writestr("app.bin", binary)
                archive.writestr("app.dat", init[:-1] + bytes([init[-1] ^ int(bad)]))
            if bad:
                with self.assertRaises(ValueError):
                    fw.verify_dfu(path, binary)
            else:
                fw.verify_dfu(path, binary)

    def test_real_nrfutil_with_synthetic_images(self):
        executable = os.environ.get("NRFUTIL") or shutil.which("adafruit-nrfutil")
        if not executable:
            self.skipTest("Install requirements-dfu.txt to test the real packaging tool")
        app, boot = self.root / "app.hex", self.root / "boot.hex"
        fw.write_hex(application(), app)
        fw.write_hex(bootloader(), boot)
        fw.release(app, boot, self.root / "release", executable)
        combined = fw.read_hex(self.root / "release/eyelash-numpad-first-install-swd.hex")
        self.assertEqual(combined, {**application(), **bootloader()})
        fw.verify_dfu(self.root / "release/eyelash-numpad-ota.zip",
                      fw.validate_application(application()))


if __name__ == "__main__":
    unittest.main()
