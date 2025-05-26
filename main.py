from contextlib import asynccontextmanager
import aiohttp
from fastapi import FastAPI
from core import AdapterMeta
from routers import router
import adapter  # pylint: disable=unused-import # 别动这行

@asynccontextmanager
async def lifespan(_app: FastAPI):
    for _adapter in AdapterMeta.adapterdict.values():
        _adapter.session = aiohttp.ClientSession()
    yield
    for _adapter in AdapterMeta.adapterdict.values():
        await _adapter.session.close()


app = FastAPI(lifespan=lifespan)
# app = FastAPI()
app.include_router(router)
