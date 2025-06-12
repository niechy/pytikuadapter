# 感谢赛博善人纯免费
from models import AdapterAns, ErrorType, Srequest
from core import Adapter


class Zxseek(Adapter):  # pylint: disable=too-few-public-methods
    url: str = "http://api.wkexam.com/api"
    FREE = True
    PAY = False

    async def search(self, question: Srequest):

        params={
            "token": "qqqqq",
            "q":question.question
        }
        async with self.session.get(url=self.url,params=params) as response:
            ans: AdapterAns = AdapterAns(None, question.type, None)
            ans.answer = []
            if response.status == 200:
                req = await response.json()
                if req["code"] == 1:
                    for i in req["data"]["answer"]:
                        ans.answer.append(question.options[self.OPTION[i]])
                    # ans.answer = req["data"]["answer"]
                    # print(ans.answer)
                else:
                    ans.error = ErrorType.TARGET_NO_ANSWER
            else:
                ans.error = ErrorType.TARGET_SERVER_ERROR  # 对方服务器有猫病
            return ans
