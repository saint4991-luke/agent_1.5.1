# tools/file_system/read_word_tool.py
"""
Read Word Tool - 讀取 Word 檔案
"""

from pathlib import Path
from typing import Any, Dict

from tools.base import BaseTool


class ReadWordTool(BaseTool):
    """讀取 Word Tool"""
    
    name = "read_word"
    description = "讀取工作區內的 Word 檔案（限定在 /workspace 內）"
    
    parameters = {
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "Word 檔案路徑（相對於 /workspace）"
            }
        },
        "required": ["filepath"]
    }
    
    def __init__(self, workspace_path: str = "/workspace"):
        self.workspace_path = Path(workspace_path)
    
    def execute(self, filepath: str) -> Dict[str, Any]:
        """
        讀取 Word
        
        Args:
            filepath: 檔案路徑（相對於 /workspace）
        
        Returns:
            {"success": bool, "data": str, "error": Optional[str]}
        """
        try:
            from docx import Document
            
            abs_path = (self.workspace_path / filepath).resolve()
            
            # 安全檢查
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
            
            doc = Document(abs_path)
            content = [p.text for p in doc.paragraphs if p.text.strip()]
            
            return {
                "success": True,
                "data": f"📘 Word 內容:\n" + "\n".join(content[:50])
            }
        except ImportError:
            return {
                "success": False,
                "error": "缺少 python-docx 模組：pip install python-docx"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"讀取 Word 失敗：{str(e)}"
            }
