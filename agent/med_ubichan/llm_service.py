"""
LLM Service - 醫療展 Virtual Human

整合 UbiLM Grant API 和 Chat Completions API
提供統一的 chat_async 介面

流程：
1. 呼叫 Grant API 獲取 api_token 和 api_endpoint
2. 呼叫 api_endpoint/v1/chat/completions 進行對話
"""

import httpx
import json
from typing import Optional, Dict, Any, List
from pathlib import Path
import os


# ===========================================
# 環境變數配置
# ===========================================

UBILM_GRANT_URL = os.getenv("UBILM_GRANT_URL", "https://sage.ubitus.ai/ubillm/api/v1/resource/grant")
UBILM_API_KEY = os.getenv("UBILM_API_KEY", "I3ksbLteZrRQHgs7HIvT4TTWmF63ZLFWwcTtZt6J1PE")
UBILM_MODEL = os.getenv("UBILM_LLM_MODEL", "qwen3-8b-fp8")


# ===========================================
# UbiLLM Service
# ===========================================

class UbiLLMService:
    """UbiLLM 服務"""
    
    def __init__(
        self,
        grant_url: str = None,
        api_key: str = None,
        model: str = None
    ):
        """
        初始化 UbiLLM 服務
        
        Args:
            grant_url: Grant API URL
            api_key: UbiLM API Key（從環境變數或配置讀取）
            model: LLM 模型名稱
        """
        self.grant_url = grant_url or UBILM_GRANT_URL
        self.api_key = api_key or UBILM_API_KEY
        self.model = model or UBILM_MODEL
        
        # 快取的 token 和 endpoint
        self._api_token: Optional[str] = None
        self._api_endpoint: Optional[str] = None
        self._token_valid: bool = False
    
    async def _grant_token(self) -> tuple[str, str]:
        """
        呼叫 Grant API 獲取 api_token 和 api_endpoint
        
        Returns:
            (api_token, api_endpoint)
        
        Raises:
            Exception: Grant API 呼叫失敗
        """
        try:
            timeout = httpx.Timeout(30.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    self.grant_url,
                    headers={"Content-Type": "application/json"},
                    json={
                        "api_key": self.api_key,
                        "model": self.model
                    }
                )
                response.raise_for_status()
                result = response.json()
                
                api_token = result.get("api_token")
                api_endpoint = result.get("api_endpoint")
                
                if not api_token or not api_endpoint:
                    raise Exception(f"Grant API 返回無效數據：{result}")
                
                # 快取 token 和 endpoint
                self._api_token = api_token
                self._api_endpoint = api_endpoint
                self._token_valid = True
                
                print(f"✅ Grant API 成功 - endpoint: {api_endpoint}")
                return api_token, api_endpoint
        
        except httpx.TimeoutException as e:
            print(f"❌ Grant API timeout: {e}")
            raise Exception(f"Grant API timeout: {str(e)}")
        except Exception as e:
            print(f"❌ Grant API 失敗：{e}")
            raise Exception(f"Grant API 失敗：{str(e)}")
    
    async def _chat_completions(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        enable_thinking: bool = False,
        stream: bool = False,
        **kwargs
    ) -> Dict[str, Any]:
        """
        呼叫 Chat Completions API
        
        Args:
            messages: 對話消息列表 [{"role": "user", "content": "..."}]
            temperature: 溫度參數
            max_tokens: 最大 token 數
            enable_thinking: 是否啟用 thinking 模式
            stream: 是否使用 stream 模式
            **kwargs: 其他參數
        
        Returns:
            LLM 回應 JSON
        
        Raises:
            Exception: API 呼叫失敗
        """
        # 每次都重新呼叫 Grant API 獲取 token（不管是否已經拿到 token）
        await self._grant_token()
        
        url = f"{self._api_endpoint}/v1/chat/completions"
        
        try:
            timeout = httpx.Timeout(30.0, connect=5.0)
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    url,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self._api_token}"
                    },
                    json={
                        "messages": messages,
                        "temperature": temperature,
                        "max_tokens": max_tokens,
                        "chat_template_kwargs": {
                            "enable_thinking": enable_thinking
                        },
                        "stream": stream,
                        **kwargs
                    }
                )
                response.raise_for_status()
                return response.json()
        
        except httpx.TimeoutException as e:
            print(f"❌ Chat Completions API timeout: {e}")
            raise Exception(f"Chat API timeout: {str(e)}")
        except httpx.HTTPStatusError as e:
            print(f"❌ Chat Completions API HTTP 錯誤：{e}")
            # 如果 token 失效，重新獲取
            if e.response.status_code == 401:
                print("⚠️ Token 失效，重新獲取...")
                self._token_valid = False
                await self._grant_token()
                # 重試一次
                return await self._chat_completions(
                    messages, temperature, max_tokens, enable_thinking, stream, **kwargs
                )
            raise Exception(f"Chat API HTTP 錯誤：{str(e)}")
        except Exception as e:
            print(f"❌ Chat Completions API 失敗：{e}")
            raise Exception(f"Chat API 失敗：{str(e)}")
    
    async def chat_async(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        enable_thinking: bool = False,
        **kwargs
    ) -> str:
        """
        非同步對話介面
        
        Args:
            messages: 對話消息列表
            temperature: 溫度參數
            max_tokens: 最大 token 數
            enable_thinking: 是否啟用 thinking 模式
            **kwargs: 其他參數
        
        Returns:
            LLM 回應的文字內容
        """
        try:
            result = await self._chat_completions(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                enable_thinking=enable_thinking,
                stream=False,
                **kwargs
            )
            
            # 提取回應內容
            if "choices" in result and len(result["choices"]) > 0:
                choice = result["choices"][0]
                if "message" in choice and "content" in choice["message"]:
                    content = choice["message"]["content"]
                    print(f"✅ LLM 回應長度：{len(content)} 字元")
                    return content
            
            # 如果沒有找到內容，返回原始 JSON
            print(f"⚠️ LLM 回應格式異常：{json.dumps(result, ensure_ascii=False)[:200]}")
            return json.dumps(result, ensure_ascii=False)
        
        except Exception as e:
            print(f"❌ chat_async 失敗：{e}")
            raise
    
    async def chat_with_retry(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        retry_count: int = 2,
        **kwargs
    ) -> str:
        """
        帶重試機制的對話介面
        
        Args:
            messages: 對話消息列表
            temperature: 溫度參數
            max_tokens: 最大 token 數
            retry_count: 重試次數
            **kwargs: 其他參數
        
        Returns:
            LLM 回應的文字內容
        """
        last_error = None
        
        for attempt in range(retry_count + 1):
            try:
                if attempt > 0:
                    print(f"🔄 重試第 {attempt} 次...")
                    # 重試時強制更新 token
                    self._token_valid = False
                
                return await self.chat_async(
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                )
            
            except Exception as e:
                last_error = e
                print(f"⚠️ 嘗試 {attempt + 1} 失敗：{e}")
        
        # 所有重試都失敗
        raise Exception(f"LLM 呼叫失敗（重試 {retry_count} 次）: {last_error}")


class MedUbiLLMService(UbiLLMService):
    """醫療展專用 LLM 服務（擴展自 UbiLLMService）"""
    
    def __init__(
        self,
        grant_url: str = None,
        api_key: str = None,
        model: str = None,
        workspace_path: Path = None
    ):
        """
        初始化醫療展 LLM 服務
        
        Args:
            grant_url: Grant API URL
            api_key: UbiLM API Key
            model: LLM 模型名稱
            workspace_path: Workspace 路徑（用於讀取配置）
        """
        super().__init__(grant_url, api_key, model)
        self.workspace_path = workspace_path
    
    async def generate_med_ubichan_response(
        self,
        prompt: str,
        user_message: str,
        robot_state: str = "available",
        conversation_history: List[Dict[str, str]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """
        生成醫療展 Virtual Human 回應
        
        Args:
            prompt: 完整的 Prompt（作為 system content）
            user_message: 用戶問題（作為 user content）
            robot_state: 小護士設備狀態（available | busy | unknown）
            conversation_history: 對話歷史（可選）
            temperature: 溫度參數
            max_tokens: 最大 token 數
        
        Returns:
            {
                "success": bool,
                "content": str,  # LLM 原始回應
                "parsed": dict,  # 解析後的 JSON
                "error": str or None
            }
        """
        try:
            # 組合消息
            messages = [
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": user_message
                },
                {
                    "role": "tool",
                    "content": self._get_robot_state_info(robot_state)
                }
            ]
            
            # 呼叫 LLM
            llm_response = await self.chat_with_retry(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            # 解析 JSON
            from prompt_builder import MedUbiOutputParser
            parser = MedUbiOutputParser()
            parsed_data = parser.parse_llm_response(llm_response)
            
            return {
                "success": parsed_data["success"],
                "content": llm_response,
                "parsed": parsed_data,
                "error": None if parsed_data["success"] else parsed_data["error"]
            }
        
        except Exception as e:
            return {
                "success": False,
                "content": None,
                "parsed": None,
                "error": str(e)
            }
    
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
- 請用語言引導來賓，不要派遣小護士"""


# 工廠函數
def create_llm_service(
    api_key: str = None,
    model: str = None,
    workspace_path: Path = None
) -> MedUbiLLMService:
    """
    創建醫療展 LLM 服務實例
    
    Args:
        api_key: UbiLM API Key（如果為 None，從環境變數讀取）
        model: LLM 模型名稱
        workspace_path: Workspace 路徑
    
    Returns:
        MedUbiLLMService 實例
    """
    return MedUbiLLMService(
        api_key=api_key,
        model=model,
        workspace_path=workspace_path
    )
