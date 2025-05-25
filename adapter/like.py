import json

from core import Adapter
from models import Srequest, AdapterAns, ErrorType


class Like(Adapter):  # pylint: disable=too-few-public-methods
    url: str = "https://api.datam.site/search"
    TYPE_request = {0: "【单选题】：", 1: "【多选题】：", 2: "【填空题】：", 3: "【判断题】：", 4: "【问答题】："}
    TYPE_response = {1: "选择题", 2: "填空题", 3: "判断题", 0: "其他题"}
    headers: dict = {"Content-Type": "application/json"}
    def  __init__(self):
        pass
    async def search(self, question: Srequest):
        _options = ""
        for option in question.options:
            _options = _options + option + "\n"
        body = {
            "query": self.TYPE_request[question.type] + question.question +"选项："+ _options,
            "token": question.use["Like"].token,
        }
        if question.use["Like"].model is not None:
            body["model"] = question.use["Like"].model
        if question.use["Like"].search is not None:
            body["search"] = question.use["Like"].search
        async with self.session.post(self.url, headers=self.headers, json=body) as response:
            ans = AdapterAns(None, question.type, None)
            if response.status == 200:
                try:  #
                    req = await response.json()
                    print(req)
                except  json.JSONDecodeError:
                    ans.error = ErrorType.PARSER_JSON
                if req["success"]:
                    if question.use["Like"].score is None or float(req["data"]["score"]) >= question.use["Like"].score:
                        _type = req["data"]["type"]
                        # 这里有点怪，测试时小概率提示找不到["type"]
                        # 大模型的原因吗？有空再来写验证这些存不存在吧
                        ans.answer = []
                        match _type:
                            case 1:
                                for i in req["data"]["choose"]:
                                    ans.answer.append(question.options[self.OPTION[i]])
                            case 2:
                                for i in req["data"]["fills"]:
                                    ans.answer.append(i)
                            case 3:
                                ans.answer = ["正确" if req["data"]["judge"] == 1 else "错误"]
                            case 0:
                                ans.answer = req["data"]["others"]
                    else:
                        ans.error = ErrorType.LOW_CONFIDENCE_SCORE
                else:
                    ans.error = ErrorType.TARGET_NO_ANSWER
            else:
                ans.error = ErrorType.TARGET_SERVER_ERROR
            return ans
