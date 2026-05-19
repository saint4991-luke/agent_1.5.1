# `rebuild_knowledge_meta` Tool

重建知識庫的 meta 索引。

## ⚙️ 配置方式

- **Persona Config:** ✅ 可配置
- **啟用方式:** 在 `config.yaml` 的 `tools.available` 中聲明

## 📍 路徑

`tools/public/knowledge/rebuild_knowledge_meta.py`

## 📝 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `knowledge_base` | string | ❌ | 知識庫名稱（預設：default） |
| `force` | boolean | ❌ | 強制重建，忽略現有緩存（預設：false） |
| `include_subdirs` | boolean | ❌ | 是否包含子目錄（預設：true） |

## 📤 返回結果

```json
{
  "success": true,
  "data": {
    "knowledge_base": "default",
    "files_indexed": 25,
    "total_chunks": 150,
    "duration_ms": 3500,
    "meta": {
      "last_updated": "2026-05-01T03:00:00Z",
      "version": "1.0"
    }
  }
}
```

## ⚠️ 注意事項

- 重建過程可能需要數秒至數分鐘（取決於知識庫大小）
- 重建期間不影響查詢操作
- 建議在離峰時段執行大規模重建

## 💡 使用場景

- 知識庫文件更新後
- 發現查詢結果不完整時
- 定期維護（建議每週一次）

## 💡 使用範例

**用戶輸入：**
```
重建知識庫索引
```

**Tool 調用：**
```json
{
  "tool": "rebuild_knowledge_meta",
  "params": {}
}
```

**強制重建特定知識庫：**
```json
{
  "tool": "rebuild_knowledge_meta",
  "params": {
    "knowledge_base": "product_docs",
    "force": true
  }
}
```

---

**相關文件：**
- [knowledge_meta.md](knowledge_meta.md) - 查詢知識庫 meta
- [knowledge_query.md](knowledge_query.md) - 查詢知識庫內容
- [web_search.md](web_search.md) - 網路搜尋
