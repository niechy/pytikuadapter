import json
from typing import Optional

import aiohttp
from pydantic import BaseModel, Field, ValidationError
from .manager import Providersbase
from model import QuestionContent, Provider, A


class enncy(Providersbase):
    """
    言溪题库适配器
    """
    # 类属性定义
    name = "言溪题库"
    home = "https://tk.enncy.cn/"
    url = "https://tk.enncy.cn/query"
    FREE = True
    PAY = True

    # 题目类型映射：内部类型 -> 言溪API类型
    TYPE_MAP = {
        0: "single",      # 单选
        1: "multiple",    # 多选
        2: "completion",  # 填空
        3: "judgement",   # 判断
        4: "completion",  # 问答（使用completion类型）
    }

    class Configs(BaseModel):
        """言溪适配器的配置参数"""
        token: str = Field(..., title="用户凭证", description="用户token，从题库个人中心获取")

    async def _search(self, query: QuestionContent, provider: Provider) -> A:
        """
        查询言溪题库

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
            # 2. 构造请求参数
            params = {
                "token": config.token,
                "title": query.content,
            }

            # 添加可选参数
            if query.options:
                # 选项用换行符分隔
                params["options"] = "\n".join(query.options)

            if query.type is not None:
                # 转换题目类型
                params["type"] = self.TYPE_MAP.get(query.type, "unknown")

            # 3. 发送HTTP GET请求
            async with self.session.get(
                self.url,
                params=params,
                timeout=aiohttp.ClientTimeout(total=10)
            ) as response:
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
                code = data.get("code")
                if code != 1:
                    # code为0表示未找到答案
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message=data.get("message", "未找到答案")
                    )

                # 7. 提取答案
                result_data = data.get("data")
                if not result_data:
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message="API返回数据为空"
                    )

                answer = result_data.get("answer")
                if not answer:
                    return A(
                        provider=self.name,
                        type=query.type,
                        success=False,
                        error_type="api_error",
                        error_message="未找到答案"
                    )

                # 8. 检查是否为AI生成答案（可选字段）
                is_ai = result_data.get("ai", False)

                # 9. 根据题目类型解析答案
                return self._parse_answer(answer, query.type, is_ai)

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

    def _parse_answer(self, answer: str, question_type: int, is_ai: bool = False) -> A:
        """
        解析答案字符串，根据题目类型返回相应格式

        Args:
            answer: 答案字符串
            question_type: 题目类型 (0-4)
            is_ai: 是否为AI生成答案

        Returns:
            A: 答案对象
        """
        try:
            if question_type == 0:  # 单选题
                # 尝试提取选项字母（A、B、C、D等）
                choice = self._extract_choice(answer)
                return A(
                    provider=self.name,
                    type=question_type,
                    choice=choice,
                    success=True
                )

            elif question_type == 1:  # 多选题
                # 尝试提取多个选项字母
                choice = self._extract_choice(answer)
                return A(
                    provider=self.name,
                    type=question_type,
                    choice=choice,
                    success=True
                )

            elif question_type == 2 or question_type == 4:  # 填空题或问答题
                # 填空题可能有多个答案，用特定分隔符分隔
                # 常见分隔符：#、|、;、；等
                text_answers = self._split_text_answer(answer)
                return A(
                    provider=self.name,
                    type=question_type,
                    text=text_answers,
                    success=True
                )

            elif question_type == 3:  # 判断题
                # 解析判断题答案（正确/错误、对/错、√/×、T/F等）
                judgement = self._parse_judgement(answer)
                return A(
                    provider=self.name,
                    type=question_type,
                    judgement=judgement,
                    success=True
                )

            else:
                # 未知类型，返回文本
                return A(
                    provider=self.name,
                    type=question_type,
                    text=[answer],
                    success=True
                )

        except Exception as e:
            return A(
                provider=self.name,
                type=question_type,
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

        # 如果没有找到字母，返回原始答案
        return [answer.strip()]

    def _split_text_answer(self, answer: str) -> list[str]:
        """
        分割文本答案（填空题/问答题）

        Examples:
            "答案1#答案2" -> ["答案1", "答案2"]
            "答案1|答案2" -> ["答案1", "答案2"]
            "单个答案" -> ["单个答案"]
        """
        # 常见分隔符
        separators = ['#@#', '#', '|', ';', '；', '、']

        for sep in separators:
            if sep in answer:
                parts = [part.strip() for part in answer.split(sep) if part.strip()]
                if parts:
                    return parts

        # 没有分隔符，返回整个答案
        return [answer.strip()]

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