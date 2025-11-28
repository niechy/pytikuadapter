import json
from typing import Optional

import aiohttp
from pydantic import BaseModel, Field, ValidationError
from .manager import Providersbase
from model import QuestionContent, Provider, A


class Like(Providersbase):
    """
    Like知识库适配器
    """
    name = "Like知识库"
    home = "https://www.datam.site/"
    url = "https://app.datam.site/api/v1/query"
    headers = {"Content-Type": "application/json"}
    FREE = False
    PAY = True
    questionType = {"CHOICE": 0, "FILL_IN_BLANK": 2, "JUDGMENT": 3}
    TYPE_request = {0: "【单选题】：", 1: "【多选题】：", 2: "【填空题】：", 3: "【判断题】：", 4: "【问答题】："}

    class Configs(BaseModel):
        """Like适配器的配置参数"""
        key: str = Field(..., title="API密钥", description="用于认证的API密钥")
        llm_model: Optional[str] = Field(None, title="大语言模型", description="指定使用的大语言模型")
        search: Optional[bool] = Field(None, title="联网搜索", description="是否启用联网搜索")
        vision: Optional[bool] = Field(None, title="视觉理解", description="是否启用视觉理解")

    async def _search(self, query: QuestionContent, provider: Provider) -> A:
        """
        查询Like知识库

        Returns:
            A: 统一的答案对象，包含成功/失败信息
        """
        try:
            # 1. 验证配置
            config = self.Configs(**provider.config)
        except ValidationError as e:
            return A(
                provider=self.name,
                type=query.type,
                success=False,
                error_type="config_error",
                error_message=f"配置参数错误: {str(e)}"
            )

        try:
            # 2. 构造请求体
            body = {
                "query": self.TYPE_request[query.type] + query.content + str(query.options),
                "llm_model": config.llm_model,
                "search": config.search,
                "vision": config.vision,
            }

            # 3. 添加认证头
            auth_header = {"Authorization": f"Bearer {config.key}"}
            headers = {**self.headers, **auth_header}

            # 4. 发送HTTP请求
            async with self.session.post(self.url, headers=headers, json=body, timeout=aiohttp.ClientTimeout(total=30)) as response:
                # 5. 处理HTTP错误
                if response.status != 200:
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message=f"HTTP {response.status}: {response.reason}"
                    )

                # 6. 解析响应
                try:
                    data = await response.json(content_type=None)
                except json.JSONDecodeError as e:
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message=f"响应解析失败: {str(e)}"
                    )

                # 7. 检查API返回状态
                if data.get("message") != "查询成功":
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message=data.get("message", "API返回错误")
                    )

                # 8. 提取答案
                results = data.get("results")
                if not results:
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message="API返回数据为空"
                    )

                ans = results.get("output")
                if not ans:
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message="未找到答案"
                    )

                # 9. 解析题目类型
                question_type_str = ans.get("questionType")
                if not question_type_str:
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message="无法识别题目类型"
                    )

                answer_type = self.questionType.get(question_type_str)
                if answer_type is None:
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message=f"不支持的题目类型: {question_type_str}"
                    )

                # 10. 根据题目类型返回答案
                answer_data = ans.get("answer")
                if not answer_data:
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message="答案数据为空"
                    )

                if answer_type == 0:  # 选择题
                    selected_options = answer_data.get("selectedOptions")
                    if not selected_options:
                        return A(
                            provider=self.name,
                            type=query.type,
                            success=False,
                            error_type="api_error",
                            error_message="未找到选项答案"
                        )
                    # 判断是单选还是多选
                    actual_type = 1 if len(selected_options) > 1 else 0
                    return A(
                        provider=self.name,
                        type=actual_type,
                        choice=selected_options,
                        success=True
                    )
                elif answer_type == 2:  # 填空题
                    blanks = answer_data.get("blanks")
                    if not blanks:
                        return A(
                            provider=self.name,
                            type=query.type,
                            success=False,
                            error_type="api_error",
                            error_message="未找到填空答案"
                        )
                    # Like知识库的填空和问答归为一类，使用query的type
                    return A(
                        provider=self.name,
                        type=query.type,
                        text=blanks,
                        success=True
                    )
                elif answer_type == 3:  # 判断题
                    is_correct = answer_data.get("isCorrect")
                    if is_correct is None:
                        return A(
                            provider=self.name,
                            type=query.type,
                            success=False,
                            error_type="api_error",
                            error_message="未找到判断答案"
                        )
                    return A(
                        provider=self.name,
                        type=answer_type,
                        judgement=is_correct,
                        success=True
                    )

        except aiohttp.ClientError as e:
            # 网络错误
            return A(
                provider=self.name,
                type=query.type,
                success=False,
                error_type="network_error",
                error_message=f"网络请求失败: {str(e)}"
            )
        except Exception as e:
            # 未知错误
            return A(
                provider=self.name,
                type=query.type,
                success=False,
                error_type="unknown",
                error_message=f"未知错误: {str(e)}"
            )
