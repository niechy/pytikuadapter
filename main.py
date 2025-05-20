from fastapi import FastAPI
from pydantic import BaseModel,Field
fro
app = FastAPI()

class Srequest(BaseModel):
    """
    search request
    """
    question:str = Field(min_items=1)
    options:list[str] | None = None
    type:int = Field(0,ge=0,le=4)
    source:str | None =None
    key:str | None = None

class A(BaseModel):
    """
        answerdata
    """

    answerKey:list[str] | None = None
    answerKeyText:str | None = None
    answerText:str | None = None
    answerIndex:list[int] | None = None
    bestAnswer:list[str] | None = None
    allAnswer:list[list[str]] | None = None

class Sresponse(BaseModel):
    """
    search response
    """
    plat:str | None = None
    question:str = Field(min_items=1)
    options:list[str] | None = None
    type:int = Field(0,ge=0,le=4)


@app.post("/adapter-service/search")
async def search(_search_request:Srequest):
    pass
