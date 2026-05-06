# LibreChat MongoDB 表结构文档

> 本文档整理了 LibreChat 项目中所有 MongoDB 集合的结构和字段含义，为数据看板实现提供基础。

## 目录

- [核心业务表](#核心业务表)
  - [users - 用户表](#users---用户表)
  - [conversations - 对话表](#conversations---对话表)
  - [messages - 消息表](#messages---消息表)
- [计费相关表](#计费相关表)
  - [transactions - 交易记录表](#transactions---交易记录表)
  - [balances - 余额表](#balances---余额表)
- [AI 功能表](#ai-功能表)
  - [agents - 智能体表](#agents---智能体表)
  - [assistants - 助手表](#assistants---助手表)
  - [presets - 预设表](#presets---预设表)
- [内容管理表](#内容管理表)
  - [prompts - 提示词表](#prompts---提示词表)
  - [promptgroups - 提示词组表](#promptgroups---提示词词组表)
  - [memories - 记忆表](#memories---记忆表)
  - [files - 文件表](#files---文件表)
- [系统配置表](#系统配置表)
  - [roles - 角色表](#roles---角色表)
  - [groups - 用户组表](#groups---用户组表)
  - [configs - 配置表](#configs---配置表)
- [认证相关表](#认证相关表)
  - [sessions - 会话表](#sessions---会话表)
  - [tokens - 令牌表](#tokens---令牌表)
  - [keys - 密钥表](#keys---密钥表)
- [其他功能表](#其他功能表)
  - [sharedlinks - 分享链接表](#sharedlinks---分享链接表)
  - [actions - 动作表](#actions---动作表)
  - [toolcalls - 工具调用表](#toolcalls---工具调用表)

---

## 核心业务表

### users - 用户表

**集合名**: `users`
**模型名**: `User`
**用途**: 存储用户账户信息

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 用户唯一标识 |
| `name` | String | 否 | - | 用户显示名称 |
| `username` | String | 否 | - | 用户名（小写） |
| `email` | String | 是 | 是 | 邮箱地址（唯一） |
| `emailVerified` | Boolean | 是 | - | 邮箱是否验证 |
| `password` | String | 否 | - | 密码哈希（默认不查询） |
| `avatar` | String | 否 | - | 头像 URL |
| `provider` | String | 是 | - | 认证提供商（默认 `local`） |
| `role` | String | 否 | 是 | 用户角色（USER/ADMIN） |
| `googleId` | String | 否 | 是 | Google OAuth ID |
| `facebookId` | String | 否 | 是 | Facebook OAuth ID |
| `openidId` | String | 否 | 是 | OpenID ID |
| `samlId` | String | 否 | 是 | SAML ID |
| `ldapId` | String | 否 | 是 | LDAP ID |
| `githubId` | String | 否 | 是 | GitHub OAuth ID |
| `discordId` | String | 否 | 是 | Discord OAuth ID |
| `appleId` | String | 否 | 是 | Apple OAuth ID |
| `plugins` | Array | 否 | - | 插件列表 |
| `twoFactorEnabled` | Boolean | 否 | - | 是否启用双因素认证 |
| `totpSecret` | String | 否 | - | TOTP 密钥（默认不查询） |
| `backupCodes` | Array | 否 | - | 备用恢复码 |
| `refreshToken` | Array | 否 | - | 刷新令牌列表 |
| `expiresAt` | Date | 否 | TTL | 账户过期时间（7天后自动删除） |
| `termsAccepted` | Boolean | 否 | - | 是否接受服务条款 |
| `personalization` | Object | 否 | - | 个性化设置 |
| `favorites` | Array | 否 | - | 收藏列表（agent/model/endpoint/spec） |
| `idOnTheSource` | String | 否 | 稀疏 | 外部来源 ID |
| `tenantId` | String | 否 | 是 | 租户 ID（多租户） |
| `createdAt` | Date | 是 | - | 创建时间 |
| `updatedAt` | Date | 是 | - | 更新时间 |

**数据看板常用查询**:
- 用户总数统计
- 按时间段新增用户
- 按认证方式分布
- 活跃用户分析

---

### conversations - 对话表

**集合名**: `conversations`
**模型名**: `Conversation`
**用途**: 存储用户对话会话

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 对话唯一标识 |
| `conversationId` | String | 是 | 是 | 对话 ID（业务主键） |
| `title` | String | 否 | - | 对话标题（默认 "New Chat"） |
| `user` | String | 是 | 是 | 用户 ID |
| `messages` | Array[ObjectId] | 否 | - | 消息 ID 列表（引用 Message） |
| `endpoint` | String | 是 | - | 端点类型（openAI/azureOpenAI/anthropic 等） |
| `endpointType` | String | 否 | - | 端点类型细分 |
| `model` | String | 否 | - | 使用的模型名称 |
| `region` | String | 否 | - | 区域（Bedrock 专用） |
| `chatGptLabel` | String | 否 | - | ChatGPT 标签 |
| `modelLabel` | String | 否 | - | 模型标签 |
| `promptPrefix` | String | 否 | - | 提示词前缀 |
| `temperature` | Number | 否 | - | 温度参数 |
| `top_p` | Number | 否 | - | Top-p 采样 |
| `topP` | Number | 否 | - | Top P（Google 专用） |
| `topK` | Number | 否 | - | Top K（Google 专用） |
| `maxOutputTokens` | Number | 否 | - | 最大输出 Token |
| `maxTokens` | Number | 否 | - | 最大 Token |
| `presence_penalty` | Number | 否 | - | 存在惩罚 |
| `frequency_penalty` | Number | 否 | - | 频率惩罚 |
| `agent_id` | String | 否 | - | 关联的智能体 ID |
| `assistant_id` | String | 否 | - | 关联的助手 ID |
| `instructions` | String | 否 | - | 系统指令 |
| `system` | String | 否 | - | 系统提示词 |
| `tags` | Array[String] | 否 | 是 | 对话标签 |
| `files` | Array[String] | 否 | - | 关联文件 ID |
| `expiredAt` | Date | 否 | TTL | 过期时间 |
| `isArchived` | Boolean | 否 | - | 是否已归档 |
| `iconURL` | String | 否 | - | 图标 URL |
| `greeting` | String | 否 | - | 问候语 |
| `tenantId` | String | 否 | 是 | 租户 ID |
| `createdAt` | Date | 是 | 是 | 创建时间 |
| `updatedAt` | Date | 是 | 是 | 更新时间 |

**数据看板常用查询**:
- 对话总数统计
- 按用户统计对话数
- 按模型/端点分布
- 按时间段对话趋势
- 平均对话长度

---

### messages - 消息表

**集合名**: `messages`
**模型名**: `Message`
**用途**: 存储对话中的每条消息

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 消息唯一标识 |
| `messageId` | String | 是 | 是 | 消息 ID（业务主键） |
| `conversationId` | String | 是 | 是 | 所属对话 ID |
| `user` | String | 是 | 是 | 用户 ID |
| `model` | String | 否 | - | 使用的模型 |
| `endpoint` | String | 否 | - | 端点类型 |
| `parentMessageId` | String | 否 | - | 父消息 ID（对话树结构） |
| `tokenCount` | Number | 否 | - | Token 数量 |
| `summaryTokenCount` | Number | 否 | - | 摘要 Token 数量 |
| `sender` | String | 否 | - | 发送者标识 |
| `text` | String | 否 | - | 消息文本内容 |
| `summary` | String | 否 | - | 消息摘要 |
| `isCreatedByUser` | Boolean | 是 | - | 是否用户创建 |
| `unfinished` | Boolean | 否 | - | 是否未完成 |
| `error` | Boolean | 否 | - | 是否有错误 |
| `finish_reason` | String | 否 | - | 完成原因 |
| `feedback` | Object | 否 | - | 用户反馈 |
| `feedback.rating` | String | 否 | - | 评分（thumbsUp/thumbsDown） |
| `feedback.tag` | Mixed | 否 | - | 反馈标签 |
| `feedback.text` | String | 否 | - | 反馈文本 |
| `files` | Array[Mixed] | 否 | - | 关联文件 |
| `content` | Array[Mixed] | 否 | - | 内容块 |
| `thread_id` | String | 否 | - | 线程 ID |
| `iconURL` | String | 否 | - | 图标 URL |
| `metadata` | Mixed | 否 | - | 元数据 |
| `attachments` | Array[Mixed] | 否 | - | 附件列表 |
| `expiredAt` | Date | 否 | TTL | 过期时间 |
| `tenantId` | String | 否 | 是 | 租户 ID |
| `createdAt` | Date | 是 | 是 | 创建时间 |
| `updatedAt` | Date | 是 | - | 更新时间 |

**数据看板常用查询**:
- 消息总数统计
- 按模型统计消息数
- Token 使用统计
- 用户反馈统计
- 错误率分析

---

## 计费相关表

### transactions - 交易记录表

> **详细分析**: [transactions-analysis.md](./transactions-analysis.md) — 包含每个字段的深度解读、记录生成机制、费率计算逻辑、缓存 Token 处理、数据看板查询建议。

**集合名**: `transactions`
**模型名**: `Transaction`
**用途**: 记录 Token 使用和计费信息

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 交易唯一标识 |
| `user` | ObjectId | 是 | 是 | 用户 ID（引用 User） |
| `conversationId` | String | 否 | 是 | 对话 ID |
| `tokenType` | String | 是 | - | Token 类型（prompt/completion/credits） |
| `model` | String | 否 | 是 | 使用的模型 |
| `context` | String | 否 | - | 上下文 |
| `valueKey` | String | 否 | - | 值键 |
| `rate` | Number | 否 | - | 费率 |
| `rawAmount` | Number | 否 | - | 原始金额 |
| `tokenValue` | Number | 否 | - | Token 值 |
| `inputTokens` | Number | 否 | - | 输入 Token 数 |
| `writeTokens` | Number | 否 | - | 写入 Token 数 |
| `readTokens` | Number | 否 | - | 读取 Token 数 |
| `messageId` | String | 否 | - | 关联消息 ID |
| `tenantId` | String | 否 | 是 | 租户 ID |
| `createdAt` | Date | 是 | - | 创建时间 |
| `updatedAt` | Date | 是 | - | 更新时间 |

**数据看板常用查询**:
- Token 消耗总量
- 按用户统计消耗
- 按模型统计消耗
- 成本分析
- 消耗趋势图

---

### balances - 余额表

**集合名**: `balances`
**模型名**: `Balance`
**用途**: 存储用户余额和自动充值设置

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 余额唯一标识 |
| `user` | ObjectId | 是 | 是 | 用户 ID（引用 User） |
| `tokenCredits` | Number | 否 | - | Token 积分（1000积分 = $0.001） |
| `autoRefillEnabled` | Boolean | 否 | - | 是否启用自动充值 |
| `refillIntervalValue` | Number | 否 | - | 充值间隔值（默认 30） |
| `refillIntervalUnit` | String | 否 | - | 充值间隔单位（seconds/minutes/hours/days/weeks/months） |
| `lastRefill` | Date | 否 | - | 上次充值时间 |
| `refillAmount` | Number | 否 | - | 每次充值金额 |
| `tenantId` | String | 否 | 是 | 租户 ID |

**数据看板常用查询**:
- 用户余额统计
- 余额分布
- 自动充值使用情况

---

## AI 功能表

### agents - 智能体表

**集合名**: `agents`
**模型名**: `Agent`
**用途**: 存储自定义智能体配置

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 智能体唯一标识 |
| `id` | String | 是 | - | 智能体业务 ID |
| `name` | String | 否 | - | 智能体名称 |
| `description` | String | 否 | - | 描述 |
| `instructions` | String | 否 | - | 指令 |
| `avatar` | Mixed | 否 | - | 头像 |
| `provider` | String | 是 | - | 提供商 |
| `model` | String | 是 | - | 使用的模型 |
| `model_parameters` | Object | 否 | - | 模型参数 |
| `artifacts` | String | 否 | - | 工件配置 |
| `access_level` | Number | 否 | - | 访问级别 |
| `recursion_limit` | Number | 否 | - | 递归限制 |
| `tools` | Array[String] | 否 | - | 工具列表 |
| `tool_kwargs` | Array[Mixed] | 否 | - | 工具参数 |
| `actions` | Array[String] | 否 | - | 动作列表 |
| `author` | ObjectId | 是 | 是 | 创建者（引用 User） |
| `authorName` | String | 否 | - | 创建者名称 |
| `hide_sequential_outputs` | Boolean | 否 | - | 是否隐藏顺序输出 |
| `end_after_tools` | Boolean | 否 | - | 工具执行后是否结束 |
| `edges` | Array[Mixed] | 否 | - | 边（智能体连接关系） |
| `conversation_starters` | Array[String] | 否 | - | 对话启动器 |
| `tool_resources` | Mixed | 否 | - | 工具资源 |
| `versions` | Array[Mixed] | 否 | - | 版本历史 |
| `category` | String | 否 | 是 | 分类（默认 general） |
| `support_contact` | Mixed | 否 | - | 支持联系方式 |
| `is_promoted` | Boolean | 否 | 是 | 是否推荐 |
| `mcpServerNames` | Array[String] | 否 | 是 | MCP 服务器名称列表 |
| `tool_options` | Mixed | 否 | - | 工具选项 |
| `tenantId` | String | 否 | 是 | 租户 ID |
| `createdAt` | Date | 是 | - | 创建时间 |
| `updatedAt` | Date | 是 | 是 | 更新时间 |

**数据看板常用查询**:
- 智能体总数
- 按分类统计
- 热门智能体
- 创建者统计

---

### assistants - 助手表

**集合名**: `assistants`
**模型名**: `Assistant`
**用途**: 存储 OpenAI 风格的助手配置

| 字段 | 类型 | 必填  | 索引 | 说明 |
|------|------|-----|------|------|
| `_id` | ObjectId | 是   | 主键 | 助手唯一标识 |
| `user` | ObjectId | 是   | - | 用户 ID（引用 User） |
| `assistant_id` | String | 是   | 是 | 助手 ID |
| `avatar` | Mixed | w 否 | - | 头像 |
| `conversation_starters` | Array[String] | 否   | - | 对话启动器 |
| `access_level` | Number | 否   | - | 访问级别 |
| `file_ids` | Array[String] | 否   | - | 关联文件 ID |
| `actions` | Array[String] | 否   | - | 动作列表 |
| `append_current_datetime` | Boolean | 否   | - | 是否附加当前时间 |
| `tenantId` | String | 否   | 是 | 租户 ID |
| `createdAt` | Date | 是   | - | 创建时间 |
| `updatedAt` | Date | 是   | - | 更新时间 |

---

### presets - 预设表

**集合名**: `presets`
**模型名**: `Preset`
**用途**: 保存用户对话预设配置

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 预设唯一标识 |
| `presetId` | String | 是 | 是 | 预设 ID |
| `title` | String | 否 | - | 预设标题 |
| `user` | String | 否 | - | 用户 ID（null 表示公开预设） |
| `defaultPreset` | Boolean | 否 | - | 是否默认预设 |
| `order` | Number | 否 | - | 排序 |
| `endpoint` | String | 是 | - | 端点类型 |
| `model` | String | 否 | - | 模型名称 |
| `temperature` | Number | 否 | - | 温度参数 |
| `agent_id` | String | 否 | - | 关联智能体 |
| `assistant_id` | String | 否 | - | 关联助手 |
| `isArchived` | Boolean | 否 | - | 是否归档 |
| `iconURL` | String | 否 | - | 图标 URL |
| `greeting` | String | 否 | - | 问候语 |
| `tags` | Array[String] | 否 | - | 标签 |
| `tenantId` | String | 否 | 是 | 租户 ID |
| `createdAt` | Date | 是 | - | 创建时间 |
| `updatedAt` | Date | 是 | - | 更新时间 |

---

## 内容管理表

### prompts - 提示词表

**集合名**: `prompts`
**模型名**: `Prompt`
**用途**: 存储提示词版本

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 提示词唯一标识 |
| `groupId` | ObjectId | 是 | 是 | 所属组 ID（引用 PromptGroup） |
| `author` | ObjectId | 是 | 是 | 作者 ID（引用 User） |
| `prompt` | String | 是 | - | 提示词内容 |
| `type` | String | 是 | - | 类型（text/chat） |
| `tenantId` | String | 否 | 是 | 租户 ID |
| `createdAt` | Date | 是 | - | 创建时间 |
| `updatedAt` | Date | 是 | - | 更新时间 |

---

### promptgroups - 提示词组表

**集合名**: `promptgroups`
**模型名**: `PromptGroup`
**用途**: 管理提示词分组

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 组唯一标识 |
| `name` | String | 是 | 是 | 组名称 |
| `numberOfGenerations` | Number | 否 | - | 生成次数 |
| `oneliner` | String | 否 | - | 一句话描述 |
| `category` | String | 否 | 是 | 分类 |
| `productionId` | ObjectId | 是 | 是 | 生产版本 ID（引用 Prompt） |
| `author` | ObjectId | 是 | 是 | 作者 ID |
| `authorName` | String | 是 | - | 作者名称 |
| `command` | String | 否 | 是 | 快捷命令 |
| `tenantId` | String | 否 | 是 | 租户 ID |
| `createdAt` | Date | 是 | - | 创建时间 |
| `updatedAt` | Date | 是 | - | 更新时间 |

---

### memories - 记忆表

**集合名**: `memories`
**模型名**: `MemoryEntry`
**用途**: 存储用户记忆信息

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 记忆唯一标识 |
| `userId` | ObjectId | 是 | 是 | 用户 ID（引用 User） |
| `key` | String | 是 | - | 记忆键（仅小写字母和下划线） |
| `value` | String | 是 | - | 记忆值 |
| `tokenCount` | Number | 否 | - | Token 数量 |
| `updated_at` | Date | 否 | - | 更新时间 |
| `tenantId` | String | 否 | 是 | 租户 ID |

---

### files - 文件表

**集合名**: `files`
**模型名**: `File`
**用途**: 存储上传文件信息

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 文件唯一标识 |
| `user` | ObjectId | 是 | 是 | 用户 ID（引用 User） |
| `conversationId` | String | 否 | 是 | 对话 ID |
| `messageId` | String | 否 | 是 | 消息 ID |
| `file_id` | String | 是 | 是 | 文件 ID |
| `temp_file_id` | String | 否 | - | 临时文件 ID |
| `bytes` | Number | 是 | - | 文件大小（字节） |
| `filename` | String | 是 | - | 文件名 |
| `filepath` | String | 是 | - | 文件路径 |
| `object` | String | 是 | - | 对象类型（默认 file） |
| `embedded` | Boolean | 否 | - | 是否嵌入 |
| `type` | String | 是 | - | 文件类型 |
| `text` | String | 否 | - | 文本内容 |
| `context` | String | 否 | - | 上下文 |
| `usage` | Number | 是 | - | 使用次数 |
| `source` | String | 否 | - | 来源（默认 local） |
| `model` | String | 否 | - | 关联模型 |
| `width` | Number | 否 | - | 图片宽度 |
| `height` | Number | 否 | - | 图片高度 |
| `metadata` | Object | 否 | - | 元数据 |
| `expiresAt` | Date | 否 | TTL | 过期时间（1小时后删除） |
| `tenantId` | String | 否 | 是 | 租户 ID |
| `createdAt` | Date | 是 | - | 创建时间 |
| `updatedAt` | Date | 是 | - | 更新时间 |

**数据看板常用查询**:
- 文件总数统计
- 存储空间使用
- 按类型统计
- 上传趋势

---

## 系统配置表

### roles - 角色表

**集合名**: `roles`
**模型名**: `Role`
**用途**: 定义用户角色和权限

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 角色唯一标识 |
| `name` | String | 是 | 是 | 角色名称 |
| `description` | String | 否 | - | 描述 |
| `permissions` | Object | 否 | - | 权限配置 |
| `permissions.bookmarks` | Object | 否 | - | 书签权限 |
| `permissions.prompts` | Object | 否 | - | 提示词权限 |
| `permissions.memories` | Object | 否 | - | 记忆权限 |
| `permissions.agents` | Object | 否 | - | 智能体权限 |
| `permissions.multi_convo` | Object | 否 | - | 多对话权限 |
| `permissions.temporary_chat` | Object | 否 | - | 临时聊天权限 |
| `permissions.run_code` | Object | 否 | - | 代码运行权限 |
| `permissions.web_search` | Object | 否 | - | 网络搜索权限 |
| `permissions.people_picker` | Object | 否 | - | 人员选择器权限 |
| `permissions.marketplace` | Object | 否 | - | 市场权限 |
| `permissions.file_search` | Object | 否 | - | 文件搜索权限 |
| `permissions.file_citations` | Object | 否 | - | 文件引用权限 |
| `permissions.mcp_servers` | Object | 否 | - | MCP 服务器权限 |
| `permissions.remote_agents` | Object | 否 | - | 远程智能体权限 |
| `tenantId` | String | 否 | 是 | 租户 ID |

---

### groups - 用户组表

**集合名**: `groups`
**模型名**: `Group`
**用途**: 管理用户组

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 组唯一标识 |
| `name` | String | 是 | 是 | 组名称 |
| `description` | String | 否 | - | 描述 |
| `email` | String | 否 | 是 | 组邮箱 |
| `avatar` | String | 否 | - | 头像 |
| `memberIds` | Array[String] | 否 | 是 | 成员 ID 列表 |
| `source` | String | 否 | - | 来源（local/entra） |
| `idOnTheSource` | String | 否 | 稀疏 | 外部来源 ID |
| `tenantId` | String | 否 | 是 | 租户 ID |
| `createdAt` | Date | 是 | - | 创建时间 |
| `updatedAt` | Date | 是 | - | 更新时间 |

---

### configs - 配置表

**集合名**: `configs`
**模型名**: `Config`
**用途**: 存储主体配置

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 配置唯一标识 |
| `principalType` | String | 是 | 是 | 主体类型（USER/GROUP/ROLE） |
| `principalId` | String | 是 | 是 | 主体 ID |
| `principalModel` | String | 是 | - | 主体模型 |
| `priority` | Number | 是 | 是 | 优先级 |
| `overrides` | Mixed | 否 | - | 覆盖配置 |
| `isActive` | Boolean | 否 | 是 | 是否激活 |
| `configVersion` | Number | 否 | - | 配置版本 |
| `tenantId` | String | 否 | 是 | 租户 ID |
| `createdAt` | Date | 是 | - | 创建时间 |
| `updatedAt` | Date | 是 | - | 更新时间 |

---

## 认证相关表

### sessions - 会话表

**集合名**: `sessions`
**模型名**: `Session`
**用途**: 管理用户会话

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 会话唯一标识 |
| `refreshTokenHash` | String | 是 | - | 刷新令牌哈希 |
| `expiration` | Date | 是 | TTL | 过期时间 |
| `user` | ObjectId | 是 | - | 用户 ID（引用 User） |
| `tenantId` | String | 否 | 是 | 租户 ID |

---

### tokens - 令牌表

**集合名**: `tokens`
**模型名**: `Token`
**用途**: 存储认证令牌

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 令牌唯一标识 |
| `userId` | ObjectId | 是 | - | 用户 ID（引用 User） |
| `email` | String | 否 | - | 邮箱 |
| `type` | String | 否 | - | 令牌类型 |
| `identifier` | String | 否 | - | 标识符 |
| `token` | String | 是 | - | 令牌值 |
| `createdAt` | Date | 是 | - | 创建时间 |
| `expiresAt` | Date | 是 | TTL | 过期时间 |
| `metadata` | Map | 否 | - | 元数据 |
| `tenantId` | String | 否 | 是 | 租户 ID |

---

### keys - 密钥表

**集合名**: `keys`
**模型名**: `Key`
**用途**: 存储用户自定义密钥

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 密钥唯一标识 |
| `userId` | ObjectId | 是 | - | 用户 ID（引用 User） |
| `name` | String | 是 | - | 密钥名称 |
| `value` | String | 是 | - | 密钥值 |
| `expiresAt` | Date | 否 | TTL | 过期时间 |
| `tenantId` | String | 否 | 是 | 租户 ID |

---

## 其他功能表

### sharedlinks - 分享链接表

**集合名**: `sharedlinks`
**模型名**: `SharedLink`
**用途**: 管理对话分享链接

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 链接唯一标识 |
| `conversationId` | String | 是 | - | 对话 ID |
| `title` | String | 否 | 是 | 分享标题 |
| `user` | String | 否 | 是 | 用户 ID |
| `messages` | Array[ObjectId] | 否 | - | 消息 ID 列表 |
| `shareId` | String | 否 | 是 | 分享 ID |
| `targetMessageId` | String | 否 | 是 | 目标消息 ID |
| `isPublic` | Boolean | 否 | - | 是否公开 |
| `tenantId` | String | 否 | 是 | 租户 ID |
| `createdAt` | Date | 是 | - | 创建时间 |
| `updatedAt` | Date | 是 | - | 更新时间 |

---

### actions - 动作表

**集合名**: `actions`
**模型名**: `Action`
**用途**: 存储自定义动作/工具

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 动作唯一标识 |
| `user` | ObjectId | 是 | 是 | 用户 ID（引用 User） |
| `action_id` | String | 是 | 是 | 动作 ID |
| `type` | String | 否 | - | 类型（默认 action_prototype） |
| `settings` | Mixed | 否 | - | 设置 |
| `agent_id` | String | 否 | - | 关联智能体 |
| `assistant_id` | String | 否 | - | 关联助手 |
| `metadata` | Object | 否 | - | 元数据 |
| `metadata.api_key` | String | 否 | - | API 密钥 |
| `metadata.auth` | Object | 否 | - | 认证配置 |
| `metadata.domain` | String | 是 | - | 域名 |
| `tenantId` | String | 否 | 是 | 租户 ID |

---

### toolcalls - 工具调用表

**集合名**: `toolcalls`
**模型名**: `ToolCall`
**用途**: 存储工具调用结果

| 字段 | 类型 | 必填 | 索引 | 说明 |
|------|------|------|------|------|
| `_id` | ObjectId | 是 | 主键 | 调用唯一标识 |
| `conversationId` | String | 是 | - | 对话 ID |
| `messageId` | String | 是 | - | 消息 ID |
| `toolId` | String | 是 | - | 工具 ID |
| `user` | ObjectId | 是 | - | 用户 ID（引用 User） |
| `result` | Mixed | 否 | - | 调用结果 |
| `attachments` | Mixed | 否 | - | 附件 |
| `blockIndex` | Number | 否 | - | 块索引 |
| `partIndex` | Number | 否 | - | 部分索引 |
| `tenantId` | String | 否 | 是 | 租户 ID |
| `createdAt` | Date | 是 | - | 创建时间 |
| `updatedAt` | Date | 是 | - | 更新时间 |

---

## 数据看板关键指标

### 用户指标
- 总用户数: `db.users.countDocuments()`
- 今日新增: `db.users.countDocuments({ createdAt: { $gte: today } })`
- 活跃用户（7天内有对话）: 联表查询 `conversations` + `users`

### 对话指标
- 总对话数: `db.conversations.countDocuments()`
- 今日对话数: `db.conversations.countDocuments({ createdAt: { $gte: today } })`
- 平均对话长度: 聚合 `messages` 表

### Token 消耗指标
- 总 Token 消耗: 聚合 `transactions` 表
- 按模型消耗分布: `db.transactions.aggregate([{ $group: { _id: "$model", total: { $sum: "$tokenValue" } } }])`
- 按用户消耗排行: 聚合 `transactions` + `users`

### 模型使用统计
- 模型使用频次: 聚合 `messages` 或 `conversations` 表的 `model` 字段
- 端点使用分布: 聚合 `endpoint` 字段

### 存储指标
- 文件总数: `db.files.countDocuments()`
- 存储空间: `db.files.aggregate([{ $group: { _id: null, totalBytes: { $sum: "$bytes" } } }])`

---

## 索引优化建议

数据看板查询应优先利用现有索引：

1. **时间范围查询**: 使用 `createdAt` 索引
2. **用户关联查询**: 使用 `user` 字段索引
3. **租户隔离**: 所有查询应包含 `tenantId` 条件
4. **聚合管道**: 尽量在 `$match` 阶段使用索引字段

---

## 附录：集合名对照表

| 模型名 | 集合名 | 中文名 |
|--------|--------|--------|
| User | users | 用户 |
| Conversation | conversations | 对话 |
| Message | messages | 消息 |
| Transaction | transactions | 交易 |
| Balance | balances | 余额 |
| Agent | agents | 智能体 |
| Assistant | assistants | 助手 |
| Preset | presets | 预设 |
| Prompt | prompts | 提示词 |
| PromptGroup | promptgroups | 提示词组 |
| MemoryEntry | memories | 记忆 |
| File | files | 文件 |
| Role | roles | 角色 |
| Group | groups | 用户组 |
| Config | configs | 配置 |
| Session | sessions | 会话 |
| Token | tokens | 令牌 |
| Key | keys | 密钥 |
| SharedLink | sharedlinks | 分享链接 |
| Action | actions | 动作 |
| ToolCall | toolcalls | 工具调用 |
| Banner | banners | 公告横幅 |
| ConversationTag | conversationtags | 对话标签 |
| AgentApiKey | agentapikey | 智能体 API 密钥 |
| AgentCategory | agentcategories | 智能体分类 |
| MCPServer | mcpservers | MCP 服务器 |
| SystemGrant | systemgrants | 系统授权 |
| AccessRole | accessroles | 访问角色 |
| AclEntry | aclentries | 访问控制条目 |
| Category | categories | 分类 |
| PluginAuth | pluginauths | 插件认证 |
