# Backend Operator 工作流程規格書

**版本：** v2.0  
**日期：** 2026-05-01  
**Branch:** `agent-ubichan`

---

## 🎯 文件職責

**本文檔說明：**
- Backend Operator 的核心定位與架構
- BO 專屬的 Tool 配置
- BO 專屬的 Prompt 規則（虛擬人與知識庫處理）
- API 端點定義

**引用通用規格：**
- Agent Loop 執行流程：[13_AGENT_LOOP_SPEC.md](13_AGENT_LOOP_SPEC.md)
- Prompt 結構：[14_AGENT_LOOP_PROMPT_STRUCTURE.md](14_AGENT_LOOP_PROMPT_STRUCTURE.md)

---

## 1. 核心定位

> **我們不是在做「通用 Agent Runtime」**
> **我們在做「RAG + Tool-based Assistant Runtime」**

### 1.1 場景本質

| 項目 | 通用 Agent | 我們的場景 |
|------|------------|------------|
| **主要用途** | 自主任務規劃、複雜 workflow | RAG 查詢、客服問答、虛擬人對話 |
| **Tool 類型** | Code execution、scientific workflow | 資料 retrieval / transformation |
| **執行流程** | 多步驟依賴、DAG 調度 | 線性對話流（查 → 補 → 回答） |
| **規劃需求** | 複雜 planning graph | 簡單的 intent + query 生成 |
| **並行需求** | 必要 | ❌ 幾乎不需要 |
| **Response 品質** | 次要 | ⭐ 核心（客服/虛擬人語氣） |

### 1.2 系統本質

> **Tool-augmented RAG Assistant**

### 1.3 架構選擇

採用 **簡化 3 層架構**：

1. **Layer 1: Intent + Routing (LLM)** - 判斷 intent + 生成 query
2. **Layer 2: Tool Runtime (Executor)** - RAG / API / DB 查詢
3. **Layer 3: Response (LLM)** - 自然語言回應（語氣控制 + hallucination 避免）

---

## 2. Agent Loop 架構

### 2.1 採用 Agent Loop 結構

BO 採用 **Agent Loop** 執行模式，詳細規格見：

- **執行流程：** [18_AGENT_LOOP_SPEC.md](18_AGENT_LOOP_SPEC.md)
- **Prompt 結構：** [19_AGENT_LOOP_PROMPT_STRUCTURE.md](19_AGENT_LOOP_PROMPT_STRUCTURE.md)

### 2.2 BO 實作位置

```
agent/backend_operator/api.py
├── /chat 端點
└── generate_stream() - 實作 Agent Loop
```

### 2.3 Agent Loop 配置

| 參數 | BO 配置值 | 說明 |
|------|----------|------|
| `max_rounds` | 10 | 最大執行輪數 |
| `quick_response.max_length` | 20 | 快速回應最大字數 |
| 執行狀態 | DONE, NEEDS_INTERACTION, ERROR | 三類狀態（見 18 號文件） |

---

## 3. BO 專屬 Tool 配置

### 3.1 啟用的 Tools

BO 啟用以下 Tools（由開發者實作決定）：

**Internal Tools（需改 code 啟用）**
- `list_dir` - 列出目錄
- `read_file` - 讀取文件
- `write_file` - 寫入文件
- `read_excel` - 讀取 Excel
- `read_csv` - 讀取 CSV
- `read_word` - 讀取 Word
- `read_pdf` - 讀取 PDF

**Public Tools（可配置）**
- `knowledge_meta` - 查詢知識庫 meta
- `knowledge_query` - 查詢知識庫內容
- `rebuild_knowledge_meta` - 重建知識庫 meta
- `web_search` - 網路搜尋

### 3.2 Tool 初始化

```python
# agent/backend_operator/api.py

from tools.internal.file_system import (
    ListDirTool, ReadFileTool, WriteFileTool,
    ReadExcelTool, ReadCsvTool, ReadWordTool, ReadPdfTool
)
from tools.public.knowledge import (
    KnowledgeMetaTool, KnowledgeQueryTool, MetaGeneratorTool
)
from tools.public import WebSearchTool

# 實例化所有 Tools
TOOL_INSTANCES = {
    # Internal
    'list_dir': ListDirTool(workspace_path="/workspace"),
    'read_file': ReadFileTool(workspace_path="/workspace"),
    'write_file': WriteFileTool(workspace_path="/workspace"),
    'read_excel': ReadExcelTool(workspace_path="/workspace"),
    'read_csv': ReadCsvTool(workspace_path="/workspace"),
    'read_word': ReadWordTool(workspace_path="/workspace"),
    'read_pdf': ReadPdfTool(workspace_path="/workspace"),
    
    # Public
    'knowledge_meta': KnowledgeMetaTool(knowledge_base_path="/knowledge"),
    'knowledge_query': KnowledgeQueryTool(knowledge_base_path="/knowledge"),
    'rebuild_knowledge_meta': MetaGeneratorTool(knowledge_base_path="/knowledge"),
    'web_search': WebSearchTool(max_results=5),
}
```

### 3.3 Tool 執行

Tool 執行邏輯遵循 [08_TOOL_SPEC.md](08_TOOL_SPEC.md) 的規範：

```python
def execute_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """執行 Tool 的統一入口"""
    if tool_name not in TOOL_INSTANCES:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    tool = TOOL_INSTANCES[tool_name]
    return tool.execute(**kwargs)
```

---

## 4. BO 專屬 Prompt 規則

### 4.1 Prompt 結構

BO 的 Prompt 採用 **4 段式結構**（見 [19_AGENT_LOOP_PROMPT_STRUCTURE.md](19_AGENT_LOOP_PROMPT_STRUCTURE.md)）：

```markdown
# 1. 基本人設與職責

# 2. 通用 AGENT LOOP 與工具使用原則

# 3. BO 專屬背景知識（虛擬人與知識庫）

# 4. BO 專屬流程（虛擬人建立）
```

### 4.2 BO 專屬背景知識

#### 虛擬人設定（Personas）

```markdown
## 虛擬人設定

**位置：** `/workspace/personas/{{角色名}}/`

| 檔案 | 用途 | 參考範本 |
|------|------|----------|
| `style.md` | 角色風格（身份、性格、說話方式、回覆規則） | `TEMPLATE/style.md` |
| `config.yaml` | 技術配置（LLM Provider、Tools、知識庫） | `TEMPLATE/config.yaml` |

**config.yaml 基本結構：**
```yaml
persona_id: ubichan
output_format: virtual_human
knowledge:
  enabled: true
  folders: ['ubitus/']
```
```

#### 知識庫（Knowledge）

```markdown
## 知識庫

**位置：** `/workspace/knowledge/{{知識庫 ID}}/`

| 檔案 | 用途 | 說明 |
|------|------|------|
| `*.txt` / `*.md` | 知識內容文件 | 實際的知識內容 |
| `meta.json` | 自動生成的索引 | 用於 RAG 檢索 |

**生成索引命令：**
```bash
python -m agent.rag.meta_generator knowledge/{{id}}
```
```

#### 範本目錄

```markdown
## 範本目錄

**位置：** `/workspace/personas/TEMPLATE/`
- 新角色建立的參考範本
- 包含 `style.md` 和 `config.yaml` 標準格式
```

### 4.3 BO 專屬流程：虛擬人建立

```markdown
## 虛擬人建立流程（僅在創建虛擬人時適用）

### 核心認知
- 建立虛擬人 = 兩個文件（`config.yaml` + `style.md`）
- 範本固定路徑：`personas/TEMPLATE/`
- 第 1 次讀取範本後，在回應中列出範本結構摘要（進入對話歷史），後續輪次可直接引用

### 工作流程（三個階段）

**階段 1：初始化**
1. 讀取範本（`personas/TEMPLATE/config.yaml` 和 `personas/TEMPLATE/style.md`）
2. 在回應中列出範本結構摘要（讓下一輪 AGENT 可從對話歷史獲取）
3. 創建目錄（`personas/{{角色名}}/`）
4. 創建基礎檔案結構
5. 說開場白

**階段 2：詢問四個問題（原則上按順序 1→2→3→4）**

每個問題的流程：
- 檢查用戶是否已提供該問題的資訊
- 如果已提供 → 直接記錄，跳過詢問
- 如果未提供 → 詢問問題
- 獲得答案
- 立即寫入檔案
- 進度回報

| 問題 | 內容 |
|------|------|
| 1. 基礎身份 | 名字、身份、服務對象 |
| 2. 個性與風格 | 性格關鍵詞、說話風格、口頭禪、表情符號 |
| 3. 能力與權限 | 先問 TOOLS，接著問知識庫 (KNOWLEDGE) 範圍 |
| 4. 回覆規則 | AGENT 生成實際內容讓用戶確認（保持人設、話題範圍、安全準則、未知問題） |

**階段 3：完成**
- 詢問有沒有要補充
- 確認完成

### 標準用語

**開場白（階段 1 完成後）**
```
好的！已經為 {{角色名}} 建立基礎設定。

接下來有四個問題需要你回答，我們會一個一個確認。

第一個問題：請問 {{角色名}} 是什麼樣的性格？
（例如：活潑、專業、親切、有點傲嬌...）
```

**進度回報（每個問題完成後）**
```
收到！已更新 {{角色名}} 的 [已完成項目]。

下一個要跟你確認的是 [下一個項目]：
[具體問題]
```

**完成（階段 2 完成後）**
```
所有預設問題都拿到答案了，有沒有什麼要補充？

如果沒有的話，{{角色名}} 的設定就完成了！
```

### 重要提醒
- 開場白說明有四個問題
- 原則上按順序詢問（1→2→3→4）
- 使用進度回報用語
- 每個狀態講清楚
- 用戶不必理解檔案結構，只要知道資訊都有被設定到了
- 範本結構摘要要在第 1 輪回應中呈現（進入對話歷史）
```

### 4.4 回應格式要求

**語言匹配：**
- 用戶用繁體中文問 → 用繁體中文回
- 用戶用英文問 → 用英文回
- 中英夾雜 → 判斷主要語言

**最終回應格式：**
```
[基於 Tool 執行結果的自然語言回應]

---
**執行摘要：**
- 已執行：XXX Tool
- 獲取：XXX 資訊
- 狀態：完成/需要確認
```

---

## 5. API 端點

### 5.1 POST /chat

**描述：** 聊天端點（支援 STREAM 模式）

**請求：**
```json
{
  "messages": [
    {"role": "user", "content": "幫我掃描 workspace"}
  ],
  "session_id": "abc123"
}
```

**回應：** SSE Stream

### 5.2 Session 管理端點

| 端點 | 方法 | 說明 |
|------|------|------|
| `/sessions` | GET | 列出 Sessions |
| `/sessions` | POST | 創建 Session |
| `/sessions/{id}` | GET | 獲取 Session |
| `/sessions/{id}` | DELETE | 刪除 Session |

詳細規格見 [05_SESSION_API_SPEC.md](05_SESSION_API_SPEC.md)。

---

## 6. 數據模型

### 6.1 ChatRequest

```python
class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    session_id: Optional[str]
```

### 6.2 ExecutionResult

遵循 [18_AGENT_LOOP_SPEC.md](18_AGENT_LOOP_SPEC.md) 的定義：

```python
class ExecutionResult(BaseModel):
    status: ExecutionStatus  # DONE, NEEDS_INTERACTION, ERROR
    result: Optional[Any]
    error: Optional[str]
    user_prompt: Optional[str]
    round_count: int
    tool_results: List[Dict]
```

---

## 7. 錯誤處理

### 7.1 錯誤分類

| 錯誤類型 | 處理方式 | 回應範例 |
|----------|----------|----------|
| Tool 不存在 | 返回錯誤，讓 LLM 修正 | "找不到該工具" |
| 文件未找到 | 返回錯誤 | "文件不存在：{path}" |
| 權限不足 | 返回錯誤 | "無權限操作該目錄" |
| 超時 | 返回錯誤 + 重試建議 | "執行超時，請重試" |

### 7.2 Session 錯誤處理

Session 操作失敗不阻斷主流程：

```python
try:
    session_store.add_message(session_id, "assistant", response)
except Exception as e:
    print(f"⚠️ 保存 Session 失敗：{e}")
    # 繼續執行
```

---

## 8. 性能配置

### 8.1 環境變數

| 變數 | 說明 | 預設值 |
|------|------|--------|
| `LLM_API_KEY` | LLM API 金鑰 | - |
| `LLM_BASE_URL` | LLM API 基礎 URL | - |
| `LLM_MODEL` | LLM 模型名稱 | `Qwen/Qwen3.5-397B-A17B-FP8` |
| `WORKSPACE` | 工作區路徑 | `/workspace` |
| `KNOWLEDGE_BASE` | 知識庫路徑 | `/knowledge` |

### 8.2 常數定義

```python
MAX_ROUNDS = 10                    # 最大執行輪數
MAX_HISTORY_MESSAGES = 10          # 對話歷史限制
QUICK_RESPONSE_MAX_LENGTH = 20     # 快速回應最大字數
```

---

## 📚 相關文檔

- [08_TOOL_SPEC.md](08_TOOL_SPEC.md) - Tool 系統規格
- [18_AGENT_LOOP_SPEC.md](18_AGENT_LOOP_SPEC.md) - Agent Loop 執行流程
- [19_AGENT_LOOP_PROMPT_STRUCTURE.md](19_AGENT_LOOP_PROMPT_STRUCTURE.md) - Prompt 結構
- [05_SESSION_API_SPEC.md](05_SESSION_API_SPEC.md) - Session API 規格
- [07_KNOWLEDGE_SPEC.md](07_KNOWLEDGE_SPEC.md) - Knowledge 庫規格

---

**文檔結束**
