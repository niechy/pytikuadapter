from contextlib import asynccontextmanager
import aiohttp
from fastapi import FastAPI
from core import AdapterMeta
from routers import router
import adapter  # pylint: disable=unused-import # 别动这行

@asynccontextmanager
async def lifespan(_app: FastAPI):

    session = aiohttp.ClientSession()
    for _adapter in AdapterMeta.adapterdict.values():
        _adapter=_adapter()#  实例化
        _adapter.session = session
    yield
    for _adapter in AdapterMeta.adapterdict.values():
        del _adapter
    await session.close()


app = FastAPI(lifespan=lifespan)
# app = FastAPI()
app.include_router(router)
