# tools/file_system/read_excel_tool.py
"""
Read Excel Tool - 讀取 Excel 檔案
"""

from pathlib import Path
from typing import Any, Dict

from tools.base import BaseTool


class ReadExcelTool(BaseTool):
    """讀取 Excel Tool"""
    
    name = "read_excel"
    description = "讀取工作區內的 Excel 檔案（限定在 /workspace 內）"
    
    parameters = {
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "Excel 檔案路徑（相對於 /workspace）"
            },
            "rows": {
                "type": "integer",
                "description": "讀取行數（預設 10）"
            }
        },
        "required": ["filepath"]
    }
    
    def __init__(self, workspace_path: str = "/workspace"):
        self.workspace_path = Path(workspace_path)
    
    def execute(self, filepath: str, rows: int = 10) -> Dict[str, Any]:
        """
        讀取 Excel
        
        Args:
            filepath: 檔案路徑（相對於 /workspace）
            rows: 讀取行數（預設 10）
        
        Returns:
            {"success": bool, "data": str, "error": Optional[str]}
        """
        try:
            import pandas as pd
            
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
            
            df = pd.read_excel(abs_path, nrows=rows)
            content = f"📊 Excel 內容 (前{rows}列):\n{df.to_string()}"
            
            return {
                "success": True,
                "data": content
            }
        except ImportError:
            return {
                "success": False,
                "error": "缺少 pandas 模組：pip install pandas openpyxl"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"讀取 Excel 失敗：{str(e)}"
            }
