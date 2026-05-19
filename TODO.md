# AgentShrimp TODO

**這是一個做事的筆記本** — 只記錄待辦事項，已完成項目會定期清除  
**最後更新：** 2026-04-30  
**狀態：** 進行中

---

## 🔴 高優先級

### #3. 移除棄用的 API 端點

**問題：** 以下 API 端點偏離原始設計，應移除：

1. `POST /vh/sessions/{session_id}/switch` - 切換虛擬人
2. `GET /vh/sessions/{session_id}/stats` - Session 統計
3. `GET /vh/sessions/stats` - 所有 Sessions 統計

**替代方案：**
- 切換虛擬人 → 直接創建新的 Session（`POST /vh/sessions`）
- Session 統計 → 無需替代（非核心功能）

**涉及檔案：**
- `agent/virtual_human/api.py`
- `docs/03_specs/01_AGENT_API_SPEC.md`

---

## 🟢 低優先級

### #8. Token Usage 追蹤

**建議：** 記錄 LLM 的 Token 使用量

```python
if hasattr(llm_result, 'usage'):
    print(f"📊 Token Usage: {llm_result.usage}")
```

**適用：**
- LLM1（快速回應）
- LLM2（完整回答）
- BO Agent

---

**文檔結束**
