from models import AdapterAns, ErrorType, Srequest
from openai import AsyncOpenAI  # 修改为异步客户端
import json
from core import Adapter


class SiliconFlow(Adapter):
    FREE = False
    PAY = True
    base_url = "https://api.siliconflow.cn/v1"

    def _generate_prompt(self, q_type: int) -> tuple[str, str]:
        system_prompt = "你是一个答题助手，请严格按JSON格式输出答案，不要包含任何额外信息，即使选项有ABCD还是输出选项文本。示例格式：{\"Answer\": [\"答案内容\"]}"

        user_prompt_templates = {
            0: "题目：{}\n选项：{}\n这是单选题，请选择唯一正确答案", 
            1: "题目：{}\n选项：{}\n这是多选题，请选择所有正确选项",
            2: "题目：{}{}\n这是填空题，请直接给出填空内容",
            3: "题目：{}\n选项：{}\n这是判断题，请回答'正确'或'错误'",
            4: "题目：{}{}\n这是简答题，请直接给出答案内容"
        }

        return system_prompt, user_prompt_templates.get(q_type, "题目：{}\n选项：{}")

    async def search(self, question: Srequest):

        client = AsyncOpenAI(
            api_key=question.use["SiliconFlow"].token,
            base_url=self.base_url
        )
        ans: AdapterAns = AdapterAns(None, question.type, None)
        try:
            system_prompt, user_prompt = self._generate_prompt(question.type)
            # noinspection PyTypeChecker
            response = await client.chat.completions.create(
                model=question.use["SiliconFlow"].model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt.format(question.question, question.options)}
                ],
                response_format={"type": "json_object"},
                max_tokens=4096,
                temperature=0.7,
                top_p=0.7
            )

            if response and response.choices:
                try:
                    content = response.choices[0].message.content
                    parsed = json.loads(content)
                    ans.answer = parsed["Answer"]
                    # 如果不是列表则转换为列表
                    if not isinstance(ans.answer, list):
                        ans.answer = [ans.answer]
                except json.JSONDecodeError:
                    ans.answer = None
                    ans.error = ErrorType.PARSER_JSON
        except Exception as e:
            # 处理各种可能的错误
            ans.answer=None
            error_str = str(e)
            ans.error = ErrorType.TARGET_SERVER_ERROR
            print(f"硅基流动API异常：{error_str}")  # 保留异常输出方便调试

        return ans
