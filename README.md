# pytikuadapter

[tikuadapter](https://github.com/DokiDoki1103/tikuAdapter) 的 Python 版，从自己的角度加了些东西。

目前用ai写出框架，细节自己修改。

## 快速开始

### 环境要求

- Python 3.12+
- PostgreSQL（用于答案缓存）

### 安装

```bash
# 克隆项目
git clone https://github.com/niechy/pytikuadapter.git
cd pytikuadapter

# 安装依赖
poetry install
```

### 配置数据库

1. 创建 PostgreSQL 数据库：

```bash
psql -U postgres -c "CREATE DATABASE tikuadapter;"
```

2. 配置环境变量（项目中有example）：
```
# 复制此文件为 .env 并填入实际配置

# PostgreSQL数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_NAME=tikuadapter

# 数据库连接池配置
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# 是否启用SQL日志（开发环境可以设置为true）
DB_ECHO=false

# 日志配置
# 日志级别：DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO
# 日志保留天数
LOG_BACKUP_DAYS=30
# 是否需要鉴权
AUTH_ENABLED=false
```

### 运行

```bash
python main.py
```

## 支持的题库（排名不分先后）

| 题库 | 名称 | 免费 | 付费 |
|------|------|------|------|
| Like知识库 | `Like知识库` | - | ✓ |
| 言溪题库 | `言溪题库` | ✓ | ✓ |
| 万能题库 | `万能题库` | ✓ | ✓ |
| everyAPI | `everyAPI题库` | ✓ | ✓ |

## API 使用

### 请求

```
POST http://localhost:8060/v1/adapter-service/search
```

**Headers:**
```
Content-Type: application/json
Authorization: Bearer your_token
```

**Body:**
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
      "config": {
        "key": "your_api_key",
        "model": "deepseek-v3.2"
      }
    },
    {
      "name": "万能题库",
      "config": {
        "token": "your_token"
      }
    },
    {
      "name": "言溪题库",
      "config": {
        "token": "your_token"
      }
    }
  ]
}
```

### 题目类型

| type | 类型 |
|------|------|
| 0 | 单选题 |
| 1 | 多选题 |
| 2 | 填空题 |
| 3 | 判断题 |
| 4 | 问答题 |

### 响应

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

## 项目结构

```
pytikuadapter/
├── main.py              # FastAPI 入口
├── model.py             # 数据模型
├── core.py              # 答案聚合逻辑
├── providers/           # 题库适配器
│   ├── manager.py       # 适配器基类和注册
│   ├── matcher.py       # 答案匹配工具
│   ├── like.py          # Like知识库
│   ├── enncy.py         # 言溪题库
│   ├── wanneng.py       # 万能题库
│   └── everyapi.py      # everyAPI
├── database/            # 数据库缓存
│   ├── models.py        # 表结构
│   ├── cache_service.py # 缓存服务
│   └── utils.py         # 工具函数
└── docs/                # 文档
    ├── DATABASE.md      # 数据库设计
    └── provider-development.md  # 适配器开发指南
```

## Todo

- [x] 多题库并发查询
- [x] 统一返回格式
- [x] 异常处理
- [x] PostgreSQL 缓存
- [x] 答案模糊匹配
- [x] 鉴权
- [ ] WebUI
- [ ] 更多题库适配器(持续添加中)

## 开发

添加新的题库适配器，参考 [适配器开发指南](docs/provider-development.md)。

## 致谢

作者是一名非计算机系大学生，代码纯菜，边写边学的，欢迎吐槽、issue，PR。

- [tikuadapter](https://github.com/DokiDoki1103/tikuAdapter) 原版项目
- 玛丽
- DeepSeek、Grok、Claude 等大模型

## License

待定
