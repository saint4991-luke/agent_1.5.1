# tools/file_system/read_csv_tool.py
"""
Read CSV Tool - 讀取 CSV 檔案
"""

from pathlib import Path
from typing import Any, Dict

from tools.base import BaseTool


class ReadCsvTool(BaseTool):
    """讀取 CSV Tool"""
    
    name = "read_csv"
    description = "讀取工作區內的 CSV 檔案（限定在 /workspace 內）"
    
    parameters = {
        "type": "object",
        "properties": {
            "filepath": {
                "type": "string",
                "description": "CSV 檔案路徑（相對於 /workspace）"
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
        讀取 CSV
        
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
            
            df = pd.read_csv(abs_path, nrows=rows)
            content = f"📊 CSV 內容 (前{rows}列):\n{df.to_string()}"
            
            return {
                "success": True,
                "data": content
            }
        except ImportError:
            return {
                "success": False,
                "error": "缺少 pandas 模組：pip install pandas"
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"讀取 CSV 失敗：{str(e)}"
            }
