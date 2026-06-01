"""
UbiBOS Device Service
實作 UbiBOS Platform API v1 的 Device API
- 2.1.3. Trigger a intent to Device
- 2.1.5. Get Device Status
"""

import os
import httpx
from typing import Optional, Dict, Any
from pathlib import Path


# 環境變數配置
UBIBOS_BASE_URL = os.getenv("UBIBOS_BASE_URL", "https://ubibos-preview.ubitus.ai")
UBIBOS_DEVICE_SN = os.getenv("UBIBOS_DEVICE_SN", "")  # 小護士設備序號


class DeviceService:
    """UbiBOS Device Service"""
    
    def __init__(self, base_url: Optional[str] = None, device_sn: Optional[str] = None):
        """
        初始化 Device Service
        
        Args:
            base_url: UbiBOS API 基礎 URL
            device_sn: 設備序號（小護士）
        """
        self.base_url = base_url or UBIBOS_BASE_URL
        self.device_sn = device_sn or UBIBOS_DEVICE_SN
    
    async def trigger_intent(self, input: str, device_sn: Optional[str] = None) -> Dict[str, Any]:
        """
        2.1.3. Trigger a intent to Device
        
        發送 intent 到設備（小護士）
        
        Args:
            input: intent 輸入內容（steps_description）
            device_sn: 設備序號，如果為 None 則使用預設值
        
        Returns:
            Dict containing response status and data
        
        Raises:
            httpx.HTTPError: If request fails
        """
        sn = device_sn or self.device_sn
        
        if not sn:
            raise ValueError("device_sn is required. Please set UBIBOS_DEVICE_SN environment variable or pass it as argument.")
        
        url = f"{self.base_url}/nagato/api/v1/devices/intents"
        
        payload = {
            "deviceSN": sn,
            "input": input
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            
            return {
                "status_code": response.status_code,
                "status": "Accepted" if response.status_code == 202 else "Unknown",
                "deviceSN": sn,
                "input": input
            }
    
    async def get_device_status(self, device_sn: Optional[str] = None) -> Dict[str, Any]:
        """
        2.1.5. Get Device Status
        
        獲取設備狀態
        
        Args:
            device_sn: 設備序號，如果為 None 則使用預設值
        
        Returns:
            Dict containing device status
        
        Raises:
            httpx.HTTPError: If request fails
        """
        sn = device_sn or self.device_sn
        
        if not sn:
            raise ValueError("device_sn is required. Please set UBIBOS_DEVICE_SN environment variable or pass it as argument.")
        
        url = f"{self.base_url}/nagato/api/v1/devices/{sn}/status"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            response.raise_for_status()
            
            return response.json()


# 全域實例（可選）
_device_service: Optional[DeviceService] = None


def get_device_service() -> DeviceService:
    """獲取 DeviceService 單例"""
    global _device_service
    if _device_service is None:
        _device_service = DeviceService()
    return _device_service


async def send_intent_to_device(steps_description: str, device_sn: Optional[str] = None) -> Dict[str, Any]:
    """
    便捷函數：發送 steps_description 到小護士設備
    
    Args:
        steps_description: 步驟描述字符串
        device_sn: 設備序號（可選）
    
    Returns:
        Dict containing response status and data
    """
    service = get_device_service()
    return await service.trigger_intent(input=steps_description, device_sn=device_sn)
