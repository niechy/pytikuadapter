from core import Adapter
from models import Srequest, AdapterAns, ErrorType


class Wanneng(Adapter):  # pylint: disable=too-few-public-methods
    def  __init__(self):
        FREE=True
        PAY=True
    async def search(self, question: Srequest):
        url: str = "http://lyck6.cn/scriptService/api/autoFreeAnswer"# 免费的
        body = {
            "question": question.question,
            "options": question.options,
            "type": question.type,
            "location":question.use["Wanneng"].location
        }
        if question.use["Wanneng"].token is not None:
            url="http://lyck6.cn/scriptService/api/autoAnswer/"+question.use["Wanneng"].token
        async with self.session.post(url=url, json=body) as response:
            ans: AdapterAns = AdapterAns(None, question.type, None)
            if response.status == 200:
                req = await response.json()
                print(req)
                if req["code"] == 0:
                    ans.answer=[]
                    if req["result"]["success"]:
                        for i in req["result"]["answers"]:
                            ans.answer.append(question.options[i])

                    else:
                        ans.answer = req["result"]["answers"]
                else:
                    ans.error = ErrorType.TARGET_SERVER_ERROR
            elif response.status == 429:
                ans.error = ErrorType.TARGET_API_FLOW
            else:
                ans.error = ErrorType.TARGET_SERVER_ERROR
            return ans
