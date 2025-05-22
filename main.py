from abc import ABC, abstractmethod
from contextlib import asynccontextmanager

import _asyncio
import aiohttp
import asyncio

from fastapi import FastAPI
from pydantic import BaseModel, Field

allsession: aiohttp.ClientSession | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # await http_client.initialize()
    global allsession
    allsession = aiohttp.ClientSession()
    # await http_client.close()
    async with allsession:
        yield


app = FastAPI(lifespan=lifespan)
adapterlist: dict = {}


class Source(BaseModel):
    name: str
    key: str


class Srequest(BaseModel):
    """
    search request
    """
    question: str = Field(min_length=1)
    options: list[str] | None = None
    type: int = Field(0, ge=0, le=4)
    key: str | None = None
    use: list[Source]


class AdapterAutoFactory(ABC):
    """
        注册工厂
    """

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__()
        adapterlist[cls.__name__] = cls()

    @abstractmethod
    async def search(self, question: Srequest, key: str):
        pass


class Adapterans:
    ans: str


class Tikuhai(AdapterAutoFactory):
    url: str = "https://api.tikuhai.com/search"
    headers: dict = {"Content-Type": "application/json",
                     "User-Agent": "tikuhaiAdapter/0.1.0",
                     "v": "0.1.0"}

    async def search(self, question: Srequest, key: str):
        body = {
            "question": question.question,
            "options": question.options,
            "type": question.type,
            "key": key,
            "questionData": ""
        }
        try:
            async with allsession.post(self.url, headers=self.headers, json=body) as response:
                req = await response.json()
                print(req)
                return {"ans": req}
        except Exception as e:
            print(f"Request error: {e}")
            return {"error": str(e)}


class Enncy(AdapterAutoFactory):
    # url: str = "https://tk.enncy.cn/query"言溪用get的，直接编码url
    TYPE = {0: "single", 1: "multiple", 3: "judgement", 2: "completion", 4: "completion"}

    # 言溪没有填空
    # ‘single’ | ‘multiple’ | ‘judgement’ | ‘completion’

    async def search(self, question: Srequest, key: str):
        _options = ""
        for option in question.options:
            _options = _options + option + "\n"

        url = f"https://tk.enncy.cn/query?question={question.question}&options={_options}&type={self.TYPE[question.type]}&token={key}"
        try:
            async with allsession.get(url) as response:
                req = await response.json()
                print(req)
                return req
        except Exception as e:
            print(f"Request error: {e}")
            return {"error": str(e)}


class A(BaseModel):
    """
        answerdata
    """

    answerKey: list[str] | None = None
    answerKeyText: str | None = None
    answerText: str | None = None
    answerIndex: list[int] | None = None
    bestAnswer: list[str] | None = None
    allAnswer: list[list[str]] | None = None


class Sresponse(BaseModel):
    """
    search response
    """
    plat: str | None = None
    question: str = Field(min_length=1)
    options: list[str] | None = None
    type: int = Field(0, ge=0, le=4)  # 单选0多选1填空2判断3问答4
    answer: A


@app.post("/adapter-service/search")
async def search_use(_search_request: Srequest):
    _ans = []
    _t: list[_asyncio.Task] = []
    valid_adapters = [(use.name, use.key) for use in _search_request.use if use.name in adapterlist]
    async with asyncio.TaskGroup() as tg:
        for name, key in valid_adapters:
            _t.append(tg.create_task(adapterlist[name].search(_search_request, key)))

    # return
    _ans = [i.result() for i in _t]
    return _ans
