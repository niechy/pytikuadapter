from models import AdapterAns, ErrorType, Srequest
from core import Adapter


class AXE(Adapter):  # pylint: disable=too-few-public-methods
    url: str = "http://tk.wanjuantiku.com/api/query"
    """
        FREE (bool): 表示有无免费模式，默认值为False
        PAY (bool): 表示有无付费模式，默认值为True
    """
    FREE = False
    PAY = True

    async def _search(self, question: Srequest):
        # 请求体
        body = {
            "tm": question.question,
            "options": question.options,
            "type": question.type,
            "token": question.use["AEX"].token,
            # answernum填空题用的
            "wid": question.use["AEX"].wid,
            "cid": question.use["AEX"].cid,
        }
        if question.type == 4:
            body["type"]=2
            # 只在body改，不影响返回校验类型
        async with self.session.post(url=self.url, json=body) as response:
            ans: AdapterAns = AdapterAns(None, question.type, None,self.__class__.__name__)
            if response.status == 200:
                req = await response.json()
                if req["code"] == 1:
                    if body["type"] == 2:
                        ans.answer = req["data"].split("#!#")
                    else:
                        ans.answer=req["data"].split("#")
                else:
                    ans.error = ErrorType.TARGET_NO_ANSWER
                    # 还要改，先这么写着吧
            else:
                ans.error = ErrorType.TARGET_SERVER_ERROR  # 对方服务器有猫病
            return ans
