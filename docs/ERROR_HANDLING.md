# 错误处理机制说明

## 统一的返回格式

所有 provider 现在都返回统一的 `A` 对象，包含以下字段：

### 成功时的返回
```python
A(
    provider="Like知识库",
    type=0,
    choice=["A"],
    success=True,  # 成功标志
    error_type=None,
    error_message=None
)
```

### 失败时的返回
```python
A(
    provider="万能题库",
    type=0,
    success=False,  # 失败标志
    error_type="api_error",  # 错误类型
    error_message="请前往更新,旧版本已停用"  # 错误详情
)
```

## 错误类型 (error_type)

| 错误类型 | 说明 | 示例 |
|---------|------|------|
| `cache_miss` | 缓存未命中 | Local provider 查询时缓存不存在 |
| `api_error` | API 返回错误 | 万能题库返回"旧版本已停用" |
| `network_error` | 网络请求失败 | 连接超时、DNS 解析失败 |
| `config_error` | 配置参数错误 | 缺少 API key、token 格式错误 |
| `unknown` | 未知错误 | 其他未预期的异常 |

## 响应结构

### 新的响应格式
```json
{
  "query": {...},
  "unified_answer": {...},
  "provider_answers": [  // 包含所有 provider 的结果
    {
      "provider": "Like知识库",
      "type": 0,
      "choice": ["A"],
      "success": true,
      "error_type": null,
      "error_message": null
    },
    {
      "provider": "万能题库",
      "type": 0,
      "success": false,
      "error_type": "api_error",
      "error_message": "请前往更新,旧版本已停用"
    }
  ],
  "successful_providers": 1,  // 成功的数量
  "failed_providers": 1,      // 失败的数量
  "total_providers": 2        // 总数量
}
```

## Provider 实现规范

### 1. 所有 provider 必须返回 A 对象
```python
async def _search(self, query: QuestionContent, provider: Provider) -> A:
    # 不要返回 None 或 dict
    # 必须返回 A 对象
    pass
```

### 2. 捕获所有异常
```python
try:
    # 业务逻辑
    return A(provider=self.name, type=query.type, choice=["A"], success=True)
except ValidationError as e:
    return A(provider=self.name, type=query.type, success=False,
             error_type="config_error", error_message=str(e))
except aiohttp.ClientError as e:
    return A(provider=self.name, type=query.type, success=False,
             error_type="network_error", error_message=str(e))
except Exception as e:
    return A(provider=self.name, type=query.type, success=False,
             error_type="unknown", error_message=str(e))
```

### 3. 不要抛出异常
```python
# ❌ 错误做法
async def _search(self, query, provider):
    if error:
        raise Exception("错误")  # 不要这样做

# ✅ 正确做法
async def _search(self, query, provider):
    if error:
        return A(provider=self.name, success=False,
                error_type="api_error", error_message="错误")
```

## 答案聚合逻辑

`core.py` 中的 `collect_true_answer` 函数会：
1. 过滤出 `success=True` 的答案
2. 使用 Counter 统计最常见的答案
3. 返回聚合后的最佳答案

**失败的 provider 不会参与答案聚合**。

## 迁移指南

### 旧代码
```python
# 旧的返回方式（混乱）
return A(provider=self.name, choice=["A"])  # 成功
return None  # 失败
return {"error": "错误信息"}  # 失败
raise Exception("错误")  # 失败
```

### 新代码
```python
# 新的统一返回方式
return A(provider=self.name, choice=["A"], success=True)  # 成功
return A(provider=self.name, success=False,
         error_type="api_error", error_message="错误信息")  # 失败
```

## 优势

1. **统一性**：所有 provider 返回格式一致
2. **可追踪**：可以看到每个 provider 的成功/失败状态
3. **详细信息**：失败时提供错误类型和详细信息
4. **不中断**：单个 provider 失败不影响其他 provider
5. **易调试**：响应中包含所有 provider 的状态

## 示例场景

### 场景1：部分成功
```
请求: [Like知识库, 万能题库, Local]
结果:
- Like知识库: 成功，返回答案 A
- 万能题库: 失败，旧版本已停用
- Local: 成功，返回缓存答案 A

最终答案: A (聚合 Like知识库 和 Local 的答案)
successful_providers: 2
failed_providers: 1
```

### 场景2：全部失败
```
请求: [万能题库]
结果:
- 万能题库: 失败，旧版本已停用

最终答案: 空
successful_providers: 0
failed_providers: 1
```

### 场景3：全部成功
```
请求: [Like知识库, Local]
结果:
- Like知识库: 成功，返回答案 A
- Local: 成功，返回缓存答案 A

最终答案: A
successful_providers: 2
failed_providers: 0
```
