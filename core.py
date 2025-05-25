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


class Adapter(ABC, metaclass=AdapterMeta):  # py
    session: aiohttp.ClientSession = None

    @abstractmethod
    async def search(self, question: Srequest):
        pass
