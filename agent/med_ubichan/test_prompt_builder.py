#!/usr/bin/env python3
"""
測試 Prompt Builder 和 Output Parser
"""

import sys
import asyncio
from pathlib import Path

# 添加父目錄到路徑
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from agent.med_ubichan.prompt_builder import MedUbiPromptBuilder, MedUbiOutputParser


async def test_prompt_builder():
    """測試 Prompt Builder"""
    print("=" * 60)
    print("測試 Prompt Builder")
    print("=" * 60)
    
    # 獲取正確的 workspace 路徑（相對於測試腳本位置）
    workspace_path = Path(__file__).parent.parent.parent / 'workspace'
    print(f"\n📂 Workspace 路徑：{workspace_path}")
    print(f"   存在：{workspace_path.exists()}")
    
    # 載入 config.yaml
    config_path = workspace_path / 'personas' / 'MED_UBIAGENT' / 'config.yaml'
    print(f"\n📄 Config 路徑：{config_path}")
    print(f"   存在：{config_path.exists()}")
    
    if not config_path.exists():
        print(f"⚠️  Config 文件不存在，使用預設配置")
        config = {
            "persona_id": "med-ubichan",
            "style": {"file": "style.md"},
            "output_format": "med_ubichan",
            "version": "v1.0"
        }
    else:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        print(f"✅ Config 已載入：{config}")
    
    # 初始化 Prompt Builder
    builder = MedUbiPromptBuilder(workspace_path)
    
    # 測試用戶消息
    user_message = "掛號處在哪？"
    conversation_history = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "<neutral><tw>你好！有什麼我可以幫你的嗎？<sbr>"}
    ]
    
    # 載入 PromptLoader
    try:
        from prompt.prompt_loader import PromptLoader
        prompt_loader = PromptLoader(workspace_path)
        
        print(f"\n📝 構建 Prompt...")
        prompt, emotion_enabled = await builder._build_prompt(
            config=config,
            user_message=user_message,
            conversation_history=conversation_history,
            prompt_loader_obj=prompt_loader,
            knowledge_content="醫療展場地資訊：掛號處在展場 A 區，藥局在展場 B 區",
            knowledge_meta="場地：A 區 - 掛號處，B 區 - 藥局",
            intent_result={"intent": "info_location", "target_location": "registration"},
            is_llm1=False,
            persona_config_path=config_path  # 新增：指定 config.yaml 路徑
        )
        print(f"✅ Prompt 構建成功")
        print(f"   長度：{len(prompt)} 字元")
        print(f"   情緒標籤啟用：{emotion_enabled}")
        print(f"\n📋 Prompt 預覽（前 500 字元）：\n{prompt[:500]}...")
        return prompt
    except ModuleNotFoundError:
        print(f"⚠️  PromptLoader 無法載入，跳過 Prompt Builder 測試")
        return None
    except Exception as e:
        print(f"❌ Prompt 構建失敗：{e}")
        import traceback
        traceback.print_exc()
        return None


def test_output_parser():
    """測試 Output Parser"""
    print("\n" + "=" * 60)
    print("測試 Output Parser")
    print("=" * 60)
    
    parser = MedUbiOutputParser()
    
    # 測試用例 1: 正確的 JSON 格式
    print("\n📋 測試用例 1: 正確的 JSON 格式")
    llm_response_1 = """{
    "ToUbiChan": "<neutral><tw>掛號處在展場 A 區<sbr>我請小護士帶你過去<sbr>請跟著它走<sbr>",
    "ToBaxiaomi": {
        "Steps": [
            {
                "action": "navigate",
                "params": {
                    "target": "counter"
                }
            },
            {
                "action": "speak",
                "params": {
                    "speech": "你好，請跟我來掛號處"
                }
            },
            {
                "action": "navigate",
                "params": {
                    "target": "registration"
                }
            },
            {
                "action": "speak",
                "params": {
                    "speech": "掛號處到了，請先抽號碼牌"
                }
            }
        ],
        "Steps_Descripts": "第一步，讓小護士移動到櫃台前方。第二步，讓小護士對 user 說「你好，請跟我來掛號處」。第三步，讓小護士導航到掛號處。第四步，讓小護士對 user 說「掛號處到了，請先抽號碼牌」"
    }
}"""
    
    result_1 = parser.parse_llm_response(llm_response_1)
    print(f"✅ 解析成功：{result_1['success']}")
    if result_1['success']:
        print(f"   ToUbiChan: {result_1['ToUbiChan'][:50]}...")
        print(f"   Steps 數量：{len(result_1['ToBaxiaomi']['Steps'])}")
        print(f"   Steps_Descripts: {result_1['ToBaxiaomi']['Steps_Descripts'][:50]}...")
        
        # 驗證 UbiChan 格式
        is_valid, error_msg = parser.validate_ubichan_format(result_1['ToUbiChan'])
        print(f"✅ UbiChan 格式驗證：{'通過' if is_valid else f'失敗 - {error_msg}'}")
        
        # 驗證 Steps 格式
        is_valid, error_msg = parser.validate_steps(result_1['ToBaxiaomi']['Steps'])
        print(f"✅ Steps 格式驗證：{'通過' if is_valid else f'失敗 - {error_msg}'}")
        
        # 測試提取函數
        ubichan = parser.extract_ubichan_content(result_1)
        steps_desc = parser.extract_steps_descripts(result_1)
        steps = parser.extract_steps(result_1)
        print(f"\n✅ extract_ubichan_content: {ubichan[:50]}...")
        print(f"✅ extract_steps_descripts: {steps_desc[:50]}...")
        print(f"✅ extract_steps: {len(steps)} 個步驟")
    else:
        print(f"   錯誤：{result_1['error']}")
        print(f"   result_1: {result_1}")
        return None, None, None
    
    # 測試用例 2: 包含 Markdown 代碼塊的 JSON
    print("\n📋 測試用例 2: 包含 Markdown 代碼塊")
    llm_response_2 = """好的，這是我的回應：

```json
{
    "ToUbiChan": "<happy><tw>藥局在展場 B 區<sbr>我請小護士帶你過去<sbr>",
    "ToBaxiaomi": {
        "Steps": [
            {
                "action": "navigate",
                "params": {
                    "target": "pharmacy"
                }
            }
        ],
        "Steps_Descripts": "第一步，讓小護士導航到藥局。"
    }
}
```

希望這對你有幫助！"""
    
    result_2 = parser.parse_llm_response(llm_response_2)
    print(f"✅ 解析成功：{result_2['success']}")
    if result_2['success']:
        print(f"   ToUbiChan: {result_2['ToUbiChan']}")
    else:
        print(f"   錯誤：{result_2['error']}")
    
    # 測試用例 3: 錯誤格式（缺少欄位）
    print("\n📋 測試用例 3: 錯誤格式（缺少 ToBaxiaomi）")
    llm_response_3 = """{
    "ToUbiChan": "<neutral><tw>測試<sbr>"
}"""
    
    result_3 = parser.parse_llm_response(llm_response_3)
    print(f"✅ 解析結果：{result_3['success']}")
    print(f"   錯誤訊息：{result_3['error']}")
    
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
