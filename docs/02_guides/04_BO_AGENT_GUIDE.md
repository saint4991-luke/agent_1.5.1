# ⚙️ Backend Operator 使用指南

**版本：** v1.0  
**最後更新：** 2026-04-30  
**適用對象：** 系統管理員、開發者

---

## 🎯 文件職責

**本文檔說明：**
- 如何使用 BO Agent 建立虛擬人（Persona）
- 如何使用 BO Agent 建立知識庫（Knowledge）

**本文檔不包含：**
- VH 對話使用（→ `02_PERSONA_GUIDE.md`）
- 知識庫 RAG 使用（→ `03_KNOWLEDGE_GUIDE.md`）

---

## 🚀 快速開始

### BO 的核心用途

**BO 是「管理助手」**，幫你完成：
- ✅ 建立新的虛擬人（Persona）
- ✅ 建立新的知識庫（Knowledge）
- ✅ 維護與配置管理

---

## 📚 核心場景 1：建立虛擬人

### 步驟 1：創建 Persona 目錄

**告訴 BO：**
```
幫我創建一個新的虛擬人，ID 是 [persona_id]
```

**範例：**
```
用戶：幫我創建一個新的虛擬人，ID 是 teacher

BO：✅ 已創建 persona 目錄

workspace/personas/teacher/
├── style.md
└── config.yaml
```

---

### 步驟 2：編輯風格文件

**BO 會幫你打開文件**，你需要填寫：

```markdown
# [角色名稱] 的風格定義

## 個性
[描述角色個性]

## 說話風格
[描述說話方式]

## 口頭禪
[常見用語]
```

**範例：**
```markdown
# 老師的風格定義

## 個性
耐心、專業、鼓勵學生

## 說話風格
清晰、有條理、常用舉例

## 口頭禪
- 讓我們一起來看看...
- 你理解了嗎？
- 有任何問題都可以問我
```

---

### 步驟 3：編輯配置文件

**BO 會幫你打開 `config.yaml`**，你需要填寫：

```yaml
persona_id: [ID]
display_name: [顯示名稱]

style:
  file: style.md

output_format: virtual_human

knowledge:
  enabled: true
  folders:
    - [knowledge_id]/

tools:
  enabled: false
  available: []
```

**範例：**
```yaml
persona_id: teacher
display_name: 王老師

style:
  file: style.md

output_format: virtual_human

knowledge:
  enabled: true
  folders:
    - education/

tools:
  enabled: false
  available: []
```

---

### 步驟 4：驗證配置

**告訴 BO：**
```
檢查 teacher 的配置是否正確
```

**BO 會：**
1. 檢查目錄結構
2. 檢查 YAML 格式
3. 檢查 style.md 內容
4. 回報結果

**回應範例：**
```
✅ teacher 配置檢查完成

目錄結構：正確
YAML 格式：正確
style.md：存在
知識庫關聯：education/

可以開始使用了！
```

---

## 📚 核心場景 2：建立知識庫

### 步驟 1：創建 Knowledge 目錄

**告訴 BO：**
```
幫我創建一個新的知識庫，ID 是 [knowledge_id]
```

**範例：**
```
用戶：幫我創建一個新的知識庫，ID 是 education

BO：✅ 已創建知識庫目錄

knowledge/education/
└── (等待添加文件)
```

---

### 步驟 2：添加知識文件

**告訴 BO：**
```
在 education 知識庫添加文件
```

**BO 會問你：**
```
請提供：
1. 文件名稱（例如：intro.txt）
2. 文件內容（可以直接貼上）
```

**範例：**
```
用戶：添加 intro.txt

內容：
教育是什麼？
教育是一個培養人才、傳承知識的過程...
```

**BO 回應：**
```
✅ 已添加 intro.txt 到 education 知識庫

文件路徑：knowledge/education/intro.txt
大小：256 bytes
```

---

### 步驟 3：生成 Meta 索引

**告訴 BO：**
```
幫 education 知識庫生成 Meta
```

**BO 會：**
1. 掃描所有文件
2. 生成 meta.json
3. 回報結果

**回應範例：**
```
✅ education 知識庫 Meta 已生成

掃描文件：1 個
- intro.txt (256 bytes)

總大小：256 bytes
Meta 路徑：knowledge/education/meta.json
```

---

### 步驟 4：驗證知識庫

**告訴 BO：**
```
檢查 education 知識庫的狀態
```

**BO 會：**
1. 檢查目錄結構
2. 檢查 meta.json
3. 回報結果

**回應範例：**
```
✅ education 知識庫檢查完成

目錄結構：正確
Meta 狀態：正常
文件數量：1
總大小：256 bytes

可以開始使用了！
```

---

## 🔗 關聯虛擬人與知識庫

### 場景：讓虛擬人使用知識庫

**步驟 1：修改 Persona 配置**

**告訴 BO：**
```
修改 teacher 的 config.yaml，關聯 education 知識庫
```

**BO 會修改：**
```yaml
knowledge:
  enabled: true
  folders:
    - education/
```

---

### 步驟 2：驗證關聯

**告訴 BO：**
```
檢查 teacher 的知識庫關聯
```

**BO 回應：**
```
✅ teacher 的知識庫配置

已啟用：true
關聯知識庫：
- education/ (✅ 存在)

關聯正確！
```

---

## 💡 進階技巧

### 技巧 1：批量創建多個虛擬人

可以一次性創建多個虛擬人：

```
用戶：幫我創建 3 個虛擬人：math_teacher, english_teacher, science_teacher

BO：✅ 已創建 3 個 persona 目錄

- workspace/personas/math_teacher/
- workspace/personas/english_teacher/
- workspace/personas/science_teacher/

請分別編輯 style.md 和 config.yaml
```

---

### 技巧 2：複製現有配置

**告訴 BO：**
```
複製 ubichan 的配置到新虛擬人
```

**BO 會：**
1. 複製目錄結構
2. 保留配置文件格式
3. 讓你修改內容

---

### 技巧 3：批量添加知識文件

**告訴 BO：**
```
批量添加文件到 education 知識庫
```

**BO 會問：**
```
請提供：
1. 文件列表
2. 每個文件的內容
```

---

## ⚠️ 注意事項

### 命名規則

- **Persona ID：** 小寫英文 + 底線（例如：`math_teacher`）
- **Knowledge ID：** 小寫英文 + 底線（例如：`education_2026`）
- **文件名稱：** 小寫英文 + `.txt` 或 `.md`

### 目錄結構

```
workspace/personas/[persona_id]/
├── style.md          ← 必須
└── config.yaml       ← 必須

knowledge/[knowledge_id]/
├── meta.json         ← 自動生成
└── *.txt / *.md      ← 至少 1 個文件
```

### 常見錯誤

| 錯誤 | 原因 | 解決方法 |
|------|------|----------|
| YAML 格式錯誤 | 縮排不對 | 使用 2 空格縮排 |
| Meta 生成失敗 | 沒有文件 | 先添加知識文件 |
| 關聯失敗 | 知識庫不存在 | 確認 knowledge_id 正確 |

---

## 🆘 常見問題

### Q: 創建虛擬人後為什麼沒有反應？

**可能原因：**
1. 目錄已存在
2. 配置文件格式錯誤

**解決方法：**
```
1. 檢查目錄：列出 personas/ 的內容
2. 檢查 YAML：讀取 config.yaml
3. 修正後重試
```

---

### Q: 知識庫 Meta 需要手動編輯嗎？

**不需要！** Meta 是自動生成的。

**正確做法：**
```
1. 添加知識文件
2. 告訴 BO：「幫 [knowledge_id] 生成 Meta」
3. BO 自動生成 meta.json
```

---

### Q: 可以修改現有的虛擬人嗎？

**可以！**

**告訴 BO：**
```
修改 [persona_id] 的 [配置項目]
```

**範例：**
```
用戶：修改 teacher 的知識庫關聯為 math

BO：✅ 已修改 teacher 的 config.yaml

knowledge.folders:
- education/ → math/
```

---

## 📚 相關資源

### 其他指南

- **Persona 設計：** `02_PERSONA_GUIDE.md`
- **知識庫管理：** `03_KNOWLEDGE_GUIDE.md`
- **快速開始：** `01_QUICKSTART.md`

### 技術文檔

- **架構設計：** `01_designs/02_BACKEND_OPERATOR_DESIGN.md`
- **Workflow 規格：** `03_specs/16_BO_WORKFLOW_SPEC.md`

---

**最後更新：** 2026-04-30  
**維護者：** 系統管理團隊
