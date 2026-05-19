# `list_dir` Tool

列出指定目錄的內容。

## ⚙️ 配置方式

- **Persona Config:** ❌ 不可配置
- **啟用方式:** 需由開發者在 Agent 實作中決定

## 📍 路徑

`tools/internal/file_system/list_dir.py`

## 🎯 設計目的

Internal Tools 不開放給平台用戶通過配置文件使用，
需要修改程式碼才能啟用，確保高權限操作的安全性。

## 📝 參數

| 參數 | 類型 | 必填 | 說明 |
|------|------|------|------|
| `path` | string | ✅ | 目錄路徑（相對於 `/workspace`） |

## 📤 返回結果

```json
{
  "success": true,
  "data": {
    "path": "/workspace/personas",
    "directories": ["TEMPLATE", "ubichan", "nurse"],
    "files": ["README.md"]
  }
}
```

## ⚠️ 安全限制

- 只能操作 `/workspace` 下的目錄
- 防止路徑遍歷攻擊（`..`）

## 💡 使用範例

**用戶輸入：**
```
幫我看看 personas 目錄下有什麼
```

**Tool 調用：**
```json
{
  "tool": "list_dir",
  "params": {
    "path": "personas"
  }
}
```

---

**相關文件：**
- [read_file.md](read_file.md) - 讀取文件內容
- [write_file.md](write_file.md) - 寫入文件
