from fastapi import FastAPI
from pydantic import BaseModel, Field
from abc import ABC, abstractmethod
import json
import aiohttp

app = FastAPI()

adapterlist: dict = {}


class Source(BaseModel):
    name: str
    key: str


class Srequest(BaseModel):
    """
    search request
    """
    question: str = Field(min_items=1)
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


class adapterans:
    ans:str

class Tikuhai(AdapterAutoFactory):
    url: str = "https://api.tikuhai.com/search"
    headers: dict = {"Content-Type": "application/json",
                     "User-Agent": "tikuhaiAdapter/0.1.0",
                     "v": "0.1.0"}

    def __init__(self):
        self.body = {
            "question": "",
            "options": None,
            "type": 0,
            "key": "",
            "questionData": ""
        }

    async def search(self, question: Srequest, key: str):
        self.body["question"] = question.question
        self.body["options"] = question.options
        self.body["type"] = question.type
        self.body["key"] = key
        async with aiohttp.ClientSession() as session:
            async with session.post(self.url, headers=self.headers, json=self.body) as response:
                return await response.json()


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
    question: str = Field(min_items=1)
    options: list[str] | None = None
    type: int = Field(0, ge=0, le=4)
    answer: A


@app.post("/adapter-service/search")
async def search_use(_search_request: Srequest):
    _t=""
    print(adapterlist)

    for use in _search_request.use:
        print(use)
        if use.name in adapterlist:
            _t=await adapterlist[use.name].search(_search_request, use.key)
    return _t
