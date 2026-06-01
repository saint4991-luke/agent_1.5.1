"""
醫療展 Virtual Human Agent - UbiChan × 小護士

醫療展場景專用模組，支持雙機器人協作：
- UbiChan：虛擬人（Kiosk 螢幕）— 對話接待、需求判斷、指令下達
- 小護士：引導機器人（地面）— 帶路引導、物品運送、現場互動

根據 MED_UBIAGENT 規格文檔 v1.0 實現
"""

from .config_loader import MedUbiConfigLoader
from .output_formatter import MedUbiOutputFormatter
from .robot_action_generator import RobotActionGenerator, RobotAction
from .api import init_med_ubichan_api, router

__all__ = [
    'MedUbiConfigLoader',
    'MedUbiOutputFormatter',
    'RobotActionGenerator',
    'RobotAction',
    'init_med_ubichan_api',
    'router'
]
