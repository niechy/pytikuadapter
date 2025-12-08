<div align="center">
  <img src="favicon.ico" alt="图标" />
</div>

# pytikuadapter

[tikuadapter](https://github.com/DokiDoki1103/tikuAdapter) 的 Python 版，从自己的角度加了些东西。

## 特性

- 多题库并发查询，答案聚合
- 用户系统 + API Token 管理
- Provider 配置持久化，支持请求时动态覆盖
- 答案缓存（PostgreSQL）
- 速率限制，防止滥用

## 快速开始

**推荐使用我们提供的在线服务，无需部署，一键使用（还在备案，耐心等待几天）**

### 环境要求

- Python 3.12+
- PostgreSQL

### 安装

```bash
git clone https://github.com/niechy/pytikuadapter.git
cd pytikuadapter
poetry install
```

### 配置

复制 `.env.example` 为 `.env` 并修改：

```bash
# PostgreSQL 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_NAME=tikuadapter

# 数据库连接池配置
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_ECHO=false  # 是否启用SQL日志

# 日志配置
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_BACKUP_DAYS=30

# 认证配置
ACCESS_TOKEN_EXPIRE_MINUTES=3600  # JWT过期时间（分钟），密钥自动生成到 data/.jwt_secret

# 邮箱验证配置（可选）
EMAIL_VERIFICATION_REQUIRED=false
EMAIL_FROM_ADDRESS=  # 阿里云邮件服务
EMAIL_FROM_ALIAS=
ALIBABA_CLOUD_ECS_METADATA=  # ECS RAM Role名称

# CORS配置
CORS_ORIGINS=*

# 速率限制
RATE_LIMIT_AUTH=5/minute    # 注册/登录
RATE_LIMIT_EMAIL=3/minute   # 发送邮件
# RATE_LIMIT_SEARCH=        # 搜索接口，留空不限制
```

### 运行

```bash
python main.py
# 或
uvicorn main:app --host 0.0.0.0 --port 8060
```

建议与前端一起使用，获得最好体验（前端做的差不多了，等我最后打磨打磨.jpg,还没提交仓库）

## 支持的题库

| 题库 | 名称 | 免费 | 付费 |
|------|------|:----:|:----:|
| Like知识库 | `Like知识库` | - | ✓ |
| 言溪题库 | `言溪题库` | ✓ | ✓ |
| 万能题库 | `万能题库` | ✓ | ✓ |
| everyAPI | `everyAPI题库` | ✓ | ✓ |
| 本地缓存 | `tikuadapter缓存` | ✓ | - |

## API 文档

### 搜索接口

```
POST /v1/adapter-service/search
Authorization: Bearer <api_token>
```

### 最简请求（使用 Token 中保存的配置，见下文）

```json
{
  "query": {
    "content": "流体力学是什么",
    "type": 4
  }
}
```

#### 完整请求（指定 Provider 和配置）

```json
{
  "query": {
    "content": "毛泽东思想形成的时代背景是( )",
    "options": [
      "帝国主义战争与无产阶级革命成为时代主题",
      "和平与发展成为时代主题",
      "世界多极化成为时代主题",
      "经济全球化成为时代主题"
    ],
    "type": 0
  },
  "providers": [
    {
      "name": "Like知识库",
      "config": { "model": "deepseek-v3.2" }
    },
    {
      "name": "万能题库"
    }
  ]
}
```

#### 配置融合规则

请求中的 `config` 会与 Token 中保存的配置融合，请求优先：

| Token 配置 | 请求配置 | 最终配置 |
|-----------|---------|---------|
| `{"key": "xxx"}` | `{"model": "gpt-4"}` | `{"key": "xxx", "model": "gpt-4"}` |
| `{"model": "gpt-3"}` | `{"model": "gpt-4"}` | `{"model": "gpt-4"}` |

#### 响应示例

```json
{
  "query": {
    "content": "毛泽东思想形成的时代背景是( )",
    "options": ["..."],
    "type": 0
  },
  "unified_answer": {
    "answerKey": ["A"],
    "answerKeyText": "A",
    "answerIndex": [0],
    "answerText": "帝国主义战争与无产阶级革命成为时代主题",
    "bestAnswer": ["帝国主义战争与无产阶级革命成为时代主题"]
  },
  "provider_answers": [
    {
      "provider": "Like知识库",
      "type": 0,
      "choice": ["A"],
      "success": true
    }
  ],
  "successful_providers": 3,
  "failed_providers": 0,
  "total_providers": 3
}
```

### 认证

#### 用户注册/登录

```bash
# 注册
POST /api/auth/register
{ "email": "user@example.com", "password": "123456" }

# 登录
POST /api/auth/login
{ "email": "user@example.com", "password": "123456" }
# 返回 JWT token
```

#### API Token 管理

```bash
# 创建 API Token（需要 JWT 认证）
POST /api/tokens
Authorization: Bearer <jwt_token>
{ "name": "my-token" }

# 获取 Token 列表
GET /api/tokens

# 删除 Token
DELETE /api/tokens/{token_id}
```

每个用户最多创建 10 个 API Token。

### Provider 配置

```bash
# 获取可用 Provider 列表
GET /api/providers/available

# 获取 Token 的 Provider 配置
GET /api/tokens/{token_id}/providers

# 批量更新 Provider 配置
PUT /api/tokens/{token_id}/providers
{
  "configs": [
    {
      "provider_name": "Like知识库",
      "api_key": "your_key",
      "config_json": { "model": "deepseek-v3" },
      "enabled": true
    }
  ]
}
```


#### 题目类型

| type | 类型 |
|------|------|
| 0 | 单选题 |
| 1 | 多选题 |
| 2 | 填空题 |
| 3 | 判断题 |
| 4 | 问答题 |

## 回家归途

[QQ群](https://qm.qq.com/q/gcZ5EKwhLq)

## 项目结构

```
pytikuadapter/
├── main.py                 # FastAPI 入口
├── model.py                # 数据模型
├── core.py                 # 答案聚合逻辑
├── providers/              # 题库适配器
│   ├── manager.py          # 适配器基类和注册
│   ├── like.py             # Like知识库
│   ├── enncy.py            # 言溪题库
│   ├── wanneng.py          # 万能题库
│   ├── everyapi.py         # everyAPI
│   └── local.py            # 本地缓存
├── database/               # 数据库
│   ├── models.py           # 表结构
│   ├── config.py           # 连接配置
│   └── cache_service.py    # 缓存服务
├── services/               # 业务服务
│   ├── auth_service.py     # 认证服务
│   ├── email_service.py    # 邮件服务
│   ├── rate_limit.py       # 速率限制
│   ├── provider_order.py   # Provider 排序
│   └── routers/            # API 路由
└── docs/                   # 文档
```

## Todo

- [x] 多题库并发查询
- [x] 统一返回格式
- [x] PostgreSQL 缓存
- [x] 用户系统 + API Token
- [x] Provider 配置持久化
- [x] 配置融合
- [x] 速率限制
- [x] WebUI
- [ ] 更多题库适配器

## 开发

添加新的题库适配器，参考 [适配器开发指南](docs/provider-development.md)。

## 致谢

路漫漫其修远兮，吾将上下而求索。

- [tikuadapter](https://github.com/DokiDoki1103/tikuAdapter) 原版项目
- DeepSeek、Claude 等大模型

## License

待定
