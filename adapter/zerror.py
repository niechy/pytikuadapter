from models import AdapterAns, ErrorType, Srequest
from core import Adapter


class Zerror(Adapter):  # pylint: disable=too-few-public-methods
    url: str = "https://api.zaizhexue.top/api/query"
    FREE = True
    PAY = False

    TYPE_request = {0: "single", 1: "multiple", 2: "completion", 3: "judgement", 4: "completion"}
    async def search(self, question: Srequest):
        body = {
            "title": question.question,
            "options":str(question.options),
            "type": self.TYPE_request[question.type],
        }
        header = {"Content-Type": "application/json",
                  "Authorization":"Bearer "+question.use["Zerror"].token,
                  }
        print(body, header,self.url)
        async with self.session.post(url=self.url, headers=header, json= body) as response:
            ans: AdapterAns = AdapterAns(None, question.type, None)
            ans.answer = []
            if response.status == 200:
                req = await response.json()
                if req["data"]["code"] == 1:
                    ans.answer = req["data"]["data"].split("#")
                    print(ans.answer)
                else:
                    ans.error = ErrorType.TARGET_NO_ANSWER
            else:
                ans.error = ErrorType.TARGET_SERVER_ERROR  # 对方服务器有猫病
            return ans
