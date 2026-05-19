# `web_search` Tool

搜尋網路資訊。

## ⚙️ 配置方式

- **Persona Config:** ✅ 可配置
- **啟用方式:** 在 `config.yaml` 的 `tools.available` 中聲明

## 📍 路徑

`tools/public/web_search.py`

## 📝 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `query` | string | ✅ | 搜尋關鍵字 |
| `max_results` | integer | ❌ | 最大結果數（預設：5） |

## 📤 返回結果

```json
{
  "success": true,
  "data": {
    "query": "最新 AI 新聞",
    "results": [
      {
        "title": "AI 技術新突破",
        "url": "https://example.com/news/123",
        "snippet": "..."
      }
    ]
  }
}
```

## 💡 使用場景

- 查詢最新新聞
- 查詢天氣、股價等即時資訊
- 查詢技術文件

---

**相關文件：**
- [knowledge_meta.md](knowledge_meta.md) - 查詢知識庫 meta
- [knowledge_query.md](knowledge_query.md) - 查詢知識庫內容
