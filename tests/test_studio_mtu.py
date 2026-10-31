from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_zmk


class StudioTransportTests(unittest.TestCase):
    def test_pinned_source_and_drift_rejection(self):
        original = (ROOT / "tests/fixtures/dya_gatt_rpc_transport.c").read_text()
        patched = prepare_zmk.patched_source(original)
        self.assertIn("indicate_buffer[128]", patched)
        self.assertNotIn("conn_info.le.data_len->tx_max_len", patched)
        with self.assertRaises(ValueError):
            prepare_zmk.patched_source(original + "// upstream changed\n")

    def test_real_replacement_function_at_small_and_large_mtu(self):
        compiler = shutil.which("cc")
        if not compiler:
            self.skipTest("A host C compiler is required")
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            code = """#include <assert.h>
#include <stdint.h>
#include <stddef.h>
struct bt_conn { uint16_t mtu; };
static uint16_t bt_gatt_get_mtu(struct bt_conn *conn) { return conn->mtu; }
""" + prepare_zmk.NEW_FUNCTION + """
int main(void) {
    struct bt_conn conn;
    assert(get_notify_size_for_conn(NULL) == 20);
    for (unsigned mtu = 0; mtu <= 517; mtu++) {
        conn.mtu = mtu;
        unsigned payload = get_notify_size_for_conn(&conn);
        assert(payload == (mtu > 3 ? mtu - 3 : 20));
        unsigned chunk = payload < 128 ? payload : 128;
        if (mtu >= 23) assert(chunk <= mtu - 3);
    }
    return 0;
}
"""
            (root / "test.c").write_text(code)
            subprocess.run([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                            str(root / "test.c"), "-o", str(root / "test")], check=True)
            subprocess.run([str(root / "test")], check=True)
