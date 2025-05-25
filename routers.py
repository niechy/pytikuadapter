from fastapi import APIRouter
from models import Srequest
from core import search_use


router = APIRouter()


@router.post("/adapter-service/search")
async def search_use_route(_search_request: Srequest):
    return await search_use(_search_request)
