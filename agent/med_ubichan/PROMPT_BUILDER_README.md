# Prompt Builder & Output Parser - 醫療展 Virtual Human

## 概述

本模組提供醫療展 Virtual Human (UbiChan × 小護士) 的 Prompt 構建和輸出解析功能。

根據 MED_UBIAGENT 規格文檔 v1.0，LLM 必須生成以下 JSON 格式：

```json
{
    "ToUbiChan": "<情緒><語言>內容<sbr>...",
    "ToBaxiaomi": {
        "Steps": [...],
        "Steps_Descripts": "..."
    }
}
```

## 組件

### 1. MedUbiPromptBuilder

Prompt 構建器，負責組合完整的 6 部分 Prompt：

1. **角色風格** - UbiChan 的角色定義
2. **輸出規格** - JSON 格式範例和說明
3. **知識庫內容** - 醫療展場地資訊
4. **小護士 Action 說明** - 支持的 Action 清單
5. **對話歷史** - 最近 10 輪對話
6. **用戶問題** - 當前用戶輸入

#### 使用方式

```python
from pathlib import Path
from med_ubichan.prompt_builder import MedUbiPromptBuilder

# 初始化
workspace_path = Path("/path/to/workspace")
builder = MedUbiPromptBuilder(workspace_path)

# 構建 Prompt
prompt, emotion_enabled = await builder._build_prompt(
    config={
        "persona_id": "med_ubichan_v1",
        "style": {"file": "style.md"},
        "output_format": "med_ubichan"
    },
    user_message="掛號處在哪？",
    conversation_history=[...],
    prompt_loader_obj=prompt_loader,
    knowledge_content="...",
    intent_result={
        "intent": "info_location",
        "target_location": "registration",
        "requires_robot": True
    },
    is_llm1=False
)
```

### 2. MedUbiOutputParser

輸出解析器，負責解析和驗證 LLM 輸出的 JSON。

#### 使用方式

```python
from med_ubichan.prompt_builder import MedUbiOutputParser

parser = MedUbiOutputParser()

# 解析 LLM 輸出
result = parser.parse_llm_response(llm_response)

if result["success"]:
    # 提取內容
    ubichan = parser.extract_ubichan_content(result)
    steps = parser.extract_steps(result)
    steps_desc = parser.extract_steps_descripts(result)
    
    # 驗證格式
    is_valid, error = parser.validate_ubichan_format(ubichan)
    is_valid, error = parser.validate_steps(steps)
else:
    print(f"解析失敗：{result['error']}")
```

## API 整合

### 在 api.py 中使用

```python
from med_ubichan.prompt_builder import MedUbiPromptBuilder, MedUbiOutputParser

# 初始化
prompt_builder = MedUbiPromptBuilder(workspace_path)
output_parser = MedUbiOutputParser()

# 在 chat 端點中
async def chat_endpoint(request):
    # 1. 意圖分類
    intent_result = await classify_intent(user_message)
    
    # 2. 使用 LLM 生成完整回應
    result = await generate_response_with_llm(
        user_message=user_message,
        conversation_history=history,
        persona_config=config,
        intent_result=intent_result,
        workspace_path=workspace_path,
        prompt_loader_obj=prompt_loader,
        knowledge_content=knowledge
    )
    
    # 3. 處理結果
    if result["success"]:
        ubichan_output = result["ubichan_output"]
        robot_steps = result["robot_steps"]
        robot_steps_desc = result["robot_steps_descripts"]
        
        # 4. STREAM 發送
        return StreamingResponse(
            send_stream(ubichan_output, robot_steps),
            media_type="text/event-stream"
        )
    else:
        # 降級處理
        return fallback_response()
```

## 輸出格式規格

### ToUbiChan 格式

```
<情緒標籤><語言標籤>內容<sbr>內容<sbr>...
```

**情緒標籤：**
- `<neutral>` - 中性
- `<happy>` - 開心
- `<concerned>` - 關心
- `<thinking>` - 思考
- `<embarrassed>` - 尷尬
- `<excited>` - 興奮
- `<sad>` - 悲傷
- `<surprised>` - 驚訝

**語言標籤：**
- `<tw>` - 繁體中文（台灣）
- `<cn>` - 簡體中文
- `<en>` - 英文

**斷句：**
- 使用 `<sbr>` 進行斷句

**範例：**
```
<neutral><tw>掛號處在展場 A 區<sbr>我請小護士帶你過去<sbr>請跟著它走<sbr>
```

### ToBaxiaomi 格式

```json
{
    "Steps": [
        {
            "action": "action_name",
            "params": {
                "key": "value"
            },
            "speech": "語音內容"
        }
    ],
    "Steps_Descripts": "自然語言步驟描述"
}
```

**支持的 Action：**

1. **navigate** - 導航
   ```json
   {
       "action": "navigate",
       "params": {"target": "registration"},
       "speech": ""
   }
   ```

2. **speak** - 播放語音
   ```json
   {
       "action": "speak",
       "params": {"speech": "你好，請跟我來"},
       "speech": ""
   }
   ```

3. **pickup_item** - 拾取物品
   ```json
   {
       "action": "pickup_item",
       "params": {"location": "pharmacy", "item": "藥品"},
       "speech": "藥劑師你好，請把藥品放到我的籃子"
   }
   ```

4. **cancel** - 停止
   ```json
   {
       "action": "cancel",
       "params": {},
       "speech": ""
   }
   ```

**Steps_Descripts 範例：**
```
第一步，讓小護士移動到櫃台前方。
第二步，讓小護士對 user 說「你好，請跟我來掛號處」。
第三步，讓小護士導航到掛號處。
第四步，讓小護士對 user 說「掛號處到了，請先抽號碼牌」。
```

## 測試

運行測試：

```bash
cd /path/to/agent_1.5.1
python -m agent.med_ubichan.test_prompt_builder
```

## 錯誤處理

### 解析錯誤

如果 LLM 輸出的 JSON 格式不正確，parser 會嘗試以下方法：

1. 直接解析 JSON
2. 提取 Markdown 代碼塊中的 JSON
3. 提取大括號內容並解析

如果都失敗，返回：
```python
{
    "success": False,
    "ToUbiChan": None,
    "ToBaxiaomi": None,
    "error": "錯誤訊息"
}
```

### 驗證錯誤

如果格式驗證失敗，返回：
```python
{
    "success": False,
    "ubichan_output": "...",
    "robot_steps": [...],
    "robot_steps_descripts": "...",
    "error": "驗證錯誤訊息"
}
```

### 降級處理

如果 LLM 生成失敗，api.py 應該降級使用舊的模板生成方式：

```python
if not llm_result["success"]:
    # 使用舊的模板生成方式
    ubichan_text, emotion = await _generate_ubichan_response(...)
    ubichan_output = formatter.format_ubichan_response(...)
    robot_steps = None
```

## 注意事項

1. **LLM 生成 Steps**：Steps 必須由 LLM 生成，不是程式碼組裝
2. **格式驗證**：必須驗證 UbiChan 和 Steps 的格式
3. **降級處理**：LLM 失敗時要能降級到模板生成
4. **錯誤日誌**：記錄所有錯誤以便除錯

## 參考文件

- MED_UBIAGENT.md - 醫療展 Virtual Human 規格文檔
- agent/virtual_human/api.py - Virtual Human API 參考實作
- specs/prompt-generation-spec.md - Prompt 生成規格
