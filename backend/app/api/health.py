from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check() -> dict:
    return {
        "status": "healthy",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
