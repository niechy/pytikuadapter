import unittest
import asyncio
from unittest.mock import Mock
from models import Srequest, AdapterAns, Sresponse, A  # Replace with actual module
from core import answer_match
# Use `asynctest` or `pytest-asyncio` for async test support
class TestAnswerMatch(unittest.TestCase):
    def setUp(self):
        self.answer_match = answer_match

    def run_async(self, coro):
        """Helper to run async tests."""
        return asyncio.get_event_loop().run_until_complete(coro)


    def test_single_options(self):
        """TC_1: 单选有选项"""
        search_request = Mock(
            spec=Srequest,
            question="毛泽东思想形成的时代背景是( )",
            options=[
                "帝国主义战争与无产阶级革命成为时代主题",
                "和平与发展成为时代主题",
                "世界多极化成为时代主题",
                "经济全球化成为时代主题"
            ],
            type=0,
            token=None,
            use=None
        )
        adapter_ans = [
            Mock(spec=AdapterAns, type=0, answer=["帝国主义战争与无产阶级革命成为时代主题"]),
            Mock(spec=AdapterAns, type=0, answer=["帝国主义战争和无产阶级革命"]),
            Mock(spec=AdapterAns, type=0, answer=["帝国主义战争与无产阶级革命成为时代主题"]),
            Mock(spec=AdapterAns, type=0, answer=["战争与革命"]),
            Mock(spec=AdapterAns, type=0, answer=["帝国主义战争与无产阶级革命成为时代主题"]),
            Mock(spec=AdapterAns, type=0, answer=["帝国主义战争与无产阶级革命"])
        ]
        result = self.run_async(self.answer_match(search_request, adapter_ans))
        print(result)
        self.assertEqual(result.answer.bestAnswer, ['帝国主义战争与无产阶级革命成为时代主题'])
        # self.assertEqual(sorted(result.answer.bestAnswer), ["A", "B"])  # Both A and B appear 1 time
    def test_single_options_no(self):
        """TC_2: 单选没选项"""
        search_request = Mock(
            spec=Srequest,
            question="毛泽东思想形成的时代背景是( )",
            options=None,
            type=0,
            token=None,
            use=None
        )
        adapter_ans = [
            Mock(spec=AdapterAns, type=0, answer=["帝国主义战争与无产阶级革命成为时代主题"]),
            Mock(spec=AdapterAns, type=0, answer=["帝国主义战争和无产阶级革命"]),
            Mock(spec=AdapterAns, type=0, answer=["帝国主义战争与无产阶级革命成为时代主题"]),
            Mock(spec=AdapterAns, type=0, answer=["战争与革命"]),
            Mock(spec=AdapterAns, type=0, answer=["帝国主义战争与无产阶级革命成为时代主题"]),
            Mock(spec=AdapterAns, type=0, answer=["帝国主义战争与无产阶级革命"])
        ]
        result = self.run_async(self.answer_match(search_request, adapter_ans))
        print(result)
        self.assertEqual(result.answer.bestAnswer, ['帝国主义战争与无产阶级革命成为时代主题'])
        # self.assertEqual(sorted(result.answer.bestAnswer), ["A", "B"])  # Both A and B appear 1 time
    def test_multiple_options(self):
        """TC_3: 多选有选项"""
        search_request = Mock(
            spec=Srequest,
            question="通过劳动教育，使学生能够理解和形成马克思主义劳动观，牢固树立（）的观念。",
            options=[
                "A劳动最光荣",
                "B劳动最崇高",
                "C劳动最伟大",
                "D劳动最美丽"
            ],
            # options=None,
            type=1,
            token=None,
            use=None
        )
        adapter_ans = [
            Mock(spec=AdapterAns, type=1, answer=["A劳动最光荣","B劳动最崇高","C劳动最伟大","D劳动最美丽"]),
            Mock(spec=AdapterAns, type=1, answer=["劳动最伟大劳动最美丽劳动最光荣劳动最崇高\n \n"]),
            Mock(spec=AdapterAns, type=1, answer=["A劳动最光荣","B劳动最崇高","C劳动最伟大","D劳动最美丽"]),
            Mock(spec=AdapterAns, type=1, answer=["劳动最光荣","劳动最崇高","劳动最伟大","劳动最美丽"]),
            Mock(spec=AdapterAns, type=1, answer=["A劳动最光荣","B劳动最崇高","C劳动最伟大","D劳动最美丽"]),
            Mock(spec=AdapterAns, type=1, answer=["劳动最光荣","劳动最崇高","劳动最伟大","劳动最美丽"])
        ]
        result = self.run_async(self.answer_match(search_request, adapter_ans))
        expected = ["A劳动最光荣","B劳动最崇高","C劳动最伟大","D劳动最美丽"]
        print(result)
        self.assertEqual(sorted(result.answer.bestAnswer), sorted(expected))
    def test_multiple_options_no(self):
        """TC_4: 多选没选项"""
        search_request = Mock(
            spec=Srequest,
            question="通过劳动教育，使学生能够理解和形成马克思主义劳动观，牢固树立（）的观念。",
            options=None,
            type=1,
            token=None,
            use=None
        )
        adapter_ans = [
            Mock(spec=AdapterAns, type=1, answer=["A劳动最光荣","B劳动最崇高","C劳动最伟大","D劳动最美丽"]),
            Mock(spec=AdapterAns, type=1, answer=["劳动最伟大劳动最美丽劳动最光荣劳动最崇高\n \n"]),
            Mock(spec=AdapterAns, type=1, answer=["A劳动最光荣","B劳动最崇高","C劳动最伟大","D劳动最美丽"]),
            Mock(spec=AdapterAns, type=1, answer=["劳动最光荣","劳动最崇高","劳动最伟大","劳动最美丽"]),
            Mock(spec=AdapterAns, type=1, answer=["A劳动最光荣","B劳动最崇高","C劳动最伟大","D劳动最美丽"]),
            Mock(spec=AdapterAns, type=1, answer=["劳动最光荣","劳动最崇高","劳动最伟大","劳动最美丽"])
        ]
        result = self.run_async(self.answer_match(search_request, adapter_ans))
        expected = ["A劳动最光荣","B劳动最崇高","C劳动最伟大","D劳动最美丽"]
        print(result)
        self.assertEqual(sorted(result.answer.bestAnswer), sorted(expected))
    def test_judgment_options(self):
        """TC_5: 判断题有选项"""
        search_request = Mock(
            spec=Srequest,
            question="劳动者应该体验劳动创造美好生活，认识到劳动不分贵贱，热爱劳动，尊重普通劳动者，培养勤俭、奋斗、创新、奉献的劳动精神。",
            options=["对", "错"],
            type=3,
            token=None,
            use=None
        )
        adapter_ans = [
            Mock(spec=AdapterAns, type=3, answer=["对"]),
            Mock(spec=AdapterAns, type=3, answer=["对"]),
            Mock(spec=AdapterAns, type=3, answer=["正确"]),
            Mock(spec=AdapterAns, type=3, answer=["正确"]),
            Mock(spec=AdapterAns, type=3, answer=["错"]),
            Mock(spec=AdapterAns, type=3, answer=["正确"])
        ]
        result = self.run_async(self.answer_match(search_request, adapter_ans))
        print(result)
        self.assertEqual(result.answer.bestAnswer, ["对"])

    def test_judgment_options_no(self):
        """TC_6: 判断题无选项"""
        search_request = Mock(
            spec=Srequest,
            question="劳动者应该体验劳动创造美好生活，认识到劳动不分贵贱，热爱劳动，尊重普通劳动者，培养勤俭、奋斗、创新、奉献的劳动精神。",
            options=None,
            type=3,
            token=None,
            use=None
        )
        adapter_ans = [
            Mock(spec=AdapterAns, type=3, answer=["对"]),
            Mock(spec=AdapterAns, type=3, answer=["对"]),
            Mock(spec=AdapterAns, type=3, answer=["正确"]),
            Mock(spec=AdapterAns, type=3, answer=["正确"]),
            Mock(spec=AdapterAns, type=3, answer=["错"]),
            Mock(spec=AdapterAns, type=3, answer=["正确"])
        ]
        result = self.run_async(self.answer_match(search_request, adapter_ans))
        print(result)
        self.assertEqual(result.answer.bestAnswer, ["对"])

    # 可在核心逻辑中添加日志记录
    import logging
    logging.basicConfig(level=logging.INFO)

    # 修改run_async方法支持异常捕获
    def run_async(self, coro):
        try:
            return asyncio.get_event_loop().run_until_complete(coro)
        except Exception as e:
            logging.error(f"Async test failed: {str(e)}")
            raise
