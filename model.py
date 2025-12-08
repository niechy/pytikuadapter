from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any

class Provider(BaseModel):
    name: str = Field(..., description="适配器名称")
    priority: Optional[int] = Field(0, description="适配器优先级，数字越大优先级越高，默认0")
    config: Optional[Dict[str, Any]] = Field(None, description="适配器配置参数")



class  QuestionContent(BaseModel):
    content: str = Field(..., description="题目内容")
    options: Optional[List[str]] = Field(None, description="题目选项")
    type: Optional[int] = Field(None, ge=0, le=4, description="题目类型，0-单选，1-多选，2-填空，3-判断，4-问答")

class QuestionRequest(BaseModel):
    query: QuestionContent = Field(..., description="题目信息")
    providers: Optional[List[Provider]] = Field(None, description="使用的适配器及其配置，不传则使用token中配置的providers")
    #那里面定义的字段就是该适配器需要的参数，可以参考下adapter/like.py中的Like类

class A(BaseModel):#每个适配器返回答案
    provider: Optional[str]=Field(None, description="适配器名称")
    type:Optional[int]=Field(None, ge=0, le=4, description="题目类型，0-单选，1-多选，2-填空，3-判断，4-问答")
    choice:Optional[List[str]]=Field(None, description="答案，仅单选和多选题目使用,example: ['A','B']，要求给选项list，并且大写，如果是文本选项请给对应的选项键")
    judgement:Optional[bool]=Field(None, description="答案，仅判断题使用example: true")
    text:Optional[List[str]]=Field(None, description="答案，仅填空和问答题目使用,即使只有一个答案也要用列表example: ['答案1','答案2']")

    # 错误信息字段
    success: bool = Field(True, description="是否成功获取答案")
    error_type: Optional[str] = Field(None, description="错误类型：cache_miss(缓存未命中), api_error(API错误), network_error(网络错误), config_error(配置错误), match_error(答案匹配失败), unknown(未知错误)")
    error_message: Optional[str] = Field(None, description="错误详细信息")

class UnifiedAnswer(BaseModel):
    answerKey: List[str] = Field(..., description="答案选项键，如 ['B','C']")
    answerKeyText: str = Field(..., description="合并后的答案键文本，如 'BC'")
    answerIndex: List[int] = Field(..., description="答案索引，如 [1,2]")
    answerText: str = Field(..., description="合并后的答案文本，用 '#@#' 分隔符连接，这样再怎么应该不会和题目里面的内容冲突")
    bestAnswer: List[str] = Field(..., description="最佳答案文本列表")

class Res(BaseModel):#构造的响应体
    query: QuestionContent = Field(..., description="题目信息")
    unified_answer: UnifiedAnswer = Field(..., description="统一答案")
    provider_answers: List[A] = Field(..., description="各适配器返回的结果列表（包括成功和失败）")
    successful_providers: int = Field(..., description="成功的适配器数量")
    failed_providers: int = Field(..., description="失败的适配器数量")
    total_providers: int = Field(..., description="总适配器数量")
"""
{
  "query":{
  "content": "违反安全保障义务责任属于（）",
  "type": 1,
  "options": [
    "公平责任",
    "特殊侵权责任", 
    "过错推定责任",
    "连带责任"
  ]
  },
  "unified_answer": {
    "answerKey": ["B", "C"],
    "answerKeyText": "BC", 
    "answerIndex": [1, 2],
    "answerText": "特殊侵权责任#过错推定责任",
    "bestAnswer": ["特殊侵权责任", "过错推定责任"]
  },
  "provider_answer": [
    {
      "provider": "Tikuhai",
      "type":0,
      "choice":["B", "C"]
    }
  ],
  "total_providers": 3,
  "successful_providers": 3
}
 """