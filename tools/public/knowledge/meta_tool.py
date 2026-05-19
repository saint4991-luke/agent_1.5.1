# tools/knowledge/meta_tool.py
"""
Knowledge Meta Tool

功能：獲取 Knowledge 的 Meta 資訊（從 meta.json）
使用場景：Backend Operator 需要知道有哪些 Knowledge 可用
"""

import json
import os
from typing import Any, Dict, Optional

from tools.base import BaseTool


class KnowledgeMetaTool(BaseTool):
    """Knowledge Meta Tool"""
    
    name = "knowledge_meta"
    description = "獲取 Knowledge 的 Meta 資訊（從 meta.json）"
    
    parameters = {
        "type": "object",
        "properties": {
            "knowledge_id": {
                "type": "string",
                "description": "Knowledge ID（如 'ubitus'），留空則返回所有"
            }
        },
        "required": []
    }
    
    def __init__(self, knowledge_base_path: str = "/workspace/knowledge"):
        """
        初始化
        
        Args:
            knowledge_base_path: Knowledge 基礎路徑（預設為 Docker 容器內路徑）
        """
        self.knowledge_base_path = knowledge_base_path
    
    def execute(self, knowledge_id: Optional[str] = None) -> Dict[str, Any]:
        """
        執行 Meta 查詢
        
        Args:
            knowledge_id: 指定的 Knowledge ID（如 "ubitus"）
                         如果為 None，返回所有 Knowledge 的 Meta
        
        Returns:
            dict: {"success": bool, "data": Any, "error": Optional[str]}
        """
        try:
            if knowledge_id:
                # 獲取單一 Knowledge 的 Meta
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
                
                return {
                    "success": True,
                    "data": {
                        "knowledge_id": knowledge_id,
                        "meta": meta
                    }
                }
            else:
                # 獲取所有 Knowledge 的 Meta
                all_metas = {}
                
                if os.path.exists(self.knowledge_base_path):
                    for folder in os.listdir(self.knowledge_base_path):
                        folder_path = os.path.join(self.knowledge_base_path, folder)
                        meta_path = os.path.join(folder_path, "meta.json")
                        
                        if os.path.isdir(folder_path) and os.path.exists(meta_path):
                            with open(meta_path, 'r', encoding='utf-8') as f:
                                all_metas[folder] = json.load(f)
                
                return {
                    "success": True,
                    "data": {
                        "count": len(all_metas),
                        "metas": all_metas
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
                "error": f"Error loading meta: {str(e)}"
            }
