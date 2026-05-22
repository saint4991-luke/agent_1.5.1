"""
Prompt Builder - 醫療展 Virtual Human (UbiChan × 豹小秘)

根據 MED_UBIAGENT 規格文檔 v1.0，構建完整的 Prompt 並解析 LLM 輸出。

輸出格式：
{
    "ToUbiChan": "<情緒><語言>內容<sbr>...",
    "ToBaxiaomi": {
        "Steps": [...],
        "Steps_Descripts": "..."
    }
}
"""

from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import json
import re


class MedUbiPromptBuilder:
    """醫療展 Prompt 構建器"""
    
    def __init__(self, workspace_path: Path):
        """
        初始化 Prompt 構建器
        
        Args:
            workspace_path: Workspace 根目錄路徑
        """
        self.workspace_path = workspace_path
    
    async def _build_prompt(
        self,
        config: dict,
        user_message: str,
        conversation_history: list,
        prompt_loader_obj,
        knowledge_content: str = None,
        knowledge_meta: str = None,
        intent_result: Optional[Dict[str, Any]] = None,
        is_llm1: bool = False
    ) -> Tuple[str, bool]:
        """
        組合完整的 Prompt（6 部分結構）
        
        根據 MED_UBIAGENT 規格：
        1. 角色風格 (Style)
        2. 輸出規格 (Output Spec) - 包含 JSON 格式範例
        3. 知識庫內容 (Knowledge) - LLM1 用 Meta，LLM2 用完整內容
        4. 豹小秘 Action 說明 (Robot Action Spec)
        5. 對話歷史 (Conversation History)
        6. 用戶問題 (User Message)
        
        Args:
            config: Persona 配置（YAML v2.0 結構）
                {
                    "persona_id": "med_ubichan_v1",
                    "style": {"file": "style.md"},
                    "output_format": "med_ubichan",
                    "version": "v1.0"
                }
            user_message: 用戶問題
            conversation_history: 對話歷史 [{"role": "user", "content": "..."}, ...]
            prompt_loader_obj: PromptLoader 實例
            knowledge_content: 知識庫完整內容（LLM2 使用）
            knowledge_meta: 知識庫 Meta（LLM1 使用）
            intent_result: 意圖分類結果（可選）
                {
                    "intent": "registration",
                    "target_location": "registration",
                    "requires_robot": True
                }
            is_llm1: 是否為 LLM1 使用
        
        Returns:
            (prompt, emotion_enabled)
        """
        # 1. 載入角色風格
        style_file = config.get('style', {}).get('file', 'style.md')
        persona_id = config.get('persona_id', 'med_ubichan_v1')
        style_path = self.workspace_path / 'personas' / persona_id / style_file
        
        if style_path.exists():
            style_content = style_path.read_text(encoding='utf-8')
        else:
            print(f"⚠️  風格文件不存在：{style_path}")
            style_content = f"# {persona_id} 風格定義\n（文件缺失）"
        
        # 2. 載入輸出格式提示詞模板
        output_format = config.get('output_format', 'med_ubichan')
        if is_llm1:
            prompt_content = prompt_loader_obj.load_prompt_for_llm1(output_format, config)
        else:
            prompt_content = prompt_loader_obj.load_prompt(output_format)
        emotion_enabled = True  # 醫療展版本始終啟用情緒標籤
        
        # 3. 載入知識庫（LLM1 vs LLM2 差異）
        if is_llm1:
            # LLM1：只載入 Meta（用於判斷）
            knowledge_section = knowledge_meta if knowledge_meta else "無"
        else:
            # LLM2：載入完整內容
            knowledge_section = knowledge_content if knowledge_content else "無"
        
        # 4. 豹小秘 Action 說明
        robot_action_spec = self._get_robot_action_spec()
        
        # 5. 格式化對話歷史
        recent_history = conversation_history[-10:] if conversation_history else []
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in recent_history
        ]) if recent_history else "（無）"
        
        # 6. 意圖資訊（如果有）
        intent_section = "無"
        if intent_result:
            intent_section = f"""
- Intent: {intent_result.get('intent', 'unknown')}
- Target Location: {intent_result.get('target_location', 'null')}
- Requires Robot: {intent_result.get('requires_robot', False)}
"""
        
        # 7. 組合 Prompt
        prompt = f"""# 角色風格
{style_content}

# 輸出規格
{prompt_content}

請按照以下 JSON 格式輸出：
```json
{{
    "ToUbiChan": "<情緒標籤><語言標籤>內容<sbr>...",
    "ToBaxiaomi": {{
        "Steps": [
            {{
                "action": "action_name",
                "params": {{
                    "key": "value"
                }},
                "speech": "語音內容或空字符串"
            }}
        ],
        "Steps_Descripts": "自然語言步驟描述"
    }}
}}
```

注意：
- ToUbiChan 必須包含情緒標籤（<neutral>, <happy>, <concerned> 等）和語言標籤（<tw>, <cn>）
- ToUbiChan 的內容必須使用 <sbr> 進行斷句
- ToBaxiaomi.Steps 必須是數組，每個步驟包含 action、params、speech
- ToBaxiaomi.Steps_Descripts 必須是自然語言描述的步驟說明

# 知識庫內容
{knowledge_section}

# 豹小秘 Action 說明
{robot_action_spec}

# 意圖分類結果
{intent_section}

# 對話歷史
{history_text}

# 用戶問題
{user_message}
"""
        
        return prompt, emotion_enabled
    
    def _get_robot_action_spec(self) -> str:
        """
        取得豹小秘支持的 Action 說明
        
        Returns:
            Action 說明文字
        """
        return """## navigate（導航）
- 描述：讓豹小秘導航到指定地點
- params: {"target": "地點 ID"}
- 支持的地點：
  - counter: 櫃台
  - registration: 掛號處
  - pharmacy: 藥局
- 範例：
```json
{
    "action": "navigate",
    "params": {"target": "registration"},
    "speech": ""
}
```

## speak（播放語音）
- 描述：讓豹小秘播放語音
- params: {"speech": "語音內容"}
- 範例：
```json
{
    "action": "speak",
    "params": {"speech": "你好，請跟我來"},
    "speech": ""
}
```

## pickup_item（拾取物品）
- 描述：讓豹小秘到指定地點拾取物品
- params: {"location": "地點 ID", "item": "物品名稱"}
- 範例：
```json
{
    "action": "pickup_item",
    "params": {"location": "pharmacy", "item": "藥品"},
    "speech": "藥劑師你好，請把藥品放到我的籃子"
}
```

## cancel（停止）
- 描述：停止豹小秘所有動作
- params: {}
- 範例：
```json
{
    "action": "cancel",
    "params": {},
    "speech": ""
}
```

## 步驟組合原則
1. 導航任務：navigate → speak → navigate → speak
   - 第一步：移動到櫃台前方
   - 第二步：對 user 說話
   - 第三步：導航到目標地點
   - 第四步：到達後說話
2. 取物任務：navigate → speak → pickup_item → navigate → speak
   - 第一步：移動到物品地點
   - 第二步：對工作人員說話
   - 第三步：拾取物品
   - 第四步：返回櫃台
   - 第五步：對 user 說話
3. 每個步驟的 speech 可以是空字符串 ""（如果不需要說話）
4. Steps_Descripts 必須用自然語言描述每個步驟，使用「第一步，... 第二步，...」格式
"""


class MedUbiOutputParser:
    """醫療展 LLM 輸出解析器"""
    
    @staticmethod
    def parse_llm_response(llm_response: str) -> Dict[str, Any]:
        """
        解析 LLM 輸出的 JSON 回應
        
        Args:
            llm_response: LLM 返回的文字（可能包含 JSON）
        
        Returns:
            {
                "success": bool,
                "ToUbiChan": str or None,
                "ToBaxiaomi": dict or None,
                "error": str or None
            }
        """
        try:
            # 1. 嘗試直接解析 JSON
            try:
                data = json.loads(llm_response.strip())
            except json.JSONDecodeError:
                # 2. 如果失敗，嘗試提取 JSON 代碼塊
                json_match = re.search(r'```json\s*(.*?)\s*```', llm_response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                    data = json.loads(json_str.strip())
                else:
                    # 3. 嘗試提取大括號內容
                    json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        data = json.loads(json_str.strip())
                    else:
                        return {
                            "success": False,
                            "ToUbiChan": None,
                            "ToBaxiaomi": None,
                            "error": "無法解析 JSON 格式"
                        }
            
            # 4. 驗證必要欄位
            if "ToUbiChan" not in data:
                return {
                    "success": False,
                    "ToUbiChan": None,
                    "ToBaxiaomi": None,
                    "error": "缺少 ToUbiChan 欄位"
                }
            
            if "ToBaxiaomi" not in data:
                return {
                    "success": False,
                    "ToUbiChan": data.get("ToUbiChan"),
                    "ToBaxiaomi": None,
                    "error": "缺少 ToBaxiaomi 欄位"
                }
            
            # 5. 驗證 ToBaxiaomi 結構
            to_baxiaomi = data.get("ToBaxiaomi")
            if not isinstance(to_baxiaomi, dict):
                return {
                    "success": False,
                    "ToUbiChan": data.get("ToUbiChan"),
                    "ToBaxiaomi": None,
                    "error": "ToBaxiaomi 必須是物件"
                }
            
            if "Steps" not in to_baxiaomi:
                return {
                    "success": False,
                    "ToUbiChan": data.get("ToUbiChan"),
                    "ToBaxiaomi": None,
                    "error": "ToBaxiaomi 缺少 Steps 欄位"
                }
            
            if "Steps_Descripts" not in to_baxiaomi:
                return {
                    "success": False,
                    "ToUbiChan": data.get("ToUbiChan"),
                    "ToBaxiaomi": None,
                    "error": "ToBaxiaomi 缺少 Steps_Descripts 欄位"
                }
            
            # 6. 驗證 Steps 是數組
            if not isinstance(to_baxiaomi.get("Steps"), list):
                return {
                    "success": False,
                    "ToUbiChan": data.get("ToUbiChan"),
                    "ToBaxiaomi": None,
                    "error": "Steps 必須是數組"
                }
            
            # 7. 成功解析
            return {
                "success": True,
                "ToUbiChan": data.get("ToUbiChan"),
                "ToBaxiaomi": to_baxiaomi,
                "error": None
            }
        
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "ToUbiChan": None,
                "ToBaxiaomi": None,
                "error": f"JSON 解析錯誤：{str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "ToUbiChan": None,
                "ToBaxiaomi": None,
                "error": f"解析錯誤：{str(e)}"
            }
    
    @staticmethod
    def extract_ubichan_content(parsed_data: Dict[str, Any]) -> Optional[str]:
        """
        從解析結果中提取 UbiChan 內容
        
        Args:
            parsed_data: parse_llm_response 返回的字典
        
        Returns:
            UbiChan 內容字符串（包含情緒標籤和語言標籤）或 None
        """
        if parsed_data.get("success") and parsed_data.get("ToUbiChan"):
            return parsed_data["ToUbiChan"]
        return None
    
    @staticmethod
    def extract_steps_descripts(parsed_data: Dict[str, Any]) -> Optional[str]:
        """
        從解析結果中提取 Steps_Descripts 內容
        
        Args:
            parsed_data: parse_llm_response 返回的字典
        
        Returns:
            Steps_Descripts 字符串或 None
        """
        if parsed_data.get("success") and parsed_data.get("ToBaxiaomi"):
            to_baxiaomi = parsed_data["ToBaxiaomi"]
            if isinstance(to_baxiaomi, dict):
                return to_baxiaomi.get("Steps_Descripts")
        return None
    
    @staticmethod
    def extract_steps(parsed_data: Dict[str, Any]) -> Optional[List[Dict[str, Any]]]:
        """
        從解析結果中提取 Steps 數組
        
        Args:
            parsed_data: parse_llm_response 返回的字典
        
        Returns:
            Steps 數組或 None
        """
        if parsed_data.get("success") and parsed_data.get("ToBaxiaomi"):
            to_baxiaomi = parsed_data["ToBaxiaomi"]
            if isinstance(to_baxiaomi, dict):
                steps = to_baxiaomi.get("Steps")
                if isinstance(steps, list):
                    return steps
        return None
    
    @staticmethod
    def validate_ubichan_format(ubichan_content: str) -> Tuple[bool, Optional[str]]:
        """
        驗證 UbiChan 內容格式是否正確
        
        格式要求：
        - 必須以情緒標籤開頭：<neutral>, <happy>, <concerned>, <thinking>, <embarrassed>
        - 必須包含語言標籤：<tw>, <cn>
        - 必須使用 <sbr> 進行斷句
        
        Args:
            ubichan_content: UbiChan 內容字符串
        
        Returns:
            (is_valid, error_message)
        """
        if not ubichan_content:
            return False, "內容為空"
        
        # 檢查情緒標籤
        emotion_pattern = r'^<(neutral|happy|concerned|thinking|embarrassed|excited|sad|surprised)>'
        if not re.match(emotion_pattern, ubichan_content):
            return False, "缺少或無效的情緒標籤（必須在開頭）"
        
        # 檢查語言標籤
        lang_pattern = r'<(tw|cn|en)>'
        if not re.search(lang_pattern, ubichan_content):
            return False, "缺少語言標籤（<tw>, <cn>, 或 <en>）"
        
        # 檢查 <sbr> 斷句
        if '<sbr>' not in ubichan_content:
            return False, "缺少 <sbr> 斷句標記"
        
        return True, None
    
    @staticmethod
    def validate_steps(steps: List[Dict[str, Any]]) -> Tuple[bool, Optional[str]]:
        """
        驗證 Steps 數組格式是否正確
        
        Args:
            steps: Steps 數組
        
        Returns:
            (is_valid, error_message)
        """
        if not steps or not isinstance(steps, list):
            return False, "Steps 必須是非空數組"
        
        valid_actions = ["navigate", "speak", "pickup_item", "cancel"]
        
        for i, step in enumerate(steps):
            if not isinstance(step, dict):
                return False, f"步驟 {i+1} 必須是物件"
            
            if "action" not in step:
                return False, f"步驟 {i+1} 缺少 action 欄位"
            
            action = step.get("action")
            if action not in valid_actions:
                return False, f"步驟 {i+1} 的 action '{action}' 無效（支持：{', '.join(valid_actions)}）"
            
            if "params" not in step:
                return False, f"步驟 {i+1} 缺少 params 欄位"
        
        return True, None
