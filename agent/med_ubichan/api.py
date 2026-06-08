"""
API 端點 - 醫療展 Virtual Human Agent (UbiChan × 小護士)

提供醫療展專用的 /sessions 和 /chat 端點，支持雙機器人協作：
- UbiChan：虛擬人（Kiosk 螢幕）- 對話接待、需求判斷、指令下達
- 小護士：引導機器人（地面）- 帶路引導、物品運送、現場互動

根據 MED_UBIAGENT 規格文檔 v1.0 實現
"""

# 設置 Log 導向（必須在 import 其他模組之前）
from log_redirector import setup_logging
setup_logging("med_ubichan")

from fastapi import APIRouter, HTTPException, FastAPI, Cookie
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
import asyncio
import json
import time
import os

# 流式模組
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / 'shared'))
from sse_events import StreamEvent, format_sse_event
from block_chunker import BlockChunker

# Tools 模組（添加到 Python path）
sys.path.insert(0, str(Path(__file__).parent.parent / 'tools'))

# 醫療展專用模組
from config_loader import MedUbiConfigLoader
from output_formatter import MedUbiOutputFormatter
# Prompt Builder 和 LLM Service
from prompt_builder import MedUbiPromptBuilder, MedUbiOutputParser, PromptLoader
from llm_service import MedUbiLLMService, create_llm_service
# Device Service
from device_service import DeviceService, send_intent_to_device
import json as json_module


def format_med_ubichan_sse(event_dict: dict) -> str:
    """
    格式化醫療展專用 SSE 事件（支持 dict，符合 10_SSE_OUTPUT_SPEC.md）

    Args:
        event_dict: 事件字典 {event, message, created, id, timing, ...}

    Returns:
        str: SSE 格式字串
    """
    # 直接序列化整個 event_dict（扁平結構）
    data_json = json_module.dumps(event_dict, ensure_ascii=False, separators=(',', ':'))
    return f"event: {event_dict['event']}\ndata: {data_json}\n\n"


# 這些會在 agent-api-streaming.py 中初始化
# config_loader = None
# session_store = None
# llm_service = None

router = APIRouter()


# ============= 請求/回應模型 =============

class CreateSessionRequest(BaseModel):
    """創建 Session 請求"""
    persona_id: str
    metadata: Optional[Dict[str, Any]] = None


class CreateSessionResponse(BaseModel):
    """創建 Session 回應"""
    session_id: str
    persona_id: str
    created_at: str


class ChatRequest(BaseModel):
    """Chat 請求"""
    input: Optional[str] = None
    message: Optional[str] = None
    messages: Optional[list] = None

    def get_message(self) -> str:
        """取得用戶消息（支持 input, message 或 messages 格式）"""
        # 優先使用 input（curl 測試格式）
        if self.input:
            return self.input
        # 其次使用 message
        if self.message:
            return self.message
        # 最後使用 messages（對話格式）
        if self.messages and len(self.messages) > 0:
            for msg in reversed(self.messages):
                if msg.get('role') == 'user':
                    return msg.get('content', '')
        return ''


class ChatResponse(BaseModel):
    """Chat 回應"""
    session_id: str
    response: str
    emotion: Optional[str] = None
    lang: Optional[str] = None
    persona_id: str
    robot_action: Optional[Dict[str, Any]] = None  # 小護士 Action
    robot_steps_desc: Optional[str] = None  # 自然語言步驟描述（Steps_Descripts）
    timings: Optional[Dict[str, Any]] = None
    usage: Optional[Dict[str, Any]] = None


# ============= 全局變數 =============
# Prompt 構建器和解析器
prompt_builder: Optional[MedUbiPromptBuilder] = None
output_parser: Optional[MedUbiOutputParser] = None

# LLM 服務
llm_service: Optional[MedUbiLLMService] = None

# 配置載入器
config_loader: Optional[MedUbiConfigLoader] = None

# Prompt Loader
prompt_loader: Optional[PromptLoader] = None


# ============= Lifespan 上下文管理器 =============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI 應用生命週期管理

    啟動時：初始化醫療展 API（LLM 服務、Prompt Builder 等）
    關閉時：清理資源
    """
    # ===== 啟動時初始化 =====
    print("🚀 初始化醫療展 Virtual Human API...")

    # 從環境變數讀取配置
    workspace_path = Path(os.getenv("WORKSPACE_PATH", "/workspace"))
    api_key = os.getenv("UBILM_API_KEY")
    llm_model = os.getenv("UBILM_LLM_MODEL", "qwen3-8b-fp8")

    print(f"   Workspace: {workspace_path}")
    print(f"   API Key: {'***' + api_key[-6:] if api_key else '未設置'}")
    print(f"   LLM Model: {llm_model}")

    # 初始化配置載入器
    config_loader_obj = MedUbiConfigLoader()

    # 初始化醫療展 API
    init_med_ubichan_api(
        config_loader_obj=config_loader_obj,
        workspace_path=workspace_path,
        api_key=api_key,
        model=llm_model
    )

    print("✅ 醫療展 Virtual Human API 初始化完成")

    yield

    # ===== 關閉時清理 =====
    print("👋 關閉醫療展 Virtual Human API...")
    # 如有需要清理的資源，在這裡處理

async def generate_med_ubichan_stream(
    request: ChatRequest,
    session_id: str,
    persona_config: dict,
    session_store,
    robot_state: str = "available",
    chat_start_time: float = None
):
    """
    醫療展 Virtual Human STREAM 生成器（純 LLM 版）

    流程：
    1. 使用 LLM 生成完整回應（UbiChan + 小護士 Steps）
    2. STREAM 發送

    Args:
        request: ChatRequest
        session_id: Session ID（從 Cookie 傳來）
        persona_config: 醫療展 Persona 配置
        session_store: Session Store 實例
        robot_state: 小護士設備狀態（available | busy | unknown）
        chat_start_time: chat() API 被呼叫的時間戳（用於計算總時間）

    Yields:
        SSE 格式事件
    """
    global prompt_builder

    # 如果有傳入 chat_start_time，則使用它；否則使用當前時間
    if chat_start_time:
        start_time = chat_start_time
    else:
        start_time = asyncio.get_event_loop().time()
    
    user_message = request.get_message()

    # 獲取時間戳
    created = int(start_time)
    event_id = f"{session_id}_{created}"

    # ========== 階段 1: 使用 LLM 生成完整回應 ==========
    print("📝 階段 1: 使用 LLM 生成完整回應")
    llm_start = time.time()

    # 獲取對話歷史
    conversation_history = session_store.get_messages(session_id)

    # 獲取知識庫內容（根據 persona_config 的 knowledge 設定）
    knowledge_content = None
    knowledge_meta = None
    
    # 檢查是否啟用知識庫
    if persona_config.get('knowledge', {}).get('enabled', False):
        try:
            from pathlib import Path
            from agent.virtual_human.knowledge.retriever import KnowledgeRetriever
            
            # 獲取知識庫資料夾列表
            knowledge_folders = persona_config.get('knowledge', {}).get('folders', [])
            
            if knowledge_folders:
                # 使用 MultiKnowledgeRetriever 檢索多個知識庫
                from agent.virtual_human.knowledge.retriever import MultiKnowledgeRetriever
                
                # 獲取 workspace 路徑
                workspace_path = prompt_builder.workspace_path if prompt_builder else Path("/workspace")
                knowledge_base_path = workspace_path / "knowledge"
                
                # 創建多知識庫檢索器
                multi_retriever = MultiKnowledgeRetriever(
                    knowledge_ids=knowledge_folders,
                    base_path=str(knowledge_base_path),
                    llm_client=llm_service
                )
                
                # 執行檢索
                print(f"🔍 檢索知識庫：{knowledge_folders}")
                rag_result = multi_retriever.query(user_message)
                
                knowledge_content = rag_result.get("content", "")
                knowledge_meta = rag_result.get("files", [])
                
                if knowledge_content:
                    print(f"✅ 知識庫檢索成功：{len(knowledge_content)} 字，使用文件：{knowledge_meta}")
                else:
                    print(f"⚠️ 知識庫檢索無相關內容")
                    
        except Exception as e:
            print(f"⚠️ 知識庫檢索失敗：{e}")
            # 不中斷流程，繼續處理

    # 調用 LLM 生成（LLM 自行判斷意圖，並根據小護士狀態決定是否可以指派任務）
    llm_result = await generate_response_with_llm(
        user_message=user_message,
        conversation_history=conversation_history,
        persona_config=persona_config,
        workspace_path=prompt_builder.workspace_path if prompt_builder else None,
        prompt_loader_obj=prompt_loader,
        knowledge_content=knowledge_content,
        knowledge_meta=knowledge_meta,
        is_llm1=False,
        robot_state=robot_state
    )

    llm_time = int((time.time() - llm_start) * 1000)

    # ========== 階段 2: 處理 LLM 結果 ==========
    if not llm_result["success"]:
        print(f"❌ LLM 生成失敗：{llm_result['error']}")
        # 發送 error 事件
        error_event = {
            "event": "error",
            "error": llm_result['error'],
            "created": created,
            "id": event_id
        }
        yield format_med_ubichan_sse(error_event)
        return

    print(f"✅ LLM 生成成功 ({llm_time}ms)")

    ubichan_output = llm_result["ubichan_output"]
    robot_steps_desc = llm_result["robot_steps_descripts"]

    # 替換特殊字元：&lt;&lt; → &lt;, &gt;&gt; → &gt;
    if ubichan_output:
        ubichan_output = ubichan_output.replace("&lt;&lt;", "&lt;").replace("&gt;&gt;", "&gt;")

    # ========== 階段 1.5: 保存用戶消息到 Session（LLM 成功後） ==========
    try:
        session_store.add_message(session_id, "user", user_message)
        print(f"✅ 已保存用戶消息到 Session: {session_id}")
    except Exception as e:
        print(f"⚠️ 保存用戶消息失敗：{e}")
        # 不中斷流程，繼續處理

    # ========== 階段 2: 發送 UbiChan 回應（text_chunk 格式） ==========
    print(f"🦐 發送 UbiChan: {ubichan_output[:50]}...")

    # 發送 text_chunk 事件
    text_chunk_event = {
        "event": "text_chunk",
        "message": ubichan_output,
        "created": created,
        "id": event_id
    }
    yield format_med_ubichan_sse(text_chunk_event)

    # ========== 階段 3: 發送 steps_description 到小護士設備 ==========
    if robot_steps_desc:
        print("🚀 階段 3: 發送 steps_description 到小護士設備")
        try:
            device_result = await send_intent_to_device(steps_description=robot_steps_desc)
            print(f"✅ 小護士 Intent 發送成功：{device_result}")
        except Exception as e:
            print(f"⚠️ 小護士 Intent 發送失敗：{e}")
            # 不中斷流程，僅記錄錯誤

    # ========== 階段 4: 發送 done 事件（含 [DONE] 標記） ==========
    total_time_seconds = time.time() - start_time
    done_event = {
        "event": "done",
        "created": created,
        "id": event_id,
        "timing": {
            "llm_ms": llm_time,
            "total_s": round(total_time_seconds, 3)
        }
    }
    yield format_med_ubichan_sse(done_event)

    # 發送 [DONE] 標記
    yield "data: [DONE]\n\n"

    # 保存助手回應到 Session（用戶消息已在前面保存）
    try:
        assistant_response = {
            "ubichan": ubichan_output
        }
        session_store.add_message(
            session_id,
            "assistant",
            json.dumps(assistant_response, ensure_ascii=False)
        )
        print(f"✅ 已保存助手回應到 Session: {session_id}")
    except Exception as e:
        print(f"⚠️ 保存助手回應失敗：{e}")

    print(f"📊 Session: {session_id} | TIMING: total={round(total_time_seconds, 3)}s")


# ============= API 端點 =============

@router.post("/session", response_model=CreateSessionResponse)
async def create_session(request: CreateSessionRequest):
    """
    創建新 Session（綁定醫療展 persona_id）

    前端在開始對話前，先創建 Session 並綁定虛擬人。
    使用 SQLite SessionStore 持久化存儲。
    """
    global config_loader

    # 驗證 persona_id
    config = config_loader.get(request.persona_id)
    if not config:
        raise HTTPException(
            status_code=400,
            detail=f"未知的醫療展虛擬人 ID: {request.persona_id}"
        )

    # 創建 Session
    from session.session_store import get_session_store
    session_store = get_session_store('/data/sessions.db')

    session = session_store.create_session(
        prefix=request.persona_id,
        metadata={
            "vh_char_config": {
                "persona_id": request.persona_id,
                "character_version": config.get('version', 'v1.0'),
                "spec": "MED_UBIAGENT"
            }
        },
        ttl_hours=24
    )

    return CreateSessionResponse(
        session_id=session['session_id'],
        persona_id=request.persona_id,
        created_at=session['created_at']
    )


@router.post("/chat", response_model=None)
async def chat(request: ChatRequest, session_id: str = Cookie(None)):
    """
    Chat 端點 - 醫療展 Virtual Human（STREAM 模式）

    流程:
    1. 從 Cookie 取得 session_id
    2. 從 Session Store 取得 Session 內容
    3. 從 metadata 獲取 vh_char_config
    4. 取得 persona_id
    5. 載入醫療展配置
    6. 檢查小護士設備狀態
    7. 意圖分類
    8. 生成 UbiChan 回應 + 小護士 Action
    9. 返回 STREAM 回應

    Args:
        request: ChatRequest
        session_id: 從 Cookie 傳來的 session_id

    Returns:
        StreamingResponse: SSE 格式回應
    """
    global config_loader

    # 1. 從 Cookie 取得 session_id
    if not session_id:
        raise HTTPException(status_code=400, detail="缺少 session_id Cookie")

    # 2. 從 Session Store 取得 Session 內容
    try:
        from session.session_store import get_session_store
        session_store = get_session_store('/data/sessions.db')
        session_data = session_store.get_session(session_id)

        if not session_data:
            raise HTTPException(status_code=404, detail="Session 不存在")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Session 讀取失敗：{str(e)}")

    # 2. 從 metadata 獲取 vh_char_config
    metadata = session_data.get('metadata')
    vh_char_config = None
    persona_id = None

    if metadata:
        vh_char_config = metadata.get('vh_char_config')
        if vh_char_config:
            persona_id = vh_char_config.get('persona_id')

    # 3. 載入醫療展配置
    if not persona_id or not persona_id.startswith('med_'):
        raise HTTPException(
            status_code=400,
            detail="Session 未綁定醫療展虛擬人"
        )

    config = config_loader.get(persona_id)
    if not config:
        raise HTTPException(
            status_code=400,
            detail=f"未知的醫療展虛擬人：{persona_id}"
        )

    # 4. 檢查小護士設備狀態（將狀態傳入 prompt_builder，讓 LLM 決定如何處理）
    print("🔍 檢查小護士設備狀態...")
    robot_state = "unknown"  # 預設為 unknown
    try:
        from device_service import DeviceService
        device_service = DeviceService()
        device_status = await device_service.get_device_status()
        print(f"📊 小護士狀態：{device_status}")

        # 預期格式：{"deviceSN":"medical2026-test-001","status":{"state":"busy"}}
        robot_state = device_status.get('status', {}).get('state', 'unknown')
        print(f"✅ 小護士狀態：{robot_state}")

    except Exception as e:
        print(f"⚠️ 檢查小護士狀態失敗：{e}")
        robot_state = "unknown"

    # 5. 記錄開始時間（用於計算總時間）
    chat_start_time = time.time()

    # 6. 返回 STREAM 回應（用戶消息將在 generate_med_ubichan_stream() 成功後保存，並傳入 robot_state 和 chat_start_time）
    return StreamingResponse(
        generate_med_ubichan_stream(
            request=request,
            session_id=session_id,
            persona_config=config,
            session_store=session_store,
            robot_state=robot_state,
            chat_start_time=chat_start_time
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============= Health Check 端點 =============

@router.get("/health")
async def health_check():
    """
    Health Check 端點

    Returns:
        dict: 健康狀態
    """
    return {
        "status": "healthy",
        "service": "med_ubichan",
        "version": "1.0.0"
    }


# ============= 初始化函數 =============

def init_med_ubichan_api(
    config_loader_obj: MedUbiConfigLoader,
    llm_service_obj=None,
    workspace_path: Path = None,
    api_key: str = None,
    model: str = "qwen3-8b-fp8"
):
    """
    初始化醫療展 API

    在 Server 啟動時調用，注入依賴。

    Args:
        config_loader_obj: 醫療展配置載入器
        llm_service_obj: LLM 服務（可選，如果為 None 則自動創建）
        workspace_path: Workspace 路徑（可選）
        api_key: UbiLM API Key（可選，從環境變數讀取）
        model: LLM 模型名稱
    """
    global config_loader, formatter, llm_service, prompt_builder, output_parser, prompt_loader

    config_loader = config_loader_obj
    formatter = MedUbiOutputFormatter()

    # 初始化 LLM 服務
    if llm_service_obj:
        llm_service = llm_service_obj
    elif workspace_path:
        llm_service = create_llm_service(
            api_key=api_key,
            model=model,
            workspace_path=workspace_path
        )
        print(f"✅ LLM 服務已初始化 (model={model})")

    # 初始化 Prompt 構建器和解析器
    if workspace_path:
        prompt_builder = MedUbiPromptBuilder(workspace_path)
        output_parser = MedUbiOutputParser()
        print(f"✅ Prompt 構建器和解析器已初始化")

    # 初始化 Prompt Loader
    if workspace_path:
        prompt_loader = PromptLoader(workspace_path)
        print(f"✅ Prompt Loader 已初始化")

    print(f"✅ 醫療展 API 初始化完成")
    print(f"   - 支持 persona: {config_loader.get_all_ids()}")
    print(f"   - 支持 Intent: registration, pharmacy, cancel, info_location")
    print(f"   - LLM 生成模式：{'啟用' if (prompt_builder and llm_service) else '未啟用'}")


# ============= LLM 回應生成器 =============

async def generate_response_with_llm(
    user_message: str,
    conversation_history: list,
    persona_config: dict,
    workspace_path: Path,
    prompt_loader_obj,
    knowledge_content: str = None,
    knowledge_meta: str = None,
    is_llm1: bool = False,
    robot_state: str = "available"
) -> Dict[str, Any]:
    """
    使用 LLM 生成完整的 UbiChan + 小護士 回應

    流程：
    1. 構建 Prompt
    2. 調用 LLM（使用 MedUbiLLMService）
    3. 解析 LLM 輸出
    4. 驗證格式

    Args:
        user_message: 用戶消息
        conversation_history: 對話歷史
        persona_config: Persona 配置
        workspace_path: Workspace 路徑
        prompt_loader_obj: PromptLoader 實例
        knowledge_content: 知識庫內容
        knowledge_meta: 知識庫 Meta
        is_llm1: 是否為 LLM1
        robot_state: 小護士設備狀態（available | busy | unknown）

    Returns:
        {
            "success": bool,
            "ubichan_output": str,
            "robot_steps_descripts": str,
            "error": str or None
        }
    """
    global prompt_builder, output_parser, llm_service

    try:
        # 1. 構建 Prompt
        print("📝 構建 Prompt...")
        prompt, emotion_enabled = await prompt_builder._build_prompt(
            config=persona_config,
            user_message=user_message,
            conversation_history=conversation_history,
            prompt_loader_obj=prompt_loader_obj,
            knowledge_content=knowledge_content,
            knowledge_meta=knowledge_meta,
            is_llm1=is_llm1,
            robot_state=robot_state
        )

        # 2. 調用 LLM
        print("🤖 調用 LLM...")

        if llm_service and hasattr(llm_service, 'generate_med_ubichan_response'):
            result = await llm_service.generate_med_ubichan_response(
                prompt=prompt,
                conversation_history=conversation_history,
                temperature=0.7,
                max_tokens=2048
            )

            if not result['success']:
                return {
                    "success": False,
                    "ubichan_output": None,
                    "robot_steps_descripts": None,
                    "error": result['error']
                }

            parsed_data = result['parsed']
        else:
            llm_response = await llm_service.chat_async(
                messages=[
                    {"role": "system", "content": "你是一個醫療展 Virtual Human 助手"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            parsed_data = output_parser.parse_llm_response(llm_response)

            if not parsed_data["success"]:
                return {
                    "success": False,
                    "ubichan_output": None,
                    "robot_steps_descripts": None,
                    "error": parsed_data["error"]
                }

        # 3. 提取數據（無需額外驗證）
        ubichan_content = parsed_data["ToUbiChan"]

        return {
            "success": True,
            "ubichan_output": ubichan_content,
            "robot_steps_descripts": parsed_data["ToBaxiaomi"].get("Steps_Descripts"),
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "ubichan_output": None,
            "robot_steps": None,
            "robot_steps_descripts": None,
            "error": str(e)
        }



# ============= FastAPI 應用實例 =============

# 創建 FastAPI 應用（帶 lifespan）
app = FastAPI(
    title="醫療展 Virtual Human API",
    description="UbiChan × 小護士 雙機器人協作系統",
    version="1.0.0",
    lifespan=lifespan
)

# 註冊 router
app.include_router(router, prefix="/med_ubichan", tags=["med_ubichan"])


# ============= 主程式入口 =============

if __name__ == "__main__":
    import argparse
    import uvicorn

    parser = argparse.ArgumentParser()
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=3007)
    args = parser.parse_args()

    print(f"🚀 啟動醫療展 Virtual Human API 服務")
    print(f"   Host: {args.host}")
    print(f"   Port: {args.port}")
    print(f"\n📖 API 端點:")
    print(f"   POST /med_ubichan/session - 創建 Session")
    print(f"   POST /med_ubichan/chat - Chat（STREAM 模式）")
    print(f"\n🔧 測試指令:")
    print(f"   # 創建 Session")
    print(f"   curl -X POST http://localhost:{args.port}/med_ubichan/session \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -d '{{\"persona_id\": \"med-ubichan\"}}'")
    print(f"\n   # Chat 測試")
    print(f"   curl -X POST http://localhost:{args.port}/med_ubichan/chat \\")
    print(f"     -H 'Content-Type: application/json' \\")
    print(f"     -d '{{\"session_id\": \"<session_id>\", \"message\": \"掛號處在哪？\"}}'")
    print(f"\n{'='*60}\n")

    uvicorn.run(app, host=args.host, port=args.port)
