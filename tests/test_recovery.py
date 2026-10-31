"""Compile only a host-side GPIO simulation of the actual recovery scanner."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RecoveryTests(unittest.TestCase):
    def test_physical_chord_debounce_and_gpio_cleanup(self):
        compiler = shutil.which("cc")
        if not compiler:
            self.skipTest("A host C compiler is required")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "nrfx.h").write_text("""
#pragma once
#include <stdbool.h>
#include <stdint.h>
#define NRFX_DELAY_US(us) ((void)(us))
""")
            (root / "nrf_gpio.h").write_text("""
#pragma once
#include <stdint.h>
#define NRF_GPIO_PIN_PULLDOWN 1
void nrf_gpio_cfg_default(uint32_t pin);
void nrf_gpio_cfg_input(uint32_t pin, int pull);
void nrf_gpio_pin_set(uint32_t pin);
void nrf_gpio_cfg_output(uint32_t pin);
uint32_t nrf_gpio_pin_read(uint32_t pin);
""")
            (root / "test.c").write_text("""
#include <assert.h>
#include <stdbool.h>
#include "board.h"
static int active = -1, row = 0, latch = -1, reads, bounce;
static unsigned pressed;
void nrf_gpio_cfg_default(uint32_t pin) {
    assert(pin == 5 || pin == 7 || pin == 9 || pin == 25 || pin == 27);
    if (active == (int)pin) active = -1;
    if (pin == 27) row = 0;
}
void nrf_gpio_cfg_input(uint32_t pin, int pull) {
    assert(pin == 27 && pull == NRF_GPIO_PIN_PULLDOWN); row = 1;
}
void nrf_gpio_pin_set(uint32_t pin) { assert(pin == 5 || pin == 9); latch = (int)pin; }
void nrf_gpio_cfg_output(uint32_t pin) {
    assert(active == -1 && latch == (int)pin); active = (int)pin;
}
uint32_t nrf_gpio_pin_read(uint32_t pin) {
    assert(pin == 27 && row && (active == 5 || active == 9));
    reads++;
    if (bounce && reads == 3) return 0;
    return (pressed >> (active == 5 ? 0 : 1)) & 1;
}
int main(void) {
    for (pressed = 0; pressed < 4; pressed++) {
        reads = 0; bounce = 0;
        assert(eyelash_matrix_dfu_requested() == (pressed == 3));
        assert(reads == 8 && active == -1 && row == 0);
    }
    pressed = 3; bounce = 1; reads = 0;
    assert(!eyelash_matrix_dfu_requested());
    assert(reads == 8 && active == -1 && row == 0);
    return 0;
}
""")
            executable = root / "test"
            subprocess.run([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                            "-I", str(root), "-I", str(ROOT / "bootloader/boards/eyelash_numpad"),
                            str(root / "test.c"), "-o", str(executable)], check=True)
            subprocess.run([str(executable)], check=True)
