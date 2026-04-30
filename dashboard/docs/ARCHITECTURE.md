# LibreChat 架构文档 (v0.8.5)

## 1. 项目总览

LibreChat 是一个开源 AI 聊天平台，采用 **Monorepo** 结构，使用 npm workspaces + Turborepo 管理。

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | React 18 + TypeScript + Vite + Tailwind CSS |
| 后端 | Express.js (JS legacy) + TypeScript (新代码) |
| 数据库 | MongoDB (Mongoose ODM) |
| 缓存 | Redis |
| 状态管理 | Jotai (原子化状态) + React Query (服务端状态) |
| 构建 | Turborepo (并行构建) + Vite (前端) |
| 容器化 | Docker + Docker Compose + Helm Charts |

### Workspace 结构



```
LibreChat/
├── api/                    # 后端 (JS legacy, Express)
├── client/                 # 前端 SPA (React + TypeScript)
├── packages/
│   ├── data-provider/      # 共享 API 类型/端点/数据服务
│   ├── data-schemas/       # 数据库模型/Schema
│   ├── api/                # 新后端代码 (TypeScript)
│   └── client/             # 共享前端工具库
├── config/                 # 运维脚本
├── e2e/                    # E2E 测试 (Playwright)
└── src/                    # 根级测试
```

---

## 2. 前端架构 (`client/src/`)

### 2.1 目录结构

```
client/src/
├── App.jsx                 # 应用入口
├── main.jsx                # 挂载点
├── Providers/              # 全局 Provider 组合
├── routes/                 # 路由定义
├── components/             # UI 组件 (按功能分组)
├── hooks/                  # 自定义 Hooks
├── data-provider/          # API 调用层 (React Query)
├── store/                  # Jotai 原子状态
├── locales/                # i18n 翻译文件
├── utils/                  # 工具函数
├── constants/              # 常量定义
├── common/                 # 共享 UI 模式
└── a11y/                   # 无障碍访问
```

### 2.2 路由系统 (`routes/`)

| 路由文件 | 功能 |
|----------|------|
| `Root.tsx` | 根布局，全局 Provider |
| `ChatRoute.tsx` | 主聊天界面 |
| `ShareRoute.tsx` | 共享对话查看 |
| `Search.tsx` | 搜索页面 |
| `Dashboard.tsx` | 仪表盘/Agent 市场 |
| `Layouts/` | 布局组件 (侧边栏、面板) |
| `useAuthRedirect.ts` | 认证重定向逻辑 |

### 2.3 核心组件模块 (`components/`)

#### Chat 模块

```
Chat/
├── ChatView.tsx            # 主聊天视图
├── Header.tsx / Footer.tsx # 头部/底部
├── Landing.tsx             # 首次进入欢迎页
├── TemporaryChat.tsx       # 临时对话模式
├── Input/                  # 输入区域 (30+ 子组件)
│   ├── ChatForm.tsx        # 主输入表单
│   ├── SendButton.tsx      # 发送按钮
│   ├── AudioRecorder.tsx   # 语音输入
│   ├── FileSearch.tsx      # 文件搜索
│   ├── MCPSelect.tsx       # MCP 服务器选择
│   ├── Mention.tsx         # @提及
│   ├── WebSearch.tsx       # 网页搜索
│   ├── CodeInterpreter.tsx # 代码解释器
│   └── ToolsDropdown.tsx   # 工具下拉菜单
├── Messages/               # 消息展示
│   ├── Message.tsx         # 单条消息
│   ├── MultiMessage.tsx    # 消息列表
│   ├── MessagesView.tsx    # 消息视图容器
│   ├── Content/            # 消息内容渲染
│   ├── HoverButtons.tsx    # 悬停操作按钮
│   ├── Feedback.tsx        # 反馈 (点赞/踩)
│   ├── Fork.tsx            # 分叉对话
│   └── SiblingSwitch.tsx   # 同级回复切换
└── Menus/                  # 聊天菜单
```

#### Agents 模块

```
Agents/
├── Marketplace.tsx         # Agent 市场首页
├── AgentGrid.tsx           # Agent 网格展示
├── AgentCard.tsx           # Agent 卡片
├── AgentDetail.tsx         # Agent 详情页
├── CategoryTabs.tsx        # 分类标签
├── SearchBar.tsx           # 搜索栏
└── VirtualizedAgentGrid.tsx # 虚拟化列表 (性能)
```

#### SidePanel 模块 (右侧边栏)

```
SidePanel/
├── Agents/                 # Agent 配置面板 (40+ 文件)
│   ├── AgentPanel.tsx      # Agent 编辑主面板
│   ├── AgentConfig.tsx     # Agent 配置
│   ├── ActionsPanel.tsx    # Actions 配置
│   ├── MCPTools.tsx        # MCP 工具配置
│   ├── Instructions.tsx    # 系统指令
│   ├── Code/               # 代码解释器
│   ├── Advanced/           # 高级设置
│   └── Version/            # 版本管理
├── Parameters/             # 模型参数调节
├── Files/                  # 文件管理
├── Bookmarks/              # 书签
├── Memories/               # 记忆管理
└── MCPBuilder/             # MCP 构建器
```

#### 其他核心组件

| 组件 | 功能 |
|------|------|
| `Endpoints/` | 端点图标、设置、预设保存 |
| `Artifacts/` | 代码/文档预览、Mermaid 图表、版本管理 |
| `Prompts/` | 提示词管理 (编辑器、变量、命令面板) |
| `MCP/` | MCP 服务器配置对话框、状态图标 |
| `Plugins/` | 插件凭证、搜索、MCP 管理 |
| `Share/` | 共享对话查看、消息渲染 |
| `Nav/` | 导航栏、设置、书签、Agent 市场入口 |
| `Bookmarks/` | 对话收藏 |
| `Conversations/` | 对话列表管理 |

### 2.4 状态管理 (`store/`)

使用 **Jotai** 原子化状态：

| Store 文件 | 管理内容 |
|------------|----------|
| `agents.ts` | Agent 相关状态 |
| `artifacts.ts` | Artifacts 面板状态 |
| `endpoints.ts` | 端点选择状态 |
| `families.ts` | 模型族分组 |
| `favorites.ts` | 收藏状态 |
| `fontSize.ts` | 字体大小 |
| `language.ts` | 语言设置 |
| `mcp.ts` | MCP 服务器状态 |
| `preset.ts` | 预设配置 |
| `prompts.ts` | 提示词状态 |
| `search.ts` | 搜索状态 |
| `settings.ts` | 用户设置 |
| `showThinking.ts` | 思考过程显示 |
| `submission.ts` | 消息提交状态 |
| `temporary.ts` | 临时对话状态 |
| `text.ts` | 输入文本状态 |
| `toast.ts` | 通知消息 |
| `user.ts` | 用户信息 |

### 2.5 数据层 (`data-provider/`)

前端 API 调用层，基于 **React Query**：

```
data-provider/
├── Agents/                 # Agent 相关查询/变更
├── Auth/                   # 认证相关
├── Endpoints/              # 端点配置
├── Files/                  # 文件操作
├── MCP/                    # MCP 服务器
├── Memories/               # 记忆管理
├── Messages/               # 消息 CRUD
├── Misc/                   # 杂项
├── SSE/                    # Server-Sent Events 流式
├── Tools/                  # 工具管理
├── mutations.ts            # 通用变更
├── queries.ts              # 通用查询
├── connection.ts           # 连接管理
├── prompts.ts              # 提示词查询
├── roles.ts                # 角色权限
└── tags.ts                 # 标签管理
```

### 2.6 Hooks (`hooks/`)

按功能分组的自定义 Hooks：

| 分组 | 功能 |
|------|------|
| `Agents/` | Agent 操作相关 |
| `Chat/` | 聊天逻辑 (提交、编辑、重试) |
| `Config/` | 配置读取 |
| `Conversations/` | 对话管理 |
| `Endpoint/` | 端点切换 |
| `Files/` | 文件上传/管理 |
| `Input/` | 输入框逻辑 |
| `Messages/` | 消息处理 |
| `Nav/` | 导航逻辑 |
| `SSE/` | 流式事件处理 |
| `useLocalize.ts` | 国际化 |
| `useNewConvo.ts` | 新建对话 |
| `useInfiniteScroll.ts` | 无限滚动 |
| `useLocalStorage.tsx` | 本地存储 |

### 2.7 共享前端库 (`packages/client/`)

```
packages/client/src/
├── Providers/              # 共享 Provider
├── components/             # 可复用组件
├── hooks/                  # 共享 Hooks
├── locales/                # 共享翻译
├── store.ts                # 共享状态
├── theme/                  # 主题系统
├── svgs/                   # SVG 图标
└── utils/                  # 工具函数
```

### 2.8 国际化

- 使用 `useLocalize()` Hook
- 翻译文件在 `client/src/locales/`
- 仅需更新英文 `translation.json`，其他语言自动处理
- 语义化 key 前缀：`com_ui_`、`com_assistants_` 等

---

## 3. 后端架构

### 3.1 Legacy 后端 (`api/`)

Express.js 服务器，JS 编写，逐步迁移到 TS。

```
api/
├── server/
│   ├── index.js            # 服务器入口
│   ├── routes/             # 路由定义 (37 个路由模块)
│   ├── controllers/        # 控制器
│   ├── services/           # 业务逻辑层
│   ├── middleware/          # 中间件
│   └── utils/              # 工具函数
├── models/                 # Mongoose 数据模型 (legacy)
├── strategies/             # Passport 认证策略
├── cache/                  # 缓存层 (Redis)
├── config/                 # 服务器配置
└── db/                     # 数据库连接
```

### 3.2 新后端 (`packages/api/`)

TypeScript 编写的新后端代码，被 `api/` 引用。

```
packages/api/src/
├── agents/                 # Agent 核心逻辑
│   ├── chain.ts            # Agent 调用链
│   ├── client.ts           # Agent 客户端
│   ├── config.ts           # Agent 配置
│   ├── context.ts          # 上下文管理
│   ├── discovery.ts        # Agent 发现
│   ├── edges.ts            # 工作流边
│   ├── handlers.ts         # 事件处理器
│   ├── initialize.ts       # 初始化
│   ├── memory.ts           # Agent 记忆
│   ├── run.ts              # 运行管理
│   ├── tools.ts            # 工具集成
│   ├── transactions.ts     # 交易记录
│   ├── usage.ts            # 用量统计
│   ├── openai/             # OpenAI 兼容接口
│   └── responses/          # Responses API
├── endpoints/              # LLM 端点实现
│   ├── anthropic/          # Anthropic Claude
│   ├── openai/             # OpenAI
│   ├── google/             # Google Gemini
│   ├── bedrock/            # AWS Bedrock
│   └── custom/             # 自定义端点
├── stream/                 # 流式响应处理
│   ├── interfaces/         # 流式接口定义
│   ├── implementations/    # 具体实现
│   └── GenerationJobManager.ts
├── files/                  # 文件处理
│   ├── rag.ts              # RAG (检索增强生成)
│   ├── ocr.ts              # OCR 文字识别
│   ├── parse.ts            # 文件解析
│   ├── text.ts             # 文本提取
│   ├── filter.ts           # 文件过滤
│   ├── encode/             # 编码处理
│   ├── documents/          # 文档处理
│   ├── agents/             # Agent 文件
│   └── mistral/            # Mistral OCR
├── mcp/                    # MCP (Model Context Protocol)
│   ├── MCPManager.ts       # MCP 管理器
│   ├── MCPConnectionFactory.ts # 连接工厂
│   ├── UserConnectionManager.ts # 用户连接管理
│   ├── ConnectionsRepository.ts # 连接仓库
│   ├── tools.ts            # MCP 工具
│   ├── oauth/              # MCP OAuth
│   ├── registry/           # 工具注册
│   └── cache.ts            # 缓存
├── tools/                  # 工具系统
│   ├── definitions.ts      # 工具定义
│   ├── classification.ts   # 工具分类
│   ├── format.ts           # 工具格式化
│   ├── registry/           # 工具注册表
│   └── toolkits/           # 工具包
├── auth/                   # 认证系统
│   ├── agent.ts            # Agent 认证
│   ├── domain.ts           # 域名验证
│   ├── exchange.ts         # Token 交换
│   ├── openid.ts           # OpenID Connect
│   ├── password.ts         # 密码管理
│   └── invite.ts           # 邀请机制
├── acl/                    # 访问控制
│   └── accessControlService.ts
├── admin/                  # 管理后台
│   ├── config.ts           # 配置管理
│   ├── grants.ts           # 权限授予
│   ├── groups.ts           # 用户组
│   ├── roles.ts            # 角色管理
│   ├── users.ts            # 用户管理
│   └── pagination.ts       # 分页
├── apiKeys/                # API Key 管理
├── app/                    # 应用配置
├── cache/                  # 缓存工具
├── cdn/                    # CDN 集成
├── cluster/                # 集群支持
├── crypto/                 # 加密工具 (JWT)
├── db/                     # 数据库工具
├── flow/                   # 工作流引擎
├── memory/                 # 记忆系统
├── middleware/             # 中间件
├── oauth/                  # OAuth 集成
├── prompts/                # 提示词服务
├── storage/                # 存储抽象
└── web/                    # 网页搜索
```

### 3.3 数据模型 (`packages/data-schemas/`)

MongoDB Schema 定义，共 **30+ 个模型**：

| 模型 | 用途 |
|------|------|
| `user.ts` | 用户账户 |
| `convo.ts` | 对话 |
| `message.ts` | 消息 |
| `agent.ts` | Agent 定义 |
| `agentApiKey.ts` | Agent API Key |
| `agentCategory.ts` | Agent 分类 |
| `assistant.ts` | OpenAI Assistant |
| `file.ts` | 文件元数据 |
| `action.ts` | Agent Actions |
| `key.ts` | API Keys |
| `preset.ts` | 用户预设 |
| `prompt.ts` / `promptGroup.ts` | 提示词/组 |
| `memory.ts` | 记忆条目 |
| `mcpServer.ts` | MCP 服务器配置 |
| `pluginAuth.ts` | 插件认证 |
| `session.ts` | 会话 |
| `token.ts` | Token |
| `balance.ts` | 余额 |
| `transaction.ts` | 交易记录 |
| `banner.ts` | 系统公告 |
| `role.ts` / `accessRole.ts` | 角色权限 |
| `aclEntry.ts` | ACL 条目 |
| `group.ts` | 用户组 |
| `systemGrant.ts` | 系统授权 |
| `sharedLink.ts` | 共享链接 |
| `conversationTag.ts` | 对话标签 |
| `toolCall.ts` | 工具调用记录 |

### 3.4 共享数据层 (`packages/data-provider/`)

前后端共享的 API 定义：

```
data-provider/src/
├── api-endpoints.ts        # 所有 API 端点路径
├── data-service.ts         # HTTP 请求封装
├── types.ts                # 核心类型定义
├── types/                  # 分类类型
│   ├── agents.ts           # Agent 类型
│   ├── assistants.ts       # Assistant 类型
│   ├── files.ts            # 文件类型
│   ├── graph.ts            # 图结构类型
│   ├── mcpServers.ts       # MCP 类型
│   ├── runs.ts             # 运行类型
│   └── web.ts              # 网页类型
├── schemas.ts              # Zod 验证 Schema
├── keys.ts                 # React Query Keys
├── react-query/            # React Query 封装
├── config.ts               # 配置解析
├── permissions.ts          # 权限类型
├── roles.ts                # 角色定义
├── models.ts               # 模型定义
├── azure.ts / bedrock.ts   # 云服务商配置
├── createPayload.ts        # 请求体构建
├── file-config.ts          # 文件配置
├── mcp.ts                  # MCP 相关
├── artifacts.ts            # Artifacts 相关
└── migrations/             # 数据迁移
```

---

## 4. API 路由总览

### 4.1 认证模块

| 路由 | 方法 | 功能 |
|------|------|------|
| `/api/auth/login` | POST | 登录 |
| `/api/auth/register` | POST | 注册 |
| `/api/auth/refresh` | POST | 刷新 Token |
| `/api/auth/logout` | POST | 登出 |
| `/api/auth/forgot-password` | POST | 忘记密码 |
| `/api/auth/reset-password` | POST | 重置密码 |
| `/api/auth/2fa` | POST | 两步验证 |

### 4.2 认证策略 (Passport.js)

| 策略 | 文件 |
|------|------|
| 本地认证 | `localStrategy.js` |
| JWT | `jwtStrategy.js` |
| LDAP | `ldapStrategy.js` |
| Google OAuth | `googleStrategy.js` |
| GitHub OAuth | `githubStrategy.js` |
| Discord OAuth | `discordStrategy.js` |
| Facebook OAuth | `facebookStrategy.js` |
| Apple Sign-In | `appleStrategy.js` |
| OpenID Connect | `openidStrategy.js` |
| OpenID JWT | `openIdJwtStrategy.js` |
| SAML | `samlStrategy.js` |

### 4.3 核心 API 路由

| 路由模块 | 端点前缀 | 功能 |
|----------|----------|------|
| `convos` | `/api/convos` | 对话 CRUD、分页、搜索 |
| `messages` | `/api/messages` | 消息 CRUD |
| `endpoints` | `/api/endpoints` | LLM 端点配置 |
| `models` | `/api/models` | 可用模型列表 |
| `agents` | `/api/agents` | Agent CRUD、市场 |
| `assistants` | `/api/assistants` | OpenAI Assistants |
| `files` | `/api/files` | 文件上传/下载/图片 |
| `search` | `/api/search` | 对话搜索 (含 MeiliSearch) |
| `prompts` | `/api/prompts` | 提示词管理 |
| `presets` | `/api/presets` | 用户预设 |
| `share` | `/api/share` | 共享对话 |
| `tags` | `/api/tags` | 对话标签 |
| `bookmarks` | `/api/bookmarks` | 收藏 |
| `memories` | `/api/memories` | 记忆系统 |
| `mcp` | `/api/mcp` | MCP 服务器管理 |
| `keys` | `/api/keys` | API Key 管理 |
| `apiKeys` | `/api/api-keys` | 用户 API Keys |
| `balance` | `/api/balance` | 余额查询 |
| `config` | `/api/config` | 前端配置 |
| `user` | `/api/user` | 用户信息 |
| `roles` | `/api/roles` | 角色管理 |
| `oauth` | `/api/oauth` | OAuth 认证 |
| `actions` | `/api/actions` | Agent Actions |
| `categories` | `/api/categories` | Agent 分类 |
| `banner` | `/api/banner` | 系统公告 |

### 4.4 管理后台 API

| 路由模块 | 功能 |
|----------|------|
| `admin/auth` | 管理员认证 |
| `admin/users` | 用户管理 (CRUD、封禁) |
| `admin/config` | 系统配置 |
| `admin/roles` | 角色管理 |
| `admin/groups` | 用户组管理 |
| `admin/grants` | 权限授予 |

### 4.5 文件/语音 API

| 端点 | 功能 |
|------|------|
| `/api/files/images` | 图片上传/处理 |
| `/api/files/avatar` | 头像上传 |
| `/api/files/speech/tts` | 文字转语音 |
| `/api/files/speech/stt` | 语音转文字 |

---

## 5. 核心功能模块详解

### 5.1 多端点 LLM 支持

支持的 LLM 提供商：

| 端点类型 | 实现位置 |
|----------|----------|
| OpenAI (GPT-4o, o1, etc.) | `packages/api/src/endpoints/openai/` |
| Anthropic (Claude) | `packages/api/src/endpoints/anthropic/` |
| Google (Gemini) | `packages/api/src/endpoints/google/` |
| AWS Bedrock | `packages/api/src/endpoints/bedrock/` |
| Azure OpenAI | `azure.ts` 配置 |
| 自定义端点 | `packages/api/src/endpoints/custom/` |

每个端点有独立的配置、模型列表、参数映射。

### 5.2 Agent 系统

**核心组件：**
- `packages/api/src/agents/` — Agent 运行时引擎
- `client/src/components/SidePanel/Agents/` — Agent 配置 UI
- `client/src/components/Agents/` — Agent 市场 UI

**功能点：**
- Agent 创建/编辑/删除/复制
- Agent 市场 (分类、搜索、虚拟化列表)
- Agent 版本管理
- Agent Actions (自定义 API 集成)
- Agent 工具配置 (MCP、文件搜索、代码解释器)
- Agent 记忆系统
- Agent 上下文管理
- Agent 用量统计和交易记录
- Agent API Key 管理
- Agent 认证 (OAuth)

**工作流：**

```
Agent 定义 → 初始化 → 加载工具 → 构建上下文 → 链式调用 → 流式响应 → 记录用量
```

### 5.3 MCP (Model Context Protocol)

**架构：**

```
MCPManager (管理器)
├── MCPConnectionFactory (连接工厂)
├── UserConnectionManager (用户连接管理)
├── ConnectionsRepository (连接仓库)
└── OAuth (认证流程)
```

**功能：**
- MCP 服务器配置和管理
- 动态工具发现和注册
- 用户自定义变量 (CustomUserVars)
- OAuth 认证流
- 连接缓存和重连
- 工具分类和格式化

### 5.4 流式响应系统

```
packages/api/src/stream/
├── interfaces/             # 流式接口抽象
├── implementations/        # 各端点流式实现
└── GenerationJobManager.ts # 生成任务管理
```

前端通过 SSE (Server-Sent Events) 接收流式数据。

### 5.5 文件系统

**存储策略：** 支持 Local / S3 / Firebase，可按文件类型分别配置

**处理流程：**

```
上传 → 验证 → 存储 → (可选) OCR/RAG/文本提取 → 元数据入库
```

**功能：**
- 图片上传和处理
- 文档上传和解析
- RAG (检索增强生成)
- OCR 文字识别 (含 Mistral OCR)
- 文件搜索 (嵌入式 + MeiliSearch)
- 头像管理
- 文件关联到 Agent/对话

### 5.6 Artifacts 系统

实时代码/文档预览：
- 代码编辑器 (Monaco)
- Mermaid 图表渲染
- 版本历史管理
- 下载功能
- Tab 式多文件展示

### 5.7 提示词系统

- 提示词创建/编辑/删除
- 提示词组管理
- 变量替换 (`{{variable}}`)
- 命令面板 (`/` 触发)
- 共享/公开提示词

### 5.8 记忆系统

- 用户记忆存储
- Agent 级别记忆
- 上下文注入
- 记忆 CRUD API

### 5.9 共享系统

- 对话共享链接生成
- 公开/私有共享
- 共享对话只读查看
- Artifacts 共享

### 5.10 权限与访问控制

**RBAC + ACL 混合模型：**
- 角色系统 (`role.ts`, `accessRole.ts`)
- ACL 条目 (`aclEntry.ts`)
- 用户组 (`group.ts`)
- 系统授权 (`systemGrant.ts`)
- 访问控制服务 (`accessControlService.ts`)

---

## 6. 中间件栈

| 中间件 | 功能 |
|--------|------|
| `requireJwtAuth.js` | JWT 认证 |
| `optionalJwtAuth.js` | 可选 JWT |
| `requireLocalAuth.js` | 本地认证 |
| `requireLdapAuth.js` | LDAP 认证 |
| `checkBan.js` | 封禁检查 |
| `limiters/` | 速率限制 |
| `moderateText.js` | 内容审核 |
| `validate/` | 请求验证 |
| `setHeaders.js` | 响应头设置 |
| `noIndex.js` | SEO 禁止索引 |
| `logHeaders.js` | 请求日志 |
| `abortMiddleware.js` | 请求中止处理 |
| `accessResources/` | 资源访问控制 |
| `roles/` | 角色中间件 |
| `config/` | 配置中间件 |
| `assistants/` | Assistant 专用中间件 |

---

## 7. 缓存层

```
api/cache/
├── index.js                # 缓存入口
├── getLogStores.js         # 日志存储
├── logViolation.js         # 违规记录
├── banViolation.js         # 封禁违规
└── clearPendingReq.js      # 清除待处理请求
```

使用 Redis 进行：
- 会话缓存
- 速率限制计数
- 违规记录
- MCP 连接缓存

---

## 8. 测试架构

| 测试类型 | 框架 | 位置 |
|----------|------|------|
| 单元测试 | Jest | 各模块 `__tests__/`、`*.spec.ts` |
| E2E 测试 | Playwright | `e2e/specs/` |
| 前端测试 | Jest + React Testing Library | `client/src/**/__tests__/` |

---

## 9. 部署架构

### Docker

- `Dockerfile` — 标准构建
- `Dockerfile.multi` — 多阶段构建
- `docker-compose.yml` — 生产环境
- `deploy-compose.yml` — 部署专用
- `docker-compose.override.yml.example` — 自定义覆盖

### Helm Charts

`helm/` 目录提供 Kubernetes 部署配置。

### 配置

- `librechat.yaml` — 主配置文件 (端点、模型、界面)
- `.env` — 环境变量
- `rag.yml` — RAG 配置
- `redis-config/` — Redis 配置

---

## 10. 关键架构特点

1. **渐进式迁移** — JS → TypeScript，`api/` 逐步迁移到 `packages/api/`
2. **端点抽象** — 统一接口支持多 LLM 提供商，新增端点只需实现接口
3. **Agent 引擎** — 完整的 Agent 生命周期管理，支持工具链、记忆、版本
4. **MCP 协议** — 标准化的工具集成协议，支持动态发现和 OAuth
5. **流式优先** — 所有 LLM 交互均支持流式响应
6. **插件化存储** — 文件存储策略可插拔 (Local/S3/Firebase)
7. **细粒度权限** — RBAC + ACL 混合，支持用户组和系统级授权
8. **Monorepo 共享** — `data-provider` 确保前后端类型一致