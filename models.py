from enum import Enum

from pydantic import BaseModel, Field


class Srequest(BaseModel):
    """
    search request
    """

    class Argument(BaseModel):
        token: str | None = None
        key: str | None = None
        model: str | None = None
        search: bool | None = None
        score:float  | None = None

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

class ErrorType(str, Enum):
    """
    错误类型枚举
    """
    TARGET_API_FLOW = "对方API接口限流"
    TARGET_SERVER_ERROR = "对方服务器异常"
    TARGET_NO_ANSWER = "对方没有答案"
    PARSER_JSON = "解析JSON错误"
    TOKEN_REQUIRED = "需要提供TOKEN"
    LOW_CONFIDENCE_SCORE="答案置信分数过低"

class AdapterAns:

    answer: list[str]|None
    type:int|None
    error:ErrorType  | None = None
    def __init__(self,  ans,anstype,error):
        self.answer = ans
        self.type = anstype
        self.error = error
    def __setitem__(self, key, value):
        self.__dict__[key] = value
    def __getitem__(self, item):
        return self.__dict__[item]
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
