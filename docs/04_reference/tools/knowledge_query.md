# `knowledge_query` Tool

查詢知識庫的內容。

## ⚙️ 配置方式

- **Persona Config:** ✅ 可配置
- **啟用方式:** 在 `config.yaml` 的 `tools.available` 中聲明

## 📍 路徑

`tools/public/knowledge/knowledge_query.py`

## 📝 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `knowledge_id` | string | ✅ | 知識庫 ID |
| `query` | string | ✅ | 查詢關鍵字 |

## 📤 返回結果

```json
{
  "success": true,
  "data": {
    "knowledge_id": "ubichan",
    "query": "退貨政策",
    "results": [
      {
        "document": "faq.md",
        "content": "退貨政策：購買後 7 天內...",
        "relevance_score": 0.95
      }
    ]
  }
}
```

## 💡 使用場景

- 查詢產品資訊
- 查詢常見問題
- 查詢公司政策

---

**相關文件：**
- [knowledge_meta.md](knowledge_meta.md) - 查詢知識庫 meta
- [rebuild_knowledge_meta.md](rebuild_knowledge_meta.md) - 重建 meta
