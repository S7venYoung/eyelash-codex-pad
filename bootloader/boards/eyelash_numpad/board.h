// SPDX-License-Identifier: MIT
#ifndef EYELASH_NUMPAD_BOARD_H
#define EYELASH_NUMPAD_BOARD_H

#include "nrfx.h"
#include "nrf_gpio.h"

// No LED/UART wiring is documented. Do not drive guessed pins.
#define LEDS_NUMBER 0
#define LED_STATE_ON 1
#define RX_PIN_NUMBER 0xFFFFFFFFu
#define TX_PIN_NUMBER 0xFFFFFFFFu
#define CTS_PIN_NUMBER 0xFFFFFFFFu
#define RTS_PIN_NUMBER 0xFFFFFFFFu
#define HWFC false
#define BLEDIS_MANUFACTURER "Eyelash"
#define BLEDIS_MODEL "Eyelash Numpad nRF52832"
#define UF2_PRODUCT_NAME "Eyelash Numpad (BLE DFU only)"
#define UF2_INDEX_URL "https://github.com/S7venYoung/eyelash-codex-pad"

// Match RMK col2row: columns source current, rows have pull-downs.
// Recovery chord is physical positions (0,0)+(0,2), labelled 7 and 9.
static inline bool eyelash_matrix_dfu_requested(void) {
    const uint32_t columns[] = {5, 7, 9, 25};
    bool held = true;
    for (unsigned i = 0; i < 4; i++) {
        nrf_gpio_cfg_default(columns[i]);
    }
    nrf_gpio_cfg_input(27, NRF_GPIO_PIN_PULLDOWN);
    for (unsigned sample = 0; sample < 4; sample++) {
        for (unsigned i = 0; i < 2; i++) {
            const uint32_t column = columns[i * 2];
            // Set the output latch before switching the pin to output.
            nrf_gpio_pin_set(column);
            nrf_gpio_cfg_output(column);
            NRFX_DELAY_US(200);
            held = (nrf_gpio_pin_read(27) != 0) && held;
            nrf_gpio_cfg_default(column);
            NRFX_DELAY_US(200);
        }
        NRFX_DELAY_US(5000);
    }
    nrf_gpio_cfg_default(27);
    return held;
}
#endif
