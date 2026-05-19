# 🏗️ AgentShrimp 系統架構

**版本：** v2.0  
**最後更新：** 2026-04-30  
**適用對象：** 開發者、系統架構師

**架構核心：** 一個平台、兩個 Agent（VH + BO）

---

## 🎯 文件職責

**本文檔說明：**
- AgentShrimp 平台的整體系統架構
- 平台共享模組（SESSION、PERSONA、KNOWLEDGE、TOOL）
- 兩個 Agent 的設計與差異（VH vs BO）
- 模組間的關係與數據流
- 技術選型與設計決策

**本文檔不包含：**
- API 格式規格（→ `03_specs/`）
- 配置說明（→ `02_guides/`）
- VH 專屬設計（→ `01_VIRTUAL_HUMAN_DESIGN.md`）
- BO 專屬設計（→ `02_BACKEND_OPERATOR_DESIGN.md`）

---

## 1. 系統概覽

### 平台 + 雙 Agent 架構

```
┌─────────────────────────────────────────────────────────┐
│                  AgentShrimp 平台                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  共享模組層（平台層）                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ SESSION  │  │ PERSONA  │  │KNOWLEDGE │  │  TOOL  │ │
│  │  Layer   │  │  Layer   │  │  Layer   │  │ Layer  │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
│       ▲              ▲              ▲             ▲     │
│       │              │              │             │     │
│       └──────────────┴──────────────┴─────────────┘     │
│                          │                               │
│                          ▼                               │
│  ┌───────────────────────────────────────────────────┐ │
│  │              LLM Provider 層                       │ │
│  │          (openai / ubisage)                       │ │
│  └───────────────────────────────────────────────────┘ │
│                                                          │
├─────────────────────────────────────────────────────────┤
│  Agent 層（使用者）                                        │
│                                                          │
│  ┌─────────────────────────┐   ┌─────────────────────┐ │
│  │  Virtual Human (VH)     │   │ Backend Operator    │ │
│  │  - 對話、情感、陪伴      │   │  (BO)               │ │
│  │  - LLM1/LLM2 雙階段      │   │  - 後台管理          │ │
│  │  - SSE 串流輸出          │   │  - Agent Loop 多輪   │ │
│  │  - 前端：HTML/JS        │   │  - 前端：API-only   │ │
│  │  - 目錄：virtual_human/ │   │  - 目錄：backend_   │ │
│  │                         │   │            operator/│ │
│  └─────────────────────────┘   └─────────────────────┘ │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**核心概念：**
- **平台層**：提供共享模組（SESSION、PERSONA、KNOWLEDGE、TOOL）
- **Agent 層**：VH 和 BO 使用平台模組完成各自職責
- **PERSONA**：VH 專屬（BO 不需要角色設定）
- **TOOL**：分為 PUBLIC（Persona 可配置）和 INTERNAL（Agent 直接調用）

---

## 2. 模組詳細說明

### 2.1 平台共享模組

---

### 2.1.1 Session 層 (session/)

**職責：** 對話歷史管理、持久化存儲、HTTP API

**歸屬：** 共享（VH + BO 共用）

**核心文件：**
```
session/
├── __init__.py              # 模組導出
├── session_store.py         # SQLite 存儲層（主版本）
├── session_api.py           # FastAPI Router
├── session_manager_backup.py # In-Memory 版本（備份）
└── tools/
    └── query_session.py     # Session 查詢工具
```

**功能：**
- Session 創建/刪除/查詢
- 訊息添加（含 emotion、lang 標籤）
- TTL 自動清理
- HTTP API 接口

**API 端點：**
```
POST   /sessions          # 創建 Session
GET    /sessions          # 列出 Sessions
GET    /sessions/{id}     # 獲取 Session
DELETE /sessions/{id}     # 刪除 Session
```

---

### 2.1.2 KNOWLEDGE 層 (workspace/knowledge/)

**職責：** 領域知識存儲、RAG 檢索來源

**歸屬：** 共享（VH + BO 共用）

**結構：**
```
/workspace/knowledge/
└── {knowledge_id}/
    ├── meta.json           # 【自動生成】文件索引
    ├── file1.txt           # 知識內容
    ├── file2.md
    └── ...
```

**Meta 格式：**
```json
{
  "version": "1.0",
  "generated_at": "2026-04-16",
  "knowledge_id": "ubitus",
  "files": [
    {
      "name": "company.txt",
      "summary": "公司介紹...",
      "keywords": ["公司", "優必達"],
      "size_bytes": 686,
      "line_count": 25
    }
  ]
}
```

**生成工具：**
```bash
python -m agent.rag.meta_generator workspace/knowledge/ubitus
```

---

### 2.1.3 TOOL 層 (tools/)

**職責：** 擴展能力，支持外部 API 調用與功能擴展

**歸屬：** 共享（VH + BO 共用）

**Tool 分類：**

| 類型 | 目錄 | 配置方式 | 使用場景 |
|------|------|----------|----------|
| **PUBLIC** | `tools/public/` | `config.yaml` 的 `tools.available` | 知識庫管理、網路搜尋等 |
| **INTERNAL** | `tools/internal/` | 不開放配置，需修改 Agent 程式碼 | 文件操作、系統級功能 |

**目錄結構：**
```
tools/
├── __init__.py              # 模組導出
├── base.py                  # Tool 基類
├── public/                  # PUBLIC Tools（可配置）
│   ├── __init__.py
│   ├── web_search_tool.py  # 網路搜尋
│   └── knowledge/          # 知識庫相關
│       ├── meta_tool.py
│       └── query_tool.py
└── internal/                # INTERNAL Tools（需改 code）
    ├── __init__.py
    └── file_system/        # 文件操作
        ├── read_file_tool.py
        ├── write_file_tool.py
        ├── list_dir_tool.py
        ├── read_pdf_tool.py
        ├── read_word_tool.py
        └── read_csv_tool.py
```

**PUBLIC Tool - Persona 授權：**
```yaml
tools:
  enabled: true
  available:
    - knowledge_meta
    - knowledge_query
    - web_search
```

**INTERNAL Tool - 使用方式：**
```python
# 在 Agent Workflow 中直接調用（由開發者決定）
from tools.internal.file_system import read_file_tool

result = await read_file_tool.execute(path="config.yaml")
```

**設計原則：**
- PUBLIC Tools：平台用戶可通過 `persona.config` 配置
- INTERNAL Tools：不開放給配置文件，需修改 Agent 程式碼才能啟用
- VH 實作：硬編碼限制，只使用 PUBLIC Tools
- BO 實作：由開發者決定啟用哪些 Tools（INTERNAL + PUBLIC）

---

### 2.1.4 LLM Provider 層

**職責：** 統一 LLM 接口、多 Provider 支援

**歸屬：** 共享（VH + BO 共用）

**核心文件：**
```
agent/
├── llm_providers.py       # LLM Provider 接口
└── llm_factory.py         # Provider 工廠
```

**支援 Provider：**
| Provider | 說明 | 配置方式 |
|----------|------|----------|
| **openai** | OpenAI 兼容接口 | `OPENAI_BASE_URL`, `OPENAI_API_KEY` |
| **ubisage** | Ubisage 專屬接口 | `UBISAGE_API_KEY`, `UBISAGE_GRANT_URL` |

**常見部署配置：**
- UBITES DIRECT (VLLM) - 通過 `openai` Provider
- QWEN (VLLM) - 通過 `openai` Provider
- UBISAGE - 通過 `ubisage` Provider

**接口方法：**
```python
chat(messages)              # 非流式
chat_stream(messages)       # 流式
```

---

### 2.1.5 PERSONA 層 (workspace/personas/)

**職責：** 角色設定與資源管理

**歸屬：** VH 專屬（BO 不需要）

**核心結構：**
```
workspace/personas/{persona_id}/
├── style.md           # 角色風格定義
└── config.yaml        # 資源配置
```

**核心功能：**

#### 角色設定（style.md）
- 定義角色個性
- 定義說話風格
- 定義口頭禪與用詞習慣

#### 資源配置（config.yaml）
```yaml
persona_id: ubichan
display_name: 優必醬

style:
  file: style.md

output_format: virtual_human

knowledge:
  enabled: true
  folders:
    - ubitus/

tools:
  enabled: false
  available: []
```

#### 知識庫授權
- `knowledge.folders` 指定可訪問的知識庫
- 支援多知識庫關聯
- 一對多、多對一關係

#### Tool 授權
- `tools.available` 指定可用工具
- 保留擴充（未來功能）

#### 輸出格式
- `output_format` 選擇輸出規格
- `virtual_human`：情緒標籤 + 語言標籤 + 斷句
- `chat`：純文字回應

---

### 2.2 Agent 層（雙 Agent 架構）

---

### 2.2.1 Virtual Human Agent

**職責：** 對話、情感、陪伴

**歸屬：** VH 專屬

**核心文件：**
```
agent/virtual_human/
├── api.py               # /vh/chat 端點
├── config_loader.py     # YAML 配置載入
├── spec_loader.py       # 輸出規格載入
└── specs/
    └── virtual-human-output-spec.md
```

**Workflow 特點：**

#### LLM1/LLM2 雙階段流程
- **階段 1：** 讀取 meta.json，LLM1 判斷相關文件
- **階段 2：** 載入相關文件完整內容
- **優勢：** 節省 Token、語意理解

#### 快速回應（LLM1 STREAM 模式）
- **目標：** <1 秒內返回第一句話
- **限制：** <20 字，一句話
- **用途：** 安撫用戶、快速反饋
- **實現：** `chat_stream()` + 早期截斷

#### 風格導入
- 從 Persona 層載入風格配置
- 應用於 `/vh/chat` 端點
- 透過 `_build_prompt()` 組建

#### Tool 使用
- **目前：** `/vh/chat` 端點支援 Tool
- **類型：** 知識庫管理、外部 API 等

---

### 2.2.2 Backend Operator Agent

**職責：** 後台管理、知識庫維護、配置修改

**歸屬：** BO 專屬

**核心文件：**
```
agent/backend_operator/
└── api.py               # /chat 端點（管理用）
```

**Workflow 特點：**

#### Agent Loop 多輪執行
- 支持最多 10 輪循環
- 每輪判斷是否繼續執行
- 實時回報執行狀態

#### 雙指標決策系統
- **指標 1：** AGENT 還要繼續（YES/NO）
- **指標 2：** 用戶指令完成（YES/NO）

#### 三類執行狀態
- **DONE：** 用戶目標完成
- **NEEDS_INTERACTION：** 需要用戶介入
- **ERROR：** 執行異常

#### Tool 使用
- **11 個 Tool：** 文件操作、知識庫、網路搜尋
- **主動調用：** 當用戶問題涉及文件操作時
- **不重複執行：** 已成功執行的 Tool 不重複調用

---

### 2.3 前端層

---

### 2.3.1 前端層 (frontend/)

**職責：** 用戶界面、SSE 串流接收、會話管理（簡單驗證用）

**歸屬：** VH + BO（兩個頁面）

**核心文件：**
```
frontend/
├── templates/
│   ├── index.html     # 首頁
│   ├── chat.html      # BO 對話頁面（一般對話）
│   └── vh-chat.html   # VH 對話頁面（虛擬人）
└── static/
    └── js/
        ├── chat.js    # BO 對話邏輯
        └── vh-chat.js # VH 對話邏輯
```

**功能：**
- 用戶輸入與訊息顯示
- SSE 串流接收與渲染
- Session 創建/刪除/切換
- 虛擬人風格選擇（VH 專屬）

**技術棧：**
- 純 HTML + JavaScript（無框架）
- EventSource API（SSE）
- Fetch API（HTTP 請求）

**存儲：**
- **主版本：** SQLite（持久化）
- **備份：** In-Memory（參考用）

**API 端點：**
```
POST   /sessions          # 創建 Session
GET    /sessions          # 列出 Sessions
GET    /sessions/{id}     # 獲取 Session
DELETE /sessions/{id}     # 刪除 Session
```

---

## 4. 數據流

### 4.1 VH 對話流程（/vh/chat）

```
1. 用戶輸入
   │
   ▼
2. 前端 → Agent API (POST /vh/chat)
   │
   ▼
3. Agent → Session 獲取對話歷史
   │
   ▼
4. Agent → Persona 載入配置
   │
   ├── style.md（風格）
   ├── output_format（輸出格式）
   └── knowledge.folders（授權）
   │
   ▼
5. Agent → 知識庫 meta.json 檢索
   │
   ▼
6. Agent → 組建 Prompt（5 部分）
   │
   ├── System Prompt
   ├── Style Prompt
   ├── Output Spec
   ├── Knowledge
   └── Conversation History
   │
   ▼
7. LLM1 → 快速回應（STREAM, <20 字）
   │
   ▼
8. Agent → 前端 SSE 發送
   │
   ├── stream_start
   ├── stream_token (×N)
   ├── stream_end
   └── session_updated
   │
   ▼
9. Agent → Session 存儲訊息
   │
   ▼
10. LLM2 → 完整回應（背景）
   │
   ▼
11. Agent → Session 存儲完整回應
```

---

### 4.2 BO 管理流程（/chat）

```
1. 用戶輸入（管理指令）
   │
   ▼
2. 前端/API → BO Agent API (POST /chat)
   │
   ▼
3. Agent → Session 獲取對話歷史
   │
   ▼
4. Agent → Agent Loop 第 1 輪
   │
   ├── 解析用戶指令
   ├── 判斷需要執行的 Tool
   ├── 調用 Tool（如：list_dir）
   └── 判斷是否繼續
   │
   ▼
5. Agent Loop 第 2 輪（如需要）
   │
   ├── 基於 Round 1 結果繼續
   ├── 執行下一個 Tool
   └── 判斷是否完成
   │
   ▼
6. 生成最終回應
   │
   ├── 整合所有執行結果
   └── 返回完整報告
   │
   ▼
7. Agent → Session 存儲訊息
   │
   ▼
8. Agent → 前端/API 回應
```

**關鍵差異：**
- **VH：** LLM1/LLM2 雙階段，快速回應 + 完整回應
- **BO：** Agent Loop 多輪執行，直到任務完成

---

### 4.3 RAG 檢索流程（共享）

```
1. 用戶問題
   │
   ▼
2. 讀取 meta.json（所有知識庫）
   │
   ▼
3. LLM1 判斷相關文件
   │
   ▼
4. 載入相關文件完整內容
   │
   ▼
5. 組建 Prompt（含知識）
   │
   ▼
6. LLM 基於知識庫回答
```

**使用場景：**
- VH：用戶詢問專業知識
- BO：管理員查詢知識庫狀態

---

### 4.4 Session 管理流程（共享）

```
1. 創建 Session
   │
   ├── 生成 Session ID ({PREFIX}_{uuid})
   ├── 存入 SQLite (sessions.db)
   └── 返回 {session_id, metadata}
   │
2. 添加訊息
   │
   ├── 寫入 messages 表
   ├── 包含 emotion、lang 標籤
   └── 更新 last_active
   │
3. 獲取歷史
   │
   ├── 查詢 messages 表
   ├── 限制最近 N 條
   └── 返回 List[Dict]
   │
4. TTL 清理
   │
   ├── 定期掃描過期 Session
   └── 自動刪除
```

**使用場景：**
- VH：保存用戶對話歷史
- BO：保存管理操作記錄

---

## 5. 目錄結構

### 完整專案結構

```
agent-shrimp/
├── agent/                          # Agent 層（Workflow 執行）
│   ├── shared/                     # 共享模組（平台層）
│   │   ├── llm_providers.py        # LLM Provider 接口
│   │   ├── llm_factory.py          # Provider 工廠
│   │   └── rag/                    # RAG 檢索
│   │       ├── meta_generator.py
│   │       └── knowledge_retriever.py
│   │
│   ├── virtual_human/              # VH Agent 專屬
│   │   ├── api.py                  # /vh/chat 端點
│   │   ├── config_loader.py        # YAML 配置載入
│   │   ├── spec_loader.py          # 輸出規格載入
│   │   └── specs/
│   │       └── virtual-human-output-spec.md
│   │
│   └── backend_operator/           # BO Agent 專屬
│       └── api.py                  # /chat 端點（管理用）
│
├── session/                        # Session 層（共享）
│   ├── __init__.py
│   ├── session_store.py            # SQLite 存儲（主版本）
│   ├── session_api.py              # FastAPI Router
│   └── session_manager_backup.py   # In-Memory 備份
│
├── frontend/                       # 前端層（簡單驗證用）
│   ├── templates/
│   │   ├── index.html              # 首頁
│   │   ├── chat.html               # BO 對話頁面
│   │   └── vh-chat.html            # VH 對話頁面
│   └── static/
│       └── js/
│           ├── chat.js             # BO 對話邏輯
│           └── vh-chat.js          # VH 對話邏輯
│
├── workspace/
│   └── personas/                   # Persona 層（VH 專屬）
│       ├── ubichan/
│       │   ├── style.md            # 角色風格
│       │   └── config.yaml         # 資源配置
│       ├── nurse/
│       │   ├── style.md
│       │   └── config.yaml
│       └── TEMPLATE/
│           ├── style.md
│           └── config.yaml
│
├── workspace/
│   ├── personas/                   # PERSONA 層（共享）
│   │   └── ubitus/
│   │       ├── style.md
│   │       └── config.yaml
│   └── knowledge/                  # 知識庫層（共享）
│       └── ubitus/
│           ├── meta.json           # 【自動生成】文件索引
│           └── *.txt               # 知識內容
│
├── tools/                          # TOOL 層（共享）
│   ├── __init__.py
│   ├── base.py                     # Tool 基類
│   ├── public/                     # PUBLIC Tools
│   │   ├── __init__.py
│   │   ├── web_search_tool.py
│   │   └── knowledge/
│   │       ├── meta_tool.py
│   │       └── query_tool.py
│   └── internal/                   # INTERNAL Tools
│       ├── __init__.py
│       └── file_system/
│           ├── read_file_tool.py
│           ├── write_file_tool.py
│           ├── list_dir_tool.py
│           ├── read_pdf_tool.py
│           ├── read_word_tool.py
│           └── read_csv_tool.py
│
├── setup/
│   ├── docker-compose.yml
│   └── Dockerfile
│
└── docs/                           # 文檔
    ├── 01_designs/                 # 設計文檔
    │   ├── 00_PLATFORM_OVERVIEW.md
    │   ├── 01_VIRTUAL_HUMAN_DESIGN.md
    │   ├── 02_BACKEND_OPERATOR_DESIGN.md
    │   └── 03_ARCHITECTURE.md      # 本文件
    ├── 03_specs/                   # 規格文件
    ├── 02_guides/                  # 使用指南
    ├── 04_reference/
    ├── 05_archive/
    └── 06_study/
```

---

## 6. 技術選型

### 平台層（共享）
- **語言：** Python 3.10+
- **框架：** FastAPI
- **數據庫：** SQLite 3
- **LLM 接口：** OpenAI 兼容

### VH Agent
- **Workflow：** LLM1/LLM2 雙階段
- **輸出：** SSE 串流
- **前端：** 純 HTML + JavaScript

### BO Agent
- **Workflow：** Agent Loop 多輪執行
- **輸出：** API 回應（無 SSE）
- **前端：** 無（API-only）

### 部署
- **容器：** Docker + Docker Compose
- **掛載：** 知識庫、Persona 配置

---

## 7. 版本歷史

| 版本 | 日期 | 變更 |
|------|------|------|
| v2.0 | 2026-04-30 | **平台 + 雙 Agent 架構**、BO Agent 加入 |
| v1.2 | 2026-04-16 | Session 模組獨立、前端清理 |
| v1.1 | 2026-04-15 | STREAM 模式、SSE 修復 |
| v1.0 | 2026-04-01 | 初始版本（VH only） |

---

**相關文檔：**
- 平台概述：`00_PLATFORM_OVERVIEW.md`
- VH 設計：`01_VIRTUAL_HUMAN_DESIGN.md`
- BO 設計：`02_BACKEND_OPERATOR_DESIGN.md`
- Tool 規格：`03_specs/08_TOOL_SPEC.md`
- API 規格：`03_specs/01_AGENT_API_SPEC.md`
- 快速開始：`02_guides/01_QUICKSTART.md`
