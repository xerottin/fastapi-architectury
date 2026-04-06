from api import check_health
from api.v1 import router_v1
from fastapi import APIRouter

router = APIRouter()
router.include_router(check_health.router, prefix="/health", tags=["Health"])
router.include_router(router_v1)
