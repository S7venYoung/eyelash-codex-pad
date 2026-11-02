# ZMK's behavior headers are private to the app target on this DYA baseline.
target_sources_ifdef(CONFIG_ZMK_BEHAVIOR_EYELASH_DFU app PRIVATE src/behavior_eyelash_dfu.c)
