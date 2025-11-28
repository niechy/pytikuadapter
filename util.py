TRUE_LIST = [1,"正确", "对", "✓", "√", "v", "是", "T", "t", "Y", "y", "中"]
FALSE_LIST = [0,"错误", "错", "✗", "叉", "×", "否", "不对", "不正确", "f", "F", "n", "N", "否定", "不中"]

def judgement_true(ans: bool) -> bool | None:
    """
    :param ans: 判断题的答案文本
    :return: True or False
    """
    if ans in TRUE_LIST:
        return True
    elif ans in FALSE_LIST:
        return False