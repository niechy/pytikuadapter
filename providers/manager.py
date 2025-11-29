
from typing import Any, Dict, List, Optional, Type
from pydantic import BaseModel
from aiohttp import ClientSession
from model import QuestionContent,Provider,QuestionRequest
from abc import ABC, abstractmethod
from logger import get_logger

log = get_logger("providers")




class Providersbase(ABC):

    name: str = ""
    session: Optional[ClientSession] = None  # 全局session，需异步初始化

    @abstractmethod
    class PParameter(BaseModel):
        #适配器需要的参数写这
        pass

    @abstractmethod
    async def _search(self, query:QuestionContent, provider:Provider) -> Any:  # 请重写此方法 喵
        pass

    async def search(self, query:QuestionContent, provider:Provider):
        try:
            return await self._search(query=query, provider=provider)
        except Exception as e:
            log.error(f"Adapter {self.name} internal error: {e}")
            raise
    @classmethod
    async def init_session(cls):
        if cls.session is None:
            cls.session = ClientSession()

    @classmethod
    async def close_session(cls):
        if cls.session is not None:
            await cls.session.close()
            cls.session = None

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if cls is Providersbase:
            return
        if not getattr(cls, "name", None):
            return
        _registry.register(cls)



class ProviderRegistry:
    """Registry holding all plugins by their unique key."""

    def __init__(self) -> None:
        self._list: Dict[str, Type[Providersbase]] = {}
        self._achievelist: Dict[str, Providersbase] = {}

    def register(self, plugin_cls: Type["Providersbase"]) -> None:

        self._list[plugin_cls.name] = plugin_cls
        self._achievelist[plugin_cls.name] = plugin_cls()

    def get(self, name: str) -> Optional[Type["Providersbase"]]:
        return self._list.get(name, None)
    def get_achieve(self, name: str) -> Optional["Providersbase"]:
        return self._achievelist.get(name,None)


    def all(self) -> Dict[str, Type["Providersbase"]]:

        return dict(self._list)
    def all_achieve(self) -> Dict[str, Providersbase]:
        return dict(self._achievelist)
_registry = ProviderRegistry()
class ProvidersManager:
    """High-level manager to validate per-plugin sections and inspect schemas."""

    def available_plugins(self) -> List[str]:
        return list(_registry.all().keys())


    def get_adapter(self,name: str):
        return _registry.get(name)
    def get_adapter_achieve(self,name: str):
        return _registry.get_achieve(name)


__all__ = [
    "Providersbase",
    "ProviderRegistry",
    "ProvidersManager",
]
