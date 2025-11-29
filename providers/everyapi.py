import json
from typing import Optional, List
from urllib.parse import quote

import aiohttp
from pydantic import BaseModel, Field, ValidationError
from .manager import Providersbase
from .matcher import build_choice_answer_from_keys
from model import QuestionContent, Provider, A


class EveryAPI(Providersbase):
    """everyAPI题库适配器"""
    name = "everyAPI题库"
    home = "https://www.everyapi.com/"
    url = "https://www.everyapi.com/api/v1/q/{question}"
    FREE = True
    PAY = True

    class Configs(BaseModel):
        """everyAPI适配器的配置参数"""
        token: str = Field(..., title="授权token")

    def _fail(self, query_type: int, error_type: str, message: str) -> A:
        """构造失败响应"""
        return A(provider=self.name, type=query_type, success=False, error_type=error_type, error_message=message)

    def _success(self, answer_type: int, *, choice: List[str] = None, text: List[str] = None, judgement: bool = None) -> A:
        """构造成功响应"""
        return A(provider=self.name, type=answer_type, choice=choice, text=text, judgement=judgement, success=True)

    async def _search(self, query: QuestionContent, provider: Provider) -> A:
        """查询everyAPI题库"""
        try:
            config = self.Configs(**provider.config)
        except ValidationError as e:
            return self._fail(query.type, "config_error", f"配置参数错误: {e}")

        try:
            # 构造请求
            request_url = self.url.format(question=quote(query.content))
            params = {"simple": "false", "token": config.token}
            headers = {"Authorization": f"Bearer {config.token}"}

            async with self.session.get(request_url, params=params, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 400:
                    try:
                        error_data = await response.json(content_type=None)
                        return self._fail(query.type, "api_error", error_data.get("msg", "请求参数错误"))
                    except:
                        return self._fail(query.type, "api_error", "请求参数错误")

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
        if data.get("code") != 0:
            return self._fail(query.type, "api_error", data.get("msg", "未找到答案"))

        result_data = data.get("data")
        if not result_data:
            return self._fail(query.type, "api_error", "API返回数据为空")

        correct_answers = result_data.get("correct")
        if not correct_answers:
            return self._fail(query.type, "api_error", "未找到答案")

        api_type = result_data.get("type")
        return self._parse_answer(correct_answers, api_type, query)

    def _parse_answer(self, correct_answers: list, api_type: int, query: QuestionContent) -> A:
        """
        解析答案

        everyAPI的type: 0=单选, 1=多选, 2=填空/问答, 3=判断
        correct_answers格式: [{"option": "A", "content": "答案内容"}, ...]
        """
        if api_type == 0 or api_type == 1:  # 选择题
            answer_keys = []
            answer_contents = []
            for ans in correct_answers:
                if option := ans.get("option"):
                    answer_keys.append(option.upper())
                if content := ans.get("content"):
                    answer_contents.append(content)

            # 如果没有option字段，尝试从content提取
            if not answer_keys:
                for content in answer_contents:
                    answer_keys.extend(self._extract_choice(content))

            return build_choice_answer_from_keys(
                provider_name=self.name,
                answer_keys=answer_keys,
                answer_text=' '.join(answer_contents) if answer_contents else None,
                options=query.options,
                question_type=query.type
            )

        elif api_type == 2:  # 填空/问答
            text_answers = [ans.get("content") for ans in correct_answers if ans.get("content")]
            if not text_answers:
                return self._fail(query.type, "api_error", "未找到文本答案")
            return self._success(query.type if query.type in [2, 4] else 2, text=text_answers)

        elif api_type == 3:  # 判断题
            if correct_answers:
                first = correct_answers[0]
                content = first.get("content", "") or first.get("option", "")
                judgement = self._parse_judgement(content)
                return self._success(3, judgement=judgement)

        # 未知类型，返回文本
        text_answers = [ans.get("content") for ans in correct_answers if ans.get("content")]
        return self._success(query.type, text=text_answers or ["未知答案"])

    def _extract_choice(self, answer: str) -> List[str]:
        """从答案字符串中提取选项字母"""
        import re
        answer = re.sub(r'^(答案[：:]\s*|正确答案[：:]\s*)', '', answer.strip())
        choices = re.findall(r'[A-Z]', answer.upper())
        if choices:
            seen = set()
            return [c for c in choices if not (c in seen or seen.add(c))]
        return []

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
