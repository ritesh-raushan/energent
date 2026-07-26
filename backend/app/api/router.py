from fastapi import APIRouter

from app.api.agent import router as agent_router
from app.api.llm import router as llm_router
from app.api.loop import router as loop_router
from app.api.simulation import router as simulation_router

api_router = APIRouter(prefix="/api")

api_router.include_router(simulation_router)
api_router.include_router(llm_router)
api_router.include_router(loop_router)
api_router.include_router(agent_router)
