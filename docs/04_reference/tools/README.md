# 🔧 Tool 參考手冊

本文檔提供所有可用 Tools 的詳細說明。

## 📋 目錄

### Internal Tools（需改 code 啟用）

| Tool | 說明 | 檔案 | 狀態 |
|------|------|------|------|
| `list_dir` | 列出目錄內容 | [list_dir.md](list_dir.md) | ✅ |
| `read_file` | 讀取文件內容 | [read_file.md](read_file.md) | ✅ |
| `write_file` | 寫入文件 | [write_file.md](write_file.md) | ✅ |
| `read_excel` | 讀取 Excel 文件 | [read_excel.md](read_excel.md) | ✅ |
| `read_csv` | 讀取 CSV 文件 | [read_csv.md](read_csv.md) | ✅ |
| `read_word` | 讀取 Word 文件 | [read_word.md](read_word.md) | ✅ |
| `read_pdf` | 讀取 PDF 文件 | [read_pdf.md](read_pdf.md) | ✅ |

### Public Tools（可配置）

| Tool | 說明 | 檔案 | 狀態 |
|------|------|------|------|
| `web_search` | 網路搜尋 | [web_search.md](web_search.md) | ✅ |
| `knowledge_meta` | 查詢知識庫 meta | [knowledge_meta.md](knowledge_meta.md) | ✅ |
| `knowledge_query` | 查詢知識庫內容 | [knowledge_query.md](knowledge_query.md) | ✅ |
| `rebuild_knowledge_meta` | 重建知識庫 meta | [rebuild_knowledge_meta.md](rebuild_knowledge_meta.md) | ✅ |

---

## ⚙️ 配置方式說明

- **Internal Tools**：不開放給 `persona.config`，需修改 Agent 程式碼才能啟用（由開發者決定）
- **Public Tools**：可通過 `persona.config` 的 `tools.available` 配置

---

## 📊 完成狀態

**所有 Tool 參考文件已完成！** ✅

共 **11 個** Tool 參考文件：
- Internal Tools：7 個
- Public Tools：4 個

