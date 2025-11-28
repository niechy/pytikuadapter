import json
from typing import Optional

import aiohttp
from pydantic import BaseModel, Field, ValidationError
from .manager import Providersbase
from model import QuestionContent, Provider, A


class Wanneng(Providersbase):
    """
    万能题库适配器
    """
    # 类属性定义
    name = "万能题库"
    home = "https://lyck6.cn/pay"
    url = "http://lyck6.cn/scriptService/api/autoAnswer/{token}"
    headers = {"Content-Type": "application/json"}
    FREE = True
    PAY = True

    class Configs(BaseModel):
        """万能适配器的配置参数"""
        token: str = Field(..., title="token密钥", description="用于认证的token密钥")
        location: Optional[str] = Field(None, title="题目来源", description="题目来源URL（可选）")

    async def _search(self, query: QuestionContent, provider: Provider) -> A:
        """
        查询万能题库

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
            # 2. 构造请求
            body = {
                "question": query.content,
                "options": query.options,
                "type": query.type,
                "location": config.location,
            }
            url = self.url.format(token=config.token)

            # 3. 发送HTTP请求
            async with self.session.post(url, json=body, headers=self.headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                # 4. 处理HTTP错误
                if response.status != 200:
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message=f"HTTP {response.status}: {response.reason}"
                    )

                # 5. 解析响应
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

                # 6. 检查API返回的code
                if data.get("code") != 0:
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message=data.get("message", "API返回错误")
                    )

                # 7. 提取答案
                result = data.get("result")
                if not result:
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message="API返回数据为空"
                    )

                answers = result.get("answers")
                if not answers:
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message="未找到答案"
                    )

                # 8. 根据题目类型返回答案
                is_success = result.get("success", False)

                # 如果success为False，取第一个相似题目的答案
                if not is_success and isinstance(answers, list) and len(answers) > 0:
                    answers = answers[0]

                if query.type == 0 or query.type == 1:  # 单选/多选
                    # 万能题库返回的是下标，需要转换为字母
                    if is_success:
                        # success=true时，answers是下标数组，如 [0, 1]
                        if not isinstance(answers, list):
                            answers = [answers]
                        # 将下标转换为字母：0->A, 1->B, 2->C...
                        choice_letters = [chr(65 + idx) for idx in answers if isinstance(idx, int)]
                        return A(
                            provider=self.name,
                            type=query.type,
                            choice=choice_letters,
                            success=True
                        )
                    else:
                        # success=false时，返回的可能是文本答案或其他格式
                        # 这里简单处理，如果是列表就用列表，否则包装成列表
                        return A(
                            provider=self.name,
                            type=query.type,
                            choice=answers if isinstance(answers, list) else [answers],
                            success=True
                        )

                elif query.type == 2 or query.type == 4:  # 填空/问答
                    return A(
                        provider=self.name,
                        type=query.type,
                        text=answers if isinstance(answers, list) else [answers],
                        success=True
                    )

                elif query.type == 3:  # 判断
                    # 判断题：answers可能是布尔值或0/1
                    if isinstance(answers, bool):
                        judgement_value = answers
                    elif isinstance(answers, int):
                        judgement_value = bool(answers)
                    elif isinstance(answers, list) and len(answers) > 0:
                        # 如果是列表，取第一个元素
                        first = answers[0]
                        judgement_value = bool(first) if isinstance(first, (int, bool)) else True
                    else:
                        judgement_value = True

                    return A(
                        provider=self.name,
                        type=query.type,
                        judgement=judgement_value,
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
