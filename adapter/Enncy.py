from core import Adapter
from models import Srequest


class Enncy(Adapter):
    # url: str = "https://tk.enncy.cn/query"言溪用get的，直接编码url
    TYPE = {0: "single", 1: "multiple", 3: "judgement", 2: "completion", 4: "completion"}

    # 言溪没有填空
    # ‘single’ | ‘multiple’ | ‘judgement’ | ‘completion’

    async def search(self, question: Srequest):
        _options = ""
        for option in question.options:
            _options = _options + option + "\n"

        url = f"https://tk.enncy.cn/query?question={question.question}&options={_options}&type={self.TYPE[question.type]}&token={question.use["Enncy"].token}"
        try:
            async with super().session.get(url) as response:
                req = await response.json()
                print(req)
                return req
        except Exception as e:
            print(f"Request error: {e}")
            return {"error": str(e)}