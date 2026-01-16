#!/usr/bin/env python3
"""
分析 XiaoZhi ESP32 项目中所有支持的板型
按照厂商国别、芯片类型进行分类
"""

import json
import os
from pathlib import Path
from collections import defaultdict

# 板型厂商分类（基于前缀和已知信息）
VENDOR_INFO = {
    # 中国企业
    "esp-box": {"name": "Espressif (乐鑫)", "country": "中国", "type": "官方开发板"},
    "esp-hi": {"name": "Espressif (乐鑫)", "country": "中国", "type": "官方开发板"},
    "esp-s3": {"name": "Espressif (乐鑫)", "country": "中国", "type": "官方开发板"},
    "esp-p4": {"name": "Espressif (乐鑫)", "country": "中国", "type": "官方开发板"},
    "esp-sensairshuttle": {"name": "Espressif (乐鑫)", "country": "中国", "type": "官方开发板"},
    "esp-sparkbot": {"name": "Espressif (乐鑫)", "country": "中国", "type": "官方开发板"},
    "esp-spot": {"name": "Espressif (乐鑫)", "country": "中国", "type": "官方开发板"},
    "esp32": {"name": "通用ESP32", "country": "中国", "type": "通用板型"},
    "esp32s3": {"name": "通用ESP32-S3", "country": "中国", "type": "通用板型"},

    "m5stack": {"name": "M5Stack", "country": "中国", "type": "开源硬件"},
    "atom": {"name": "M5Stack (Atom系列)", "country": "中国", "type": "开源硬件"},

    "lilygo": {"name": "LilyGo (深圳市立派科技)", "country": "中国", "type": "开源硬件"},

    "df-": {"name": "DFRobot (上海智位机器人)", "country": "中国", "type": "教育/开源硬件"},

    "waveshare": {"name": "Waveshare (微雪电子)", "country": "中国", "type": "模块厂商"},

    "atk-": {"name": "正点原子 (Alientek)", "country": "中国", "type": "教育/开发板"},

    "lichuang": {"name": "立创开发板", "country": "中国", "type": "开发板/EDA平台"},

    "labplus": {"name": "LabPlus (盛思科教)", "country": "中国", "type": "教育硬件"},

    "movecall": {"name": "魔趣科技", "country": "中国", "type": "智能硬件"},

    "xingzhi": {"name": "行知科技", "country": "中国", "type": "智能硬件"},

    "zhengchen": {"name": "正臣科技", "country": "中国", "type": "物联网模块"},

    "minsi": {"name": "敏思科技", "country": "中国", "type": "智能硬件"},

    "genjutech": {"name": "根聚科技", "country": "中国", "type": "智能硬件"},

    "jiuchuan": {"name": "玖川科技", "country": "中国", "type": "智能硬件"},

    "yunliao": {"name": "云辽科技", "country": "中国", "type": "智能硬件"},

    "xmini": {"name": "XMini", "country": "中国", "type": "智能硬件"},

    "magiclick": {"name": "MagiClick", "country": "中国", "type": "智能硬件"},

    "mixgo": {"name": "MixGo", "country": "中国", "type": "教育硬件"},

    "bread-compact": {"name": "Bread Compact", "country": "中国", "type": "定制硬件"},

    "kevin-": {"name": "Kevin定制板", "country": "中国", "type": "定制硬件"},

    "sp-esp32": {"name": "SP系列", "country": "中国", "type": "定制硬件"},

    "taiji-pi": {"name": "太极派", "country": "中国", "type": "教育硬件"},

    "tudouzi": {"name": "土豆子", "country": "中国", "type": "智能硬件"},

    "surfer": {"name": "Surfer", "country": "中国", "type": "智能硬件"},

    "aipi": {"name": "AIPI", "country": "中国", "type": "AI硬件"},

    "doit": {"name": "DoIt (四博智联)", "country": "中国", "type": "物联网模块"},

    "du-chatx": {"name": "DU ChatX", "country": "中国", "type": "智能硬件"},

    "echoear": {"name": "EchoEar", "country": "中国", "type": "智能硬件"},

    "hu-087": {"name": "HU-087", "country": "中国", "type": "智能硬件"},

    "wireless-tag": {"name": "Wireless-Tag", "country": "中国", "type": "智能硬件"},

    # 国际企业/社区
    "sensecap": {"name": "SenseCAP (Seeed Studio)", "country": "国际", "type": "开源硬件"},

    "otto": {"name": "Otto Robot", "country": "国际", "type": "开源机器人"},

    "electron-bot": {"name": "Electron Bot", "country": "国际", "type": "开源硬件"},
}

def get_vendor_info(board_name):
    """根据板型名称获取厂商信息"""
    for prefix, info in VENDOR_INFO.items():
        if board_name.startswith(prefix):
            return info
    return {"name": "未分类", "country": "未知", "type": "其他"}

def analyze_boards():
    boards_dir = Path("main/boards")
    boards = []

    # 遍历所有板型目录
    for board_dir in sorted(boards_dir.iterdir()):
        if not board_dir.is_dir() or board_dir.name == "common":
            continue

        board_name = board_dir.name
        config_file = board_dir / "config.json"

        board_info = {
            "name": board_name,
            "path": str(board_dir),
        }

        # 读取配置文件
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    board_info["target"] = config.get("target", "unknown")
                    board_info["flash_size"] = config.get("sdkconfig_append", {}).get("CONFIG_ESPTOOLPY_FLASHSIZE", "unknown")
            except Exception as e:
                board_info["target"] = "error"
                board_info["error"] = str(e)
        else:
            board_info["target"] = "no-config"

        # 获取厂商信息
        vendor = get_vendor_info(board_name)
        board_info["vendor_name"] = vendor["name"]
        board_info["country"] = vendor["country"]
        board_info["type"] = vendor["type"]

        boards.append(board_info)

    return boards

def generate_markdown_report(boards):
    """生成Markdown格式的分析报告"""

    # 统计数据
    china_boards = [b for b in boards if b["country"] == "中国"]
    intl_boards = [b for b in boards if b["country"] == "国际"]
    unknown_boards = [b for b in boards if b["country"] == "未知"]

    # 按芯片类型分类
    chip_stats = defaultdict(int)
    for board in boards:
        chip_stats[board.get("target", "unknown")] += 1

    # 按厂商分类
    vendor_stats = defaultdict(list)
    for board in boards:
        vendor_stats[board["name"]].append(board)

    # 生成报告
    report = []
    report.append("# XiaoZhi ESP32 支持的板型分析报告")
    report.append(f"\n**生成时间**: {Path.cwd()}")
    report.append(f"**项目**: XiaoZhi ESP32 v2.1.0")
    report.append(f"\n## 概览")
    report.append(f"\n- **总板型数**: {len(boards)}")
    report.append(f"- **中国企业板型**: {len(china_boards)} ({len(china_boards)/len(boards)*100:.1f}%)")
    report.append(f"- **国际企业板型**: {len(intl_boards)} ({len(intl_boards)/len(boards)*100:.1f}%)")
    report.append(f"- **未分类板型**: {len(unknown_boards)} ({len(unknown_boards)/len(boards)*100:.1f}%)")

    # 芯片类型统计
    report.append(f"\n## 按芯片类型分布")
    report.append("\n| 芯片型号 | 数量 | 占比 |")
    report.append("|---------|------|------|")
    for chip, count in sorted(chip_stats.items(), key=lambda x: -x[1]):
        report.append(f"| {chip} | {count} | {count/len(boards)*100:.1f}% |")

    # 中国企业板型详细列表
    report.append(f"\n## 中国企业板型 ({len(china_boards)}个)")

    # 按厂商分组
    china_vendors = defaultdict(list)
    for board in china_boards:
        china_vendors[board["vendor_name"]].append(board)

    for vendor_name in sorted(china_vendors.keys()):
        boards_list = china_vendors[vendor_name]
        report.append(f"\n### {vendor_name} ({len(boards_list)}个板型)")
        report.append(f"\n**类型**: {boards_list[0]['type']}")
        report.append(f"\n| 板型名称 | 芯片型号 | Flash大小 |")
        report.append("|---------|---------|----------|")
        for board in sorted(boards_list, key=lambda x: x["name"]):
            flash_size = board.get("flash_size", "unknown").replace("CONFIG_ESPTOOLPY_FLASHSIZE_", "").replace("MB=y", "MB")
            report.append(f"| `{board['name']}` | {board.get('target', 'unknown')} | {flash_size} |")

    # 国际企业板型
    if intl_boards:
        report.append(f"\n## 国际企业/社区板型 ({len(intl_boards)}个)")

        intl_vendors = defaultdict(list)
        for board in intl_boards:
            intl_vendors[board["vendor_name"]].append(board)

        for vendor_name in sorted(intl_vendors.keys()):
            boards_list = intl_vendors[vendor_name]
            report.append(f"\n### {vendor_name} ({len(boards_list)}个板型)")
            report.append(f"\n**类型**: {boards_list[0]['type']}")
            report.append(f"\n| 板型名称 | 芯片型号 | Flash大小 |")
            report.append("|---------|---------|----------|")
            for board in sorted(boards_list, key=lambda x: x["name"]):
                flash_size = board.get("flash_size", "unknown").replace("CONFIG_ESPTOOLPY_FLASHSIZE_", "").replace("MB=y", "MB")
                report.append(f"| `{board['name']}` | {board.get('target', 'unknown')} | {flash_size} |")

    # 未分类板型
    if unknown_boards:
        report.append(f"\n## 未分类板型 ({len(unknown_boards)}个)")
        report.append(f"\n| 板型名称 | 芯片型号 | Flash大小 |")
        report.append("|---------|---------|----------|")
        for board in sorted(unknown_boards, key=lambda x: x["name"]):
            flash_size = board.get("flash_size", "unknown").replace("CONFIG_ESPTOOLPY_FLASHSIZE_", "").replace("MB=y", "MB")
            report.append(f"| `{board['name']}` | {board.get('target', 'unknown')} | {flash_size} |")

    # 社区活跃度分析
    report.append(f"\n## 社区活跃度分析")
    report.append(f"\n### 中国市场")
    report.append(f"\n**优势**:")
    report.append(f"- **生态完整**: 覆盖教育（正点原子、LabPlus）、开源硬件（M5Stack、LilyGo）、商业模块（微雪、立创）等各个领域")
    report.append(f"- **芯片原厂支持**: Espressif（乐鑫）官方提供多款开发板")
    report.append(f"- **社区活跃**: QQ群1011329060，文档使用飞书，适合中国开发者")
    report.append(f"- **硬件多样性**: 支持ESP32/C3/S3/P4/C6全系列芯片")
    report.append(f"- **定制化强**: 多个定制板型（Kevin系列、Bread系列等）说明项目灵活性高")

    report.append(f"\n### 国际市场")
    report.append(f"\n**现状**:")
    report.append(f"- **板型较少**: 仅{len(intl_boards)}个国际板型 vs {len(china_boards)}个中国板型")
    report.append(f"- **代表厂商**: Seeed Studio (SenseCAP)、开源机器人社区")
    report.append(f"- **增长潜力**: 项目基于ESP-IDF和开源协议，具备国际化基础")

    report.append(f"\n**建议**:")
    report.append(f"- 增加英文文档和国际社区渠道（Discord/GitHub Discussions）")
    report.append(f"- 支持更多国际流行的开发板（Arduino、Adafruit等）")
    report.append(f"- 提供英文版服务器和示例代码注释")

    # 技术特点总结
    report.append(f"\n## 技术特点总结")
    report.append(f"\n1. **芯片覆盖全面**: 支持ESP32全系列（ESP32/C3/S3/P4/C6）")
    report.append(f"2. **显示方案多样**: LCD、OLED、AMOLED、E-Paper等")
    report.append(f"3. **网络连接丰富**: WiFi、4G（ML307调制解调器）、双网络板型")
    report.append(f"4. **尺寸规格齐全**: 从0.85寸到7寸屏幕")
    report.append(f"5. **应用场景广泛**: 语音助手、机器人、教育、物联网等")

    # 厂商类型分布
    report.append(f"\n## 厂商类型分布")
    type_stats = defaultdict(int)
    for board in boards:
        type_stats[board["type"]] += 1

    report.append(f"\n| 厂商类型 | 数量 | 占比 |")
    report.append(f"|---------|------|------|")
    for type_name, count in sorted(type_stats.items(), key=lambda x: -x[1]):
        report.append(f"| {type_name} | {count} | {count/len(boards)*100:.1f}% |")

    return "\n".join(report)

if __name__ == "__main__":
    print("正在分析板型配置...")
    boards = analyze_boards()

    print(f"找到 {len(boards)} 个板型配置")

    # 生成报告
    report = generate_markdown_report(boards)

    # 保存到文件
    output_file = "BOARD_ANALYSIS.md"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"报告已生成: {output_file}")

    # 同时输出到控制台
    print("\n" + "="*80)
    print(report)
