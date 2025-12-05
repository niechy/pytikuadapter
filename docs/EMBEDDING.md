# BGE-M3 向量匹配

基于 BGE-M3 模型实现题目的语义模糊匹配，替代原有的精确字符串匹配。

## 依赖

```toml
# pyproject.toml
FlagEmbedding = "^1.2.10"
pgvector = "^0.2.5"
torch = "^2.3.0"
```

## 数据库配置

### 启用 pgvector 扩展

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

### 添加 embedding 列（已有表）

```sql
ALTER TABLE questions ADD COLUMN IF NOT EXISTS embedding vector(1024);

CREATE INDEX IF NOT EXISTS idx_questions_embedding
ON questions USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
```

## 架构设计

### 文件结构

```
services/
├── __init__.py
└── embedding.py      # EmbeddingService 单例

database/
├── models.py         # Question.embedding 列
└── cache_service.py  # 向量匹配逻辑
```

### 核心组件

#### EmbeddingService (`services/embedding.py`)

单例模式的 embedding 服务，支持异步调用。

```python
from services import get_embedding_service

service = get_embedding_service()

# 查询编码（检索时使用）
query_vector = await service.embed_query("题目内容")

# 文档编码（存储时使用）
passage_vector = await service.embed_passage("题目内容")
```

**关键点：**
- BGE-M3 使用非对称编码，查询和文档需使用不同方法
- 模型首次加载约需 10-30 秒（约 3GB）
- 自动检测 CUDA，无 GPU 时回退到 CPU

#### CacheService 匹配流程

```
find_question()
    │
    ├─► _find_by_normalized()  # 1. 精确匹配（快速）
    │       └─► 命中 → 返回
    │
    └─► _find_by_embedding()   # 2. 向量匹配（回退）
            ├─► 生成查询向量
            ├─► 余弦相似度搜索 (TOP_K=5)
            ├─► 相似度 ≥ 0.82 且选项一致 → 返回
            └─► 无匹配 → 返回 None
```

## 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `EMBEDDING_SIMILARITY_THRESHOLD` | 0.82 | 相似度阈值，越高越严格 |
| `EMBEDDING_TOP_K` | 5 | 向量搜索返回的候选数量 |
| `lists` (索引参数) | 100 | IVFFlat 索引的聚类数，数据量大时可增加 |

## 匹配规则

1. **类型匹配**：`question_type` 必须完全相等
2. **相似度阈值**：余弦相似度 ≥ 0.82
3. **选项一致性**：
   - 两边都有选项 → 必须相等
   - 两边都无选项 → 通过
   - 一边有一边无 → 不匹配

## 新题目入库

新题目保存时自动生成 embedding：

```python
# save_answer / batch_save_answers 内部逻辑
if question is None:
    embedding = await self._generate_embedding(content, options)
    question = Question(
        content=content,
        embedding=embedding,  # 使用 embed_passage 生成
        ...
    )
```

## 旧数据兼容

- 旧题目 `embedding` 为 NULL
- 向量搜索自动跳过无 embedding 的记录
- 旧数据仍可通过精确匹配命中

## 性能优化建议

### 索引调优

```sql
-- 数据量 > 10万时，增加 lists 参数
CREATE INDEX idx_questions_embedding
ON questions USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 200);

-- 查询时设置 probes（精度/速度权衡）
SET ivfflat.probes = 10;
```

### 模型预热

首次请求会触发模型加载，可在启动时预热：

```python
# main.py 启动时
from services import get_embedding_service

@app.on_event("startup")
async def warmup():
    service = get_embedding_service()
    await service.embed_query("预热")
```

## 阈值调优

建议记录匹配日志，根据实际效果调整阈值：

```python
# cache_service.py 中已有日志
log.debug(f"向量匹配成功: similarity={similarity:.4f}, question_id={question.id}")
```

- 误匹配多 → 提高阈值（如 0.85）
- 漏匹配多 → 降低阈值（如 0.78）
