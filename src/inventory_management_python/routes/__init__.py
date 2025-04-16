from fastapi.routing import APIRouter

from inventory_management_python.routes.auth import router as auth_router

router = APIRouter()

router.include_router(auth_router, prefix="/auth", tags=["auth"])
