"""
測試 LLM Service

用法：
python -m agent.med_ubichan.test_llm_service

注意：需要設置環境變數 UBILM_API_KEY
"""

import asyncio
import json
import os
from pathlib import Path
import sys

# 添加父目錄到 Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from med_ubichan.llm_service import UbiLLMService, MedUbiLLMService, create_llm_service


async def test_grant_api():
    """測試 Grant API"""
    print("=" * 60)
    print("測試 Grant API")
    print("=" * 60)
    
    api_key = os.getenv("UBILM_API_KEY")
    if not api_key:
        print("❌ 請設置環境變數 UBILM_API_KEY")
        return None
    
    service = UbiLLMService(api_key=api_key)
    
    try:
        api_token, api_endpoint = await service._grant_token()
        print(f"✅ Grant API 成功")
        print(f"   api_token: {api_token[:20]}...")
        print(f"   api_endpoint: {api_endpoint}")
        return service
    except Exception as e:
        print(f"❌ Grant API 失敗：{e}")
        return None


async def test_chat_completions(service: UbiLLMService):
    """測試 Chat Completions API"""
    print("\n" + "=" * 60)
    print("測試 Chat Completions API")
    print("=" * 60)
    
    messages = [
        {"role": "system", "content": "你是一個助手。"},
        {"role": "user", "content": "你好，請自我介紹。"}
    ]
    
    try:
        response = await service.chat_async(
            messages=messages,
            temperature=0.7,
            max_tokens=500
        )
        print(f"✅ Chat API 成功")
        print(f"   回應長度：{len(response)} 字元")
        print(f"\n📄 回應內容：")
        print(response[:300] + "..." if len(response) > 300 else response)
        return True
    except Exception as e:
        print(f"❌ Chat API 失敗：{e}")
        return False


async def test_med_ubichan_prompt():
    """測試醫療展 Prompt"""
    print("\n" + "=" * 60)
    print("測試醫療展 Prompt")
    print("=" * 60)
    
    api_key = os.getenv("UBILM_API_KEY")
    if not api_key:
        print("❌ 請設置環境變數 UBILM_API_KEY")
        return False
    
    service = create_llm_service(api_key=api_key)
    
    # 測試 Prompt
    prompt = """# 角色風格
你是一個醫療展 Virtual Human 助手 UbiChan。

# 輸出規格
請按照以下 JSON 格式輸出：
{
    "ToUbiChan": "<情緒><語言>內容<sbr>...",
    "ToBaxiaomi": {
        "Steps": [...],
        "Steps_Descripts": "..."
    }
}

# 知識庫內容
醫療展場地資訊：櫃台在入口處，掛號處在 A 區，藥局在 B 區。

# 小護士 Action 說明
- navigate: 導航到指定地點（counter, registration, pharmacy）
- speak: 播放語音
- pickup_item: 拾取物品
- cancel: 停止動作

# 對話歷史
（無）

# 用戶問題
掛號處在哪？
"""
    
    try:
        result = await service.generate_med_ubichan_response(
            prompt=prompt,
            temperature=0.7,
            max_tokens=2048
        )
        
        print(f"✅ LLM 回應生成：{'成功' if result['success'] else '失敗'}")
        
        if result['success']:
            parsed = result['parsed']
            print(f"\n📋 ToUbiChan:")
            print(parsed['ToUbiChan'][:200] + "..." if len(parsed['ToUbiChan']) > 200 else parsed['ToUbiChan'])
            
            print(f"\n🤖 ToBaxiaomi.Steps 數量：{len(parsed['ToBaxiaomi']['Steps'])}")
            print(f"📝 Steps_Descripts:")
            print(parsed['ToBaxiaomi']['Steps_Descripts'][:200] + "..." if len(parsed['ToBaxiaomi']['Steps_Descripts']) > 200 else parsed['ToBaxiaomi']['Steps_Descripts'])
        else:
            print(f"❌ 錯誤：{result['error']}")
        
        return result['success']
    
    except Exception as e:
        print(f"❌ 測試失敗：{e}")
        return False


async def test_retry_mechanism():
    """測試重試機制"""
    print("\n" + "=" * 60)
    print("測試重試機制")
    print("=" * 60)
    
    api_key = os.getenv("UBILM_API_KEY")
    if not api_key:
        print("❌ 請設置環境變數 UBILM_API_KEY")
        return False
    
    service = create_llm_service(api_key=api_key)
    
    messages = [
        {"role": "user", "content": "請測試重試機制。"}
    ]
    
    try:
        response = await service.chat_with_retry(
            messages=messages,
            retry_count=2
        )
        print(f"✅ 重試機制測試成功")
        print(f"   回應：{response[:100]}...")
        return True
    except Exception as e:
        print(f"❌ 重試機制測試失敗：{e}")
        return False


async def main():
    """主測試函數"""
    print("\n🦐 醫療展 LLM Service 測試\n")
    
    # 1. 測試 Grant API
    service = await test_grant_api()
    if not service:
        print("\n⚠️ 跳過後續測試（Grant API 失敗）")
        return
    
    # 2. 測試 Chat Completions API
    await test_chat_completions(service)
    
    # 3. 測試醫療展 Prompt
    await test_med_ubichan_prompt()
    
    # 4. 測試重試機制
    await test_retry_mechanism()
    
    print("\n" + "=" * 60)
    print("測試完成！")
    print("=" * 60)


if __name__ == "__main__":
    # 從環境變數讀取 API Key
    api_key = os.getenv("UBILM_API_KEY")
    if not api_key:
        print("⚠️ 請設置環境變數 UBILM_API_KEY")
        print("範例：export UBILM_API_KEY='your_api_key_here'")
    
    asyncio.run(main())
