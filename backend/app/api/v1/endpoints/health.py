from fastapi import APIRouter

from app.core.config import settings

router = APIRouter()


@router.get("/health")
def health_check() -> dict:
    return {
        "status": "ok",
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
    }
