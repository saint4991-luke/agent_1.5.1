# 🏛️ 虛擬人平台概述

**版本：** v3.1  
**日期：** 2026-04-30  
**Branch:** `agent-ubichan`

---

## 🎯 文件職責

**本文檔說明：**
- 虛擬人平台的整體設計理念
- 平台層共享模組的職責與協作方式
- 兩種 Agent 類型（VH 與 BO）的概述

**本文檔不包含：**
- VH Agent 專屬設計（→ `01_VIRTUAL_HUMAN_DESIGN.md`）
- BO Agent 專屬設計（→ `02_BACKEND_OPERATOR_DESIGN.md`）
- 技術架構細節（→ `03_ARCHITECTURE.md`）

---

## 1. 平台概述

### 設計理念

虛擬人平台致力於打造**有溫度、有個性、有知識**的對話體驗，通過共享模組與 Agent 層的緊密協作，實現：

- ✅ **快速回應** - 安撫話語 < 1 秒發送
- ✅ **個性化** - 每個虛擬人都有獨特風格
- ✅ **專業知識** - 知識庫支撐準確回答
- ✅ **會話管理** - 獨立 Session 追蹤對話歷史
- ✅ **擴展能力** - Tool 系統支持功能擴展
- ✅ **多端適配** - 前端模組支持多種 UI 場景
- ✅ **多 Provider** - 支持 LLM Provider 切換

### 平台架構：一平台、兩 Agent

```
┌─────────────────────────────────────────────────────────┐
│                    虛擬人平台                            │
│                                                         │
│  平台層（共享模組）                                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────┐ │
│  │ PERSONA  │  │ SESSION  │  │ KNOWLEDGE│  │  TOOL  │ │
│  │  角色    │  │  會話    │  │  知識庫  │  │  工具  │ │
│  └──────────┘  └──────────┘  └──────────┘  └────────┘ │
│                                                         │
│  Agent 層（使用者）                                       │
│  ┌──────────────────────┐  ┌──────────────────────┐   │
│  │  Virtual Human (VH)  │  │  Backend Operator    │   │
│  │  虛擬人 Agent         │  │  後台運維 Agent       │   │
│  │  - 對話、陪伴、客服   │  │  - 管理、維護、配置   │   │
│  │  - 情感化回應         │  │  - 專業、直接         │   │
│  └──────────────────────┘  └──────────────────────┘   │
│                                                         │
│  支援模組                                                │
│  ┌──────────┐  ┌──────────┐                            │
│  │  前端    │  │  LLM     │                            │
│  │Frontend  │  │Provider  │                            │
│  └──────────┘  └──────────┘                            │
└─────────────────────────────────────────────────────────┘
```

### 兩種 Agent 對比

| 維度 | Virtual Human (VH) | Backend Operator (BO) |
|------|-------------------|----------------------|
| **用途** | 對話、陪伴、客服 | 後台管理、知識庫維護 |
| **用戶** | 一般用戶 | 管理員、開發者 |
| **回應風格** | 有情感、有個性 | 專業、直接 |
| **Tool 使用** | 較少（知識庫查詢） | 較多（文件操作） |
| **Agent Loop** | 雙 LLM（快速回應 + 完整） | 單 Agent Loop（多輪執行） |
| **Persona** | 需要（風格定義） | 不需要（或簡化） |
| **Session** | 需要（對話歷史） | 需要（任務追蹤） |

---

## 2. 平台層共享模組

### 2.1 PERSONA（角色設定）

**職責：** 定義虛擬人的個性、風格、語言特徵

**核心特點：**
- **風格 Prompt** - 通過 YAML 配置定義虛擬人個性
- **多角色支持** - 同時運行多個虛擬人
- **輸出格式** - 支持 3 種格式（virtual_human, plain, markdown）
- **綁定 Session** - 每個 Session 綁定一個 Persona ID
- **快速回應配置** - 可配置快速回應長度（`quick_response.max_length`）

**配置結構：**
```
workspace/personas/
└── ubichan/
    ├── config.yaml       # YAML v2.1 配置
    └── style.md          # 風格 Prompt
```

**相關規格：**
- [03_specs/03_PERSONA_SPEC.md](../03_specs/03_PERSONA_SPEC.md) - Persona 配置規格

---

### 2.2 SESSION（會話管理）

**職責：** 管理獨立對話會話，追蹤對話歷史與 Metadata

**核心特點：**
- **獨立 Session** - 每個對話擁有獨立 Session ID
- **TTL 過期** - 支持自動過期清理（背景任務）
- **Metadata 擴展** - 命名空間設計，支持自定義數據
- **持久化存儲** - SQLite 存儲，支持重啟恢復

**API 端點：**
- `POST /sessions` - 創建 Session
- `GET /sessions/{session_id}` - 查詢 Session
- `DELETE /sessions/{session_id}` - 刪除 Session
- `GET /sessions/{session_id}/messages` - 查詢消息歷史

**相關規格：**
- [03_specs/03_SESSION_API_SPEC.md](../03_specs/03_SESSION_API_SPEC.md) - Session API 規格
- [03_specs/04_SESSION_SDK_SPEC.md](../03_specs/04_SESSION_SDK_SPEC.md) - Session SDK 規格

---

### 2.3 KNOWLEDGE（知識庫）

**職責：** 提供專業知識支撐，支持準確回答

**核心特點：**
- **兩階段檢索** - Meta 判斷（快）+ 文件載入（準）
- **通關密語** - 口語觸發知識庫管理（安全機制）
- **多格式支持** - TXT、Markdown、PDF（擴展中）
- **自動 Tool** - LLM 自動判斷何時呼叫知識庫

**知識庫結構：**
```
/workspace/knowledge/
└── ubitus/
    ├── meta.json           # 自動生成，文件索引
    ├── company.txt         # 公司資訊
    ├── products.txt        # 產品介紹
    └── faq.txt             # 常見問題
```

**相關規格：**
- [03_specs/06_KNOWLEDGE_SPEC.md](../03_specs/06_KNOWLEDGE_SPEC.md) - Knowledge 系統規格

---

### 2.4 TOOL（工具系統）

**職責：** 擴展虛擬人能力，支持外部 API 調用與功能擴展

**核心特點：**
- **Persona 授權** - 每個虛擬人可配置不同的可用工具
- **安全機制** - 通關密語保護敏感操作
- **可擴展** - 支持自定義 Tool 開發

**內建 Tool：**
| Tool 名稱 | 功能 | 說明 |
|-----------|------|------|
| `rebuild_knowledge_meta` | 重新生成知識庫 Meta | 需要通關密語保護 |

**相關規格：**
- [03_specs/09_TOOL_SPEC.md](../03_specs/09_TOOL_SPEC.md) - Tool 系統規格

---

### 2.5 前端（Frontend）

**職責：** 提供用戶介面，支持多種場景適配

**核心特點：**
- **多端適配** - Web UI、管理員前端、虛擬人前端
- **STREAM 支持** - 實時顯示回答片段
- **emotion/lang 渲染** - 根據標籤調整 UI 表現

**前端類型：**
| 類型 | 場景 | 特點 |
|------|------|------|
| Web UI | 一般用戶對話 | 簡單易用，支持 STREAM |
| 管理員前端 | 內部測試/調試 | 完整功能，日誌查看 |
| 虛擬人前端 | 品牌場景 | 客製化 UI，頭像顯示 |

---

### 2.6 LLM Provider（模型層）

**職責：** 統一 LLM 接口，支持多 Provider 切換

**核心特點：**
- **多 Provider 支援** - OpenAI 兼容接口、Ubisage 專屬接口
- **統一接口** - `chat()` 和 `chat_stream()` 方法
- **靈活配置** - 通過環境變數切換 Provider

**支援 Provider：**
| Provider | 說明 | 配置方式 |
|----------|------|----------|
| **openai** | OpenAI 兼容接口 | `OPENAI_BASE_URL`, `OPENAI_API_KEY` |
| **ubisage** | Ubisage 專屬接口 | `UBISAGE_API_KEY`, `UBISAGE_GRANT_URL` |

---

## 3. 技術架構

### Docker 容器架構

```
┌─────────────────────────────────────────────────────────┐
│              Agent API 容器 (Port 8000)                  │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  AGENT   │  │ PERSONA  │  │ SESSION  │              │
│  └──────────┘  └──────────┘  └──────────┘              │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │KNOWLEDGE │  │   TOOL   │  │   LLM    │              │
│  └──────────┘  └──────────┘  │ Provider │              │
│                              └──────────┘              │
│                                                         │
│  SQLite: /data/sessions.db                              │
│  Workspace: /workspace/                                 │
│    - Personas: /workspace/personas/*/                   │
│    - Knowledge: /workspace/knowledge/*                  │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                     前端 (Frontend)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │
│  │ 虛擬人前端  │  │ 管理員前端  │  │  Web UI     │     │
│  └─────────────┘  └─────────────┘  └─────────────┘     │
└─────────────────────────────────────────────────────────┘
```

### 目錄結構

```
agtshrimp/
├── agent/                      # Agent 層（Workflow 執行）
│   ├── agent-api-streaming.py  # 主程式
│   ├── virtual_human/          # 虛擬人端點
│   ├── backend_operator/       # 後台運維端點
│   ├── rag/                    # KNOWLEDGE 模組
│   └── tools/                  # TOOL 模組
├── session/                    # SESSION 模組（平行目錄）
│   ├── session_api.py
│   └── session_store.py
├── workspace/
│   ├── personas/               # PERSONA 目錄
│   └── knowledge/              # KNOWLEDGE 目錄
├── frontend/                   # Frontend 目錄
├── setup/                      # Docker 部署
└── docs/                       # 文檔
```

---

## 📚 相關文檔

| 類別 | 文檔 | 說明 |
|------|------|------|
| **VH Agent** | [01_VIRTUAL_HUMAN_DESIGN.md](01_VIRTUAL_HUMAN_DESIGN.md) | Virtual Human 專屬設計 |
| **BO Agent** | [02_BACKEND_OPERATOR_DESIGN.md](02_BACKEND_OPERATOR_DESIGN.md) | Backend Operator 專屬設計 |
| **架構** | [03_ARCHITECTURE.md](03_ARCHITECTURE.md) | 系統架構說明 |

---

**🦐 Have fun with Virtual Human Platform!**
