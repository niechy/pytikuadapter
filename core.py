import asyncio
from abc import ABC, abstractmethod, ABCMeta
import aiohttp
from models import Srequest, Sresponse, AdapterAns, A
from collections import defaultdict

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
TRUE_LIST=["正确", "对", "✓", "√", "v", "是", "T", "t", "Y", "y", "中"]
FALSE_LIST=["错误", "错", "✗", "叉", "×", "否", "不对", "不正确", "f", "F", "n", "N", "否定", "不中"]

# 准备写答案匹配
# 这里能做很多文章
# 打算写个笨笨的暴力
# https://scikit-learn.org.cn/view/108.html
# 查了相关聚类算法，OPTICS的效果挺好，就用它了
# 写个OPTICS聚类（不知道写不写的出来，代码低手.jpg）
async def answer_match(_search_request: Srequest, _adapter_ans: list[AdapterAns]) -> Sresponse:
    # _temp = {}
    answer_counts = defaultdict(int)
    allans = Sresponse(question=_search_request.question, options=_search_request.options, type=_search_request.type)
    allans.answer = A()
    allans.answer.allAnswer = []
    allans.answer.bestAnswer = []
    # 接下来写的非常屎，按道理if 嵌套之类的不应该超过三次，到时候再优化吧
    for i in _adapter_ans:
        if i.type != _search_request.type:
            continue
        allans.answer.allAnswer.append(i.answer)
        for j in i.answer:
            if i.type in (0,1):
                if _search_request.options is not None:
                    if j in _search_request.options:
                        answer_counts[j] += 1
                else:
                    answer_counts[j] += 1
            elif i.type ==3:
                if j in TRUE_LIST:
                    answer_counts["对"] += 1
                elif j in FALSE_LIST:
                    answer_counts["错"] += 1
            else:
                answer_counts[j] += 1
            # if _search_request.options is not None:
            #     if _search_request.type == 0 or _search_request.type == 1:
            #         # 单选多选大概没问题
            #         if j in _search_request.options:
            #             _temp.setdefault(j, 0)
            #             _temp[j] += 1
            #     elif _search_request.type == 3:
            #         # 填空和简答题没选项的
            #         # 判断题
            #         # 正确,对,✓,√,v,是,T,t,Y,y,中(doge)
            #         # 错误,错,✗,叉,×,否,不对,不正确,f,F,n,N,否定,不中(doge)
            #         if j in ["正确", "对", "✓", "√", "v", "是", "T", "t", "Y", "y", "中"]:
            #             _temp.setdefault("对", 0)
            #             _temp["对"] += 1
            #         elif j in ["错误", "错", "✗", "叉", "×", "否", "不对", "不正确", "f", "F", "n", "N", "否定",
            #                    "不中"]:
            #             _temp.setdefault("错", 0)
            #             _temp["错"] += 1
            #
            # else:
            #     if _search_request.type == 3:
            #         if j in ["正确", "对", "✓", "√", "v", "是", "T", "t", "Y", "y", "中"]:
            #             _temp.setdefault("对", 0)
            #             _temp["对"] += 1
            #         elif j in ["错误", "错", "✗", "叉", "×", "否", "不对", "不正确", "f", "F", "n", "N", "否定",
            #                    "不中"]:
            #             _temp.setdefault("错", 0)
            #             _temp["错"] += 1
            #     else:
            #         _temp.setdefault(j, 0)
            #         _temp[j] += 1
    _max = max(answer_counts.values())
    allans.answer.bestAnswer = [ans for ans, count in answer_counts.items() if count == _max]
    return allans


async def search_use(_search_request: Srequest):
    _ans = []
    _t: list = []
    valid_adapters = [use for use in _search_request.use if use in AdapterMeta.adapterdict]
    async with asyncio.TaskGroup() as tg:
        for adapter in valid_adapters:
            _t.append(tg.create_task(AdapterMeta.adapterdict[adapter].search(_search_request)))
    _ans = [i.result() for i in _t]
    ans = await answer_match(_search_request, _ans)
    print(ans)
    return _ans
