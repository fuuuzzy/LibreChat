# transactions 交易记录表深度分析

> 基于源码 `packages/data-schemas/src/schema/transaction.ts`、`packages/data-schemas/src/methods/transaction.ts`、`packages/data-schemas/src/methods/spendTokens.ts`、`packages/data-schemas/src/methods/tx.ts`、`packages/api/src/agents/usage.ts` 的分析。

## 字段详解

### 基础字段

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 唯一标识 |
| `user` | ObjectId | 是 | 是 | 用户 ID（引用 users 表） |
| `conversationId` | String | 否 | 是 | 对话 ID |
| `messageId` | String | 否 | - | 生成此记录的消息 ID，同一次 AI 回复的 prompt 和 completion 记录共享同一 messageId |
| `model` | String | 否 | 是 | 模型名称（如 `claude-3-5-sonnet`、`gpt-4o`） |
| `tenantId` | String | 否 | 是 | 租户 ID |
| `createdAt` | Date | 是 | - | 创建时间（自动，`timestamps: true`） |
| `updatedAt` | Date | 是 | - | 更新时间（自动） |

### 核心计费字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `tokenType` | String | 枚举值：`'prompt'`（输入）/ `'completion'`（输出）/ `'credits'`（自动充值） |
| `rawAmount` | Number | **实际 token 数量，存储为负数**。如输入 1000 token 存为 `-1000` |
| `rate` | Number | 费率乘数，单位 USD/1M tokens。来自 `tokenValues` 定价表 |
| `tokenValue` | Number | **扣除的积分金额，负数**。公式：`rawAmount × rate` |

### 结构化 Token 字段

仅 `tokenType='prompt'` 的记录有值，用于区分缓存相关的 token 类型。

| 字段 | 类型 | 说明 |
|------|------|------|
| `inputTokens` | Number | **非缓存输入 token**，负数。按标准输入价格计费 |
| `writeTokens` | Number | **缓存写入 token**（对应 Anthropic `cache_creation_input_tokens`），负数。按缓存写入价格计费 |
| `readTokens` | Number | **缓存读取 token**（对应 Anthropic `cache_read_input_tokens`），负数。按缓存读取价格计费 |

三者关系：`rawAmount = inputTokens + writeTokens + readTokens`（均为负数）

### 辅助字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `valueKey` | String | 匹配到的定价表 key（如 `claude-3-5-sonnet`、`gpt-4o`） |
| `context` | String | 来源标记：`'message'`（正常消息）、`'abort'`/`'incomplete'`（中止）、`'summarization'`（摘要压缩） |
| `inputTokenCount` | Number | 本轮总 prompt token 数（正值），用于阶梯定价判断（如 Gemini 3.1 超 200k 加价） |

---

## 记录生成机制

### 每次 AI 回复产生两条记录

```
tokenType='prompt'     → rawAmount=-1500  （输入 1500 token）
tokenType='completion' → rawAmount=-800   （输出 800 token）
```

两条记录共享同一 `messageId`、`conversationId`、`user`。

### 生成流程

1. **BaseClient** 发起请求，记录 `promptTokens`（输入 token 数）
2. AI 返回响应后，获取 `completionTokens`（输出 token 数）
3. 调用 `spendTokens()` 或 `spendStructuredTokens()` 创建交易记录
4. `createTransaction()` / `createStructuredTransaction()` 计算 `rate` 和 `tokenValue` 并保存
5. 如果启用了余额功能，同时更新 `balances` 表

### 结构化 Token 的触发条件

当模型返回了缓存相关信息时（`cache_creation_input_tokens > 0` 或 `cache_read_input_tokens > 0`），使用 `spendStructuredTokens()` 创建记录，此时 prompt 记录会填充 `inputTokens`、`writeTokens`、`readTokens` 字段。

来源：`packages/api/src/agents/usage.ts` 中的 `splitUsage()` 函数。

---

## 费率计算

### 普通模式（calculateTokenValue）

```
tokenValue = rawAmount × rate
```

- `rate` 从 `tokenValues` 表查找，按 `valueKey` + `tokenType` 匹配
- 如果 `context='incomplete'`（中止），completion 的 `rate` 会乘以 1.15 惩罚系数

### 结构化模式（calculateStructuredTokenValue）

prompt 记录：
```
tokenValue = -(inputTokens × inputRate + writeTokens × writeRate + readTokens × readRate)
rate = 加权平均费率
rawAmount = inputTokens + writeTokens + readTokens
```

completion 记录仍使用普通模式。

### 定价表

- `tokenValues`：标准定价，USD/1M tokens
- `cacheTokenValues`：缓存定价（write/read），USD/1M tokens
- `premiumTokenValues`：阶梯定价（如 Gemini 3.1 超 200k token 加价）
- `endpointTokenConfig`：自定义端点定价（优先级最高）

源码位置：`packages/data-schemas/src/methods/tx.ts`

---

## 缓存 Token 的 Provider 差异

不同 Provider 的 `input_tokens` 字段含义不同：

**子集型**（`input_tokens` 已包含缓存 token）：
- OpenAI / Azure OpenAI
- Google / Vertex AI
- xAI, DeepSeek, OpenRouter, Moonshot

计算：`inputOnly = input_tokens - cache_creation - cache_read`

**独立型**（缓存 token 与 `input_tokens` 分开存储）：
- Anthropic / Bedrock

计算：`totalInput = input_tokens + cache_creation + cache_read`

源码：`packages/api/src/agents/usage.ts` 中的 `SUBSET_PROVIDERS` 和 `splitUsage()`。

---

## 数据看板查询建议

### 统计确切 token 数量

**使用 `rawAmount`（取绝对值），不要使用 `tokenValue`**（它是积分扣费金额 = token数 × 费率）。

```javascript
// 输入 token 总量
db.transactions.aggregate([
  { $match: { tokenType: 'prompt' } },
  { $group: { _id: null, total: { $sum: { $abs: '$rawAmount' } } } }
])

// 输出 token 总量
db.transactions.aggregate([
  { $match: { tokenType: 'completion' } },
  { $group: { _id: null, total: { $sum: { $abs: '$rawAmount' } } } }
])
```

### 统计结构化 token

```javascript
db.transactions.aggregate([
  { $match: { tokenType: 'prompt', inputTokens: { $exists: true } } },
  { $group: {
    _id: null,
    inputTokens: { $sum: { $abs: '$inputTokens' } },
    writeTokens:  { $sum: { $abs: '$writeTokens' } },
    readTokens:   { $sum: { $abs: '$readTokens' } }
  }}
])
```

### 统计费用（积分消耗）

```javascript
db.transactions.aggregate([
  { $group: { _id: null, totalCost: { $sum: { $abs: '$tokenValue' } } } }
])
```

---

## 注意事项

1. `tokenValue` 是积分扣费金额（token数 × 费率），不是 token 数量
2. `rawAmount` 是确切的 token 数量（取绝对值）
3. `tokenType='credits'` 是自动充值记录，不是 token 使用
4. 中止的消息 `context='incomplete'` 时，completion 的 `rate` 会 ×1.15（惩罚系数），但 `rawAmount` 仍是实际 token 数
5. `inputTokenCount` 是正值（总 prompt token 数），而 `inputTokens`/`writeTokens`/`readTokens`/`rawAmount` 都是负数
