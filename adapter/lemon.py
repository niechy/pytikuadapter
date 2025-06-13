from core import Adapter
from models import Srequest, AdapterAns, ErrorType


class Lemon(Adapter):  # pylint: disable=too-few-public-methods
    url: str = "https://api.vanse.top"
    FREE=True
    PAY=True
    async def _search(self, question: Srequest):
        header = {"Content-Type": "application/json"}
        body = {
            "v": "1.0",
            "question": question.question,
            "options": question.options,
            "type": question.type,
        }
        if question.use["Lemon"].query_type == 2 :
            if question.use["Lemon"].token is None:
                return AdapterAns(None, question.type, ErrorType.TOKEN_REQUIRED)
            else:
                url = self.url + "/api/v1/mcx"
        else:
            url = self.url + "/api/v1/cx"
            if question.use["Lemon"].token is not None:
                header["Authorization"] = "Bearer "+question.use["Lemon"].token
        async with self.session.post(url=url,headers=header, json=body) as response:
            ans: AdapterAns = AdapterAns(None, question.type, None)
            if response.status == 200:
                req = await response.json()
                print(req)
                if req["code"] == 1000:
                    ans.answer = req["data"]["answer"].split('#')
                    if not isinstance(ans.answer,list):
                        ans.answer=[ans.answer]
                else:
                    ans.error = ErrorType.TARGET_SERVER_ERROR
            elif response.status == 429:
                ans.error = ErrorType.TARGET_API_FLOW
            else:
                ans.error = ErrorType.TARGET_SERVER_ERROR
            return ans
