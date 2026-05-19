# tools/knowledge/meta_generator_tool.py
"""
Knowledge Meta Generator Tool

功能：為知識庫生成 meta.json（使用 LLM 生成摘要與關鍵字）
使用場景：初始化知識庫、更新知識庫 Meta
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

from tools.base import BaseTool


class MetaGeneratorTool(BaseTool):
    """Knowledge Meta Generator Tool"""
    
    name = "rebuild_knowledge_meta"
    description = "重新生成知識庫的 meta.json（需要通關密語）"
    
    parameters = {
        "type": "object",
        "properties": {
            "knowledge_id": {
                "type": "string",
                "description": "知識庫 ID，例如 'ubitus'。如果為空則重新生成所有知識庫"
            },
            "passphrase": {
                "type": "string",
                "description": "通關密語"
            }
        },
        "required": ["passphrase"]
    }
    
    def __init__(
        self,
        knowledge_base_path: str = "/workspace/knowledge",
        llm_client: Optional[Any] = None,
        llm_model: str = "Qwen/Qwen3.5-397B-A17B-FP8"
    ):
        """
        初始化
        
        Args:
            knowledge_base_path: Knowledge 基礎路徑
            llm_client: LLM 客戶端（可選）
            llm_model: LLM 模型名稱
        """
        self.knowledge_base_path = knowledge_base_path
        self.llm = llm_client
        self.llm_model = llm_model
    
    def execute(
        self,
        knowledge_id: str,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        為單一知識庫生成 meta.json
        
        Args:
            knowledge_id: Knowledge ID（如 "ubitus"）
            force: 是否強制重新生成（覆蓋現有 meta.json）
        
        Returns:
            {"success": bool, "data": meta_dict, "error": Optional[str]}
        """
        try:
            knowledge_path = Path(self.knowledge_base_path) / knowledge_id
            meta_path = knowledge_path / "meta.json"
            
            # 檢查目錄是否存在
            if not knowledge_path.exists():
                return {
                    "success": False,
                    "error": f"Knowledge directory not found: {knowledge_id}"
                }
            
            # 檢查是否已存在
            if meta_path.exists() and not force:
                return {
                    "success": True,
                    "data": {
                        "message": "meta.json already exists",
                        "meta": json.load(open(meta_path, 'r', encoding='utf-8'))
                    }
                }
            
            # 收集所有 .txt 文件
            txt_files = list(knowledge_path.glob("*.txt"))
            if not txt_files:
                return {
                    "success": False,
                    "error": f"No .txt files found in {knowledge_id}"
                }
            
            # 生成每個文件的 meta
            files_meta = []
            for txt_file in txt_files:
                file_meta = self._generate_file_meta(txt_file)
                files_meta.append(file_meta)
            
            # 組合 meta
            meta = {
                "version": "1.0",
                "generated_at": datetime.utcnow().isoformat() + "Z",
                "knowledge_id": knowledge_id,
                "files": files_meta
            }
            
            # 寫入 meta.json
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(meta, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "data": {
                    "message": f"Generated meta.json for {knowledge_id}",
                    "file_count": len(files_meta),
                    "meta": meta
                }
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error generating meta: {str(e)}"
            }
    
    def _generate_file_meta(self, file_path: Path) -> Dict[str, Any]:
        """
        為單一文件生成 meta
        
        Args:
            file_path: 文件路徑
        
        Returns:
            文件 meta 字典
        """
        # 讀取文件內容（前 3000 字）
        content = file_path.read_text(encoding='utf-8')
        content_preview = content[:3000]
        
        # 如果沒有 LLM，使用基本資訊
        if not self.llm:
            return {
                "filename": file_path.name,
                "summary": f"文件：{file_path.name}（{len(content)} 字）",
                "keywords": [file_path.stem],
                "size_bytes": len(content.encode('utf-8')),
                "line_count": len(content.splitlines())
            }
        
        # 使用 LLM 生成摘要與關鍵字
        prompt = f"""
以下是文件內容：
{content_preview}

請生成：
1. 一句話摘要（50-100 字，說明這份文件的主要內容）
2. 5-10 個關鍵字（用來說明文件主題）

請用 JSON 格式回應：
{{
  "summary": "摘要內容",
  "keywords": ["關鍵字 1", "關鍵字 2", "..."]
}}
"""
        try:
            llm_response = self._call_llm(prompt)
            # 解析 JSON（可能需要清理）
            llm_response = llm_response.strip()
            if llm_response.startswith('```json'):
                llm_response = llm_response[7:]
            if llm_response.endswith('```'):
                llm_response = llm_response[:-3]
            
            file_meta = json.loads(llm_response.strip())
            
            return {
                "filename": file_path.name,
                "summary": file_meta.get("summary", f"文件：{file_path.name}"),
                "keywords": file_meta.get("keywords", [file_path.stem]),
                "size_bytes": len(content.encode('utf-8')),
                "line_count": len(content.splitlines())
            }
        except Exception as e:
            print(f"    ⚠️  LLM 生成失敗：{e}，使用基本資訊")
            return {
                "filename": file_path.name,
                "summary": f"文件：{file_path.name}（{len(content)} 字）",
                "keywords": [file_path.stem],
                "size_bytes": len(content.encode('utf-8')),
                "line_count": len(content.splitlines())
            }
    
    def _call_llm(self, prompt: str) -> str:
        """
        調用 LLM
        
        Args:
            prompt: 提示詞
        
        Returns:
            LLM 回應
        """
        if hasattr(self.llm, 'generate'):
            # 自定義 generate 方法
            return self.llm.generate(prompt)
        elif hasattr(self.llm, 'chat') and hasattr(self.llm.chat, 'completions'):
            # OpenAI 客戶端
            response = self.llm.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=500
            )
            return response.choices[0].message.content
        else:
            raise ValueError("Unsupported LLM client")
    
    def execute_all(
        self,
        force: bool = False
    ) -> Dict[str, Any]:
        """
        為所有知識庫生成 meta.json
        
        Args:
            force: 是否強制重新生成
        
        Returns:
            {"success": bool, "data": {...}, "error": Optional[str]}
        """
        try:
            base_path = Path(self.knowledge_base_path)
            if not base_path.exists():
                return {
                    "success": False,
                    "error": f"Knowledge base path not found: {self.knowledge_base_path}"
                }
            
            all_metas = {}
            success_count = 0
            error_count = 0
            
            for knowledge_dir in base_path.iterdir():
                if knowledge_dir.is_dir():
                    result = self.execute(knowledge_dir.name, force)
                    if result["success"]:
                        all_metas[knowledge_dir.name] = result["data"]
                        success_count += 1
                    else:
                        all_metas[knowledge_dir.name] = {"error": result["error"]}
                        error_count += 1
            
            return {
                "success": True,
                "data": {
                    "message": f"Processed {success_count + error_count} knowledge bases",
                    "success_count": success_count,
                    "error_count": error_count,
                    "metas": all_metas
                }
            }
        
        except Exception as e:
            return {
                "success": False,
                "error": f"Error processing all knowledge bases: {str(e)}"
            }
