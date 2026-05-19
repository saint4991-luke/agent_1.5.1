# tools/knowledge/query_tool.py
"""
Knowledge Query Tool

功能：查詢 Knowledge 內容（基於 meta.json 中的文件列表）
使用場景：Backend Operator 需要獲取特定 Knowledge 的詳細內容
"""

import json
import os
from typing import Any, Dict, List, Optional

from tools.base import BaseTool


class KnowledgeQueryTool(BaseTool):
    """Knowledge Query Tool"""
    
    name = "knowledge_query"
    description = "查詢 Knowledge 內容（基於 meta.json 中的文件列表）"
    
    parameters = {
        "type": "object",
        "properties": {
            "knowledge_id": {
                "type": "string",
                "description": "Knowledge ID（如 'ubitus'）"
            },
            "query": {
                "type": "string",
                "description": "查詢關鍵字（可選）"
            },
            "file_pattern": {
                "type": "string",
                "description": "文件匹配模式（如 '*.md'）"
            }
        },
        "required": ["knowledge_id"]
    }
    
    def __init__(self, knowledge_base_path: str = "/workspace/knowledge"):
        """
        初始化
        
        Args:
            knowledge_base_path: Knowledge 基礎路徑（預設為 Docker 容器內路徑）
        """
        self.knowledge_base_path = knowledge_base_path
    
    def execute(
        self,
        knowledge_id: str,
        query: Optional[str] = None,
        file_pattern: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        執行 Knowledge 查詢
        
        Args:
            knowledge_id: Knowledge ID（如 "ubitus"）
            query: 查詢關鍵字（可選，未來支持全文搜尋）
            file_pattern: 文件匹配模式（可選，如 "*.md"）
        
        Returns:
            dict: {"success": bool, "data": Any, "error": Optional[str]}
        """
        try:
            # 1. 加載 meta.json
            meta_path = os.path.join(
                self.knowledge_base_path,
                knowledge_id,
                "meta.json"
            )
            
            if not os.path.exists(meta_path):
                return {
                    "success": False,
                    "error": f"Knowledge '{knowledge_id}' not found (meta.json missing)"
                }
            
            with open(meta_path, 'r', encoding='utf-8') as f:
                meta = json.load(f)
            
            # 2. 獲取文件列表
            files = meta.get("files", [])
            
            # 3. 如果有 file_pattern，進行過濾
            if file_pattern:
                files = self._filter_files(files, file_pattern)
            
            # 4. 如果有 query，進行關鍵字匹配（未來擴展）
            if query:
                files = self._search_files(knowledge_id, files, query)
            
            # 5. 返回結果
            return {
                "success": True,
                "data": {
                    "knowledge_id": knowledge_id,
                    "query": query,
                    "file_pattern": file_pattern,
                    "meta": meta,
                    "files": files,
                    "count": len(files)
                }
            }
        
        except json.JSONDecodeError as e:
            return {
                "success": False,
                "error": f"Invalid JSON in meta.json: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Error querying knowledge: {str(e)}"
            }
    
    def _filter_files(self, files: List[Dict], pattern: str) -> List[Dict]:
        """
        過濾文件（基於 pattern）
        
        範例：
            pattern = "*.md" → 只返回 Markdown 文件
            pattern = "product_*" → 只返回 product_ 開頭的文件
        """
        import fnmatch
        
        return [
            f for f in files
            if fnmatch.fnmatch(f.get("filename", ""), pattern)
        ]
    
    def _search_files(
        self,
        knowledge_id: str,
        files: List[Dict],
        query: str
    ) -> List[Dict]:
        """
        搜尋文件內容（未來擴展：全文搜尋）
        
        目前實現：基於文件名和描述進行關鍵字匹配
        """
        query_lower = query.lower()
        
        matched_files = []
        for f in files:
            filename = f.get("filename", "").lower()
            description = f.get("description", "").lower()
            
            if query_lower in filename or query_lower in description:
                matched_files.append(f)
        
        return matched_files
