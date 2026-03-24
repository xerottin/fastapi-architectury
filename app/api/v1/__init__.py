from api.v1 import file, mongo_test
from api.v1 import (
    user,
    project,
)
from fastapi import APIRouter

router_v1 = APIRouter()

router_v1.include_router(user.router, prefix="/users", tags=["User"])
router_v1.include_router(project.router, prefix="/project", tags=["Project"])
router_v1.include_router(file.router, prefix="/file", tags=["File"])
router_v1.include_router(mongo_test.router, prefix="/mongo_test", tags=["Mongo-Test"])
