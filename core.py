import asyncio
from abc import ABC, abstractmethod, ABCMeta
import aiohttp
from models import Srequest


class AdapterMeta(ABCMeta):
    adapterdict = {}

    def __new__(mcs, name, bases, attrs):
        new_class = super().__new__(mcs, name, bases, attrs)
        if name != 'Adapter':
            mcs.adapterdict[name] = new_class()
        return new_class


class Adapter(ABC, metaclass=AdapterMeta):
    session: aiohttp.ClientSession = None
    OPTION = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "G": 6, "H": 7, "I": 8, "J": 9, "K": 10, "L": 11, "M": 12,
              "N": 13, }
    @abstractmethod
    async def search(self, question: Srequest):
        pass


async def search_use(_search_request: Srequest):
    _ans = []
    _t: list = []
    valid_adapters = [use for use in _search_request.use if use in AdapterMeta.adapterdict]
    async with asyncio.TaskGroup() as tg:
        for adapter in valid_adapters:
            _t.append(tg.create_task(AdapterMeta.adapterdict[adapter].search(_search_request)))
    _ans = [i.result() for i in _t]
    print(_ans)
    return _ans
