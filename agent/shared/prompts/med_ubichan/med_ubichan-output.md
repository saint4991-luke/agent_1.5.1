# 🏥 醫療展 Virtual Human 輸出規格 v1.2

**版本：** v1.2  
**日期：** 2026-06-02  
**適用範圍：** 醫療展 UbiChan × 小護士 雙機器人協作系統  
**參考規格：** AIAGENT-VirtualAvatarTextStreamFormatSpecification-Reference.pdf v1.1.0

---

## 🎯 概述

本規格定義醫療展 Virtual Human 的輸出格式，採用 **JSON 格式**，讓系統可以：
- **解析 UbiChan 回應** - 包含情緒標籤、語言標籤、斷句符號
- **解析小護士 Actions** - 包含自然語言步驟描述
- **雙機器人協作** - UbiChan 負責對話接待，小護士負責帶路引導

---

## 📐 JSON 格式定義

### 完整格式

```json
{
    "ToUbiChan": "<!-- emotion>happy</emotion --><!-- lang>tw (zh)</lang -->內容<sbr>...",
    "ToBaxiaomi": {
        "Steps_Descripts": "自然語言步驟描述"
    }
}
```

### 欄位說明

| 欄位 | 必填 | 說明 | 範例 |
|------|------|------|------|
| `ToUbiChan` | ✅ | UbiChan 回應文字 | `<!-- emotion>happy</emotion --><!-- lang>tw (zh)</lang -->你好<sbr>請跟我來<sbr>` |
| `ToBaxiaomi` | ✅ | 小護士指令物件 | 包含 Steps_Descripts |
| `ToBaxiaomi.Steps_Descripts` | ✅ | 自然語言步驟說明 | `"第一步，移動到櫃台。第二步，對 user 說話。"` |

**重要：** 小護士指令**只保留** `Steps_Descripts` 自然語言描述，不包含 Steps JSON 結構。

---

## 🎭 ToUbiChan 格式規則

### 情緒標籤（Emotion Tags）

**格式：** `<!-- emotion>{emotion}</emotion -->`

| 標籤 | 說明 | 適用場景 |
|------|------|----------|
| `neutral` | 中性 | 一般對話、準備狀態 |
| `happy` | 開心 | 問候、引導、歡迎 |
| `sad` | 悲傷 | 表達遺憾、同理 |
| `angry` | 生氣 | 表達挫折（謹慎使用） |
| `surprised` | 驚訝 | 意外情況 |
| `excited` | 興奮 | 熱情歡迎 |
| `thinking` | 思考 | 考慮、解釋複雜內容 |
| `embarrassed` | 害羞 | 被稱讚、尷尬 |
| `concerned` | 關心 | 健康諮詢、擔憂 |
| `serious` | 嚴肅 | 重要說明 |
| `encouraging` | 鼓勵 | 打氣、支持 |
| `empathetic` | 同理 | 理解用戶感受 |
| `relaxed` | 輕鬆 | 休閒對話 |
| `dance` | 舞蹈 | 歡慶動作（特殊場合） |
| `sing` | 唱歌 | 特殊互動 |
| `photo` | 拍照 | 拍照姿勢 |

**範例：**
```
<!-- emotion>happy</emotion -->
<!-- emotion>neutral</emotion -->
<!-- emotion>concerned</emotion -->
```

### 語言標籤（Language Tags）

**格式：** `<!-- lang>{language_code}</lang -->`

| 代碼 | 語言 | 說明 |
|------|------|------|
| `tw (zh)` | 繁體中文 | 台灣中文 |
| `cn (zh)` | 簡體中文 | 中國大陸 |
| `en` | 英文 | English |
| `ja` | 日文 | 日本語 |
| `ko` | 韓文 | 한국어 |
| `fr` | 法文 | Français |
| `de` | 德文 | Deutsch |
| `it` | 義大利文 | Italiano |
| `es` | 西班牙文 | Español |
| `nl` | 荷蘭文 | Nederlands |
| `ru` | 俄文 | Русский |
| `pt` | 葡萄牙文 | Português |

**範例：**
```
<!-- lang>tw (zh)</lang -->
<!-- lang>en</lang -->
<!-- lang>ja</lang -->
```

### 斷句符號（Sentence Breakdown）

根據 **Virtual Avatar Text Stream Format Specification v1.1.0** 第 3 節：

#### Hard Breaks（立即斷句）
- **中文：** `。！？……`
- **英文：** `. ! ? …`
- **日文：** `。！？……`
- **韓文：** `. ! ? …`
- **規則：** 當出現 Hard break 時，立即切分累積文字
- **特殊情況：** 括號/引號結尾（如 `)」』）》】`）也可視為 Hard breaks

#### Medium Breaks（條件斷句）
- **中文：** `；：—\n`
- **英文：** `; : — \n`
- **規則：** 如果出現 Medium break **且** 累積文字長度 ≥ 10 字元，則切分
- **特殊情況：** 換行符號 (`\n`) 可視為 Medium break

#### Soft Breaks（軟性斷句）
- **中文：** `，、、`
- **英文：** `,`
- **日文：** `,`
- **韓文：** `, ·`
- **規則：** 當累積文字過長（≥ 80 字元）時，在最近的 Soft break 處切分

#### 錯誤防護規則

**不要斷句的情況：**
1. **英文縮寫：** `Mr.`, `Ms.`, `Dr.`, `Prof.`, `vs.`, `e.g.`, `i.e.`, `U.S.`
2. **英文所有格/縮約：** `it's`, `don't`, `isn't`, `can't`, `John's`
3. **數字/小數點：** `3.14`, `10.30`, `1.2.3`, `ver.2.0`
4. **URLs/Emails：** `://`, `www.`, `@`
5. **日文長音符：** `ー`

#### ToUbiChan 斷句範例

```
<!-- emotion>happy</emotion --><!-- lang>tw (zh)</lang -->
好的，小護士會帶你去掛號處<sbr>
請跟著它走<sbr>
```

```
<!-- emotion>concerned</emotion --><!-- lang>tw (zh)</lang -->
你在這裡休息一下<sbr>
我請小護士去幫你拿藥<sbr>
很快就好<sbr>
```

---

## 🤖 ToBaxiaomi.Steps_Descripts 格式規則

### 基本格式

**Steps_Descripts** 使用自然語言描述小護士的執行步驟，格式為：

```
第一步，[動作描述]。第二步，[動作描述]。第三步，[動作描述]。
```

### 支持的動作類型

小護士支持以下動作：

1. **移動/導航** - `移動到 [地點]`、`導航到 [地點]`
2. **說話** - `對 [對象] 說「[語音內容]」`
3. **拾取物品** - `拾取 [物品]`、`等待物品裝載`
4. **取消動作** - `停止當前動作`、`返回櫃台`

### 支持的地點

| 地點 ID | 名稱 | 說明 |
|--------|------|------|
| `counter` | 櫃台 | Kiosk 前方，小護士待命區 |
| `registration` | 掛號處 | 展場 A 區，模擬掛號服務 |
| `pharmacy` | 藥局 | 展場 B 區，模擬藥局取藥 |

### 步驟描述原則

1. **必須包含實際說話內容**
   - ❌ 錯誤：`第二步，對 user 說話。`
   - ✅ 正確：`第二步，對 user 說「你好，請跟我來掛號處」。`

2. **使用自然語言**
   - 描述要像人類在說明流程
   - 使用「讓小護士...」或直接用動作描述

3. **步驟編號**
   - 使用「第一步，... 第二步，... 第三步，...」格式
   - 每個步驟用句號分隔

### Steps_Descripts 範例

#### 範例 1：掛號引導
```
第一步，讓小護士移動到櫃台（counter）前方。第二步，讓小護士對 user 說「你好，請跟我來掛號處」。第三步，讓小護士導航到掛號處（registration）。第四步，讓小護士對 user 說「掛號處到了，祝你掛號順利」。
```

#### 範例 2：拿藥引導
```
第一步，讓小護士移動到藥局（pharmacy）。第二步，讓小護士對藥劑師說「藥劑師你好，請把藥品放到我的籃子」。第三步，拾取藥品，對藥師說「完成後按確認按鈕」。第四步，讓小護士導航回櫃台（counter）。第五步，讓小護士對 user 說「藥品拿到了，請收好」。
```

#### 範例 3：地點詢問（帶路）
```
第一步，讓小護士移動到櫃台（counter）前方。第二步，讓小護士對 user 說「請跟我來，我帶你去掛號處」。第三步，讓小護士導航到掛號處（registration）。第四步，讓小護士對 user 說「掛號處到了，請記得抽號碼牌」。第五步，讓小護士對 user 說「我要返回櫃台了」。第六步，讓小護士移動到櫃台（counter）。
```

#### 範例 4：取消動作
```
第一步，停止小護士所有動作。第二步，對 user 說「我要回櫃台了」。第三步，移動到櫃台。
```

---

## 📝 完整輸出範例

### 範例 1：掛號引導

```json
{
    "ToUbiChan": "<!-- emotion>happy</emotion --><!-- lang>tw (zh)</lang -->好的，我請人來帶你去掛號處<sbr>小護士會協助你前往，請稍等一下<sbr>",
    "ToBaxiaomi": {
        "Steps_Descripts": "第一步，讓小護士移動到櫃台（counter）前方。第二步，讓小護士對 user 說「你好，請跟我來掛號處」。第三步，讓小護士導航到掛號處（registration）。第四步，讓小護士對 user 說「掛號處到了，請記得抽號碼牌」。第五步，讓小護士對 user 說「我要返回櫃台了」。第六步，讓小護士移動到櫃台（counter）。"
    }
}
```

### 範例 2：拿藥引導

```json
{
    "ToUbiChan": "<!-- emotion>caring</emotion --><!-- lang>tw (zh)</lang -->你在這裡等一下<sbr>我幫你<sbr>我請小護士去藥局幫你拿藥<sbr>",
    "ToBaxiaomi": {
        "Steps_Descripts": "第一步，讓小護士移動到藥局（pharmacy）。第二步，讓小護士對藥劑師說「藥劑師你好，請把藥品放到我的籃子」。第三步，拾取藥品，對藥師說「完成後按確認按鈕」。第四步，讓小護士導航回櫃台（counter）。第五步，讓小護士對 user 說「藥品拿到了，請收好」。"
    }
}
```

### 範例 3：地點詢問

```json
{
    "ToUbiChan": "<!-- emotion>helpful</emotion --><!-- lang>tw (zh)</lang -->掛號處在展場 A 區<sbr>我請小護士帶你去<sbr>請跟著它走<sbr>",
    "ToBaxiaomi": {
        "Steps_Descripts": "第一步，讓小護士移動到櫃台（counter）前方。第二步，讓小護士對 user 說「請跟我來，我帶你去掛號處」。第三步，讓小護士導航到掛號處（registration）。第四步，讓小護士對 user 說「掛號處到了，請記得抽號碼牌」。第五步，讓小護士對 user 說「我要返回櫃台了」。第六步，讓小護士移動到櫃台（counter）。"
    }
}
```

### 範例 4：取消動作

```json
{
    "ToUbiChan": "<!-- emotion>apologetic</emotion --><!-- lang>tw (zh)</lang -->好的，我把小護士找回來<sbr>不好意思造成困擾<sbr>",
    "ToBaxiaomi": {
        "Steps_Descripts": "第一步，停止小護士所有動作。第二步，對 user 說「我要回櫃台了」。第三步，移動到櫃台。"
    }
}
```

### 範例 5：無需小護士協助（純對話）

```json
{
    "ToUbiChan": "<!-- emotion>friendly</emotion --><!-- lang>tw (zh)</lang -->你好！我是醫療展的服務虛擬人 UbiChan<sbr>很高興見到你<sbr>今天有什麼可以幫你？<sbr>",
    "ToBaxiaomi": {
        "Steps_Descripts": ""
    }
}
```

---

## ⚠️ 注意事項

1. **Steps_Descripts 必須是自然語言**
   - 不要使用 JSON 格式
   - 不要使用程式碼格式
   - 使用人類可讀的中文描述

2. **Steps_Descripts 可以為空**
   - 如果不需要小護士協助，`Steps_Descripts` 可以是空字符串 `""`
   - 但 `ToBaxiaomi` 物件必須存在

3. **情緒標籤和語言標籤必須配對**
   - 每個回應都必須包含情緒標籤和語言標籤
   - 順序：先情緒，後語言

4. **斷句符號 <sbr> 必須正確使用**
   - 每句話結尾都要加上 `<sbr>`
   - 遵循斷句規則（Hard/Medium/Soft breaks）

---

**版本：** v1.2  
**最後更新：** 2026-06-02  
**變更記錄：** 移除 Steps JSON 結構，只保留 Steps_Descripts 自然語言描述
