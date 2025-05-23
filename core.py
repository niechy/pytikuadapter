#
# class Adapter:  #
#     pass
#
#
#
# class AdapterFactory:
#
#     adapterdict = {}
#
#     @classmethod
#     def register(cls):
#
#         def decorator(func: Adapter):
#
#             cls.adapterdict[func.__name__] = func
#             return func
#
#         return decorator
from abc import ABC, abstractmethod, ABCMeta

import aiohttp

from models import Srequest


class AdapterMeta(ABCMeta):
    adapterdict = {}

    def __new__(cls, name, bases, attrs):
        new_class = super().__new__(cls, name, bases, attrs)
        if name != 'Adapter':
            cls.adapterdict[name] = new_class()
        return new_class


class Adapter(ABC, metaclass=AdapterMeta):
    session: aiohttp.ClientSession = None

    @abstractmethod
    def search(self, question: Srequest):
        pass
