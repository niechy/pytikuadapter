from contextlib import asynccontextmanager
import aiohttp
from fastapi import FastAPI
from core import Adapter
from routers import router
import adapter  # pylint: disable=unused-import # 别动这行


@asynccontextmanager
async def lifespan(_app: FastAPI):
    Adapter.session = aiohttp.ClientSession()
    async with Adapter.session:
        yield


app = FastAPI(lifespan=lifespan)
app.include_router(router)
