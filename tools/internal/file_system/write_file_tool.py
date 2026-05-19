# tools/file_system/write_file_tool.py
"""
Write File Tool - 寫入檔案內容
"""

from pathlib import Path
from typing import Any, Dict

from tools.base import BaseTool


class WriteFileTool(BaseTool):
    """寫入檔案 Tool"""
    
    name = "write_file"
    description = "寫入檔案內容到工作區（限定在 /workspace 內）"
    
    parameters = {
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "檔案路徑（相對於 /workspace）"
            },
            "content": {
                "type": "string",
                "description": "檔案內容"
            }
        },
        "required": ["filepath", "content"]
    }
    
    def __init__(self, workspace_path: str = "/workspace"):
        self.workspace_path = Path(workspace_path)
    
    def execute(self, filepath: str, content: str) -> Dict[str, Any]:
        """
        寫入檔案
        
        Args:
            filepath: 檔案路徑（相對於 /workspace）
            content: 檔案內容
        
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
            
            # 創建父目錄（如果不存在）
            abs_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 寫入檔案
            with open(abs_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            return {
                "success": True,
                "data": f"✅ 寫入成功：{filepath}"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"寫入失敗：{str(e)}"
            }
