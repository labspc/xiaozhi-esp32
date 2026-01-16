# XiaoZhi生态标准与下一代基础设施设计

## 文档目标

本文档明确：
1. **XiaoZhi生态的核心标准**（必须兼容的部分）
2. **可精简优化的非标准部分**（提升质量的空间）
3. **下一代基础设施的设计原则**（保持兼容 + 更纯粹）

---

## 一、XiaoZhi生态核心标准（🔒 不可变）

### 1.1 协议标准层（最核心）

这些是**XiaoZhi生态的DNA**，所有设备必须遵守才能兼容xiaozhi.me服务器。

#### **A. WebSocket协议标准**

**连接握手标准：**
```http
GET /audio HTTP/1.1
Upgrade: websocket
Authorization: Bearer <token>
Protocol-Version: 3                    # 固定值（当前最新版本）
Device-Id: <MAC地址>                    # 设备唯一标识
Client-Id: <UUID>                      # 客户端UUID
```

**二进制帧格式（版本3）：**
```c
struct BinaryProtocol3 {
    uint8_t type;            // 消息类型：0=OPUS, 1=JSON
    uint8_t reserved;        // 保留字段（必须为0）
    uint16_t payload_size;   // 负载大小（网络字节序）
    uint8_t payload[];       // Opus音频数据或JSON
} __attribute__((packed));
```

**JSON消息标准格式：**
```json
{
  "session_id": "xxx",      // 会话ID（必须）
  "type": "hello|stt|tts|llm|mcp|listen|abort|system",
  "payload": { ... }        // 类型相关数据
}
```

**关键JSON消息定义：**

1. **Hello消息（设备→服务器）：**
```json
{
  "type": "hello",
  "version": 1,
  "features": {
    "mcp": true,            // 是否支持MCP
    "aec": true            // 是否启用服务器端AEC
  },
  "transport": "websocket",
  "audio_params": {
    "format": "opus",
    "sample_rate": 16000,   // 固定16kHz
    "channels": 1,
    "frame_duration": 60    // 固定60ms
  }
}
```

2. **Hello响应（服务器→设备）：**
```json
{
  "type": "hello",
  "session_id": "xxx",
  "audio_params": {
    "sample_rate": 24000,   // 服务器采样率（通常24kHz）
    "frame_duration": 60
  }
}
```

3. **Listen消息（监听控制）：**
```json
{
  "session_id": "xxx",
  "type": "listen",
  "state": "start|stop|detect"
}
```

4. **Abort消息（中断播放）：**
```json
{
  "session_id": "xxx",
  "type": "abort",
  "reason": "wake_word_detected"
}
```

**🔒 为什么是标准？**
- xiaozhi.me服务器完全依赖这些消息格式
- 任何偏差都会导致连接失败或功能异常
- 协议版本号必须匹配

---

#### **B. MQTT+UDP混合协议标准**

**MQTT控制通道：**
```json
// Hello消息
{
  "type": "hello",
  "version": 3,
  "transport": "udp",
  "features": { "mcp": true, "aec": true },
  "audio_params": {
    "format": "opus",
    "sample_rate": 16000,
    "channels": 1,
    "frame_duration": 60
  }
}

// 服务器响应（包含UDP参数）
{
  "type": "hello",
  "session_id": "xxx",
  "udp": {
    "server": "192.168.1.100",
    "port": 8888,
    "key": "0123456789ABCDEF...",      // AES-128密钥（32字符十六进制）
    "nonce": "0123456789ABCDEF..."    // AES随机数（32字符十六进制）
  }
}
```

**UDP音频包格式：**
```
+------+-------+-------------+------+--------+----------+
| type | flags | payload_len | ssrc | time   | sequence |
| 1B   | 1B    | 2B          | 4B   | 4B     | 4B       |
+------+-------+-------------+------+--------+----------+
|          AES-CTR加密的Opus音频数据                    |
+--------------------------------------------------------+
```

**加密算法：AES-128-CTR**
- 密钥长度：128位（16字节）
- 模式：CTR计数器模式
- 计数器：基于timestamp和sequence

**🔒 为什么是标准？**
- 服务器解密依赖精确的包格式
- 序列号用于丢包检测和重排序
- 加密参数必须完全一致

---

#### **C. MCP协议标准（JSON-RPC 2.0）**

**MCP规范版本：2024-11-05**

**1. 初始化流程：**
```json
// 请求（服务器→设备）
{
  "jsonrpc": "2.0",
  "method": "initialize",
  "params": {
    "capabilities": {
      "vision": {
        "url": "https://vision.api.com",
        "token": "xxx"
      }
    }
  },
  "id": 1
}

// 响应（设备→服务器）
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",  // 固定版本
    "capabilities": { "tools": {} },
    "serverInfo": {
      "name": "ESP-BOX-3",
      "version": "2.1.0"
    }
  }
}
```

**2. 工具列表：**
```json
// 请求
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "params": {
    "cursor": "",
    "withUserTools": false
  },
  "id": 2
}

// 响应
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "self.get_device_status",
        "description": "获取设备状态",
        "inputSchema": {
          "type": "object",
          "properties": {},
          "required": []
        }
      }
    ]
  }
}
```

**3. 工具调用：**
```json
// 请求
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "self.audio_speaker.set_volume",
    "arguments": { "volume": 50 }
  },
  "id": 3
}

// 成功响应
{
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      { "type": "text", "text": "true" }
    ],
    "isError": false
  }
}

// 错误响应
{
  "jsonrpc": "2.0",
  "id": 3,
  "error": {
    "code": -32601,
    "message": "Unknown tool: xxx"
  }
}
```

**🔒 核心MCP工具（所有设备必须实现）：**

| 工具名称 | 参数 | 返回值 | 说明 |
|---------|------|--------|------|
| `self.get_device_status` | 无 | JSON对象 | 设备状态 |
| `self.audio_speaker.set_volume` | `volume` (0-100) | boolean | 音量控制 |
| `self.screen.set_brightness` | `brightness` (0-100) | boolean | 亮度控制 |
| `self.screen.set_theme` | `theme` ("light"\|"dark") | boolean | 主题切换 |

**🔒 为什么是标准？**
- AI需要统一的工具名称和参数结构
- 服务器依赖这些核心工具实现设备控制
- JSON-RPC 2.0是行业标准

---

#### **D. 音频处理标准**

**固定参数（🔒 不可修改）：**
```c
// 编码参数
#define AUDIO_ENCODE_SAMPLE_RATE  16000      // 发送给服务器：16kHz
#define OPUS_FRAME_DURATION_MS    60         // 帧长度：60ms
#define AUDIO_CHANNELS            1          // 单声道

// 解码参数（服务器→设备）
服务器采样率：24000 Hz（标准）
帧长度：60ms
声道：单声道

// 队列大小
#define MAX_DECODE_PACKETS_IN_QUEUE  40      // 2400ms缓冲
#define MAX_SEND_PACKETS_IN_QUEUE    40      // 2400ms缓冲
```

**Opus编码配置：**
```c
esp_opus_enc_config_t config = {
    .sample_rate = 16000,
    .channel = 1,
    .bits_per_sample = 16,
    .bitrate = AUTO,
    .frame_duration = 60,
    .application_mode = AUDIO,
    .complexity = 0,
    .enable_fec = false,
    .enable_dtx = true,
    .enable_vbr = true
};
```

**🔒 为什么是标准？**
- 服务器解码器配置为24kHz
- 帧长60ms确保实时性和音质平衡
- 16kHz编码平衡带宽和识别准确度

---

#### **E. 服务器接口标准**

**1. 激活接口：`POST <OTA_URL>/activate`**

请求头：
```http
Content-Type: application/json
Device-Id: <MAC地址>
Client-Id: <UUID>
User-Agent: XiaoZhi/<version> (<board_name>)
```

请求体：
```json
{
  "challenge": "xxx",
  "code": "123456",
  "hmac": "xxx"
}
```

响应：
```json
{ "status": "success" }
```

**2. 版本检查接口：`POST/GET <OTA_URL>`**

响应：
```json
{
  "firmware": {
    "version": "2.1.0",
    "url": "https://ota.example.com/firmware.bin"
  },
  "websocket": {
    "url": "wss://ws.example.com/audio",
    "token": "Bearer xxx",
    "version": 3
  },
  "mqtt": { ... },
  "server_time": 1706256000000
}
```

**3. 设备状态JSON标准：**
```json
{
  "audio_speaker": { "volume": 70 },
  "screen": { "brightness": 100, "theme": "light" },
  "battery": { "level": 50, "charging": true },
  "network": { "type": "wifi", "ssid": "xxx", "signal": "strong" }
}
```

**🔒 为什么是标准？**
- xiaozhi.me服务器依赖这些接口进行设备管理
- JSON结构被AI模型解析和使用

---

### 1.2 标准总结：必须兼容的部分

| 分类 | 标准项 | 版本 | 兼容性 |
|------|--------|------|--------|
| **协议** | WebSocket协议v3 | 固定 | 🔒 强制 |
| **协议** | MQTT+UDP混合协议 | 固定 | 🔒 强制 |
| **协议** | JSON消息格式 | 固定 | 🔒 强制 |
| **MCP** | JSON-RPC 2.0 | 2024-11-05 | 🔒 强制 |
| **MCP** | 核心工具（4个） | 固定 | 🔒 强制 |
| **音频** | Opus 16kHz 60ms | 固定 | 🔒 强制 |
| **音频** | 服务器解码24kHz | 固定 | 🔒 强制 |
| **接口** | 激活接口 | 固定 | 🔒 强制 |
| **接口** | 版本检查接口 | 固定 | 🔒 强制 |
| **接口** | 设备状态JSON | 固定 | 🔒 强制 |

**兼容性测试清单：**
```bash
✅ 能否连接xiaozhi.me服务器？
✅ Hello消息是否被正确响应？
✅ 音频流能否正常收发？
✅ MCP工具调用是否成功？
✅ 设备状态能否被AI读取？
```

---

## 二、可优化精简的非标准部分（🔧 可变）

### 2.1 板型实现层（109个→8个核心）

**当前问题：**
- ❌ 109个板型配置文件
- ❌ 每个板型独立GPIO、音频参数、显示驱动
- ❌ 无法统一测试和维护

**优化方案：**
```
main/boards/
├── official/              # 🔒 官方维护（8个核心板型）
│   ├── esp32s3_box3/
│   ├── m5stack_cores3/
│   └── ...
├── community/             # 🔧 社区扩展（不破坏核心）
│   ├── legacy/            # 迁移的101个旧板型
│   └── custom/            # 用户自定义
└── template/              # 模板目录
    └── custom_board_template/
```

**保留标准：**
- ✅ Board抽象接口（GetAudioCodec/GetDisplay/GetNetwork）
- ✅ 板型注册机制（Board::create_board）

**精简内容：**
- 🔧 官方只维护8个核心板型
- 🔧 其他板型移到community/legacy（代码保留，不维护）
- 🔧 新板型使用模板自行扩展

---

### 2.2 硬件抽象层（HAL）

**当前问题：**
- ⚠️ 部分应用层代码硬编码GPIO
- ⚠️ 音频编解码器接口不统一
- ⚠️ 显示接口混合使用LVGL和自定义

**优化方案：**

**统一音频接口：**
```cpp
// 当前：不同codec有不同API
ES8311Codec codec;
codec.SetVolume(50);

// 优化后：统一抽象
class AudioCodec {
public:
    virtual bool SetVolume(float volume) = 0;   // 0.0-1.0
    virtual bool SetSampleRate(int rate) = 0;
    virtual bool Start() = 0;
    virtual bool Stop() = 0;
};
```

**统一显示接口：**
```cpp
class Display {
public:
    virtual void ShowMessage(const std::string& msg) = 0;
    virtual void SetBrightness(float brightness) = 0;  // 0.0-1.0
    virtual void SetTheme(Theme theme) = 0;
};
```

**保留标准：**
- ✅ Board::GetAudioCodec()接口定义
- ✅ Board::GetDisplay()接口定义
- ✅ Board::GetNetwork()接口定义

**精简内容：**
- 🔧 移除应用层硬编码（所有GPIO访问通过Board抽象）
- 🔧 统一编解码器接口（消除差异）
- 🔧 简化显示抽象（专注语音助手场景）

---

### 2.3 应用层逻辑

**当前问题：**
- ⚠️ 状态机复杂（10个状态）
- ⚠️ 事件循环耦合板级逻辑
- ⚠️ 音频处理流程冗长

**优化方案：**

**精简状态机：**
```
当前10个状态：
Starting → WifiConfiguring → Activating → Idle → Listening →
Speaking → Connecting → Upgrading → AudioTesting → FatalError

优化后6个核心状态：
Starting → Connecting → Idle → Listening → Speaking → Error
```

**解耦事件循环：**
```cpp
// 当前：事件处理直接访问硬件
void Application::OnEvent(Event event) {
    gpio_set_level(GPIO_NUM_5, 1);  // ❌ 硬编码
}

// 优化后：通过抽象层
void Application::OnEvent(Event event) {
    Board::GetInstance().GetLed()->SetState(true);  // ✅ 抽象
}
```

**保留标准：**
- ✅ 协议层接口（Protocol::SendAudio/OnIncomingJson）
- ✅ 音频服务接口（AudioService::Start/Stop）
- ✅ MCP服务器接口（McpServer::AddTool/HandleMessage）

**精简内容：**
- 🔧 简化状态机（合并非核心状态）
- 🔧 移除调试状态（AudioTesting仅用于开发）
- 🔧 优化事件循环（减少轮询，增加事件驱动）

---

### 2.4 显示系统

**当前问题：**
- ⚠️ 多种显示后端（LCD/OLED/LVGL/Emote/NoDisplay）
- ⚠️ 显示更新频率过高（影响性能）
- ⚠️ UI元素过于复杂

**优化方案：**

**简化显示后端：**
```
当前：5种显示类型
优化后：2种核心类型
  1. LVGLDisplay（带屏板型）
  2. NoDisplay（无屏板型，如Atom Echo）
```

**精简UI元素：**
```
保留核心：
✅ 状态指示（Idle/Listening/Speaking）
✅ 网络状态
✅ 电量显示
✅ 音量条

移除非核心：
🔧 复杂动画（消耗CPU）
🔧 表情符号（不是所有屏幕都支持）
🔧 聊天历史（内存占用大）
```

**保留标准：**
- ✅ Display基类接口（SetStatus/ShowMessage）
- ✅ MCP工具对显示的控制（SetBrightness/SetTheme）

**精简内容：**
- 🔧 合并LCD/OLED到LVGLDisplay
- 🔧 移除Emote显示（特殊需求）
- 🔧 简化UI渲染（仅核心信息）

---

### 2.5 网络层

**当前问题：**
- ⚠️ 同时支持WiFi和4G（DualNetworkBoard）
- ⚠️ 网络切换逻辑复杂
- ⚠️ 4G支持仅针对ML307模块

**优化方案：**

**简化网络栈：**
```
当前：
- WifiBoard（WiFi）
- DualNetworkBoard（WiFi + 4G/ML307）
- 网络切换逻辑

优化后（核心8板型）：
- 仅WiFi（所有核心板型都是WiFi）
- 4G支持移到community/（特殊需求）
```

**保留标准：**
- ✅ Network抽象接口（Connect/Disconnect/IsConnected）
- ✅ 网络事件（MAIN_EVENT_NETWORK_CONNECTED/DISCONNECTED）

**精简内容：**
- 🔧 核心板型仅支持WiFi
- 🔧 移除4G/ML307相关代码到community/
- 🔧 简化网络状态管理

---

## 三、下一代基础设施设计原则

### 3.1 设计哲学

**奥卡姆剃刀原则：简单即美**
```
如无必要，勿增实体
- 每个组件必须有明确的职责
- 每个抽象必须有实际价值
- 每行代码必须有存在理由
```

**保持纯粹：分离关注点**
```
应用层：不关心硬件细节
抽象层：只定义接口，不实现
板型层：只实现硬件，不涉及业务
```

**兼容优先：不破坏生态**
```
协议标准：100%兼容xiaozhi.me
MCP标准：100%兼容AI模型
音频标准：100%兼容服务器
```

---

### 3.2 架构层次（严格三层）

```
┌─────────────────────────────────────────────────────────┐
│  应用层（Application Layer）                              │
│  - 完全硬件无关                                           │
│  - 依赖抽象接口                                           │
│  - 实现业务逻辑                                           │
│                                                          │
│  核心模块：                                               │
│    • Application（主循环）                                │
│    • AudioService（音频管道）                             │
│    • Protocol（WebSocket/MQTT）                         │
│    • McpServer（MCP服务器）                              │
│    • DeviceStateMachine（状态机）                        │
│    • OTA（升级）                                          │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  硬件抽象层（HAL - Hardware Abstraction Layer）           │
│  - 纯虚接口定义                                           │
│  - 零实现代码                                             │
│  - 板型无关                                               │
│                                                          │
│  核心接口：                                               │
│    • Board（板级抽象）                                     │
│    • AudioCodec（音频编解码器）                            │
│    • Display（显示器）                                     │
│    • Network（网络）                                       │
│    • Led（指示灯）                                         │
│    • Button（按键）                                        │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│  板型实现层（Board Implementation Layer）                  │
│  - 实现HAL接口                                            │
│  - 硬件相关代码                                           │
│  - GPIO/I2C/SPI配置                                      │
│                                                          │
│  目录结构：                                               │
│    official/                                            │
│      ├── esp32s3_box3/          🔒 官方维护              │
│      ├── m5stack_cores3/        🔒 官方维护              │
│      └── ...                                            │
│    community/                                           │
│      ├── legacy/                🔧 社区维护              │
│      └── custom/                🔧 用户自定义            │
└─────────────────────────────────────────────────────────┘
```

---

### 3.3 代码规范

**1. 应用层代码禁止事项：**
```cpp
// ❌ 禁止：直接访问GPIO
gpio_set_level(GPIO_NUM_5, 1);

// ❌ 禁止：硬编码硬件参数
#define AUDIO_SAMPLE_RATE 16000  // 应从Board配置读取

// ❌ 禁止：直接访问I2C/SPI
i2c_master_write(...);

// ❌ 禁止：板型判断逻辑
#ifdef BOARD_ESP_BOX_3
  // ...
#endif
```

**2. 应用层代码推荐模式：**
```cpp
// ✅ 推荐：通过抽象层访问硬件
Board::GetInstance().GetLed()->SetColor(Color::Red);

// ✅ 推荐：读取板级配置
int sample_rate = Board::GetInstance().GetAudioConfig().sample_rate;

// ✅ 推荐：使用抽象接口
AudioCodec* codec = Board::GetInstance().GetAudioCodec();
codec->SetVolume(0.5f);

// ✅ 推荐：依赖注入
void ProcessAudio(AudioCodec* codec, Display* display);
```

**3. HAL层接口规范：**
```cpp
// ✅ 纯虚基类
class AudioCodec {
public:
    virtual ~AudioCodec() = default;
    virtual bool SetVolume(float volume) = 0;  // 标准化参数（0.0-1.0）
    virtual bool Start() = 0;
    virtual bool Stop() = 0;
};

// ❌ 禁止在HAL层实现
class AudioCodec {
public:
    bool SetVolume(float volume) {
        // 实现代码应该在板型层
    }
};
```

---

### 3.4 核心8板型标准配置

**每个核心板型必须提供：**

**1. 板型元数据：**
```cpp
struct BoardInfo {
    const char* name;           // "ESP-BOX-3"
    const char* type;           // "esp-box-3"
    const char* chip_model;     // "esp32s3"
    const char* version;        // "2.1.0"
};
```

**2. 音频配置：**
```cpp
struct AudioConfig {
    int input_sample_rate;      // 硬件采样率（例：24000）
    int output_sample_rate;     // 硬件采样率（例：24000）
    int encode_sample_rate;     // 固定16000（发送给服务器）
    int decode_sample_rate;     // 固定24000（服务器返回）
    AudioCodecType codec_type;  // ES8311/ES8388/...
};
```

**3. 显示配置：**
```cpp
struct DisplayConfig {
    bool has_display;           // 是否有屏幕
    DisplayType type;           // LCD/OLED/None
    int width;                  // 宽度（像素）
    int height;                 // 高度（像素）
    bool monochrome;            // 是否单色
};
```

**4. 必须实现的HAL接口：**
```cpp
class ESP32S3Box3Board : public Board {
public:
    // 🔒 强制实现
    AudioCodec* GetAudioCodec() override;
    Display* GetDisplay() override;
    Network* GetNetwork() override;

    // 🔧 可选实现
    Led* GetLed() override { return nullptr; }
    Camera* GetCamera() override { return nullptr; }
    Button* GetButton() override { return nullptr; }

    // 🔒 强制实现（MCP需要）
    cJSON* GetDeviceStatusJson() override;
};
```

---

### 3.5 扩展机制设计

**用户添加自定义板型流程：**

**第一步：复制模板**
```bash
cp -r main/boards/template/custom_board_template \
      main/boards/community/custom/my_awesome_board
```

**第二步：修改配置**
```cpp
// main/boards/community/custom/my_awesome_board/config.h
#define BOARD_NAME "My Awesome Board"
#define BOARD_TYPE "my-awesome-board"

// GPIO配置
#define GPIO_LED 5
#define GPIO_BUTTON 0

// 音频配置
#define AUDIO_CODEC_TYPE AUDIO_CODEC_ES8311
#define AUDIO_INPUT_SAMPLE_RATE 24000
#define AUDIO_OUTPUT_SAMPLE_RATE 24000

// 显示配置
#define DISPLAY_TYPE DISPLAY_TYPE_LCD
#define DISPLAY_WIDTH 320
#define DISPLAY_HEIGHT 240
```

**第三步：实现板型类**
```cpp
// my_awesome_board.cc
class MyAwesomeBoard : public Board {
public:
    MyAwesomeBoard() {
        // 初始化硬件
        audio_codec_ = new ES8311Codec(...);
        display_ = new LcdDisplay(...);
        network_ = new WifiNetwork(...);
    }

    AudioCodec* GetAudioCodec() override { return audio_codec_; }
    Display* GetDisplay() override { return display_; }
    Network* GetNetwork() override { return network_; }

    cJSON* GetDeviceStatusJson() override {
        // 实现设备状态（🔒 兼容MCP标准）
        cJSON* root = cJSON_CreateObject();
        cJSON_AddNumberToObject(root, "volume", current_volume_);
        // ...
        return root;
    }
};
```

**第四步：注册板型**
```cpp
// main/boards/community/custom/my_awesome_board/register.cc
#include "board.h"

extern "C" void register_my_awesome_board() {
    Board::RegisterBoard("my-awesome-board", []() {
        return new MyAwesomeBoard();
    });
}
```

**第五步：编译配置**
```bash
idf.py menuconfig
# → Xiaozhi Assistant → Board Type → Community Boards → My Awesome Board

idf.py build
```

**关键点：**
- ✅ 用户代码完全隔离在`community/custom/`
- ✅ 官方更新不会覆盖用户板型
- ✅ 必须遵守HAL接口（保证兼容性）
- ✅ 必须实现MCP标准工具（保证生态兼容）

---

### 3.6 兼容性保证机制

**编译时检查：**
```cpp
// 静态断言：确保板型实现必要接口
static_assert(std::is_base_of<Board, MyAwesomeBoard>::value,
              "Board must inherit from Board base class");

// 接口完整性检查
#define REQUIRE_BOARD_METHOD(method) \
    static_assert(has_method_##method<Board>::value, \
                  "Board must implement " #method)
```

**运行时检查：**
```cpp
// 启动时验证
bool Board::ValidateImplementation() {
    if (!GetAudioCodec()) {
        ESP_LOGE(TAG, "GetAudioCodec() returned nullptr");
        return false;
    }

    if (!GetNetwork()) {
        ESP_LOGE(TAG, "GetNetwork() returned nullptr");
        return false;
    }

    // 验证MCP标准工具
    cJSON* status = GetDeviceStatusJson();
    if (!status || !cJSON_HasObjectItem(status, "audio_speaker")) {
        ESP_LOGE(TAG, "Invalid device status JSON");
        return false;
    }

    return true;
}
```

**协议兼容性测试：**
```cpp
// 测试套件
TEST(BoardCompatibility, WebSocketProtocol) {
    // 测试Hello消息格式
    // 测试音频包格式
    // 测试MCP消息格式
}

TEST(BoardCompatibility, MCPTools) {
    // 测试核心工具存在性
    ASSERT_TRUE(HasTool("self.get_device_status"));
    ASSERT_TRUE(HasTool("self.audio_speaker.set_volume"));
    ASSERT_TRUE(HasTool("self.screen.set_brightness"));
}

TEST(BoardCompatibility, AudioParams) {
    // 测试音频参数
    ASSERT_EQ(GetEncodeSampleRate(), 16000);
    ASSERT_EQ(GetFrameDuration(), 60);
}
```

---

## 四、精简实施路线图

### 4.1 阶段1：标准梳理与文档化（1周）

**目标：明确标准边界**

✅ 完成：
- [x] 协议标准文档（本文档）
- [x] 核心8板型清单
- [x] HAL接口定义

⏳ 待办：
- [ ] 社区公告（预告精简计划）
- [ ] 兼容性测试清单
- [ ] 迁移指南草稿

---

### 4.2 阶段2：创建模板与目录结构（1周）

**目标：建立新架构**

任务：
1. 创建目录结构
```bash
main/boards/
├── official/
│   ├── esp32s3_box3/
│   ├── m5stack_cores3/
│   ├── lilygo_tdisplay_s3/
│   ├── seeed_xiao_esp32s3/
│   ├── esp32s3_lcd_ev/
│   ├── esp32p4_ev/
│   ├── esp32c3_devkit/
│   └── m5stack_atom_echo/
├── community/
│   ├── legacy/          # 101个旧板型
│   └── custom/          # 空目录（用户自定义）
└── template/
    └── custom_board_template/
```

2. 开发板型模板
```cpp
// template/custom_board_template/board_template.cc
// 包含详细注释和示例代码
```

3. 编写扩展文档
```markdown
docs/custom-board-guide.md
- 如何使用模板
- HAL接口说明
- 兼容性要求
- 调试技巧
```

---

### 4.3 阶段3：精简核心板型（2-3周）

**目标：8个核心板型100%测试通过**

任务清单：
1. **实现8个核心板型**
   - [ ] ESP32-S3-BOX-3
   - [ ] M5Stack CoreS3
   - [ ] LilyGo T-Display-S3
   - [ ] Seeed Xiao ESP32S3
   - [ ] ESP32-S3-LCD-EV-Board
   - [ ] ESP32-P4-Function-EV-Board
   - [ ] ESP32-C3-DevKitM-1
   - [ ] M5Stack Atom Echo

2. **统一HAL接口**
   - [ ] AudioCodec抽象
   - [ ] Display抽象
   - [ ] Network抽象
   - [ ] Led抽象

3. **移除应用层硬编码**
   ```bash
   # 检查硬编码
   grep -r "GPIO_NUM_" main/*.cc
   grep -r "i2c_master" main/*.cc

   # 应该只在main/boards/official/内出现
   ```

4. **兼容性测试**
   - [ ] 连接xiaozhi.me服务器
   - [ ] 语音流传输
   - [ ] MCP工具调用
   - [ ] OTA升级

---

### 4.4 阶段4：迁移旧板型（1周）

**目标：不丢失任何代码，仅重组**

任务：
1. 批量移动
```bash
# 移动101个旧板型到legacy
for board in $(ls main/boards/ | grep -v official | grep -v community | grep -v template); do
    mv main/boards/$board main/boards/community/legacy/
done
```

2. 更新CMakeLists.txt
```cmake
# 默认不编译legacy板型（节省编译时间）
option(BUILD_LEGACY_BOARDS "Build legacy community boards" OFF)

if(BUILD_LEGACY_BOARDS)
    add_subdirectory(community/legacy)
endif()
```

3. 提供迁移说明
```markdown
# 如果你使用旧板型

## 选项1：继续使用v2.x分支（推荐）
git checkout v2.x-lts

## 选项2：迁移到v3.x（需要自行维护）
idf.py menuconfig
→ Enable BUILD_LEGACY_BOARDS
→ Select your board from Community/Legacy

## 选项3：基于模板重新实现（推荐）
cp -r main/boards/template/custom_board_template \
      main/boards/community/custom/my_board
```

---

### 4.5 阶段5：国际化与文档（2周）

**目标：8个核心板型100%双语文档**

任务：
1. 英文README
```markdown
README.md (English)
docs/en/getting-started.md
docs/en/supported-boards.md
docs/en/custom-board-guide.md
docs/en/protocol-reference.md
```

2. 代码注释国际化
```cpp
// 核心文件添加英文注释
main/application.h/cc
main/mcp_server.h/cc
main/protocols/protocol.h
```

3. 8个核心板型的快速开始指南
```markdown
# ESP32-S3-BOX-3 Quick Start
## 1. Flash firmware
## 2. Connect to WiFi
## 3. Activate device
## 4. Start talking
```

---

### 4.6 阶段6：发布v3.0（1周）

**目标：稳定版本发布**

里程碑：
- ✅ 8个核心板型测试通过
- ✅ xiaozhi.me服务器兼容性100%
- ✅ 英文文档完整
- ✅ 社区反馈收集
- ✅ 迁移指南完善

发布内容：
1. v3.0正式版固件（8个核心板型）
2. v2.x-lts长期支持分支（维护到2026年底）
3. 完整文档（中英文）
4. 社区板型模板

---

## 五、总结：保持纯粹 + 兼容生态

### 5.1 核心原则

**🔒 不可变的标准（生态DNA）：**
1. WebSocket/MQTT协议（xiaozhi.me依赖）
2. MCP工具定义（AI依赖）
3. 音频参数（服务器依赖）
4. 设备状态JSON（服务器依赖）

**🔧 可优化的实现（质量提升）：**
1. 板型数量（109→8核心）
2. 硬件抽象（统一接口）
3. 应用逻辑（简化状态机）
4. 显示系统（精简UI）

**🎯 下一代目标：**
1. **更纯粹**：应用层零硬件依赖
2. **更稳定**：集中测试核心板型
3. **更国际化**：双语文档、国际社区
4. **更可扩展**：社区可自由添加板型

### 5.2 成功标准

**技术指标：**
- [ ] 编译时间<5分钟（当前>10分钟）
- [ ] 核心板型测试覆盖率100%
- [ ] xiaozhi.me兼容性100%
- [ ] 应用层硬件依赖=0

**生态指标：**
- [ ] 8个核心板型100%双语文档
- [ ] 社区板型模板使用率>50%
- [ ] 国际板型销售渠道建立
- [ ] GitHub国际贡献者>20%

**用户体验：**
- [ ] 核心板型开箱即用
- [ ] 自定义板型<1小时完成
- [ ] 错误信息清晰易懂
- [ ] 文档搜索准确快速

---

**作者**: XiaoZhi架构团队
**版本**: v1.0
**日期**: 2026-01-16
**状态**: RFC - 征求意见

**反馈渠道**:
- GitHub Discussions: 架构讨论
- QQ群: 1011329060
- Email: feedback@xiaozhi.me
