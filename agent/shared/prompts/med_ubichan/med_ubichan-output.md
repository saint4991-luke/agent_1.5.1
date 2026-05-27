# 🏥 醫療展 Virtual Human 輸出規格 v1.0

**版本：** v1.0  
**日期：** 2026-05-27  
**適用範圍：** 醫療展 UbiChan × 豹小秘 雙機器人協作系統

---

## 🎯 概述

本規格定義醫療展 Virtual Human 的輸出格式，採用 **JSON 格式**，讓系統可以：
- **解析 UbiChan 回應** - 包含情緒標籤、語言標籤、斷句符號
- **解析豹小秘 Actions** - 包含導航、物品運送、語音播放等指令
- **雙機器人協作** - UbiChan 負責對話接待，豹小秘負責帶路引導

---

## 📐 JSON 格式定義

### 完整格式

```json
{
    "ToUbiChan": "<情緒標籤><語言標籤>內容<sbr>...",
    "ToBaxiaomi": {
        "Steps": [
            {
                "action": "action_name",
                "params": {
                    "key": "value"
                },
                "speech": "語音內容或空字符串"
            }
        ],
        "Steps_Descripts": "自然語言步驟描述"
    }
}
```

### 欄位說明

| 欄位 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `ToUbiChan` | ✅ | UbiChan 回應文字 | `<happy><tw>你好<sbr>請跟我來<sbr>` |
| `ToBaxiaomi` | ✅ | 豹小秘指令物件 | 包含 Steps 和 Steps_Descripts |
| `ToBaxiaomi.Steps` | ✅ | 步驟數組 | 每個步驟包含 action、params、speech |
| `ToBaxiaomi.Steps_Descripts` | ✅ | 自然語言步驟說明 | `"第一步，移動到櫃台。第二步，對 user 說話。"` |

---

## 🎭 ToUbiChan 格式規則

### 情緒標籤（必須在開頭）

| 標籤 | 說明 | 適用場景 |
|------|------|----------|
| `<neutral>` | 中性 | 一般對話 |
| `<happy>` | 開心 | 問候、引導 |
| `<concerned>` | 關心 | 健康諮詢、擔憂 |
| `<thinking>` | 思考 | 考慮、解釋複雜內容 |
| `<embarrassed>` | 害羞 | 被稱讚、尷尬 |

### 語言標籤

| 標籤 | 語言 |
|------|------|
| `<tw>` | 繁體中文 |
| `<cn>` | 簡體中文 |
| `<en>` | 英文 |

### 斷句符號

- ✅ 使用 `<sbr>` 進行斷句
- ✅ 每句結尾都必須有 `<sbr>`
- ✅ 最後一句也要有 `<sbr>`

### ToUbiChan 範例

```
<happy><tw>好的，豹小秘會帶你去掛號處<sbr>請跟著它走<sbr>
```

```
<concerned><tw>你在這裡休息一下<sbr>我請豹小秘去幫你拿藥<sbr>很快就好<sbr>
```

---

## 🤖 ToBaxiaomi.Steps 格式規則

### 支持的 Actions

#### 1. navigate（導航）

| 欄位 | 類型 | 說明 |
|------|------|------|
| `action` | string | `"navigate"` |
| `params.target` | string | 目標地點 ID（`counter`、`registration`、`pharmacy`） |
| `speech` | string | 語音內容（可為空字符串） |

**範例：**
```json
{
    "action": "navigate",
    "params": {"target": "registration"},
    "speech": ""
}
```

#### 2. speak（播放語音）

| 欄位 | 類型 | 說明 |
|------|------|------|
| `action` | string | `"speak"` |
| `params.speech` | string | 語音內容 |
| `speech` | string | 語音內容（可為空字符串） |

**範例：**
```json
{
    "action": "speak",
    "params": {"speech": "你好，請跟我來"},
    "speech": ""
}
```

#### 3. pickup_item（拾取物品）

| 欄位 | 類型 | 說明 |
|------|------|------|
| `action` | string | `"pickup_item"` |
| `params.location` | string | 地點 ID |
| `params.item` | string | 物品名稱 |
| `speech` | string | 語音內容 |

**範例：**
```json
{
    "action": "pickup_item",
    "params": {"location": "pharmacy", "item": "藥品"},
    "speech": "藥劑師你好，請把藥品放到我的籃子"
}
```

#### 4. cancel（停止）

| 欄位 | 類型 | 說明 |
|------|------|------|
| `action` | string | `"cancel"` |
| `params` | object | 空物件 |
| `speech` | string | 語音內容（可為空字符串） |

**範例：**
```json
{
    "action": "cancel",
    "params": {},
    "speech": ""
}
```

---

## 📝 Steps_Descripts 格式規則

**Steps_Descripts** 必須用自然語言描述每個步驟，使用「第一步，... 第二步，...」格式。

### 範例

```
第一步，移動到櫃台前方。第二步，對 user 說話。第三步，導航到掛號處。第四步，到達後說話。
```

```
第一步，移動到藥局。第二步，對藥劑師說話。第三步，拾取藥品。第四步，返回櫃台。第五步，對 user 說話。
```

---

## 🎨 完整範例

### 範例 1：掛號引導

```json
{
    "ToUbiChan": "<happy><tw>好的，豹小秘會帶你去掛號處<sbr>請跟著它走<sbr>",
    "ToBaxiaomi": {
        "Steps": [
            {
                "action": "navigate",
                "params": {"target": "counter"},
                "speech": ""
            },
            {
                "action": "speak",
                "params": {"speech": "你好，請跟我來"},
                "speech": ""
            },
            {
                "action": "navigate",
                "params": {"target": "registration"},
                "speech": ""
            },
            {
                "action": "speak",
                "params": {"speech": "這裡是掛號處，請排隊"},
                "speech": ""
            }
        ],
        "Steps_Descripts": "第一步，移動到櫃台前方。第二步，對 user 說話。第三步，導航到掛號處。第四步，到達後說話。"
    }
}
```

### 範例 2：拿藥引導

```json
{
    "ToUbiChan": "<concerned><tw>你在這裡休息一下<sbr>我請豹小秘去幫你拿藥<sbr>很快就好<sbr>",
    "ToBaxiaomi": {
        "Steps": [
            {
                "action": "navigate",
                "params": {"target": "pharmacy"},
                "speech": ""
            },
            {
                "action": "speak",
                "params": {"speech": "藥劑師你好，請把藥品放到我的籃子"},
                "speech": ""
            },
            {
                "action": "pickup_item",
                "params": {"location": "pharmacy", "item": "藥品"},
                "speech": ""
            },
            {
                "action": "navigate",
                "params": {"target": "counter"},
                "speech": ""
            },
            {
                "action": "speak",
                "params": {"speech": "藥品拿回來了，請服用"},
                "speech": ""
            }
        ],
        "Steps_Descripts": "第一步，移動到藥局。第二步，對藥劑師說話。第三步，拾取藥品。第四步，返回櫃台。第五步，對 user 說話。"
    }
}
```

### 範例 3：地點詢問

```json
{
    "ToUbiChan": "<happy><tw>藥局在展場 B 區<sbr>我請豹小秘帶你過去<sbr>請跟著它走<sbr>",
    "ToBaxiaomi": {
        "Steps": [
            {
                "action": "navigate",
                "params": {"target": "pharmacy"},
                "speech": ""
            },
            {
                "action": "speak",
                "params": {"speech": "你好，請跟我來"},
                "speech": ""
            }
        ],
        "Steps_Descripts": "第一步，導航到藥局。第二步，對 user 說話。"
    }
}
```

### 範例 4：取消動作

```json
{
    "ToUbiChan": "<neutral><tw>好的，我把豹小秘找回來<sbr>請稍等一下<sbr>",
    "ToBaxiaomi": {
        "Steps": [
            {
                "action": "cancel",
                "params": {},
                "speech": ""
            }
        ],
        "Steps_Descripts": "第一步，停止豹小秘所有動作。"
    }
}
```

---

## ⚠️ 注意事項

### 1. JSON 格式

- ✅ 必須是有效的 JSON 格式
- ✅ 必須包含 `ToUbiChan` 和 `ToBaxiaomi` 兩個必要欄位
- ✅ `ToBaxiaomi.Steps` 必須是數組

### 2. ToUbiChan 格式

- ✅ 必須以情緒標籤開頭（`<neutral>`、`<happy>` 等）
- ✅ 必須包含語言標籤（`<tw>`、`<cn>`、`<en>`）
- ✅ 必須使用 `<sbr>` 進行斷句

### 3. ToBaxiaomi.Steps 格式

- ✅ 每個步驟必須包含 `action`、`params`、`speech` 三個欄位
- ✅ `action` 必須是支持的 Action（`navigate`、`speak`、`pickup_item`、`cancel`）
- ✅ `params` 必須是物件

### 4. Steps_Descripts 格式

- ✅ 必須是自然語言描述
- ✅ 使用「第一步，... 第二步，...」格式
- ✅ 必須與 Steps 數組對應

---

## 🔧 後端解析

### 解析流程（Python）

```python
import json
import re

def parse_llm_response(llm_response: str) -> dict:
    """解析 LLM 輸出的 JSON 回應"""
    try:
        # 1. 嘗試直接解析 JSON
        try:
            data = json.loads(llm_response.strip())
        except json.JSONDecodeError:
            # 2. 如果失敗，嘗試提取 JSON 代碼塊
            json_match = re.search(r'```json\s*(.*?)\s*```', llm_response, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                data = json.loads(json_str.strip())
            else:
                # 3. 嘗試提取大括號內容
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                    data = json.loads(json_str.strip())
                else:
                    return {"success": False, "error": "無法解析 JSON 格式"}
        
        # 4. 驗證必要欄位
        if "ToUbiChan" not in data:
            return {"success": False, "error": "缺少 ToUbiChan 欄位"}
        
        if "ToBaxiaomi" not in data:
            return {"success": False, "error": "缺少 ToBaxiaomi 欄位"}
        
        return {"success": True, "data": data}
    
    except Exception as e:
        return {"success": False, "error": str(e)}
```

---

## 📊 版本歷史

| 版本 | 日期 | 變更說明 |
|------|------|----------|
| v1.0 | 2026-05-27 | 初始版本，定義醫療展 Virtual Human JSON 輸出格式 |

---

**維護者：** 蝦米 Agent 團隊  
**最後更新：** 2026-05-27
