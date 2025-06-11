from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Union


class Qtype(int, Enum):
    """
    Lemon题库\n
    1普通查询\t2高级查询
    """
    normal: 1
    advanced: 2


class Argument(BaseModel):
    """
       token:密钥 这两个参数其实一样的\n
       key:密钥 只是有些题库用token有些用\n
       model: Like知识库：指定使用的AI模型名称\n
       search: Like知识库：是否启用模糊搜索模式\n
       score: Like知识库：匹配结果的最低置信度阈值\n
       query_type: Lemon题库：查询类型枚举值（Qtype）\n
       location: 万能题库：查询需要的源地址 比如chaoxing.com
       wid cid:AXE题库：AXE题库: 学习通的，wid是workid，cid是courseid
    """
    token: str | None = None
    key: str | None = None
    model: str | None = None
    search: bool | None = None
    score: float | None = None
    query_type: Qtype | None = None
    location: str | None = None
    wid :str|None = None
    cid:str|None = None
    # 不够灵活，要是新题库有新的东西得一直加下去
    # 考虑把adapter独有的Argument拆到每个adapter中
    # 投降QAQ，拆了半天总有问题，暂时搁置


# 应该是只加不减的，参数只会越来越多
class Srequest(BaseModel):
    """
    question: 待查询的问题内容\n
    options: 选项\n
    type: 问题类型标识符[0,4]：单选0多选1填空2判断3问答4\n
    token: 请求签名\n
    use: 适配器参数映射表，键为适配器名称，值为对应参数配置
    """
    question: str = Field(min_length=1)
    options: list[str] | None = None
    type: int = Field(0, ge=0, le=4)
    token: str | None = None
    use: dict[str, Argument] | None = None


class ErrorType(str, Enum):
    """
    错误类型枚举
    """
    TARGET_API_FLOW = "对方API接口限流"
    TARGET_SERVER_ERROR = "对方服务器异常"
    TARGET_NO_ANSWER = "对方没有答案"
    PARSER_JSON = "解析JSON错误"
    TOKEN_REQUIRED = "需要提供TOKEN"
    LOW_CONFIDENCE_SCORE = "答案置信分数过低"


class AdapterAns:
    answer: list[str] | None
    type: int | None
    error: ErrorType | None = None

    def __init__(self, ans, anstype, error):
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
    answer: A | None = None
