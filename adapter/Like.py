import json

from core import Adapter
from models import Srequest, AdapterAns, ErrorType


class Like(Adapter):
    url: str = "https://api.datam.site/search"
    TYPE_request = {0: "【单选题】", 1: "【多选题】", 2: "【填空题】", 3: "【判断题】", 4: "【问答题】"}
    TYPE_response = {1: "选择题", 2: "填空题", 3: "判断题", 0: "其他题"}
    OPTION={0: "A", 1: "B", 2: "C", 3: "D", 4: "E", 5: "F", 6: "G", 7: "H", 8: "I", 9: "J", 10: "K", 11: "L", 12: "M"}
    headers: dict = {"Content-Type": "application/json"}

    async def search(self, question: Srequest):
        _options = ""
        for option in question.options:
            _options = _options + option + "\n"
        body = {
            "query": self.TYPE_request[question.type] + question.question + _options,
            "token": question.use["Like"].token,
        }
        if question.use["Like"].model is not None:
            body["model"] = question.use["Like"].model
        if question.use["Like"].search is not None:
            body["search"] = question.use["Like"].search
        async with super().session.post(self.url, headers=self.headers, json=body) as response:
            ans = AdapterAns(None, question.type, None)
            if response.status == 200:
                try:  #
                    req = await response.json()
                except  json.JSONDecodeError as e:
                    ans.error = ErrorType.PARSER_JSON
                if req["success"]:
                    if float(req["data"]["score"]) >= question.use["Like"].score:#还要改
                        _type = req["type"]
                        match _type:
                            case 1:
                                for i in req["data"]["choose"]:
                                    ans.answer.append(self.OPTION[i["index"]])
                            case 2:
                            case 3:
                            case 0:
                    else:
                        ans.error = ErrorType.LOW_CONFIDENCE_SCORE
                else:
                    ans.error = ErrorType.TARGET_NO_ANSWER
            else:
                ans.error = ErrorType.TARGET_SERVER_ERROR
                return ans
            return req
