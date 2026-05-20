# 🏥 醫療展 Virtual Human Agent 設計 (MED_UBIAGENT)

**版本：** v1.0  
**日期：** 2026-05-19  
**Branch:** `agent-ubichan`

---

## 🎯 文件職責

**本文檔說明：**
- 醫療展場景的 Virtual Human Agent 設計
- UbiChan（虛擬人）與豹小秘（引導機器人）的協作流程
- 雙機器人架構與 LLM 驅動的情境回應

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
│  (文字/語音)     │      │  (JSON Action)  │
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
當來賓只是想詢問資訊時，直接回答即可。

回應風格：親切、專業、簡潔
```

**Intent 分類：**
| Intent | 關鍵字 | 動作 |
|--------|--------|------|
| `registration` | 掛號、登記、報到 | 呼叫豹小秘帶路到掛號處 |
| `pharmacy` | 拿藥、取藥、藥品 | 呼叫豹小秘去藥局取藥 |
| `cancel` | 停止、取消、不要了 | 呼叫豹小秘取消動作 |
| `info` | 請問、哪裡、怎麼 | 直接回答資訊 |
| `other` | 其他 | 禮貌回應或轉人工 |

### 3.4 豹小秘 Action 格式

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

## 第四章：技術實作

### 4.1 UbiChan Agent 流程

```python
async def handle_user_input(user_input: str, session_id: str):
    # 1. LLM 判斷意圖
    intent_result = await llm_classify_intent(user_input)
    
    # 2. 生成 UbiChan 回應
    ubichan_response = await llm_generate_response(
        user_input=user_input,
        intent=intent_result.intent,
        context=session_context
    )
    
    # 3. 判斷是否需要豹小秘協助
    if intent_result.requires_robot:
        robot_action = generate_robot_action(intent_result)
        await send_to_robot(robot_action)
    
    # 4. 返回 UbiChan 回應
    return ubichan_response
```

### 4.2 豹小秘指令發送

```python
async def send_to_robot(action: dict):
    """發送指令到豹小秘機器人"""
    response = await http_post(
        url="http://baxiaomi.local/api/v1/action",
        json=action
    )
    return response.status == "accepted"
```

### 4.3 狀態管理

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

## 第五章：測試情境

### 5.1 測試案例清單

| ID | 情境 | 預期 UbiChan 回應 | 預期豹小秘動作 |
|----|------|------------------|---------------|
| T01 | 掛號 | 「好的，我請人來帶你去掛號處」 | 導航到櫃台 → 帶路到掛號處 |
| T02 | 拿藥 | 「你在這裡等一下，我幫你」 | 去藥局 → 取藥 → 返回櫃台 |
| T03 | 停止 | 「好的，我把豹小秘找回來」 | 取消動作 → 返回櫃台 |
| T04 | 詢問資訊 | 直接回答問題 | 無動作 |
| T05 | 無效輸入 | 「抱歉，我不太理解您的需求」 | 無動作 |

### 5.2 邊界情況處理

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

---

**🦐 醫療展專案 - UbiChan × 豹小秘 聯手服務！**
