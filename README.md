# Eyelash Numpad：DYA ZMK + 蓝牙 DFU

nRF52832 的 16 键纯蓝牙数字小键盘。保留原 RMK 默认层键位，接入 DYA 动态改键、运行时宏、Tap Dance、Combo 和蓝牙 DFU。编码器、轨迹球、鼠标输入处理器及显示模块不接入。

**状态：2026-11-02 Actions 41372417099 全部成功（固件提交 daf7d73f3bd731ac38f2daa18c6d9f84314ac412）。18 项主机检查、ZMK、Bootloader 和打包通过。应用 Flash 225,344 / 290,816 字节，RAM 62,920 / 65,536 字节。产物已复核；尚未刷写或实机验证。测试生成的合成镜像不能当作固件使用。**

## 键位与 DYA

默认层按原固件保留，不按图案键帽猜测：

| 7 | 8 | 9 | / |
|---|---|---|---|
| 4 | 5 | 6 | * |
| 1 | 2 | 3 | − |
| Enter（长按 Fn） | 0 | . | + |

Fn 层：

| Num Lock | Enter | Delete | Backspace |
|---|---|---|---|
| 静音 | 音量加 | 音量减 | 空 |
| 蓝牙配置 1 | 蓝牙配置 2 | 蓝牙配置 3 | 空 |
| Fn | 空 | 解锁 DYA | 蓝牙 DFU |

- 共 4 层：Numpad、Fn、Custom 1、Custom 2。后两层初始为透明，不改变默认输入。
- DYA 通过当前已配对主机的加密 BLE GATT 连接，不配置 USB/串口传输。
- 进入 DYA 前，按住左下角，再按小数点键解锁。保存修改后重新开机检查持久化。
- 8 个运行时宏，共享 1024 字节名字/内容池；单宏编码上限 256 字节，动作队列 32。长文本占用取决于编码，不等同于固定字符数。
- 8 个运行时 Tap Dance，共享 512 字节名字/动作池，最多同时处理 4 个序列；支持单击、双击、三击。
- 8 个运行时 Combo，每组最多 4 个物理键。
- 内置 Mod-Tap、Layer-Tap、Sticky Key、层切换、Caps Word、Repeat 和默认 Grave/Escape Mod-Morph 行为，可由 DYA 选择。它们的编译期结构/时序与运行时宏、Tap Dance、Combo 的编辑能力不同，不宣称所有原生行为参数都能动态创建。
- 宏和 Tap Dance 初始为空，通过 DYA 创建后绑定到任意键；没有预绑会改变数字输入的演示宏。
- 已补齐 16 键物理布局及行为元数据。DYA Device Info 和核心 Settings RPC 也启用。

DYA 分支为 cormoran 的 `main+dya` 固定提交；不把它表述为官方 ZMK 的某个发布版。宏/Tap Dance/Combo/custom-settings 模块均固定提交。见 `config/west.yml`。

## 硬件与 Flash

硬件依据为本地原始 eyelash-numpad 的 keyboard.toml、memory.x、.cargo/config.toml，与原仓库 RMK 配置一致。照片为 4 行 × 4 列。

- nRF52832 xxAA，512 KiB Flash、64 KiB RAM。
- 行 P0.27/P0.28/P0.03/P0.04；列 P0.05/P0.07/P0.09/P0.25；col2row。
- P0.09 使用 GPIO，禁用 NFC 用途。电池 P0.02=AIN0，分压比 2000/2806。
- 内部 RC 低频时钟。不驱动未知的 LED/UART 引脚，不新增复位脚映射。
- USB 仅作供电/充电；无 USB HID 或拖拽 UF2 功能。

| Flash 地址（含首尾） | 用途 | 大小 |
|---|---|---|
| 0x00000–0x25FFF | MBR + Nordic S132 6.1.1 | 152 KiB |
| 0x26000–0x6CFFF | DYA ZMK 应用 | 284 KiB |
| 0x6D000–0x73FFF | ZMK 设置和绑定 | 28 KiB |
| 0x74000–0x7DFFF | Adafruit Bootloader | 40 KiB |
| 0x7E000–0x7EFFF | MBR 参数页 | 4 KiB |
| 0x7F000–0x7FFFF | DFU 状态页 | 4 KiB |

S132 仅供 Bootloader 蓝牙 DFU 使用，ZMK 运行时使用 Zephyr BLE 栈。固定 SoftDevice 的信息结构为 size=0x26000、FWID=0x00B7。应用大小超限时必须让构建/打包失败，不可覆盖设置区。

启用 LTO 和大小优化，关闭日志和无关硬件，限制蓝牙发送缓冲池。实际链接已通过，但 RAM 仅剩 2,616 字节静态余量；线程栈峰值、DYA 操作和蓝牙 DFU 仍需实机验证。

## 蓝牙 DFU

首次通过 SWD 安装配套 Bootloader 和 ZMK，之后可通过手机更新应用。

- 日常入口：按住左下角 Fn，再按右下角 +。
- 恢复入口：关机，按住顶行 7 和 9，开机后继续按住约 1 秒。这由 Bootloader 直接扫描矩阵，不依赖 ZMK 能正常启动。
- 应用无效时，Bootloader 默认进入蓝牙 DFU。
- DFU 广播名：`Eyelash_DFU`。
- 手机使用 Nordic **nRF Device Firmware Update**，选择 `eyelash-numpad-ota.zip` 和设备，传完等待重启。
- 只有安装此配套 Bootloader 后，固件里的 DFU 按键才有效。

使用 **Adafruit Legacy DFU ZIP**，不是 Nordic Secure DFU protobuf 包。S132 要求 0x00B7，device type=0x0052、revision=0xADAF。使用上游默认 CRC16 完整性校验，没有固件签名认证；仅在主动进入的 DFU 模式接收升级。

采用单 Bank 以保留 nRF52832 应用空间，没有双 Bank 回滚保证。传输中断可能擦除旧应用；重新上电，应用无效时应回到 Eyelash_DFU，再传同一 ZIP。Bootloader 损坏或无法进入 DFU 时用 SWD 恢复。

日常应用 OTA 不写 ZMK 设置区；RMK 到 ZMK 的首次迁移不兼容旧配对，迁移后需重新配对。

## 源码适配内容

- [Adafruit nRF52 Bootloader](https://github.com/adafruit/Adafruit_nRF52_Bootloader)：固定提交见 bootloader/upstream.json。板级文件在 bootloader/boards/eyelash_numpad。
- bootloader/eyelash.patch：加入矩阵恢复入口，移除 nRF52832 的默认 UART 下载等待，关闭无 LED 时的 PWM 更新，保留未知的复位脚映射。默认应用无效回退到 OTA 的逻辑沿用上游。
- 自带 ZMK DFU behavior：写入 GPREGRET=0xA8 后直接复位，避免通用 reboot 路径覆盖请求值。入口约定也见开源 [Blueboot](https://github.com/te9no/zmk-feature-blueboot)，本项目不依赖其模块。
- scripts/prepare_zmk.py：仅对固定 DYA 源码应用 BLE Studio 修正，以 ATT MTU−3 限制 GATT indication，最大块 128 字节，避免用链路层长度推算而超出 ATT 限制。相关上游实现见 [BLE Studio 修正](https://github.com/cormoran/zmk/commit/494711c183e54de88a81b0cde111ce5acfd526e0)。源文件有其他变动时拒绝覆盖。
- scripts/prepare_custom_settings.py：对固定 Custom Settings 版本将约束元数据改为逐项 protobuf 回调编码，移除响应/通知中重复的约 7 KiB 内联元数据数组；字段号与线上协议不变，不缩减 8 个宏、8 个 Tap Dance 和 8 个 Combo 的容量。低优先级栈为流式回调预留 3072 字节。
- scripts/firmware_artifacts.py：拒绝越界 HEX、错误向量、错误 S132/UICR、非应用 OTA，复核真实打包工具输出的二进制和 CRC16。

## 构建和产物

工作流 **Build Eyelash DYA ZMK and BLE DFU** 仅支持 workflow_dispatch。推送、开 PR 都不会由本分支工作流自动构建。已通过的构建见 [Actions 41372417099](https://github.com/S7venYoung/eyelash-codex-pad/actions/runs/41372417099)。

手动构建依次执行主机检查、DYA ZMK/Bootloader 编译、地址和升级包检查。下载最终 artifact `eyelash-numpad-zmk-swd-and-ble-dfu`：

- eyelash-numpad-first-install-swd.hex：首次 SWD 安装，包含 MBR、S132、Bootloader、ZMK 和 Bootloader/MBR 两个 UICR 地址。
- eyelash-numpad-ota.zip：后续手机蓝牙升级，仅包含应用。
- eyelash-numpad-zmk.hex：地址从 0x26000 开始的单独应用。
- eyelash-numpad-bootloader-s132.hex：Bootloader 和 S132。
- manifest.json：分区、应用大小和 SHA-256。
- README.md：安装和恢复说明。

另一个 artifact `eyelash-numpad-build-evidence` 保存 ELF、链接 map、实际 .config 和设备树，供检查 Flash/RAM 与功能开关。

本地主机检查（不编译固件）：

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-test.txt
PATH="$PWD/.venv/bin:$PATH" .venv/bin/python -m unittest discover -s tests -v
```

准备 Bootloader 源码（不编译、不刷写）：

```sh
python3 scripts/prepare_bootloader.py
```

编译 Bootloader 需 ARM GNU 工具链，命令为 `bash scripts/build_bootloader.sh`。ZMK 构建需先运行 `python3 scripts/prepare_zmk.py zmk` 和 `python3 scripts/prepare_custom_settings.py zmk-feature-custom-settings`，并传入 `-DZMK_EXTRA_MODULES=<本仓库绝对路径>`；本仓库 Zephyr module 注册板级和 DFU behavior。

## 首次从 RMK 迁移

先通过 SWD 只读备份完整 Flash 和 UICR。开启读保护时停止，不自动执行 recover。取得经过编译和镜像检查的首次安装 HEX 后，迁移需要擦除旧 Flash/UICR，写入合并 HEX 并校验。若备份存在自定义复位脚映射，应确认后单独处理。

J-Link/nrfjprog 参考命令，脚本不会自动执行：

```sh
# 只读备份
nrfjprog -f NRF52 --readcode rmk-flash-backup.hex
nrfjprog -f NRF52 --readuicr rmk-uicr-backup.hex

# 以下是备份后执行的首次迁移，会清除旧固件和配对
nrfjprog -f NRF52 --eraseall
nrfjprog -f NRF52 --program eyelash-numpad-first-install-swd.hex --verify
nrfjprog -f NRF52 --reset
```

首次启动验证 16 键、Fn、休眠唤醒、电池显示，再验证 DYA 连接、解锁、改键、宏/Tap Dance/Combo 保存和重启恢复，最后验证 BLE DFU 成功、中断重试和硬件恢复组合。

## 证据边界

主机测试验证地址检查、真实 DFU 工具的合成升级包、恢复 GPIO 逻辑、MTU 修正和配置一致性。Actions 已另外证明固件可编译、静态内存分配未超限、最终升级包通过镜像检查。实物矩阵接线、运行时栈峰值、蓝牙重连、DYA 编辑持久化和蓝牙更新仍需实机验收。
