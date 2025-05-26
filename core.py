import asyncio
from abc import ABC, abstractmethod, ABCMeta
import aiohttp
from models import Srequest, Sresponse,AdapterAns,A


class AdapterMeta(ABCMeta):
    adapterdict = {}

    def __new__(mcs, name, bases, attrs):
        new_class = super().__new__(mcs, name, bases, attrs)
        if name != 'Adapter':
            mcs.adapterdict[name] = new_class()
            # mcs.adapterdict[name].session = aiohttp.ClientSession()
            # 将全局session改为每个adapter一个session
            # 方便adapter设置重试以及超时等

            # aiohttp.ClientSession()与close()移到lifespan()中管理
        return new_class


class Adapter(ABC, metaclass=AdapterMeta):
    session: aiohttp.ClientSession = None
    OPTION = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6, "H": 7, "I": 8, "J": 9, "K": 10, "L": 11, "M": 12,
              "N": 13}
    FREE = False  # 有免费接口就设置为True
    PAY = True  # 有付费接口就设置为True

    # 暂且默认为需要付费

    @abstractmethod
    async def search(self, question: Srequest):
        pass


# 准备写答案匹配
# 这里能做很多文章
# 打算写个笨笨的暴力
# https://scikit-learn.org.cn/view/108.html
# 查了相关聚类算法，OPTICS的效果挺好，就用它了
# 写个OPTICS聚类（不知道写不写的出来，代码低手.jpg）
async def answer_match(_search_request: Srequest, _adapter_ans: list[AdapterAns]) -> Sresponse:
    # _adapter_ans.pop()
    _temp={}
    allans=Sresponse(question=_search_request.question,options=_search_request.options,type=_search_request.type)
    allans.answer=A()
    allans.answer.allAnswer=[]
    allans.answer.bestAnswer=[]
    if _search_request.options is not None:
        # 单选多选大概没问题
        for i in _adapter_ans:
            if i.type == _search_request.type:
                allans.answer.allAnswer.append(i.answer)
                for j in i.answer:
                    if j in _search_request.options:
                        _temp.setdefault(j,0)
                        _temp[j] +=1
        _max=max(_temp.values())
        for i in _temp:
            if _temp[i]==_max:
                allans.answer.bestAnswer.append(i)
    else:
        pass
    return allans


async def search_use(_search_request: Srequest):
    _ans = []
    _t: list = []
    valid_adapters = [use for use in _search_request.use if use in AdapterMeta.adapterdict]
    async with asyncio.TaskGroup() as tg:
        for adapter in valid_adapters:
            _t.append(tg.create_task(AdapterMeta.adapterdict[adapter].search(_search_request)))
    _ans = [i.result() for i in _t]
    # ans=await answer_match(_search_request, _ans)
    # print(_ans)
    return _ans
