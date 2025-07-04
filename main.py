from contextlib import asynccontextmanager
import aiohttp
import uvicorn
import log
from config import Configs
from loguru import logger
from fastapi import FastAPI
from core import AdapterMeta
from log import loginit
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
app.include_router(router)
if __name__ == '__main__':

    config=Configs("config/config_template.toml")
    print(config.config)
    loginit(config.config["level"])
    logger.info("主程序启动")
    uvicorn.run('main:app', host=config.config["server"]["host"], port=config.config["server"]["port"], log_level='info')
