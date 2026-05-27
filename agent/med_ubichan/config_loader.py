"""
醫療展 UbiChan 配置載入器

載入醫療展場景的虛擬人配置（YAML 格式）
支持地點定義、Intent 分類、豹小秘 Action 配置
"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime


class MedUbiConfigLoader:
    """醫療展 UbiChan 配置載入器（YAML 格式）"""
    
    # 醫療展地點定義（根據 MED_UBIAGENT.md）
    VALID_LOCATIONS = ['counter', 'registration', 'pharmacy']
    
    def __init__(self, personas_path: str = "/workspace/personas"):
        """
        初始化 MedUbiConfigLoader
        
        Args:
            personas_path: personas 目錄路徑
        """
        self.personas_path = Path(personas_path)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_all()
    
    def _load_all(self):
        """預先載入所有醫療展相關 CONFIG 到記憶體"""
        if not self.personas_path.exists():
            print(f"⚠️  personas 目錄不存在：{self.personas_path}")
            return
        
        # 掃描所有 persona 目錄（只載入醫療展相關）
        persona_dirs = [d for d in self.personas_path.iterdir() if d.is_dir()]
        if not persona_dirs:
            print(f"⚠️  personas 目錄為空：{self.personas_path}")
            return
        
        for persona_dir in persona_dirs:
            config_file = persona_dir / "config.yaml"
            if not config_file.exists():
                continue
            
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                
                # 只載入醫療展相關的 persona（例如：med_ubichan）
                persona_id = config.get('persona_id', persona_dir.name)
                if not persona_id.startswith('med_'):
                    continue
                
                # 驗證配置
                self._validate(config, str(config_file))
                
                # 存入快取
                self._cache[persona_id] = config
                print(f"✅ 載入醫療展 CONFIG: {persona_id}")
            
            except Exception as e:
                print(f"❌ 載入 CONFIG 失敗 {config_file}: {e}")
        
        print(f"✅ 預先載入 {len(self._cache)} 個醫療展虛擬人配置")
    
    def _validate(self, config: Dict[str, Any], filename: str):
        """
        驗證醫療展 CONFIG 必要欄位
        
        必要結構：
        ```yaml
        persona_id: med_ubichan
        display_name: 優必醬（醫療展）
        
        style:
          file: style.md
        
        output_format: virtual_human
        
        # 醫療展專用配置
        med_expo:
          locations:
            - counter
            - registration
            - pharmacy
          intent_mapping:
            registration:
              keywords: ["掛號", "登記", "報到"]
              action: navigate
              target: registration
            pharmacy:
              keywords: ["拿藥", "取藥", "藥品"]
              action: pickup_item
              location: pharmacy
            cancel:
              keywords: ["停止", "取消", "不要了"]
              action: cancel
            info_location:
              keywords: ["哪裡", "怎麼走", "在哪"]
              action: navigate
              target: auto  # 根據地點自動判斷
        
        knowledge:
          enabled: true
          folders:
            - medical_expo/
        
        metadata:
          version: "1.0"
          spec: "MED_UBIAGENT"
        ```
        
        Args:
            config: CONFIG 字典
            filename: 檔案名稱（用於錯誤訊息）
        """
        # 必要欄位：persona_id, style, output_format
        required_fields = ['persona_id', 'style', 'output_format']
        missing = [field for field in required_fields if field not in config]
        
        if missing:
            raise ValueError(f"{filename}: 缺少必要欄位：{', '.join(missing)}")
        
        # 驗證 style 結構
        if 'style' in config:
            if not isinstance(config['style'], dict):
                raise ValueError(f"{filename}: style 必須是物件")
            if 'file' not in config['style']:
                raise ValueError(f"{filename}: style 缺少 file 欄位")
        
        # 驗證 output_format
        if 'output_format' in config:
            valid_formats = ['med_ubichan', 'virtual_human', 'plain', 'markdown']
            if config['output_format'] not in valid_formats:
                raise ValueError(f"{filename}: output_format 必須是 {valid_formats} 之一")
        
        # 驗證 med_expo 配置（醫療展專用）
        if 'med_expo' in config:
            med_config = config['med_expo']
            
            # 驗證 locations
            if 'locations' in med_config:
                if not isinstance(med_config['locations'], list):
                    raise ValueError(f"{filename}: med_expo.locations 必須是列表")
                for loc in med_config['locations']:
                    if loc not in self.VALID_LOCATIONS:
                        raise ValueError(f"{filename}: 無效地點 '{loc}'，必須是 {self.VALID_LOCATIONS}")
            
            # 驗證 intent_mapping
            if 'intent_mapping' in med_config:
                if not isinstance(med_config['intent_mapping'], dict):
                    raise ValueError(f"{filename}: med_expo.intent_mapping 必須是物件")
                
                for intent_name, intent_config in med_config['intent_mapping'].items():
                    if not isinstance(intent_config, dict):
                        raise ValueError(f"{filename}: intent '{intent_name}' 必須是物件")
                    if 'keywords' not in intent_config:
                        raise ValueError(f"{filename}: intent '{intent_name}' 缺少 keywords 欄位")
                    if not isinstance(intent_config['keywords'], list):
                        raise ValueError(f"{filename}: intent '{intent_name}' 的 keywords 必須是列表")
        
        # 驗證 knowledge（可選）
        if 'knowledge' in config:
            if not isinstance(config['knowledge'], dict):
                raise ValueError(f"{filename}: knowledge 必須是物件")
            if 'enabled' not in config['knowledge']:
                raise ValueError(f"{filename}: knowledge 缺少 enabled 欄位")
            if config['knowledge'].get('enabled') and 'folders' not in config['knowledge']:
                raise ValueError(f"{filename}: knowledge.enabled=true 時需要 folders 欄位")
    
    def get(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """
        從快取取得 CONFIG（O(1)）
        
        Args:
            persona_id: 虛擬人 ID
        
        Returns:
            CONFIG 字典，如果不存在則返回 None
        """
        if persona_id not in self._cache:
            print(f"⚠️  未知的醫療展虛擬人 ID: {persona_id}")
            return None
        
        return self._cache[persona_id]
    
    def has(self, persona_id: str) -> bool:
        """
        檢查 CONFIG 是否存在
        
        Args:
            persona_id: 虛擬人 ID
        
        Returns:
            True 如果存在
        """
        return persona_id in self._cache
    
    def get_all_ids(self) -> List[str]:
        """
        取得所有醫療展虛擬人 ID 列表
        
        Returns:
            ID 列表
        """
        return list(self._cache.keys())
    
    def get_intent_mapping(self, persona_id: str) -> Optional[Dict[str, Any]]:
        """
        取得 Intent 分類映射
        
        Args:
            persona_id: 虛擬人 ID
        
        Returns:
            Intent 映射字典，如果不存在則返回 None
        """
        config = self.get(persona_id)
        if not config:
            return None
        
        med_config = config.get('med_expo', {})
        return med_config.get('intent_mapping', {})
    
    def get_locations(self, persona_id: str) -> List[str]:
        """
        取得地點列表
        
        Args:
            persona_id: 虛擬人 ID
        
        Returns:
            地點列表
        """
        config = self.get(persona_id)
        if not config:
            return self.VALID_LOCATIONS
        
        med_config = config.get('med_expo', {})
        return med_config.get('locations', self.VALID_LOCATIONS)
    
    def reload(self, persona_id: str = None):
        """
        重新載入 CONFIG（用於開發環境）
        
        Args:
            persona_id: 指定重新載入的 ID，如果為 None 則重新載入所有
        """
        if persona_id:
            config_file = self.personas_path / persona_id / "config.yaml"
            if config_file.exists():
                with open(config_file, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f)
                self._validate(config, str(config_file))
                self._cache[persona_id] = config
                print(f"🔄 重新載入醫療展 CONFIG: {persona_id}")
        else:
            self._cache.clear()
            self._load_all()
