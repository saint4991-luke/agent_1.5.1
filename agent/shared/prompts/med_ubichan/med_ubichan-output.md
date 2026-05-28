# 🏥 醫療展 Virtual Human 輸出規格 v1.1

**版本：** v1.1  
**日期：** 2026-05-28  
**適用範圍：** 醫療展 UbiChan × 豹小秘 雙機器人協作系統  
**參考規格：** AIAGENT-VirtualAvatarTextStreamFormatSpecification-Reference.pdf v1.1.0

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
    "ToUbiChan": "<!-- emotion>happy</emotion --><!-- lang>tw (zh)</lang -->內容<sbr>...",
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
| `ToUbiChan` | ✅ | UbiChan 回應文字 | `<!-- emotion>happy</emotion --><!-- lang>tw (zh)</lang -->你好<sbr>請跟我來<sbr>` |
| `ToBaxiaomi` | ✅ | 豹小秘指令物件 | 包含 Steps 和 Steps_Descripts |
| `ToBaxiaomi.Steps` | ✅ | 步驟數組 | 每個步驟包含 action、params、speech |
| `ToBaxiaomi.Steps_Descripts` | ✅ | 自然語言步驟說明 | `"第一步，移動到櫃台。第二步，對 user 說話。"` |

---

## 🎭 ToUbiChan 格式規則

### 情緒標籤（Emotion Tags）

**格式：** `<!-- emotion>{emotion}</emotion -->`

| 標籤 | 說明 | 適用場景 |
|------|------|----------|
| `neutral` | 中性 | 一般對話、準備狀態 |
| `happy` | 開心 | 問候、引導、歡迎 |
| `sad` | 悲傷 | 表達遺憾、同理 |
| `angry` | 生氣 | 表達挫折（謹慎使用） |
| `surprised` | 驚訝 | 意外情況 |
| `excited` | 興奮 | 熱情歡迎 |
| `thinking` | 思考 | 考慮、解釋複雜內容 |
| `embarrassed` | 害羞 | 被稱讚、尷尬 |
| `concerned` | 關心 | 健康諮詢、擔憂 |
| `serious` | 嚴肅 | 重要說明 |
| `encouraging` | 鼓勵 | 打氣、支持 |
| `empathetic` | 同理 | 理解用戶感受 |
| `relaxed` | 輕鬆 | 休閒對話 |
| `dance` | 舞蹈 | 歡慶動作（特殊場合） |
| `sing` | 唱歌 | 特殊互動 |
| `photo` | 拍照 | 拍照姿勢 |

**範例：**
```
<!-- emotion>happy</emotion -->
<!-- emotion>neutral</emotion -->
<!-- emotion>concerned</emotion -->
```

### 語言標籤（Language Tags）

**格式：** `<!-- lang>{language_code}</lang -->`

| 代碼 | 語言 | 說明 |
|------|------|------|
| `tw (zh)` | 繁體中文 | 台灣中文 |
| `cn (zh)` | 簡體中文 | 中國大陸 |
| `en` | 英文 | English |
| `ja` | 日文 | 日本語 |
| `ko` | 韓文 | 한국어 |
| `fr` | 法文 | Français |
| `de` | 德文 | Deutsch |
| `it` | 義大利文 | Italiano |
| `es` | 西班牙文 | Español |
| `nl` | 荷蘭文 | Nederlands |
| `ru` | 俄文 | Русский |
| `pt` | 葡萄牙文 | Português |

**範例：**
```
<!-- lang>tw (zh)</lang -->
<!-- lang>en</lang -->
<!-- lang>ja</lang -->
```

### 斷句符號（Sentence Breakdown）

根據 **Virtual Avatar Text Stream Format Specification v1.1.0** 第 3 節：

#### Hard Breaks（立即斷句）
- **中文：** `。！？……`
- **英文：** `. ! ? …`
- **日文：** `。！？……`
- **韓文：** `. ! ? …`
- **規則：** 當出現 Hard break 時，立即切分累積文字
- **特殊情況：** 括號/引號結尾（如 `)」』）》】`）也可視為 Hard breaks

#### Medium Breaks（條件斷句）
- **中文：** `；：—\n`
- **英文：** `; : — \n`
- **規則：** 如果出現 Medium break **且** 累積文字長度 ≥ 10 字元，則切分
- **特殊情況：** 換行符號 (`\n`) 可視為 Medium break

#### Soft Breaks（軟性斷句）
- **中文：** `，、、`
- **英文：** `,`
- **日文：** `,`
- **韓文：** `, ·`
- **規則：** 當累積文字過長（≥ 80 字元）時，在最近的 Soft break 處切分

#### 錯誤防護規則

**不要斷句的情況：**
1. **英文縮寫：** `Mr.`, `Ms.`, `Dr.`, `Prof.`, `vs.`, `e.g.`, `i.e.`, `U.S.`
2. **英文所有格/縮約：** `it's`, `don't`, `isn't`, `can't`, `John's`
3. **數字/小數點：** `3.14`, `10.30`, `1.2.3`, `ver.2.0`
4. **URLs/Emails：** `://`, `www.`, `@`
5. **日文長音符：** `ー`

#### ToUbiChan 斷句範例

```
<!-- emotion>happy</emotion --><!-- lang>tw (zh)</lang -->
好的，豹小秘會帶你去掛號處<sbr>
請跟著它走<sbr>
```

```
<!-- emotion>concerned</emotion --><!-- lang>tw (zh)</lang -->
你在這裡休息一下<sbr>
我請豹小秘去幫你拿藥<sbr>
很快就好<sbr>
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
    "ToUbiChan": "<!-- emotion>happy</emotion --><!-- lang>tw (zh)</lang -->好的，豹小秘會帶你去掛號處<sbr>請跟著它走<sbr>",
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
    "ToUbiChan": "<!-- emotion>concerned</emotion --><!-- lang>tw (zh)</lang -->你在這裡休息一下<sbr>我請豹小秘去幫你拿藥<sbr>很快就好<sbr>",
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
    "ToUbiChan": "<!-- emotion>happy</emotion --><!-- lang>tw (zh)</lang -->藥局在展場 B 區<sbr>我請豹小秘帶你過去<sbr>請跟著它走<sbr>",
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
    "ToUbiChan": "<!-- emotion>neutral</emotion --><!-- lang>tw (zh)</lang -->好的，我把豹小秘找回來<sbr>請稍等一下<sbr>",
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

- ✅ 必須使用 XML 註解格式的情緒標籤：`<!-- emotion>{emotion}</emotion -->`
- ✅ 必須使用 XML 註解格式的語言標籤：`<!-- lang>{language_code}</lang -->`
- ✅ 必須使用 `<sbr>` 進行斷句
- ✅ 標籤順序：先 `emotion`，再 `lang`

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
| v1.1 | 2026-05-28 | 更新情緒標籤和語言標籤格式，符合 AIAGENT-VirtualAvatarTextStreamFormatSpecification-Reference.pdf v1.1.0 |

---

## 📚 參考文件

- **AIAGENT-VirtualAvatarTextStreamFormatSpecification-Reference.pdf** v1.1.0
  - Section 2: General Format
  - Section 3: Sentence Breakdown Rules
  - Section 4: Actions

---

**維護者：** 蝦米 Agent 團隊  
**最後更新：** 2026-05-28
