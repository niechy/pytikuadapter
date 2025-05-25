from models import AdapterAns, ErrorType,Srequest
from core import Adapter


class Tikuhai(Adapter):  # pylint: disable=too-few-public-methods

    url: str = "https://api.tikuhai.com/search"
    headers: dict = {"Content-Type": "application/json",
                     "User-Agent": "pytikuhaiAdapter/1.0.0",
                     "v": "1.0.0"}

    def __init__(self):
        pass

    async def search(self, question: Srequest):
        body = {
            "question": question.question,
            "options": question.options,
            "type": question.type,
            "key": question.use["Tikuhai"].key,
            "questionData": ""
        }
        async with super().session.post(url=self.url, headers=self.headers, json=body) as response:
            ans: AdapterAns = AdapterAns(None, question.type, None)
            if response.status == 200:
                req = await response.json()
                if req["code"] == 200:
                    ans.answer = req["data"]["answer"]
                else:
                    if "有答案" in req["msg"]:
                        ans.error = ErrorType.TOKEN_REQUIRED  # 付费题库才有
                    else:
                        ans.error = ErrorType.TARGET_NO_ANSWER  # 题库里没有
            else:
                ans.error = ErrorType.TARGET_SERVER_ERROR
            return ans
