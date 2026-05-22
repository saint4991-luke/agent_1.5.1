# LLM Service - 醫療展 Virtual Human

## 概述

本模組整合 UbiLM Grant API 和 Chat Completions API，提供統一的 LLM 呼叫介面。

## API 流程

```
1. 呼叫 Grant API
   POST https://sage.ubitus.ai/ubillm/api/v1/resource/grant
   Body: {"api_key": "...", "model": "qwen3-8b-fp8"}
   Response: {"api_token": "...", "api_endpoint": "..."}

2. 呼叫 Chat Completions API
   POST {api_endpoint}/v1/chat/completions
   Headers: {"Authorization": "Bearer {api_token}"}
   Body: {"messages": [...], "temperature": 0.7, ...}
   Response: {"choices": [{"message": {"content": "..."}}]}
```

## 組件

### 1. UbiLLMService

基礎 LLM 服務類，提供：

- `_grant_token()` - 獲取 API Token
- `_chat_completions()` - 呼叫 Chat API
- `chat_async()` - 非同步對話介面
- `chat_with_retry()` - 帶重試機制的對話

#### 使用方式

```python
from med_ubichan.llm_service import UbiLLMService

# 初始化
service = UbiLLMService(
    api_key="your_api_key",
    model="qwen3-8b-fp8"
)

# 對話
response = await service.chat_async(
    messages=[
        {"role": "system", "content": "你是一個助手。"},
        {"role": "user", "content": "你好"}
    ],
    temperature=0.7
)
print(response)
```

### 2. MedUbiLLMService

醫療展專用 LLM 服務（擴展自 UbiLLMService），提供：

- `generate_med_ubichan_response()` - 生成醫療展 Virtual Human 回應

#### 使用方式

```python
from med_ubichan.llm_service import MedUbiLLMService

# 初始化
service = MedUbiLLMService(
    api_key="your_api_key",
    model="qwen3-8b-fp8",
    workspace_path=Path("/path/to/workspace")
)

# 生成醫療展回應
prompt = """# 角色風格
...

# 用戶問題
掛號處在哪？
"""

result = await service.generate_med_ubichan_response(
    prompt=prompt,
    temperature=0.7,
    max_tokens=2048
)

if result['success']:
    ubichan = result['parsed']['ToUbiChan']
    steps = result['parsed']['ToBaxiaomi']['Steps']
    steps_desc = result['parsed']['ToBaxiaomi']['Steps_Descripts']
else:
    print(f"失敗：{result['error']}")
```

### 3. 工廠函數

```python
from med_ubichan.llm_service import create_llm_service

# 創建服務實例
llm_service = create_llm_service(
    api_key="your_api_key",
    model="qwen3-8b-fp8",
    workspace_path=Path("/path/to/workspace")
)
```

## 環境變數

建議使用環境變數管理敏感資訊：

```bash
export UBILM_API_KEY="your_api_key_here"
export UBILM_GRANT_URL="https://sage.ubitus.ai/ubillm/api/v1/resource/grant"
export UBILM_LLM_MODEL="qwen3-8b-fp8"
```

在程式碼中讀取：

```python
import os
api_key = os.getenv("UBILM_API_KEY")
```

## 錯誤處理

### Grant API 錯誤

```python
try:
    api_token, api_endpoint = await service._grant_token()
except Exception as e:
    print(f"Grant API 失敗：{e}")
    # 處理錯誤（重試、降級等）
```

### Chat API 錯誤

```python
try:
    response = await service.chat_async(messages=messages)
except Exception as e:
    print(f"Chat API 失敗：{e}")
    # 處理錯誤（重試、降級等）
```

### 重試機制

```python
# 自動重試 2 次
response = await service.chat_with_retry(
    messages=messages,
    retry_count=2
)
```

## Token 管理

服務會自動快取 api_token 和 api_endpoint：

```python
# 第一次呼叫會獲取 token
await service.chat_async(messages=messages)

# 後續呼叫會使用快取的 token
await service.chat_async(messages=messages)

# 如果 token 失效（401），會自動重新獲取
```

## 在 api.py 中整合

```python
from fastapi import FastAPI
from med_ubichan import init_med_ubichan_api, router
from med_ubichan.llm_service import create_llm_service

app = FastAPI()

# 初始化 LLM 服務
llm_service = create_llm_service(
    api_key=os.getenv("UBILM_API_KEY"),
    model="qwen3-8b-fp8",
    workspace_path=Path("/path/to/workspace")
)

# 初始化醫療展 API
init_med_ubichan_api(
    config_loader_obj=MedUbiConfigLoader(),
    llm_service_obj=llm_service,
    workspace_path=Path("/path/to/workspace")
)

# 添加路由
app.include_router(router, prefix='/med_ubichan')
```

## 測試

運行測試：

```bash
cd /path/to/agent_1.5.1
export UBILM_API_KEY="your_api_key_here"
python -m agent.med_ubichan.test_llm_service
```

## 配置選項

### UbiLLMService 參數

| 參數 | 類型 | 預設值 | 說明 |
|------|------|--------|------|
| grant_url | str | `https://sage.ubitus.ai/ubillm/api/v1/resource/grant` | Grant API URL |
| api_key | str | 從環境變數讀取 | UbiLM API Key |
| model | str | `qwen3-8b-fp8` | LLM 模型名稱 |

### chat_async 參數

| 參數 | 類型 | 預設值 | 說明 |
|------|------|--------|------|
| messages | List[Dict] | 必填 | 對話消息列表 |
| temperature | float | 0.7 | 溫度參數 |
| max_tokens | int | 2048 | 最大 token 數 |
| enable_thinking | bool | False | 是否啟用 thinking 模式 |
| **kwargs | Any | - | 其他參數 |

### generate_med_ubichan_response 參數

| 參數 | 類型 | 預設值 | 說明 |
|------|------|--------|------|
| prompt | str | 必填 | 完整的 Prompt |
| conversation_history | List[Dict] | None | 對話歷史 |
| temperature | float | 0.7 | 溫度參數 |
| max_tokens | int | 2048 | 最大 token 數 |

## 回應格式

### chat_async 回應

```python
# 返回字串（LLM 回應內容）
response = await service.chat_async(...)
# "<neutral><tw>掛號處在展場 A 區<sbr>..."
```

### generate_med_ubichan_response 回應

```python
{
    "success": True,
    "content": "LLM 原始回應（JSON 字串）",
    "parsed": {
        "success": True,
        "ToUbiChan": "<neutral><tw>...",
        "ToBaxiaomi": {
            "Steps": [...],
            "Steps_Descripts": "..."
        },
        "error": None
    },
    "error": None
}
```

## 注意事項

1. **API Key 安全**：不要將 API Key 硬編碼在程式碼中，使用環境變數
2. **Token 快取**：服務會自動快取 token，避免頻繁呼叫 Grant API
3. **錯誤重試**：使用 `chat_with_retry` 處理暫時性錯誤
4. **Timeout 設置**：預設 connect=5s, read=30s, write=30s
5. **醫療展專用**：`MedUbiLLMService` 自動整合 Prompt Builder 和 Output Parser

## 參考文件

- prompt_builder.md - Prompt 構建和解析器文檔
- MED_UBIAGENT.md - 醫療展 Virtual Human 規格文檔
- https://sage.ubitus.ai - UbiLM API 文檔
