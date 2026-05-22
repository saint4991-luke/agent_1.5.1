"""
測試 Prompt Builder 和 Output Parser

用法：
python -m agent.med_ubichan.test_prompt_builder
"""

import asyncio
import json
from pathlib import Path
import sys

# 添加父目錄到 Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from med_ubichan.prompt_builder import MedUbiPromptBuilder, MedUbiOutputParser


async def test_prompt_builder():
    """測試 Prompt 構建器"""
    print("=" * 60)
    print("測試 Prompt Builder")
    print("=" * 60)
    
    # 初始化
    workspace_path = Path("/tmp/agent_repo")
    builder = MedUbiPromptBuilder(workspace_path)
    
    # 測試配置
    config = {
        "persona_id": "med_ubichan_v1",
        "style": {"file": "style.md"},
        "output_format": "med_ubichan",
        "version": "v1.0"
    }
    
    # 測試用戶消息
    user_message = "掛號處在哪？"
    
    # 測試對話歷史
    conversation_history = []
    
    # 測試意圖分類結果
    intent_result = {
        "intent": "info_location",
        "target_location": "registration",
        "requires_robot": True
    }
    
    # 模擬 PromptLoader
    class MockPromptLoader:
        def load_prompt(self, output_format):
            return "請按照 JSON 格式輸出回應。"
        
        def load_prompt_for_llm1(self, output_format, config):
            return "請按照 JSON 格式輸出回應（LLM1 版本）。"
    
    prompt_loader = MockPromptLoader()
    
    # 構建 Prompt
    print("\n📝 構建 Prompt...")
    prompt, emotion_enabled = await builder._build_prompt(
        config=config,
        user_message=user_message,
        conversation_history=conversation_history,
        prompt_loader_obj=prompt_loader,
        knowledge_content="醫療展場地資訊：櫃台在入口處，掛號處在 A 區，藥局在 B 區。",
        knowledge_meta="醫療展 Meta 資訊",
        intent_result=intent_result,
        is_llm1=False
    )
    
    print(f"✅ emotion_enabled: {emotion_enabled}")
    print(f"\n📋 Prompt 長度：{len(prompt)} 字元")
    print(f"\n📄 Prompt 預覽：")
    print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
    
    return prompt


def test_output_parser():
    """測試輸出解析器"""
    print("\n" + "=" * 60)
    print("測試 Output Parser")
    print("=" * 60)
    
    parser = MedUbiOutputParser()
    
    # 測試用例 1: 正確的 JSON 格式
    print("\n📋 測試用例 1: 正確的 JSON 格式")
    llm_response_1 = """{
    "ToUbiChan": "<neutral><tw>掛號處在展場 A 區<sbr>我請豹小秘帶你過去<sbr>請跟著它走<sbr>",
    "ToBaxiaomi": {
        "Steps": [
            {
                "action": "navigate",
                "params": {"target": "counter"},
                "speech": ""
            },
            {
                "action": "speak",
                "params": {"speech": "你好，請跟我來掛號處"},
                "speech": ""
            },
            {
                "action": "navigate",
                "params": {"target": "registration"},
                "speech": ""
            },
            {
                "action": "speak",
                "params": {"speech": "掛號處到了，請先抽號碼牌"},
                "speech": ""
            }
        ],
        "Steps_Descripts": "第一步，讓豹小秘移動到櫃台前方。\\n第二步，讓豹小秘對 user 說 \"你好，請跟我來掛號處\"。\\n第三步，讓豹小秘導航到掛號處。\\n第四步，讓豹小秘對 user 說 \"掛號處到了，請先抽號碼牌\""
    }
}"""
    
    result_1 = parser.parse_llm_response(llm_response_1)
    print(f"✅ 解析成功：{result_1['success']}")
    print(f"   ToUbiChan: {result_1['ToUbiChan'][:50]}...")
    print(f"   Steps 數量：{len(result_1['ToBaxiaomi']['Steps'])}")
    print(f"   Steps_Descripts: {result_1['ToBaxiaomi']['Steps_Descripts'][:50]}...")
    
    # 驗證 UbiChan 格式
    is_valid, error_msg = parser.validate_ubichan_format(result_1['ToUbiChan'])
    print(f"✅ UbiChan 格式驗證：{'通過' if is_valid else f'失敗 - {error_msg}'}")
    
    # 驗證 Steps 格式
    is_valid, error_msg = parser.validate_steps(result_1['ToBaxiaomi']['Steps'])
    print(f"✅ Steps 格式驗證：{'通過' if is_valid else f'失敗 - {error_msg}'}")
    
    # 測試用例 2: 包含 Markdown 代碼塊的 JSON
    print("\n📋 測試用例 2: 包含 Markdown 代碼塊")
    llm_response_2 = """好的，這是我的回應：

```json
{
    "ToUbiChan": "<happy><tw>藥局在展場 B 區<sbr>我請豹小秘帶你過去<sbr>",
    "ToBaxiaomi": {
        "Steps": [
            {
                "action": "navigate",
                "params": {"target": "pharmacy"},
                "speech": ""
            }
        ],
        "Steps_Descripts": "第一步，讓豹小秘導航到藥局。"
    }
}
```

希望這對你有幫助！"""
    
    result_2 = parser.parse_llm_response(llm_response_2)
    print(f"✅ 解析成功：{result_2['success']}")
    print(f"   ToUbiChan: {result_2['ToUbiChan']}")
    
    # 測試用例 3: 錯誤格式（缺少欄位）
    print("\n📋 測試用例 3: 錯誤格式（缺少 ToBaxiaomi）")
    llm_response_3 = """{
    "ToUbiChan": "<neutral><tw>測試<sbr>"
}"""
    
    result_3 = parser.parse_llm_response(llm_response_3)
    print(f"✅ 解析結果：{result_3['success']}")
    print(f"   錯誤訊息：{result_3['error']}")
    
    # 測試用例 4: 提取函數
    print("\n📋 測試用例 4: 提取函數")
    ubichan = parser.extract_ubichan_content(result_1)
    steps_desc = parser.extract_steps_descripts(result_1)
    steps = parser.extract_steps(result_1)
    
    print(f"✅ extract_ubichan_content: {ubichan[:50]}...")
    print(f"✅ extract_steps_descripts: {steps_desc[:50]}...")
    print(f"✅ extract_steps: {len(steps)} 個步驟")
    
    return result_1, result_2, result_3


async def main():
    """主測試函數"""
    print("\n🦐 醫療展 Prompt Builder & Output Parser 測試\n")
    
    # 測試 Prompt Builder
    prompt = await test_prompt_builder()
    
    # 測試 Output Parser
    results = test_output_parser()
    
    print("\n" + "=" * 60)
    print("測試完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
