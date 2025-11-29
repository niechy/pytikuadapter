import json
from typing import Optional, List

import aiohttp
from pydantic import BaseModel, Field, ValidationError
from .manager import Providersbase
from .matcher import build_choice_answer_from_keys
from model import QuestionContent, Provider, A


class Like(Providersbase):
    """Like知识库适配器"""
    name = "Like知识库"
    home = "https://www.datam.site/"
    url = "https://app.datam.site/api/v1/query"
    FREE = False
    PAY = True

    # API 返回的题目类型映射
    QUESTION_TYPE = {"CHOICE": 0, "FILL_IN_BLANK": 2, "JUDGMENT": 3}
    # 请求时的题目类型前缀
    TYPE_PREFIX = {0: "【单选题】：", 1: "【多选题】：", 2: "【填空题】：", 3: "【判断题】：", 4: "【问答题】："}

    class Configs(BaseModel):
        """Like适配器的配置参数"""
        key: str = Field(..., title="API密钥")
        model: Optional[str] = Field(None, title="大语言模型")
        search: Optional[bool] = Field(None, title="联网搜索")
        vision: Optional[bool] = Field(None, title="视觉理解")

    def _fail(self, query_type: int, error_type: str, message: str) -> A:
        """构造失败响应"""
        return A(provider=self.name, type=query_type, success=False, error_type=error_type, error_message=message)

    def _success(self, answer_type: int, *, choice: List[str] = None, text: List[str] = None, judgement: bool = None) -> A:
        """构造成功响应"""
        return A(provider=self.name, type=answer_type, choice=choice, text=text, judgement=judgement, success=True)

    async def _search(self, query: QuestionContent, provider: Provider) -> A:
        """查询Like知识库"""
        try:
            config = self.Configs(**provider.config)
        except ValidationError as e:
            return self._fail(query.type, "config_error", f"配置参数错误: {e}")

        try:
            # 构造请求
            body = {
                "query": self.TYPE_PREFIX.get(query.type, "") + query.content + str(query.options or []),
                "model": config.model,
                "search": config.search,
                "vision": config.vision,
            }
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {config.key}"
            }

            async with self.session.post(self.url, headers=headers, json=body, timeout=aiohttp.ClientTimeout(total=30)) as response:
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
        if data.get("message") != "查询成功":
            return self._fail(query.type, "api_error", data.get("message", "API返回错误"))

        # 提取 results.output
        results = data.get("results")
        if not results:
            return self._fail(query.type, "api_error", "API返回数据为空")

        output = results.get("output")
        if not output:
            return self._fail(query.type, "api_error", "未找到答案")

        # 获取题目类型
        question_type_str = output.get("questionType")
        if not question_type_str:
            return self._fail(query.type, "api_error", "无法识别题目类型")

        answer_type = self.QUESTION_TYPE.get(question_type_str)
        if answer_type is None:
            return self._fail(query.type, "api_error", f"不支持的题目类型: {question_type_str}")

        # 获取答案
        answer_data = output.get("answer")
        if not answer_data:
            return self._fail(query.type, "api_error", "答案数据为空")

        # 根据题目类型解析答案
        if answer_type == 0:  # 选择题
            selected_options = answer_data.get("selectedOptions")
            if not selected_options:
                return self._fail(query.type, "api_error", "未找到选项答案")
            return build_choice_answer_from_keys(
                provider_name=self.name,
                answer_keys=selected_options,
                answer_text=answer_data.get("otherText"),
                options=query.options,
                question_type=query.type
            )

        elif answer_type == 2:  # 填空题
            blanks = answer_data.get("blanks")
            if not blanks:
                return self._fail(query.type, "api_error", "未找到填空答案")
            return self._success(query.type, text=blanks)

        elif answer_type == 3:  # 判断题
            is_correct = answer_data.get("isCorrect")
            if is_correct is None:
                return self._fail(query.type, "api_error", "未找到判断答案")
            return self._success(answer_type, judgement=is_correct)

        return self._fail(query.type, "api_error", f"未处理的题目类型: {answer_type}")
