from core import Adapter
from models import Srequest, AdapterAns, ErrorType


class Tikuhai(Adapter):
    url: str = "https://api.tikuhai.com/search"
    headers: dict = {"Content-Type": "application/json",
                     "User-Agent": "pytikuhaiAdapter/1.0.0",
                     "v": "1.0.0"}

    async def search(self, question: Srequest):
        body = {
            "question": question.question,
            "options": question.options,
            "type": question.type,
            "key": question.use["Tikuhai"].key,
            "questionData": ""
        }
        # try:
        async with super().session.post(self.url, headers=self.headers, json=body) as response:
            ans: AdapterAns = AdapterAns(None,question.type, None)
            if response.status == 200:
                req = await response.json()
                if req["code"] == -1:
                    if "有答案" in req["msg"]:
                        ans.error = ErrorType.TOKEN_REQUIRED  # 付费题库才有
                    else:
                        ans.error = ErrorType.TARGET_NO_ANSWER  # 题库里没有
                else:
                    ans.answer = req["data"]["answer"]
            else:
                ans.error = ErrorType.TARGET_SERVER_ERROR
            return ans

        # except Exception as e:
        #     print(f"Request error: {e}")
        #     return {"error": str(e)}
