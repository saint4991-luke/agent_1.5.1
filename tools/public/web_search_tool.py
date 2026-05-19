# tools/external/web_search_tool.py
"""
Web Search Tool - 網頁搜尋工具

使用 DuckDuckGo 搜尋引擎進行網頁搜尋
"""

from typing import Any, Dict, List, Optional

from tools.base import BaseTool


class WebSearchTool(BaseTool):
    """網頁搜尋 Tool（使用 DuckDuckGo）"""
    
    name = "web_search"
    description = "搜尋網路資訊（使用 DuckDuckGo 搜尋引擎）"
    
    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜尋關鍵字"
            }
        },
        "required": ["query"]
    }
    
    def __init__(self, max_results: int = 5):
        """
        初始化
        
        Args:
            max_results: 最大搜尋結果數量（預設 5）
        """
        self.max_results = max_results
    
    def execute(self, query: str) -> Dict[str, Any]:
        """
        執行網頁搜尋
        
        Args:
            query: 搜尋關鍵字
        
        Returns:
            {
                "success": bool,
                "data": str,  # 格式化的搜尋結果
                "error": Optional[str]
            }
        """
        try:
            # 嘗試新舊兩個庫名（ddgs 是新名稱，duckduckgo_search 是舊名稱）
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=self.max_results))
            
            # 沒有結果
            if not results:
                return {
                    "success": True,
                    "data": f"🔍 沒有找到相關結果（搜尋詞：{query}）"
                }
            
            # 格式化結果
            content = self._format_results(query, results)
            
            return {
                "success": True,
                "data": content
            }
        
        except ImportError:
            return {
                "success": False,
                "error": "缺少 ddgs 模組：pip install ddgs"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"搜尋失敗：{str(e)}"
            }
    
    def _format_results(self, query: str, results: List[Dict]) -> str:
        """
        格式化搜尋結果
        
        Args:
            query: 搜尋關鍵字
            results: 搜尋結果列表
        
        Returns:
            格式化的字串
        """
        content = [f"🔍 搜尋結果 ({query}):", ""]
        
        for i, r in enumerate(results, 1):
            title = r.get('title', '無標題')
            body = r.get('body', '無摘要')
            href = r.get('href', '無連結')
            
            content.append(f"{i}. {title}")
            content.append(f"   {body}")
            content.append(f"   {href}")
            content.append("")  # 空行分隔
        
        return "\n".join(content)
    
    def execute_raw(self, query: str) -> Dict[str, Any]:
        """
        執行網頁搜尋（返回原始數據）
        
        Args:
            query: 搜尋關鍵字
        
        Returns:
            {
                "success": bool,
                "data": List[Dict],  # 原始搜尋結果
                "error": Optional[str]
            }
        """
        try:
            # 嘗試新舊兩個庫名
            try:
                from ddgs import DDGS
            except ImportError:
                from duckduckgo_search import DDGS
            
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=self.max_results))
            
            return {
                "success": True,
                "data": results
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"搜尋失敗：{str(e)}"
            }
