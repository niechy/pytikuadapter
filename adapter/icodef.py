from core import Adapter
from models import Srequest, AdapterAns, ErrorType


class Icodef(Adapter):  # pylint: disable=too-few-public-methods

    async def search(self, question: Srequest):
        # body = {
        #     "question": question.question,
        #     "options": question.options,
        #     "type": question.type,
        #     "key": question.use["Icodef"].key,
        #     "questionData": ""
        # }
        url = f"https://q.icodef.com/api/v1/q/{question.question}?simple=false"
        # 咱不用简单模式哈
        async with super().session.get(url=url, headers={"Authorization":question.use["Icodef"].token}) as response:
            ans: AdapterAns = AdapterAns(None, question.type, None)
            if response.status == 200:
                req = await response.json()
                print(req)
                if req["code"] == 0:
                    ans.answer=[]
                    for i in req["data"]["correct"]:
                        ans.answer.append(i["content"])
                    ans.type=req["data"]["type"]-1
                    #在icodef题型是1-5，而本框架题型是0-4，故-1
                    # ans.answer = req["data"]["answer"]
                else:
                    ans.error=ErrorType.TARGET_NO_ANSWER
            else:
                ans.error = ErrorType.TARGET_SERVER_ERROR
            return ans

        # except Exception as e:
        #     print(f"Request error: {e}")
        #     return {"error": str(e)}
