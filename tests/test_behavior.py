from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DfuBehaviorTests(unittest.TestCase):
    def test_actual_behavior_preserves_ota_magic_until_reset(self):
        compiler = shutil.which("cc")
        if not compiler:
            self.skipTest("A host C compiler is required")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for directory in ("zephyr", "drivers", "zmk"):
                (root / directory).mkdir()
            for path in ("zephyr/device.h", "zephyr/devicetree.h", "zephyr/irq.h",
                         "drivers/behavior.h", "zmk/behavior.h", "nrfx.h"):
                (root / path).write_text("")
            (root / "test.c").write_text(r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <setjmp.h>
static jmp_buf reboot;
static unsigned irq_disabled, barrier;
static struct { uint32_t GPREGRET; } power_registers;
#define NRF_POWER (&power_registers)
#define ARG_UNUSED(x) ((void)(x))
#define IS_ENABLED(x) 0
#define BEHAVIOR_LOCALITY_EVENT_SOURCE 1
#define ZMK_BEHAVIOR_OPAQUE 0
#define DT_INST_FOREACH_STATUS_OKAY(fn)
struct zmk_behavior_binding { int unused; };
struct zmk_behavior_binding_event { int unused; };
struct behavior_driver_api {
    int (*binding_pressed)(struct zmk_behavior_binding *, struct zmk_behavior_binding_event);
    int locality;
};
static unsigned irq_lock(void) { irq_disabled = 1; return 0; }
static void __DSB(void) { assert(irq_disabled && NRF_POWER->GPREGRET == 0xA8); barrier = 1; }
static _Noreturn void NVIC_SystemReset(void) {
    assert(irq_disabled && barrier && NRF_POWER->GPREGRET == 0xA8);
    longjmp(reboot, 1);
}
#include "behavior_eyelash_dfu.c"
int main(void) {
    assert(eyelash_dfu_api.locality == BEHAVIOR_LOCALITY_EVENT_SOURCE);
    if (setjmp(reboot) == 0) {
        struct zmk_behavior_binding binding = {0};
        struct zmk_behavior_binding_event event = {0};
        eyelash_dfu_api.binding_pressed(&binding, event);
        assert(0 && "DFU behavior did not reset");
    }
    assert(NRF_POWER->GPREGRET == 0xA8);
    return 0;
}
''')
            subprocess.run([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                            "-I", str(root), "-I", str(ROOT / "src"), str(root / "test.c"),
                            "-o", str(root / "test")], check=True)
            subprocess.run([str(root / "test")], check=True)
