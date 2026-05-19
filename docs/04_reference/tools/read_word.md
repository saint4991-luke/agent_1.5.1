# `read_word` Tool

讀取 Word 文件內容（.docx, .doc）。

## ⚙️ 配置方式

- **Persona Config:** ❌ 不可配置
- **啟用方式:** 需由開發者在 Agent 實作中決定

## 📍 路徑

`tools/internal/file_system/read_word.py`

## 🎯 設計目的

Internal Tools 不開放給平台用戶通過配置文件使用，
需要修改程式碼才能啟用，確保高權限操作的安全性。

## 📝 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `path` | string | ✅ | Word 文件路徑（相對於 `/workspace`） |
| `extract_images` | boolean | ❌ | 是否提取圖片（預設：false） |
| `include_metadata` | boolean | ❌ | 是否包含文件元數據（預設：false） |

## 📤 返回結果

```json
{
  "success": true,
  "data": {
    "path": "/workspace/docs/report.docx",
    "title": "季度報告",
    "author": "王小明",
    "pages": 5,
    "word_count": 2500,
    "content": "# 季度報告\n\n## 摘要\n\n本季度業績成長...",
    "images": []  // 當 extract_images=true 時
  }
}
```

## ⚠️ 安全限制

- 只能讀取 `/workspace` 下的文件
- 防止路徑遍歷攻擊
- 文件大小限制：最大 10MB
- 僅支援 .docx 格式（.doc 需轉換）

## 💡 使用範例

**用戶輸入：**
```
讀取季度報告的 Word 文件
```

**Tool 調用：**
```json
{
  "tool": "read_word",
  "params": {
    "path": "docs/quarterly_report.docx"
  }
}
```

**提取圖片：**
```json
{
  "tool": "read_word",
  "params": {
    "path": "docs/manual.docx",
    "extract_images": true
  }
}
```

---

**相關文件：**
- [read_pdf.md](read_pdf.md) - 讀取 PDF 文件
- [read_file.md](read_file.md) - 讀取文字文件
- [read_excel.md](read_excel.md) - 讀取 Excel 文件
