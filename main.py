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
        AdapterMeta.adapterdict[_adapter.__name__] = _adapter()
        _adapter.session = session
    yield
    await session.close()


app = FastAPI(lifespan=lifespan)
# app = FastAPI()
app.include_router(router)
