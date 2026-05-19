# `read_pdf` Tool

讀取 PDF 文件內容。

## ⚙️ 配置方式

- **Persona Config:** ❌ 不可配置
- **啟用方式:** 需由開發者在 Agent 實作中決定

## 📍 路徑

`tools/internal/file_system/read_pdf.py`

## 🎯 設計目的

Internal Tools 不開放給平台用戶通過配置文件使用，
需要修改程式碼才能啟用，確保高權限操作的安全性。

## 📝 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `path` | string | ✅ | PDF 文件路徑（相對於 `/workspace`） |
| `pages` | string/array | ❌ | 指定頁碼（例如：`"1-5"` 或 `[1,2,3]`，預設：全部） |
| `extract_images` | boolean | ❌ | 是否提取圖片（預設：false） |
| `extract_tables` | boolean | ❌ | 是否提取表格（預設：false） |

## 📤 返回結果

```json
{
  "success": true,
  "data": {
    "path": "/workspace/docs/manual.pdf",
    "pages": 10,
    "content": "第 1 頁\n\n產品使用手冊\n\n第 1 章：簡介\n\n...",
    "tables": [  // 當 extract_tables=true 時
      {"page": 3, "data": [["產品", "價格"], ["A", "$100"]]}
    ],
    "images": []  // 當 extract_images=true 時
  }
}
```

## ⚠️ 安全限制

- 只能讀取 `/workspace` 下的文件
- 防止路徑遍歷攻擊
- 文件大小限制：最大 20MB
- 不支援加密的 PDF 文件

## 💡 使用範例

**用戶輸入：**
```
讀取產品手冊 PDF
```

**Tool 調用：**
```json
{
  "tool": "read_pdf",
  "params": {
    "path": "docs/product_manual.pdf"
  }
}
```

**讀取特定頁面：**
```json
{
  "tool": "read_pdf",
  "params": {
    "path": "docs/report.pdf",
    "pages": "1-3"
  }
}
```

**提取表格：**
```json
{
  "tool": "read_pdf",
  "params": {
    "path": "docs/data_sheet.pdf",
    "extract_tables": true
  }
}
```

---

**相關文件：**
- [read_word.md](read_word.md) - 讀取 Word 文件
- [read_file.md](read_file.md) - 讀取文字文件
- [read_excel.md](read_excel.md) - 讀取 Excel 文件
