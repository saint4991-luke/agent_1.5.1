"""
豹小秘機器人 Action 生成器

根據 MED_UBIAGENT 規格文檔 v1.0 生成豹小秘 Action：
- JSON 指令格式
- 自然語言步驟描述

支持 Actions：
- navigate: 導航到指定地點
- pickup_item: 在指定地點拾取物品
- speak: 播放語音
- cancel: 停止所有動作
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass


@dataclass
class RobotAction:
    """豹小秘 Action 數據結構"""
    action: str  # navigate, pickup_item, speak, cancel
    params: Dict[str, Any]
    speech: Optional[str] = None
    natural_language_steps: Optional[str] = None
    
    def to_json(self) -> Dict[str, Any]:
        """轉換為 JSON 格式"""
        return {
            "robot": "baxiaomi",
            "action": self.action,
            "params": self.params,
            "speech": self.speech
        }


class RobotActionGenerator:
    """豹小秘 Action 生成器"""
    
    # 醫療展地點定義
    LOCATIONS = {
        'counter': '櫃台',
        'registration': '掛號處',
        'pharmacy': '藥局'
    }
    
    def __init__(self):
        """初始化 Action 生成器"""
        pass
    
    def generate_navigate_action(
        self,
        target: str,
        speech: str,
        user_message: str = "",
        include_steps: bool = True
    ) -> RobotAction:
        """
        生成導航 Action
        
        Args:
            target: 目標地點 ID (counter, registration, pharmacy)
            speech: 豹小秘播放的語音
            user_message: 用戶原始消息（用於生成步驟描述）
            include_steps: 是否包含自然語言步驟描述
        
        Returns:
            RobotAction 物件
        
        Example:
            >>> generator = RobotActionGenerator()
            >>> action = generator.generate_navigate_action(
            ...     target="registration",
            ...     speech="我帶你去掛號處，請跟我來"
            ... )
            >>> action.to_json()
            {
                "robot": "baxiaomi",
                "action": "navigate",
                "params": {"target": "registration"},
                "speech": "我帶你去掛號處，請跟我來"
            }
        """
        # 驗證地點
        if target not in self.LOCATIONS:
            raise ValueError(f"無效地點 '{target}'，必須是 {list(self.LOCATIONS.keys())}")
        
        # 生成 JSON Action
        action = RobotAction(
            action="navigate",
            params={"target": target},
            speech=speech
        )
        
        # 生成自然語言步驟描述
        if include_steps:
            target_name = self.LOCATIONS[target]
            action.natural_language_steps = self._generate_navigate_steps(
                target=target,
                target_name=target_name,
                speech=speech
            )
        
        return action
    
    def _generate_navigate_steps(
        self,
        target: str,
        target_name: str,
        speech: str
    ) -> str:
        """
        生成導航的自然語言步驟描述
        
        Args:
            target: 目標地點 ID
            target_name: 目標地點中文名稱
            speech: 豹小秘播放的語音
        
        Returns:
            自然語言步驟描述字串
        """
        steps = [
            f"第一步，讓豹小秘移動到櫃台（counter）前方。",
            f"第二步，讓豹小秘對 user 說「{speech}」。",
            f"第三步，讓豹小秘導航到{target_name}（{target}）。",
            f"第四步，讓豹小秘對 user 說「{target_name}到了，祝你{self._get_blessing(target)}」。"
        ]
        
        return "\n".join(steps)
    
    def generate_pickup_item_action(
        self,
        location: str,
        item: str,
        speech: str,
        return_location: str = "counter",
        include_steps: bool = True
    ) -> RobotAction:
        """
        生成取物 Action
        
        Args:
            location: 地點 ID (pharmacy)
            item: 物品名稱（例如：藥品）
            speech: 豹小秘播放的語音（對工作人員說）
            return_location: 返回地點 ID（預設 counter）
            include_steps: 是否包含自然語言步驟描述
        
        Returns:
            RobotAction 物件
        """
        # 驗證地點
        if location not in self.LOCATIONS:
            raise ValueError(f"無效地點 '{location}'，必須是 {list(self.LOCATIONS.keys())}")
        
        # 生成 JSON Action
        action = RobotAction(
            action="pickup_item",
            params={
                "location": location,
                "item": item
            },
            speech=speech
        )
        
        # 生成自然語言步驟描述
        if include_steps:
            location_name = self.LOCATIONS[location]
            return_name = self.LOCATIONS.get(return_location, '櫃台')
            action.natural_language_steps = self._generate_pickup_steps(
                location=location,
                location_name=location_name,
                item=item,
                speech=speech,
                return_location=return_location,
                return_name=return_name
            )
        
        return action
    
    def _generate_pickup_steps(
        self,
        location: str,
        location_name: str,
        item: str,
        speech: str,
        return_location: str,
        return_name: str
    ) -> str:
        """
        生成取物的自然語言步驟描述
        
        Args:
            location: 地點 ID
            location_name: 地點中文名稱
            item: 物品名稱
            speech: 豹小秘播放的語音
            return_location: 返回地點 ID
            return_name: 返回地點中文名稱
        
        Returns:
            自然語言步驟描述字串
        """
        steps = [
            f"第一步，讓豹小秘移動到{location_name}（{location}）。",
            f"第二步，讓豹小秘對工作人員說「{speech}」。",
            f"第三步，讓豹小秘等待物品裝載完成。",
            f"第四步，讓豹小秘導航回{return_name}（{return_location}）。",
            f"第五步，讓豹小秘對 user 說「幫你把{item}拿來了，祝你早日康復」。"
        ]
        
        return "\n".join(steps)
    
    def generate_speak_action(
        self,
        speech: str,
        include_steps: bool = False
    ) -> RobotAction:
        """
        生成播放語音 Action
        
        Args:
            speech: 播放的語音內容
            include_steps: 是否包含自然語言步驟描述
        
        Returns:
            RobotAction 物件
        """
        action = RobotAction(
            action="speak",
            params={},
            speech=speech
        )
        
        if include_steps:
            action.natural_language_steps = f"讓豹小秘對 user 說「{speech}」。"
        
        return action
    
    def generate_cancel_action(
        self,
        speech: str = "我要回去櫃台了",
        include_steps: bool = True
    ) -> RobotAction:
        """
        生成取消動作 Action
        
        Args:
            speech: 播放的語音內容
            include_steps: 是否包含自然語言步驟描述
        
        Returns:
            RobotAction 物件
        """
        action = RobotAction(
            action="cancel",
            params={},
            speech=speech
        )
        
        if include_steps:
            action.natural_language_steps = "\n".join([
                "第一步，讓豹小秘停止當前動作。",
                f"第二步，讓豹小秘對 user 說「{speech}」。",
                "第三步，讓豹小秘導航回櫃台（counter）待命區。"
            ])
        
        return action
    
    def _get_blessing(self, target: str) -> str:
        """
        根據目標地點獲取祝福語
        
        Args:
            target: 目標地點 ID
        
        Returns:
            祝福語字串
        """
        blessings = {
            'registration': '掛號順利',
            'pharmacy': '取藥順利',
            'counter': '一切順利'
        }
        return blessings.get(target, '一切順利')
    
    def generate_from_intent(
        self,
        intent: str,
        user_message: str,
        config: Optional[Dict[str, Any]] = None
    ) -> Optional[RobotAction]:
        """
        根據 Intent 生成對應的豹小秘 Action
        
        Args:
            intent: Intent 類型 (registration, pharmacy, cancel, info_location)
            user_message: 用戶原始消息
            config: 配置字典（可選，用於自定義）
        
        Returns:
            RobotAction 物件，如果不匹配則返回 None
        
        Example:
            >>> generator = RobotActionGenerator()
            >>> action = generator.generate_from_intent(
            ...     intent="registration",
            ...     user_message="我想要掛號"
            ... )
        """
        # 根據 Intent 生成對應 Action
        if intent == 'registration':
            return self.generate_navigate_action(
                target='registration',
                speech="你好，請跟我來掛號處"
            )
        
        elif intent == 'pharmacy':
            return self.generate_pickup_item_action(
                location='pharmacy',
                item='藥品',
                speech="藥劑師你好，請把藥品放到我的籃子，並按下按鈕"
            )
        
        elif intent == 'cancel':
            return self.generate_cancel_action(
                speech="我要回去櫃台了"
            )
        
        elif intent == 'info_location':
            # 根據用戶消息判斷目標地點
            target = self._infer_target_from_message(user_message)
            if target:
                target_name = self.LOCATIONS[target]
                return self.generate_navigate_action(
                    target=target,
                    speech=f"{target_name}在{self._get_location_area(target)}，請跟我來"
                )
        
        return None
    
    def _infer_target_from_message(self, message: str) -> Optional[str]:
        """
        從用戶消息推斷目標地點
        
        Args:
            message: 用戶消息
        
        Returns:
            地點 ID，如果無法推斷則返回 None
        """
        message_lower = message.lower()
        
        # 關鍵字匹配
        if any(kw in message_lower for kw in ['掛號', '登記', '報到']):
            return 'registration'
        elif any(kw in message_lower for kw in ['藥', '取藥', '拿藥']):
            return 'pharmacy'
        elif any(kw in message_lower for kw in ['櫃台', '服務台']):
            return 'counter'
        
        return None
    
    def _get_location_area(self, target: str) -> str:
        """
        獲取地點的展區描述
        
        Args:
            target: 地點 ID
        
        Returns:
            展區描述字串
        """
        areas = {
            'counter': '這裡',
            'registration': '展場 A 區',
            'pharmacy': '展場 B 區'
        }
        return areas.get(target, '展場')
    
    def format_complete_output(
        self,
        ubichan_text: str,
        robot_action: Optional[RobotAction],
        emotion: str = "neutral",
        lang: str = "tw"
    ) -> Dict[str, Any]:
        """
        格式化完整的 MED_UBIAGENT 輸出
        
        Args:
            ubichan_text: UbiChan 回應文字
            robot_action: 豹小秘 Action（可選，None 表示無需行動）
            emotion: 情緒標籤
            lang: 語言標籤
        
        Returns:
            {
                "ubichan_output": str,  # UbiChan 輸出（含情緒標籤）
                "robot_json": Optional[Dict],  # 豹小秘 JSON 指令
                "robot_steps": Optional[str]  # 豹小秘自然語言步驟
            }
        """
        from .output_formatter import MedUbiOutputFormatter
        
        formatter = MedUbiOutputFormatter()
        
        # 格式化 UbiChan 輸出
        ubichan_output = formatter.format_ubichan_response(
            text=ubichan_text,
            emotion=emotion,
            lang=lang
        )
        
        # 格式化豹小秘輸出
        robot_json = robot_action.to_json() if robot_action else None
        robot_steps = robot_action.natural_language_steps if robot_action else None
        
        return {
            "ubichan_output": ubichan_output,
            "robot_json": robot_json,
            "robot_steps": robot_steps
        }
