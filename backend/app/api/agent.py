import logging

from fastapi import APIRouter, HTTPException

from app.services.mcp.agent import run_agent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agent"])


@router.post("/agent/run")
def run_agent_endpoint(request: dict) -> dict:
    objective = request.get("objective", "Run closed-loop building energy optimization")
    context = request.get("context", {})

    try:
        result = run_agent(objective, context)
    except Exception as e:
        logger.error("Agent run failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Agent failed: {e}")

    return {
        "success": result.success,
        "steps": [
            {
                "iteration": step.iteration,
                "tool": step.tool,
                "arguments": step.arguments,
                "result": step.result,
            }
            for step in result.steps
        ],
        "final_result": result.final_result,
        "error": result.error,
    }