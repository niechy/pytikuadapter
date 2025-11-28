# 错误处理重构总结

## 重构内容

### 1. 统一返回格式

**之前的混乱情况**：
```python
# 成功
return A(provider="Like", choice=["A"])

# 失败（三种不同方式）
return None                              # Local
return {"error": "错误信息"}              # 万能题库
raise Exception("错误")                   # 其他异常
```

**现在的统一格式**：
```python
# 成功
return A(provider="Like", choice=["A"], success=True)

# 失败
return A(provider="Like", success=False,
         error_type="api_error", error_message="错误信息")
```

### 2. 新增字段

在 `model.py` 的 `A` 类中添加了三个字段：

```python
class A(BaseModel):
    # ... 原有字段 ...

    # 新增字段
    success: bool = Field(True, description="是否成功获取答案")
    error_type: Optional[str] = Field(None, description="错误类型")
    error_message: Optional[str] = Field(None, description="错误详细信息")
```

### 3. 错误类型分类

| 错误类型 | 说明 | 使用场景 |
|---------|------|---------|
| `cache_miss` | 缓存未命中 | Local provider 查询时缓存不存在 |
| `api_error` | API 返回错误 | API 返回错误码、错误消息 |
| `network_error` | 网络请求失败 | 连接超时、DNS 解析失败 |
| `config_error` | 配置参数错误 | 缺少必填参数、参数格式错误 |
| `unknown` | 未知错误 | 其他未预期的异常 |

### 4. 响应结构变化

**之前**：
```json
{
  "provider_answer": [...],
  "successful_providers": 1
}
```

**现在**：
```json
{
  "provider_answers": [
    {
      "provider": "Like知识库",
      "success": true,
      "choice": ["A"]
    },
    {
      "provider": "万能题库",
      "success": false,
      "error_type": "api_error",
      "error_message": "旧版本已停用"
    }
  ],
  "successful_providers": 1,
  "failed_providers": 1,
  "total_providers": 2
}
```

## 修改的文件

### 1. `model.py`
- ✅ 在 `A` 类中添加 `success`、`error_type`、`error_message` 字段
- ✅ 在 `Res` 类中添加 `failed_providers`、`total_providers` 字段
- ✅ 将 `provider_answer` 重命名为 `provider_answers`

### 2. `core.py`
- ✅ 更新 `collect_true_answer()` 函数，只聚合成功的答案
- ✅ 更新 `construct_res()` 函数，统计成功/失败数量

### 3. `providers/wanneng.py`
- ✅ 完全重写，统一错误处理
- ✅ 所有错误都返回 `A` 对象，不再返回 `dict` 或抛出异常
- ✅ 添加详细的错误分类和消息

### 4. `providers/like.py`
- ✅ 完全重写，统一错误处理
- ✅ 添加超时设置（30秒）
- ✅ 详细的错误处理和日志

### 5. `providers/local.py`
- ✅ 更新返回格式
- ✅ 缓存未命中返回 `error_type="cache_miss"`
- ✅ 不再返回 `None`

### 6. `main.py`
- ✅ 移除对 `None` 和 `dict` 返回值的处理
- ✅ 统一处理所有 provider 返回的 `A` 对象
- ✅ 添加详细的日志输出（✅ 成功、❌ 失败）
- ✅ 只有成功的答案才写入缓存

## 日志输出示例

### 之前
```
Adapter ans: {'error': '请前往更新,旧版本已停用'}
最终结果: 成功provider数=1, 总答案数=2
```

### 现在
```
缓存命中: Like知识库
❌ 失败 [万能题库]: api_error - 请前往更新,旧版本已停用

📊 查询统计:
   总provider数: 2
   ✅ 成功: 1
   ❌ 失败: 1
   最终答案: A
```

## 优势

1. **统一性** ✅
   - 所有 provider 返回格式完全一致
   - 不再有 `None`、`dict`、异常等混乱情况

2. **可追踪性** ✅
   - 可以看到每个 provider 的成功/失败状态
   - 失败时提供详细的错误类型和消息

3. **健壮性** ✅
   - 单个 provider 失败不影响其他 provider
   - 所有异常都被捕获并转换为错误对象

4. **易调试** ✅
   - 清晰的日志输出（✅/❌ 图标）
   - 响应中包含所有 provider 的详细状态

5. **智能聚合** ✅
   - 只聚合成功的答案
   - 失败的 provider 不参与答案投票

## 向后兼容性

⚠️ **破坏性变更**：

1. 响应字段名变化：
   - `provider_answer` → `provider_answers`
   - 新增 `failed_providers`、`total_providers`

2. `A` 对象结构变化：
   - 新增 `success`、`error_type`、`error_message` 字段

如果有客户端依赖旧的响应格式，需要更新客户端代码。

## 测试建议

### 1. 测试成功场景
```json
{
  "providers": [
    {"name": "Like知识库", "config": {"key": "valid_key"}}
  ]
}
```

预期：`success=true`，有答案

### 2. 测试失败场景
```json
{
  "providers": [
    {"name": "万能题库", "config": {"token": "invalid_token"}}
  ]
}
```

预期：`success=false`，`error_type="api_error"`

### 3. 测试缓存未命中
```json
{
  "providers": [
    {"name": "Local", "config": {"enabled": true}}
  ]
}
```

预期：`success=false`，`error_type="cache_miss"`

### 4. 测试部分成功
```json
{
  "providers": [
    {"name": "Like知识库", "config": {"key": "valid_key"}},
    {"name": "万能题库", "config": {"token": "invalid_token"}}
  ]
}
```

预期：
- `successful_providers=1`
- `failed_providers=1`
- 最终答案来自 Like知识库

## 后续优化建议

1. **错误重试机制**
   - 对于 `network_error`，可以自动重试
   - 配置重试次数和间隔

2. **错误统计**
   - 记录每个 provider 的失败率
   - 自动降低频繁失败的 provider 的优先级

3. **错误通知**
   - 当所有 provider 都失败时，发送告警
   - 记录错误日志到文件或监控系统

4. **降级策略**
   - 当主 provider 失败时，自动切换到备用 provider
   - 配置 provider 的优先级和降级规则
