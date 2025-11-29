# 适配器开发指南

本文档介绍如何为 pytikuadapter 开发新的题库适配器。

## 目录结构

```
providers/
├── __init__.py      # 自动导入所有适配器
├── manager.py       # 适配器基类和注册机制
├── matcher.py       # 答案匹配工具
├── like.py          # Like知识库适配器
├── enncy.py         # 言溪题库适配器
├── everyapi.py      # everyAPI题库适配器
├── wanneng.py       # 万能题库适配器
└── local.py         # 本地题库适配器
```

## 快速开始

创建一个新适配器只需要继承 `Providersbase` 并实现 `_search` 方法：

```python
from typing import Optional, List
from pydantic import BaseModel, Field, ValidationError
from .manager import Providersbase
from .matcher import build_choice_answer_from_keys
from model import QuestionContent, Provider, A
import aiohttp
import json


class MyProvider(Providersbase):
    """我的题库适配器"""
    name = "我的题库"  # 必须唯一，用于请求时指定
    home = "https://example.com"  # 题库主页
    url = "https://api.example.com/query"  # API地址
    FREE = True   # 是否有免费额度
    PAY = True    # 是否支持付费
    CACHEABLE = True  # 是否缓存答案（默认True）

    class Configs(BaseModel):
        """配置参数，会从请求的 provider.config 中读取"""
        api_key: str = Field(..., title="API密钥")
        timeout: Optional[int] = Field(10, title="超时时间")

    async def _search(self, query: QuestionContent, provider: Provider) -> A:
        """查询题库，返回答案对象 A"""
        # 实现查询逻辑...
        pass
```

适配器会自动注册，无需手动添加到任何列表。

## 标准代码结构

推荐使用以下结构，保持代码一致性：

```python
class MyProvider(Providersbase):
    name = "我的题库"
    # ... 其他类属性

    class Configs(BaseModel):
        # 配置参数定义
        pass

    def _fail(self, query_type: int, error_type: str, message: str) -> A:
        """构造失败响应"""
        return A(
            provider=self.name,
            type=query_type,
            success=False,
            error_type=error_type,
            error_message=message
        )

    def _success(self, answer_type: int, *,
                 choice: List[str] = None,
                 text: List[str] = None,
                 judgement: bool = None) -> A:
        """构造成功响应"""
        return A(
            provider=self.name,
            type=answer_type,
            choice=choice,
            text=text,
            judgement=judgement,
            success=True
        )

    async def _search(self, query: QuestionContent, provider: Provider) -> A:
        """主入口"""
        # 1. 验证配置
        try:
            config = self.Configs(**provider.config)
        except ValidationError as e:
            return self._fail(query.type, "config_error", f"配置参数错误: {e}")

        # 2. 发送请求
        try:
            async with self.session.get(...) as response:
                if response.status != 200:
                    return self._fail(query.type, "api_error", f"HTTP {response.status}")

                data = await response.json(content_type=None)
                return self._parse_response(data, query)

        except aiohttp.ClientError as e:
            return self._fail(query.type, "network_error", f"网络请求失败: {e}")
        except Exception as e:
            return self._fail(query.type, "unknown", f"未知错误: {e}")

    def _parse_response(self, data: dict, query: QuestionContent) -> A:
        """解析API响应"""
        # 检查返回状态、提取答案...
        pass
```

## 题目类型

| type | 类型 | 返回字段 | 示例 |
|------|------|----------|------|
| 0 | 单选题 | `choice` | `["A"]` |
| 1 | 多选题 | `choice` | `["A", "B", "C"]` |
| 2 | 填空题 | `text` | `["答案1", "答案2"]` |
| 3 | 判断题 | `judgement` | `True` / `False` |
| 4 | 问答题 | `text` | `["答案内容"]` |

## 错误类型

| error_type | 说明 |
|------------|------|
| `config_error` | 配置参数错误 |
| `api_error` | API返回错误 |
| `network_error` | 网络请求失败 |
| `match_error` | 答案匹配失败 |
| `unknown` | 未知错误 |

## 答案匹配器

`matcher.py` 提供了选择题答案匹配功能，解决适配器返回的答案与选项不完全一致的问题。

### build_choice_answer

直接用答案文本匹配选项：

```python
from .matcher import build_choice_answer

# 适配器返回 "帝国主义战争和无产阶级革命"
# 选项是 "帝国主义战争与无产阶级革命成为时代主题"
# 会自动匹配到对应选项

return build_choice_answer(
    provider_name=self.name,
    answer_text="帝国主义战争和无产阶级革命",
    options=query.options,  # ["选项A内容", "选项B内容", ...]
    question_type=query.type  # 0=单选, 1=多选
)
```

### build_choice_answer_from_keys

优先使用选项键（A/B/C/D），无效时回退到文本匹配：

```python
from .matcher import build_choice_answer_from_keys

# 如果 answer_keys 是有效的选项键，直接使用
# 如果无效（如返回了文本），则用 answer_text 进行模糊匹配

return build_choice_answer_from_keys(
    provider_name=self.name,
    answer_keys=["A", "B"],  # 可能是 ["A"] 或 ["答案文本"]
    answer_text="备用的答案文本",  # 当 keys 无效时使用
    options=query.options,
    question_type=query.type
)
```

### 匹配算法

1. **文本归一化**：去除标点、统一"与/和"等连接词
2. **包含关系检测**：答案是选项的子串
3. **字符重叠度**：Jaccard 相似度
4. **最长公共子串**：连续匹配的字符比例

## 完整示例

以下是一个完整的适配器实现示例：

```python
import json
from typing import Optional, List

import aiohttp
from pydantic import BaseModel, Field, ValidationError
from .manager import Providersbase
from .matcher import build_choice_answer_from_keys
from model import QuestionContent, Provider, A


class ExampleProvider(Providersbase):
    """示例题库适配器"""
    name = "示例题库"
    home = "https://example.com"
    url = "https://api.example.com/search"
    FREE = True
    PAY = False

    class Configs(BaseModel):
        token: str = Field(..., title="API Token")

    def _fail(self, query_type: int, error_type: str, message: str) -> A:
        return A(provider=self.name, type=query_type, success=False,
                 error_type=error_type, error_message=message)

    def _success(self, answer_type: int, *, choice: List[str] = None,
                 text: List[str] = None, judgement: bool = None) -> A:
        return A(provider=self.name, type=answer_type, choice=choice,
                 text=text, judgement=judgement, success=True)

    async def _search(self, query: QuestionContent, provider: Provider) -> A:
        try:
            config = self.Configs(**provider.config)
        except ValidationError as e:
            return self._fail(query.type, "config_error", f"配置错误: {e}")

        try:
            params = {"q": query.content, "token": config.token}

            async with self.session.get(self.url, params=params,
                                        timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return self._fail(query.type, "api_error", f"HTTP {resp.status}")

                try:
                    data = await resp.json(content_type=None)
                except json.JSONDecodeError as e:
                    return self._fail(query.type, "api_error", f"JSON解析失败: {e}")

                return self._parse_response(data, query)

        except aiohttp.ClientError as e:
            return self._fail(query.type, "network_error", f"网络错误: {e}")
        except Exception as e:
            return self._fail(query.type, "unknown", f"未知错误: {e}")

    def _parse_response(self, data: dict, query: QuestionContent) -> A:
        if data.get("code") != 0:
            return self._fail(query.type, "api_error", data.get("msg", "查询失败"))

        answer = data.get("answer")
        if not answer:
            return self._fail(query.type, "api_error", "未找到答案")

        # 选择题
        if query.type in [0, 1]:
            return build_choice_answer_from_keys(
                provider_name=self.name,
                answer_keys=answer.get("options", []),
                answer_text=answer.get("text"),
                options=query.options,
                question_type=query.type
            )

        # 填空/问答
        if query.type in [2, 4]:
            texts = answer.get("texts", [])
            return self._success(query.type, text=texts)

        # 判断题
        if query.type == 3:
            return self._success(query.type, judgement=answer.get("correct", True))

        return self._fail(query.type, "api_error", "未知题目类型")
```

## 禁用缓存

某些适配器（如本地题库）不需要缓存，设置 `CACHEABLE = False`：

```python
class LocalProvider(Providersbase):
    name = "本地题库"
    CACHEABLE = False  # 禁用缓存
```

## 注意事项

1. **类名**：使用 PascalCase，如 `MyProvider`
2. **name 属性**：必须唯一，这是请求时指定适配器的标识
3. **HTTP 客户端**：使用 `self.session`（共享的 aiohttp ClientSession）
4. **超时设置**：建议设置合理的超时时间（10-30秒）
5. **错误处理**：所有异常都应该被捕获并返回带有错误信息的 `A` 对象
6. **JSON 解析**：使用 `content_type=None` 避免 Content-Type 检查问题
