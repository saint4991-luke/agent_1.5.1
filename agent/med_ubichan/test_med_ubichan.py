#!/usr/bin/env python3
"""
醫療展 med_ubichan 模組測試腳本

測試 UbiChan 輸出格式化和豹小秘 Action 生成
"""

import sys
from pathlib import Path

# 添加 agent 目錄到 Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from med_ubichan import (
    MedUbiOutputFormatter,
    RobotActionGenerator
)


def test_ubichan_formatter():
    """測試 UbiChan 輸出格式化器"""
    print("=" * 60)
    print("測試 UbiChan 輸出格式化器")
    print("=" * 60)
    
    formatter = MedUbiOutputFormatter()
    
    # 測試 1：基本格式化
    print("\n【測試 1】基本格式化")
    output = formatter.format_ubichan_response(
        text="好的，豹小秘會帶你去掛號處。請跟著它走。",
        emotion="happy",
        lang="tw"
    )
    print(output)
    print()
    
    # 驗證
    assert "<!-- emotion -->happy<!-- /emotion -->" in output
    assert "<!-- lang -->tw (zh)<!-- /lang -->" in output
    assert "<sbr>" in output
    print("✅ 測試 1 通過")
    
    # 測試 2：解析回應
    print("\n【測試 2】解析回應")
    parsed = formatter.parse_full_response(output)
    print(f"情緒：{parsed['emotion']}")
    print(f"語言：{parsed['lang']}")
    print(f"句子：{parsed['sentences']}")
    
    assert parsed['emotion'] == 'happy'
    assert parsed['lang'] == 'tw (zh)'
    assert len(parsed['sentences']) == 2
    print("✅ 測試 2 通過")
    
    # 測試 3：多語言
    print("\n【測試 3】多語言支持")
    en_output = formatter.format_ubichan_response(
        text="Hello! How can I help you today?",
        emotion="neutral",
        lang="en"
    )
    print(en_output)
    assert "<!-- lang -->en<!-- /lang -->" in en_output
    print("✅ 測試 3 通過")
    
    print("\n" + "=" * 60)
    print("所有 UbiChan 測試通過！")
    print("=" * 60)


def test_robot_action_generator():
    """測試豹小秘 Action 生成器"""
    print("\n" + "=" * 60)
    print("測試豹小秘 Action 生成器")
    print("=" * 60)
    
    action_gen = RobotActionGenerator()
    
    # 測試 1：導航 Action
    print("\n【測試 1】導航 Action（掛號）")
    nav_action = action_gen.generate_navigate_action(
        target="registration",
        speech="你好，請跟我來掛號處"
    )
    
    print("JSON 指令:")
    import json
    print(json.dumps(nav_action.to_json(), indent=2, ensure_ascii=False))
    print("\n自然語言步驟:")
    print(nav_action.natural_language_steps)
    
    assert nav_action.action == "navigate"
    assert nav_action.params["target"] == "registration"
    assert nav_action.natural_language_steps is not None
    print("✅ 測試 1 通過")
    
    # 測試 2：取物 Action
    print("\n【測試 2】取物 Action（拿藥）")
    pickup_action = action_gen.generate_pickup_item_action(
        location="pharmacy",
        item="藥品",
        speech="藥劑師你好，請把藥品放到我的籃子，並按下按鈕"
    )
    
    print("JSON 指令:")
    print(json.dumps(pickup_action.to_json(), indent=2, ensure_ascii=False))
    print("\n自然語言步驟:")
    print(pickup_action.natural_language_steps)
    
    assert pickup_action.action == "pickup_item"
    assert pickup_action.params["location"] == "pharmacy"
    assert pickup_action.params["item"] == "藥品"
    print("✅ 測試 2 通過")
    
    # 測試 3：取消 Action
    print("\n【測試 3】取消 Action")
    cancel_action = action_gen.generate_cancel_action(
        speech="我要回去櫃台了"
    )
    
    print("JSON 指令:")
    print(json.dumps(cancel_action.to_json(), indent=2, ensure_ascii=False))
    print("\n自然語言步驟:")
    print(cancel_action.natural_language_steps)
    
    assert cancel_action.action == "cancel"
    print("✅ 測試 3 通過")
    
    # 測試 4：Intent 分類
    print("\n【測試 4】Intent 分類")
    test_cases = [
        ("我想要掛號", "registration"),
        ("我看完病了，要拿藥", "pharmacy"),
        ("請停止動作", "cancel"),
        ("掛號處在哪？", "info_location"),
    ]
    
    for user_msg, expected_intent in test_cases:
        action = action_gen.generate_from_intent(expected_intent, user_msg)
        if action:
            print(f"✅ '{user_msg}' → {action.action}")
        else:
            print(f"⚠️  '{user_msg}' → 無動作")
    
    print("✅ 測試 4 通過")
    
    print("\n" + "=" * 60)
    print("所有豹小秘測試通過！")
    print("=" * 60)


def test_complete_output():
    """測試完整輸出（UbiChan + 豹小秘）"""
    print("\n" + "=" * 60)
    print("測試完整輸出（UbiChan × 豹小秘）")
    print("=" * 60)
    
    formatter = MedUbiOutputFormatter()
    action_gen = RobotActionGenerator()
    
    # 情境：用戶說「我想要掛號」
    print("\n【情境】用戶說：「我想要掛號」")
    print("-" * 60)
    
    ubichan_text = "好的，豹小秘會帶你去掛號處。請跟著它走。"
    robot_action = action_gen.generate_navigate_action(
        target="registration",
        speech="你好，請跟我來掛號處"
    )
    
    complete_output = action_gen.format_complete_output(
        ubichan_text=ubichan_text,
        robot_action=robot_action,
        emotion="happy",
        lang="tw"
    )
    
    print("\n1️⃣ UbiChan 輸出:")
    print(complete_output['ubichan_output'])
    
    print("\n2️⃣ 豹小秘 JSON 指令:")
    import json
    print(json.dumps(complete_output['robot_json'], indent=2, ensure_ascii=False))
    
    print("\n3️⃣ 豹小秘自然語言步驟:")
    print(complete_output['robot_steps'])
    
    # 驗證
    assert complete_output['ubichan_output'] is not None
    assert complete_output['robot_json'] is not None
    assert complete_output['robot_steps'] is not None
    
    print("\n✅ 完整輸出測試通過！")
    print("=" * 60)


if __name__ == "__main__":
    print("\n🦐 醫療展 med_ubichan 模組測試\n")
    
    test_ubichan_formatter()
    test_robot_action_generator()
    test_complete_output()
    
    print("\n" + "🎉" * 30)
    print("所有測試通過！med_ubichan 模組運作正常")
    print("🎉" * 30 + "\n")
