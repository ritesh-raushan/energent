from fastapi import APIRouter

from app.api.simulation import router as simulation_router

api_router = APIRouter(prefix="/api")

api_router.include_router(simulation_router)
