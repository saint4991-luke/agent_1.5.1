"""
Prompt Builder - 醫療展 Virtual Human (UbiChan × 小護士)

根據 MED_UBIAGENT 規格文檔 v1.2，構建完整的 Prompt 並解析 LLM 輸出。

輸出格式（v1.2）：
{
    "ToUbiChan": "<!-- emotion>xxx</emotion --><!-- lang>xxx</lang -->內容<sbr>...",
    "ToBaxiaomi": {
        "Steps_Descripts": "自然語言步驟描述"
    }
}

注意：v1.2 已移除 Steps JSON 結構，只保留 Steps_Descripts 自然語言描述。
"""

from pathlib import Path
from typing import Optional, Dict, Any, Tuple, List
import json
import re


# ===========================================
# PromptLoader - 輸出提示詞模板管理
# ===========================================

class PromptLoader:
    """醫療展 Prompt 載入器"""

    def __init__(self, workspace_path: Path):
        """
        初始化 PromptLoader

        Args:
            workspace_path: Workspace 根目錄路徑
        """
        self.workspace_path = Path(workspace_path)
        project_root = self.workspace_path.parent
        self.prompts_path = project_root / 'agent' / 'shared' / 'prompts' / 'med_ubichan'
        self._cache: Dict[str, str] = {}

    def load_prompt(self, output_format: str) -> str:
        """
        載入輸出提示詞模板

        Args:
            output_format: 輸出格式（med_ubichan | plain | markdown）

        Returns:
            提示詞模板內容
        """
        # 檢查快取
        if output_format in self._cache:
            return self._cache[output_format]

        # 根據 output_format 選擇提示詞文件
        if output_format == 'med_ubichan':
            prompt_file = self.prompts_path / "med_ubichan-output.md"
        elif output_format == 'plain':
            prompt_file = self.prompts_path / "plain-output.md"
        elif output_format == 'markdown':
            prompt_file = self.prompts_path / "markdown-output.md"
        else:
            print(f"⚠️  未知的 output_format: {output_format}，使用預設")
            return "一般文字回應，無需情緒標籤"

        # 檢查文件是否存在
        if not prompt_file.exists():
            print(f"⚠️  提示詞文件不存在：{prompt_file}")
            return "一般文字回應，無需情緒標籤"

        # 讀取文件
        try:
            with open(prompt_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # 存入快取
            self._cache[output_format] = content
            print(f"✅ 載入提示詞模板：{output_format} ({len(content)} 字)")
            return content

        except Exception as e:
            print(f"⚠️  讀取提示詞文件失敗：{e}")
            return "一般文字回應，無需情緒標籤"

    def load_prompt_for_llm1(self, output_format: str, config: Dict = None) -> str:
        """
        為 LLM1 載入提示詞模板（完整版，但 LLM1 只關注 language + 斷句）

        Args:
            output_format: 輸出格式
            config: Persona 配置（可選，用於獲取 quick_response 配置）

        Returns:
            提示詞模板內容（完整版）
        """
        # 從 config 獲取快速回應長度
        max_length = 20  # 預設
        if config and 'quick_response' in config:
            max_length = config['quick_response'].get('max_length', 20)

        # 載入基礎提示詞
        base_prompt = self.load_prompt(output_format)

        # 添加快速回應長度限制
        length_instruction = f"""

# 快速回應長度限制
**嚴格遵守：快速回應只能一句話，不超過 {max_length}個字**
"""
        return base_prompt + length_instruction

    def load_prompt_for_llm2(self, output_format: str) -> str:
        """
        為 LLM2 載入提示詞模板（完整版，含 emotion）

        Args:
            output_format: 輸出格式

        Returns:
            提示詞模板內容（完整版）
        """
        # LLM2 使用完整版提示詞模板
        return self.load_prompt(output_format)

    def clear_cache(self):
        """清空快取（用於開發環境重新載入）"""
        self._cache.clear()
        print("🔄 已清空提示詞快取")


# ===========================================
# MedUbiPromptBuilder - 醫療展 Prompt 構建器
# ===========================================

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
        is_llm1: bool = False,
        persona_config_path: Optional[Path] = None,
        robot_state: str = "available"
    ) -> Tuple[str, bool]:
        """
        組合完整的 Prompt（6 部分結構）

        根據 MED_UBIAGENT 規格：
        1. 角色風格 (Style)
        2. 輸出規格 (Output Spec) - 包含 JSON 格式範例
        3. 知識庫內容 (Knowledge) - LLM1 用 Meta，LLM2 用完整內容
        4. 小護士 Action 說明 (Robot Action Spec)
        5. 對話歷史 (Conversation History)
        6. 用戶問題 (User Message)

        Args:
            config: Persona 配置（YAML v2.0 結構）
                {
                    "persona_id": "med-ubichan",
                    "style": {"file": "style.md"},
                    "output_format": "virtual_human",
                    "version": "1.0"
                }
            user_message: 用戶問題
            conversation_history: 對話歷史 [{"role": "user", "content": "..."}, ...]
            prompt_loader_obj: PromptLoader 實例
            knowledge_content: 知識庫完整內容（LLM2 使用）
            knowledge_meta: 知識庫 Meta（LLM1 使用）
            is_llm1: 是否為 LLM1 使用
            persona_config_path: config.yaml 的路徑（可選，用於確定風格文件位置）
                如果未提供，則使用 personas/{persona_id}/ 路徑
            robot_state: 小護士設備狀態（available | busy | unknown）
                - available: 可以指派新任務
                - busy: 只能取消當前任務
                - unknown: 不可指派任務

        Returns:
            (prompt, emotion_enabled)
        """
        # 1. 載入角色風格
        style_file = config.get('style', {}).get('file', 'style.md')
        persona_id = config.get('persona_id', 'med-ubichan')

        # 優先使用 persona_config_path 確定風格文件位置
        if persona_config_path:
            # 風格文件與 config.yaml 在同一目錄
            style_path = persona_config_path.parent / style_file
        else:
            # 向後兼容：使用 personas/{persona_id}/ 路徑
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

        # 4. 小護士 Action 說明
        robot_action_spec = self._get_robot_action_spec()

        # 5. 格式化對話歷史
        recent_history = conversation_history[-10:] if conversation_history else []
        history_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in recent_history
        ]) if recent_history else "（無）"
        
        # 6. 小護士設備狀態
        robot_state_info = self._get_robot_state_info(robot_state)
        
        # 7. 組合 Prompt（不包含用戶問題，用戶問題將在 api.py 中作為 "role": "user" 傳遞）
        prompt = f"""# 角色風格
{style_content}

# 輸出規格
{prompt_content}

# 知識庫內容
{knowledge_section}

# 小護士 Action 說明
{robot_action_spec}

# 小護士設備狀態
{robot_state_info}

# 對話歷史
{history_text}
"""

        return prompt, emotion_enabled

    def _get_robot_state_info(self, state: str) -> str:
        """
        根據小護士設備狀態生成對應的提示資訊

        Args:
            state: 設備狀態（available | busy | unknown）

        Returns:
            狀態說明文字
        """
        if state == "available":
            return """**小護士當前狀態：available（空閒）**
- 可以指派小護士執行新任務
- 可以派遣小護士進行導航、取物等動作
- 請根據用戶需求判斷是否需要小護士協助"""
        elif state == "busy":
            return """**小護士當前狀態：busy（忙碌）**
- 小護士正在執行前一次任務
- **只能指派「取消」動作**，讓小護士停止當前任務並返回櫃台
- **不可指派新的導航或取物任務**
- 如果用戶需要幫助，請用語言引導，等待小護士完成當前任務"""
        else:  # unknown
            return """**小護士當前狀態：unknown（未知）**
- 無法確認小護士的當前狀態
- **不可指派小護士進行任何任務**
- 請用語言引導用戶，不要派遣小護士"""

    def _get_robot_action_spec(self) -> str:
        """
        取得小護士支持的 Action 說明

        Returns:
            Action 說明文字
        """
        return """## navigate（導航）
- 描述：讓小護士導航到指定地點
- params: {"target": "地點 ID"}
- 支持的地點：
  - counter: 櫃台
  - registration: 掛號處
  - pharmacy: 藥局
  - charging: 充電點
- 範例：
```json
{
    "action": "navigate",
    "params": {"target": "registration"},
    "speech": ""
}
```

## speak（播放語音）
- 描述：讓小護士播放語音
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
- 描述：讓小護士到指定地點拾取物品
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
- 描述：停止小護士所有動作
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
1. 導航任務：移動到櫃台前方 → 對 user 說話 → 導航到目標地點 → 到達後說話
2. 取物任務：移動到物品地點 → 對工作人員說話 → 拾取物品 → 返回櫃台 → 對 user 說話
3. Steps_Descripts 必須用自然語言描述每個步驟，使用「第一步，... 第二步，... 第三步，...」格式
4. 每個步驟必須包含實際說話內容（如果該步驟需要說話）
   - 正確範例：「第二步，對 user 說『你好，請跟我來掛號處』」
   - 錯誤範例：「第二步，對 user 說話」（缺少實際說話內容）
"""


class MedUbiOutputParser:
    """醫療展 LLM 輸出解析器"""

    @staticmethod
    def parse_llm_response(llm_response: str) -> Dict[str, Any]:
        """
        解析 LLM 輸出的字串回應

        輸出格式（字串版本）：
        <!-- emotion>happy</emotion --><!-- lang>tw (zh)</lang -->護理長回應內容<sbr>
        "ToBaxiaomi:"第一步，... 第二步，..."

        Args:
            llm_response: LLM 返回的字串

        Returns:
            {
                "success": bool,
                "ToUbiChan": str or None,
                "ToBaxiaomi": dict or None,
                "error": str or None
            }
        """
        try:
            # 1. 檢查是否包含 "ToBaxiaomi:" 標記（包含引號）
            to_baxiaomi_marker = '"ToBaxiaomi:"'
            
            if to_baxiaomi_marker in llm_response:
                # 分割成兩部分：ToUbiChan 和 ToBaxiaomi
                parts = llm_response.split(to_baxiaomi_marker, 1)
                ubichan_part = parts[0].strip()
                baxiaomi_part = parts[1].strip() if len(parts) > 1 else ""
                
                # 移除 ToBaxiaomi 部分的末尾引號（如果有）
                if baxiaomi_part.endswith('"'):
                    baxiaomi_part = baxiaomi_part[:-1]
                
                # 2. 成功解析
                return {
                    "success": True,
                    "ToUbiChan": ubichan_part,
                    "ToBaxiaomi": baxiaomi_part,  # 直接是字串，不再是物件
                    "error": None
                }
            else:
                # 沒有 ToBaxiaomi 標記，只返回 ToUbiChan 部分
                return {
                    "success": True,
                    "ToUbiChan": llm_response,
                    "ToBaxiaomi": "",  # 空字串
                    "error": None
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
