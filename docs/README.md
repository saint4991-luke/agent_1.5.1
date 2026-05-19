# 📚 AgentShrimp 文檔地圖

**Branch:** `agent-ubichan`  
**最後更新:** 2026-05-01  
**版本:** v5.0 (文件重組)

---

## 📁 目錄結構

```
docs/
├── 01_designs/         # 設計文檔（系統架構、設計理念）
├── 02_guides/          # 使用指南（快速開始、操作手冊）
├── 03_specs/           # 規格文件（14 個核心規格）
├── 04_reference/       # 參考手冊（Tool 參考等）
└── README.md           # 本文件
```

---

## 📋 文檔清單

### 01_designs/ - 設計文檔

| 檔案 | 說明 |
|------|------|
| [00_PLATFORM_OVERVIEW.md](01_designs/00_PLATFORM_OVERVIEW.md) | 平台概述 |
| [01_VIRTUAL_HUMAN_DESIGN.md](01_designs/01_VIRTUAL_HUMAN_DESIGN.md) | Virtual Human 設計 |
| [02_BACKEND_OPERATOR_DESIGN.md](01_designs/02_BACKEND_OPERATOR_DESIGN.md) | Backend Operator 設計 |
| [03_ARCHITECTURE.md](01_designs/03_ARCHITECTURE.md) | 系統架構（平台 + 雙 Agent） |

### 02_guides/ - 使用指南

| 檔案 | 說明 |
|------|------|
| [01_QUICKSTART.md](02_guides/01_QUICKSTART.md) | 快速開始 |
| [02_PERSONA_GUIDE.md](02_guides/02_PERSONA_GUIDE.md) | Persona 設計指南 |
| [03_KNOWLEDGE_GUIDE.md](02_guides/03_KNOWLEDGE_GUIDE.md) | 知識庫指南 |
| [04_BO_AGENT_GUIDE.md](02_guides/04_BO_AGENT_GUIDE.md) | BO Agent 使用指南 |
| [05_DEPLOYMENT_TROUBLESHOOTING.md](02_guides/05_DEPLOYMENT_TROUBLESHOOTING.md) | 部署與問題診斷 |

### 03_specs/ - 規格文件（14 個）

| 編號 | 檔案 | 說明 |
|------|------|------|
| 01 | [01_AGENT_API_SPEC.md](03_specs/01_AGENT_API_SPEC.md) | Agent API 規格 |
| 02 | [02_VIRTUAL_HUMAN_WORKFLOW.md](03_specs/02_VIRTUAL_HUMAN_WORKFLOW.md) | VH Workflow 規格 |
| 03 | [03_BACKEND_OPERATOR_WORKFLOW.md](03_specs/03_BACKEND_OPERATOR_WORKFLOW.md) | BO Workflow 規格 |
| 04 | [04_PERSONA_SPEC.md](03_specs/04_PERSONA_SPEC.md) | Persona 配置規格 |
| 05 | [05_SESSION_API_SPEC.md](03_specs/05_SESSION_API_SPEC.md) | Session API 規格 |
| 06 | [06_SESSION_SDK_SPEC.md](03_specs/06_SESSION_SDK_SPEC.md) | Session SDK 規格 |
| 07 | [07_KNOWLEDGE_SPEC.md](03_specs/07_KNOWLEDGE_SPEC.md) | Knowledge 系統規格 |
| 08 | [08_TOOL_SPEC.md](03_specs/08_TOOL_SPEC.md) | **Tool 系統規格**（合併版） |
| 09 | [09_OUTPUT_FORMAT.md](03_specs/09_OUTPUT_FORMAT.md) | 輸出格式規格 |
| 10 | [10_SSE_OUTPUT_SPEC.md](03_specs/10_SSE_OUTPUT_SPEC.md) | SSE 輸出規格 |
| 11 | [11_LLM_PROVIDER_SPEC.md](03_specs/11_LLM_PROVIDER_SPEC.md) | LLM Provider 規格 |
| 12 | [12_PERFORMANCE_SPEC.md](03_specs/12_PERFORMANCE_SPEC.md) | 效能規格 |
| 13 | [13_AGENT_LOOP_SPEC.md](03_specs/13_AGENT_LOOP_SPEC.md) | **Agent Loop 執行規格**（通用） |
| 14 | [14_AGENT_LOOP_PROMPT_STRUCTURE.md](03_specs/14_AGENT_LOOP_PROMPT_STRUCTURE.md) | **Agent Loop Prompt 結構**（通用） |

### 04_reference/ - 參考手冊

| 目錄/檔案 | 說明 |
|-----------|------|
| [tools/](04_reference/tools/) | **Tool 參考手冊**（11 個 Tool） |
| └── [README.md](04_reference/tools/README.md) | Tool 參考索引 |

**Tool 參考清單：**
- Internal Tools（7 個）：`list_dir`, `read_file`, `write_file`, `read_excel`, `read_csv`, `read_word`, `read_pdf`
- Public Tools（4 個）：`web_search`, `knowledge_meta`, `knowledge_query`, `rebuild_knowledge_meta`

---

## 🚀 快速開始

### 新用戶閱讀順序

1. **[01_designs/00_PLATFORM_OVERVIEW.md](01_designs/00_PLATFORM_OVERVIEW.md)** → 了解平台設計理念
2. **[01_designs/03_ARCHITECTURE.md](01_designs/03_ARCHITECTURE.md)** → 了解系統架構
3. **[02_guides/01_QUICKSTART.md](02_guides/01_QUICKSTART.md)** → 開始使用

### 開發者閱讀順序

1. **[01_designs/](01_designs/)** → 了解架構設計
2. **[03_specs/](03_specs/)** → 查看技術規格
3. **[04_reference/tools/](04_reference/tools/)** → 查看 Tool 參考

### Agent Loop 開發者

1. **[13_AGENT_LOOP_SPEC.md](03_specs/13_AGENT_LOOP_SPEC.md)** → Agent Loop 執行流程
2. **[14_AGENT_LOOP_PROMPT_STRUCTURE.md](03_specs/14_AGENT_LOOP_PROMPT_STRUCTURE.md)** → Prompt 結構規格
3. **[03_BACKEND_OPERATOR_WORKFLOW.md](03_specs/03_BACKEND_OPERATOR_WORKFLOW.md)** → BO 專屬配置

---

## 📝 文檔分類原則

| 分類 | 說明 | 特點 |
|------|------|------|
| **01_designs** | 設計理念、架構思路 | 哲學性、宏觀 |
| **02_guides** | 操作手冊、使用指南 | 實用性、步驟式 |
| **03_specs** | 技術規格、API 定義 | 硬性規定、必須遵守 |
| **04_reference** | 參考手冊、Tool 說明 | 補充說明、查詢用 |

---

## 🔄 最新版本變更（v5.0）

**2026-05-01 文件重組：**

| 變更類型 | 說明 |
|----------|------|
| **合併** | Tool 架構 + 執行規格 → `08_TOOL_SPEC.md` |
| **新增** | 5 個 Internal Tool 參考文件 |
| **重組** | Agent Loop 規格分離為通用（13/14）與 BO 專屬（03） |
| **刪除** | `04_TESTING/` 目錄 |
| **前移** | `05_reference/` → `04_reference/` |
| **編號** | 03_specs 編號調整為連續 1-14 |

---

**文檔結束**
