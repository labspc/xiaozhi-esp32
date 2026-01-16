# XiaoZhi ESP32 项目规模详细说明

本文档详细说明 xiaozhi-esp32 项目的规模和核心模块实现，包括硬件支持、多语言系统、音频编解码器、显示系统和通信协议。

---

## 目录

1. [多语言支持系统 (38种语言)](#1-多语言支持系统)
2. [硬件板型支持 (110+板型)](#2-硬件板型支持)
3. [音频编解码器系统 (6种驱动)](#3-音频编解码器系统)
4. [显示系统抽象 (5种类型)](#4-显示系统抽象)
5. [通信协议实现 (2种协议)](#5-通信协议实现)

---

## 1. 多语言支持系统

### 1.1 支持的语言列表（共38种语言）

xiaozhi-esp32 支持以下语言，在 `main/Kconfig.projbuild` 中配置：

#### 亚洲语言（10种）
- 中文简体 (zh-CN) - **默认语言**
- 中文繁体 (zh-TW)
- 日语 (ja-JP)
- 韩语 (ko-KR)
- 越南语 (vi-VN)
- 泰语 (th-TH)
- 印地语 (hi-IN)
- 印尼语 (id-ID)
- 马来语 (ms-MY)
- 菲律宾语 (fil-PH)

#### 欧洲语言（24种）
- 英语 (en-US)
- 德语 (de-DE)
- 法语 (fr-FR)
- 西班牙语 (es-ES)
- 意大利语 (it-IT)
- 俄语 (ru-RU)
- 波兰语 (pl-PL)
- 捷克语 (cs-CZ)
- 芬兰语 (fi-FI)
- 土耳其语 (tr-TR)
- 乌克兰语 (uk-UA)
- 罗马尼亚语 (ro-RO)
- 保加利亚语 (bg-BG)
- 加泰罗尼亚语 (ca-ES)
- 丹麦语 (da-DK)
- 希腊语 (el-GR)
- 克罗地亚语 (hr-HR)
- 匈牙利语 (hu-HU)
- 挪威语 (nb-NO)
- 荷兰语 (nl-NL)
- 斯洛伐克语 (sk-SK)
- 斯洛文尼亚语 (sl-SI)
- 瑞典语 (sv-SE)
- 塞尔维亚语 (sr-RS)

#### 其他语言（4种）
- 阿拉伯语 (ar-SA)
- 波斯语 (fa-IR)
- 希伯来语 (he-IL)
- 葡萄牙语 (pt-PT)

### 1.2 语言文件组织结构

```
main/assets/locales/
├── en-US/
│   ├── language.json          # 英文字符串资源
│   ├── 0.ogg ~ 9.ogg          # 数字音效
│   ├── activation.ogg          # 激活音效
│   ├── err_pin.ogg             # SIM卡错误音效
│   ├── err_reg.ogg             # 网络注册错误音效
│   ├── upgrade.ogg             # 升级音效
│   ├── welcome.ogg             # 欢迎音效
│   └── wificonfig.ogg          # WiFi配置音效
├── zh-CN/
│   ├── language.json           # 中文字符串资源
│   └── (同样的音效文件)
├── ja-JP/
├── ko-KR/
... (其他38种语言)
└── common/
    ├── exclamation.ogg         # 通用音效
    ├── low_battery.ogg
    ├── popup.ogg
    ├── success.ogg
    └── vibration.ogg
```

### 1.3 语言文件格式

**language.json 结构示例：**

```json
{
    "language": {
        "type": "zh-CN"
    },
    "strings": {
        "WARNING": "警告",
        "INFO": "信息",
        "ERROR": "错误",
        "VERSION": "版本 ",
        "LOADING_PROTOCOL": "登录服务器...",
        "INITIALIZING": "正在初始化...",
        "CONNECTING": "连接中...",
        "CONNECTION_SUCCESSFUL": "连接成功",
        "SERVER_NOT_FOUND": "服务器未找到",
        "BATTERY_LOW": "电量低",
        "BATTERY_CHARGING": "充电中",
        "BATTERY_FULL": "电量充足",
        "VOLUME": "音量",
        "MUTED": "静音",
        "MAX_VOLUME": "最大音量",
        "LISTENING": "监听中",
        "SPEAKING": "说话中",
        "ACTIVATION": "激活",
        "OTA_UPGRADE": "OTA升级",
        "UPGRADING": "升级中",
        "UPGRADE_FAILED": "升级失败"
    }
}
```

### 1.4 语言生成脚本

**脚本位置：** `scripts/gen_lang.py`

**功能说明：**

1. **基准语言加载**
   - 加载 en-US 作为基准语言
   - 统计基准语言中的字符串数量

2. **字符串合并机制**
   - 以 en-US 为基准
   - 用户选择的语言覆盖基准语言
   - 缺失的字符串自动回退到 en-US

3. **音效文件处理**
   - 收集当前语言的音效文件
   - 收集 en-US 的音效文件作为备用
   - 收集通用音效文件
   - 优先使用当前语言的音效，缺失时回退到 en-US

4. **生成 C++ 头文件**
   - 输出：`main/assets/lang_config.h`
   - 包含所有字符串常量
   - 包含所有音效资源的二进制引用

**使用方式：**

```bash
python scripts/gen_lang.py --language zh-CN --output main/assets/lang_config.h
```

**输出统计信息示例：**

```
Language zh-CN string statistics:
  - Base language (en-US): 54 strings
  - User language: 53 strings
  - Total: 54 strings
  - Fallback to en-US: 1 strings

Language zh-CN sound statistics:
  - Base language (en-US): 8 sounds
  - User language: 8 sounds
  - Common sounds: 5 sounds
  - Sound fallback to en-US: 0 sounds
```

### 1.5 配置方法

**步骤1：选择语言**

```bash
idf.py menuconfig
# 导航: Xiaozhi Assistant > Default Language > 选择所需语言
```

**步骤2：编译固件**

```bash
idf.py build
```

编译过程中会自动：
1. 读取选定语言的 language.json
2. 运行 gen_lang.py 生成 lang_config.h
3. 嵌入所有语言音效文件
4. 编译生成固件

### 1.6 运行时使用

**代码示例：**

```cpp
#include "assets/lang_config.h"

// 使用字符串资源
const char* status = Lang::Strings::CONNECTING;
display->SetStatus(status);

// 使用音效资源
std::string_view sound = Lang::Sounds::OGG_WELCOME;
audio_player->Play(sound);
```

### 1.7 关键特性

- ✅ **38种语言支持**：覆盖全球主要语言
- ✅ **自动回退机制**：缺失资源自动使用英文版本
- ✅ **编译时生成**：所有资源在编译时处理，运行时无额外开销
- ✅ **音效本地化**：每种语言都有对应的语音提示
- ✅ **通用音效**：某些音效在所有语言中共用
- ✅ **灵活扩展**：易于添加新语言

---

## 2. 硬件板型支持

### 2.1 板型统计

- **总计板型数量**: 110+
- **支持的芯片**: ESP32、ESP32-C3、ESP32-S3、ESP32-P4、ESP32-C5、ESP32-C6
- **板型文档数量**: 73 个 README.md

### 2.2 主要品牌和系列

| 品牌 | 板型示例 | 数量 | 特点 |
|------|---------|------|------|
| **Espressif** | esp-box, esp-box-3, esp-box-lite | 6+ | 官方开发板 |
| **M5Stack** | m5stack-core-s3, atom-echos3r | 3+ | 模块化设计 |
| **LILYGO** | lilygo-t-circle-s3 | 2+ | 创客友好 |
| **Waveshare** | waveshare-s3-touch-amoled-* | 12+ | 多样化屏幕 |
| **荔枝派** | lichuang-c3-dev | 2+ | 国产开发板 |
| **Bread Compact** | bread-compact-wifi | 6+ | 紧凑设计 |
| **小智立方** | xingzhi-cube-* | 4+ | 专用硬件 |
| **其他品牌** | ATK、kevin、movecall 等 | 70+ | 多样化选择 |

### 2.3 板型配置文件结构

```
main/boards/{board-name}/
├── {board}_board.cc      # 板级类实现
├── config.h              # GPIO 脚位、采样率、显示参数
├── config.json           # 构建元数据
└── README.md             # 板级专用文档
```

### 2.4 板型层次结构

```cpp
Board (基类)
├── WifiBoard (WiFi 基础板型)
│   ├── EspBox3Board
│   ├── M5StackCoreS3Board
│   └── [70+ WiFi 变体]
├── DualNetworkBoard (WiFi + 4G)
│   └── ML307 调制解调器板型
└── [自定义板型实现]
```

---

## 3. 音频编解码器系统

### 3.1 编解码器驱动列表

| 编解码器 | 芯片类型 | 用途 | 特点 |
|---------|---------|------|------|
| **ES8311** | Everest Semi ES8311 | 单芯片编解码器 | 全双工、低成本 |
| **ES8388** | Everest Semi ES8388 | 双通道编解码器 | 支持AEC参考 |
| **ES8374** | Everest Semi ES8374 | 低功耗编解码器 | 集成功放 |
| **ES8389** | Everest Semi ES8389 | 高级编解码器 | 高输入增益 |
| **Box Audio** | ES8311+ES7210 | 多芯片方案 | 麦克风阵列(4路) |
| **No Audio** | 无芯片 | I2S直通 | 软件仿真 |

**文件位置**: `main/audio/codecs/`

### 3.2 编解码器基类接口

```cpp
class AudioCodec {
public:
    // 音量和增益控制
    virtual void SetOutputVolume(int volume);
    virtual void SetInputGain(float gain);

    // 开关控制
    virtual void EnableInput(bool enable);
    virtual void EnableOutput(bool enable);

    // 数据读写
    virtual void OutputData(std::vector<int16_t>& data);
    virtual bool InputData(std::vector<int16_t>& data);

    // 属性查询
    inline int input_sample_rate() const;
    inline int output_sample_rate() const;
    inline bool duplex() const;
    inline bool input_reference() const;  // AEC支持
};
```

### 3.3 代表性编解码器

#### ES8311 - 单芯片方案

**技术规格**:
- 采样率: 16kHz, 24kHz, 48kHz
- 通道数: 单声道
- 全双工: 是
- I2C地址: 0x10

**使用场景**: 简单语音设备、成本敏感应用

#### Box Audio Codec - 麦克风阵列方案

**架构**:
- DAC: ES8311（扬声器输出）
- ADC: ES7210（4路麦克风输入）

**技术规格**:
- 支持4个麦克风
- AEC参考输入
- TDM模式输入

**使用场景**: ESP-Box-3、高端语音设备

### 3.4 编解码器选择矩阵

| 板型 | 编解码器 | 采样率 | 特殊功能 |
|------|---------|--------|---------|
| ESP-Box-3 | BoxAudioCodec | 24kHz | 麦克风阵列+AEC |
| M5Stack Core S3 | ES8311 | 16kHz | 单麦克风 |
| MinSi K08 | NoAudioCodec | 16kHz | I2S直通 |
| Waveshare S3 | BoxAudioCodec | 24kHz | 麦克风阵列 |

---

## 4. 显示系统抽象

### 4.1 显示类型列表

| 显示类型 | 适用场景 | 特点 | 分辨率 |
|---------|---------|------|--------|
| **NoDisplay** | 纯语音设备 | 最小资源占用 | 无 |
| **OledDisplay** | 小屏设备 | 低功耗、单色 | 128x64/128x32 |
| **LcdDisplay** | 中等屏幕 | 彩色、成本低 | 240-480px |
| **EmoteDisplay** | 机器人/玩具 | 实时表情动画 | 可变 |
| **LvglDisplay** | 通用彩屏 | 功能丰富 | 可变 |

**文件位置**: `main/display/`

### 4.2 显示系统架构

```cpp
Display (基类)
├── NoDisplay (无头模式)
├── LvglDisplay (LVGL基础)
│   ├── OledDisplay (OLED)
│   └── LcdDisplay (LCD)
│       ├── SpiLcdDisplay (SPI接口)
│       ├── RgbLcdDisplay (RGB接口)
│       └── MipiLcdDisplay (MIPI接口)
└── EmoteDisplay (情感化显示)
```

### 4.3 显示基类接口

```cpp
class Display {
public:
    // 状态和通知
    virtual void SetStatus(const char* status);
    virtual void ShowNotification(const char* notification, int duration_ms);

    // 情感和消息
    virtual void SetEmotion(const char* emotion);
    virtual void SetChatMessage(const char* role, const char* content);

    // 主题和控制
    virtual void SetTheme(Theme* theme);
    virtual void UpdateStatusBar(bool update_all);
    virtual void SetPowerSaveMode(bool on);
};
```

### 4.4 显示类型对比

| 特性 | NoDisplay | OledDisplay | LcdDisplay | EmoteDisplay |
|------|-----------|-------------|------------|--------------|
| 功耗 | 最低 | 低 | 中 | 高 |
| 成本 | 无 | 低 | 中 | 高 |
| 色彩 | 无 | 单色 | 彩色 | 彩色 |
| 动画 | 无 | 有限 | 丰富 | 实时 |
| 分辨率 | 无 | 128x64 | 240-480px | 可变 |

---

## 5. 通信协议实现

### 5.1 协议类型

xiaozhi-esp32 支持两种主要通信协议：

| 协议 | 控制通道 | 音频通道 | 特点 |
|------|---------|---------|------|
| **WebSocket** | WebSocket | WebSocket (二进制) | 简单、防火墙友好 |
| **MQTT+UDP** | MQTT | UDP (AES加密) | 低延迟、高实时性 |

**文件位置**: `main/protocols/`

### 5.2 协议基类接口

```cpp
class Protocol {
public:
    // 核心接口
    virtual bool Start() = 0;
    virtual bool OpenAudioChannel() = 0;
    virtual void CloseAudioChannel() = 0;
    virtual bool SendAudio(std::unique_ptr<AudioStreamPacket> packet) = 0;

    // 回调注册
    void OnIncomingAudio(callback);
    void OnIncomingJson(callback);
    void OnAudioChannelOpened(callback);
    void OnAudioChannelClosed(callback);
    void OnNetworkError(callback);
};
```

### 5.3 WebSocket 协议

#### 协议版本

- **版本1**: 直接发送Opus音频数据
- **版本2**: 带时间戳的二进制协议（支持服务器端AEC）
- **版本3**: 简化的二进制协议（4字节头部）

#### 帧格式

**版本2格式**:
```
[version(2) | type(2) | reserved(4) | timestamp(4) | size(4) | payload]
```

**版本3格式**:
```
[type(1) | reserved(1) | size(2) | payload]
```

#### Hello消息

```json
{
  "type": "hello",
  "version": 1,
  "features": {
    "mcp": true,
    "aec": true
  },
  "transport": "websocket",
  "audio_params": {
    "format": "opus",
    "sample_rate": 16000,
    "channels": 1,
    "frame_duration": 60
  }
}
```

### 5.4 MQTT+UDP 协议

#### 双通道架构

- **MQTT通道**: 控制消息、状态同步、JSON数据
- **UDP通道**: 实时音频数据（AES-CTR加密）

#### 加密机制

- **算法**: AES-CTR（计数器模式）
- **密钥长度**: 128位
- **Nonce长度**: 128位
- **序列号保护**: 防止重放攻击

#### UDP音频包格式

```
[type(1) | flags(1) | payload_len(2) | ssrc(4) | timestamp(4) | sequence(4) | encrypted_payload]
```

### 5.5 协议对比

| 特性 | WebSocket | MQTT+UDP |
|------|-----------|----------|
| 实时性 | 中等 | 高 |
| 可靠性 | 高 | 中等 |
| 复杂度 | 低 | 高 |
| 加密 | TLS | AES-CTR |
| 防火墙友好 | 是 | 否 |
| 防重放攻击 | 否 | 是 |

### 5.6 使用场景

**WebSocket适用于**:
- 跨越防火墙/NAT的场景
- 需要高可靠性
- 实现简单性优先

**MQTT+UDP适用于**:
- 对实时性要求极高
- 网络环境相对稳定
- 需要防重放攻击保护

---

## 总结

xiaozhi-esp32 项目展现了出色的规模和模块化设计：

- ✅ **38种语言** - 全球化支持
- ✅ **110+硬件板型** - 广泛的硬件兼容性
- ✅ **6种音频编解码器** - 灵活的音频方案
- ✅ **5种显示类型** - 从无显示到高清屏幕
- ✅ **2种通信协议** - 适应不同网络环境

这种设计使得项目能够在各种不同的硬件平台和应用场景中运行，提供了极高的可移植性和扩展性。

