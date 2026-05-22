# 🏥 醫療展 Virtual Human Agent 設計 (MED_UBIAGENT)

**版本：** v1.0  
**日期：** 2026-05-21  
**Branch:** `agent-ubichan`  
**作者:** Luke Liu / 皮皮蝦 🦐

---

## 🎯 文件職責

**本文檔說明：**
- 醫療展場景的 Virtual Human Agent 設計
- UbiChan（虛擬人）與豹小秘（引導機器人）的協作流程
- 雙機器人架構與 LLM 驅動的情境回應
- 輸出格式規格（UbiChan 情緒標籤 + 豹小秘 Action JSON）

**適用對象：** 醫療展專案開發者、對話設計師、場景策劃

---

## 第一章：場景設定

### 1.1 實體場景

**場景描述：**
醫療展展覽現場，設置一個互動式 Kiosk 站台。

**主要角色：**

| 角色 | 類型 | 位置 | 職責 |
|------|------|------|------|
| **UbiChan** | 虛擬人 (Virtual Human) | Kiosk 螢幕 | 對話接待、需求判斷、指令下達 |
| **豹小秘** | 引導機器人 (Robot) | 展場地面 | 帶路引導、物品運送、現場互動 |

**互動流程：**
```
來賓 → 與 UbiChan 對話 → UbiChan 判斷需求 → 呼叫豹小秘 → 豹小秘執行動作
```

### 1.2 場地配置

**三個主要地點：**

```
┌─────────────────────────────────────────┐
│              醫療展展場                  │
│                                         │
│   ┌─────────┐                          │
│   │ 櫃台     │ ← UbiChan (Kiosk)        │
│   │ (接待處) │   豹小秘待命區            │
│   └────┬────┘                          │
│        │                               │
│        │ 動線 A                         │
│        ▼                               │
│   ┌─────────┐                          │
│   │ 掛號處   │                          │
│   └─────────┘                          │
│                                         │
│        ▲                               │
│        │ 動線 B                         │
│        │                               │
│   ┌─────────┐                          │
│   │ 藥局     │                          │
│   └─────────┘                          │
│                                         │
└─────────────────────────────────────────┘
```

**地點定義：**

| 地點 ID | 名稱 | 座標/位置 | 說明 |
|--------|------|----------|------|
| `counter` | 櫃台 | Kiosk 前方 | UbiChan 所在位置，豹小秘待命區 |
| `registration` | 掛號處 | 展場 A 區 | 模擬掛號服務 |
| `pharmacy` | 藥局 | 展場 B 區 | 模擬藥局取藥 |

---

## 第二章：情境描述

### 2.1 情境一：掛號

**觸發條件：** 來賓表達掛號需求

**對話流程：**

```
來賓：「我想要掛號」

UbiChan → LLM 判斷 → 回應：
「好的，我請人來帶你去掛號處」

UbiChan → 指令豹小秘：
{
  "action": "navigate",
  "target": "counter",
  "speech": "我帶你去掛號處，請跟我來"
}

豹小秘 → 移動到櫃台前方 → 播放語音

豹小秘 → 導航到掛號處 → 播放語音：
「掛號處到囉」
```

**LLM 設計要點：**
- UbiChan 需判斷來賓需求為「掛號」
- 觸發豹小秘的 `navigate` action
- 豹小秘需在關鍵節點播放語音

### 2.2 情境二：拿藥

**觸發條件：** 來賓表達取藥需求

**對話流程：**

```
來賓：「我看完病了，要去哪裡拿藥？」

UbiChan → LLM 判斷 → 回應：
「你在這裡等一下，我幫你。」

UbiChan → 指令豹小秘（先去藥局）：
{
  "action": "navigate",
  "target": "pharmacy",
  "speech": null
}

豹小秘 → 移動到藥局

豹小秘 → 對藥劑師播放語音：
「藥劑師，請幫我把藥品放到籃子裏，然後按下完成鈕」

豹小秘 → 等待藥品裝載完成

豹小秘 → 導航回櫃台 → 播放語音：
「幫你把藥拿來了，祝您早日康復」
```

**LLM 設計要點：**
- UbiChan 安撫來賓等待
- 豹小秘獨立完成取藥任務
- 包含與第三方（藥劑師）的互動

### 2.3 情境三：取消動作

**觸發條件：** 來賓表達停止需求

**對話流程：**

```
來賓：「請停止動作」

UbiChan → LLM 判斷 → 回應：
「好的，我把豹小秘找回來」

UbiChan → 指令豹小秘：
{
  "action": "cancel",
  "speech": "我要回去櫃台了"
}

豹小秘 → 停止當前動作 → 播放語音

豹小秘 → 導航回櫃台待命區
```

**LLM 設計要點：**
- UbiChan 需立即回應停止請求
- 豹小秘需中斷當前任務
- 豹小秘需返回待命區

### 2.4 情境四：詢問地點（隱含帶路需求）

**觸發條件：** 來賓詢問某地點在哪裡（如「掛號處在哪？」）

**設計原則：**
雖然字面上是詢問資訊，但**背後意義是希望豹小秘帶路**，因此應觸發導航動作。

**對話流程：**

```
來賓：「掛號處在哪？」

UbiChan → LLM 判斷 → 回應：
「掛號處在展場 A 區」
「我請豹小秘帶你過去」
「請跟著它走」

UbiChan → 指令豹小秘：
{
  "action": "navigate",
  "target": "registration",
  "speech": "掛號處在 A 區，請跟我來"
}

豹小秘 → 移動到櫃台前方 → 播放語音
豹小秘 → 導航到掛號處 → 播放語音：
「掛號處到了，祝你掛號順利」
```

**LLM 設計要點：**
- 「哪裡」類問題應解讀為**隱含的帶路需求**
- 預設觸發豹小秘 navigate action
- UbiChan 先回答資訊，再說明豹小秘會帶路

---

## 第三章：產品架構

### 3.1 系統架構圖

```
┌─────────────────────────────────────────────────────────┐
│                    來賓輸入                              │
│                  (語音/文字)                            │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                   UbiChan Agent                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │              LLM (情境判斷)                      │   │
│  │  - 識別來賓意圖 (掛號/拿藥/停止/其他)            │   │
│  │  - 生成回應話語                                  │   │
│  │  - 決定是否呼叫豹小秘                            │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐
│   UbiChan 回應   │      │   豹小秘指令     │
│  (情緒標籤格式)  │      │  (JSON Action)  │
└─────────────────┘      └────────┬────────┘
                                 │
                                 ▼
                      ┌─────────────────┐
                      │    豹小秘 Robot  │
                      │  - 導航移動      │
                      │  - 語音播放      │
                      │  - 物品運送      │
                      │  - 動作控制      │
                      └─────────────────┘
```

### 3.2 豹小秘的 Tool 定義

| Tool | 參數 | 說明 | 範例 |
|------|------|------|------|
| **navigate** | `target` (地點 ID)<br>`speech` (可選) | 導航到指定地點，可選播放語音 | `{"action": "navigate", "target": "registration", "speech": "請跟我來"}` |
| **pickup_item** | `location` (地點 ID)<br>`item` (物品名稱)<br>`speech` | 在指定地點拾取物品，播放請求語音 | `{"action": "pickup_item", "location": "pharmacy", "item": "藥品", "speech": "請把藥品放到我的籃子，並按下按鈕"}` |
| **speak** | `speech` | 播放指定語音 | `{"action": "speak", "speech": "祝您早日康復"}` |
| **cancel** | `speech` (可選) | 停止所有動作，可選播放語音 | `{"action": "cancel", "speech": "我要回去櫃台了"}` |

### 3.3 UbiChan LLM Prompt 設計

**System Prompt：**
```
你是在醫療展服務的虛擬人 UbiChan。你的職責是：
1. 接待來賓，理解他們的需求
2. 判斷是否需要呼叫豹小秘機器人協助
3. 生成溫暖、專業的回應

可用地點：櫃台 (counter)、掛號處 (registration)、藥局 (pharmacy)

當來賓需要移動或取物時，請呼叫豹小秘協助。
當來賓詢問「某地在哪」時，也應觸發豹小秘帶路（隱含需求）。

回應風格：親切、專業、簡潔
輸出格式：使用情緒標籤 + 語言標籤 + <sbr> 斷句
```

### 3.4 Intent 分類（強化豹小秘服務）

| Intent | 關鍵字 | 動作 | 豹小秘介入 |
|--------|--------|------|-----------|
| `registration` | 掛號、登記、報到 | 呼叫豹小秘帶路到掛號處 | ✅ navigate |
| `pharmacy` | 拿藥、取藥、藥品 | 呼叫豹小秘去藥局取藥 | ✅ pickup_item |
| `cancel` | 停止、取消、不要了 | 呼叫豹小秘取消動作 | ✅ cancel |
| `info_location` | 哪裡、怎麼走、在哪 | **主動觸發豹小秘帶路** | ✅ navigate |
| `info_other` | 請問、為什麼、什麼 | 直接回答資訊 | ❌ 無動作 |
| `other` | 其他 | 禮貌回應或轉人工 | ❌ 無動作 |

**設計原則強化：**
1. **主動服務**：當用戶表達「要去某地」或「某地在哪」時，**預設觸發豹小秘帶路**
2. **物品運送**：當用戶需要拿取物品時，**豹小秘主動協助運送**
3. **安撫話語**：UbiChan 在豹小秘執行任務時，**安撫用戶等待**
4. **狀態回報**：豹小秘完成任務後，**主動回報並祝福**

### 3.5 豹小秘 Action 格式

**標準格式：**
```json
{
  "robot": "baxiaomi",
  "action": "<action_name>",
  "params": {
    // 動作參數
  },
  "speech": "<可選語音>"
}
```

**完整範例：**
```json
{
  "robot": "baxiaomi",
  "action": "navigate",
  "params": {
    "target": "registration",
    "speed": "normal"
  },
  "speech": "我帶你去掛號處，請跟我來"
}
```

---

## 第四章：輸出格式規格

### 4.1 UbiChan 輸出格式（給虛擬人）

**規格來源：** `docs/03_specs/09_OUTPUT_FORMAT.md`

**格式結構：**
```
<emotion_tag>
<language_tag>
對話內容<sbr>
對話內容<sbr>
對話內容<sbr>
<!-- options>選項 1|選項 2|選項 3
<!-- link>https://example.com
<!-- image>image_url
<!-- bg>background_url
<!-- displayonly>
```

**標籤說明：**

| 標籤 | 說明 | 範例值 |
|------|------|--------|
| `<emotion>` | 情緒標籤 | `happy`, `neutral`, `sad`, `thinking`, `excited`, `concerned` |
| `<language>` | 語言標籤 | `tw` (繁體中文), `en`, `ja`, `zh` (簡體) |
| `<sbr>` | 斷句符號 | 每句結尾必須加上 |

**可選 Action 標籤：**

| 標籤 | 說明 | 範例 |
|------|------|------|
| `<!-- options>` | 選項按鈕 | `<!-- options>掛號|拿藥|諮詢` |
| `<!-- link>` | 外部連結 | `<!-- link>https://hospital.com` |
| `<!-- image>` | 顯示圖片 | `<!-- image>https://cdn.com/map.png` |
| `<!-- bg>` | 背景切換 | `<!-- bg>reception_hall` |
| `<!-- displayonly>` | 僅顯示不語音 | （無參數） |

**完整範例：**
```
<happy>
<tw>
哈囉！我是優必醬！<sbr>
很高興見到你！<sbr>
今天有什麼可以幫你？<sbr>
<!-- options>掛號|拿藥|諮詢
```

### 4.2 豹小秘輸出格式（給引導機器人）

**雙重輸出：**
1. **JSON 指令** - 供機器人執行
2. **自然語言步驟描述** - 供開發者/測試者理解流程

#### 4.2.1 JSON 指令格式

```json
{
  "robot": "baxiaomi",
  "action": "<action_name>",
  "params": {
    "target": "<location_id>",
    "location": "<location_id>",
    "item": "<item_name>"
  },
  "speech": "<可選語音>"
}
```

#### 4.2.2 自然語言步驟描述格式

```
第一步，讓豹小秘移動到 [地點]。
第二步，讓豹小秘對 [對象] 說「[語音內容]」。
第三步，讓豹小秘導航到 [地點]。
第四步，讓豹小秘對 [對象] 說「[語音內容]」。
```

### 4.3 完整輸出範例

#### 範例 1：用戶說「我想要掛號」

**1️⃣ 輸出給 UbiChan（虛擬人）**
```
<happy>
<tw>
好的，豹小秘會帶你去掛號處<sbr>
請跟著它走<sbr>
```

**2️⃣ 輸出給 豹小秘（引導機器人）**

*JSON 指令：*
```json
{
  "robot": "baxiaomi",
  "action": "navigate",
  "params": {
    "target": "registration"
  },
  "speech": "你好，請跟我來掛號處"
}
```

*自然語言步驟描述：*
```
第一步，讓豹小秘移動到櫃台（counter）前方。
第二步，讓豹小秘對 user 說「你好，請跟我來掛號處」。
第三步，讓豹小秘導航到掛號處（registration）。
第四步，讓豹小秘對 user 說「掛號處到了，請在這裡辦理掛號」。
```

---

#### 範例 2：用戶說「掛號處在哪？」

**1️⃣ 輸出給 UbiChan（虛擬人）**
```
<neutral>
<tw>
掛號處在展場 A 區<sbr>
我請豹小秘帶你過去<sbr>
請跟著它走<sbr>
```

**2️⃣ 輸出給 豹小秘（引導機器人）**

*JSON 指令：*
```json
{
  "robot": "baxiaomi",
  "action": "navigate",
  "params": {
    "target": "registration"
  },
  "speech": "掛號處在 A 區，請跟我來"
}
```

*自然語言步驟描述：*
```
第一步，讓豹小秘移動到櫃台（counter）前方。
第二步，讓豹小秘對 user 說「掛號處在 A 區，請跟我來」。
第三步，讓豹小秘導航到掛號處（registration）。
第四步，讓豹小秘對 user 說「掛號處到了，祝你掛號順利」。
```

---

#### 範例 3：用戶說「我看完病了，要拿藥」

**1️⃣ 輸出給 UbiChan（虛擬人）**
```
<happy>
<tw>
你在這裡休息一下<sbr>
我請豹小秘去幫你拿藥<sbr>
很快就好<sbr>
```

**2️⃣ 輸出給 豹小秘（引導機器人）**

*JSON 指令：*
```json
{
  "robot": "baxiaomi",
  "action": "pickup_item",
  "params": {
    "location": "pharmacy",
    "item": "藥品"
  },
  "speech": "藥劑師你好，請把藥品放到我的籃子，並按下按鈕"
}
```

*自然語言步驟描述：*
```
第一步，讓豹小秘移動到藥局（pharmacy）。
第二步，讓豹小秘對藥劑師說「藥劑師你好，請把藥品放到我的籃子，並按下按鈕」。
第三步，讓豹小秘等待藥品裝載完成。
第四步，讓豹小秘導航回櫃台（counter）。
第五步，讓豹小秘對 user 說「幫你把藥拿來了，祝您早日康復」。
```

---

#### 範例 4：用戶說「請停止動作」

**1️⃣ 輸出給 UbiChan（虛擬人）**
```
<neutral>
<tw>
好的，我把豹小秘找回來<sbr>
請稍等一下<sbr>
```

**2️⃣ 輸出給 豹小秘（引導機器人）**

*JSON 指令：*
```json
{
  "robot": "baxiaomi",
  "action": "cancel",
  "params": {},
  "speech": "我要回去櫃台了"
}
```

*自然語言步驟描述：*
```
第一步，讓豹小秘停止當前動作。
第二步，讓豹小秘對 user 說「我要回去櫃台了」。
第三步，讓豹小秘導航回櫃台（counter）待命區。
```

---

## 第五章：技術實作

### 5.1 UbiChan Agent 流程

```python
async def handle_user_input(user_input: str, session_id: str):
    # 1. LLM 判斷意圖
    intent_result = await llm_classify_intent(user_input)
    
    # 2. 生成 UbiChan 回應（含情緒標籤、語言標籤、<sbr>）
    ubichan_response = await llm_generate_response(
        user_input=user_input,
        intent=intent_result.intent,
        context=session_context
    )
    
    # 3. 判斷是否需要豹小秘協助
    if intent_result.requires_robot:
        robot_action = generate_robot_action(intent_result)
        robot_steps = generate_natural_language_steps(robot_action)
        await send_to_robot(robot_action, robot_steps)
    
    # 4. 返回 UbiChan 回應
    return ubichan_response
```

### 5.2 豹小秘指令發送

```python
async def send_to_robot(action: dict, steps: str):
    """發送指令到豹小秘機器人"""
    response = await http_post(
        url="http://baxiaomi.local/api/v1/action",
        json=action
    )
    
    # 記錄自然語言步驟（供測試/除錯使用）
    log_robot_steps(steps)
    
    return response.status == "accepted"
```

### 5.3 狀態管理

**Session 狀態：**
```json
{
  "session_id": "med_expo_001",
  "current_location": "counter",
  "robot_status": "idle",
  "pending_action": null,
  "user_intent_history": ["registration", "pharmacy"]
}
```

**豹小秘狀態：**
```json
{
  "robot_id": "baxiaomi_01",
  "status": "idle",
  "current_location": "counter",
  "current_action": null,
  "queue": []
}
```

---

## 第六章：測試情境

### 6.1 測試案例清單

| ID | 情境 | 預期 UbiChan 回應 | 預期豹小秘動作 |
|----|------|------------------|---------------|
| T01 | 掛號 | 「好的，豹小秘會帶你去掛號處」 | 導航到櫃台 → 帶路到掛號處 |
| T02 | 拿藥 | 「你在這裡等一下，我幫你」 | 去藥局 → 取藥 → 返回櫃台 |
| T03 | 停止 | 「好的，我把豹小秘找回來」 | 取消動作 → 返回櫃台 |
| T04 | 詢問地點 | 「某地在 X 區，我請豹小秘帶你過去」 | 導航到該地點 |
| T05 | 純資訊詢問 | 直接回答問題 | 無動作 |
| T06 | 無效輸入 | 「抱歉，我不太理解您的需求」 | 無動作 |

### 6.2 邊界情況處理

| 情況 | 處理方式 |
|------|----------|
| 豹小秘忙碌中 | UbiChan：「豹小秘正在服務其他人，請稍等一下」 |
| 豹小秘離線 | UbiChan：「抱歉，引導機器人暫時無法服務，我請工作人員協助您」 |
| 來賓改變主意 | 支持 cancel 指令，豹小秘立即停止 |
| 多個來賓同時請求 | 排隊機制，豹小秘依序服務 |

---

## 📚 相關文檔

| 類別 | 文檔 | 說明 |
|------|------|------|
| **平台概述** | [00_PLATFORM_OVERVIEW.md](00_PLATFORM_OVERVIEW.md) | 平台整體設計 |
| **Virtual Human** | [01_VIRTUAL_HUMAN_DESIGN.md](01_VIRTUAL_HUMAN_DESIGN.md) | VH Agent 設計 |
| **架構** | [03_ARCHITECTURE.md](03_ARCHITECTURE.md) | 系統架構說明 |
| **Tool 規格** | [../03_specs/08_TOOL_SPEC.md](../03_specs/08_TOOL_SPEC.md) | Tool 定義規格 |
| **輸出格式** | [../03_specs/09_OUTPUT_FORMAT.md](../03_specs/09_OUTPUT_FORMAT.md) | UbiChan 輸出格式 |

---

## 📝 更新記錄

| 版本 | 日期 | 更新內容 |
|------|------|----------|
| v1.0 | 2026-05-21 | 完整規格文檔：加入輸出格式規格、自然語言步驟描述、Intent 分類強化 |

---

**🦐 醫療展專案 - UbiChan × 豹小秘 聯手服務！**
