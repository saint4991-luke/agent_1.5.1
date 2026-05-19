# 🚀 快速開始指南

**版本：** v1.3  
**最後更新：** 2026-04-30  
**預計時間：** 10 分鐘

---

## 🎯 文件職責

**本文檔說明：**
- AgentShrimp 的快速安裝與啟動指南
- VH 和 BO 的第一次使用測試

---

## 🎯 目標

在 10 分鐘內：
1. 啟動 AgentShrimp 服務
2. 測試 VH 對話（Virtual Human）
3. 測試 BO 管理（Backend Operator）

---

## 📋 前置條件

### 必要條件

- ✅ Docker + Docker Compose 已安裝
- ✅ Git 已安裝
- ✅ API Key（Qwen / OpenAI）

### 檢查命令

```bash
# 檢查 Docker
docker --version
docker compose version

# 檢查 Git
git --version
```

---

## 步驟 1：克隆專案

```bash
# 克隆專案
git clone https://github.com/srjiang/agtshrimp.git
cd agtshrimp

# 切換到正確分支
git checkout agent-ubichan
```

---

## 步驟 2：配置環境

### 2.1 複製環境配置文件

```bash
cd setup
cp .env.example .env
```

### 2.2 編輯 .env 文件

```bash
# Linux / macOS
nano .env

# Windows
notepad .env
```

**必要配置：**
```bash
# OpenAI Provider（Qwen）
OPENAI_BASE_URL=http://116.50.47.234:8081/v1
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=Qwen/Qwen3.5-397B-A17B-FP8

# KNOWLEDGE 配置（選用）
KNOWLEDGE_PASSPHRASE=5688
```

**⚠️ 重要：** 將 `your-api-key-here` 替換為你的實際 API Key。

---

## 步驟 3：啟動服務

```bash
cd setup

# 構建並啟動
docker compose up -d --build

# 查看日誌（可選）
docker compose logs -f agent
```

**預期輸出：**
```
✔ Container setup-agent-1  Started
✔ Container setup-web-1     Started
```

---

## 步驟 4：驗證服務

### 4.1 檢查健康狀態

```bash
curl http://localhost:8000/health
```

**預期回應：**
```json
{"status":"healthy"}
```

### 4.2 訪問 Web UI

打開瀏覽器訪問：
- **Web UI:** http://localhost:5000
- **API:** http://localhost:8000

---

## 步驟 5：VH 對話測試（Virtual Human）

### 方法 A：使用 Web UI（推薦）

1. 打開 http://localhost:5000
2. 點擊「創建新對話」
3. 輸入訊息：「你好！」
4. 確認助手回應正常

### 方法 B：使用 CURL

```bash
# 創建 Session
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{
    "prefix": "TEST",
    "metadata": {"test": true}
  }'

# 回應：
# {"session_id": "TEST_abc123", ...}
```

```bash
# 發送訊息
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "TEST_abc123",
    "messages": [{"role": "user", "content": "你好！"}]
  }'
```

---

## 步驟 6：BO Agent 快速測試（Backend Operator）

### 什麼是 BO Agent？

**Backend Operator (BO)** 是系統的「後台管理助手」，幫你完成：
- ✅ 建立虛擬人（Persona）
- ✅ 建立知識庫（Knowledge）
- ✅ 系統配置管理

### 快速測試 1：建立第一個虛擬人

**1. 打開對話頁面**

訪問 http://localhost:5000 或使用 CURL

**2. 輸入指令：**
```
幫我創建一個新的虛擬人，ID 是 teacher
```

**3. BO 會回應：**
```
✅ 已創建 persona 目錄

workspace/personas/teacher/
├── style.md
└── config.yaml
```

**4. 編輯配置文件**

BO 會幫你打開文件，你需要填寫：

**style.md：**
```markdown
# 老師的風格定義

## 個性
耐心、專業、鼓勵學生

## 說話風格
清晰、有條理、常用舉例
```

**config.yaml：**
```yaml
persona_id: teacher
display_name: 王老師
style:
  file: style.md
output_format: virtual_human
knowledge:
  enabled: false
tools:
  enabled: false
```

**5. 驗證配置：**
```
檢查 teacher 的配置是否正確
```

**BO 回應：**
```
✅ teacher 配置檢查完成

目錄結構：正確
YAML 格式：正確
style.md：存在

可以開始使用了！
```

---

### 快速測試 2：建立第一個知識庫

**1. 輸入指令：**
```
幫我創建一個新的知識庫，ID 是 education
```

**2. BO 會回應：**
```
✅ 已創建知識庫目錄

knowledge/education/
└── (等待添加文件)
```

**3. 添加知識文件：**
```
在 education 知識庫添加 intro.txt

內容：
教育是什麼？
教育是一個培養人才、傳承知識的過程...
```

**4. 生成 Meta 索引：**
```
幫 education 知識庫生成 Meta
```

**5. BO 回應：**
```
✅ education 知識庫 Meta 已生成

掃描文件：1 個
- intro.txt (256 bytes)
```

---

### 進階：關聯虛擬人與知識庫

**讓虛擬人使用知識庫：**
```
修改 teacher 的 config.yaml，關聯 education 知識庫
```

**BO 會修改 config.yaml：**
```yaml
knowledge:
  enabled: true
  folders:
    - education/
```

**驗證關聯：**
```
檢查 teacher 的知識庫關聯
```

**BO 回應：**
```
✅ teacher 的知識庫配置

已啟用：true
關聯知識庫：
- education/ (✅ 存在)
```

---

## 📚 更多學習資源

### VH 相關
- **`02_PERSONA_GUIDE.md`** - Persona 設計與配置
- **`03_KNOWLEDGE_GUIDE.md`** - 知識庫管理

### BO 相關
- **`04_BO_AGENT_GUIDE.md`** - 完整的 BO 使用教學

### 故障排除
- **`05_DEPLOYMENT_TROUBLESHOOTING.md`** - 部署問題解決

---

## 🔧 常見問題

### 問題 1：Docker 啟動失敗

**錯誤：** `permission denied`

**解決：**
```bash
# Linux：將用戶加入 docker 組
sudo usermod -aG docker $USER
newgrp docker

# 重啟 Docker
sudo systemctl restart docker
```

### 問題 2：API Key 錯誤

**錯誤：** `401 Unauthorized`

**解決：**
1. 檢查 `.env` 中的 `OPENAI_API_KEY`
2. 確認 API Key 有效
3. 重啟服務：`docker compose restart`

### 問題 3：端口衝突

**錯誤：** `Address already in use`

**解決：**
```bash
# 檢查端口佔用
lsof -i :8000
lsof -i :5000

# 停止衝突服務或修改 docker-compose.yml 端口
```

---

## 🎉 完成！

你已成功啟動 AgentShrimp 服務並完成 VH 和 BO 的測試！

**有用連結：**
- 專案 Repo: https://github.com/srjiang/agtshrimp
- 文檔地圖：`docs/README.md`
- 技術規格：`docs/03_specs/`

---

**版本歷史：**
- v1.3 (2026-04-30) - 添加 BO 快速測試
- v1.2 (2026-04-16) - 初始版本
