#!/usr/bin/env python3
"""
🦐 蝦米 Agent API 服務 v4.2.0 - 三類架構重構

支援的 Provider:
- OpenAI Provider: OpenAI, vLLM, LocalAI, Ollama (OpenAI 相容)
- Ubisage Provider: Ubisage 私有模型 (需要 Token 交換)

架構變更：
- Session API 作為 Agent API 的內建模組
- 代碼職責分離，但運行在同一容器
- 對話時調用 Session API 模組獲取 Session 內容
- 使用三類執行狀態：DONE, NEEDS_INTERACTION, ERROR
"""

import sys
import os
import json
import time  # 用於 TIMING 記錄
import re  # 用於正則表達式解析
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from enum import Enum
from dataclasses import dataclass, field


# FastAPI
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
import uvicorn
import asyncio

# Dotenv - 環境變數由 docker-compose env_file 注入
# 容器內不需要載入 .env 檔案，直接使用 os.getenv() 即可
import os
print(f"📝 環境變數已注入（通過 docker-compose env_file）")

# ============= 語言檢測函數已移除 =============
# 語言判斷應該讓 LLM 自己根據 prompt 指令處理，不需要程式碼檢測
# System Prompt 第 4.2 節已有語言匹配指令，LLM 會自動判斷用戶語言並回應

# 流式模組
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'shared'))
from block_chunker import BlockChunker
from sse_events import StreamEvent, StreamEventType, format_sse_event

# Tools 模組（添加到 Python path）
# /app/backend_operator → /app (這樣才能 import tools.xxx)
app_path = str(Path(__file__).parent.parent)
sys.path.insert(0, app_path)
print(f"🔧 添加 app 路徑：{app_path}")
print(f"📋 當前 sys.path: {sys.path[:5]}")

# LLM Provider 抽象層
from llm_factory import create_provider, get_default_provider_type
from llm_providers import LLMProvider

# Tools Base（新增）
from tools.base import BaseTool

# KNOWLEDGE Tools（Public - VH + BO 都可用）
from tools.public.knowledge import KnowledgeMetaTool, KnowledgeQueryTool, MetaGeneratorTool

# FILE SYSTEM Tools（Internal - 僅 BO 可用）
from tools.internal.file_system import (
    ReadFileTool,
    WriteFileTool,
    ListDirTool,
    ReadExcelTool,
    ReadCsvTool,
    ReadWordTool,
    ReadPdfTool,
)

# EXTERNAL Tools（Public - VH + BO 都可用）
from tools.public import WebSearchTool


# ============= Session 模組（直接函數調用）=============
import sys
sys.path.insert(0, '/app')  # 添加根目錄到 Python path
from session.session_store import get_session_store

# 獲取全局 Session Store 實例
session_store = get_session_store('/data/sessions.db')


async def get_session_from_api(session_id: str) -> Optional[Dict[str, Any]]:
    """
    從 Session Store 獲取 Session 內容
    
    Args:
        session_id: Session ID
    
    Returns:
        Session 內容字典，如果失敗則返回 None
    """
    try:
        session = session_store.get_session(session_id)
        return session
    except Exception as e:
        print(f"❌ 獲取 Session 失敗：{e}")
        return None


async def add_message_to_session(session_id: str, role: str, content: str, 
                                  emotion: Optional[str] = None, 
                                  lang: Optional[str] = None) -> bool:
    """
    添加訊息到 Session
    
    Args:
        session_id: Session ID
        role: 角色 ('user' 或 'assistant')
        content: 訊息內容
        emotion: 情緒標籤（可選）
        lang: 語言標籤（可選）
    
    Returns:
        是否添加成功
    """
    try:
        return session_store.add_message(session_id, role, content, emotion, lang)
    except Exception as e:
        print(f"❌ 添加訊息失敗：{e}")
        return False

# 虛擬人模組
try:
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from virtual_human.api import router as virtual_human_router, init_virtual_human_api
    from virtual_human.config_loader import ConfigLoader
    from virtual_human.style_manager import StyleManager
    from shared.llm_service import create_llm_service
    VIRTUAL_HUMAN_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  虛擬人模組未導入：{e}")
    VIRTUAL_HUMAN_AVAILABLE = False
    virtual_human_router = None
    ConfigLoader = None
    StyleManager = None
    create_llm_service = None

# ============= 配置 =============
WORKSPACE = Path("/workspace")
KNOWLEDGE_BASE = WORKSPACE / "knowledge"

# LLM Provider 配置
LLM_PROVIDER_TYPE = get_default_provider_type()  # "openai" 或 "ubisage"
llm_provider: Optional[LLMProvider] = None

# 其他配置
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "4096"))
THINKING = os.getenv("THINKING", "enabled")
REASONING_EFFORT = os.getenv("REASONING_EFFORT", "low")
REQUEST_TIMEOUT = float(os.getenv("REQUEST_TIMEOUT", "30.0"))
STREAM_MIN_CHARS = int(os.getenv("STREAM_MIN_CHARS", "800"))
STREAM_MAX_CHARS = int(os.getenv("STREAM_MAX_CHARS", "1200"))
MAX_PARALLEL_TOOLS = int(os.getenv("MAX_PARALLEL_TOOLS", "5"))

# ============= 工具定義 =============
# 使用 Tool 類別的 to_schema() 方法生成 Schema
TOOLS = []

# 初始化所有 Tool 實例
WORKSPACE_PATH = "/workspace"
read_tool = ReadFileTool(workspace_path=WORKSPACE_PATH)
write_tool = WriteFileTool(workspace_path=WORKSPACE_PATH)
list_tool = ListDirTool(workspace_path=WORKSPACE_PATH)
excel_tool = ReadExcelTool(workspace_path=WORKSPACE_PATH)
csv_tool = ReadCsvTool(workspace_path=WORKSPACE_PATH)
word_tool = ReadWordTool(workspace_path=WORKSPACE_PATH)
pdf_tool = ReadPdfTool(workspace_path=WORKSPACE_PATH)
meta_tool = KnowledgeMetaTool(knowledge_base_path=str(KNOWLEDGE_BASE))
query_tool = KnowledgeQueryTool(knowledge_base_path=str(KNOWLEDGE_BASE))
gen_tool = MetaGeneratorTool(knowledge_base_path=str(KNOWLEDGE_BASE), llm_client=None)
search_tool = WebSearchTool(max_results=5)

# 生成 Tool Schema（移除 scan_workspace，改用基本 Tool）
TOOLS.extend([
    # scan_tool.to_schema(),  ← 已移除
    read_tool.to_schema(),
    write_tool.to_schema(),
    list_tool.to_schema(),
    excel_tool.to_schema(),
    csv_tool.to_schema(),
    word_tool.to_schema(),
    pdf_tool.to_schema(),
    search_tool.to_schema(),  # WebSearchTool
])

# 手動定義 rebuild_knowledge_meta 的 Schema
TOOLS.append({
    "type": "function",
    "function": {
        "name": "rebuild_knowledge_meta",
        "description": "重新生成知識庫的 meta.json（需要通關密語）",
        "parameters": {
            "type": "object",
            "properties": {
                "knowledge_id": {
                    "type": "string",
                    "description": "知識庫 ID，例如 'ubitus'。如果為空則重新生成所有知識庫"
                },
                "passphrase": {
                    "type": "string",
                    "description": "通關密語"
                }
            },
            "required": ["passphrase"]
        }
    }
})

# ============= 執行狀態定義（三類架構） =============

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
    tool_results: list = field(default_factory=list)

# ============= 工具實作 =============
# ⚠️ 注意：以下 Tool 已重構為 tools/ 下的類別
# - scan_workspace → ScanWorkspaceTool (tools/file_system/)
# - read_file → ReadFileTool (tools/file_system/)
# - write_file → WriteFileTool (tools/file_system/)
# - list_dir → ListDirTool (tools/file_system/)
# - read_excel → ReadExcelTool (tools/file_system/)
# - read_csv → ReadCsvTool (tools/file_system/)
# - read_word → ReadWordTool (tools/file_system/)
# - read_pdf → ReadPdfTool (tools/file_system/)
# - web_search → WebSearchTool (tools/external/)
# - rebuild_knowledge_meta → MetaGeneratorTool (tools/knowledge/)
#
# 所有 Tool 現在都通過 TOOL_INSTANCES 調用


def rebuild_knowledge_meta(knowledge_id: str = "", passphrase: str = "") -> str:
    """
    重新生成知識庫的 meta.json（使用 MetaGeneratorTool）
    
    Args:
        knowledge_id: 知識庫 ID（例如 'ubitus'），如果為空則重新生成所有知識庫
        passphrase: 通關密語（預設：5688）
    
    Returns:
        執行結果字串
    """
    # 驗證通關密語
    expected_passphrase = os.getenv("KNOWLEDGE_PASSPHRASE", "5688")
    if passphrase != expected_passphrase:
        return f"❌ 通關密語錯誤"
    
    try:
        # 初始化 Tool（不使用 LLM，僅生成基本資訊）
        tool = MetaGeneratorTool(
            knowledge_base_path=str(KNOWLEDGE_BASE),
            llm_client=None
        )
        
        if knowledge_id:
            # 重新生成單一知識庫
            result = tool.execute(knowledge_id=knowledge_id, force=True)
            if result["success"]:
                meta = result["data"]["meta"]
                return f"✅ 已重新生成知識庫 '{knowledge_id}' 的 meta.json\n\n摘要：\n- 文件數量：{len(meta.get('files', []))}\n- 知識庫 ID: {meta.get('knowledge_id', 'N/A')}"
            else:
                return f"❌ 重新生成失敗：{result.get('error', 'Unknown error')}"
        else:
            # 重新生成所有知識庫
            result = tool.execute_all(force=True)
            if result["success"]:
                data = result["data"]
                all_metas = data.get("metas", {})
                if not all_metas:
                    return "⚠️ 沒有找到任何知識庫"
                
                result_list = [f"✅ 已重新生成 {len(all_metas)} 個知識庫的 meta.json:\n"]
                for kid, meta in all_metas.items():
                    if "error" in meta:
                        result_list.append(f"- {kid}: ❌ {meta['error']}")
                    else:
                        file_count = len(meta.get('files', []))
                        result_list.append(f"- {kid}: {file_count} 個文件")
                return "\n".join(result_list)
            else:
                return f"❌ 批量重新生成失敗：{result.get('error', 'Unknown error')}"
            
    except Exception as e:
        import traceback
        print(f"❌ rebuild_knowledge_meta 錯誤：{e}")
        traceback.print_exc()
        return f"❌ 重新生成失敗：{e}"

# 工具函數映射（使用 Tool 實例的 execute 方法）
# 移除 scan_workspace，改用基本的 list_dir + read_file 測試多 Tool 調用
TOOL_INSTANCES = {
    # "scan_workspace": scan_tool,  ← 已移除，使用基本 Tool 代替
    "read_file": read_tool,
    "write_file": write_tool,
    "list_dir": list_tool,
    "read_excel": excel_tool,
    "read_csv": csv_tool,
    "read_word": word_tool,
    "read_pdf": pdf_tool,
    "knowledge_meta": meta_tool,
    "knowledge_query": query_tool,
    "web_search": search_tool,
    "rebuild_knowledge_meta": gen_tool,
}

def execute_tool(tool_name: str, **kwargs):
    """
    執行 Tool
    
    Args:
        tool_name: Tool 名稱
        **kwargs: Tool 參數
    
    Returns:
        dict: {"success": bool, "data": Any, "error": Optional[str]}
    """
    if tool_name not in TOOL_INSTANCES:
        return {"success": False, "error": f"Unknown tool: {tool_name}"}
    
    tool = TOOL_INSTANCES[tool_name]
    if tool is None:
        return {"success": False, "error": f"Tool not implemented: {tool_name}"}
    
    # 使用 Tool 的 execute 方法
    return tool.execute(**kwargs)

# ============= FastAPI 應用 =============
@asynccontextmanager
async def lifespan(app: FastAPI):
    """應用生命週期管理"""
    # 啟動時
    print("🦐 蝦米 Agent API 服務 v3.2.1 啟動中...")
    print(f"📦 LLM Provider: {LLM_PROVIDER_TYPE}")
    print(f"📦 LLM Provider: {LLM_PROVIDER_TYPE}")
    print(f"🌐 API 基礎 URL: {os.getenv('OPENAI_BASE_URL', 'N/A')}")
    print(f"🤖 模型：{os.getenv('LLM_MODEL', os.getenv('OPENAI_MODEL', 'N/A'))}")
    print(f"⚙️  Session 功能：已啟用（內建模組）")
    
    # 初始化 LLM Provider
    global llm_provider
    try:
        llm_provider = create_provider()
        print(f"✅ LLM Provider 初始化成功")
    except Exception as e:
        print(f"⚠️  LLM Provider 初始化失敗：{e}")
        print(f"   將在首次請求時重試")
    
    # 獲取 Git Commit Hash（用於版本追蹤）
    git_hash = "unknown"
    try:
        import subprocess
        git_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd="/app",  # Docker 容器內的工作目錄
            stderr=subprocess.DEVNULL
        ).decode("ascii").strip()
    except Exception:
        pass
    
    # 印出 Git Commit Hash（方便版本追蹤）
    print(f"📋 Git Commit: {git_hash}")
    
    # 初始化虛擬人模組
    if VIRTUAL_HUMAN_AVAILABLE:
        print("🎭 初始化虛擬人模組...")
        try:
            # 1. 初始化 ConfigLoader（載入所有 personas 配置）
            config_loader = ConfigLoader(personas_path="/workspace/personas")
            
            # 2. 初始化 StyleManager（快取風格 Prompt）
            style_manager = StyleManager(style_base="/workspace/personas")
            
            # 4. 預熱 Persona 快取（優化：啟動時載入所有風格 Prompt）
            print("🔥 預熱 Persona 快取...")
            persona_ids = config_loader.get_all_ids()
            for persona_id in persona_ids:
                try:
                    # ConfigLoader 已經在 _cache 中，直接獲取
                    config = config_loader._cache.get(persona_id)
                    if config:
                        # 從 config 獲取 style 路徑
                        style_rel_path = config.get('style')
                        if style_rel_path:
                            style_path = Path("/workspace/personas") / persona_id / style_rel_path
                            if style_path.exists():
                                style_manager.load_style(str(style_path))
                                print(f"   ✅ 預熱：{persona_id}")
                except Exception as e:
                    print(f"   ⚠️  預熱失敗 {persona_id}: {e}")
            
            # 5. 初始化 LLM Service（統一服務層）
            llm_service = create_llm_service(llm_provider) if llm_provider else None
            
            # 6. Knowledge Retriever（在 /vh/chat 中動態創建）
            knowledge_retriever = None
            
            # 7. 註冊虛擬人路由（使用 SQLite SessionStore）
            init_virtual_human_api(
                config_loader_obj=config_loader,
                session_store_obj=session_store,
                style_manager_obj=style_manager,
                knowledge_retriever_obj=knowledge_retriever,
                llm_service_obj=llm_service
            )
            app.include_router(virtual_human_router, prefix="/vh", tags=["Virtual Human"])
            
            print("✅ 虛擬人模組初始化完成")
            print(f"   - personas 數量：{len(persona_ids)}")
            print(f"   - personas 路徑：/workspace/personas")
            print(f"   - Git Commit: {git_hash}")
            print(f"   - Persona 快取：已預熱 {len(persona_ids)} 個角色")
        except Exception as e:
            print(f"⚠️  虛擬人模組初始化失敗：{e}")
    
    yield
    
    # 關閉時
    print("🦐 蝦米 Agent API 服務關閉中...")

app = FastAPI(
    title="🦐 蝦米 Agent API",
    version="3.2.1",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= 請求/回應模型 =============
class ChatRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(..., description="對話歷史")
    session_id: Optional[str] = Field(None, description="Session ID")

class ChatResponse(BaseModel):
    response: str = Field(..., description="Agent 回應")
    session_id: str = Field(..., description="Session ID")
    used_tools: List[Dict[str, Any]] = Field(default_factory=list, description="使用的工具")
    thinking: Optional[str] = Field(None, description="思考過程（如果有）")
    message_count: int = Field(0, description="Session 中的訊息總數")
    timings: Optional[Dict[str, Any]] = Field(default=None, description="性能計時數據")
    usage: Optional[Dict[str, Any]] = Field(default=None, description="Token Usage 統計")

# ============= API 端點 =============
@app.get("/health")
async def health_check():
    """健康檢查"""
    return {
        "status": "healthy",
        "version": "v4.0.0",  # 虛擬人版本
        "provider": LLM_PROVIDER_TYPE,
        "model": os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", "N/A")),
        "workspace": str(WORKSPACE),
        "session_support": True,
        "virtual_human_support": VIRTUAL_HUMAN_AVAILABLE,
        "knowledge_support": True
    }

@app.get("/sessions")
async def list_sessions():
    """列出 Sessions"""
    try:
        sessions = session_store.list_sessions()
        return {"sessions": sessions}
    except Exception as e:
        print(f"❌ 列出 Sessions 失敗：{e}")
        return {"sessions": []}


@app.post("/sessions")
async def create_session(request: dict):
    """創建 Session（支持 metadata）"""
    try:
        prefix = request.get("prefix")  # 可為空（一般無風格對話）
        metadata = request.get("metadata")  # 可選的 metadata（JSON 物件）
        ttl_hours = request.get("ttl_hours", 1)
        
        session = session_store.create_session(prefix=prefix, metadata=metadata, ttl_hours=ttl_hours)
        return session
    except Exception as e:
        print(f"❌ 創建 Session 失敗：{e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}")
async def get_session(session_id: str):
    """獲取 Session 詳情"""
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """刪除 Session"""
    success = session_store.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True, "message": "Session deleted"}


@app.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    """獲取 Session 的訊息歷史"""
    session = session_store.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"messages": session.get("messages", [])}


@app.post("/sessions/{session_id}/messages")
async def add_message(session_id: str, role: str, content: str, emotion: Optional[str] = None, lang: Optional[str] = None):
    """添加訊息到 Session"""
    success = session_store.add_message(session_id, role, content, emotion, lang)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"success": True}


# ⚠️ 暫時註解：Knowledge 功能將在後續實作為 Tool
# def _auto_search_knowledge(question: str) -> tuple:
#     """
#     自動檢索 KNOWLEDGE
#     
#     Args:
#         question: 用戶問題
#     
#     Returns:
#         (知識內容，timings 數據) 或 (None, {})
#     """
#     try:
#         # 檢查知識庫目錄是否存在
#         if not KNOWLEDGE_BASE.exists():
#             print("⚠️  KNOWLEDGE 目錄不存在")
#             return None, {}
#         
#         # 獲取所有知識庫 ID
#         knowledge_ids = [d.name for d in KNOWLEDGE_BASE.iterdir() if d.is_dir()]
#         if not knowledge_ids:
#             print("📚 沒有知識庫")
#             return None, {}
#         
#         print(f"🔍 自動檢索知識庫：{knowledge_ids}")
#         
#         # 創建檢索器（使用 LLM Provider 的客戶端）
#         llm_client = llm_provider.client if llm_provider else None
#         
#         # 創建適配器
#         class LLMAdapter:
#             def __init__(self, client, model):
#                 self.client = client
#                 self.model = model
#             
#             def generate(self, prompt: str) -> str:
#                 response = self.client.chat.completions.create(
#                     model=self.model,
#                     messages=[{"role": "user", "content": prompt}],
#                     max_tokens=500
#                 )
#                 return response.choices[0].message.content
#         
#         if llm_client:
#             adapter = LLMAdapter(llm_client, getattr(llm_provider, 'model', 'Qwen/Qwen3.5-397B-A17B-FP8'))
#             retriever = MultiKnowledgeRetriever(knowledge_ids, str(KNOWLEDGE_BASE), adapter)
#         else:
#             retriever = MultiKnowledgeRetriever(knowledge_ids, str(KNOWLEDGE_BASE), None)
#         
#         # 執行檢索
#         result = retriever.query(question)
#         
#         if result["content"]:
#             print(f"✅ 找到相關知識：{result.get('knowledge_used', [])}")
#             # 返回知識內容和 timings
#             return result["content"], result.get("timings", {})
#         else:
#             print("⚠️  未找到相關知識")
#             return None, {}
#             
#     except Exception as e:
#         print(f"❌ 自動檢索失敗：{e}")
#         return None, {}


# ============= P0 實作：多輪循環 + Tool Calling =============

def build_tool_schema(tool: BaseTool) -> Dict:
    """
    生成 LLM Provider 需要的 Tool Schema（方案 A：Native Function Calling）
    
    Args:
        tool: Tool 實例
    
    Returns:
        Tool Schema 字典
    """
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters if hasattr(tool, 'parameters') else {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    }


def parse_tool_calls_from_response(result) -> List[Dict]:
    """
    從 LLM Response 獲取 Tool Calls（方案 A：Native Function Calling）
    
    Args:
        result: LLM Provider 的 response 物件或 chat_with_tools() 返回的字典
    
    Returns:
        Tool Calls 列表
    """
    tool_calls = []
    
    try:
        # 情況 1: chat_with_tools() 返回的字典格式
        if isinstance(result, dict):
            raw_tool_calls = result.get("tool_calls", [])
            if raw_tool_calls:
                for tc in raw_tool_calls:
                    # arguments 已經是 dict（llm_providers.py 已處理）或 JSON 字串
                    args = tc.get('arguments', '{}')
                    if isinstance(args, str):
                        try:
                            args = json.loads(args) if args else {}
                        except json.JSONDecodeError as e:
                            print(f"⚠️  解析 arguments JSON 失敗：{e}")
                            print(f"📝 arguments 內容：{args[:200]}...")
                            args = {}
                    tool_calls.append({
                        'name': tc.get('name', ''),
                        'args': args
                    })
                print(f"🔧 [方案 A] 解析 Tool Calls: {len(tool_calls)} 個")
        
        # 情況 2: OpenAI response 物件格式
        elif hasattr(result, 'choices'):
            if hasattr(result.choices[0].message, 'tool_calls'):
                raw_tool_calls = result.choices[0].message.tool_calls
                if raw_tool_calls:
                    for tc in raw_tool_calls:
                        tool_calls.append({
                            'name': tc.function.name,
                            'args': json.loads(tc.function.arguments) if tc.function.arguments else {}
                        })
                    print(f"🔧 [方案 A] 解析 Tool Calls: {len(tool_calls)} 個")
    
    except Exception as e:
        print(f"⚠️  解析 Tool Calls 失敗：{e}")
    
    return tool_calls


def parse_tool_calls_from_text(llm_output: str) -> List[Dict]:
    """
    解析 LLM 輸出的 Tool Calls（方案 B：Prompt + Parsing，作為 Fallback）
    
    格式：工具調用：[{"name": "tool_name", "args": {...}}]
    
    Args:
        llm_output: LLM 輸出的完整內容
    
    Returns:
        Tool Calls 列表
    """
    import re
    
    tool_calls = []
    
    # 查找「工具調用：」開頭的行
    pattern = r'工具調用：\s*(\[.*?\])'
    match = re.search(pattern, llm_output, re.DOTALL)
    
    if match:
        try:
            tool_calls_json = match.group(1)
            tool_calls = json.loads(tool_calls_json)
            print(f"🔧 [方案 B] 解析 Tool Calls: {len(tool_calls)} 個")
        except json.JSONDecodeError as e:
            print(f"⚠️  解析 Tool Calls JSON 失敗：{e}")
            print(f"📝 JSON 內容：{match.group(1)[:200]}")
    
    return tool_calls


# 別名：保持向後相容
parse_tool_calls = parse_tool_calls_from_text


def parse_quick_response(llm_output: str, round: int = 1) -> str:
    """
    解析快速回應（安撫語）
    
    格式：快速回應：[一句話，不超過 20 字]
    
    Args:
        llm_output: LLM 輸出的完整內容
        round: 當前輪數（只有第 1 輪需要快速回應）
    
    Returns:
        快速回應字串
    """
    if round != 1:
        return ""
    
    # 查找「快速回應：」開頭的行
    pattern = r'快速回應：\s*(.+?)(?:\n|$)'
    match = re.search(pattern, llm_output)
    
    if match:
        quick_response = match.group(1).strip()
        # 限制長度
        if len(quick_response) > 50:
            quick_response = quick_response[:47] + "..."
        # DEBUG: print(f"⚡ 快速回應：{quick_response}")
        return quick_response
    
    # 第 1 輪但 LLM 沒有輸出快速回應，使用預設安撫語
    # DEBUG: print(f"⚡ 快速回應：（未找到，使用預設）")
    return "讓我幫你處理"


def parse_agent_should_continue(llm_output: str, has_tool_calls: bool = False) -> bool:
    """
    解析「AGENT 還要繼續」指標
    
    優先順序：
    1. LLM 明確輸出的標記（最可信）
    2. Fallback: has_tool_calls（保守判斷）
    
    判斷標準：
    - YES：LLM 還有「主動」的下一步行動（執行 Tool 或內部處理）
    - NO：LLM 沒有下一步行動了（任務完成或需要用戶介入）
    
    Args:
        llm_output: LLM 輸出的完整內容
        has_tool_calls: 是否有 tool_calls
    
    Returns:
        AGENT 是否還要繼續
    """
    # 1. 優先從 LLM 輸出的明確標記解析
    pattern_continue = r'AGENT 還要繼續：\s*(true|false|YES|NO)'
    match_continue = re.search(pattern_continue, llm_output, re.IGNORECASE)
    
    if match_continue:
        val = match_continue.group(1).upper()
        should_continue = val in ['TRUE', 'YES']
        print(f"📊 AGENT 還要繼續：{should_continue}（從標記解析）")
        return should_continue
    
    # 2. 沒有明確標記時，根據 has_tool_calls 判斷（保守）
    if has_tool_calls:
        print(f"📊 AGENT 還要繼續：True（fallback: 有 Tool 調用）")
        return True
    
    # 預設：不需要繼續
    print(f"📊 AGENT 還要繼續：False（fallback: 無標記且無 Tool）")
    return False


def parse_user_instruction_completed(llm_output: str) -> bool:
    """
    解析「用戶指令完成」指標
    
    優先順序：
    1. LLM 明確輸出的標記（最可信）
    2. Fallback: 從內容推斷（包含問題 → 未完成）
    
    判斷標準：
    - YES：已收集的資訊足以滿足用戶需求（用戶目的達成）
    - NO：還需要用戶提供資訊或執行更多 Tool
    
    Args:
        llm_output: LLM 輸出的完整內容
    
    Returns:
        用戶指令是否完成
    """
    # 1. 優先從 LLM 輸出的明確標記解析
    pattern_completed = r'用戶指令完成：\s*(true|false|YES|NO)'
    match_completed = re.search(pattern_completed, llm_output, re.IGNORECASE)
    
    if match_completed:
        val = match_completed.group(1).upper()
        completed = val in ['TRUE', 'YES']
        print(f"📊 用戶指令完成：{completed}（從標記解析）")
        return completed
    
    # 2. 沒有明確標記時，從內容推斷（保守）
    # 如果回應包含問題/詢問，視為未完成
    question_patterns = [r'請問', r'嗎？', r'什麼', r'哪個', r'如何', r'要不要']
    for pattern in question_patterns:
        if re.search(pattern, llm_output):
            print(f"📊 用戶指令完成：False（fallback: 回應包含問題）")
            return False
    
    # 預設：未完成（保守判斷）
    print(f"📊 用戶指令完成：False（fallback: 無明確標記）")
    return False


def clean_llm_output(llm_output: str) -> str:
    """
    清理 LLM 輸出中的標記
    
    移除：
    - 「快速回應：XXX」行
    - 「完成：true/false」行
    - 「AGENT 還要繼續：XXX」行
    - 「用戶指令完成：XXX」行
    - 「指標 1：XXX」或「**指標 1：XXX**」行
    
    Args:
        llm_output: LLM 輸出的完整內容
    
    Returns:
        清理後的內容
    """
    lines = llm_output.split('\n')
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # 跳過標記行
        if stripped.startswith('快速回應：'):
            continue
        if stripped.startswith('完成：'):
            continue
        if stripped.startswith('AGENT 還要繼續：'):
            continue
        if stripped.startswith('用戶指令完成：'):
            continue
        # 處理「**指標 1：XXX**」或「指標 1：XXX」格式
        if stripped.startswith('**指標') or stripped.startswith('指標'):
            continue
        cleaned_lines.append(line)
    
    # 確保段落之間有雙換行（Markdown 標準）
    cleaned_output = '\n'.join(cleaned_lines)
    cleaned_output = re.sub(r'\n{3,}', '\n\n', cleaned_output)
    
    return cleaned_output


def execute_tools(tool_calls: List[Dict], last_errors: Dict[str, str] = None) -> tuple[List[Dict], Dict[str, str], bool]:
    """
    執行 Tools（Layer 2: Tool Runtime）
    
    Args:
        tool_calls: Tool 調用列表
        last_errors: 上一輪的錯誤記錄 {tool_name: error_signature}
    
    Returns:
        (執行結果列表，當前錯誤記錄，是否應該停止)
    """
    if last_errors is None:
        last_errors = {}
    
    results = []
    current_errors = {}
    should_stop = False
    tool_start = time.time()
    
    for tool_call in tool_calls:
        tool_name = tool_call.get('name')
        tool_args = tool_call.get('args') or tool_call.get('arguments', {})
        
        # 🔍 印出 Tool 參數
        print(f"🔧 執行 Tool: {tool_name}")
        print(f"   📋 參數：{json.dumps(tool_args, ensure_ascii=False)}")
        
        # 獲取 Tool 實例
        tool = TOOL_INSTANCES.get(tool_name)
        
        if not tool:
            print(f"❌ Tool 不存在：{tool_name}")
            results.append({
                'tool_name': tool_name,
                'error': f'Tool 不存在：{tool_name}',
                'success': False
            })
            continue
        
        # 執行 Tool
        try:
            result = tool.execute(**tool_args)
            results.append({
                'tool_name': tool_name,
                'result': result,
                'success': True
            })
            print(f"✅ Tool 執行成功：{tool_name}")
            # 印出結果摘要（前 200 字）
            if 'data' in result:
                result_preview = str(result['data'])[:200]
                print(f"   📄 結果摘要：{result_preview}...")
            # 成功則清除錯誤記錄
            if tool_name in current_errors:
                del current_errors[tool_name]
        except Exception as e:
            import traceback
            error_msg = str(e)
            error_sig = f"{type(e).__name__}:{error_msg}"
            current_errors[tool_name] = error_sig
            
            print(f"❌ Tool 執行失敗：{tool_name} → {e}")
            traceback.print_exc()
            results.append({
                'tool_name': tool_name,
                'error': error_msg,
                'success': False
            })
            
            # 檢查是否是同樣的錯誤
            if tool_name in last_errors and last_errors[tool_name] == error_sig:
                print(f"⚠️ 同樣的錯誤再次發生，停止循環：{tool_name}")
                should_stop = True
    
    tool_time = int((time.time() - tool_start) * 1000)
    print(f"🔧 Tool 執行時間：{tool_time}ms（共 {len(tool_calls)} 個）")
    
    return results, current_errors, should_stop


def build_system_prompt(round: int, tool_results: List[Dict], require_quick_response: bool = False) -> str:
    """
    組合 System Prompt（方案 A：Native Function Calling）
    
    Args:
        round: 當前輪數
        tool_results: Tool 執行結果（v1.1 後已不再使用，Tool Result 在 conversation_history 中）
        require_quick_response: 是否要求快速回應（第 1 輪）
    
    Returns:
        System Prompt
    """
    # v1.1 變更：Tool Result 現在在 conversation_history 中，不再需要在 System Prompt 中生成
    # tool_results 參數保留以維持向後兼容，但不再使用
    
    # 動態生成可用工具清單（從 TOOLS 變數自動生成）
    tool_names = []
    for tool in TOOLS:
        if tool.get("type") == "function":
            tool_names.append(tool["function"]["name"])
    
    tools_section = ""
    if tool_names:
        tools_section = f"""
## 可用工具清單（共 {len(tool_names)} 個）

你可以使用以下工具：
{chr(10).join(['- `' + name + '`' for name in tool_names])}

**注意：** 請使用上述正確的 Tool 名稱，不要自行發明工具名稱！

"""
    
    # 快速回應格式要求（第 1 輪必須）
    quick_response_instruction = ""
    if require_quick_response and round == 1:
        quick_response_instruction = """
## 第 1 輪回應格式（必須遵守）
"""
    
    # 輸出格式要求（純文字）
    output_format_instruction = """
## 輸出格式要求

- **不要使用** Markdown 格式（如 **粗體**、*斜體*、`代碼`）
- **使用** 純文字、標點符號和換行排版
- 可以用空行分隔段落
- 可以用簡單的符號（如 -、•）做列表
"""
    
    # 組合完整指令
    format_instructions = quick_response_instruction + output_format_instruction
    
    if require_quick_response and round == 1:
        quick_response_instruction = format_instructions
    else:
        quick_response_instruction = output_format_instruction
    
    # System Prompt - 按照清晰結構組織
    # 結構：1.基本人設/職責 2.可用目錄 3.輸出格式 4.通用 AGENT LOOP 原則 5.虛擬人背景知識 6.虛擬人建立流程
    system_prompt = f"""你是一個虛擬人平台的後台助手（Backend Operator）。

---

# 1. 基本人設與職責

## 核心職責

### 1.1 知識庫管理
- 查詢、更新、維護知識內容
- 建立新知識庫、修改或删除文件

### 1.2 虛擬人設定
- 創建角色、配置風格、設定技術參數
- 查詢角色資訊、修改或删除設定

**工作方式：** 接收用戶的自然語言指令，幫忙資訊收集，處理修改相關設定檔

---

# 2. 可用目錄（重要！）

## 你可以訪問的目錄

出於安全考慮，你**只能訪問** `/workspace/` 內的目錄：

- `/workspace/` - 工作目錄（所有可變資料）
- `/workspace/knowledge/` - 知識庫目錄（知識內容）
- `/workspace/personas/` - Persona 配置目錄（虛擬人設定）

## 目錄使用範例

**查詢知識庫：**
- ✅ 正確：「列出 /workspace/knowledge 目錄下有什麼」
- ❌ 錯誤：「列出 /knowledge 目錄」（路徑不存在）
- ❌ 錯誤：「列出 / 目錄」（無法訪問根目錄）

**查詢 Persona：**
- ✅ 正確：「列出 /workspace/personas 目錄下有什麼」
- ❌ 錯誤：「列出 /personas 目錄」（路徑不存在）

**注意：** 如果用戶沒有指定完整路徑，請主動詢問或使用正確的 `/workspace/` 路徑。

---

# 3. ⚠️ 輸出格式要求（非常重要！）

**你必須使用純文字回應，禁止使用 Markdown 格式！**

- ❌ **禁止使用：** **粗體**、*斜體*、`代碼`、### 標題
- ✅ **只能使用：** 純文字、標點符號、換行
- ✅ **可以用：** 空行分隔段落、簡單符號（如 -、•）做列表

**錯誤範例：**
```
我幫你**查查** personas 目錄
找到 `ubichan` 和 `nurse` 兩個角色
```

**正確範例：**
```
我幫你查查 personas 目錄
找到 ubichan 和 nurse 兩個角色
```

---

# 4. 通用 AGENT LOOP 與工具使用原則（適用於所有任務）

{tools_section}

## 4.1 工具使用規則
1. 當用戶問題涉及知識庫或虛擬人時，主動調用工具
2. 每次調用工具時，只提供工具名稱和參數，不需要解釋
3. 如果一個工具無法完成任務，可以調用多個工具（多輪循環）
4. 當所有工具執行完成後，根據兩個指標生成最終回應

## 4.2 語言與回應格式
- **語言匹配：** 如果用戶用中文問，就用繁體中文回；用英文問就用英文回；如果是中英夾雜，判斷主要語言，用該語言回應
- 工具執行結果會自動提供給你，請根據結果生成最終回應

## 4.3 第 1 輪回應格式（僅第 1 輪）

{quick_response_instruction}

**快速回應（寫在內容開頭）：**
快速回應：[一句話，不超過 20 字]
範例：「我幫你查查」、「我開始處理」、「讓我試試看」

**Tool 調用（使用 Function Calling）：**
請使用 Tool 調用功能，不要將 Tool 調用寫在內容中。

**注意：**
- 第一行必須是「快速回應：」開頭
- **只能一句話，不超過 20 個字**
- 語言匹配用戶（用戶用繁體中文就用繁體中文，用戶用英文就用英文）

## 4.4 判斷任務是否完成（第 2 輪及之後）

請先總結當前進度：「我已經執行了 XXX Tool，獲取了 XXX 資訊」

然後判斷任務類型：

### 查詢型任務（例如：「看看有什麼」、「列出...」）
✅ 完成：已列出用戶要求的目錄/檔案/資訊
✅ 完成：資訊已呈現給用戶（在對話中）
❌ 未完成：只查詢了部分，還有用戶要求的內容沒查

### 操作型任務（例如：「創建檔案」、「修改...」）
✅ 完成：Tool 執行成功（success: true）
✅ 完成：結果已確認並告訴用戶
❌ 未完成：Tool 執行失敗或還沒執行

### 分析型任務（例如：「比較...」、「哪個比較好」）
✅ 完成：提供了分析結果或建議
✅ 完成：用戶表示理解或接受
❌ 未完成：只羅列數據，沒有結論

### 資訊不足（需要詢問用戶）
🤔 需要詢問：用戶描述模糊（如「那個檔案」）
🤔 需要詢問：缺少必要參數（如路徑、內容）
✅ 完成：已說明需要什麼資訊，等待用戶補充

**重要：**
- 如果已滿足上述任一「✅ 完成」條件 → 在回應末尾設置「用戶指令完成：YES」
- **不要重複執行已成功且結果明確的 Tool！**
- 直接告訴用戶最終結果

## 4.5 兩個關鍵指標（系統決策依據，每輪必須）

請在回應末尾明確表達以下兩個指標：

### 指標 1：AGENT 還要繼續：YES/NO

**判斷標準：** 你是否有「主動」的下一步行動？

**YES（繼續循環）：**
- 你計畫執行 Tool（有 tool_calls）
- Tool 執行後，你還需要進一步處理或分析
- 多步驟任務中，還有下一步要執行

**NO（停止循環）：**
- 任務已完成，可以給用戶最終回應
- 你需要用戶提供更多資訊（等待用戶輸入）
- 你需要用戶確認或選擇（等待用戶決策）
- 你遇到錯誤（不重試，直接叫停）
- 你無法判定用戶的目的（詢問用戶）
- 你想提供額外建議（見好就收，不要主動）

**重要原則：**
- 如果需要「用戶輸入」才能繼續 → NO（循環停止）
- 如果你可以「主動執行」下一步 → YES（循環繼續）

### 指標 2：用戶指令完成：YES/NO

**判斷標準：** 已收集的資訊是否足以滿足用戶需求？

**YES：**
- 你可以給用戶完整答案
- 用戶的目的已達成

**NO：**
- 還需要用戶提供資訊
- 還需要執行更多 Tool
- 你無法判斷用戶目的是否達成

**重要原則：**
- 如果無法判斷用戶目的是否達成 → 不要猜，詢問用戶
- 不要主動提供額外建議（見好就收）

**範例：**
```
第 1-3 輪：AGENT 還要繼續=YES，用戶指令完成=NO
第 4 輪（詢問問題）：AGENT 還要繼續=NO（需要用戶輸入），用戶指令完成=NO
最終輪：AGENT 還要繼續=NO，用戶指令完成=YES
```

**系統決策邏輯：**
- 如果 AGENT 還要繼續=YES → 繼續 Agent Loop
- 如果 AGENT 還要繼續=NO 且 用戶指令完成=YES → 生成最終回應（成功）
- 如果 AGENT 還要繼續=NO 且 用戶指令完成=NO → 直接傳遞問題（等待用戶）
- 如果達到 10 輪上限 → 強制結束（無論任務是否完成）

---

# 5. 虛擬人背景知識（參考資訊）

## 4.1 虛擬人設定（Personas）

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

## 4.2 知識庫（Knowledge）

**位置：** `/workspace/knowledge/{{知識庫 ID}}/`

| 檔案 | 用途 | 說明 |
|------|------|------|
| `*.txt` / `*.md` | 知識內容文件 | 實際的知識內容 |
| `meta.json` | 自動生成的索引 | 用於 RAG 檢索 |

**生成索引命令：**
```bash
python -m agent.rag.meta_generator knowledge/{{id}}
```

## 4.3 範本目錄

**位置：** `/workspace/personas/TEMPLATE/`
- 新角色建立的參考範本
- 包含 `style.md` 和 `config.yaml` 標準格式

---

# 6. 虛擬人建立流程（僅在創建虛擬人時適用）

## 5.1 核心認知
- 建立虛擬人 = 兩個文件（`config.yaml` + `style.md`）
- 範本固定路徑：`personas/TEMPLATE/`
- 第 1 次讀取範本後，在回應中列出範本結構摘要（進入對話歷史），後續輪次可直接引用

## 5.2 工作流程（三個階段）

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

## 4.3 標準用語

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

## 5.3 標準用語

**完成（階段 2 完成後）**
```
所有預設問題都拿到答案了，有沒有什麼要補充？

如果沒有的話，{{角色名}} 的設定就完成了！
```

## 5.4 重要提醒
- 開場白說明有四個問題
- 原則上按順序詢問（1→2→3→4）
- 使用進度回報用語
- 每個狀態講清楚
- 用戶不必理解檔案結構，只要知道資訊都有被設定到了
- 範本結構摘要要在第 1 輪回應中呈現（進入對話歷史）

---

## 3.6 Tool 執行結果（自動提供）

**重要：** Tool 執行結果會作為獨立消息（`role: "tool"`）提供給你。
- 你會在對話歷史中看到 Tool 結果
- 請根據 Tool 結果決定下一步行動
- **不要重複執行已成功且結果明確的 Tool！**
""".strip()
    
    # 第 2 輪及之後：強調判斷任務完成
    if round > 1:
        system_prompt += """

## 重要：判斷任務是否完成（客觀標準）

請先總結當前進度：「我已經執行了 XXX Tool，獲取了 XXX 資訊」

然後判斷任務類型：

### 查詢型任務（例如：「看看有什麼」、「列出...」）
✅ 完成：已列出用戶要求的目錄/檔案/資訊
✅ 完成：資訊已呈現給用戶（在對話中）
❌ 未完成：只查詢了部分，還有用戶要求的內容沒查

### 操作型任務（例如：「創建檔案」、「修改...」）
✅ 完成：Tool 執行成功（success: true）
✅ 完成：結果已確認並告訴用戶
❌ 未完成：Tool 執行失敗或還沒執行

### 分析型任務（例如：「比較...」、「哪個比較好」）
✅ 完成：提供了分析結果或建議
✅ 完成：用戶表示理解或接受
❌ 未完成：只羅列數據，沒有結論

### 資訊不足（需要詢問用戶）
🤔 需要詢問：用戶描述模糊（如「那個檔案」）
🤔 需要詢問：缺少必要參數（如路徑、內容）
✅ 完成：已說明需要什麼資訊，等待用戶補充

**重要：**
- 如果已滿足上述任一「✅ 完成」條件 → 在回應末尾設置「用戶指令完成：YES」
- **不要重複執行已成功且結果明確的 Tool！**
- 直接告訴用戶最終結果

---

## 兩個關鍵指標（系統決策依據）

請在回應末尾明確表達以下兩個指標：

### 指標 1：AGENT 還要繼續：YES/NO

**判斷標準：** 你是否有「主動」的下一步行動？

**YES（繼續循環）：**
- 你計畫執行 Tool（有 tool_calls）
- Tool 執行後，你還需要進一步處理或分析
- 多步驟任務中，還有下一步要執行

**NO（停止循環）：**
- 任務已完成，可以給用戶最終回應
- 你需要用戶提供更多資訊（等待用戶輸入）
- 你需要用戶確認或選擇（等待用戶決策）
- 你遇到錯誤（不重試，直接叫停）
- 你無法判定用戶的目的（詢問用戶）
- 你想提供額外建議（見好就收，不要主動）

**重要原則：**
- 如果需要「用戶輸入」才能繼續 → NO（循環停止）
- 如果你可以「主動執行」下一步 → YES（循環繼續）

### 指標 2：用戶指令完成：YES/NO

**判斷標準：** 已收集的資訊是否足以滿足用戶需求？

**YES：**
- 你可以給用戶完整答案
- 用戶的目的已達成

**NO：**
- 還需要用戶提供資訊
- 還需要執行更多 Tool
- 你無法判斷用戶目的是否達成

**重要原則：**
- 如果無法判斷用戶目的是否達成 → 不要猜，詢問用戶
- 不要主動提供額外建議（見好就收）

**虛擬人建立流程範例：**
```
第 1-3 輪：AGENT 還要繼續=YES，用戶指令完成=NO
第 4 輪（詢問問題）：AGENT 還要繼續=NO（需要用戶輸入），用戶指令完成=NO（只問了 1/4 個問題）
最終輪：AGENT 還要繼續=NO，用戶指令完成=YES
```

**系統決策邏輯：**
- 如果 AGENT 還要繼續=YES → 繼續 Agent Loop
- 如果 AGENT 還要繼續=NO 且 用戶指令完成=YES → 生成最終回應（成功）
- 如果 AGENT 還要繼續=NO 且 用戶指令完成=NO → 直接傳遞問題（等待用戶）
- 如果達到 10 輪上限 → 強制結束（無論任務是否完成）
"""
    
    return system_prompt


# ============= STREAM 生成器（多輪循環架構）=============

async def generate_stream(request, user_message: str, tools=None, knowledge_ids: List[str] = None, persona_config=None):
    """
    統一 STREAM 生成器（多輪循環架構）
    
    Args:
        request: ChatRequest（用於 session_id）
        user_message: 用戶問題
        tools: Tool 列表（可選，None 表示不執行 Tool）
        knowledge_ids: 知識庫 ID 列表（可選，空列表表示不執行 RAG）
        persona_config: Persona 配置（可選，None 表示一般 Agent）
    
    Yields:
        SSE 格式事件
    """
    global llm_provider
    
    start_time = asyncio.get_event_loop().time()
    
    # ========== 多輪循環參數（三類架構） ==========
    max_rounds = 10
    round = 0
    tool_results = []
    agent_should_continue = True  # 指標 1：AGENT 還該不該繼續
    user_instruction_completed = False  # 指標 2：用戶指令有沒有完成
    conversation_history = []
    last_errors: Dict[str, str] = {}  # 記錄上一輪的錯誤 {tool_name: error_signature}
    last_tool_calls: List[str] = []  # 記錄上一輪的 tool calls 簽名 ["tool_name(args)"]
    round_timings = []  # 收集每輪時間統計
    execution_result: Optional[ExecutionResult] = None  # 三類執行結果
    
    # 獲取對話歷史（包含 tool 消息）
    try:
        session_data = session_store.get_session(request.session_id)
        if session_data:
            messages = session_data.get('messages', [])
            # 只取最近 10 條歷史（包含 user/assistant/tool）
            conversation_history = [m for m in messages[-10:] if m.get('role') in ['user', 'assistant', 'tool']]
            print(f"📚 獲取對話歷史：{len(conversation_history)} 條")
    except Exception as e:
        print(f"⚠️  獲取對話歷史失敗：{e}")
    
    # 時間戳（用於 UBICHAN v2.0 格式）
    created = int(start_time)
    event_id = f"{request.session_id}_{created}"
    
    # ========== 多輪循環開始 ==========
    while agent_should_continue and round < max_rounds:
        round += 1
        print(f"\n🔄 ========== 第 {round} 輪 ==========")
        
        # 階段 1: 組合 Prompt
        require_quick_response = (round == 1)
        
        # 方案 A：Native Function Calling
        # 組合 messages（System + 對話歷史 + 用戶輸入）
        system_prompt = build_system_prompt(
            round=round,
            tool_results=tool_results,
            require_quick_response=require_quick_response
        )
        
        # 組合完整 messages
        messages = [{"role": "system", "content": system_prompt}]
        if conversation_history:
            messages.extend(conversation_history[-10:])
        messages.append({"role": "user", "content": user_message})
        
        # 準備 Tool Schemas - 使用 TOOL_INSTANCES 中的所有 Tool
        tool_schemas = [build_tool_schema(tool) for tool in TOOL_INSTANCES.values()]
        
        # 階段 2: 呼叫 LLM（方案 A：Native Function Calling）
        llm_start = time.time()
        
        # 方案 A：Native Function Calling
        # 使用 chat_with_tools() 方法（支援 tools 參數）
        result = await llm_provider.chat_with_tools(
            messages=messages,
            tools=tool_schemas,
            use_reasoning=False,
            temperature=0
        )
        
        # 從 result 獲取 tool_calls 和 content
        tool_calls = result.get("tool_calls", [])
        llm_output = result.get("content", "")
        
        llm_time = int((time.time() - llm_start) * 1000)
        
        # 🔍 印出 LLM 完整回應結構
        print(f"🤖 LLM 完整回應結構:")
        print(f"   content: {repr(llm_output[:200] if llm_output else 'None')}...")
        print(f"   tool_calls: {len(tool_calls)} 個")
        for i, tc in enumerate(tool_calls):
            print(f"   [{i}] name={tc.get('name')}, args={json.dumps(tc.get('arguments', {}), ensure_ascii=False)[:100]}")
        
        # LLM 選擇的 Tool
        if tool_calls:
            tool_summary = ", ".join([tc.get('name', 'unknown') for tc in tool_calls])
            print(f"🤖 LLM 決策：調用 Tool[{tool_summary}]（Function Calling）")
        else:
            print(f"🤖 LLM 決策：無需 Tool，準備回應")
        
        print(f"💬 LLM 耗時：{llm_time}ms")
        
        # 階段 3: 解析結果（使用兩個新指標）
        quick_response = parse_quick_response(llm_output, round)
        agent_should_continue = parse_agent_should_continue(llm_output, has_tool_calls=(len(tool_calls) > 0))
        user_instruction_completed = parse_user_instruction_completed(llm_output)
        
        # 🔍 印出解析結果
        print(f"📋 解析結果:")
        print(f"   快速回應：{repr(quick_response)}")
        print(f"   AGENT 還要繼續：{agent_should_continue}")
        print(f"   用戶指令完成：{user_instruction_completed}")
        
        # LLM 對任務完成的分析
        if not agent_should_continue:
            if user_instruction_completed:
                print(f"✅ LLM 判斷：用戶指令完成，準備最終回應")
            else:
                print(f"🔄 LLM 判斷：需要用戶輸入，等待回答")
        else:
            print(f"🔄 LLM 判斷：AGENT 還要繼續，執行 Tool")
        
        # 階段 4: 發送快速回應（只有第 1 輪）
        if quick_response and round == 1:
            event = StreamEvent.create_text_chunk(
                message=quick_response,
                created=created,
                event_id=event_id
            )
            yield format_sse_event(event)
            print(f"⚡ 已發送快速回應")
        
        # 階段 5: 執行 Tools（如果有）
        tool_time = 0  # 初始化 Tool 時間
        
        if tool_calls:
            # 生成當前 tool calls 簽名
            current_tool_calls = [
                f"{tc.get('name')}({json.dumps(tc.get('arguments', {}), sort_keys=True)})"
                for tc in tool_calls
            ]
            
            # 檢測是否重複同樣的 tool calls → 執行異常
            if current_tool_calls == last_tool_calls and len(current_tool_calls) > 0:
                print(f"⚠️  檢測到重複的 Tool Calls，標記為執行異常")
                execution_result = ExecutionResult(
                    status=ExecutionStatus.ERROR,
                    error="重複的 Tool 調用",
                    result=tool_results if tool_results else None,
                    round_count=round,
                    tool_results=tool_results.copy()
                )
                break
            
            print(f"🔧 準備執行 {len(tool_calls)} 個 Tools")
            new_results, current_errors, should_stop = execute_tools(tool_calls, last_errors)
            tool_results.extend(new_results)
            last_errors = current_errors  # 更新錯誤記錄
            last_tool_calls = current_tool_calls  # 更新 tool calls 簽名
            
            # 🔍 印出 tool_results 詳細內容
            print(f"📋 Tool 執行結果:")
            for i, r in enumerate(new_results):
                if r['success']:
                    result_data = r.get('result', {})
                    if isinstance(result_data, dict) and 'data' in result_data:
                        data_preview = str(result_data['data'])[:150]
                        print(f"   [{i}] {r['tool_name']}: ✅ success, data={data_preview}...")
                    else:
                        print(f"   [{i}] {r['tool_name']}: ✅ success, result={str(result_data)[:150]}...")
                else:
                    print(f"   [{i}] {r['tool_name']}: ❌ error: {r.get('error', 'Unknown')}")
            
            # 如果檢測到同樣的錯誤，立即停止
            if should_stop:
                print(f"⚠️  同樣的錯誤再次發生，停止循環")
                break
            
            # 如果 Tool 執行失敗且沒有其他 tool_calls，強制結束
            if all(not r['success'] for r in new_results):
                print(f"⚠️  所有 Tool 執行失敗，強制結束")
                # 設定執行結果為 ERROR，確保會生成錯誤訊息給用戶
                execution_result = ExecutionResult(
                    status=ExecutionStatus.ERROR,
                    error="Tool 執行失敗，無法完成指令",
                    result=tool_results if tool_results else None,
                    round_count=round,
                    tool_results=tool_results.copy()
                )
                break
            
            # ✅ 新增：將 Tool Result 添加到 conversation_history 並持久化
            for i, result in enumerate(new_results):
                tool_call_id = tool_calls[i].get('id', f'tool_call_{round}_{i}')
                
                if result['success']:
                    # 成功：添加 tool 消息
                    tool_message = {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": json.dumps(result['result'], ensure_ascii=False)
                    }
                    conversation_history.append(tool_message)
                    print(f"   📝 已添加 tool 消息到 conversation_history: {result['tool_name']}")
                    
                    # 持久化到 Session Store
                    try:
                        session_store.add_message(
                            request.session_id,
                            'tool',
                            tool_message['content'],
                            tool_call_id=tool_call_id
                        )
                        print(f"   💾 已保存 tool 消息到 Session Store")
                    except Exception as e:
                        print(f"   ⚠️  保存 tool 消息失敗：{e}")
                else:
                    # 失敗：添加錯誤消息
                    error_message = {
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": f"Error: {result.get('error', 'Unknown')}"
                    }
                    conversation_history.append(error_message)
                    print(f"   📝 已添加 error 消息到 conversation_history: {result['tool_name']}")
                    
                    # 持久化錯誤消息
                    try:
                        session_store.add_message(
                            request.session_id,
                            'tool',
                            error_message['content'],
                            tool_call_id=tool_call_id
                        )
                        print(f"   💾 已保存 error 消息到 Session Store")
                    except Exception as e:
                        print(f"   ⚠️  保存 error 消息失敗：{e}")
            
            # 同時，將 assistant 的 tool_calls 也加入歷史並持久化
            # 注意：需要轉換為 OpenAI 標準格式
            openai_tool_calls = []
            for tc in tool_calls:
                openai_tool_calls.append({
                    "id": tc['id'],
                    "type": "function",
                    "function": {
                        "name": tc['name'],
                        "arguments": json.dumps(tc['arguments'], ensure_ascii=False)
                    }
                })
            
            assistant_message = {
                "role": "assistant",
                "content": llm_output if llm_output else "",
                "tool_calls": openai_tool_calls
            }
            conversation_history.append(assistant_message)
            print(f"   📝 已添加 assistant 消息到 conversation_history")
            
            # 持久化 assistant 消息
            try:
                session_store.add_message(
                    request.session_id,
                    'assistant',
                    assistant_message['content']
                )
                print(f"   💾 已保存 assistant 消息到 Session Store")
            except Exception as e:
                print(f"   ⚠️  保存 assistant 消息失敗：{e}")
            
            # 印出該輪時間統計
            print(f"📊 第 {round} 輪統計：LLM={llm_time}ms | Tool={tool_time}ms")
            
            # 收集該輪時間（不發送，最後在 done 中一起發送）
            round_timings.append({
                "round": round,
                "llm_ms": llm_time,
                "tool_ms": tool_time
            })
        else:
            # 印出該輪時間統計（沒有 Tool）
            print(f"📊 第 {round} 輪統計：LLM={llm_time}ms")
            
            # 收集該輪時間（沒有 Tool）
            round_timings.append({
                "round": round,
                "llm_ms": llm_time,
                "tool_ms": 0
            })
        
        # 階段 6: 檢查執行結果（三分類）
        if not agent_should_continue:
            if user_instruction_completed:
                # 情況 A: 用戶目標完成 → DONE
                print(f"✅ 用戶指令完成，標記為 DONE")
                execution_result = ExecutionResult(
                    status=ExecutionStatus.DONE,
                    result=tool_results if tool_results else llm_output,
                    round_count=round,
                    tool_results=tool_results.copy()
                )
                break
            else:
                # 情況 B: 需要用戶介入 → NEEDS_INTERACTION
                print(f"🔄 需要用戶介入，標記為 NEEDS_INTERACTION")
                execution_result = ExecutionResult(
                    status=ExecutionStatus.NEEDS_INTERACTION,
                    user_prompt=clean_llm_output(llm_output),
                    round_count=round,
                    tool_results=tool_results.copy()
                )
                break
        
        # 檢查輪數 → 執行異常
        if round >= max_rounds:
            print(f"⚠️  達到最大輪數 {max_rounds}，標記為執行異常")
            execution_result = ExecutionResult(
                status=ExecutionStatus.ERROR,
                error=f"超過最大輪數限制 ({max_rounds})",
                result=tool_results if tool_results else None,
                round_count=round,
                tool_results=tool_results.copy()
            )
            break
    
    # ========== 生成最終回應（三分類架構） ==========
    full_response = ""
    
    if execution_result is not None:
        print(f"\n📤 生成最終回應（狀態：{execution_result.status.value}）")
        
        # 根據執行狀態建構不同的 Prompt
        if execution_result.status == ExecutionStatus.DONE:
            # 情況 A: 用戶目標完成
            if execution_result.warning:
                final_prompt = f"""你已經完成了用戶的指令，但有一些注意事項。

## 用戶問題
{user_message}

## 執行結果
{json.dumps(execution_result.result, ensure_ascii=False, indent=2) if execution_result.result else "無"}

## 注意事項
{execution_result.warning}

## 回應要求
1. 用繁體中文生成完整的回應
2. 總結執行結果
3. 說明注意事項
4. 保持回應自然流暢
"""
            else:
                final_prompt = f"""你已經成功完成用戶的指令。

## 用戶問題
{user_message}

## 執行結果
{json.dumps(execution_result.result, ensure_ascii=False, indent=2) if execution_result.result else "無"}

## 回應要求
1. 用繁體中文生成完整的回應
2. 總結執行結果
3. 保持回應自然流暢
"""
        
        elif execution_result.status == ExecutionStatus.NEEDS_INTERACTION:
            # 情況 B: 需要用戶介入
            final_prompt = f"""你需要用戶介入才能繼續。

## 用戶原始問題
{user_message}

## 需要用戶
{execution_result.user_prompt}

## 回應要求
1. 用繁體中文將問題轉達給用戶
2. 解釋為什麼需要這個資訊
3. 說明需要什麼樣的介入（提供資訊、確認、選擇、授權等）
4. 保持語氣友好
"""
        
        else:  # ERROR
            # 情況 C: 執行異常
            if execution_result.result:
                final_prompt = f"""處理過程中遇到問題，但已獲得部分結果。

## 用戶問題
{user_message}

## 錯誤說明
{execution_result.error}

## 已獲得的結果
{json.dumps(execution_result.result, ensure_ascii=False, indent=2)}

## 回應要求
1. 用繁體中文解釋發生的問題
2. 提供已獲得的結果
3. 建議用戶下一步可以做什麼
"""
            else:
                final_prompt = f"""無法完成用戶的指令。

## 用戶問題
{user_message}

## 錯誤說明
{execution_result.error}

## 回應要求
1. 用繁體中文解釋原因，語氣要友善
2. 如果是 Tool 執行失敗，說明可能是技術問題
3. 建議用戶：
   - 重試一次
   - 檢查指令是否明確
   - 如果問題持續，聯絡開發人員並提供錯誤資訊
4. 保持專業且樂於助人的態度
"""
        
        # STREAM 模式呼叫 LLM 生成最終回應
        chunker = BlockChunker(min_chars=STREAM_MIN_CHARS, max_chars=STREAM_MAX_CHARS)
        llm_final_start = asyncio.get_event_loop().time()
        
        # ⭐ 如果第 1 輪有快速回應，在最終回應前添加換行
        first_final_chunk = True
        has_quick_response = quick_response and (round == 1)
        
        try:
            async for chunk in llm_provider.chat_stream(
                messages=[{"role": "user", "content": final_prompt}],
                use_reasoning=False,
                temperature=0.7
            ):
                if chunker.should_send(chunk):
                    chunk_text = chunker.get_chunk(chunk)
                    # 在第一個最終回應 chunk 前添加換行（分隔快速回應和正式回應）
                    if first_final_chunk and has_quick_response:
                        chunk_text = "\n\n" + chunk_text
                        first_final_chunk = False
                    full_response += chunk_text
                    try:
                        event = StreamEvent.create_text_chunk(
                            message=chunk_text,
                            created=created,
                            event_id=event_id
                        )
                        yield format_sse_event(event)
                    except Exception as e:
                        print(f"⚠️  SSE 事件序列化失敗：{e}")
                        clean_chunk = chunk_text.replace('\n', '\\n').replace('\r', '\\r').replace('"', '\\"')
                        event = StreamEvent.create_text_chunk(
                            message=clean_chunk,
                            created=created,
                            event_id=event_id
                        )
                        yield format_sse_event(event)
            
            # 發送剩餘內容
            if chunker.has_remaining():
                remaining = chunker.get_remaining()
                # 如果還沒有發送過最終回應（所有內容都在 remaining 中），添加換行
                if first_final_chunk and has_quick_response:
                    remaining = "\n\n" + remaining
                    first_final_chunk = False
                full_response += remaining
                event = StreamEvent.create_text_chunk(
                    message=remaining,
                    created=created,
                    event_id=event_id
                )
                yield format_sse_event(event)
            
            llm_final_time = int((asyncio.get_event_loop().time() - llm_final_start) * 1000)
            print(f"💬 最終回應生成：{llm_final_time}ms")
            
        except Exception as e:
            import traceback
            print(f"⚠️  最終回應生成失敗：{e}")
            print(f"🔍 異常堆疊：{traceback.format_exc()}")
        
        # 保存到 Session
        if request.session_id and full_response:
            try:
                session_store.add_message(request.session_id, "assistant", full_response)
                print(f"✅ 已保存助手回复到 Session: {request.session_id} ({len(full_response)} 字)")
            except Exception as e:
                print(f"⚠️  保存 Session 失敗：{e}")
    else:
        # 沒有執行結果（不應發生）
        print(f"\n⚠️  警告：沒有執行結果，不生成最終回應")
    
    # ========== Done 事件 ==========
    total_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
    
    event = StreamEvent.create_done(
        created=created,
        event_id=event_id,
        timing={
            "total_ms": total_time,
            "rounds": round,
            "tools_executed": len(tool_results),
            "round_details": round_timings,  # 每輪時間明細
            "execution_status": execution_result.status.value if execution_result else "none",  # 三類狀態
            "has_result": execution_result.result is not None if execution_result else False,
            "has_error": execution_result.error is not None if execution_result else False,
        }
    )
    yield format_sse_event(event)
    
    print(f"📊 Session: {request.session_id} | 輪數：{round} | Tools: {len(tool_results)} | 總時間：{total_time}ms")
    if execution_result:
        print(f"📊 執行狀態：{execution_result.status.value}")
        if execution_result.error:
            print(f"   錯誤：{execution_result.error}")
        if execution_result.user_prompt:
            print(f"   用戶介入：{execution_result.user_prompt[:100]}...")
    
@app.post("/chat")
async def chat(request: ChatRequest):
    """
    聊天端點 - 僅支援 STREAM 模式
    
    Args:
        request: ChatRequest
    
    Returns:
        StreamingResponse: SSE 格式回應
    """
    global llm_provider
    
    # ⭐ 所有請求都使用 STREAM 模式
    # 非 STREAM 模式已移除（保留參考見 git history）
    
    user_message = request.messages[-1]["content"] if request.messages else ""
    
    return StreamingResponse(
        generate_stream(
            request=request,
            user_message=user_message,
            tools=TOOLS,
            knowledge_ids=["ubitus"],  # 可配置
            persona_config=None
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
    
    # ========================================================================
    # ⚠️ 非 STREAM 模式已移除（保留參考）
    # ========================================================================
    # 歷史代碼見 git commit bf3e715
    # 
    # 移除原因：
    # 1. 維護兩套邏輯複雜且容易出錯
    # 2. STREAM 模式體驗更好（即時回應）
    # 3. 前端已統一使用 STREAM
    # 
    # 如果需要非 STREAM 模式，請參考 git history
    # ========================================================================

# ========================================================================
# ⚠️ /chat/stream 端點已移除
# ========================================================================
# 歷史代碼見 git commit 4857825
# 
# 移除原因：
# 1. 與 /chat 端點功能重複
# 2. 統一使用單一 STREAM 端點
# 3. 避免混淆
# 
# 如果需要參考，請查看 git history
# ========================================================================

# ============= 主程式 =============
if __name__ == "__main__":
    uvicorn.run(
        "backend_operator.api:app",
        host="0.0.0.0",
        port=8000,
        reload=False
    )
