"""
题库适配器服务入口
"""
from dotenv import load_dotenv
load_dotenv()

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
import uvicorn

from database import init_database, close_database
from services.rate_limit import limiter
from services.provider_order import sync_provider_order
from providers.manager import ProvidersManager, Providersbase
from services.routers import (
    auth_router,
    tokens_router,
    providers_router,
    providers_token_router,
    search_router,
)
from logger import get_logger

log = get_logger("main")
_mgr = ProvidersManager()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    log.info("正在初始化数据库...")
    await init_database()
    log.info("数据库初始化完成")

    await Providersbase.init_session()
    await sync_provider_order()

    yield

    await Providersbase.close_session()
    await close_database()
    log.info("应用已关闭")


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(tokens_router)
app.include_router(providers_router)
app.include_router(providers_token_router)
app.include_router(search_router)


if __name__ == '__main__':
    uvicorn.run('main:app', host="127.0.0.1", port=8060, log_level='info')
