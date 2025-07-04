from core import Adapter
from models import Srequest, AdapterAns, ErrorType


class Wanneng(Adapter):  # pylint: disable=too-few-public-methods
    FREE = True
    PAY = True

    async def _search(self, question: Srequest):
        url: str = "http://lyck6.cn/scriptService/api/autoFreeAnswer"  # 免费的
        body = {
            "question": question.question,
            "options": question.options,
            "type": question.type,
            "location": question.use["Wanneng"].location
        }
        if question.use["Wanneng"].token is not None:
            url = "http://lyck6.cn/scriptService/api/autoAnswer/" + question.use["Wanneng"].token
        async with self.session.post(url=url, json=body) as response:
            ans: AdapterAns = AdapterAns(None, question.type, None,self.__class__.__name__)
            if response.status == 200:
                req = await response.json()
                print(req)
                if req["code"] == 0:
                    ans.answer = []
                    if req["result"]["success"]:
                        for i in req["result"]["answers"]:
                            ans.answer.append(question.options[i])
                    else:
                        if len(req["result"]["answers"]) == 0:
                            ans.answer=None
                            ans.error=ErrorType.TARGET_NO_ANSWER
                        else :
                            ans.answer = req["result"]["answers"]
                        # 万能没匹配成功会返回二维数组，应该要处理一下
                else:
                    ans.error = ErrorType.TARGET_SERVER_ERROR
            elif response.status == 429:
                ans.error = ErrorType.TARGET_API_FLOW
            else:
                ans.error = ErrorType.TARGET_SERVER_ERROR
            return ans
