from core import Adapter
from models import Srequest, AdapterAns, ErrorType


class EveryAPI(Adapter):  # pylint: disable=too-few-public-methods
    FREE = True  # 注意普通搜索没搜到时会用高级搜索使用点数
    PAY = True  # EveryAPI有ai，暂未支持，先挖坑

    async def _search(self, question: Srequest):
        # body = {
        #     "question": question.question,
        #     "options": question.options,
        #     "type": question.type,
        #     "key": question.use["EveryAPI"].key,
        #     "questionData": ""
        # }
        url = f"https://q.icodef.com/api/v1/q/{question.question}"
        # 咱不用简单模式哈
        async with self.session.get(url=url, params={"simple": 0},
                                    headers={"Authorization": "Bearer "+question.use["EveryAPI"].token}) as response:
            ans: AdapterAns = AdapterAns(None, question.type, None,self.__class__.__name__)
            if response.status == 200:
                req = await response.json()
                print(req)
                if req["code"] == 0:
                    ans.answer = []
                    for i in req["data"]["correct"]:
                        ans.answer.append(i["content"])
                    ans.type = req["data"]["type"] - 1
                    # 在EveryAPI题型是1-5，而本框架题型是0-4，故-1
                    # ans.answer = req["data"]["answer"]
                else:
                    ans.error = ErrorType.TARGET_NO_ANSWER
            else:
                ans.error = ErrorType.TARGET_SERVER_ERROR
            return ans

        # except Exception as e:
        #     print(f"Request error: {e}")
        #     return {"error": str(e)}
