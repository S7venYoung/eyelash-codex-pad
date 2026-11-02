from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_custom_settings


class StreamedMetadataTests(unittest.TestCase):
    def test_constraints_repeated_encoding_keyspace_and_failures(self):
        compiler = shutil.which("cc")
        if not compiler:
            self.skipTest("A host C compiler is required")
        preamble = r'''
#include <assert.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
typedef struct { unsigned count, tags; int values[16]; bool fail_tag, fail_value; } pb_ostream_t;
typedef struct { int unused; } pb_field_t;
typedef struct {
    struct { bool (*encode)(pb_ostream_t *, const pb_field_t *, void *const *); } funcs;
    void *arg;
} pb_callback_t;
struct zmk_custom_setting_constraint { int type, value; };
struct zmk_custom_setting_keyspace {
    const struct zmk_custom_setting_constraint *constraints;
    size_t constraints_count;
};
struct zmk_custom_setting {
    int confidentiality, read_permission, write_permission;
    const struct zmk_custom_setting_constraint *constraints;
    size_t constraints_count;
    const struct zmk_custom_setting_keyspace *keyspace;
};
typedef struct { int value; } cormoran_zmk_custom_settings_SettingConstraint;
typedef struct {
    int confidentiality, read_permission, write_permission;
    pb_callback_t constraints;
} cormoran_zmk_custom_settings_SettingMeta;
#define ZMK_CUSTOM_SETTING_CONSTRAINT_NONE 0
#define cormoran_zmk_custom_settings_SettingConstraint_init_zero {0}
#define cormoran_zmk_custom_settings_SettingMeta_init_zero {0}
#define cormoran_zmk_custom_settings_SettingConstraint_fields NULL
static const struct zmk_custom_setting_keyspace *
zmk_custom_setting_keyspace_of(const struct zmk_custom_setting *setting) { return setting->keyspace; }
static int proto_confidentiality(int value) { return value; }
static int proto_permission(int value) { return value; }
static int constraint_to_proto(const struct zmk_custom_setting_constraint *source,
                               cormoran_zmk_custom_settings_SettingConstraint *target) {
    target->value = source->value; return source->type < 0 ? -1 : 0;
}
static bool pb_encode_tag_for_field(pb_ostream_t *stream, const pb_field_t *field) {
    (void)field; stream->tags++; return !stream->fail_tag;
}
static bool pb_encode_submessage(pb_ostream_t *stream, const void *fields, const void *value) {
    (void)fields;
    if (stream->fail_value) return false;
    stream->values[stream->count++] = ((const cormoran_zmk_custom_settings_SettingConstraint *)value)->value;
    return true;
}
'''
        tests = r'''
int main(void) {
    struct zmk_custom_setting_constraint constraints[12];
    for (int i = 0; i < 12; i++) constraints[i] = (struct zmk_custom_setting_constraint){1, i};
    struct zmk_custom_setting setting = {2, 1, 1, constraints, 12, NULL};
    cormoran_zmk_custom_settings_SettingMeta meta;
    assert(setting_meta_to_proto(&setting, &meta) == 0);
    assert(meta.confidentiality == 2 && meta.read_permission == 1 && meta.write_permission == 1);
    for (unsigned pass = 0; pass < 2; pass++) {
        pb_ostream_t stream = {0};
        assert(meta.constraints.funcs.encode(&stream, NULL, &meta.constraints.arg));
        assert(stream.count == 12 && stream.tags == 12);
        for (unsigned i = 0; i < 12; i++) assert(stream.values[i] == (int)i);
    }
    // A slot exposes its keyspace's payload metadata instead of empty slot metadata.
    struct zmk_custom_setting_keyspace keyspace = {constraints, 12};
    setting.constraints = NULL; setting.constraints_count = 0; setting.keyspace = &keyspace;
    constraints[1].type = 0; constraints[2].type = -1;
    pb_ostream_t stream = {0};
    assert(meta.constraints.funcs.encode(&stream, NULL, &meta.constraints.arg));
    assert(stream.count == 10 && stream.values[1] == 3);
    assert(keyspace.constraints_count == 12 && constraints[11].value == 11);
    stream = (pb_ostream_t){.fail_tag = true};
    assert(!meta.constraints.funcs.encode(&stream, NULL, &meta.constraints.arg));
    stream = (pb_ostream_t){.fail_value = true};
    assert(!meta.constraints.funcs.encode(&stream, NULL, &meta.constraints.arg));
    setting.keyspace = NULL;
    stream = (pb_ostream_t){0};
    assert(meta.constraints.funcs.encode(&stream, NULL, &meta.constraints.arg));
    assert(stream.count == 0);
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "test.c").write_text(preamble + prepare_custom_settings.STREAMING_METADATA + tests)
            subprocess.run([compiler, "-std=c11", "-Wall", "-Wextra", "-Werror",
                            str(root / "test.c"), "-o", str(root / "test")], check=True)
            subprocess.run([str(root / "test")], check=True)
