# XiaoZhi ESP32 项目完整概览

本文档提供 xiaozhi-esp32 仓库的全面深入分析，包括架构、模块、构建流程和开发指南。

## 📋 项目核心信息

**xiaozhi-esp32** 是一个功能完整的 ESP32 AI 语音助手固件项目，具有以下特点：

- **🎯 当前版本**: v2.1.0
- **🔧 支持芯片**: ESP32, ESP32-C3, ESP32-S3, ESP32-P4, ESP32-C6
- **🎛️ 硬件板型**: 支持 **110+ 开源硬件板型**
- **🌐 通信协议**: WebSocket 和 MQTT+UDP 混合协议
- **🤖 AI 集成**: 基于 MCP 协议与 AI 模型（Qwen/DeepSeek）交互
- **🎙️ 完整语音管道**: 唤醒词检测 → 音频流式传输 → LLM 处理 → TTS 播放

---

## 🏗️ 核心架构

### 1. 音频系统 (main/audio/)

**双任务音频管道架构**：

```
麦克风 → 扬声器路径:
  Mic (硬件编解码器)
    → [AudioInputTask]
    → 输入重采样（→16kHz 如需）
    → 音频处理（AFE/VAD/AEC）
    → 唤醒词检测（ESP-SR）
    → 编码队列
    → [OpusCodecTask: 编码器]
    → 发送队列
    → 协议（WebSocket/MQTT）
    → 服务器

扬声器 ← 服务器路径:
  服务器
    → 协议接收
    → 解码队列
    → [OpusCodecTask: 解码器]
    → 输出重采样（→编解码器速率）
    → 播放队列
    → [AudioOutputTask]
    → Speaker (硬件编解码器)
```

**关键音频参数**:
- Opus 帧长: 60ms
- 编码采样率: 16kHz 单声道
- 服务器采样率: 24kHz（可配置）
- 队列大小: 40 个数据包（2400ms 缓冲）
- 硬件编解码器速率: 板级特定（通常 16kHz-48kHz）

**支持的硬件编解码器**:
- ES8311 Audio Codec
- ES8374 Audio Codec
- ES8388 Audio Codec
- ES8389 Audio Codec
- Espressif Box Audio Codec
- Dummy/No Audio Codec

**关键文件**:
- `main/audio/audio_service.h/cc` - 音频管道编排器
- `main/audio/audio_codecs/*.cc` - 硬件编解码器驱动
- `main/audio/audio_processor.h/cc` - AFE/VAD/AEC 处理
- `main/audio/wake_word.cc` - ESP-SR 唤醒词检测
- `main/audio/opus_encoder.cc` / `opus_decoder.cc` - Opus 编解码
- `main/audio/rate_converter.cc` - 采样率重采样

---

### 2. 设备状态机 (main/device_state_machine.h/cc)

**10 个设备状态的完整状态机**：

```
kDeviceStateStarting
  → kDeviceStateWifiConfiguring
    → kDeviceStateActivating
      → kDeviceStateIdle
        ↓↑ (listening/speaking/connecting)
      ← kDeviceStateListening
      ← kDeviceStateSpeaking
      ← kDeviceStateConnecting
      ← kDeviceStateUpgrading
      ← kDeviceStateAudioTesting
      ← kDeviceStateFatalError
```

**状态变化触发**:
- 显示界面更新
- LED 指示灯变化
- 音频行为改变

---

### 3. MCP 服务器实现 (main/mcp_server.h/cc)

**设备侧 MCP 服务器**，允许 AI 模型通过 JSON-RPC 2.0 调用设备工具。

**MCP 交互流程**:
```
1. 设备连接 → 发送 "hello" + {"mcp": true}
2. 服务器 → 发送 initialize 请求
3. 设备 → 响应 serverInfo + protocolVersion
4. 服务器 → 发送 tools/list 请求
5. 设备 → 响应可用工具数组及 JSON Schema
6. 服务器 → 发送 tools/call 请求（tool_name + arguments）
7. 设备 → 执行工具并返回结果或错误
```

**常见 MCP 工具**:
- `self.get_device_status` - 返回完整设备 JSON（状态、电池、网络等）
- `self.audio_speaker.set_volume` - 音量控制（0-100）
- `self.screen.set_brightness` - 显示亮度（0-100）
- 板级专用工具: LED 控制、舵机控制、GPIO、摄像头等

**添加自定义工具**:
```cpp
// 在板级初始化中
McpServer::GetInstance().AddTool(
    "self.my_tool",                // 工具名称
    "AI 可见的描述",                // 工具功能说明
    {
        {"param_name", McpPropertyType::kInt, true, 0, 100}  // 输入 schema
    },
    [](const cJSON* args) -> bool { // 回调函数
        // 工具实现
        return true;
    }
);
```

详见 `docs/mcp-protocol.md` 和 `docs/mcp-usage.md`。

---

### 4. 显示系统 (main/display/)

**多后端显示抽象** - 支持 5 种显示类型：

```cpp
Display (基类)
├── LcdDisplay       // SPI/QSPI LCD (ST7789, ILI9341, SH8601 等)
├── OledDisplay      // I2C OLED (SSD1306 等)
├── LvglDisplay      // LVGL 图形库，功能丰富
│   ├── Emoji 渲染
│   ├── 主题系统
│   ├── GIF 动画支持
│   └── 自定义字体
├── EmoteDisplay     // 情感化极简 UI
└── NoDisplay        // 无头模式

线程安全: DisplayLockGuard (基于互斥锁)
```

**显示接口**:
```cpp
Display::SetStatus(status_string)
Display::SetChatMessage(role, content)
Display::SetEmotion(emotion_name)
Display::ShowNotification(message, duration_ms)
Display::UpdateStatusBar()  // 网络、电池、时间
Display::SetTheme(theme)
Display::SetPowerSaveMode(bool)
```

---

### 5. 通信协议层 (main/protocols/)

**两种协议实现**:

#### WebSocket 协议 (`websocket_protocol.cc`)
- 直接 WebSocket 连接
- 二进制协议 v1/v2/v3 支持
- 处理音频包 + JSON 控制消息
- 帧格式 v2: `[version(2) | type(2) | reserved(4) | timestamp(4) | size(4) | payload]`
- 帧格式 v3: `[type(1) | reserved(1) | size(2) | payload]`

#### MQTT+UDP 协议 (`mqtt_protocol.cc`)
- MQTT 用于控制消息
- UDP 用于音频流（AES 加密）
- 序列号支持数据包排序
- 重连计时器: 60 秒间隔

**协议接口**:
```cpp
Protocol::Start()                    // 连接到服务器
Protocol::OpenAudioChannel()         // 开始音频流
Protocol::SendAudio(packet)          // 发送编码音频
Protocol::SendText(json)             // 发送控制消息

// 回调:
OnIncomingAudio(packet)
OnIncomingJson(json)
OnAudioChannelOpened/Closed()
OnConnected/Disconnected()
OnNetworkError(message)
```

---

### 6. 板型抽象层 (main/boards/)

**硬件抽象，支持 110+ 板型配置**

#### 板型层次结构:
```cpp
Board (基类)
├── WifiBoard (WiFi 基础板型)
│   ├── EspBox3Board
│   ├── M5StackCoreS3Board
│   ├── LilygoBoards
│   └── [70+ WiFi 变体]
│
├── DualNetworkBoard (WiFi + 4G 蜂窝网络)
│   └── ML307 调制解调器板型
│
└── [自定义板型实现]
```

#### 板型接口方法:
```cpp
Board::GetAudioCodec()           // 硬件音频编解码器实例
Board::GetDisplay()              // 显示驱动实例
Board::GetNetwork()              // 网络接口
Board::GetLed()                  // LED 控制器
Board::GetBacklight()            // 背光控制器
Board::GetCamera()               // 摄像头接口（可选）
Board::GetBatteryLevel()         // 电池信息
Board::GetDeviceStatusJson()     // 完整设备状态
```

#### 板型配置结构:
```
main/boards/{board-name}/
├── {board}_board.cc      # 板级类实现
├── config.h              # GPIO 脚位、采样率、显示参数
├── config.json           # 构建元数据（目标芯片、sdkconfig 选项）
└── README.md             # 板级专用文档
```

#### 支持的主要硬件品牌:

| 品牌 | 板型示例 | 数量 |
|------|---------|------|
| Espressif | esp-box, esp-box-3, esp-box-lite, esp-s3-lcd-ev-board | 6+ |
| M5Stack | m5stack-core-s3, m5stack-tab5, atom-echos3r | 3+ |
| LILYGO | lilygo-t-circle-s3, lilygo-t-cameraplus-s3 | 2+ |
| Waveshare | waveshare-s3-touch-amoled-*, waveshare-c6-* | 12+ |
| 荔枝派 | lichuang-c3-dev, lichuang-dev | 2+ |
| Bread Compact | bread-compact-wifi, bread-compact-ml307 | 6+ |
| 小智立方 | xingzhi-cube-* | 4+ |
| 其他 | ATK、kevin、movecall 等 | 70+ |

#### 创建自定义板型:
1. 复制相似板型目录作为模板
2. 修改 `config.h` 设置 GPIO 脚位和硬件参数
3. 更新 `config.json` 设置目标芯片和 Flash 大小
4. 在 `.cc` 文件中实现板级专用初始化
5. 添加到 `main/Kconfig.projbuild`（choice BOARD_TYPE）
6. 添加到 `main/CMakeLists.txt`（板型映射）
7. 使用 `python scripts/release.py {board-name}` 构建

详见 `docs/custom-board.md`。

---

### 7. 主事件循环 (Application::Run)

**基于 FreeRTOS 事件组的事件驱动架构**:

```cpp
事件处理器:
├─ MAIN_EVENT_NETWORK_CONNECTED → InitializeProtocol() + ActivationTask
├─ MAIN_EVENT_NETWORK_DISCONNECTED → CloseAudioChannel()
├─ MAIN_EVENT_SEND_AUDIO → PopPacketFromSendQueue() → protocol_->SendAudio()
├─ MAIN_EVENT_WAKE_WORD_DETECTED → OpenAudioChannel() + SetState(Listening)
├─ MAIN_EVENT_START_LISTENING → 启用语音处理
├─ MAIN_EVENT_STOP_LISTENING → 禁用语音处理
├─ MAIN_EVENT_TOGGLE_CHAT → 切换监听模式
├─ MAIN_EVENT_STATE_CHANGED → 更新显示 + LED
├─ MAIN_EVENT_CLOCK_TICK → 更新状态栏（1Hz）
├─ MAIN_EVENT_SCHEDULE → 执行排队的回调（线程安全）
└─ MAIN_EVENT_ERROR → 显示警报 + 返回空闲
```

线程安全事件发布: `Application::PostEvent()` 和 `Application::Schedule()`

---

## 📦 项目目录结构

```
xiaozhi-esp32/
├── main/                          # 主应用源代码
│   ├── boards/                    # 110+ 硬件板型配置
│   ├── audio/                     # 音频处理系统
│   ├── display/                   # 显示驱动系统
│   ├── led/                       # LED 控制
│   ├── protocols/                 # 通信协议（WebSocket/MQTT+UDP）
│   ├── assets/                    # 资源管理
│   ├── application.h/cc           # 主应用类和事件循环
│   ├── board.h/cc                 # 板级抽象接口
│   ├── device_state_machine.h/cc  # 设备状态机（10 个状态）
│   ├── mcp_server.h/cc            # MCP 服务器
│   ├── settings.h/cc              # NVS 配置存储
│   ├── system_info.h/cc           # 设备信息采集
│   ├── ota.h/cc                   # OTA 固件升级
│   ├── main.cc                    # 程序入口点
│   ├── CMakeLists.txt             # 构建配置
│   ├── Kconfig.projbuild          # 配置菜单定义
│   └── idf_component.yml          # 组件描述
│
├── docs/                          # 文档资源
│   ├── custom-board.md            # 自定义板型指南
│   ├── mcp-protocol.md            # MCP 协议详细说明
│   ├── mcp-usage.md               # MCP 使用示例
│   ├── websocket.md               # WebSocket 协议文档
│   ├── mqtt-udp.md                # MQTT+UDP 混合协议
│   ├── blufi.md                   # WiFi 配网文档
│   └── v0/, v1/                   # 历史版本文档
│
├── scripts/                       # 构建和工具脚本
│   ├── release.py                 # 自动化编译和打包脚本
│   ├── build_default_assets.py    # 构建默认资源
│   ├── audio_debug_server.py      # 音频调试工具
│   ├── gen_lang.py                # 语言文件生成
│   ├── mp3_to_ogg.sh              # 音频转换
│   ├── Image_Converter/           # 图片转换工具
│   ├── acoustic_check/            # 音频检查工具
│   ├── ogg_converter/             # OGG 转换工具
│   ├── spiffs_assets/             # SPIFFS 资源工具
│   └── p3_tools/                  # Python 3 工具集
│
├── partitions/                    # 分区表配置
│   └── v2/
│       ├── 8m.csv                 # 8MB Flash 分区表
│       ├── 16m.csv                # 16MB Flash 分区表（标准）
│       ├── 16m_c3.csv             # ESP32-C3 优化的 16MB 分区
│       ├── 32m.csv                # 32MB Flash 分区表
│       └── README.md              # v2 分区表说明
│
├── CMakeLists.txt                 # 根构建配置（定义项目版本 2.1.0）
├── sdkconfig.defaults             # 默认全局配置
├── sdkconfig.defaults.esp32*      # 各芯片专用默认配置（6 个）
├── README.md                       # 英文项目说明
├── README_zh.md                   # 中文项目说明
├── README_ja.md                   # 日文项目说明
├── LICENSE                        # MIT 许可证
└── CLAUDE.md                      # Claude Code 工作指南
```

---

## 🚀 构建和开发

### 初始设置

```bash
# 设置目标芯片（首次构建或切换芯片时必需）
idf.py set-target esp32s3  # 或 esp32c3, esp32, esp32p4, esp32c6

# 清理旧构建（推荐在切换板型时执行）
idf.py fullclean
```

### 配置与构建

```bash
# 交互式配置菜单
idf.py menuconfig
# 导航: Xiaozhi Assistant → Board Type → 选择板型

# 构建固件
idf.py build

# 烧录并监控
idf.py flash monitor

# 烧录特定分区
idf.py storage-flash   # 烧录 SPIFFS 分区
```

### 自动化板型构建（推荐）

```bash
# 读取 main/boards/{board}/config.json，自动处理所有配置
python scripts/release.py {board-name}

# 示例:
python scripts/release.py esp-box-3
python scripts/release.py m5stack-core-s3
python scripts/release.py lichuang-c3-dev

# 此脚本:
# - 读取 config.json 中的目标芯片
# - 应用 sdkconfig_append 选项
# - 构建并打包固件到 releases/v{version}_{name}.zip
```

### 资源生成

```bash
# 构建默认资源（字体、表情符号、唤醒词）
python scripts/build_default_assets.py

# 自定义资源生成器（独立仓库）
# https://github.com/78/xiaozhi-assets-generator
```

---

## ⚙️ 关键构建配置

### 分区表

- **v2 与 v1 不兼容** - 需要手动烧录（无法从 v1 OTA 升级到 v2）
- 分区表位置: `partitions/v2/`（4m.csv, 8m.csv, 16m.csv, 32m.csv）
- 根据 Flash 大小在 `config.json` 中选择正确的分区表

### IDF 版本

- **要求: ESP-IDF 5.4 或更高版本**
- 推荐 Linux（编译更快，驱动问题更少）

### 芯片支持

- ESP32, ESP32-C3, ESP32-S3, ESP32-P4, ESP32-C6
- 构建前设置目标: `idf.py set-target {chip}`

### AEC 配置

- **设备侧 AEC** (`CONFIG_USE_DEVICE_AEC=y`) - 仅限 ESP32-S3/P4
- **服务器侧 AEC** (`CONFIG_USE_SERVER_AEC=y`) - 所有芯片
- **互斥** - 仅启用一个

### 唤醒词检测

- ESP32-S3/P4: ESP-SR 唤醒词引擎
- ESP32-C3/C6: 有限的唤醒词支持（仅自定义模型）
- 可禁用: `CONFIG_WAKE_WORD_DISABLED=y`

### 常用 sdkconfig 选项

```
CONFIG_ESPTOOLPY_FLASHSIZE_4MB=y    # 4MB Flash
CONFIG_ESPTOOLPY_FLASHSIZE_8MB=y    # 8MB Flash
CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y   # 16MB Flash

CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions/v2/8m.csv"

CONFIG_USE_DEVICE_AEC=y             # 设备侧 AEC
CONFIG_USE_SERVER_AEC=y             # 服务器侧 AEC
CONFIG_WAKE_WORD_DISABLED=y         # 禁用唤醒词

CONFIG_LANGUAGE_ZH_CN=y             # 中文
CONFIG_LANGUAGE_EN_US=y             # 英文
CONFIG_LANGUAGE_JA_JP=y             # 日语
```

---

## 🧑‍💻 代码风格与模式

### 设计模式

- **单例模式**: Application, Board, McpServer
- **工厂模式**: Board::create_board()
- **观察者模式**: 状态变化监听器、事件回调
- **策略模式**: 协议实现（WebSocket vs MQTT）
- **事件驱动**: FreeRTOS 事件组

### 线程模型

```
主任务:
├─ Application::Run() [事件循环 - 永不返回]
└─ 事件驱动处理器

后台任务:
├─ AudioInputTask        [麦克风 → 编码]
├─ AudioOutputTask       [解码 → 扬声器]
├─ OpusCodecTask         [Opus 编解码]
├─ ActivationTask        [设备注册]
├─ Network Tasks         [WiFi/MQTT/WebSocket]
├─ Wake Word Task        [ESP-SR 检测]
└─ Clock Timer Task      [1Hz 状态更新]

同步机制:
├─ FreeRTOS 事件组 (event_group_)
├─ 互斥锁 (audio_queue_mutex_, decoder_mutex_)
├─ 条件变量 (audio_queue_cv_)
└─ 原子标志 (voice_detected_, service_stopped_)
```

### 代码风格

- **Google C++ 风格** - 提交代码前请确保符合规范
- 从多个线程修改显示时使用 `DisplayLockGuard`
- 使用 `Application::Schedule()` 进行线程安全的主循环回调
- 音频队列使用互斥锁 + 条件变量模式
- 状态变化通过 `Application::PostEvent()` 触发事件

---

## 🛠️ 常见开发任务

### 调试音频问题

```bash
# 使用音频调试服务器捕获原始音频
python scripts/audio_debug_server.py

# 检查音频日志
idf.py monitor | grep "AUDIO"

# 常见问题:
# - 采样率错误 → 检查 config.h 中的 AUDIO_INPUT_SAMPLE_RATE
# - 编解码器未初始化 → 检查 I2C 脚位和编解码器地址
# - 无唤醒词 → 检查 ESP-SR 模型与芯片的兼容性
# - 音频失真 → 检查重采样器质量设置
```

### 添加新板型

1. 参考 `main/boards/` 中的类似硬件
2. 创建目录: `main/boards/my-board/`
3. 复制并修改: `config.h`, `config.json`, `my_board.cc`
4. 在 `main/Kconfig.projbuild` 中添加 Kconfig 条目
5. 在 `main/CMakeLists.txt` 中添加 CMake 映射
6. 测试构建: `python scripts/release.py my-board`

### 修改协议行为

- WebSocket: `main/protocols/websocket_protocol.cc`
- MQTT+UDP: `main/protocols/mqtt_protocol.cc`
- 协议选择: `main/protocols/protocol.cc`（工厂）
- 消息处理器: `Application::OnIncomingJson()`

### 添加 MCP 工具

```cpp
// 在板级初始化或 Application::Initialize() 中
McpServer::GetInstance().AddTool(
    "self.category.action",
    "AI 可见的描述",
    {
        {"param1", McpPropertyType::kString, true},
        {"param2", McpPropertyType::kInt, false, 0, 100}
    },
    [](const cJSON* args) -> int {
        // 工具实现
        return result;
    }
);
```

---

## 📚 关键文件参考

### 核心应用

- `main/main.cc` - 入口点
- `main/application.h/cc` - 主应用单例和事件循环
- `main/device_state_machine.h/cc` - 状态机（10 个状态）
- `main/settings.h/cc` - NVS flash 持久化（WiFi、音量等）
- `main/system_info.h/cc` - 设备遥测
- `main/ota.h/cc` - OTA 固件更新

### 音频系统

- `main/audio/audio_service.h/cc` - 音频管道编排器
- `main/audio/audio_codecs/` - 硬件编解码器驱动
- `main/audio/opus_encoder.cc` / `opus_decoder.cc` - Opus 编解码
- `main/audio/rate_converter.cc` - 采样率重采样
- `main/audio/audio_processor.h/cc` - AFE/VAD/AEC
- `main/audio/wake_word.cc` - 唤醒词检测

### 网络

- `main/protocols/protocol.cc` - 协议工厂
- `main/protocols/websocket_protocol.cc` - WebSocket 实现
- `main/protocols/mqtt_protocol.cc` - MQTT+UDP 实现

### MCP 服务器

- `main/mcp_server.h/cc` - MCP 服务器和工具注册
- `docs/mcp-protocol.md` - 协议文档
- `docs/mcp-usage.md` - 使用示例

### 显示和 UI

- `main/display/display.h` - 显示基类
- `main/display/lcd_display.cc` - LCD 驱动
- `main/display/lvgl_display/` - LVGL 图形
- `main/display/oled_display.cc` - OLED 驱动

### 板型抽象

- `main/board.h/cc` - 板型基类
- `main/boards/` - 110+ 板型配置
- `main/boards/wifi_board.h/cc` - WiFi 板型基类
- `main/boards/dual_network_board.h/cc` - WiFi+4G 基类

### 构建系统

- `CMakeLists.txt` - 根构建配置
- `main/CMakeLists.txt` - 主组件构建
- `main/Kconfig.projbuild` - 配置选项
- `sdkconfig.defaults*` - 各芯片默认配置
- `scripts/release.py` - 自动化构建脚本

---

## 📖 文档资源

| 文档 | 说明 |
|------|------|
| **README.md** | 主项目文档 |
| **custom-board.md** | 创建自定义板型 |
| **mcp-protocol.md** | MCP 协议规范 |
| **mcp-usage.md** | MCP 使用指南 |
| **websocket.md** | WebSocket 协议详情 |
| **mqtt-udp.md** | MQTT+UDP 协议详情 |
| 板级文档 | `main/boards/{board}/README.md` |

---

## 🌐 相关资源

- **官方服务器:** https://xiaozhi.me（免费 Qwen 实时模型）
- **QQ 群:** 1011329060
- **文档:** https://ccnphfhqs21z.feishu.cn/wiki/F5krwD16viZoF0kKkvDcrZNYnhb
- **自定义资源生成器:** https://github.com/78/xiaozhi-assets-generator
- **ESP-IDF 文档:** https://docs.espressif.com/projects/esp-idf/
- **ESP-SR（唤醒词）:** https://github.com/espressif/esp-sr

---

## 📊 项目统计

| 项目 | 数量 |
|------|------|
| 硬件板型 | 110+ |
| 板型文档 | 73 个 README.md |
| 编解码器驱动 | 6 个（ES8311/8374/8388/8389 + Box + Dummy） |
| 显示类型 | 5 种（LCD、OLED、LVGL、Emote、Headless） |
| 通信协议 | 2 个（WebSocket、MQTT+UDP） |
| 设备状态 | 10 个 |
| 支持语言 | 20+ 种 |
| 分区表配置 | 4 个（8m、16m、16m_c3、32m） |
| 支持 ESP 芯片 | 5 个（ESP32、C3、S3、P4、C6） |

---

## 🎯 核心数据流

### 程序入口

```cpp
// main/main.cc - 程序入口点
extern "C" void app_main(void) {
    // 初始化 NVS flash（WiFi 配置存储）
    // 初始化并运行应用
    Application::GetInstance().Initialize();
    Application::GetInstance().Run();  // 主事件循环，永不返回
}

// 应用初始化顺序 (application.cc)
Application::Initialize() {
    → Board::GetInstance()           // 板级硬件抽象
    → Display 初始化                 // 显示驱动
    → AudioService 初始化            // 音频管道
    → McpServer 工具注册             // MCP 服务器
    → DeviceStateMachine 创建        // 状态机（10 个状态）
    → Protocol 初始化                // WebSocket 或 MQTT+UDP
}

// 主事件循环 (FreeRTOS)
Application::Run() {
    ├─ MAIN_EVENT_NETWORK_CONNECTED
    ├─ MAIN_EVENT_WAKE_WORD_DETECTED
    ├─ MAIN_EVENT_SEND_AUDIO
    ├─ MAIN_EVENT_STATE_CHANGED
    ├─ MAIN_EVENT_CLOCK_TICK
    └─ ... 其他 10+ 事件
}
```

---

## 💡 开发建议

1. **添加新板型**: 复制相似板型目录，修改 `config.h` 和 `config.json`
2. **调试音频**: 使用 `scripts/audio_debug_server.py` 捕获原始音频
3. **添加 MCP 工具**: 在板级初始化中调用 `McpServer::AddTool()`
4. **遵循代码风格**: Google C++ 风格
5. **线程安全**: 使用 `DisplayLockGuard` 和 `Application::Schedule()`
6. **状态变化**: 通过 `Application::PostEvent()` 触发事件
7. **参考文档**: 查看 `docs/` 目录获取详细的协议和实现指南

---

这个项目展现了一个完整、模块化的 ESP32 AI 应用架构，具有出色的硬件适配性和高度的可定制性。核心特点是将复杂的音频处理、通信协议和 MCP 整合在统一的框架下，使开发者能轻松为不同硬件适配固件。
