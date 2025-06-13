from models import AdapterAns, ErrorType, Srequest
from core import Adapter


class Zero(Adapter):  # pylint: disable=too-few-public-methods
    url: str = "http://www.anyzero.org/user/api.php"
    FREE = True
    PAY = True
    header = {"Content-Type": "application/json"}

    async def _search(self, question: Srequest):
        params = {
            "token": question.use["Zero"].token,
            "q": question.question
        }
        async with self.session.get(url=self.url, headers=self.header, params=params) as response:
            ans: AdapterAns = AdapterAns(None, question.type, None)
            ans.answer = []
            print(await response.text())
            if response.status == 200:
                req = await response.json()
                # 这段代码会报错，因为对方服务器返回Content-Type为text/html，所以无法解析成json
                if req["code"] == 1:
                    # for i in req["data"]["answer"]:
                    #     ans.answer.append(question.options[self.OPTION[i]])
                    ans.answer = req["data"]["answer"]
                    print(ans.answer)
                else:
                    ans.error = ErrorType.TARGET_NO_ANSWER
            else:
                ans.error = ErrorType.TARGET_SERVER_ERROR  # 对方服务器有猫病
            return ans
