from models import AdapterAns, ErrorType, Srequest
from core import Adapter


class Local(Adapter):  # pylint: disable=too-few-public-methods
    """
        FREE (bool): 表示有无免费模式，默认值为False
        PAY (bool): 表示有无付费模式，默认值为True
    """
    FREE = False
    PAY = True

    async def search(self, question: Srequest):
        pass
