# 数据库缓存系统文档

## 概述

使用 PostgreSQL 数据库实现题目答案缓存，支持模糊匹配和多 provider 管理。

## 核心特性

### 1. 模糊匹配
- **题目内容归一化**：去除标点符号、空格，转小写
- **选项归一化**：排序后存储，解决选项顺序变化问题

### 2. Provider 为核心的设计
- 每个 provider 的答案独立存储
- 同一题目 + 同一 provider = 一份缓存
- 不区分配置（token/key 等认证信息不影响答案）

### 3. 性能优化
- **批量查询**：一次查询获取多个 provider 的缓存
- **异步写入**：后台写入，不阻塞响应
- **连接池**：SQLAlchemy 连接池管理

## 环境变量

```bash
# 数据库连接
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=tikuadapter

# 连接池
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# SQL日志（调试用）
DB_ECHO=false
```

## 表结构

### questions（题目表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| content | Text | 题目原始内容 |
| normalized_content | Text | 归一化内容 |
| type | Integer | 题目类型（0-4） |
| options | JSONB | 选项列表 |
| normalized_options | JSONB | 归一化选项（排序后） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

**索引**：
- `idx_normalized_content_type`: (normalized_content, type)
- `idx_normalized_options`: GIN 索引

### answers（答案表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| type | Integer | 答案类型 |
| choice | JSONB | 选择题答案 `["A", "B"]` |
| judgement | Boolean | 判断题答案 |
| text | JSONB | 填空/问答答案 |
| created_at | DateTime | 创建时间 |

### question_provider_answers（关联表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | Integer | 主键 |
| question_id | Integer | 题目ID（外键） |
| provider_name | String | Provider 名称 |
| answer_id | Integer | 答案ID（外键） |
| confidence | Integer | 置信度（0-100） |
| created_at | DateTime | 创建时间 |
| updated_at | DateTime | 更新时间 |

**索引**：
- `idx_unique_question_provider`: (question_id, provider_name) **唯一**
- `idx_provider_name`: (provider_name)

## 缓存逻辑

```
题目 (Question)
└── provider_name → 答案 (Answer)
```

**同一题目 + 同一 provider = 一份缓存答案**

## 使用方式

### 自动缓存

正常调用 API，系统自动处理缓存：

```json
POST /v1/adapter-service/search
{
  "query": {
    "content": "题目内容",
    "options": ["选项A", "选项B"],
    "type": 0
  },
  "providers": [
    {"name": "Like知识库", "config": {"key": "xxx"}}
  ]
}
```

流程：
1. 查询前检查缓存
2. 有缓存 → 直接返回
3. 无缓存 → 调用 API → 异步写入缓存

### 禁用缓存

适配器设置 `CACHEABLE = False`：

```python
class LocalProvider(Providersbase):
    name = "本地题库"
    CACHEABLE = False
```

## 缓存场景

| 场景 | 请求 | 缓存状态 | 结果 |
|------|------|----------|------|
| 首次查询 | [Like, 万能] | 无 | 调用两个 API，写入缓存 |
| 二次查询 | [Like, 万能] | 都有 | 直接返回缓存 |
| 部分缓存 | [Like, 万能, 题库海] | Like/万能有 | 返回2个缓存 + 调用题库海 |

## 模糊匹配示例

### 题目匹配

```python
# 这些会被识别为同一题目：
"你好，世界！"
"你好世界"
"你好  世界"
# 归一化后: "你好世界"
```

### 选项匹配

```python
# 这些会被识别为相同：
["A. 你好", "B. 你坏"]
["B. 你坏", "A. 你好"]  # 顺序不同
# 归一化并排序后: ["a你好", "b你坏"]
```

## 数据库维护

### 查看统计

```sql
-- 题目总数
SELECT COUNT(*) FROM questions;

-- 各 provider 缓存数量
SELECT provider_name, COUNT(*)
FROM question_provider_answers
GROUP BY provider_name;
```

### 清理缓存

```sql
-- 清理特定 provider
DELETE FROM question_provider_answers
WHERE provider_name = 'Like知识库';

-- 清理所有
TRUNCATE questions, answers, question_provider_answers CASCADE;
```

### 备份恢复

```bash
# 备份
pg_dump -U postgres tikuadapter > backup.sql

# 恢复
psql -U postgres tikuadapter < backup.sql
```

## 初始化

应用启动时自动创建表，也可手动：

```python
from database import init_database
import asyncio

asyncio.run(init_database())
```

## 迁移（从旧版本升级）

如果从包含 `config_hash` 的旧版本升级：

```sql
-- 删除旧索引
DROP INDEX IF EXISTS idx_unique_question_provider;

-- 创建新索引
CREATE UNIQUE INDEX idx_unique_question_provider
ON question_provider_answers (question_id, provider_name);

-- 删除 config_hash 列
ALTER TABLE question_provider_answers DROP COLUMN IF EXISTS config_hash;
```

或直接重建：

```sql
DROP TABLE IF EXISTS question_provider_answers CASCADE;
DROP TABLE IF EXISTS answers CASCADE;
DROP TABLE IF EXISTS questions CASCADE;
```

重启应用后表会自动创建。
