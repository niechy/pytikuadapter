from __future__ import annotations
from providers.manager import ProvidersManager, Providersbase, get_adapter
from model import QS
from providers import like  # noqa: F401
import asyncio

async def main():
    mgr = ProvidersManager()
    await Providersbase.init_session()
    LikeClass = get_adapter("Like知识库")
    like_instance = LikeClass()
    print(like_instance)
    schema = LikeClass.Configs

    # 示例：从环境变量读取 API key
    import os
    api_key = os.getenv("LIKE_API_KEY", "your-api-key-here")

    i = await like_instance._search(
        QS(
            question='通过劳动教育，使学生能够理解和形成马克思主义劳动观，牢固树立（）的观念。',
            options=["A劳动最光荣"],
            type=1
        ),
        args=schema(key=api_key)
    )
    print(i)
    await Providersbase.close_session()


if __name__ == "__main__":
    asyncio.run(main())
