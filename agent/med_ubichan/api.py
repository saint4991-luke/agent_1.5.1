"""
API 端點 - 醫療展 Virtual Human Agent (UbiChan × 豹小秘)

提供醫療展專用的 /sessions 和 /chat 端點，支持雙機器人協作：
- UbiChan：虛擬人（Kiosk 螢幕）— 對話接待、需求判斷、指令下達
- 豹小秘：引導機器人（地面）— 帶路引導、物品運送、現場互動

根據 MED_UBIAGENT 規格文檔 v1.0 實現
"""

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
from .config_loader import MedUbiConfigLoader
from .output_formatter import MedUbiOutputFormatter
from .robot_action_generator import RobotActionGenerator, RobotAction
# Prompt Builder 和 LLM Service
from .prompt_builder import MedUbiPromptBuilder, MedUbiOutputParser, PromptLoader
from .llm_service import MedUbiLLMService, create_llm_service


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
    message: Optional[str] = None
    messages: Optional[list] = None
    
    def get_message(self) -> str:
        """取得用戶消息（支持 message 或 messages 格式）"""
        if self.message:
            return self.message
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
    robot_action: Optional[Dict[str, Any]] = None  # 豹小秘 Action
    robot_steps: Optional[str] = None  # 自然語言步驟
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
    session_store
):
    """
    醫療展 Virtual Human STREAM 生成器（純 LLM 版）
    
    流程：
    1. 使用 LLM 生成完整回應（UbiChan + 豹小秘 Steps）
    2. STREAM 發送
    
    Args:
        request: ChatRequest
        session_id: Session ID（從 Cookie 傳來）
        persona_config: 醫療展 Persona 配置
        session_store: Session Store 實例
    
    Yields:
        SSE 格式事件
    """
    global prompt_builder
    
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
    
    # 獲取知識庫內容（如果需要）
    knowledge_content = None
    knowledge_meta = None
    # TODO: 根據 persona_config 載入知識庫
    
    # 調用 LLM 生成（不傳 intent_result，讓 LLM 自行判斷）
    llm_result = await generate_response_with_llm(
        user_message=user_message,
        conversation_history=conversation_history,
        persona_config=persona_config,
        intent_result=None,  # 讓 LLM 自行判斷意圖
        workspace_path=prompt_builder.workspace_path if prompt_builder else None,
        prompt_loader_obj=prompt_loader,  # ← 使用正確的對象
        knowledge_content=knowledge_content,
        knowledge_meta=knowledge_meta,
        is_llm1=False
    )
    
    llm_time = int((time.time() - llm_start) * 1000)
    
    # ========== 階段 2: 處理 LLM 結果 ==========
    if not llm_result["success"]:
        print(f"❌ LLM 生成失敗：{llm_result['error']}")
        # 直接返回錯誤
        event = {
            "id": f"{event_id}_error",
            "event": "error",
            "data": {
                "session_id": request.session_id,
                "error": llm_result['error']
            }
        }
        yield format_sse_event(event)
        return
    
    print(f"✅ LLM 生成成功 ({llm_time}ms)")
    
    ubichan_output = llm_result["ubichan_output"]
    robot_steps = llm_result["robot_steps"]
    robot_steps_desc = llm_result["robot_steps_descripts"]
    
    # 發送 UbiChan 回應
    print(f"🦐 發送 UbiChan: {ubichan_output[:50]}...")
    event = {
        "id": f"{event_id}_ubichan",
        "event": "ubichan_response",
        "data": {
            "session_id": request.session_id,
            "text": ubichan_output,
            "emotion": "neutral",
            "lang": "tw",
            "timing": {
                "llm_ms": llm_time
            }
        }
    }
    yield format_sse_event(event)
    
    # 發送豹小秘 Steps（如果有）
    if robot_steps:
        print(f"🤖 發送豹小秘 Steps: {len(robot_steps)} 個步驟")
        event = {
            "id": f"{event_id}_robot",
            "event": "robot_action",
            "data": {
                "session_id": request.session_id,
                "steps": robot_steps,
                "steps_description": robot_steps_desc
            }
        }
        yield format_sse_event(event)
    
    # 保存對話到 Session
    try:
        session_store.add_message(request.session_id, "user", user_message)
        
        assistant_response = {
            "ubichan": ubichan_output,
            "robot_steps": robot_steps,
            "robot_steps_desc": robot_steps_desc
        }
        session_store.add_message(
            request.session_id,
            "assistant",
            json.dumps(assistant_response, ensure_ascii=False)
        )
        print(f"✅ 已保存對話到 Session: {request.session_id}")
    except Exception as e:
        print(f"⚠️ 保存 Session 失敗：{e}")
    
    # 計算總時間
    total_time = int((time.time() - start_time) * 1000)
    print(f"📊 Session: {request.session_id} | TIMING: total={total_time}ms")


async def _generate_ubichan_response(
    intent: str,
    user_message: str,
    target_location: Optional[str] = None
) -> tuple[str, str]:
    """
    根據 Intent 生成 UbiChan 回應
    
    Args:
        intent: Intent 類型
        user_message: 用戶消息
        target_location: 目標地點（可選）
    
    Returns:
        (回應文字，情緒標籤)
    """
    # 醫療展專用回應模板
    responses = {
        "registration": (
            "好的，豹小秘會帶你去掛號處。<sbr>請跟著它走。<sbr>",
            "happy"
        ),
        "pharmacy": (
            "你在這裡休息一下。<sbr>我請豹小秘去幫你拿藥。<sbr>很快就好。<sbr>",
            "concerned"
        ),
        "cancel": (
            "好的，我把豹小秘找回來。<sbr>請稍等一下。<sbr>",
            "neutral"
        ),
        "info_location": (
            f"{_get_location_name(target_location)}在{_get_location_area(target_location)}。<sbr>"
            f"我請豹小秘帶你過去。<sbr>請跟著它走。<sbr>",
            "happy"
        ),
        "info_other": (
            "這個我需要查詢一下。<sbr>請稍等一下。<sbr>",
            "thinking"
        ),
        "other": (
            "抱歉，我不太理解您的需求。<sbr>請問您需要什麼協助？<sbr>",
            "embarrassed"
        )
    }
    
    return responses.get(intent, responses["other"])


def _get_location_name(location: Optional[str]) -> str:
    """取得地點中文名稱"""
    names = {
        "counter": "櫃台",
        "registration": "掛號處",
        "pharmacy": "藥局"
    }
    return names.get(location, "那個地方")


def _get_location_area(location: Optional[str]) -> str:
    """取得地點展區描述"""
    areas = {
        "counter": "這裡",
        "registration": "展場 A 區",
        "pharmacy": "展場 B 區"
    }
    return areas.get(location, "展場")


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
    6. 意圖分類
    7. 生成 UbiChan 回應 + 豹小秘 Action
    8. 返回 STREAM 回應
    
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
    
    # 4. 添加用戶消息到 Session Store
    user_message = request.get_message()
    session_store.add_message(session_id, "user", user_message)
    
    # 5. 返回 STREAM 回應
    return StreamingResponse(
        generate_med_ubichan_stream(
            request=request,
            session_id=session_id,
            persona_config=config,
            session_store=session_store
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
    global config_loader, formatter, action_gen, llm_service, prompt_builder, output_parser, prompt_loader
    
    config_loader = config_loader_obj
    formatter = MedUbiOutputFormatter()
    action_gen = RobotActionGenerator()
    
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
    print(f"   - 支持地點：{RobotActionGenerator.LOCATIONS}")
    print(f"   - 支持 Intent: registration, pharmacy, cancel, info_location")
    print(f"   - LLM 生成模式：{'啟用' if (prompt_builder and llm_service) else '未啟用'}")


# ============= LLM 回應生成器 =============

async def generate_response_with_llm(
    user_message: str,
    conversation_history: list,
    persona_config: dict,
    intent_result: Dict[str, Any],
    workspace_path: Path,
    prompt_loader_obj,
    knowledge_content: str = None,
    knowledge_meta: str = None,
    is_llm1: bool = False
) -> Dict[str, Any]:
    """
    使用 LLM 生成完整的 UbiChan + 豹小秘 回應
    
    流程：
    1. 構建 Prompt
    2. 調用 LLM（使用 MedUbiLLMService）
    3. 解析 LLM 輸出
    4. 驗證格式
    
    Returns:
        {
            "success": bool,
            "ubichan_output": str,
            "robot_steps": list,
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
            intent_result=intent_result,
            is_llm1=is_llm1
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
                    "robot_steps": None,
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
                    "robot_steps": None,
                    "robot_steps_descripts": None,
                    "error": parsed_data["error"]
                }
        
        # 3. 驗證格式
        ubichan_content = parsed_data["ToUbiChan"]
        is_valid, error_msg = output_parser.validate_ubichan_format(ubichan_content)
        if not is_valid:
            return {
                "success": False,
                "ubichan_output": ubichan_content,
                "robot_steps": None,
                "robot_steps_descripts": None,
                "error": f"UbiChan 格式錯誤：{error_msg}"
            }
        
        steps = parsed_data["ToBaxiaomi"].get("Steps")
        if steps:
            is_valid, error_msg = output_parser.validate_steps(steps)
            if not is_valid:
                return {
                    "success": False,
                    "ubichan_output": ubichan_content,
                    "robot_steps": steps,
                    "robot_steps_descripts": parsed_data["ToBaxiaomi"].get("Steps_Descripts"),
                    "error": f"Steps 格式錯誤：{error_msg}"
                }
        
        return {
            "success": True,
            "ubichan_output": ubichan_content,
            "robot_steps": steps,
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
    description="UbiChan × 豹小秘 雙機器人協作系統",
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
