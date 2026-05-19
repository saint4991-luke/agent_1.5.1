# tools/file_system/read_pdf_tool.py
"""
Read PDF Tool - 讀取 PDF 檔案
"""

from pathlib import Path
from typing import Any, Dict

from tools.base import BaseTool


class ReadPdfTool(BaseTool):
    """讀取 PDF Tool"""
    
    name = "read_pdf"
    description = "讀取工作區內的 PDF 檔案（限定在 /workspace 內）"
    
    parameters = {
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "PDF 檔案路徑（相對於 /workspace）"
            }
        },
        "required": ["filepath"]
    }
    
    def __init__(self, workspace_path: str = "/workspace"):
        self.workspace_path = Path(workspace_path)
    
    def execute(self, filepath: str) -> Dict[str, Any]:
        """
        讀取 PDF
        
        Args:
            filepath: 檔案路徑（相對於 /workspace）
        
        Returns:
            {"success": bool, "data": str, "error": Optional[str]}
        """
        try:
            import pdfplumber
            
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
            
            content = []
            with pdfplumber.open(abs_path) as pdf:
                for i, page in enumerate(pdf.pages[:5]):
                    text = page.extract_text()
                    if text:
                        content.append(f"--- 第 {i+1} 頁 ---\n{text}")
            
            return {
                "success": True,
                "data": f"📕 PDF 內容:\n\n" + "\n\n".join(content)
            }
        except ImportError:
            return {
                "success": False,
                "error": "缺少 pdfplumber 模組：pip install pdfplumber"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"讀取 PDF 失敗：{str(e)}"
            }
