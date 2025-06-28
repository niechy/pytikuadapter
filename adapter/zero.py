import requests
import json
import re
from models import AdapterAns, ErrorType, Srequest
from core import Adapter


class Zero(Adapter):  # pylint: disable=too-few-public-methods
    """
    Zero题库API适配器，用于与https://www.anyzero.org/user/api.php接口交互
    """
    url: str = "https://www.anyzero.org/user/api.php"
    FREE = True
    PAY = True
    header = {"Content-Type": "application/json"}

    async def _search(self, question: Srequest):
        """
        异步查询题库API获取问题答案

        Args:
            question: Srequest对象，包含问题文本和请求选项

        Returns:
            AdapterAns对象，包含查询结果或错误信息
        """
        # 构建请求参数
        params = {
            "token": question.use["Zero"].token,
            "q": question.question
        }

        # 初始化响应对象
        ans: AdapterAns = AdapterAns(None, question.type, None)
        ans.answer = []

        try:
            # 发送异步HTTP请求
            async with self.session.get(url=self.url, headers=self.header, params=params) as response:
                # 打印原始响应文本用于调试
                raw_text = await response.text()
                print(f"API原始响应: {raw_text}")

                # 处理HTTP状态码
                if response.status == 200:
                    try:
                        # 尝试解析JSON响应
                        # 注意：尽管服务器返回Content-Type为text/html，但实际返回JSON格式
                        req = json.loads(raw_text)

                        # 检查API返回状态码
                        if req["code"] == 1:
                            # 提取答案字段
                            if "answer" in req:
                                # 使用正则表达式匹配多种分隔符
                                # 支持的分隔符：=== ; --- # ### 等
                                # 正则表达式说明：使用 | 连接多个分隔符，确保最长匹配优先
                                separators = ['===', ';', '---', '#', '###']
                                # 转义特殊正则字符并按长度排序，确保最长分隔符优先匹配
                                separators_sorted = sorted(separators, key=len, reverse=True)
                                separator_pattern = '|'.join(re.escape(sep) for sep in separators_sorted)

                                # 使用正则表达式分割答案
                                ans.answer = re.split(separator_pattern, req["answer"])
                                # 过滤空字符串
                                ans.answer = [a.strip() for a in ans.answer if a.strip()]

                                print(f"成功获取答案: {ans.answer}")
                            else:
                                ans.error = ErrorType.TARGET_NO_ANSWER
                                print("API返回结果中缺少answer字段")
                        else:
                            # API返回非成功状态码
                            ans.error = ErrorType.TARGET_NO_ANSWER
                            print(f"API返回错误状态: {req}")

                    except json.JSONDecodeError as e:
                        # JSON解析失败
                        ans.error = ErrorType.PARSER_JSON
                        print(f"JSON解析错误: {e}, 原始文本: {raw_text}")
                else:
                    # HTTP状态码非200
                    ans.error = ErrorType.TARGET_SERVER_ERROR
                    print(f"HTTP请求失败，状态码: {response.status}")

        except Exception as e:
            # 处理其他异常
            ans.error = ErrorType.TARGET_SERVER_ERROR
            print(f"网络请求异常: {e}")

        return ans