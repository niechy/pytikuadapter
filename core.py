# 目前所有处理都在这里处理，未来按需拆分吧
import asyncio
import hashlib
import re
from abc import ABC, abstractmethod, ABCMeta
import aiohttp

from models import Srequest, Sresponse, AdapterAns, A, ErrorType
from collections import defaultdict
from sql import CAO

questionCAO = CAO()


class AdapterMeta(ABCMeta):
    adapterdict = {}

    def __new__(mcs, name, bases, attrs):
        new_class = super().__new__(mcs, name, bases, attrs)
        if name != 'Adapter':
            mcs.adapterdict[name] = new_class

            # aiohttp.ClientSession()与close()移到lifespan()中管理
        return new_class


class Adapter(ABC, metaclass=AdapterMeta):
    session: aiohttp.ClientSession = None
    OPTION = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6, "H": 7, "I": 8, "J": 9, "K": 10, "L": 11, "M": 12,
              "N": 13}
    FREE = False  # 有免费接口就设置为True
    PAY = True  # 有付费接口就设置为True
    retries = 1  # 重试次数
    delay = 1  # 重试前延迟

    # 按指数退避延迟

    # 暂且默认为需要付费

    async def search(self, question: Srequest):
        # 兜个底，别让一个adapter崩了整个asyncio.TaskGroup()
        try:
            result = await self._search(question)
            return result
        except Exception as e:
            print(f"Adapter {self.__class__.__name__} failed: {e}")
            return None

    @abstractmethod
    async def _search(self, question: Srequest):
        pass


TRUE_LIST = ["正确", "对", "✓", "√", "v", "是", "T", "t", "Y", "y", "中"]
FALSE_LIST = ["错误", "错", "✗", "叉", "×", "否", "不对", "不正确", "f", "F", "n", "N", "否定", "不中"]


# 准备写答案匹配
# 这里能做很多文章
# 打算写个笨笨的暴力
# https://scikit-learn.org.cn/view/108.html
# 查了相关聚类算法，OPTICS的效果挺好，就用它了
# 写个OPTICS聚类（不知道写不写的出来，代码低手.jpg）
async def answer_match_new(_search_request: Srequest, _adapter_ans: list[AdapterAns]) -> Sresponse:
    """
        自己写了点加ai缝合的
        单选题有选项：
            使用层次聚类或K-means（指定簇数=选项数）进行分组。
            按聚类大小降序遍历，首个包含预设选项的聚类作为答案。
        单选题没选项：
            直接选择最大聚类的众数答案。
        多选题有选项：
            聚类，（DBSCAN，HDBSCAN，OPTICS这几个可去离群值，但对只有四到五个选项的极小数据，基于密度的聚类效果可能不好，全认为是离群值或直接都丢到一个聚类中去了）
            保留所有包含预设选项的聚类（即使小簇也需检查）。
            计算最大候选簇的样本数N_max，其他候选簇若样本数≥（阈值*N_max）则并入答案。
            若无候选簇包含选项，退回无选项流程处理。
        多选题没选项:
            选择最大聚类作为核心答案。
            其他聚类若样本数≥阈值*N_max，则视为补充答案。
        判断，填空，问答:
            直接提取最大聚类的众数答案。
            可选增强：对最大聚类内答案做语义相似度过滤（如BERT编码+余弦相似度），剔除低置信样本。
        """
    # allans = Sresponse(question=_search_request.question, options=_search_request.options, type=_search_request.type)
    # allans.answer = A()

    pass


# DROP TABLE IF EXISTS `tiku`;
# CREATE TABLE tiku (
#     id INTEGER PRIMARY KEY AUTOINCREMENT,  -- 自增主键
#     question TEXT NOT NULL,               -- 问题原文（保留完整格式）
#     question_text TEXT NOT NULL,          -- 清洗后的问题（仅汉字/数字/字母）
#     question_hash TEXT NOT NULL,          -- 问题文本的哈希值
#     type INTEGER NOT NULL ,               -- 题目类型
#     options TEXT NOT NULL,                -- 选项（建议JSON格式存储）
#     full_hash TEXT NOT NULL,              -- 完整题目哈希（问题+选项）
#     source TEXT,                          -- 题目来源
#     answer TEXT NOT NULL,                 -- 正确答案
#     tags TEXT,                            -- 标签（逗号分隔或JSON）
#     created_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 新增：创建时间
#     updated_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP   -- 新增：更新时间
# );
#
# -- 创建索引优化查询
# CREATE INDEX idx_question_text ON tiku(question_text);  -- 模糊匹配索引
# CREATE UNIQUE INDEX idx_full_hash ON tiku(full_hash);   -- 哈希唯一性索引

async def local_save(_search_request: Srequest, answer: list[str]):
    # 指定要插入的列名，并使用 ? 占位符

    query = """
            INSERT INTO tiku (question, \
                              question_text, \
                              question_hash, \
                              type, \
                              options, \
                              full_hash, \
                              source, \
                              answer, \
                              tags, \
                              created_time, \
                              updated_time) \
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) \
            """

    # 构造参数列表，其中部分字段设为默认值或占位符
    md5 = hashlib.md5()
    md5.update(_search_request.question.encode('utf-8'))
    question_hash = md5.hexdigest()  # 获取十六进制格式的哈希值

    # 计算 full_hash
    full_question = _search_request.question + str(sorted(_search_request.options))
    md5_full = hashlib.md5()
    md5_full.update(full_question.encode('utf-8'))
    full_hash = md5_full.hexdigest()
    _temp = questionCAO.database.execute("SELECT full_hash, options, answer FROM tiku WHERE full_hash = ?",
                                         (full_hash,)).fetchall()  # 几种情况，全hash相同，缺答案
    # 没有选项或者没有答案需要更新

    # if full_hash in _temp and :
    #     #没有选项或者没有答案需要更新
    #     pass

    params = (
        _search_request.question,
        re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9]', '', _search_request.question),  # question_text
        question_hash,  # question_hash
        _search_request.type,  #
        str(_search_request.options),  # options
        full_hash,  # full_hash
        "unknown",  # source
        str(answer),  # answer
        "default_tag"  # tags
    )

    # 执行插入操作
    questionCAO.database.execute(query, params)
    questionCAO.database.commit()


# 感觉这一整个函数我写的就是屎一坨，ni bu la
async def answer_match(_search_request: Srequest, _adapter_ans: list[AdapterAns]) -> Sresponse:
    # _temp = {}
    answer_counts = defaultdict(int)  # 没有的默认为0
    allans = Sresponse(question=_search_request.question, options=_search_request.options, type=_search_request.type)
    allans.answer = A()
    allans.answer.allAnswer = []
    allans.answer.bestAnswer = []
    allans.answer.answerKey = []
    allans.answer.answerKeyText = ""
    allans.answer.answerIndex = []
    allans.answer.answerText = ""
    # 接下来写的非常屎，按道理if 嵌套之类的不应该超过三次，到时候再优化吧,留点注释，怕自己都不记得这一坨屎怎么写的了
    for i in _adapter_ans:
        # 先是循环每个适配器的答案
        if i.type != _search_request.type:
            continue
            # 类型不对不计入答案
        allans.answer.allAnswer.append(i.answer)
        # 把这个适配器的答案加入所有答案
        print("适配器答案:", i.answer)
        for j in i.answer:
            # 循环适配器中的每个答案
            if i.type in (0, 1):
                # 如果是单多选
                if _search_request.options is not None:
                    # 如果有选项
                    if j in _search_request.options:
                        # 如果适配器的答案在选项里
                        answer_counts[j] += 1
                else:
                    # 没选项直接加字典
                    answer_counts[j] += 1
            elif i.type == 3:
                #  判断题，适配器返回的答案是判断题TRUE/FALSE_LIST中的才加字典
                if j in TRUE_LIST:
                    answer_counts["对"] += 1
                elif j in FALSE_LIST:
                    answer_counts["错"] += 1
            else:
                #  填空和简答题
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
    # 出现最多的次数
    allans.answer.bestAnswer = [ans for ans, count in answer_counts.items() if count == _max]
    # 其实这有点问题，假如是问答题，各个题库返回的结果不同，那么_max可能就为一,所有的答案都是最佳答案
    # 把出现最多的认为是最佳答案
    if allans.answer.bestAnswer and _search_request.options:
        #  如果有选项并且最佳答案不为空
        # await local_save(_search_request, allans.answer.bestAnswer)
        #   保存答案
        for i in allans.answer.bestAnswer:
            allans.answer.answerKey.append(chr(_search_request.options.index(i) + 65))
            allans.answer.answerKeyText += (chr(_search_request.options.index(i) + 65))
            allans.answer.answerIndex.append(_search_request.options.index(i))
            if allans.answer.answerText == "":
                allans.answer.answerText = i
            else:
                allans.answer.answerText += ('#' + i)  # #是分隔符

    return allans


async def search_use(_search_request: Srequest):
    _ans = []
    _t: list = []

    if "local" in _search_request.use:
        # 使用适配器，本地local也作为一个适配器
        # 但特判
        pass
    valid_adapters = [use for use in _search_request.use if use in AdapterMeta.adapterdict]
    async with asyncio.TaskGroup() as tg:
        for adapter in valid_adapters:
            task = tg.create_task(AdapterMeta.adapterdict[adapter].search(_search_request))
            _t.append(task)

    for i in _t:
        if i.result() is not None and i.result().error is None:
            _ans.append(i.result())
    ans = await answer_match(_search_request, _ans)

    print(ans)
    return ans

# class A(BaseModel):
#     """
#         answerdata
#     """
#
#     answerKey: list[str] | None = None
#     answerKeyText: str | None = None
#     answerText: str | None = None
#     answerIndex: list[int] | None = None
#     bestAnswer: list[str] | None = None
#     allAnswer: list[list[str]] | None = None
#
#
# class Sresponse(BaseModel):
#     """
#     search response
#     """
#     plat: str | None = None
#     question: str = Field(min_length=1)
#     options: list[str] | None = None
#     type: int = Field(0, ge=0, le=4)  # 单选0多选1填空2判断3问答4
#     answer: A | None = None
