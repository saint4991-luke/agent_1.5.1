# `read_excel` Tool

讀取 Excel 文件內容（.xlsx, .xls）。

## ⚙️ 配置方式

- **Persona Config:** ❌ 不可配置
- **啟用方式:** 需由開發者在 Agent 實作中決定

## 📍 路徑

`tools/internal/file_system/read_excel.py`

## 🎯 設計目的

Internal Tools 不開放給平台用戶通過配置文件使用，
需要修改程式碼才能啟用，確保高權限操作的安全性。

## 📝 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `path` | string | ✅ | Excel 文件路徑（相對於 `/workspace`） |
| `sheet` | string/integer | ❌ | 工作表名稱或索引（預設：0，第一個工作表） |
| `range` | string | ❌ | 儲存格範圍（例如：`A1:C10`，預設：全部） |
| `header` | boolean | ❌ | 是否將第一列作為欄位名（預設：true） |

## 📤 返回結果

```json
{
  "success": true,
  "data": {
    "path": "/workspace/data/report.xlsx",
    "sheet": "Sheet1",
    "rows": 50,
    "columns": 5,
    "data": [
      {"姓名": "王小明", "部門": "工程部", "職級": "P5"},
      {"姓名": "李小華", "部門": "產品部", "職級": "P4"}
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
幫我讀取 sales_report.xlsx 的第一個工作表
```

**Tool 調用：**
```json
{
  "tool": "read_excel",
  "params": {
    "path": "data/sales_report.xlsx"
  }
}
```

**讀取特定工作表：**
```json
{
  "tool": "read_excel",
  "params": {
    "path": "data/report.xlsx",
    "sheet": "Q1 Summary"
  }
}
```

---

**相關文件：**
- [read_csv.md](read_csv.md) - 讀取 CSV 文件
- [read_file.md](read_file.md) - 讀取文字文件
- [list_dir.md](list_dir.md) - 列出目錄
