# Agent Loop 執行規格書

**版本：** v2.0  
**日期：** 2026-05-01  
**Branch:** `agent-ubichan`

---

## 🎯 文件職責

**本文檔說明：**
- Agent Loop 的執行流程
- 三類執行狀態
- Tool 結果整合到對話歷史的機制
- 執行結果結構

**不包含：**
- Prompt 結構細節（見 [19_AGENT_LOOP_PROMPT_STRUCTURE.md](19_AGENT_LOOP_PROMPT_STRUCTURE.md)）
- Agent 專屬配置（見各 Agent 規格文件）

---

## 1. 三類執行狀態

```python
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Any

class ExecutionStatus(Enum):
    """執行狀態（3 類）"""
    DONE = "done"                        # 用戶目標完成
    NEEDS_INTERACTION = "needs_input"    # 需要用戶介入（輸入、確認、選擇、授權）
    ERROR = "error"                      # 執行異常（重複 Tool、超輪數、系統錯誤）

@dataclass
class ExecutionResult:
    """執行結果"""
    
    # 核心狀態
    status: ExecutionStatus
    
    # 附加資訊
    result: Optional[Any] = None         # 結果數據
    error: Optional[str] = None          # 錯誤訊息
    warning: Optional[str] = None        # 警告訊息
    user_prompt: Optional[str] = None    # 需要用戶介入的問題
    
    # 元數據
    round_count: int = 0
    tool_results: list = None
    
    def __post_init__(self):
        if self.tool_results is None:
            self.tool_results = []
```

---

## 2. Agent Loop 流程圖

```
                              ┌─────────────┐
                              │   開始      │
                              └──────┬──────┘
                                     │
                     ┌───────────────▼───────────────┐
                     │  初始化變數                    │
                     │  - round = 0                  │
                     │  - tool_results = []          │
                     │  - last_tool_calls = []       │
                     │  - execution_result = None    │
                     └───────────────┬───────────────┘
                                     │
              ┌──────────────────────▼──────────────────────┐
              │         ⭕ while 循環條件檢查                │
              │  agent_should_continue AND round < max_rounds│
              └──────────────────────┬──────────────────────┘
                                     │ YES
                    ┌────────────────▼────────────────┐
                    │   🔄 round += 1                 │
                    └────────────────┬────────────────┘
                                     │
          ┌──────────────────────────▼──────────────────────────┐
          │   階段 1: 組合 Prompt                               │
          │   system_prompt = build_system_prompt(...)         │
          │   messages = [system, ...history, user_message]    │
          └──────────────────────────┬──────────────────────────┘
                                     │
          ┌──────────────────────────▼──────────────────────────┐
          │   階段 2: 呼叫 LLM                                  │
          │   tool_calls, llm_output = llm_provider.chat()     │
          └──────────────────────────┬──────────────────────────┘
                                     │
          ┌──────────────────────────▼──────────────────────────┐
          │   階段 3: 解析雙指標                                │
          │   agent_should_continue = parse_agent_continue()   │
          │   user_instruction_completed = parse_completed()   │
          └──────────────────────────┬──────────────────────────┘
                                     │
          ┌──────────────────────────▼──────────────────────────┐
          │   階段 4: 發送快速回應 (round==1)                   │
          │   if quick_response: yield SSE                     │
          └──────────────────────────┬──────────────────────────┘
                                     │
          ┌──────────────────────────▼──────────────────────────┐
          │   階段 5: 執行 Tools                                │
          │                                                     │
          │   if tool_calls:                                    │
          │     │                                               │
          │     │  生成簽名 (包含參數)                           │
          │     │  current_tool_calls = [...]                  │
          │     │                                               │
          │     │  ┌─────────────────────────────────────────┐ │
          │     │  │ ⚠️  檢測重複 Tool Calls                  │ │
          │     │  │ if current_tool_calls == last_tool_calls│ │
          │     │  │   → execution_result = ERROR            │ │
          │     │  │   → error = "重複 Tool 調用"              │ │
          │     │  │   → result = tool_results (已有結果)     │ │
          │     │  │   → break                               │ │
          │     │  └─────────────────────────────────────────┘ │
          │     │                                               │
          │     │  執行 Tool                                   │
          │     │  tool_results.append(result)                 │
          │     │                                               │
          │     │  ┌─────────────────────────────────────────┐ │
          │     │  │ 📝 將 Tool 結果添加到 Session History    │ │
          │     │  │ messages.append({                        │ │
          │     │  │   "role": "tool",                       │ │
          │     │  │   "content": tool_result,               │ │
          │     │  │   "name": tool_name                     │ │
          │     │  │ })                                      │ │
          │     │  └─────────────────────────────────────────┘ │
          │     │                                               │
          │     │  last_tool_calls = current_tool_calls        │
          │                                                     │
          │   else:                                             │
          │     │                                               │
          │     │  沒有 Tool 調用，準備最終回應                   │
          │     │  execution_result = DONE                     │
          │     │  result = llm_output                         │
          │     │                                               │
          └──────────────────────────┬──────────────────────────┘
                                     │
          ┌──────────────────────────▼──────────────────────────┐
          │   階段 6: 檢查循環條件                              │
          │                                                     │
          │   if agent_should_continue == NO:                   │
          │     │                                               │
          │     if user_instruction_completed == YES:           │
          │       → execution_result = DONE                     │
          │     else:                                           │
          │       → execution_result = NEEDS_INTERACTION        │
          │       → user_prompt = "需要用戶輸入"                 │
          │       → break                                       │
          │                                                     │
          └──────────────────────────┬──────────────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │   檢查輪數限制                   │
                    │   if round >= max_rounds:       │
                    │     → execution_result = ERROR  │
                    │     → error = "超過最大輪數"     │
                    └────────────────┬────────────────┘
                                     │ NO
                    ┌────────────────▼────────────────┐
                    │   發送最終回應                    │
                    │   yield SSE stream              │
                    └────────────────┬────────────────┘
                                     │
                    ┌────────────────▼────────────────┐
                    │   保存到 Session                 │
                    │   session_store.add_message()   │
                    └────────────────┬────────────────┘
                                     │
                              ┌──────▼──────┐
                              │   結束      │
                              └─────────────┘
```

---

## 3. Tool 結果整合到 Session

### 3.1 Tool 結果格式

Tool 執行結果必須遵循統一格式（見 [08_TOOL_SPEC.md](08_TOOL_SPEC.md)）：

```python
{
    "success": bool,           # 執行是否成功
    "data": Any,               # 成功時的數據
    "error": Optional[str]     # 失敗時的錯誤訊息
}
```

### 3.2 Session 訊息結構

每條 Session 訊息包含：

```python
{
    "role": str,               # "user" / "assistant" / "tool"
    "content": str,            # 訊息內容
    "timestamp": str,          # ISO 8601 時間戳
    "metadata": {              # 可選元數據
        "tool_name": str,      # Tool 名稱（當 role="tool" 時）
        "tool_result": dict    # Tool 執行結果（當 role="tool" 時）
    }
}
```

### 3.3 Agent Loop 整合邏輯

每輪循環中，Tool 結果按以下順序整合：

```python
# 1. 執行 Tool
tool_result = execute_tool(tool_name, **tool_args)

# 2. 將 Tool 結果添加到 messages（作為下一輪的 context）
messages.append({
    "role": "tool",
    "name": tool_name,
    "content": json.dumps(tool_result, ensure_ascii=False)
})

# 3. 同時保存到 Session Store（持久化）
session_store.add_message(
    session_id=session_id,
    role="tool",
    content=json.dumps(tool_result),
    metadata={
        "tool_name": tool_name,
        "tool_result": tool_result
    }
)

# 4. 下一輪 LLM 呼叫時，Tool 結果會自動包含在 messages 中
response = llm_provider.chat(messages=messages)
```

### 3.4 關鍵設計原則

| 原則 | 說明 |
|------|------|
| **即時整合** | Tool 執行後立即添加到 messages，不等待最終回應 |
| **雙重存儲** | 同時添加到 messages（臨時）和 Session Store（持久化） |
| **role 標記** | 使用 `role: "tool"` 標記 Tool 結果，區別於 user/assistant |
| **可追溯** | metadata 中包含完整 Tool 執行結果，便於調試 |

---

## 4. 執行結果結構

### 4.1 成功完成（DONE）

```python
ExecutionResult(
    status=ExecutionStatus.DONE,
    result={
        "response": "最終回應內容",
        "tool_results": [...],  # 所有執行的 Tool 結果
        "round_count": 3
    },
    round_count=3,
    tool_results=[...]
)
```

### 4.2 需要用戶介入（NEEDS_INTERACTION）

```python
ExecutionResult(
    status=ExecutionStatus.NEEDS_INTERACTION,
    result=None,
    user_prompt="請提供更多資訊：...",
    round_count=2,
    tool_results=[...]
)
```

### 4.3 執行錯誤（ERROR）

```python
ExecutionResult(
    status=ExecutionStatus.ERROR,
    result=None,
    error="重複 Tool 調用",
    round_count=5,
    tool_results=[...]
)
```

---

## 5. 循環控制

### 5.1 繼續循環條件

```python
while agent_should_continue and round < max_rounds:
    # 繼續執行
```

### 5.2 停止循環條件

| 條件 | 說明 | 狀態 |
|------|------|------|
| `agent_should_continue == NO` | Agent 沒有下一步行動 | DONE 或 NEEDS_INTERACTION |
| `round >= max_rounds` | 超過最大輪數（預設 10） | ERROR |
| 重複 Tool 調用 | 檢測到相同的 Tool Calls | ERROR |

### 5.3 最大輪數

```python
MAX_ROUNDS = 10  # 預設最大輪數
```

---

## 6. 快速回應（第 1 輪）

### 6.1 快速回應格式

```
快速回應：[一句話，不超過 {max_length} 字]
```

### 6.2 參數配置

| Agent | 配置來源 | 預設值 |
|-------|----------|--------|
| VH Agent | `persona.config` → `quick_response.max_length` | 20 |
| BO Agent | 固定值 | 20 |

### 6.3 發送時機

```python
if round == 1 and quick_response:
    yield SSE(quick_response)  # 立即發送，不等待 Tool 執行
```

---

## 📚 相關文檔

- [08_TOOL_SPEC.md](08_TOOL_SPEC.md) - Tool 系統規格（Tool 結果格式）
- [14_AGENT_LOOP_PROMPT_STRUCTURE.md](14_AGENT_LOOP_PROMPT_STRUCTURE.md) - Prompt 結構規格
- [06_SESSION_SDK_SPEC.md](06_SESSION_SDK_SPEC.md) - Session SDK 規格（存儲細節）
- [03_BACKEND_OPERATOR_WORKFLOW.md](03_BACKEND_OPERATOR_WORKFLOW.md) - BO Agent 規格

---

**文檔結束**
