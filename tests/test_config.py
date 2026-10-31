import json
from pathlib import Path
import re
import unittest
import yaml

ROOT = Path(__file__).resolve().parents[1]


class ConfigTests(unittest.TestCase):
    def test_flash_partitions_match_bootloader(self):
        text = (ROOT / "boards/eyelash/eyelash_numpad/eyelash_numpad_nrf52832.dts").read_text()
        partitions = [(int(address, 16), int(start, 16), int(size, 16))
                      for address, start, size in re.findall(
                          r"partition@([0-9a-f]+)\s*\{[^}]*reg\s*=\s*<(0x[0-9a-f]+)\s+(0x[0-9a-f]+)>", text)]
        self.assertEqual(partitions, [
            (0, 0, 0x26000), (0x26000, 0x26000, 0x47000),
            (0x6D000, 0x6D000, 0x7000), (0x74000, 0x74000, 0xA000),
            (0x7E000, 0x7E000, 0x1000), (0x7F000, 0x7F000, 0x1000)])
        self.assertEqual(sum(size for _, _, size in partitions), 512 * 1024)
        lock = json.loads((ROOT / "bootloader/upstream.json").read_text())
        self.assertEqual(lock["application_start"], partitions[1][1])
        self.assertEqual(lock["application_end"], partitions[2][1])
        self.assertEqual(lock["bootloader_start"], partitions[3][1])

    def test_yaml_pins_and_manual_build_only(self):
        for path in list(ROOT.rglob("*.yml")) + list(ROOT.rglob("*.yaml")):
            if ".deps" in path.parts:
                continue
            with self.subTest(path=path):
                self.assertIsInstance(yaml.safe_load(path.read_text()), dict)
        workflow = yaml.safe_load((ROOT / ".github/workflows/build-zmk.yml").read_text())
        triggers = workflow.get("on", workflow.get(True))  # YAML 1.1 'on' alias
        self.assertEqual(set(triggers), {"workflow_dispatch"})
        west = yaml.safe_load((ROOT / "config/west.yml").read_text())
        for project in west["manifest"]["projects"]:
            self.assertRegex(project["revision"], r"^[a-f0-9]{40}$")
        names = {project["name"] for project in west["manifest"]["projects"]}
        self.assertTrue({"zmk-feature-runtime-macro", "zmk-feature-runtime-tapdance",
                         "zmk-feature-runtime-combo"} <= names)
        self.assertFalse(any("sensor-rotate" in name or "input-processor" in name for name in names))

    def test_original_primary_keys_and_studio_layout(self):
        text = (ROOT / "config/eyelash_numpad.keymap").read_text()
        primary = text.split("default_layer", 1)[1].split("function_layer", 1)[0]
        keys = re.findall(r"KP_[A-Z0-9]+", primary)
        self.assertEqual(keys, ["KP_N7", "KP_N8", "KP_N9", "KP_DIVIDE",
                                "KP_N4", "KP_N5", "KP_N6", "KP_MULTIPLY",
                                "KP_N1", "KP_N2", "KP_N3", "KP_MINUS",
                                "KP_ENTER", "KP_N0", "KP_DOT", "KP_PLUS"])
        board = (ROOT / "boards/eyelash/eyelash_numpad/eyelash_numpad_nrf52832.dts").read_text()
        self.assertEqual(board.count("<&key_physical_attrs"), 16)
        self.assertIn("&studio_unlock", text)
        self.assertIn("&eyelash_dfu", text)
