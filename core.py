from collections import defaultdict
from collections import Counter
from operator import truediv
from typing import Dict

from model import A, QuestionContent, Res, UnifiedAnswer


# TRUE_LIST = [1,"正确", "对", "✓", "√", "v", "是", "T", "t", "Y", "y", "中"]
# FALSE_LIST = [0,"错误", "错", "✗", "叉", "×", "否", "不对", "不正确", "f", "F", "n", "N", "否定", "不中"]

# def normalize_choices(ans: list[A], type: int = 0):
#这个函数按道理是用来标准化各个题库的答案格式的，比如把小写字母转成大写字母之类的，但已经在model中限定了格式，所以这里其实不需要做什么
#     # [{'Like知识库': A(type=0, choice=['A'], judegement=None, text=None)}]
#
#     if type == 0 or type == 1:
#         for a in ans:
#             if a.choice:
#                 a.choice = [str(ch).strip().upper() for ch in a.choice]
#     return ans
    # elif type==2:
    #     return ans
    # elif type==3:
    #     # 在定义A的时候已经限定了bool类型，不需要再转换
    #     return ans
    # elif type==4:
    #     return ans


def collect_true_answer(question: QuestionContent, ans: list[A]) -> A | None:
    """
    从多个provider的答案中聚合出最佳答案

    只聚合成功的答案（success=True），忽略失败的答案
    """
    # 过滤出成功的答案
    successful_ans = [a for a in ans if a.success]

    if not successful_ans:
        # 没有成功的答案，返回空答案
        return A(provider="TrueAnswer", type=question.type, choice=None, success=False)

    counter = Counter()
    if question.type == 0 or question.type == 1:  # 单选/多选：聚合选择项
        for choice in successful_ans:
            if choice.choice:
                counter.update([tuple(sorted(choice.choice))])  # 排序确保 ['A','B'] 和 ['B','A'] 被视为相同
        if not counter:
            return A(provider="TrueAnswer", type=question.type, choice=None)
        return A(provider="TrueAnswer", type=question.type, choice=list(counter.most_common(1)[0][0]))
    elif question.type == 2 or question.type == 4:  # 填空/问答：聚合文本
        for text in successful_ans:
            if text.text:
                counter.update([tuple(text.text)])  # 填空
        if not counter:
            return A(provider="TrueAnswer", type=question.type, text=None)
        return A(provider="TrueAnswer", type=question.type, text=list(counter.most_common(1)[0][0]))
    else:  # 判断：聚合布尔
        for judgement in successful_ans:
            if judgement.judgement is not None:
                counter.update([judgement.judgement])
        if not counter:
            return A(provider="TrueAnswer", type=question.type, judgement=None)
        return A(provider="TrueAnswer", type=question.type, judgement=counter.most_common(1)[0][0])


def construct_res(query: QuestionContent, ans: list[A]):
    """
    构造统一的响应结果

    Args:
        query: 题目内容
        ans: 所有provider的返回结果（包括成功和失败）

    Returns:
        Res: 统一的响应对象
    """
    # 聚合答案（只聚合成功的答案）
    trueans = collect_true_answer(query, ans)

    UA = None

    if query.type == 0 or query.type == 1:  # 单选多选
        answerIndex = [ord(choice) - 65 for choice in trueans.choice] if trueans.choice else []
        bestAnswer = [query.options[index] for index in answerIndex] if trueans.choice else []
        UA = UnifiedAnswer(
            answerKey=trueans.choice if trueans.choice else [],
            answerKeyText=''.join(trueans.choice) if trueans.choice else "",
            answerIndex=answerIndex,
            bestAnswer=bestAnswer,
            answerText='#@#'.join(bestAnswer) if trueans.choice else ""
        )
    elif query.type == 2 or query.type == 4:  # 填空/问答
        UA = UnifiedAnswer(
            answerKey=[],
            answerKeyText="",
            answerIndex=[],
            bestAnswer=trueans.text if trueans.text else [],
            answerText='#@#'.join(trueans.text) if trueans.text else ""
        )
    elif query.type == 3:  # 判断
        bestAnswer = []
        if trueans.judgement is True:
            bestAnswer = ["对"]
        elif trueans.judgement is False:
            bestAnswer = ["错"]
        UA = UnifiedAnswer(
            answerKey=[],
            answerKeyText="",
            answerIndex=[],
            bestAnswer=bestAnswer,
            answerText=bestAnswer[0] if bestAnswer else ""
        )

    # 统计成功和失败的provider数量
    successful_count = len([a for a in ans if a.success])
    failed_count = len([a for a in ans if not a.success])

    return Res(
        query=query,
        unified_answer=UA,
        provider_answers=ans,  # 包含所有provider的结果（成功和失败）
        successful_providers=successful_count,
        failed_providers=failed_count,
        total_providers=len(ans)
    )
