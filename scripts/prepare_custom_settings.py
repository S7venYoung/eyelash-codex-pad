#!/usr/bin/env python3
"""Stream Custom Settings metadata without changing the DYA wire protocol."""
import argparse
import hashlib
from pathlib import Path
import subprocess

REVISION = "c6a7fef3a3be3d3ace5de9a4b0628c6418cd1f3f"
HANDLER = "src/studio/custom_settings_handler.c"
OPTIONS = "proto/cormoran/zmk/custom_settings/custom_settings.options"
HASHES = {
    HANDLER: "5859044d6dea01abdace75f335bcb1984dc4f59804df4f658cbd1165967bc1d7",
    OPTIONS: "95d0e48e5b6b3291bfcc3657c01b51ec7bb599bf0ab74c5d35e79169be7ea9b3",
}

STREAMING_METADATA = """static bool encode_setting_constraints(pb_ostream_t *stream, const pb_field_t *field,
                                       void *const *arg) {
    const struct zmk_custom_setting *setting = *arg;
    const struct zmk_custom_setting_keyspace *keyspace = zmk_custom_setting_keyspace_of(setting);
    const struct zmk_custom_setting_constraint *constraints =
        keyspace ? keyspace->constraints : setting->constraints;
    size_t count = keyspace ? keyspace->constraints_count : setting->constraints_count;

    // Protobuf sizing and writing may both call this function. Do not consume
    // an iterator or mutate settings. Descriptors remain owned by the registry.
    for (size_t i = 0; i < count; i++) {
        if (constraints[i].type == ZMK_CUSTOM_SETTING_CONSTRAINT_NONE) {
            continue;
        }
        cormoran_zmk_custom_settings_SettingConstraint constraint =
            cormoran_zmk_custom_settings_SettingConstraint_init_zero;
        if (constraint_to_proto(&constraints[i], &constraint) < 0) {
            continue;
        }
        if (!pb_encode_tag_for_field(stream, field) ||
            !pb_encode_submessage(stream, cormoran_zmk_custom_settings_SettingConstraint_fields,
                                  &constraint)) {
            return false;
        }
    }
    return true;
}

static int setting_meta_to_proto(const struct zmk_custom_setting *setting,
                                 cormoran_zmk_custom_settings_SettingMeta *dest) {
    *dest = (cormoran_zmk_custom_settings_SettingMeta)
        cormoran_zmk_custom_settings_SettingMeta_init_zero;
    dest->confidentiality = proto_confidentiality(setting->confidentiality);
    dest->read_permission = proto_permission(setting->read_permission);
    dest->write_permission = proto_permission(setting->write_permission);
    dest->constraints.funcs.encode = encode_setting_constraints;
    dest->constraints.arg = (void *)setting;
    return 0;
}"""


def patch_file(relative, original):
    original = original.replace("\r\n", "\n").rstrip() + "\n"
    if hashlib.sha256(original.encode()).hexdigest() != HASHES[relative]:
        raise ValueError(f"Unexpected pinned Custom Settings source: {relative}")
    if relative == OPTIONS:
        return original.replace(
            "cormoran.zmk.custom_settings.SettingMeta.constraints max_count:8",
            "cormoran.zmk.custom_settings.SettingMeta.constraints type:FT_CALLBACK", 1)
    start = original.index("static int setting_meta_to_proto(")
    opening = original.index("{", start)
    depth, end = 1, opening + 1
    while depth:
        if original[end] == "{":
            depth += 1
        elif original[end] == "}":
            depth -= 1
        end += 1
    result = original[:start] + STREAMING_METADATA + original[end:]
    old_log = '''        LOG_DBG("Custom settings proto meta ready: subsystem=%s key=%s constraints=%u",
                setting->custom_subsystem_id, zmk_custom_setting_public_key(setting),
                (uint32_t)dest->meta.constraints_count);'''
    if old_log not in result:
        raise ValueError("Unexpected metadata log access")
    return result.replace(old_log, '''        LOG_DBG("Custom settings proto meta ready: subsystem=%s key=%s (streamed)",
                setting->custom_subsystem_id, zmk_custom_setting_public_key(setting));''', 1)


def prepare(directory):
    directory = Path(directory)
    head = subprocess.check_output(["git", "-C", str(directory), "rev-parse", "HEAD"], text=True).strip()
    if head != REVISION:
        raise ValueError("Custom Settings revision does not match manifest")
    candidates = []
    for relative in (HANDLER, OPTIONS):
        original = subprocess.check_output(["git", "-C", str(directory), "show",
                                            f"HEAD:{relative}"], text=True)
        candidate = patch_file(relative, original)
        target = directory / relative
        if target.read_text() not in (original, candidate):
            raise ValueError(f"Unrelated local edits: {relative}")
        candidates.append((target, candidate))
    for target, candidate in candidates:
        target.write_text(candidate)
    print("Custom Settings metadata: callback encoding, unchanged protobuf field numbers")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("module", type=Path)
    prepare(parser.parse_args().module)
