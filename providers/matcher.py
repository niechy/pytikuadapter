"""
答案匹配模块

提供适配器返回答案与题目选项的匹配功能。
解决适配器返回的答案文本与选项文本不完全一致的问题。

例如：
- 选项: "帝国主义战争与无产阶级革命成为时代主题"
- 适配器返回: "帝国主义战争和无产阶级革命"
- 需要匹配到选项 A

使用方式：
    from .matcher import build_choice_answer

    # 在适配器中直接调用，返回 A 对象
    return build_choice_answer(
        provider_name=self.name,
        answer_text="帝国主义战争和无产阶级革命",
        options=query.options,
        question_type=query.type
    )
"""

import re
from typing import List, Optional, Tuple
from model import A


def normalize_for_match(text: str) -> str:
    """
    归一化文本用于匹配

    处理：
    1. 转小写
    2. 去除标点符号
    3. 去除空格
    4. 统一"与"和"和"
    """
    if not text:
        return ""

    text = text.lower()
    # 去除标点符号，保留字母数字中文
    text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
    # 统一连接词
    text = text.replace('与', '和').replace('及', '和').replace('以及', '和')
    return text


def calculate_match_score(answer: str, option: str) -> float:
    """
    计算答案与选项的匹配分数

    Returns:
        匹配分数 0-1
    """
    if not answer or not option:
        return 0.0

    norm_answer = normalize_for_match(answer)
    norm_option = normalize_for_match(option)

    if not norm_answer or not norm_option:
        return 0.0

    # 完全相等
    if norm_answer == norm_option:
        return 1.0

    # 包含关系（答案是选项的核心部分）
    if norm_answer in norm_option:
        return len(norm_answer) / len(norm_option) * 0.95

    if norm_option in norm_answer:
        return len(norm_option) / len(norm_answer) * 0.9

    # 计算字符重叠度
    set_answer = set(norm_answer)
    set_option = set(norm_option)
    intersection = len(set_answer & set_option)
    union = len(set_answer | set_option)

    if union == 0:
        return 0.0

    jaccard = intersection / union

    # 计算最长公共子串比例
    lcs_len = _longest_common_substring_length(norm_answer, norm_option)
    lcs_ratio = lcs_len / max(len(norm_answer), len(norm_option))

    # 综合评分
    return jaccard * 0.4 + lcs_ratio * 0.6


def _longest_common_substring_length(s1: str, s2: str) -> int:
    """计算最长公共子串长度"""
    if not s1 or not s2:
        return 0

    m, n = len(s1), len(s2)
    prev = [0] * (n + 1)
    curr = [0] * (n + 1)
    max_len = 0

    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i - 1] == s2[j - 1]:
                curr[j] = prev[j - 1] + 1
                max_len = max(max_len, curr[j])
            else:
                curr[j] = 0
        prev, curr = curr, prev

    return max_len


def _match_text_to_options(
    answer_text: str,
    options: List[str],
    threshold: float = 0.5,
    is_multiple: bool = False
) -> Tuple[bool, List[str], List[int], float, Optional[str]]:
    """
    内部函数：将答案文本匹配到选项

    Returns:
        (success, matched_keys, matched_indices, confidence, error_message)
    """
    if not answer_text or not options:
        return False, [], [], 0.0, "答案或选项为空"

    # 计算每个选项的匹配分数
    scores: List[Tuple[int, str, float]] = []
    for i, option in enumerate(options):
        key = chr(65 + i)  # A, B, C, D...
        score = calculate_match_score(answer_text, option)
        scores.append((i, key, score))

    # 按分数降序排序
    scores.sort(key=lambda x: x[2], reverse=True)

    if is_multiple:
        # 多选：选择所有超过阈值的选项
        matched = [(i, k, s) for i, k, s in scores if s >= threshold]
        if not matched and scores[0][2] >= threshold * 0.6:
            matched = [scores[0]]
    else:
        # 单选：选择分数最高的
        best = scores[0]
        if best[2] >= threshold * 0.6:
            matched = [best]
        else:
            matched = []

    if not matched:
        return False, [], [], scores[0][2], f"无法匹配到选项，最高匹配度: {scores[0][2]:.2f}"

    # 按索引排序结果
    matched.sort(key=lambda x: x[0])

    return (
        True,
        [m[1] for m in matched],
        [m[0] for m in matched],
        sum(m[2] for m in matched) / len(matched),
        None
    )


def build_choice_answer(
    provider_name: str,
    answer_text: str,
    options: Optional[List[str]],
    question_type: int,
    threshold: float = 0.5
) -> A:
    """
    构建选择题答案对象（适配器主要调用此函数）

    将适配器返回的答案文本匹配到选项，返回统一的 A 对象。
    自动判断单选/多选。

    Args:
        provider_name: 适配器名称
        answer_text: 适配器返回的答案文本
        options: 题目选项列表
        question_type: 题目类型 0=单选 1=多选
        threshold: 匹配阈值

    Returns:
        A: 统一的答案对象
    """
    if not options:
        return A(
            provider=provider_name,
            type=question_type,
            success=False,
            error_type="match_error",
            error_message="题目没有选项，无法匹配"
        )

    if not answer_text:
        return A(
            provider=provider_name,
            type=question_type,
            success=False,
            error_type="match_error",
            error_message="答案文本为空"
        )

    is_multiple = question_type == 1

    success, keys, indices, confidence, error_msg = _match_text_to_options(
        answer_text, options, threshold, is_multiple
    )

    if success:
        # 根据匹配结果数量判断实际类型
        actual_type = 1 if len(keys) > 1 else 0
        return A(
            provider=provider_name,
            type=actual_type,
            choice=keys,
            success=True
        )
    else:
        return A(
            provider=provider_name,
            type=question_type,
            success=False,
            error_type="match_error",
            error_message=error_msg
        )


def build_choice_answer_from_keys(
    provider_name: str,
    answer_keys: List[str],
    answer_text: Optional[str],
    options: Optional[List[str]],
    question_type: int,
    threshold: float = 0.5
) -> A:
    """
    从选项键或文本构建选择题答案（优先使用选项键）

    优先验证选项键（A/B/C/D），如果无效则回退到文本匹配。

    Args:
        provider_name: 适配器名称
        answer_keys: 适配器返回的选项键 ['A', 'B'] 或文本答案
        answer_text: 备用的答案文本
        options: 题目选项列表
        question_type: 题目类型 0=单选 1=多选
        threshold: 匹配阈值

    Returns:
        A: 统一的答案对象
    """
    if not options:
        return A(
            provider=provider_name,
            type=question_type,
            success=False,
            error_type="match_error",
            error_message="题目没有选项，无法匹配"
        )

    # 验证选项键是否有效
    valid_keys = []
    for key in answer_keys:
        key_upper = key.upper().strip()
        if len(key_upper) == 1 and 'A' <= key_upper <= chr(64 + len(options)):
            idx = ord(key_upper) - 65
            if idx < len(options):
                valid_keys.append(key_upper)

    # 选项键有效，直接返回
    if valid_keys:
        actual_type = 1 if len(valid_keys) > 1 else 0
        return A(
            provider=provider_name,
            type=actual_type,
            choice=valid_keys,
            success=True
        )

    # 选项键无效，尝试文本匹配
    text_to_match = answer_text or ' '.join(answer_keys)
    return build_choice_answer(
        provider_name, text_to_match, options, question_type, threshold
    )
