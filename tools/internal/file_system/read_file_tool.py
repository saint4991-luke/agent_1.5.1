# tools/file_system/read_file_tool.py
"""
Read File Tool - 讀取檔案內容
"""

from pathlib import Path
from typing import Any, Dict

from tools.base import BaseTool


class ReadFileTool(BaseTool):
    """讀取檔案 Tool"""
    
    name = "read_file"
    description = "讀取工作區內的檔案內容（限定在 /workspace 內）"
    
    parameters = {
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "檔案路徑（相對於 /workspace）"
            }
        },
        "required": ["filepath"]
    }
    
    def __init__(self, workspace_path: str = "/workspace"):
        self.workspace_path = Path(workspace_path)
    
    def execute(self, filepath: str) -> Dict[str, Any]:
        """
        讀取檔案
        
        Args:
            filepath: 檔案路徑（相對於 /workspace）
        
        Returns:
            {"success": bool, "data": str, "error": Optional[str]}
        """
        try:
            abs_path = (self.workspace_path / filepath).resolve()
            
            # 安全檢查：防止訪問 workspace 外的檔案
            if not str(abs_path).startswith(str(self.workspace_path)):
                return {
                    "success": False,
                    "error": "無法訪問 workspace 外的檔案"
                }
            
            if not abs_path.exists():
                return {
                    "success": False,
                    "error": f"檔案不存在：{filepath}"
                }
            
            with open(abs_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return {
                "success": True,
                "data": content
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"讀取失敗：{str(e)}"
            }
