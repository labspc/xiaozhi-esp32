# 下一代AI语音助手协议设计（VASP v1.0）

## Voice Assistant Streaming Protocol

**设计目标**：创建一个开放、标准化的AI语音助手协议，兼容xiaozhi生态，同时成为行业标准。

---

## 一、设计哲学

### 1.1 核心原则

**像MCP一样成为标准**：
- ✅ 开放规范，任何人可实现
- ✅ 版本化，向后兼容
- ✅ 文档完善，易于理解
- ✅ 社区驱动，持续演进

**解决现有问题**：
- ❌ xiaozhi协议版本混乱（v1/v2/v3）
- ❌ 缺乏标准化的错误处理
- ❌ 扩展性有限
- ❌ 安全性较弱

**保持兼容性**：
- ✅ 设备可同时支持xiaozhi协议和VASP
- ✅ 服务器可通过协商选择协议
- ✅ 平滑迁移路径

---

## 二、协议概述

### 2.1 协议命名

**VASP** - Voice Assistant Streaming Protocol

**版本**: v1.0 (2026-01-16)

**灵感来源**：
- MCP (Model Context Protocol) - 工具调用标准
- WebRTC - 实时音视频传输
- gRPC - 高性能RPC框架
- HTTP/2 - 多路复用和流控

### 2.2 协议特性

| 特性 | xiaozhi协议 | VASP v1.0 |
|------|------------|-----------|
| **版本协商** | ⚠️ 固定版本号 | ✅ 能力协商 |
| **传输层** | WebSocket/MQTT+UDP | WebSocket/HTTP/2/QUIC |
| **帧格式** | 简单二进制 | 灵活帧结构 |
| **消息格式** | 自定义JSON | JSON-RPC 2.0 |
| **错误处理** | ⚠️ 有限 | ✅ 标准错误码 |
| **流控** | ❌ 无 | ✅ 背压机制 |
| **安全性** | Bearer Token | OAuth 2.0/mTLS |
| **扩展性** | ⚠️ 有限 | ✅ 插件机制 |
| **多模态** | ❌ 仅音频 | ✅ 音频/视频/文本 |

---

## 三、协议架构

### 3.1 分层设计

```
┌─────────────────────────────────────────────┐
│  Application Layer (应用层)                  │
│  - 语音识别/合成                              │
│  - 工具调用（MCP兼容）                        │
│  - 会话管理                                   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Message Layer (消息层)                      │
│  - JSON-RPC 2.0消息                          │
│  - 请求/响应/通知                             │
│  - 错误处理                                   │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Frame Layer (帧层)                          │
│  - 二进制帧封装                               │
│  - 流控和优先级                               │
│  - 压缩和加密                                 │
└─────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────┐
│  Transport Layer (传输层)                    │
│  - WebSocket (默认)                          │
│  - HTTP/2 (可选)                             │
│  - QUIC (未来)                               │
└─────────────────────────────────────────────┘
```

### 3.2 协议栈对比

**xiaozhi协议栈**:
```
应用 → 自定义JSON → 简单二进制帧 → WebSocket
```

**VASP协议栈**:
```
应用 → JSON-RPC 2.0 → 标准化帧 → WebSocket/HTTP/2
```

---

## 四、帧层设计（Frame Layer）

### 4.1 帧格式

**VASP帧结构**（灵活且可扩展）:

```c
struct VASPFrame {
    // 帧头（8字节）
    uint8_t  magic[2];        // 魔数：0x56 0x41 ('V' 'A')
    uint8_t  version;         // 协议版本：0x01
    uint8_t  flags;           // 标志位
    uint16_t stream_id;       // 流ID（支持多路复用）
    uint16_t frame_type;      // 帧类型

    // 帧体长度（4字节）
    uint32_t payload_length;  // 负载长度（网络字节序）

    // 可选扩展头（变长）
    uint8_t  extensions[];    // 扩展字段（根据flags决定）

    // 负载数据（变长）
    uint8_t  payload[];       // 实际数据

    // 可选校验（4字节）
    uint32_t checksum;        // CRC32校验（根据flags决定）
} __attribute__((packed));
```

**字段说明**:

**magic** (2字节):
- 固定值：`0x56 0x41` ('V' 'A')
- 用于快速识别VASP协议

**version** (1字节):
- 当前版本：`0x01`
- 支持版本协商

**flags** (1字节):
```
Bit 7: 是否有扩展头
Bit 6: 是否压缩（gzip/zstd）
Bit 5: 是否加密（AES-GCM）
Bit 4: 是否有校验和
Bit 3: 优先级（高）
Bit 2: 优先级（中）
Bit 1: 是否流结束（FIN）
Bit 0: 保留
```

**stream_id** (2字节):
- 支持多路复用（类似HTTP/2）
- 0x0000: 控制流
- 0x0001-0xFFFE: 数据流
- 0xFFFF: 广播

**frame_type** (2字节):
```
0x0001: HELLO（握手）
0x0002: HELLO_ACK（握手响应）
0x0010: AUDIO_DATA（音频数据）
0x0011: VIDEO_DATA（视频数据）
0x0012: TEXT_DATA（文本数据）
0x0020: RPC_REQUEST（RPC请求）
0x0021: RPC_RESPONSE（RPC响应）
0x0022: RPC_ERROR（RPC错误）
0x0030: STREAM_CONTROL（流控制）
0x0031: PING（心跳）
0x0032: PONG（心跳响应）
0x00FF: GOODBYE（断开连接）
```

### 4.2 帧类型详解

#### **HELLO帧（0x0001）**

握手帧，建立连接时发送。

**Payload（JSON格式）**:
```json
{
  "protocol": "VASP",
  "version": "1.0",
  "client_id": "uuid",
  "capabilities": {
    "audio": {
      "codecs": ["opus", "aac", "pcm"],
      "sample_rates": [16000, 24000, 48000],
      "channels": [1, 2]
    },
    "video": {
      "codecs": ["h264", "vp9"],
      "resolutions": ["640x480", "1280x720"]
    },
    "features": {
      "mcp": true,
      "streaming": true,
      "multiplexing": true,
      "compression": ["gzip", "zstd"],
      "encryption": ["aes-gcm"]
    }
  },
  "auth": {
    "type": "bearer",
    "token": "xxx"
  }
}
```

#### **HELLO_ACK帧（0x0002）**

服务器响应握手。

**Payload**:
```json
{
  "protocol": "VASP",
  "version": "1.0",
  "session_id": "session_uuid",
  "selected_capabilities": {
    "audio": {
      "codec": "opus",
      "sample_rate": 24000,
      "channels": 1
    },
    "features": {
      "compression": "zstd",
      "encryption": "aes-gcm"
    }
  },
  "server_info": {
    "name": "xiaozhi-server",
    "version": "3.0.0"
  }
}
```

#### **AUDIO_DATA帧（0x0010）**

音频数据帧。

**Payload**:
```
[音频编码数据]
```

**扩展头**（如果flags.bit7=1）:
```c
struct AudioExtension {
    uint32_t timestamp;       // 时间戳（毫秒）
    uint16_t sequence;        // 序列号
    uint8_t  codec;           // 编码格式
    uint8_t  reserved;
};
```

#### **RPC_REQUEST帧（0x0020）**

RPC请求帧（兼容JSON-RPC 2.0）。

**Payload**:
```json
{
  "jsonrpc": "2.0",
  "method": "asr.recognize",
  "params": {
    "language": "zh-CN",
    "model": "whisper-large"
  },
  "id": 1
}
```

---

## 五、消息层设计（Message Layer）

### 5.1 消息格式标准

**采用JSON-RPC 2.0**（与MCP一致）

**优势**:
- ✅ 行业标准，工具链成熟
- ✅ 与MCP协议一致，易于集成
- ✅ 清晰的请求/响应/错误模型

### 5.2 核心消息类型

#### **1. 能力协商（Capability Negotiation）**

**请求**:
```json
{
  "jsonrpc": "2.0",
  "method": "vasp.negotiate",
  "params": {
    "client_capabilities": {
      "audio": ["opus", "aac"],
      "features": ["mcp", "streaming"]
    }
  },
  "id": 1
}
```

**响应**:
```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "server_capabilities": {
      "audio": ["opus"],
      "features": ["mcp", "streaming", "multiplexing"]
    },
    "selected": {
      "audio": "opus",
      "sample_rate": 24000
    }
  }
}
```

#### **2. 音频流控制**

**开始监听**:
```json
{
  "jsonrpc": "2.0",
  "method": "audio.listen.start",
  "params": {
    "stream_id": 1,
    "mode": "continuous",
    "vad_enabled": true
  },
  "id": 2
}
```

**停止监听**:
```json
{
  "jsonrpc": "2.0",
  "method": "audio.listen.stop",
  "params": {
    "stream_id": 1
  },
  "id": 3
}
```

#### **3. 语音识别结果**

**中间结果（通知）**:
```json
{
  "jsonrpc": "2.0",
  "method": "asr.result.partial",
  "params": {
    "stream_id": 1,
    "text": "你好",
    "confidence": 0.85,
    "is_final": false
  }
}
```

**最终结果**:
```json
{
  "jsonrpc": "2.0",
  "method": "asr.result.final",
  "params": {
    "stream_id": 1,
    "text": "你好世界",
    "confidence": 0.95,
    "is_final": true,
    "alternatives": [
      {"text": "你好事件", "confidence": 0.12}
    ]
  }
}
```

#### **4. TTS合成控制**

**请求合成**:
```json
{
  "jsonrpc": "2.0",
  "method": "tts.synthesize",
  "params": {
    "text": "你好，我是小智",
    "voice": "zh-CN-XiaoxiaoNeural",
    "speed": 1.0,
    "pitch": 0,
    "stream_id": 2
  },
  "id": 4
}
```

**合成开始通知**:
```json
{
  "jsonrpc": "2.0",
  "method": "tts.started",
  "params": {
    "stream_id": 2,
    "duration_estimate": 3500
  }
}
```

#### **5. MCP工具调用（完全兼容）**

**工具列表**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/list",
  "params": {},
  "id": 5
}
```

**工具调用**:
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "self.audio_speaker.set_volume",
    "arguments": {
      "volume": 50
    }
  },
  "id": 6
}
```

### 5.3 错误处理

**标准错误码**（扩展JSON-RPC 2.0）:

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "error": {
    "code": -32001,
    "message": "Audio codec not supported",
    "data": {
      "requested": "aac",
      "supported": ["opus", "pcm"]
    }
  }
}
```

**VASP错误码定义**:
```
-32000: 服务器内部错误
-32001: 不支持的编解码器
-32002: 不支持的采样率
-32003: 流ID冲突
-32004: 认证失败
-32005: 会话过期
-32006: 流控限制
-32007: 资源不足
-32100: ASR识别失败
-32101: TTS合成失败
-32200: MCP工具调用失败
```

