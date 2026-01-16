# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

XiaoZhi ESP32 is an MCP-based AI voice chatbot running on ESP32 hardware (C3/S3/P4/C6 chips). It provides voice interaction with large language models (Qwen/DeepSeek) and supports 70+ different hardware configurations. The firmware implements a complete voice assistant pipeline: wake word detection → audio streaming → LLM processing → TTS playback, with device control via MCP protocol.

**Current version:** v2.1.0 (incompatible with v1 partition table - cannot OTA upgrade from v1)

## Build Commands

### Initial Setup
```bash
# Set target chip (required before first build or when switching chips)
idf.py set-target esp32s3  # or esp32c3, esp32, esp32p4, esp32c6

# Clean previous builds (recommended when switching boards)
idf.py fullclean
```

### Configure & Build
```bash
# Interactive configuration menu
idf.py menuconfig
# Navigate to: Xiaozhi Assistant → Board Type → Select your board

# Build firmware
idf.py build

# Flash and monitor
idf.py flash monitor

# Flash specific partitions
idf.py storage-flash   # Flash SPIFFS partition
```

### Automated Board Build (Recommended)
```bash
# Build for a specific board (reads main/boards/{board}/config.json)
python scripts/release.py {board-name}

# Examples:
python scripts/release.py esp-box-3
python scripts/release.py m5stack-core-s3
python scripts/release.py lichuang-c3-dev

# This script:
# - Reads target chip from config.json
# - Applies sdkconfig_append options
# - Builds and packages firmware to releases/v{version}_{name}.zip
```

### Asset Generation
```bash
# Build default assets (fonts, emojis, wake words)
python scripts/build_default_assets.py

# Custom asset generator (separate repo)
# https://github.com/78/xiaozhi-assets-generator
```

## Architecture Overview

### Core Components & Data Flow

```
Entry Point: main/main.cc → app_main()
           ↓
Application::GetInstance().Initialize()
  ├─ Board::GetInstance() [hardware abstraction, 112+ configs]
  ├─ Display + UI initialization
  ├─ AudioService [dual-task audio pipeline]
  ├─ McpServer tool registration
  ├─ DeviceStateMachine [10 states]
  └─ Protocol [WebSocket or MQTT+UDP]
           ↓
Application::Run() [FreeRTOS event loop - never returns]
```

### Device State Machine (10 States)
`kDeviceStateStarting` → `kDeviceStateWifiConfiguring` → `kDeviceStateActivating` → `kDeviceStateIdle` → `kDeviceStateListening` → `kDeviceStateSpeaking` → `kDeviceStateConnecting` / `kDeviceStateUpgrading` / `kDeviceStateAudioTesting` / `kDeviceStateFatalError`

State transitions trigger display updates, LED changes, and audio behaviors.

### Audio Pipeline Architecture

**Two-way streaming with dedicated tasks:**

```
MICROPHONE → SPEAKER PATH:
  Mic (hardware codec)
    → [AudioInputTask]
    → Input Resampler (→16kHz if needed)
    → Audio Processors (AFE/VAD/AEC)
    → Wake Word Detection (ESP-SR)
    → Encode Queue
    → [OpusCodecTask: Encoder]
    → Send Queue
    → Protocol (WebSocket/MQTT)
    → Server

SPEAKER ← SERVER PATH:
  Server
    → Protocol
    → Decode Queue
    → [OpusCodecTask: Decoder]
    → Output Resampler (→codec rate)
    → Playback Queue
    → [AudioOutputTask]
    → Speaker (hardware codec)
```

**Key Audio Parameters:**
- Opus frame duration: 60ms
- Encoding sample rate: 16kHz mono
- Server sample rate: 24kHz (configurable)
- Queue sizes: 40 packets max (2400ms buffer)
- Hardware codec rates: Board-specific (typically 16kHz-48kHz)

**Critical Audio Components:**
- `main/audio/audio_service.h/cc` - Main orchestrator
- `main/audio/audio_codecs/*.cc` - Hardware codec drivers (ES8311, ES8388, etc.)
- `main/audio/audio_processor.h/cc` - AFE/VAD/AEC processing
- `main/audio/wake_word.cc` - ESP-SR wake word detection
- `main/audio/opus_encoder.cc` / `opus_decoder.cc` - Opus codec
- `main/audio/rate_converter.cc` - Sample rate resampling

### Main Event Loop (Application::Run)

**Event-driven architecture using FreeRTOS event groups:**

```cpp
Event Handlers:
├─ MAIN_EVENT_NETWORK_CONNECTED → InitializeProtocol() + ActivationTask
├─ MAIN_EVENT_NETWORK_DISCONNECTED → CloseAudioChannel()
├─ MAIN_EVENT_SEND_AUDIO → PopPacketFromSendQueue() → protocol_->SendAudio()
├─ MAIN_EVENT_WAKE_WORD_DETECTED → OpenAudioChannel() + SetState(Listening)
├─ MAIN_EVENT_START_LISTENING → Enable voice processing
├─ MAIN_EVENT_STOP_LISTENING → Disable voice processing
├─ MAIN_EVENT_TOGGLE_CHAT → Toggle listening mode
├─ MAIN_EVENT_STATE_CHANGED → Update display + LED
├─ MAIN_EVENT_CLOCK_TICK → Update status bar (1Hz)
├─ MAIN_EVENT_SCHEDULE → Execute queued callbacks (thread-safe)
└─ MAIN_EVENT_ERROR → Show alert + return to idle
```

Thread-safe event posting: `Application::PostEvent()` and `Application::Schedule()`

### Protocol Layer

**Two protocol implementations:**

**1. WebSocket Protocol (`main/protocols/websocket_protocol.cc`)**
- Direct WebSocket connection
- Binary protocol v1/v2/v3 support
- Handles audio packets + JSON control messages
- Frame format v2: `[version(2) | type(2) | reserved(4) | timestamp(4) | size(4) | payload]`
- Frame format v3: `[type(1) | reserved(1) | size(2) | payload]`

**2. MQTT+UDP Protocol (`main/protocols/mqtt_protocol.cc`)**
- MQTT for control messages
- UDP for audio streaming (AES-encrypted)
- Sequence numbers for packet ordering
- Reconnect timer: 60s interval

**Protocol Interface:**
```cpp
Protocol::Start()                    // Connect to server
Protocol::OpenAudioChannel()         // Begin audio streaming
Protocol::SendAudio(packet)          // Send encoded audio
Protocol::SendText(json)             // Send control messages

// Callbacks:
OnIncomingAudio(packet)
OnIncomingJson(json)
OnAudioChannelOpened/Closed()
OnConnected/Disconnected()
OnNetworkError(message)
```

### MCP Server Implementation

**Device-side MCP server for AI tool access** (`main/mcp_server.h/cc`)

The device acts as an MCP server, exposing tools that AI models can call via JSON-RPC 2.0:

```
MCP Interaction Flow:
1. Device connects → Sends "hello" with {"mcp": true}
2. Server sends: initialize request
3. Device responds: serverInfo + protocolVersion
4. Server sends: tools/list request
5. Device responds: Array of available tools with schemas
6. Server sends: tools/call request (tool_name + arguments)
7. Device executes tool → Returns result or error
```

**Common MCP Tools:**
- `self.get_device_status` - Returns full device JSON (state, battery, network, etc.)
- `self.audio_speaker.set_volume` - Volume control (0-100)
- `self.screen.set_brightness` - Display brightness (0-100)
- Board-specific tools: LED control, servo control, GPIO, camera, etc.

**Adding Custom Tools:**
```cpp
// In your board initialization:
McpServer::GetInstance().AddTool(
    "self.my_tool",                // Tool name
    "Description for AI",          // What the tool does
    {{"param_name", McpPropertyType::kInt, true, 0, 100}},  // Input schema
    [](const cJSON* args) -> bool { // Callback
        // Implementation
        return true;
    }
);
```

See `docs/mcp-protocol.md` for detailed protocol flow and `docs/mcp-usage.md` for usage examples.

### Board Abstraction Layer

**Hardware abstraction with 112+ board configurations** (`main/boards/`)

```cpp
Board Hierarchy:
├─ Board (base class)
│  ├─ WifiBoard (WiFi-based boards)
│  │  ├─ EspBox3Board
│  │  ├─ M5StackCoreS3Board
│  │  ├─ LilygoBoards
│  │  └─ [70+ WiFi variants]
│  │
│  ├─ DualNetworkBoard (WiFi + 4G cellular)
│  │  └─ ML307 modem boards
│  │
│  └─ [Custom board implementations]
```

**Board Interface Methods:**
```cpp
Board::GetAudioCodec()           // Hardware audio codec instance
Board::GetDisplay()              // Display driver instance
Board::GetNetwork()              // Network interface
Board::GetLed()                  // LED controller
Board::GetBacklight()            // Backlight controller
Board::GetCamera()               // Camera interface (optional)
Board::GetBatteryLevel()         // Battery info
Board::GetDeviceStatusJson()     // Full device state
```

**Board Configuration Structure:**
```
main/boards/{board-name}/
├─ {board}_board.cc      # Board class implementation
├─ config.h              # GPIO pins, sample rates, display params
├─ config.json           # Build metadata (target, sdkconfig options)
└─ README.md             # Board-specific documentation
```

**Creating a Custom Board:**
1. Copy similar board directory as template
2. Modify `config.h` for GPIO pins and hardware params
3. Update `config.json` with target chip and Flash size
4. Implement board-specific initialization in `.cc` file
5. Add to `main/Kconfig.projbuild` (choice BOARD_TYPE)
6. Add to `main/CMakeLists.txt` (board type mapping)
7. Build with `python scripts/release.py {board-name}`

See `docs/custom-board.md` for detailed custom board guide.

### Display System

**Multi-backend display abstraction** (`main/display/`)

```cpp
Display (base class)
├─ LcdDisplay       // SPI/QSPI LCD (ST7789, ILI9341, SH8601, etc.)
├─ OledDisplay      // I2C OLED (SSD1306, etc.)
├─ LvglDisplay      // LVGL graphics library with rich features
│  ├─ Emoji rendering
│  ├─ Theme system
│  ├─ GIF animation support
│  └─ Custom fonts
├─ EmoteDisplay     // Emotion-based minimalist UI
└─ NoDisplay        // Headless mode

Thread Safety: DisplayLockGuard (mutex-based)
```

**Display Interface:**
```cpp
Display::SetStatus(status_string)
Display::SetChatMessage(role, content)
Display::SetEmotion(emotion_name)
Display::ShowNotification(message, duration_ms)
Display::UpdateStatusBar()  // Network, battery, time
Display::SetTheme(theme)
Display::SetPowerSaveMode(bool)
```

## Critical Build Considerations

### Partition Table
- **v2 is incompatible with v1** - Manual flash required (no OTA from v1 → v2)
- Partition tables: `partitions/v2/` (4m.csv, 8m.csv, 16m.csv)
- Select correct partition table in `config.json` based on Flash size

### IDF Version
- **Required: ESP-IDF 5.4 or above**
- Linux preferred over Windows (faster compilation, fewer driver issues)

### Chip Support
- ESP32, ESP32-C3, ESP32-S3, ESP32-P4, ESP32-C6
- Set target before build: `idf.py set-target {chip}`

### AEC Configuration
- **Device-side AEC** (`CONFIG_USE_DEVICE_AEC=y`) - ESP32-S3/P4 only
- **Server-side AEC** (`CONFIG_USE_SERVER_AEC=y`) - All chips
- **Mutually exclusive** - Enable only one

### Wake Word Detection
- ESP32-S3/P4: ESP-SR wake word engine
- ESP32-C3/C6: Limited wake word support (custom models only)
- Can be disabled: `CONFIG_WAKE_WORD_DISABLED=y`

### Common sdkconfig Options
```
CONFIG_ESPTOOLPY_FLASHSIZE_4MB=y    # 4MB Flash
CONFIG_ESPTOOLPY_FLASHSIZE_8MB=y    # 8MB Flash
CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y   # 16MB Flash

CONFIG_PARTITION_TABLE_CUSTOM_FILENAME="partitions/v2/8m.csv"

CONFIG_USE_DEVICE_AEC=y             # Device-side AEC
CONFIG_USE_SERVER_AEC=y             # Server-side AEC
CONFIG_WAKE_WORD_DISABLED=y         # Disable wake word

CONFIG_LANGUAGE_ZH_CN=y             # Chinese
CONFIG_LANGUAGE_EN_US=y             # English
CONFIG_LANGUAGE_JA_JP=y             # Japanese
```

## Code Style & Patterns

### Design Patterns
- **Singleton**: Application, Board, McpServer
- **Factory**: Board::create_board()
- **Observer**: State change listeners, event callbacks
- **Strategy**: Protocol implementations (WebSocket vs MQTT)
- **Event-Driven**: FreeRTOS event groups

### Threading Model
```
Main Task:
├─ Application::Run() [event loop - never returns]
└─ Event-driven handlers

Background Tasks:
├─ AudioInputTask        [mic → encode]
├─ AudioOutputTask       [decode → speaker]
├─ OpusCodecTask         [opus encode/decode]
├─ ActivationTask        [device registration]
├─ Network Tasks         [WiFi/MQTT/WebSocket]
├─ Wake Word Task        [ESP-SR detection]
└─ Clock Timer Task      [1Hz status updates]

Synchronization:
├─ FreeRTOS event groups (event_group_)
├─ Mutexes (audio_queue_mutex_, decoder_mutex_)
├─ Condition variables (audio_queue_cv_)
└─ Atomic flags (voice_detected_, service_stopped_)
```

### Code Style
- **Google C++ style** - Please ensure compliance when submitting code
- Use `DisplayLockGuard` when modifying display from multiple threads
- Use `Application::Schedule()` for thread-safe callbacks to main loop
- Audio queues use mutex + condition variable pattern
- State changes trigger events via `Application::PostEvent()`

## Common Development Tasks

### Debugging Audio Issues
```bash
# Use audio debug server to capture raw audio
python scripts/audio_debug_server.py

# Check audio logs
idf.py monitor | grep "AUDIO"

# Common issues:
# - Wrong sample rates → Check config.h AUDIO_INPUT_SAMPLE_RATE
# - Codec not initializing → Check I2C pins and codec address
# - No wake word → Check ESP-SR model compatibility with chip
# - Distorted audio → Check resampler quality setting
```

### Adding a New Board
1. Reference similar hardware in `main/boards/`
2. Create directory: `main/boards/my-board/`
3. Copy and modify: `config.h`, `config.json`, `my_board.cc`
4. Add Kconfig entry in `main/Kconfig.projbuild`
5. Add CMake mapping in `main/CMakeLists.txt`
6. Test build: `python scripts/release.py my-board`

### Modifying Protocol Behavior
- WebSocket: `main/protocols/websocket_protocol.cc`
- MQTT+UDP: `main/protocols/mqtt_protocol.cc`
- Protocol selection: `main/protocols/protocol.cc` (factory)
- Message handlers: `Application::OnIncomingJson()`

### Adding MCP Tools
```cpp
// In board initialization or Application::Initialize()
McpServer::GetInstance().AddTool(
    "self.category.action",
    "Description visible to AI",
    {
        {"param1", McpPropertyType::kString, true},
        {"param2", McpPropertyType::kInt, false, 0, 100}
    },
    [](const cJSON* args) -> int {
        // Tool implementation
        return result;
    }
);
```

## Key Files Reference

### Core Application
- `main/main.cc` - Entry point
- `main/application.h/cc` - Main application singleton & event loop
- `main/device_state_machine.h/cc` - State machine (10 states)
- `main/settings.h/cc` - NVS flash persistence (WiFi, volume, etc.)
- `main/system_info.h/cc` - Device telemetry
- `main/ota.h/cc` - OTA firmware updates

### Audio System
- `main/audio/audio_service.h/cc` - Audio pipeline orchestrator
- `main/audio/audio_codecs/` - Hardware codec drivers
- `main/audio/opus_encoder.cc` / `opus_decoder.cc` - Opus codec
- `main/audio/rate_converter.cc` - Sample rate resampling
- `main/audio/audio_processor.h/cc` - AFE/VAD/AEC
- `main/audio/wake_word.cc` - Wake word detection

### Networking
- `main/protocols/protocol.cc` - Protocol factory
- `main/protocols/websocket_protocol.cc` - WebSocket implementation
- `main/protocols/mqtt_protocol.cc` - MQTT+UDP implementation

### MCP Server
- `main/mcp_server.h/cc` - MCP server & tool registry
- `docs/mcp-protocol.md` - Protocol documentation
- `docs/mcp-usage.md` - Usage examples

### Display & UI
- `main/display/display.h` - Display base class
- `main/display/lcd_display.cc` - LCD driver
- `main/display/lvgl_display/` - LVGL graphics
- `main/display/oled_display.cc` - OLED driver

### Board Abstraction
- `main/board.h/cc` - Board base class
- `main/boards/` - 112+ board configurations
- `main/boards/wifi_board.h/cc` - WiFi board base
- `main/boards/dual_network_board.h/cc` - WiFi+4G base

### Build System
- `CMakeLists.txt` - Root build config
- `main/CMakeLists.txt` - Main component build
- `main/Kconfig.projbuild` - Configuration options
- `sdkconfig.defaults*` - Default configurations per chip
- `scripts/release.py` - Automated build script

## Documentation

- `README.md` - Main project documentation
- `docs/custom-board.md` - Creating custom boards
- `docs/mcp-protocol.md` - MCP protocol specification
- `docs/mcp-usage.md` - MCP usage guide
- `docs/websocket.md` - WebSocket protocol details
- `docs/mqtt-udp.md` - MQTT+UDP protocol details
- Board-specific docs: `main/boards/{board}/README.md`

## Related Resources

- **Official Server:** https://xiaozhi.me (free Qwen real-time model)
- **QQ Group:** 1011329060
- **Documentation:** https://ccnphfhqs21z.feishu.cn/wiki/F5krwD16viZoF0kKkvDcrZNYnhb
- **Custom Assets Generator:** https://github.com/78/xiaozhi-assets-generator
- **ESP-IDF Documentation:** https://docs.espressif.com/projects/esp-idf/
- **ESP-SR (Wake Word):** https://github.com/espressif/esp-sr
