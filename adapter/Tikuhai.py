# from core.core import Adapter,AdapterFactory
from core import Adapter
from models import Srequest
# @AdapterFactory.register()
class Tikuhai(Adapter):
    url: str = "https://api.tikuhai.com/search"
    headers: dict = {"Content-Type": "application/json",
                     "User-Agent": "tikuhaiAdapter/0.1.0",
                     "v": "0.1.0"}

    async def search(self, question: Srequest):
        body = {
            "question": question.question,
            "options": question.options,
            "type": question.type,
            "key": question.use["Tikuhai"].key,
            "questionData": ""
        }
        try:
            async with super().session.post(self.url, headers=self.headers, json=body) as response:
                req = await response.json()
                print(req)
                return {"ans": req}
        except Exception as e:
            print(f"Request error: {e}")
            return {"error": str(e)}
