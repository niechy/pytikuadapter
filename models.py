from pydantic import BaseModel, Field



class Srequest(BaseModel):
    """
    search request
    """

    class Argument(BaseModel):
        token: str | None = None
        key: str | None = None
        model: str | None = None
        search: str | None = None

    question: str = Field(min_length=1)
    options: list[str] | None = None
    type: int = Field(0, ge=0, le=4)
    key: str | None = None
    use: dict[str, Argument]

#
# class AdapterAutoFactory(ABC):
#     """
#         注册工厂
#     """
#
#     def __init_subclass__(cls, **kwargs):
#         super().__init_subclass__()
#         adapterlist[cls.__name__] = cls()
#
#     @abstractmethod
#     async def search(self, question: Srequest, arg: Srequest.Argument):
#         pass


class AdapterAns:
    ans: str


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
