# VASP与XiaoZhi兼容性设计

## 六、兼容性策略

### 6.1 双协议支持架构

**核心思想**：设备同时支持xiaozhi协议和VASP协议，通过协商选择。

```
设备启动
  ↓
连接服务器
  ↓
发送HELLO（包含支持的协议列表）
  ↓
服务器选择协议
  ├─ xiaozhi协议 → 使用现有实现
  └─ VASP协议 → 使用新实现
```

### 6.2 协议检测机制

**方法1：通过HELLO消息协商**

```json
// 设备发送（支持两种协议）
{
  "type": "hello",
  "version": 1,
  "supported_protocols": [
    {
      "name": "xiaozhi",
      "version": "3"
    },
    {
      "name": "VASP",
      "version": "1.0"
    }
  ],
  "features": {
    "mcp": true,
    "aec": true
  }
}

// 服务器响应（选择协议）
{
  "type": "hello",
  "selected_protocol": {
    "name": "VASP",
    "version": "1.0"
  },
  "session_id": "xxx"
}
```

**方法2：通过魔数自动检测**

```c
// 读取前2字节
uint8_t magic[2];
read(socket, magic, 2);

if (magic[0] == 0x56 && magic[1] == 0x41) {
    // VASP协议（'V' 'A'）
    use_vasp_protocol();
} else {
    // xiaozhi协议（回退）
    use_xiaozhi_protocol();
}
```

### 6.3 代码架构设计

```cpp
// 协议抽象接口
class VoiceProtocol {
public:
    virtual bool Connect(const char* url) = 0;
    virtual bool SendAudio(const AudioPacket& packet) = 0;
    virtual bool SendMessage(const cJSON* json) = 0;
    virtual void SetCallbacks(ProtocolCallbacks* callbacks) = 0;
};

// xiaozhi协议实现（现有）
class XiaozhiProtocol : public VoiceProtocol {
    // 现有实现
};

// VASP协议实现（新增）
class VASPProtocol : public VoiceProtocol {
public:
    bool Connect(const char* url) override {
        // 1. 建立WebSocket连接
        // 2. 发送HELLO帧
        // 3. 等待HELLO_ACK
        // 4. 协商能力
    }

    bool SendAudio(const AudioPacket& packet) override {
        // 构造AUDIO_DATA帧
        VASPFrame frame;
        frame.magic[0] = 0x56;
        frame.magic[1] = 0x41;
        frame.version = 0x01;
        frame.frame_type = 0x0010;  // AUDIO_DATA
        frame.stream_id = audio_stream_id_;
        frame.payload_length = packet.size;
        // 发送帧
    }
};

// 协议工厂
class ProtocolFactory {
public:
    static VoiceProtocol* Create(const char* protocol_name) {
        if (strcmp(protocol_name, "xiaozhi") == 0) {
            return new XiaozhiProtocol();
        } else if (strcmp(protocol_name, "VASP") == 0) {
            return new VASPProtocol();
        }
        return nullptr;
    }
};
```

### 6.4 配置选项

```cpp
// menuconfig选项
CONFIG_PROTOCOL_XIAOZHI=y          // 支持xiaozhi协议
CONFIG_PROTOCOL_VASP=y             // 支持VASP协议
CONFIG_PROTOCOL_DEFAULT="VASP"    // 默认协议
CONFIG_PROTOCOL_AUTO_DETECT=y     // 自动检测协议
```

---

## 七、渐进迁移路径

### 7.1 阶段1：VASP协议实现（1-2个月）

**目标**：实现VASP协议的基础功能

**任务清单**：
- [ ] 定义VASP帧格式和消息格式
- [ ] 实现VASPProtocol类
- [ ] 实现帧编解码器
- [ ] 实现能力协商机制
- [ ] 单元测试

**里程碑**：
- VASP协议可以连接测试服务器
- 音频流传输正常
- MCP工具调用正常

### 7.2 阶段2：双协议支持（2-3周）

**目标**：设备同时支持xiaozhi和VASP

**任务清单**：
- [ ] 实现协议抽象接口
- [ ] 重构现有xiaozhi协议为XiaozhiProtocol类
- [ ] 实现协议工厂和自动检测
- [ ] 配置选项（menuconfig）
- [ ] 兼容性测试

**里程碑**：
- 设备可以连接xiaozhi.me（xiaozhi协议）
- 设备可以连接VASP服务器（VASP协议）
- 协议自动协商正常

### 7.3 阶段3：服务器端支持（并行开发）

**目标**：xiaozhi.me服务器支持VASP协议

**任务清单**：
- [ ] 服务器端VASP协议实现
- [ ] 协议协商逻辑
- [ ] 向后兼容xiaozhi协议
- [ ] 性能测试和优化

**里程碑**：
- xiaozhi.me同时支持两种协议
- 旧设备（xiaozhi协议）正常工作
- 新设备（VASP协议）正常工作

### 7.4 阶段4：生态推广（3-6个月）

**目标**：VASP成为开放标准

**任务清单**：
- [ ] 发布VASP规范文档
- [ ] 开源参考实现（设备端+服务器端）
- [ ] 提供SDK和示例代码
- [ ] 社区推广和反馈收集
- [ ] 规范迭代和完善

**里程碑**：
- VASP规范v1.0正式发布
- 至少3个第三方实现
- 社区采纳率>30%

---

## 八、VASP相比xiaozhi的优势

### 8.1 技术优势

| 特性 | xiaozhi协议 | VASP v1.0 | 提升 |
|------|------------|-----------|------|
| **版本管理** | 混乱（v1/v2/v3） | 清晰的版本协商 | ⭐⭐⭐⭐⭐ |
| **扩展性** | 有限 | 灵活的帧扩展机制 | ⭐⭐⭐⭐⭐ |
| **多路复用** | ❌ 不支持 | ✅ 支持（stream_id） | ⭐⭐⭐⭐ |
| **流控** | ❌ 无 | ✅ 背压机制 | ⭐⭐⭐⭐ |
| **错误处理** | 简单 | 标准错误码体系 | ⭐⭐⭐⭐ |
| **安全性** | Bearer Token | OAuth 2.0/mTLS | ⭐⭐⭐⭐ |
| **压缩** | ❌ 不支持 | ✅ gzip/zstd | ⭐⭐⭐ |
| **多模态** | 仅音频 | 音频/视频/文本 | ⭐⭐⭐⭐⭐ |

### 8.2 生态优势

**标准化**：
- ✅ 像MCP一样成为开放标准
- ✅ 任何人可以实现客户端/服务器
- ✅ 不绑定特定云平台

**互操作性**：
- ✅ VASP设备可以连接任何VASP服务器
- ✅ 不同厂商的设备可以互通
- ✅ 促进生态繁荣

**向后兼容**：
- ✅ 不破坏现有xiaozhi生态
- ✅ 平滑迁移路径
- ✅ 双协议共存

---

## 九、实施建议

### 9.1 优先级评估

**高优先级**（立即开始）：
1. ✅ 完成VASP规范文档（本文档）
2. ⏳ 实现VASP协议的设备端（VASPProtocol类）
3. ⏳ 实现协议抽象层（VoiceProtocol接口）

**中优先级**（1-2个月后）：
1. ⏳ 服务器端VASP协议实现
2. ⏳ 双协议兼容性测试
3. ⏳ 性能优化和压力测试

**低优先级**（3-6个月后）：
1. ⏳ 视频流支持
2. ⏳ HTTP/2传输层
3. ⏳ QUIC传输层

### 9.2 资源需求

**开发资源**：
- 设备端开发：1人 × 2个月
- 服务器端开发：1人 × 1.5个月
- 测试和文档：1人 × 1个月

**硬件资源**：
- 测试设备：8个核心板型
- 测试服务器：1台（用于VASP协议测试）

### 9.3 风险评估

**技术风险**：
- ⚠️ VASP协议复杂度高于xiaozhi
- ⚠️ 双协议支持增加代码量
- ⚠️ Flash空间可能不足（需要优化）

**应对措施**：
- 分阶段实现，先实现核心功能
- 通过menuconfig可选编译
- 代码优化和压缩

**生态风险**：
- ⚠️ 社区接受度未知
- ⚠️ 第三方实现需要时间

**应对措施**：
- 保持向后兼容xiaozhi协议
- 提供完整的SDK和文档
- 积极推广和社区建设

---

## 十、总结

### 10.1 核心价值

**VASP协议的核心价值**：

1. **标准化**：像MCP一样成为开放标准
2. **现代化**：采用现代协议设计（多路复用、流控、压缩）
3. **兼容性**：不破坏现有xiaozhi生态
4. **扩展性**：支持未来的多模态AI（视频、文本）
5. **互操作性**：促进生态繁荣

### 10.2 回答用户问题

**Q: 能不能在兼容xiaozhi协议的基础上，再做一个自有协议更好的协议？**

**A: 完全可以！**

**方案**：
- ✅ 设计VASP协议（Voice Assistant Streaming Protocol）
- ✅ 设备同时支持xiaozhi和VASP（双协议）
- ✅ 通过协商选择协议（向后兼容）
- ✅ VASP成为开放标准（像MCP一样）

**优势**：
- ✅ 不破坏现有生态（xiaozhi.me继续工作）
- ✅ 提供更好的技术方案（多路复用、流控、扩展性）
- ✅ 促进生态发展（开放标准，任何人可实现）

**实施路径**：
1. 完成VASP规范（已完成）
2. 实现设备端VASP协议（1-2个月）
3. 实现服务器端VASP协议（1-2个月）
4. 推广和生态建设（3-6个月）

### 10.3 下一步行动

**立即执行**：
- [ ] 审阅VASP规范文档
- [ ] 确认技术方案可行性
- [ ] 评估资源需求

**第一阶段**（1-2个月）：
- [ ] 实现VASPProtocol类
- [ ] 实现协议抽象层
- [ ] 单元测试和集成测试

**第二阶段**（2-3个月）：
- [ ] 服务器端VASP实现
- [ ] 双协议兼容性测试
- [ ] 性能优化

**第三阶段**（3-6个月）：
- [ ] 发布VASP规范v1.0
- [ ] 开源参考实现
- [ ] 社区推广

---

**文档版本**: v1.0
**创建时间**: 2026-01-16
**作者**: XiaoZhi架构团队
**状态**: RFC - 征求意见
