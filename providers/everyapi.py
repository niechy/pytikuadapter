import json
from typing import Optional
from urllib.parse import quote

import aiohttp
from pydantic import BaseModel, Field, ValidationError
from .manager import Providersbase
from model import QuestionContent, Provider, A


class EveryAPI(Providersbase):
    """
    everyAPI题库适配器
    """
    # 类属性定义
    name = "everyAPI题库"
    home = "https://www.everyapi.com/"
    url = "https://www.everyapi.com/api/v1/q/{question}"
    FREE = True
    PAY = True

    class Configs(BaseModel):
        """everyAPI适配器的配置参数"""
        token: str = Field(..., title="授权token", description="API授权token")

    async def _search(self, query: QuestionContent, provider: Provider) -> A:
        """
        查询everyAPI题库

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
            # 2. 构造请求URL（问题内容作为路径参数）
            # URL编码问题内容
            encoded_question = quote(query.content)
            request_url = self.url.format(question=encoded_question)

            # 3. 构造请求参数
            params = {
                "simple": "false",  # 不使用简单模式，获取结构化数据
                "token": config.token,
            }

            # 4. 设置Authorization头（也可以通过header传递token）
            headers = {
                "Authorization": f"Bearer {config.token}"
            }

            # 5. 发送HTTP GET请求
            async with self.session.get(
                request_url,
                params=params,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
                # 6. 处理HTTP错误
                if response.status == 400:
                    # 400错误通常是参数错误
                    try:
                        error_data = await response.json(content_type=None)
                        return A(
                            provider=self.name,
                            type=query.type,
                            success=False,
                            error_type="api_error",
                            error_message=error_data.get("msg", "请求参数错误")
                        )
                    except:
                        return A(
                            provider=self.name,
                            type=query.type,
                            success=False,
                            error_type="api_error",
                            error_message="请求参数错误"
                        )

                if response.status != 200:
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message=f"HTTP {response.status}: {response.reason}"
                    )

                # 7. 解析响应
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

                # 8. 检查API返回的code
                code = data.get("code")
                if code != 0:
                    # code不为0表示失败
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message=data.get("msg", "未找到答案")
                    )

                # 9. 提取答案数据
                result_data = data.get("data")
                if not result_data:
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message="API返回数据为空"
                    )

                # 10. 提取correct数组
                correct_answers = result_data.get("correct")
                if not correct_answers:
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message="未找到答案"
                    )

                # 11. 获取题目类型
                answer_type = result_data.get("type")

                # 12. 根据题目类型解析答案
                return self._parse_everyapi_answer(correct_answers, answer_type, query.type)

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

    def _parse_everyapi_answer(self, correct_answers: list, api_type: int, query_type: int) -> A:
        """
        解析everyAPI返回的答案

        Args:
            correct_answers: API返回的correct数组，格式如：
                [{"option": "A", "content": "答案A"}, {"option": "B", "content": "答案B"}]
            api_type: API返回的题目类型
            query_type: 查询时的题目类型

        Returns:
            A: 答案对象
        """
        try:
            # everyAPI的type字段：
            # 0: 单选题
            # 1: 多选题
            # 2: 填空题/问答题
            # 3: 判断题

            # 根据API返回的类型判断
            if api_type == 0 or api_type == 1:  # 单选或多选
                # 提取选项字母
                options = []
                for answer in correct_answers:
                    option = answer.get("option")
                    if option:
                        options.append(option.upper())

                if not options:
                    # 如果没有option字段，尝试从content提取
                    for answer in correct_answers:
                        content = answer.get("content", "")
                        extracted = self._extract_choice(content)
                        options.extend(extracted)

                # 确定实际类型（单选还是多选）
                actual_type = 1 if len(options) > 1 else 0

                return A(
                    provider=self.name,
                    type=actual_type,
                    choice=options,
                    success=True
                )

            elif api_type == 2:  # 填空题/问答题
                # 提取所有答案内容
                text_answers = []
                for answer in correct_answers:
                    content = answer.get("content")
                    if content:
                        text_answers.append(content)

                if not text_answers:
                    return A(
                        provider=self.name,
                        type=query_type,
                        success=False,
                        error_type="parse_error",
                        error_message="未找到文本答案"
                    )

                # 使用查询时的类型（可能是2填空或4问答）
                return A(
                    provider=self.name,
                    type=query_type if query_type in [2, 4] else 2,
                    text=text_answers,
                    success=True
                )

            elif api_type == 3:  # 判断题
                # 判断题通常只有一个答案
                if correct_answers:
                    first_answer = correct_answers[0]
                    content = first_answer.get("content", "")
                    option = first_answer.get("option", "")

                    # 尝试从content或option解析判断结果
                    judgement = self._parse_judgement(content or option)

                    return A(
                        provider=self.name,
                        type=3,
                        judgement=judgement,
                        success=True
                    )

            # 未知类型或无法解析，返回文本
            text_answers = []
            for answer in correct_answers:
                content = answer.get("content")
                if content:
                    text_answers.append(content)

            return A(
                provider=self.name,
                type=query_type,
                text=text_answers if text_answers else ["未知答案"],
                success=True
            )

        except Exception as e:
            return A(
                provider=self.name,
                type=query_type,
                success=False,
                error_type="parse_error",
                error_message=f"答案解析失败: {str(e)}"
            )

    def _extract_choice(self, answer: str) -> list[str]:
        """
        从答案字符串中提取选项字母

        Examples:
            "A" -> ["A"]
            "AB" -> ["A", "B"]
            "A、B" -> ["A", "B"]
            "答案：A" -> ["A"]
        """
        import re

        # 移除常见前缀
        answer = re.sub(r'^(答案[：:]\s*|正确答案[：:]\s*)', '', answer.strip())

        # 提取所有大写字母（A-Z）
        choices = re.findall(r'[A-Z]', answer.upper())

        if choices:
            # 去重并保持顺序
            seen = set()
            result = []
            for c in choices:
                if c not in seen:
                    seen.add(c)
                    result.append(c)
            return result

        # 如果没有找到字母，返回空列表
        return []

    def _parse_judgement(self, answer: str) -> bool:
        """
        解析判断题答案

        Examples:
            "正确" -> True
            "错误" -> False
            "对" -> True
            "错" -> False
            "√" -> True
            "×" -> False
            "T" -> True
            "F" -> False
        """
        answer_lower = answer.strip().lower()

        # 正确的表示
        true_values = ['正确', '对', '是', '√', '✓', 't', 'true', 'yes', '1']
        # 错误的表示
        false_values = ['错误', '错', '否', '×', '✗', 'f', 'false', 'no', '0']

        if any(val in answer_lower for val in true_values):
            return True
        elif any(val in answer_lower for val in false_values):
            return False

        # 默认返回True（如果无法判断）
        return True