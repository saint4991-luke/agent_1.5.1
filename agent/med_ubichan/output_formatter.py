"""
醫療展 UbiChan 輸出格式化器

根據 MED_UBIAGENT 規格文檔 v1.0 格式化輸出：
- UbiChan 輸出：情緒標籤 + 語言標籤 + <sbr> 斷句
- 符合 docs/03_specs/09_OUTPUT_FORMAT.md 規格
"""

from typing import Dict, Any, Optional, List
from datetime import datetime


class MedUbiOutputFormatter:
    """醫療展 UbiChan 輸出格式化器"""
    
    # 支持的情緒標籤
    VALID_EMOTIONS = [
        'neutral', 'happy', 'sad', 'angry', 'surprised',
        'excited', 'thinking', 'embarrassed', 'concerned',
        'serious', 'encouraging', 'empathetic'
    ]
    
    # 支持的語言標籤
    VALID_LANGS = {
        'tw': 'tw (zh)',  # 繁體中文
        'zh': 'tw (zh)',  # 預設繁體中文
        'cn': 'cn (zh)',  # 簡體中文
        'en': 'en',       # 英文
        'ja': 'ja',       # 日文
    }
    
    def __init__(self, default_emotion: str = 'neutral', default_lang: str = 'tw'):
        """
        初始化輸出格式化器
        
        Args:
            default_emotion: 預設情緒標籤
            default_lang: 預設語言標籤
        """
        self.default_emotion = default_emotion
        self.default_lang = default_lang
    
    def format_ubichan_response(
        self,
        text: str,
        emotion: Optional[str] = None,
        lang: Optional[str] = None,
        add_options: Optional[List[str]] = None,
        add_link: Optional[str] = None,
        add_image: Optional[str] = None,
        add_bg: Optional[str] = None,
        display_only: bool = False
    ) -> str:
        """
        格式化 UbiChan 回應（符合 09_OUTPUT_FORMAT.md 規格）
        
        Args:
            text: 回應文字（可包含多句）
            emotion: 情緒標籤（可選，預設 neutral）
            lang: 語言標籤（可選，預設 tw）
            add_options: 選項按鈕列表（可選）
            add_link: 連結 URL（可選）
            add_image: 圖片 URL（可選）
            add_bg: 背景顏色或 URL（可選）
            display_only: 是否僅顯示不播放 TTS（可選）
        
        Returns:
            格式化後的輸出字串
        
        Example:
            >>> formatter = MedUbiOutputFormatter()
            >>> formatter.format_ubichan_response(
            ...     "好的，豹小秘會帶你去掛號處。請跟著它走。",
            ...     emotion="happy",
            ...     lang="tw"
            ... )
            '<!-- emotion -->happy<!-- /emotion -->\n<!-- lang -->tw (zh)<!-- /lang -->\n\n好的，豹小秘會帶你去掛號處。<sbr>\n請跟著它走。<sbr>\n'
        """
        # 驗證情緒標籤
        if emotion is None:
            emotion = self.default_emotion
        elif emotion not in self.VALID_EMOTIONS:
            print(f"⚠️  未知的情緒標籤 '{emotion}'，使用預設 '{self.default_emotion}'")
            emotion = self.default_emotion
        
        # 轉換語言標籤
        if lang is None:
            lang_tag = self.default_lang
        else:
            lang_tag = self.VALID_LANGS.get(lang, self.default_lang)
        
        # 分割句子並添加 <sbr>
        sentences = self._split_sentences(text)
        sentences_with_sbr = [f"{s}<sbr>" for s in sentences if s.strip()]
        
        # 組合輸出
        output_parts = [
            f"<!-- emotion -->{emotion}<!-- /emotion -->",
            f"<!-- lang -->{lang_tag}<!-- /lang -->",
            ""  # 空行分隔
        ]
        
        # 添加可選 Actions
        if add_options:
            import json
            options_json = json.dumps({"items": add_options}, ensure_ascii=False)
            output_parts.append(f"<!-- options -->{options_json}<!-- /options -->")
        
        if add_link:
            output_parts.append(f"<!-- link -->{add_link}<!-- /link -->")
        
        if add_image:
            output_parts.append(f"<!-- image -->{add_image}<!-- /image -->")
        
        if add_bg:
            output_parts.append(f"<!-- bg -->{add_bg}<!-- /bg -->")
        
        if display_only:
            output_parts.append("<!-- displayonly -->true<!-- /displayonly -->")
        
        # 添加內容
        output_parts.append("\n".join(sentences_with_sbr))
        
        return "\n".join(output_parts)
    
    def _split_sentences(self, text: str) -> List[str]:
        """
        將文字分割成句子
        
        Args:
            text: 原始文字
        
        Returns:
            句子列表
        """
        # 簡單的斷句邏輯：根據句號、問號、驚嘆號分割
        import re
        
        # 移除現有的 <sbr> 標籤
        text = text.replace('<sbr>', '')
        
        # 根據中文句號、問號、驚嘆號分割
        sentences = re.split(r'([。！？!?])', text)
        
        # 合併標點符號到句子中
        result = []
        for i, part in enumerate(sentences):
            part = part.strip()
            if not part:
                continue
            
            # 如果下一個部分是標點符號，合併到當前句子
            if i + 1 < len(sentences) and sentences[i + 1] in '。！？!?':
                result.append(part + sentences[i + 1])
            elif part not in '。！？!?':
                result.append(part)
        
        return result
    
    def extract_emotion(self, text: str) -> str:
        """
        從回應中提取情緒標籤
        
        Args:
            text: 回應文字
        
        Returns:
            情緒標籤，如果找不到則返回 neutral
        """
        import re
        match = re.search(r'<!--\s*emotion\s*-->(\w+)<!--\s*/emotion\s*-->', text)
        return match.group(1) if match else self.default_emotion
    
    def extract_lang(self, text: str) -> str:
        """
        從回應中提取語言標籤
        
        Args:
            text: 回應文字
        
        Returns:
            語言標籤，如果找不到則返回預設
        """
        import re
        match = re.search(r'<!--\s*lang\s*-->([\w\s()]+)<!--\s*/lang\s*-->', text)
        return match.group(1) if match else self.default_lang
    
    def extract_sentences(self, text: str) -> List[str]:
        """
        從回應中提取句子（移除所有 Action 標籤）
        
        Args:
            text: 回應文字
        
        Returns:
            句子列表
        """
        import re
        
        # 移除所有 Action 標籤
        content = text
        for action in ['emotion', 'lang', 'options', 'link', 'image', 'bg', 'displayonly']:
            pattern = rf'<!--\s*{action}\s*>.*?<!--\s*/{action}\s*-->'
            content = re.sub(pattern, '', content, flags=re.DOTALL)
        
        # 移除前後空白
        content = content.strip()
        
        # 根據 <sbr> 分割
        sentences = [s.strip() for s in content.split('<sbr>') if s.strip()]
        
        return sentences
    
    def parse_full_response(self, text: str) -> Dict[str, Any]:
        """
        解析完整的 UbiChan 回應
        
        Args:
            text: 回應文字
        
        Returns:
            {
                "emotion": str,
                "lang": str,
                "sentences": List[str],
                "options": Optional[Dict],
                "link": Optional[str],
                "image": Optional[str],
                "bg": Optional[str],
                "display_only": bool
            }
        """
        import re
        import json
        
        result = {
            "emotion": self.default_emotion,
            "lang": self.default_lang,
            "sentences": [],
            "options": None,
            "link": None,
            "image": None,
            "bg": None,
            "display_only": False
        }
        
        # 提取所有 Actions
        for action in ['emotion', 'lang', 'options', 'link', 'image', 'bg', 'displayonly']:
            pattern = rf'<!--\s*{action}\s*-->(.*?)<!--\s*/{action}\s*-->'
            match = re.search(pattern, text, re.DOTALL)
            if match:
                content = match.group(1).strip()
                
                if action == 'emotion':
                    result['emotion'] = content
                elif action == 'lang':
                    result['lang'] = content
                elif action == 'options':
                    try:
                        result['options'] = json.loads(content)
                    except:
                        print(f"⚠️  解析 options 失敗：{content}")
                elif action == 'link':
                    result['link'] = content
                elif action == 'image':
                    result['image'] = content
                elif action == 'bg':
                    result['bg'] = content
                elif action == 'displayonly':
                    result['display_only'] = (content.lower() == 'true')
        
        # 提取句子
        result['sentences'] = self.extract_sentences(text)
        
        return result
