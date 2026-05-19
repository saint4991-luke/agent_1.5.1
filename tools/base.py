# tools/base.py
"""
Tool 基礎類別（Interface）

參考 LangChain 設計，保持輕量：
- 統一的 execute() 介面
- 支持同步/異步調用
- 標準化返回格式：{"success": bool, "data": Any, "error": Optional[str]}
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import asyncio


class BaseTool(ABC):
    """Tool 基礎類別（抽象基類）"""
    
    # 類別屬性（可被子類覆蓋）
    name: str = ""
    description: str = ""
    parameters: Dict[str, Any] = {}  # JSON Schema 格式的參數定義
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        執行 Tool（同步）
        
        Args:
            **kwargs: 輸入參數
            
        Returns:
            dict: 執行結果，建議格式：
                  {"success": bool, "data": Any, "error": Optional[str]}
        """
        pass
    
    async def aexecute(self, **kwargs) -> Dict[str, Any]:
        """
        執行 Tool（異步）
        
        預設實現：將同步 execute() 包裝成異步
        子類可以覆蓋此方法以實現真正的異步邏輯
        """
        # 使用執行緒池運行同步代碼，避免阻塞 Event Loop
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.execute(**kwargs)
        )
    
    def __call__(self, **kwargs) -> Dict[str, Any]:
        """
        允許像函數一樣調用
        
        範例：
            tool = KnowledgeMetaTool()
            result = tool(knowledge_id="ubitus")
        """
        return self.execute(**kwargs)
    
    def to_schema(self) -> Dict[str, Any]:
        """
        返回 Tool 的 Schema（供 LLM 使用）
        
        返回完整的 Function Calling Schema，包含參數定義
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters
            }
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
