from core import Adapter
from models import Srequest, AdapterAns, ErrorType

class Enncy(Adapter):
    url: str = "https://tk.enncy.cn/query"
    TYPE = {0: "single", 1: "multiple", 3: "judgement", 2: "completion", 4: "completion"}

    # 言溪没有填空
    # ‘single’ | ‘multiple’ | ‘judgement’ | ‘completion’

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

        async with super().session.get(self.url, params=params) as response:
            ans=AdapterAns(None,question.type,None)
            req = await response.json()
            if response.status == 200:
                if req["code"] == 1:
                    ans.answer = req["data"]["answer"]
                else:
                    ans.error=ErrorType.TARGET_NO_ANSWER
            else:
                ans.error = ErrorType.TARGET_SERVER_ERROR
            return ans
