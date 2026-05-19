# `read_csv` Tool

讀取 CSV 文件內容。

## ⚙️ 配置方式

- **Persona Config:** ❌ 不可配置
- **啟用方式:** 需由開發者在 Agent 實作中決定

## 📍 路徑

`tools/internal/file_system/read_csv.py`

## 🎯 設計目的

Internal Tools 不開放給平台用戶通過配置文件使用，
需要修改程式碼才能啟用，確保高權限操作的安全性。

## 📝 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `path` | string | ✅ | CSV 文件路徑（相對於 `/workspace`） |
| `delimiter` | string | ❌ | 分隔符號（預設：`,`） |
| `encoding` | string | ❌ | 文件編碼（預設：utf-8） |
| `header` | boolean | ❌ | 是否將第一列作為欄位名（預設：true） |
| `limit` | integer | ❌ | 最大讀取列數（預設：無限制） |

## 📤 返回結果

```json
{
  "success": true,
  "data": {
    "path": "/workspace/data/users.csv",
    "rows": 100,
    "columns": 4,
    "data": [
      {"id": 1, "name": "王小明", "email": "wang@example.com", "dept": "工程部"},
      {"id": 2, "name": "李小華", "email": "li@example.com", "dept": "產品部"}
    ]
  }
}
```

## ⚠️ 安全限制

- 只能讀取 `/workspace` 下的文件
- 防止路徑遍歷攻擊
- 文件大小限制：最大 10MB

## 💡 使用範例

**用戶輸入：**
```
讀取 users.csv 的內容
```

**Tool 調用：**
```json
{
  "tool": "read_csv",
  "params": {
    "path": "data/users.csv"
  }
}
```

**使用分號分隔：**
```json
{
  "tool": "read_csv",
  "params": {
    "path": "data/eu_data.csv",
    "delimiter": ";"
  }
}
```

**限制讀取列數：**
```json
{
  "tool": "read_csv",
  "params": {
    "path": "data/large_file.csv",
    "limit": 50
  }
}
```

---

**相關文件：**
- [read_excel.md](read_excel.md) - 讀取 Excel 文件
- [read_file.md](read_file.md) - 讀取文字文件
- [list_dir.md](list_dir.md) - 列出目錄
