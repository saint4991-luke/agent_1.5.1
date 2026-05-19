# `write_file` Tool

寫入文件內容。

## ⚙️ 配置方式

- **Persona Config:** ❌ 不可配置
- **啟用方式:** 需由開發者在 Agent 實作中決定

## 📍 路徑

`tools/internal/file_system/write_file.py`

## 🎯 設計目的

Internal Tools 不開放給平台用戶通過配置文件使用，
需要修改程式碼才能啟用，確保高權限操作的安全性。

## 📝 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `path` | string | ✅ | 文件路徑（相對於 `/workspace`） |
| `content` | string | ✅ | 文件內容 |
| `encoding` | string | ❌ | 文件編碼（預設：utf-8） |

## 📤 返回結果

```json
{
  "success": true,
  "data": {
    "path": "/workspace/personas/yuki/style.md",
    "size": 567,
    "action": "created"
  }
}
```

## ⚠️ 安全限制

- 只能寫入 `/workspace` 下的文件
- 防止路徑遍歷攻擊

---

**相關文件：**
- [read_file.md](read_file.md) - 讀取文件
- [list_dir.md](list_dir.md) - 列出目錄
