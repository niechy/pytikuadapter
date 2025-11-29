import json
from typing import Optional, List

import aiohttp
from pydantic import BaseModel, Field, ValidationError
from .manager import Providersbase
from .matcher import build_choice_answer_from_keys
from model import QuestionContent, Provider, A


class Enncy(Providersbase):
    """言溪题库适配器"""
    name = "言溪题库"
    home = "https://tk.enncy.cn/"
    url = "https://tk.enncy.cn/query"
    FREE = True
    PAY = True

    # 题目类型映射：内部类型 -> API类型
    TYPE_MAP = {0: "single", 1: "multiple", 2: "completion", 3: "judgement", 4: "completion"}

    class Configs(BaseModel):
        """言溪适配器的配置参数"""
        token: str = Field(..., title="用户凭证")

    def _fail(self, query_type: int, error_type: str, message: str) -> A:
        """构造失败响应"""
        return A(provider=self.name, type=query_type, success=False, error_type=error_type, error_message=message)

    def _success(self, answer_type: int, *, choice: List[str] = None, text: List[str] = None, judgement: bool = None) -> A:
        """构造成功响应"""
        return A(provider=self.name, type=answer_type, choice=choice, text=text, judgement=judgement, success=True)

    async def _search(self, query: QuestionContent, provider: Provider) -> A:
        """查询言溪题库"""
        try:
            config = self.Configs(**provider.config)
        except ValidationError as e:
            return self._fail(query.type, "config_error", f"配置参数错误: {e}")

        try:
            # 构造请求参数
            params = {
                "token": config.token,
                "title": query.content,
            }
            if query.options:
                params["options"] = "\n".join(query.options)
            if query.type is not None:
                params["type"] = self.TYPE_MAP.get(query.type, "unknown")

            async with self.session.get(self.url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
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
        # 检查返回状态
        if data.get("code") != 1:
            return self._fail(query.type, "api_error", data.get("message", "未找到答案"))

        # 提取答案
        result_data = data.get("data", {})
        answer = result_data.get("answer")
        if not answer:
            return self._fail(query.type, "api_error", "未找到答案")

        # 根据题目类型解析答案
        return self._parse_answer(answer, query)

    def _parse_answer(self, answer: str, query: QuestionContent) -> A:
        """解析答案字符串"""
        if query.type == 0 or query.type == 1:  # 单选/多选
            choice = self._extract_choice(answer)
            return build_choice_answer_from_keys(
                provider_name=self.name,
                answer_keys=choice,
                answer_text=answer,
                options=query.options,
                question_type=query.type
            )

        elif query.type == 2 or query.type == 4:  # 填空/问答
            text_answers = self._split_text_answer(answer)
            return self._success(query.type, text=text_answers)

        elif query.type == 3:  # 判断题
            judgement = self._parse_judgement(answer)
            return self._success(query.type, judgement=judgement)

        # 未知类型，返回文本
        return self._success(query.type, text=[answer])

    def _extract_choice(self, answer: str) -> List[str]:
        """从答案字符串中提取选项字母"""
        import re
        answer = re.sub(r'^(答案[：:]\s*|正确答案[：:]\s*)', '', answer.strip())
        choices = re.findall(r'[A-Z]', answer.upper())
        if choices:
            seen = set()
            return [c for c in choices if not (c in seen or seen.add(c))]
        return [answer.strip()]

    def _split_text_answer(self, answer: str) -> List[str]:
        """分割文本答案"""
        for sep in ['#@#', '#', '|', ';', '；', '、']:
            if sep in answer:
                parts = [p.strip() for p in answer.split(sep) if p.strip()]
                if parts:
                    return parts
        return [answer.strip()]

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
