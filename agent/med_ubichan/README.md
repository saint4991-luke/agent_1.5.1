# 🏥 醫療展 Virtual Human Agent (med_ubichan)

**版本：** v1.0  
**日期：** 2026-05-22  
**規格文檔：** [MED_UBIAGENT.md](../../docs/01_designs/MED_UBIAGENT.md)

---

## 📋 模組概述

`med_ubichan` 是醫療展場景專用的 Virtual Human Agent 模組，實現 **UbiChan × 小護士** 雙機器人協作架構。

### 主要角色

| 角色 | 類型 | 職責 |
|------|------|------|
| **UbiChan** | 虛擬人 (Kiosk 螢幕) | 對話接待、需求判斷、指令下達 |
| **小護士** | 引導機器人 (地面) | 帶路引導、物品運送、現場互動 |

### 支持場景

- ✅ 掛號引導
- ✅ 藥局取藥
- ✅ 地點詢問（主動帶路）
- ✅ 取消動作

---

## 🏗️ 模組結構

```
agent/med_ubichan/
├── __init__.py                      # 模組初始化
├── config_loader.py                 # 配置載入器（YAML）
├── output_formatter.py              # UbiChan 輸出格式化器
├── robot_action_generator.py        # 小護士 Action 生成器
└── README.md                        # 本文檔
```

---

## 🚀 快速開始

### 1. 導入模組

```python
from agent.med_ubichan import (
    MedUbiConfigLoader,
    MedUbiOutputFormatter,
    RobotActionGenerator
)

# 初始化
config_loader = MedUbiConfigLoader()
formatter = MedUbiOutputFormatter()
action_gen = RobotActionGenerator()
```

### 2. 載入配置

```python
# 載入醫療展虛擬人配置
config = config_loader.get('med_ubichan')

# 取得 Intent 分類映射
intent_mapping = config_loader.get_intent_mapping('med_ubichan')

# 取得地點列表
locations = config_loader.get_locations('med_ubichan')
# 返回：['counter', 'registration', 'pharmacy']
```

### 3. 格式化 UbiChan 輸出

```python
# 格式化回應（符合 09_OUTPUT_FORMAT.md 規格）
output = formatter.format_ubichan_response(
    text="好的，小護士會帶你去掛號處。請跟著它走。",
    emotion="happy",
    lang="tw"
)

# 輸出：
# <!-- emotion -->happy<!-- /emotion -->
# <!-- lang -->tw (zh)<!-- /lang -->
#
# 好的，小護士會帶你去掛號處。<sbr>
# 請跟著它走。<sbr>
```

### 4. 生成小護士 Action

```python
# 生成導航 Action
action = action_gen.generate_navigate_action(
    target="registration",
    speech="我帶你去掛號處，請跟我來"
)

# 取得 JSON 格式
json_output = action.to_json()
# {
#     "robot": "baxiaomi",
#     "action": "navigate",
#     "params": {"target": "registration"},
#     "speech": "我帶你去掛號處，請跟我來"
# }

# 取得自然語言步驟描述
steps = action.natural_language_steps
# 第一步，讓小護士移動到櫃台（counter）前方。
# 第二步，讓小護士對 user 說「我帶你去掛號處，請跟我來」。
# 第三步，讓小護士導航到掛號處（registration）。
# 第四步，讓小護士對 user 說「掛號處到了，祝你掛號順利」。
```

---

## 📊 完整使用範例

### 情境：用戶說「我想要掛號」

```python
from agent.med_ubichan import MedUbiOutputFormatter, RobotActionGenerator

# 初始化
formatter = MedUbiOutputFormatter()
action_gen = RobotActionGenerator()

# 1. 生成 UbiChan 回應
ubichan_text = "好的，小護士會帶你去掛號處。請跟著它走。"
ubichan_output = formatter.format_ubichan_response(
    text=ubichan_text,
    emotion="happy",
    lang="tw"
)

# 2. 生成小護士 Action
robot_action = action_gen.generate_navigate_action(
    target="registration",
    speech="你好，請跟我來掛號處"
)

# 3. 格式化完整輸出
complete_output = action_gen.format_complete_output(
    ubichan_text=ubichan_text,
    robot_action=robot_action,
    emotion="happy",
    lang="tw"
)

# 輸出結果：
print("=== UbiChan 輸出 ===")
print(complete_output['ubichan_output'])

print("\n=== 小護士 JSON 指令 ===")
print(complete_output['robot_json'])

print("\n=== 小護士自然語言步驟 ===")
print(complete_output['robot_steps'])
```

### 完整輸出範例

```
=== UbiChan 輸出 ===
<!-- emotion -->happy<!-- /emotion -->
<!-- lang -->tw (zh)<!-- /lang -->

好的，小護士會帶你去掛號處。<sbr>
請跟著它走。<sbr>

=== 小護士 JSON 指令 ===
{
  "robot": "baxiaomi",
  "action": "navigate",
  "params": {"target": "registration"},
  "speech": "你好，請跟我來掛號處"
}

=== 小護士自然語言步驟 ===
第一步，讓小護士移動到櫃台（counter）前方。
第二步，讓小護士對 user 說「你好，請跟我來掛號處」。
第三步，讓小護士導航到掛號處（registration）。
第四步，讓小護士對 user 說「掛號處到了，祝你掛號順利」。
```

---

## 🎯 Intent 分類

根據 [MED_UBIAGENT.md](../../docs/01_designs/MED_UBIAGENT.md) 規格，支持以下 Intent：

| Intent | 關鍵字 | 小護士 Action |
|--------|--------|--------------|
| `registration` | 掛號、登記、報到 | `navigate` → `registration` |
| `pharmacy` | 拿藥、取藥、藥品 | `pickup_item` → `pharmacy` |
| `cancel` | 停止、取消、不要了 | `cancel` |
| `info_location` | 哪裡、怎麼走、在哪 | `navigate` → 自動判斷 |
| `info_other` | 其他資訊詢問 | 無動作 |

---

## 📐 輸出格式規格

### UbiChan 輸出格式

遵循 [09_OUTPUT_FORMAT.md](../../docs/03_specs/09_OUTPUT_FORMAT.md)：

```
<!-- emotion -->{emotion}<!-- /emotion -->
<!-- lang -->{lang}<!-- /lang -->

{sentence}<sbr>
{sentence}<sbr>
```

### 小護士 Action 格式

```json
{
  "robot": "baxiaomi",
  "action": "{action_name}",
  "params": { ... },
  "speech": "{可選語音}"
}
```

### 自然語言步驟描述

```
第一步，讓小護士移動到 [地點]。
第二步，讓小護士對 [對象] 說「[語音內容]」。
第三步，讓小護士導航到 [地點]。
第四步，讓小護士對 [對象] 說「[語音內容]」。
```

---

## 🧪 測試

```python
# 測試 UbiChan 輸出格式化
def test_ubichan_output():
    formatter = MedUbiOutputFormatter()
    output = formatter.format_ubichan_response(
        text="你好！今天天氣真好。",
        emotion="happy",
        lang="tw"
    )
    assert "<!-- emotion -->happy<!-- /emotion -->" in output
    assert "<!-- lang -->tw (zh)<!-- /lang -->" in output
    assert "<sbr>" in output
    print("✅ UbiChan 輸出測試通過")

# 測試小護士 Action 生成
def test_robot_action():
    action_gen = RobotActionGenerator()
    action = action_gen.generate_navigate_action(
        target="registration",
        speech="請跟我來"
    )
    assert action.action == "navigate"
    assert action.params["target"] == "registration"
    assert action.speech == "請跟我來"
    assert action.natural_language_steps is not None
    print("✅ 小護士 Action 測試通過")

# 執行測試
test_ubichan_output()
test_robot_action()
```

---

## 📚 相關文檔

| 文檔 | 說明 |
|------|------|
| [MED_UBIAGENT.md](../../docs/01_designs/MED_UBIAGENT.md) | 醫療展 Virtual Human Agent 設計規格 |
| [09_OUTPUT_FORMAT.md](../../docs/03_specs/09_OUTPUT_FORMAT.md) | UbiChan 輸出格式規格 |
| [08_TOOL_SPEC.md](../../docs/03_specs/08_TOOL_SPEC.md) | Tool 定義規格 |

---

## 🦐 開發團隊

**醫療展專案 - UbiChan × 小護士 聯手服務！**

---

**最後更新：** 2026-05-22
