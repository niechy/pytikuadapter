import asyncio
from fastapi import APIRouter
from models import Srequest
from core import AdapterMeta

router = APIRouter()


@router.post("/adapter-service/search")
async def search_use(_search_request: Srequest):
    _ans = []
    _t: list = []
    valid_adapters = [use for use in _search_request.use if use in AdapterMeta.adapterdict]
    print(valid_adapters)
    async with asyncio.TaskGroup() as tg:
        for adapter in valid_adapters:
            _t.append(tg.create_task(AdapterMeta.adapterdict[adapter].search(_search_request)))
    _ans = [i.result() for i in _t]
    return _ans
