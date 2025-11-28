# 数据库缓存系统使用文档

## 概述

本项目使用PostgreSQL数据库实现题目答案的缓存系统，支持模糊匹配和多provider管理。

## 核心特性

### 1. 模糊匹配
- **题目内容归一化**：自动去除标点符号、空格，转小写，解决"你好。"和"你好"被视为不同题目的问题
- **选项归一化**：选项排序后存储，解决选项顺序变化的问题（如"A你好,B你坏"和"A你坏,B你好"）

### 2. Provider为核心的设计
- 每个provider的答案独立存储
- 支持同一题目在不同provider下有不同答案
- 配置感知：同一provider使用不同配置（如不同的model）会被视为不同的缓存

### 3. 性能优化
- **批量查询**：一次数据库查询获取多个provider的缓存，避免N+1问题
- **异步写入**：缓存写入在后台异步执行，不阻塞API响应
- **连接池**：使用SQLAlchemy连接池管理数据库连接

### 4. Local Provider
- 特殊的适配器，从本地缓存查询答案
- 不进行网络请求，只返回已缓存的数据
- 可以在请求中添加Local provider来优先使用缓存

## 数据库配置

### 1. 环境变量配置

复制 `.env.example` 为 `.env` 并配置：

```bash
# PostgreSQL数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password_here
DB_NAME=tikuadapter

# 连接池配置
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# SQL日志（开发环境可以开启）
DB_ECHO=false
```

### 2. 安装依赖

```bash
poetry install
```

新增的依赖：
- `sqlalchemy ^2.0.0` - ORM框架
- `asyncpg ^0.29.0` - PostgreSQL异步驱动

### 3. 创建数据库

```bash
# 登录PostgreSQL
psql -U postgres

# 创建数据库
CREATE DATABASE tikuadapter;

# 退出
\q
```

### 4. 初始化表结构

应用启动时会自动创建表结构，无需手动执行SQL。

如果需要手动管理，可以使用：

```python
from database import init_database, close_database
import asyncio

async def main():
    await init_database()  # 创建所有表
    await close_database()

asyncio.run(main())
```

## 数据库表结构

### 1. questions 表（题目表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| content | Text | 题目原始内容 |
| normalized_content | Text | 归一化内容（用于模糊匹配） |
| type | Integer | 题目类型（0-4） |
| options | JSON | 选项列表 |
| normalized_options | JSON | 归一化选项（排序后） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

**索引**：
- `idx_normalized_content_type`: (normalized_content, type)
- `idx_normalized_options`: (normalized_options)

### 2. answers 表（答案表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| type | Integer | 答案类型 |
| choice | JSON | 选择题答案 ["A", "B"] |
| judgement | Boolean | 判断题答案 |
| text | JSON | 填空/问答题答案 |
| created_at | DateTime | 创建时间 |

**索引**：
- `idx_answer_type_choice`: (type, choice)
- `idx_answer_type_judgement`: (type, judgement)

### 3. question_provider_answers 表（关联表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| question_id | Integer | 题目ID（外键） |
| provider_name | String | Provider名称 |
| answer_id | Integer | 答案ID（外键） |
| config_hash | String | 配置哈希值 |
| confidence | Integer | 置信度（0-100） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

**索引**：
- `idx_unique_question_provider`: (question_id, provider_name, config_hash) UNIQUE
- `idx_question_providers`: (question_id, provider_name)
- `idx_provider_name`: (provider_name)

## 使用方式

### 1. 自动缓存（推荐）

正常使用API，系统会自动：
1. 查询前检查缓存
2. 有缓存直接返回
3. 无缓存调用provider查询
4. 异步写入新答案到缓存

```json
POST /v1/adapter-service/search
{
  "query": {
    "content": "题目内容",
    "options": ["选项A", "选项B"],
    "type": 0
  },
  "providers": [
    {
      "name": "Like知识库",
      "config": {"key": "your-key"}
    }
  ]
}
```

### 2. 使用Local Provider

在请求中添加Local provider来优先使用缓存：

```json
{
  "query": {
    "content": "题目内容",
    "options": ["选项A", "选项B"],
    "type": 0
  },
  "providers": [
    {
      "name": "Local",
      "config": {"enabled": true}
    },
    {
      "name": "Like知识库",
      "config": {"key": "your-key"}
    }
  ]
}
```

**工作流程**：
1. Local provider从缓存查询
2. 如果缓存命中，返回缓存答案
3. 如果缓存未命中，调用Like知识库查询
4. 新答案异步写入缓存

### 3. 缓存行为说明

#### 场景1：第一次查询（无缓存）
```
请求: [Like知识库, 万能题库]
缓存: 无
结果: 调用两个provider，返回两个答案，异步写入缓存
```

#### 场景2：第二次查询（有缓存）
```
请求: [Like知识库, 万能题库]
缓存: Like知识库有缓存，万能题库有缓存
结果: 直接返回两个缓存答案，不调用provider
```

#### 场景3：部分缓存
```
请求: [Like知识库, 万能题库, 题库海]
缓存: Like知识库有缓存，万能题库有缓存
结果: 返回两个缓存答案 + 调用题库海查询，异步写入题库海答案
```

#### 场景4：请求provider变化
```
第一次请求: [Like知识库]
第二次请求: [万能题库]
缓存: Like知识库有缓存
结果: 第二次请求不会返回Like知识库的缓存（因为没有请求它）
      只调用万能题库查询，异步写入万能题库答案
```

## 性能优化细节

### 1. 批量查询优化

**问题**：如果请求10个provider，逐个查询缓存需要10次数据库查询。

**解决**：使用一次JOIN查询获取所有provider的缓存：

```python
# 一次查询获取所有provider的缓存
cached_answers = await query_cache_batch(
    session=session,
    query=query,
    providers=providers  # 10个provider
)
# 返回: {"Like知识库": A(...), "万能题库": A(...), ...}
```

### 2. 异步写入优化

**问题**：同步写入缓存会增加API响应时间。

**解决**：使用 `asyncio.create_task` 在后台异步写入：

```python
# 不等待写入完成，立即返回响应
asyncio.create_task(
    save_cache_async(query, provider_answers)
)
return result  # 立即返回
```

### 3. 连接池优化

使用SQLAlchemy连接池管理数据库连接：
- `pool_size=10`: 保持10个活跃连接
- `max_overflow=20`: 最多额外创建20个连接
- `pool_pre_ping=True`: 连接前检查有效性
- `pool_recycle=3600`: 1小时回收连接

## 模糊匹配示例

### 题目内容匹配

```python
# 这些题目会被识别为同一题目：
"你好，世界！"
"你好世界"
"你好  世界"
"你好，世界。"

# 归一化后都是: "你好世界"
```

### 选项匹配

```python
# 这些选项会被识别为相同：
["A. 你好", "B. 你坏"]
["A你好", "B你坏"]

# 归一化后都是: ["a你好", "b你坏"]

# 这些选项也会被识别为相同（排序后）：
["A. 你好", "B. 你坏"]
["B. 你坏", "A. 你好"]

# 归一化并排序后都是: ["a你好", "b你坏"]
```

## 配置感知缓存

同一provider使用不同配置会被视为不同的缓存：

```json
// 第一次请求
{
  "name": "Like知识库",
  "config": {"key": "xxx", "llm_model": "gpt-4"}
}

// 第二次请求（不同model）
{
  "name": "Like知识库",
  "config": {"key": "xxx", "llm_model": "deepseek-v3"}
}
```

这两次请求会产生两个独立的缓存记录，因为配置不同。

## 数据库维护

### 查看缓存统计

```sql
-- 查看总题目数
SELECT COUNT(*) FROM questions;

-- 查看各provider的缓存数量
SELECT provider_name, COUNT(*)
FROM question_provider_answers
GROUP BY provider_name;

-- 查看最近缓存的题目
SELECT q.content, qpa.provider_name, qpa.created_at
FROM questions q
JOIN question_provider_answers qpa ON q.id = qpa.question_id
ORDER BY qpa.created_at DESC
LIMIT 10;
```

### 清理缓存

```sql
-- 清理特定provider的缓存
DELETE FROM question_provider_answers
WHERE provider_name = 'Like知识库';

-- 清理所有缓存（保留题目）
DELETE FROM question_provider_answers;

-- 清理所有数据
TRUNCATE questions, answers, question_provider_answers CASCADE;
```

### 备份和恢复

```bash
# 备份数据库
pg_dump -U postgres tikuadapter > backup.sql

# 恢复数据库
psql -U postgres tikuadapter < backup.sql
```

## 故障排查

### 1. 数据库连接失败

检查：
- PostgreSQL是否运行：`pg_isready`
- 环境变量配置是否正确
- 数据库是否存在：`psql -U postgres -l`

### 2. 缓存未命中

可能原因：
- 题目内容或选项有细微差异（检查归一化逻辑）
- Provider配置不同（检查config_hash）
- 缓存尚未写入（异步写入有延迟）

### 3. 性能问题

检查：
- 数据库索引是否创建：`\d questions` 查看索引
- 连接池配置是否合理
- 是否有慢查询：启用 `DB_ECHO=true` 查看SQL

## 最佳实践

1. **生产环境**：
   - 使用独立的PostgreSQL服务器
   - 配置合理的连接池大小
   - 定期备份数据库
   - 关闭SQL日志（`DB_ECHO=false`）

2. **开发环境**：
   - 可以使用本地PostgreSQL
   - 开启SQL日志方便调试
   - 定期清理测试数据

3. **缓存策略**：
   - 优先使用Local provider减少网络请求
   - 对于高频题目，缓存命中率会很高
   - 定期清理过期或错误的缓存

4. **监控**：
   - 监控缓存命中率
   - 监控数据库连接数
   - 监控查询响应时间
