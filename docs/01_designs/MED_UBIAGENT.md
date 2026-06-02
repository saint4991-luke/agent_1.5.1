# 🏥 醫療展 Virtual Human Agent 設計 (MED_UBIAGENT)

**版本：** v1.0  
**日期：** 2026-05-21  
**Branch:** `agent-ubichan`  
**作者:** Luke Liu / 皮皮蝦 🦐

---

## 🎯 文件職責

**本文檔說明：**
- 醫療展場景的 Virtual Human Agent 設計
- UbiChan（虛擬人）與小護士（引導機器人）的協作流程
- 雙機器人架構與 LLM 驅動的情境回應
- 輸出格式規格（UbiChan 情緒標籤 + 小護士 Action JSON）

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
| **小護士** | 引導機器人 (Robot) | 展場地面 | 帶路引導、物品運送、現場互動 |

**互動流程：**
```
來賓 → 與 UbiChan 對話 → UbiChan 判斷需求 → 呼叫小護士 → 小護士執行動作
```

### 1.2 場地配置

**三個主要地點：**

```
┌─────────────────────────────────────────┐
│              醫療展展場                  │
│                                         │
│   ┌─────────┐                          │
│   │ 櫃台     │ ← UbiChan (Kiosk)        │
│   │ (接待處) │   小護士待命區            │
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
| `counter` | 櫃台 | Kiosk 前方 | UbiChan 所在位置，小護士待命區 |
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

UbiChan → 指令小護士：
{
  "action": "navigate",
  "target": "counter",
  "speech": "我帶你去掛號處，請跟我來"
}

小護士 → 移動到櫃台前方 → 播放語音

小護士 → 導航到掛號處 → 播放語音：
「掛號處到囉」
```

**LLM 設計要點：**
- UbiChan 需判斷來賓需求為「掛號」
- 觸發小護士的 `navigate` action
- 小護士需在關鍵節點播放語音

### 2.2 情境二：拿藥

**觸發條件：** 來賓表達取藥需求

**對話流程：**

```
來賓：「我看完病了，要去哪裡拿藥？」

UbiChan → LLM 判斷 → 回應：
「你在這裡等一下，我幫你。」

UbiChan → 指令小護士（先去藥局）：
{
  "action": "navigate",
  "target": "pharmacy",
  "speech": null
}

小護士 → 移動到藥局

小護士 → 對藥劑師播放語音：
「藥劑師，請幫我把藥品放到籃子裏，然後按下完成鈕」

小護士 → 等待藥品裝載完成

小護士 → 導航回櫃台 → 播放語音：
「幫你把藥拿來了，祝您早日康復」
```

**LLM 設計要點：**
- UbiChan 安撫來賓等待
- 小護士獨立完成取藥任務
- 包含與第三方（藥劑師）的互動

### 2.3 情境三：取消動作

**觸發條件：** 來賓表達停止需求

**對話流程：**

```
來賓：「請停止動作」

UbiChan → LLM 判斷 → 回應：
「好的，我把小護士找回來」

UbiChan → 指令小護士：
{
  "action": "cancel",
  "speech": "我要回去櫃台了"
}

小護士 → 停止當前動作 → 播放語音

小護士 → 導航回櫃台待命區
```

**LLM 設計要點：**
- UbiChan 需立即回應停止請求
- 小護士需中斷當前任務
- 小護士需返回待命區

### 2.4 情境四：詢問地點（隱含帶路需求）

**觸發條件：** 來賓詢問某地點在哪裡（如「掛號處在哪？」）

**設計原則：**
雖然字面上是詢問資訊，但**背後意義是希望小護士帶路**，因此應觸發導航動作。

**對話流程：**

```
來賓：「掛號處在哪？」

UbiChan → LLM 判斷 → 回應：
「掛號處在展場 A 區」
「我請小護士帶你過去」
「請跟著它走」

UbiChan → 指令小護士：
{
  "action": "navigate",
  "target": "registration",
  "speech": "掛號處在 A 區，請跟我來"
}

小護士 → 移動到櫃台前方 → 播放語音
小護士 → 導航到掛號處 → 播放語音：
「掛號處到了，祝你掛號順利」
```

**LLM 設計要點：**
- 「哪裡」類問題應解讀為**隱含的帶路需求**
- 預設觸發小護士 navigate action
- UbiChan 先回答資訊，再說明小護士會帶路

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
│  │  - 決定是否呼叫小護士                            │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────┬───────────────────────────────────┘
                      │
         ┌────────────┴────────────┐
         │                         │
         ▼                         ▼
┌─────────────────┐      ┌─────────────────────────┐
│   UbiChan 回應   │      │   小護士指令             │
│  (情緒標籤格式)  │      │  (自然語言步驟描述)      │
└─────────────────┘      └────────┬────────────────┘
                                 │
                                 ▼
                      ┌─────────────────┐
                      │    小護士 Robot  │
                      │  - 導航移動      │
                      │  - 語音播放      │
                      │  - 物品運送      │
                      │  - 動作控制      │
                      └─────────────────┘
```

### 3.2 小護士的指令格式

**輸出格式：** 使用自然語言步驟描述（Steps_Descripts）

| 欄位 | 說明 | 範例 |
|------|------|------|
| **Steps_Descripts** | 自然語言步驟描述 | `"第一步，移動到櫃台。第二步，對 user 說「你好」。"` |

**完整範例：**
```json
{
    "ToUbiChan": "<!-- emotion>happy</emotion --><!-- lang>tw (zh)</lang -->好的<sbr>我請人來帶你去<sbr>",
    "ToBaxiaomi": {
        "Steps_Descripts": "第一步，讓小護士移動到櫃台（counter）前方。第二步，讓小護士對 user 說「你好，請跟我來掛號處」。第三步，讓小護士導航到掛號處（registration）。"
    }
}
```

**支持的動作：**
- **移動/導航** - `移動到 [地點]`、`導航到 [地點]`
- **說話** - `對 [對象] 說「[語音內容]」`
- **拾取物品** - `拾取 [物品]`、`等待物品裝載`
- **取消動作** - `停止當前動作`、`返回櫃台`

### 3.3 UbiChan LLM Prompt 設計

**System Prompt：**
```
你是在醫療展服務的虛擬人 UbiChan。你的職責是：
1. 接待來賓，理解他們的需求
2. 判斷是否需要呼叫小護士機器人協助
3. 生成溫暖、專業的回應

可用地點：櫃台 (counter)、掛號處 (registration)、藥局 (pharmacy)

當來賓需要移動或取物時，請呼叫小護士協助。
當來賓詢問「某地在哪」時，也應觸發小護士帶路（隱含需求）。

回應風格：親切、專業、簡潔
輸出格式：使用情緒標籤 + 語言標籤 + <sbr> 斷句
```

### 3.4 Intent 分類（強化小護士服務）

| Intent | 關鍵字 | 動作 | 小護士介入 |
|--------|--------|------|-----------|
| `registration` | 掛號、登記、報到 | 呼叫小護士帶路到掛號處 | ✅ Steps_Descripts |
| `pharmacy` | 拿藥、取藥、藥品 | 呼叫小護士去藥局取藥 | ✅ Steps_Descripts |
| `cancel` | 停止、取消、不要了 | 呼叫小護士取消動作 | ✅ Steps_Descripts |
| `info_location` | 哪裡、怎麼走、在哪 | **主動觸發小護士帶路** | ✅ Steps_Descripts |
| `info_other` | 請問、為什麼、什麼 | 直接回答資訊 | ❌ 無動作 |
| `other` | 其他 | 禮貌回應或轉人工 | ❌ 無動作 |

**設計原則強化：**
1. **主動服務**：當用戶表達「要去某地」或「某地在哪」時，**預設觸發小護士帶路**
2. **物品運送**：當用戶需要拿取物品時，**小護士主動協助運送**
3. **安撫話語**：UbiChan 在小護士執行任務時，**安撫用戶等待**
4. **狀態回報**：小護士完成任務後，**主動回報並祝福**

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

### 4.2 小護士輸出格式（給引導機器人）

**輸出格式：** 自然語言步驟描述（Steps_Descripts）

```json
{
    "ToUbiChan": "<!-- emotion>happy</emotion --><!-- lang>tw (zh)</lang -->內容<sbr>...",
    "ToBaxiaomi": {
        "Steps_Descripts": "自然語言步驟描述"
    }
}
```

**Steps_Descripts 格式：**
```
第一步，讓小護士移動到 [地點]。
第二步，讓小護士對 [對象] 說「[語音內容]」。
第三步，讓小護士導航到 [地點]。
第四步，讓小護士對 [對象] 說「[語音內容]」。
```

**重要：** 只保留 `Steps_Descripts`，不包含 Steps JSON 結構。

### 4.3 完整輸出範例

#### 範例 1：用戶說「我想要掛號」

**1️⃣ 輸出給 UbiChan（虛擬人）**
```
<happy>
<tw>
好的，小護士會帶你去掛號處<sbr>
請跟著它走<sbr>
```

**2️⃣ 輸出給 小護士（引導機器人）**

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
第一步，讓小護士移動到櫃台（counter）前方。
第二步，讓小護士對 user 說「你好，請跟我來掛號處」。
第三步，讓小護士導航到掛號處（registration）。
第四步，讓小護士對 user 說「掛號處到了，請在這裡辦理掛號」。
```

---

#### 範例 2：用戶說「掛號處在哪？」

**1️⃣ 輸出給 UbiChan（虛擬人）**
```
<neutral>
<tw>
掛號處在展場 A 區<sbr>
我請小護士帶你過去<sbr>
請跟著它走<sbr>
```

**2️⃣ 輸出給 小護士（引導機器人）**

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
第一步，讓小護士移動到櫃台（counter）前方。
第二步，讓小護士對 user 說「掛號處在 A 區，請跟我來」。
第三步，讓小護士導航到掛號處（registration）。
第四步，讓小護士對 user 說「掛號處到了，祝你掛號順利」。
```

---

#### 範例 3：用戶說「我看完病了，要拿藥」

**1️⃣ 輸出給 UbiChan（虛擬人）**
```
<happy>
<tw>
你在這裡休息一下<sbr>
我請小護士去幫你拿藥<sbr>
很快就好<sbr>
```

**2️⃣ 輸出給 小護士（引導機器人）**

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
第一步，讓小護士移動到藥局（pharmacy）。
第二步，讓小護士對藥劑師說「藥劑師你好，請把藥品放到我的籃子，並按下按鈕」。
第三步，讓小護士等待藥品裝載完成。
第四步，讓小護士導航回櫃台（counter）。
第五步，讓小護士對 user 說「幫你把藥拿來了，祝您早日康復」。
```

---

#### 範例 4：用戶說「請停止動作」

**1️⃣ 輸出給 UbiChan（虛擬人）**
```
<neutral>
<tw>
好的，我把小護士找回來<sbr>
請稍等一下<sbr>
```

**2️⃣ 輸出給 小護士（引導機器人）**

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
第一步，讓小護士停止當前動作。
第二步，讓小護士對 user 說「我要回去櫃台了」。
第三步，讓小護士導航回櫃台（counter）待命區。
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
    
    # 3. 判斷是否需要小護士協助
    if intent_result.requires_robot:
        robot_action = generate_robot_action(intent_result)
        robot_steps = generate_natural_language_steps(robot_action)
        await send_to_robot(robot_action, robot_steps)
    
    # 4. 返回 UbiChan 回應
    return ubichan_response
```

### 5.2 小護士指令發送

```python
async def send_to_robot(action: dict, steps: str):
    """發送指令到小護士機器人"""
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

**小護士狀態：**
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

| ID | 情境 | 預期 UbiChan 回應 | 預期小護士動作 |
|----|------|------------------|---------------|
| T01 | 掛號 | 「好的，小護士會帶你去掛號處」 | 導航到櫃台 → 帶路到掛號處 |
| T02 | 拿藥 | 「你在這裡等一下，我幫你」 | 去藥局 → 取藥 → 返回櫃台 |
| T03 | 停止 | 「好的，我把小護士找回來」 | 取消動作 → 返回櫃台 |
| T04 | 詢問地點 | 「某地在 X 區，我請小護士帶你過去」 | 導航到該地點 |
| T05 | 純資訊詢問 | 直接回答問題 | 無動作 |
| T06 | 無效輸入 | 「抱歉，我不太理解您的需求」 | 無動作 |

### 6.2 邊界情況處理

| 情況 | 處理方式 |
|------|----------|
| 小護士忙碌中 | UbiChan：「小護士正在服務其他人，請稍等一下」 |
| 小護士離線 | UbiChan：「抱歉，引導機器人暫時無法服務，我請工作人員協助您」 |
| 來賓改變主意 | 支持 cancel 指令，小護士立即停止 |
| 多個來賓同時請求 | 排隊機制，小護士依序服務 |

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

**🦐 醫療展專案 - UbiChan × 小護士 聯手服務！**
