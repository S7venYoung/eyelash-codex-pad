// SPDX-License-Identifier: MIT
#define DT_DRV_COMPAT eyelash_behavior_dfu

#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/irq.h>
#include <nrfx.h>
#include <drivers/behavior.h>
#include <zmk/behavior.h>

static int enter_dfu(struct zmk_behavior_binding *binding,
                     struct zmk_behavior_binding_event event) {
    ARG_UNUSED(binding);
    ARG_UNUSED(event);
    // The generic Nordic sys_reboot path can replace GPREGRET with a reboot
    // type. Write Adafruit's OTA request and reset directly so 0xA8 survives.
    (void)irq_lock();
    NRF_POWER->GPREGRET = 0xA8;
    __DSB();
    NVIC_SystemReset();
    return ZMK_BEHAVIOR_OPAQUE;
}

static const struct behavior_driver_api eyelash_dfu_api = {
    .binding_pressed = enter_dfu,
    .locality = BEHAVIOR_LOCALITY_EVENT_SOURCE,
#if IS_ENABLED(CONFIG_ZMK_BEHAVIOR_METADATA)
    .get_parameter_metadata = zmk_behavior_get_empty_param_metadata,
#endif
};

#define EYELASH_DFU_INST(n)                                                         \
    BEHAVIOR_DT_INST_DEFINE(n, NULL, NULL, NULL, NULL, POST_KERNEL,                    \
                            CONFIG_KERNEL_INIT_PRIORITY_DEFAULT, &eyelash_dfu_api);

DT_INST_FOREACH_STATUS_OKAY(EYELASH_DFU_INST)
