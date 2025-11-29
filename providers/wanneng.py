import json
from typing import Optional, List

import aiohttp
from pydantic import BaseModel, Field, ValidationError
from .manager import Providersbase
from .matcher import build_choice_answer
from model import QuestionContent, Provider, A


class Wanneng(Providersbase):
    """万能题库适配器"""
    name = "万能题库"
    home = "https://lyck6.cn/pay"
    url = "http://lyck6.cn/scriptService/api/autoAnswer/{token}"
    FREE = True
    PAY = True

    class Configs(BaseModel):
        """万能适配器的配置参数"""
        token: str = Field(..., title="token密钥")
        location: Optional[str] = Field(None, title="题目来源")

    def _fail(self, query_type: int, error_type: str, message: str) -> A:
        """构造失败响应"""
        return A(provider=self.name, type=query_type, success=False, error_type=error_type, error_message=message)

    def _success(self, answer_type: int, *, choice: List[str] = None, text: List[str] = None, judgement: bool = None) -> A:
        """构造成功响应"""
        return A(provider=self.name, type=answer_type, choice=choice, text=text, judgement=judgement, success=True)

    async def _search(self, query: QuestionContent, provider: Provider) -> A:
        """查询万能题库"""
        try:
            config = self.Configs(**provider.config)
        except ValidationError as e:
            return self._fail(query.type, "config_error", f"配置参数错误: {e}")

        try:
            # 构造请求
            body = {
                "question": query.content,
                "options": query.options,
                "type": query.type,
                "location": config.location,
            }
            url = self.url.format(token=config.token)
            headers = {"Content-Type": "application/json"}

            async with self.session.post(url, json=body, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status != 200:
                    return self._fail(query.type, "api_error", f"HTTP {response.status}: {response.reason}")

                try:
                    data = await response.json(content_type=None)
                except json.JSONDecodeError as e:
                    return self._fail(query.type, "api_error", f"响应解析失败: {e}")

                return self._parse_response(data, query)

        except aiohttp.ClientError as e:
            return self._fail(query.type, "network_error", f"网络请求失败: {e}")
        except Exception as e:
            return self._fail(query.type, "unknown", f"未知错误: {e}")

    def _parse_response(self, data: dict, query: QuestionContent) -> A:
        """解析API响应"""
        # 检查状态码
        code = data.get("code")
        if code == 404:
            return self._fail(query.type, "api_error", "积分不足")
        if code != 0:
            return self._fail(query.type, "api_error", data.get("message", "API返回错误"))

        result = data.get("result")
        if not result:
            return self._fail(query.type, "api_error", "API返回数据为空")

        answers = result.get("answers")
        if not answers:
            return self._fail(query.type, "api_error", "未找到答案")

        is_success = result.get("success", False)

        # success=false时，answers是二维数组，取第一个
        if not is_success and isinstance(answers, list) and answers:
            if isinstance(answers[0], list):
                answers = answers[0]

        return self._parse_answer(answers, is_success, query)

    def _parse_answer(self, answers, is_success: bool, query: QuestionContent) -> A:
        """解析答案"""
        if query.type == 0 or query.type == 1:  # 单选/多选
            if is_success:
                # success=true: answers是下标数组 [0, 1]
                if not isinstance(answers, list):
                    answers = [answers]
                choice_letters = [chr(65 + idx) for idx in answers if isinstance(idx, int)]
                actual_type = 1 if len(choice_letters) > 1 else 0
                return self._success(actual_type, choice=choice_letters)
            else:
                # success=false: answers是文本答案，需要匹配
                answer_text = answers[0] if isinstance(answers, list) else str(answers)
                return build_choice_answer(
                    provider_name=self.name,
                    answer_text=answer_text,
                    options=query.options,
                    question_type=query.type
                )

        elif query.type == 2 or query.type == 4:  # 填空/问答
            text_list = answers if isinstance(answers, list) else [answers]
            return self._success(query.type, text=[str(t) for t in text_list])

        elif query.type == 3:  # 判断题
            if isinstance(answers, bool):
                return self._success(query.type, judgement=answers)
            elif isinstance(answers, int):
                return self._success(query.type, judgement=bool(answers))
            elif isinstance(answers, list) and answers:
                first = answers[0]
                if isinstance(first, (int, bool)):
                    return self._success(query.type, judgement=bool(first))
                # 文本判断
                return self._success(query.type, judgement=self._parse_judgement(str(first)))
            return self._success(query.type, judgement=True)

        # 未知类型
        text_list = answers if isinstance(answers, list) else [answers]
        return self._success(query.type, text=[str(t) for t in text_list])

    def _parse_judgement(self, answer: str) -> bool:
        """解析判断题答案"""
        answer_lower = answer.strip().lower()
        true_values = ['正确', '对', '是', '√', '✓', 't', 'true', 'yes', '1']
        false_values = ['错误', '错', '否', '×', '✗', 'f', 'false', 'no', '0']

        if any(val in answer_lower for val in true_values):
            return True
        if any(val in answer_lower for val in false_values):
            return False
        return True  # 默认
