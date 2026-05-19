# `knowledge_meta` Tool

查詢知識庫的 meta 資訊。

## ⚙️ 配置方式

- **Persona Config:** ✅ 可配置
- **啟用方式:** 在 `config.yaml` 的 `tools.available` 中聲明

## 📍 路徑

`tools/public/knowledge/knowledge_meta.py`

## 📝 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `knowledge_id` | string | ✅ | 知識庫 ID |

## 📤 返回結果

```json
{
  "success": true,
  "data": {
    "knowledge_id": "ubichan",
    "metadata": {
      "category": "customer_service",
      "tags": ["產品", "客服", "常見問題"],
      "language": "zh-TW",
      "version": "1.0"
    },
    "document_count": 15
  }
}
```

## 💡 使用場景

- 查看知識庫的基本資訊
- 確認知識庫是否存在
- 獲取知識庫的標籤和分類

---

**相關文件：**
- [knowledge_query.md](knowledge_query.md) - 查詢知識庫內容
- [rebuild_knowledge_meta.md](rebuild_knowledge_meta.md) - 重建 meta
