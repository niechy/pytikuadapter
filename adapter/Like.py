from core import Adapter
from models import Srequest


class Like(Adapter):
    url: str = "https://api.datam.site/search"
    TYPE = {0: "【单选题】", 1: "【多选题】", 2: "【填空题】", 3: "【判断题】", 4: "【问答题】"}

    async def search(self, question: Srequest):
        body = {
            "query": question.question,
            "token": question.use["Like"].token,
            "model": question.use["Like"].model,
            "search": question.use["Like"].search,
        }

        try:
            async with super().session.get(self.url, json=body) as response:
                req = await response.json()
                print(req)
                return req
        except Exception as e:
            print(f"Request error: {e}")
            return {"error": str(e)}