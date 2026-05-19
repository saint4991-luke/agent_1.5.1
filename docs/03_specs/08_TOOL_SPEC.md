# 🔧 Tool 系統規格書

**版本：** v5.0  
**日期：** 2026-05-01  
**Branch:** `agent-ubichan`

---

## 🎯 文件職責

**本文檔說明：**
- Tool 系統的分層架構
- Tool 分類與配置方式
- BaseTool 介面規範
- Tool 註冊與執行流程
- 錯誤處理規範

**不包含：**
- 個別 Tool 的詳細說明（見 `/docs/04_reference/tools/`）
- 實作程式碼範例（見 Agent 實作）

---

## 1. Tool 分層架構

### 結構分離設計

```
tools/
├── __init__.py              # 匯出所有 tools
├── base.py                  # BaseTool 抽象類別
│
├── internal/                # ← Internal Tools（不開放給 persona.config）
│   └── file_system/         # 文件系統操作
│
└── public/                  # ← Public Tools（開放給 persona.config）
    ├── web_search.py        # 網路搜尋
    └── knowledge/           # 知識庫工具
```

### 配置方式矩陣

| 類型 | 路徑 | Persona Config | Agent 實作 | 說明 |
|------|------|---------------|-----------|------|
| **Internal** | `tools/internal/` | ❌ 不可配置 | ✅ 由開發者決定 | 文件系統操作（高權限） |
| **Public** | `tools/public/` | ✅ 可配置 | ✅ 由開發者決定 | 知識查詢、網路搜尋 |

**關鍵設計原則：**
- **結構分離**：透過目錄結構自然隔離配置方式
- **Internal Tools**：不開放給 `persona.config`，需要修改 Agent 程式碼才能啟用
- **Public Tools**：可通過 `persona.config` 的 `tools.available` 配置
- **VH 實作**：只 import `tools/public/` 下的 tools（硬編碼限制）
- **BO 實作**：import 所有 tools（由開發者決定啟用哪些）

---

## 2. Persona Tool 配置規範

### Config.yaml 結構

```yaml
# /workspace/personas/nurse/config.yaml
name: "護士角色"
description: "專業醫療諮詢護士"

# 可用 Tools 列表（白名單）
tools:
  # Public Tools（可配置）
  - knowledge_meta
  - knowledge_query
  - web_search

# 進階配置（可選）
tool_config:
  web_search:
    max_results: 3  # 覆蓋預設值
```

### Internal Tools 配置說明

Internal Tools **不開放給 `persona.config`** 配置，需要修改 Agent 程式碼才能啟用。

**設計原則：**
- Internal Tools 由開發者通過程式碼控制
- 平台用戶無法通過配置文件啟用 Internal Tools
- 確保高權限操作的安全性

---

## 3. BaseTool 介面規範

所有 Tool 必須繼承 `BaseTool` 抽象類別。

### 必填欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| `name` | string | Tool 唯一名稱（用於 LLM 調用） |
| `description` | string | Tool 描述（給 LLM 看，說明用途） |
| `parameters` | Dict[str, Any] | 參數定義（JSON Schema 格式） |

### 抽象方法

```python
@abstractmethod
def execute(self, **kwargs) -> Dict[str, Any]:
    """
    執行 Tool
    
    Args:
        **kwargs: Tool 參數（由 LLM 提供）
    
    Returns:
        dict: {
            "success": bool,      # 執行是否成功
            "data": Any,          # 成功時的數據
            "error": Optional[str] # 失敗時的錯誤訊息
        }
    """
    pass
```

### 可選方法

```python
def validate_params(self, **kwargs) -> bool:
    """
    驗證參數（可選覆寫）
    
    預設實作：檢查必填參數
    子類可覆寫以添加自定義驗證邏輯
    """
    required = self.parameters.get('required', [])
    for param in required:
        if param not in kwargs:
            raise ValueError(f"Missing required parameter: {param}")
    return True
```

---

## 4. Tool 註冊機制

### TOOL_INSTANCES 字典規範

在 `api.py` 中統一註冊所有 Tools：

```python
TOOL_INSTANCES = {
    "read_file": ReadFileTool(),
    "write_file": WriteFileTool(),
    "list_dir": ListDirTool(),
    "knowledge_meta": KnowledgeMetaTool(),
    "knowledge_query": KnowledgeQueryTool(),
    "web_search": WebSearchTool(),
    # ... 其他 tools
}
```

### 執行函數介面

```python
def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    執行 Tool 的統一入口
    
    Args:
        tool_name: Tool 名稱（必須在 TOOL_INSTANCES 中）
        **kwargs: Tool 參數
    
    Returns:
        dict: {"success": bool, "data": Any, "error": Optional[str]}
    """
    pass
```

---

## 5. Tool 執行流程

### 生命週期

1. **載入：** Agent 啟動時，根據 persona config 載入可用 tools
2. **註冊：** tools 註冊到 `TOOL_INSTANCES` 字典
3. **調用：** LLM 返回 tool_calls → Agent 執行對應 tool
4. **清理：** Agent 關閉時釋放資源

### 執行流程圖

```
用戶輸入
    ↓
LLM 判斷是否需要調用 tool
    ↓
返回 tool_calls (name + arguments)
    ↓
Agent 檢查權限
    ↓
執行 tool.execute(**args)
    ↓
返回結果給 LLM
    ↓
LLM 生成最終回應
```

### 詳細流程

```
┌─────────────────────────────────────────────────────────┐
│  1. LLM 輸出 Tool 調用                                   │
│     格式：{"tool": "read_file", "params": {"path": "..."}}│
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  2. 解析 LLM 輸出                                        │
│     - 提取 tool_name                                    │
│     - 提取 params                                       │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  3. 查找 TOOL_INSTANCES[tool_name]                      │
│     - 不存在 → 返回錯誤                                 │
│     - 存在 → 繼續                                      │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  4. 執行 tool.execute(**params)                         │
│     - 驗證參數（validate_params）                       │
│     - 執行邏輯                                          │
│     - 監控時長（可選：安撫語）                          │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  5. 返回結果                                            │
│     格式：{"success": bool, "data": ..., "error": ...}  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│  6. 整合到 LLM 上下文                                    │
│     - 成功：添加 Tool 結果                              │
│     - 失敗：添加錯誤訊息                                │
└─────────────────────────────────────────────────────────┘
```

---

## 6. 錯誤處理規範

### 統一錯誤格式

所有 Tool 執行失敗必須返回統一格式：

```python
{
    "success": False,
    "error": "錯誤訊息（給 LLM 看，應為自然語言）",
    "error_code": "OPTIONAL_ERROR_CODE"  # 可選
}
```

### 常見錯誤類型

| 錯誤類型 | 處理方式 | 範例 |
|----------|----------|------|
| 參數驗證失敗 | 返回錯誤，讓 LLM 修正 | "缺少必填參數：path" |
| 文件不存在 | 返回錯誤，不拋異常 | "文件未找到：/workspace/xxx.md" |
| 權限不足 | 返回錯誤 | "無權限寫入該目錄" |
| 超時 | 返回錯誤 + 重試建議 | "執行超時，請重試" |
| 未知異常 | 捕獲異常，返回錯誤訊息 | "執行失敗：{exception}" |

---

## 7. 未來擴展

### 可能的 Tools

| 類別 | Tool Name | 說明 | 配置方式 |
|------|-----------|------|----------|
| File System | `copy_file` | 複製文件 | Internal（需改 code） |
| File System | `delete_file` | 刪除文件（高風險） | Internal（需改 code） |
| Knowledge | `export_knowledge` | 匯出知識庫 | Public（可配置） |
| External | `http_request` | 發送 HTTP 請求 | Public（可配置） |
| System | `restart_agent` | 重啟 Agent | Internal（需改 code） |

---

## 📚 相關文檔

- [03_ARCHITECTURE.md](../01_designs/03_ARCHITECTURE.md) - 系統架構
- [04_PERSONA_SPEC.md](04_PERSONA_SPEC.md) - Persona 配置規格
- [03_BACKEND_OPERATOR_WORKFLOW.md](03_BACKEND_OPERATOR_WORKFLOW.md) - BO 系統說明
- [07_KNOWLEDGE_SPEC.md](07_KNOWLEDGE_SPEC.md) - Knowledge 庫規格
- [09_OUTPUT_FORMAT.md](09_OUTPUT_FORMAT.md) - 輸出格式規格
- [Tool 參考手冊](../04_reference/tools/README.md) - 個別 Tool 說明

---

**文檔結束**
