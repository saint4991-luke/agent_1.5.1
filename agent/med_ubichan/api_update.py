# ============= 新增導入 =============

# 在現有導入後添加：
from .prompt_builder import MedUbiPromptBuilder, MedUbiOutputParser


# ============= 新增全局變數 =============

# 在現有全局變數後添加：
# Prompt 構建器和解析器
prompt_builder: Optional[MedUbiPromptBuilder] = None
output_parser: Optional[MedUbiOutputParser] = None


# ============= 新增函數：使用 LLM 生成完整回應 =============

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
    2. 調用 LLM
    3. 解析 LLM 輸出
    4. 驗證格式
    
    Args:
        user_message: 用戶消息
        conversation_history: 對話歷史
        persona_config: Persona 配置
        intent_result: 意圖分類結果
        workspace_path: Workspace 路徑
        prompt_loader_obj: PromptLoader 實例
        knowledge_content: 知識庫完整內容
        knowledge_meta: 知識庫 Meta
        is_llm1: 是否為 LLM1 使用
    
    Returns:
        {
            "success": bool,
            "ubichan_output": str,  # UbiChan 輸出（包含情緒標籤）
            "robot_steps": list,  # 豹小秘 Steps
            "robot_steps_descripts": str,  # 豹小秘步驟描述
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
        llm_response = await llm_service.chat_async(
            messages=[
                {"role": "system", "content": "你是一個醫療展 Virtual Human 助手，負責生成 UbiChan 和豹小秘的協作回應。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        
        # 3. 解析 LLM 輸出
        print("🔍 解析 LLM 輸出...")
        parsed_data = output_parser.parse_llm_response(llm_response)
        
        if not parsed_data["success"]:
            print(f"❌ 解析失敗：{parsed_data['error']}")
            return {
                "success": False,
                "ubichan_output": None,
                "robot_steps": None,
                "robot_steps_descripts": None,
                "error": parsed_data["error"]
            }
        
        # 4. 驗證 UbiChan 格式
        ubichan_content = parsed_data["ToUbiChan"]
        is_valid, error_msg = output_parser.validate_ubichan_format(ubichan_content)
        if not is_valid:
            print(f"❌ UbiChan 格式驗證失敗：{error_msg}")
            return {
                "success": False,
                "ubichan_output": ubichan_content,
                "robot_steps": None,
                "robot_steps_descripts": None,
                "error": f"UbiChan 格式錯誤：{error_msg}"
            }
        
        # 5. 驗證 Steps 格式
        steps = parsed_data["ToBaxiaomi"].get("Steps")
        if steps:
            is_valid, error_msg = output_parser.validate_steps(steps)
            if not is_valid:
                print(f"❌ Steps 格式驗證失敗：{error_msg}")
                return {
                    "success": False,
                    "ubichan_output": ubichan_content,
                    "robot_steps": steps,
                    "robot_steps_descripts": parsed_data["ToBaxiaomi"].get("Steps_Descripts"),
                    "error": f"Steps 格式錯誤：{error_msg}"
                }
        
        print("✅ LLM 回應生成成功")
        return {
            "success": True,
            "ubichan_output": ubichan_content,
            "robot_steps": steps,
            "robot_steps_descripts": parsed_data["ToBaxiaomi"].get("Steps_Descripts"),
            "error": None
        }
    
    except Exception as e:
        print(f"❌ LLM 回應生成失敗：{e}")
        return {
            "success": False,
            "ubichan_output": None,
            "robot_steps": None,
            "robot_steps_descripts": None,
            "error": str(e)
        }


# ============= 修改 generate_med_ubichan_stream 函數 =============

# 替換現有的 generate_med_ubichan_stream 函數：

async def generate_med_ubichan_stream(
    request: ChatRequest,
    persona_config: dict,
    session_store,
    workspace_path: Path,
    prompt_loader_obj,
    knowledge_content: str = None,
    knowledge_meta: str = None,
    is_llm1: bool = False
):
    """
    醫療展 Virtual Human STREAM 生成器（使用 LLM 生成完整回應）
    
    流程：
    1. 意圖分類
    2. 使用 LLM 生成 UbiChan + 豹小秘 完整回應
    3. 解析並驗證 LLM 輸出
    4. STREAM 發送
    
    Args:
        request: ChatRequest
        persona_config: 醫療展 Persona 配置
        session_store: Session Store 實例
        workspace_path: Workspace 路徑
        prompt_loader_obj: PromptLoader 實例
        knowledge_content: 知識庫完整內容
        knowledge_meta: 知識庫 Meta
        is_llm1: 是否為 LLM1 使用
    
    Yields:
        SSE 格式事件
    """
    global prompt_builder, output_parser, formatter, llm_service
    
    start_time = asyncio.get_event_loop().time()
    user_message = request.get_message()
    
    # 獲取時間戳
    created = int(start_time)
    event_id = f"{request.session_id}_{created}"
    
    # ========== 階段 1: 意圖分類 ==========
    print("🔍 階段 1: 意圖分類")
    intent_start = time.time()
    
    intent_result = await classify_intent(user_message)
    
    intent_time = int((time.time() - intent_start) * 1000)
    print(f"✅ 意圖：{intent_result['intent']} ({intent_time}ms)")
    
    # ========== 階段 2: 使用 LLM 生成完整回應 ==========
    print("📝 階段 2: 使用 LLM 生成完整回應")
    
    llm_result = await generate_response_with_llm(
        user_message=user_message,
        conversation_history=session_store.get_messages(request.session_id, limit=10),
        persona_config=persona_config,
        intent_result=intent_result,
        workspace_path=workspace_path,
        prompt_loader_obj=prompt_loader_obj,
        knowledge_content=knowledge_content,
        knowledge_meta=knowledge_meta,
        is_llm1=is_llm1
    )
    
    if not llm_result["success"]:
        print(f"❌ LLM 生成失敗：{llm_result['error']}")
        # 降級處理：使用舊的模板生成方式
        print("⚠️ 降級使用模板生成方式")
        ubichan_text, emotion = await _generate_ubichan_response(
            intent=intent_result['intent'],
            user_message=user_message,
            target_location=intent_result.get('target_location')
        )
        ubichan_output = formatter.format_ubichan_response(
            text=ubichan_text,
            emotion=emotion,
            lang="tw"
        )
        robot_steps = None
        robot_steps_descripts = None
    else:
        ubichan_output = llm_result["ubichan_output"]
        robot_steps = llm_result["robot_steps"]
        robot_steps_descripts = llm_result["robot_steps_descripts"]
        print(f"✅ LLM 生成成功")
    
    # ========== 階段 3: STREAM 發送 ==========
    print("📡 階段 3: STREAM 發送")
    
    try:
        # 發送 UbiChan 輸出（逐句發送）
        sentences = formatter.extract_sentences(ubichan_output)
        
        for i, sentence in enumerate(sentences):
            event = StreamEvent.create_text_chunk(
                message=sentence + "<sbr>" if i < len(sentences) - 1 else sentence,
                created=created,
                event_id=event_id
            )
            yield format_sse_event(event)
            await asyncio.sleep(0.1)  # 模擬逐句顯示
        
        # 如果有豹小秘 Steps，記錄到日誌（後續可通過 metadata 發送）
        if robot_steps:
            print(f"📋 豹小秘 Steps: {json.dumps(robot_steps, ensure_ascii=False)}")
            print(f"📝 豹小秘步驟描述：{robot_steps_descripts}")
    
    except Exception as e:
        print(f"❌ STREAM 發送失敗：{e}")
        event = StreamEvent.create_error(
            error=str(e),
            created=created,
            event_id=event_id
        )
        yield format_sse_event(event)
        return
    
    # ========== 階段 4: Done 事件 ==========
    total_time = int((asyncio.get_event_loop().time() - start_time) * 1000)
    
    event = StreamEvent.create_done(
        created=created,
        event_id=event_id,
        timing={
            "intent_ms": intent_time,
            "total_ms": total_time,
            "llm_success": llm_result["success"] if 'llm_result' in locals() else False,
            "has_robot_steps": robot_steps is not None
        }
    )
    yield format_sse_event(event)
    
    # 保存對話到 Session
    if request.session_id:
        try:
            # 保存用戶消息
            session_store.add_message(request.session_id, "user", user_message)
            
            # 保存助手回應
            assistant_response = {
                "ubichan": ubichan_output,
                "robot_steps": robot_steps,
                "robot_steps_descripts": robot_steps_descripts
            }
            session_store.add_message(
                request.session_id,
                "assistant",
                json.dumps(assistant_response, ensure_ascii=False)
            )
            print(f"✅ 已保存對話到 Session: {request.session_id}")
        except Exception as e:
            print(f"⚠️ 保存 Session 失敗：{e}")
    
    print(f"📊 Session: {request.session_id} | TIMING: total={total_time}ms")


# ============= 更新 init_med_ubichan_api 函數 =============

# 在 init_med_ubichan_api 函數中添加：

def init_med_ubichan_api(
    config_loader_obj: MedUbiConfigLoader,
    llm_service_obj=None,
    workspace_path: Path = None
):
    """
    初始化醫療展 API
    
    在 Server 啟動時調用，注入依賴。
    
    Args:
        config_loader_obj: 醫療展配置載入器
        llm_service_obj: LLM 服務（可選）
        workspace_path: Workspace 路徑（可選）
    """
    global config_loader, formatter, action_gen, llm_service, prompt_builder, output_parser
    
    config_loader = config_loader_obj
    formatter = MedUbiOutputFormatter()
    action_gen = RobotActionGenerator()
    llm_service = llm_service_obj
    
    # 初始化 Prompt 構建器和解析器
    if workspace_path:
        prompt_builder = MedUbiPromptBuilder(workspace_path)
        output_parser = MedUbiOutputParser()
        print(f"✅ Prompt 構建器和解析器已初始化")
    
    print(f"✅ 醫療展 API 初始化完成")
    print(f"   - 支持 persona: {config_loader.get_all_ids()}")
    print(f"   - 支持地點：{RobotActionGenerator.LOCATIONS}")
    print(f"   - 支持 Intent: registration, pharmacy, cancel, info_location")
    print(f"   - LLM 生成模式：{'啟用' if prompt_builder else '未啟用'}")
