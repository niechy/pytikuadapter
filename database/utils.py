"""
数据库工具函数

提供题目内容和选项的归一化处理，用于模糊匹配。
解决以下问题：
1. 标点符号差异（"你好。" vs "你好"）
2. 空格差异（"你 好" vs "你好"）
3. 大小写差异（"Hello" vs "hello"）
4. 选项顺序差异（["A你好", "B你坏"] vs ["A你坏", "B你好"]）
"""

import re
import hashlib
import json
from typing import List, Optional, Dict, Any


def normalize_text(text: str) -> str:
    """
    归一化文本内容

    处理步骤：
    1. 转小写
    2. 去除所有标点符号
    3. 去除所有空格和换行符
    4. 去除多余的空白字符

    Args:
        text: 原始文本

    Returns:
        归一化后的文本

    Example:
        >>> normalize_text("你好，世界！")
        "你好世界"
        >>> normalize_text("Hello World.")
        "helloworld"
    """
    if not text:
        return ""

    # 转小写
    text = text.lower()

    # 去除所有标点符号（中英文）
    # 保留字母、数字、中文字符
    text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)

    # 去除所有空格
    text = re.sub(r'\s+', '', text)

    return text


def normalize_options(options: Optional[List[str]]) -> Optional[List[str]]:
    """
    归一化选项列表

    处理步骤：
    1. 对每个选项进行文本归一化
    2. 按归一化后的内容排序（解决选项顺序变化问题）
    3. 返回排序后的归一化选项列表

    Args:
        options: 原始选项列表

    Returns:
        归一化并排序后的选项列表，如果输入为None则返回None

    Example:
        >>> normalize_options(["A. 你好", "B. 你坏"])
        ["a你好", "b你坏"]
        >>> normalize_options(["B. 你坏", "A. 你好"])  # 顺序变化
        ["a你好", "b你坏"]  # 排序后结果相同
    """
    if not options:
        return None

    # 归一化每个选项
    normalized = [normalize_text(opt) for opt in options]

    # 排序（确保选项顺序一致）
    normalized.sort()

    return normalized


def compute_config_hash(config: Dict[str, Any]) -> str:
    """
    计算provider配置的哈希值

    用于区分同一provider使用不同配置时的缓存。
    例如：Like知识库使用不同的llm_model可能返回不同答案。

    Args:
        config: provider配置字典

    Returns:
        配置的MD5哈希值（16进制字符串）

    Example:
        >>> compute_config_hash({"key": "abc", "model": "gpt-4"})
        "5d41402abc4b2a76b9719d911017c592"
    """
    # 将配置转为排序后的JSON字符串（确保顺序一致）
    config_str = json.dumps(config, sort_keys=True, ensure_ascii=False)

    # 计算MD5哈希
    return hashlib.md5(config_str.encode('utf-8')).hexdigest()


def calculate_similarity(text1: str, text2: str) -> float:
    """
    计算两个文本的相似度（简单版本）

    使用字符级别的Jaccard相似度。
    后续可以升级为更复杂的算法（如编辑距离、余弦相似度等）。

    Args:
        text1: 第一个文本
        text2: 第二个文本

    Returns:
        相似度分数，范围 [0, 1]，1表示完全相同

    Example:
        >>> calculate_similarity("你好世界", "你好世界")
        1.0
        >>> calculate_similarity("你好", "你坏")
        0.5
    """
    if not text1 or not text2:
        return 0.0

    # 转为字符集合
    set1 = set(text1)
    set2 = set(text2)

    # 计算Jaccard相似度
    intersection = len(set1 & set2)
    union = len(set1 | set2)

    if union == 0:
        return 0.0

    return intersection / union


def find_best_match_threshold() -> float:
    """
    返回模糊匹配的阈值

    当两个题目的相似度 >= 该阈值时，认为是同一题目。
    可以根据实际使用情况调整。

    Returns:
        相似度阈值，默认 0.85
    """
    return 0.85


def is_similar_question(
    content1: str,
    options1: Optional[List[str]],
    content2: str,
    options2: Optional[List[str]],
    threshold: Optional[float] = None
) -> bool:
    """
    判断两个题目是否相似

    综合考虑题目内容和选项的相似度。

    Args:
        content1: 第一个题目内容
        options1: 第一个题目选项
        content2: 第二个题目内容
        options2: 第二个题目选项
        threshold: 相似度阈值，默认使用 find_best_match_threshold()

    Returns:
        是否相似
    """
    if threshold is None:
        threshold = find_best_match_threshold()

    # 归一化题目内容
    norm_content1 = normalize_text(content1)
    norm_content2 = normalize_text(content2)

    # 计算内容相似度
    content_similarity = calculate_similarity(norm_content1, norm_content2)

    # 如果内容相似度不够，直接返回False
    if content_similarity < threshold:
        return False

    # 如果都没有选项，只看内容相似度
    if not options1 and not options2:
        return True

    # 如果一个有选项一个没有，认为不相似
    if bool(options1) != bool(options2):
        return False

    # 归一化选项
    norm_options1 = normalize_options(options1)
    norm_options2 = normalize_options(options2)

    # 比较归一化后的选项（已排序，可以直接比较）
    # 这里使用严格相等，因为选项变化可能影响答案
    return norm_options1 == norm_options2
