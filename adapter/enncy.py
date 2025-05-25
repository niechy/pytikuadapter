from core import Adapter
from models import Srequest, AdapterAns, ErrorType


class Enncy(Adapter):  # pylint: disable=too-few-public-methods
    url: str = "https://tk.enncy.cn/query"
    TYPE = {0: "single", 1: "multiple", 3: "judgement", 2: "completion", 4: "completion"}

    # 言溪没有填空
    # ‘single’ | ‘multiple’ | ‘judgement’ | ‘completion’
    FREE = False
    PAY = True
        # 言溪就是只有付费题库的
    async def search(self, question: Srequest):
        _options = ""
        for option in question.options:
            _options = _options + option + "\n"
        params = {
            "question": question.question,
            "options": _options,
            "type": self.TYPE[question.type],
            "token": question.use["Enncy"].token
        }

        async with self.session.get(url=self.url, params=params) as response:
            ans = AdapterAns(None, question.type, None)
            req = await response.json()
            if response.status == 200:
                if req["code"] == 1:
                    ans.answer = req["data"]["answer"].split("#")
                    # 劳动主体#劳动个体#劳动结果
                    # 劳动最伟大劳动最美丽劳动最光荣劳动最崇高
                    # 有些答案有分隔符有些没 我拿什么分，NLP吗？
                    # 能分分，分不了摆
                    if not isinstance(ans.answer, list):
                        ans.answer = [ans.answer]
                else:
                    ans.error = ErrorType.TARGET_NO_ANSWER
            else:
                ans.error = ErrorType.TARGET_SERVER_ERROR
            return ans
