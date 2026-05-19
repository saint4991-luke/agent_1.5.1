# tools/file_system/list_dir_tool.py
"""
List Directory Tool - 列出目錄內容
"""

from pathlib import Path
from typing import Any, Dict

from tools.base import BaseTool


class ListDirTool(BaseTool):
    """列出目錄 Tool"""
    
    name = "list_dir"
    description = "列出工作區內的目錄內容（限定在 /workspace 內）"
    
    parameters = {
        "type": "object",
        "properties": {
            "dirpath": {
                "type": "string",
                "description": "目錄路徑（相對於 /workspace），預設為根目錄"
            }
        },
        "required": ["dirpath"]
    }
    
    def __init__(self, workspace_path: str = "/workspace"):
        self.workspace_path = Path(workspace_path)
    
    def execute(self, dirpath: str) -> Dict[str, Any]:
        """
        列出目錄
        
        Args:
            dirpath: 目錄路徑（相對於 /workspace）
        
        Returns:
            {"success": bool, "data": str, "error": Optional[str]}
        """
        try:
            abs_path = (self.workspace_path / dirpath).resolve()
            
            # 安全檢查
            if not str(abs_path).startswith(str(self.workspace_path)):
                return {
                    "success": False,
                    "error": "無法訪問 workspace 外的目錄"
                }
            
            if not abs_path.exists():
                return {
                    "success": False,
                    "error": f"目錄不存在：{dirpath}"
                }
            
            items = []
            for item in sorted(abs_path.iterdir()):
                icon = "📂" if item.is_dir() else "📄"
                items.append(f"{icon} {item.name}")
            
            return {
                "success": True,
                "data": f"📁 {dirpath}:\n" + "\n".join(items)
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"列出失敗：{str(e)}"
            }
