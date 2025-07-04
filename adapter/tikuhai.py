import asyncio
import json

from aiohttp import ClientResponse, ClientRequest, ClientError
from aiohttp.web_middlewares import middleware

from models import AdapterAns, ErrorType, Srequest
from core import Adapter


# 欢迎大佬们提PR和issue
# orz orz orz
class Tikuhai(Adapter):  # pylint: disable=too-few-public-methods
    # 这里写些不动的属性
    # url需要拼接的最好在search中创建一个url，把两部分拼起来，直接拼self.url的话异步可能对其他请求有影响（大概，猜的）
    url: str = "https://api.tikuhai.com/search"
    headers: dict = {"Content-Type": "application/json",
                     "User-Agent": "pytikuhaiAdapter/1.0.0",
                     "v": "1.0.0"}

    """
        FREE (bool): 表示有无免费模式，默认值为False
        PAY (bool): 表示有无付费模式，默认值为True
    """
    FREE = False
    PAY = True

    @staticmethod
    async def retry_middleware(
            req: ClientRequest, handler
    ) -> ClientResponse:
        """
        重试中间件
        :param req: ClientRequest对象
        :param handler: 请求处理函数
        :return: ClientResponse对象
        """
        for _ in range(3):  # Try up to 3 times
            resp = await handler(req)
            if resp.ok:
                break
            await asyncio.sleep(1*(_ ** 2))
        return resp
    async def _search(self, question: Srequest):
        """
       异步搜索题库获取题目答案
       :param question: Srequest对象
       :return: AdapterAns对象
       """
        # 请求体
        body = {
            "question": question.question,
            "options": question.options,
            "type": question.type,
            "key": question.use["Tikuhai"].key,
            "questionData": ""
        }
        # params 题库海并没用到
        # params = {"question": question.question}
        ans: AdapterAns = AdapterAns(None, question.type, None, self.__class__.__name__)
        try:
            async with self.session.post(url=self.url, headers=self.headers, json=body,middlewares=(self.retry_middleware,)) as response:
                # 还有可能是session.get

                # 初始化一个答案对象
                # 正常返回ans有东西，error为None；错误返回ans为None，error有东西
                # 错误类型可以去看看ErrorType
                if response.status == 200:
                    # 看请求成功没，200再解析json
                    try:
                        req = await response.json()
                    except json.JSONDecodeError:
                        ans.error = ErrorType.PARSER_JSON
                    # 如果是大模型类的建议try，放在try except里面
                    # 返回的json可能有问题，毕竟不是准确的程序，可能出现比如没有["data"]之类的情况
                    # 接下来每个题库的返回格式不同，所以要视题库的返回格式来写，不能找找
                    if req["code"] == 200:
                        ans.answer = req["data"]["answer"]
                        # if not isinstance(ans.answer, list):
                        #   ans.answer = [ans.answer]题库海用不到，因为题库还返回的是列表，哪怕只有一个答案
                        # ans.answer要是一个列表，哪怕只有一个答案
                    else:
                        if "有答案" in req["msg"]:
                            ans.error = ErrorType.TOKEN_REQUIRED  # 付费题库才有
                        else:
                            ans.error = ErrorType.TARGET_NO_ANSWER  # 题库里没有
                else:
                    ans.error = ErrorType.TARGET_SERVER_ERROR  # 对方服务器有猫病
        except ClientError:
            ans.error = ErrorType.NETWORK_ERROR # 网络错误
        return ans
