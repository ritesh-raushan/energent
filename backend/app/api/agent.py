import logging

from fastapi import APIRouter, HTTPException

from app.services.mcp.agent import run_iterative_agent

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agent"])


@router.post("/agent/run")
def run_agent_endpoint(request: dict) -> dict:
    objective = request.get("objective", "Run closed-loop building energy optimization")
    context = request.get("context", {})
    max_rounds = request.get("max_rounds", 5)

    try:
        result = run_iterative_agent(objective, context, max_rounds=max_rounds)
    except Exception as e:
        logger.error("Agent run failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Agent failed: {e}")

    return {
        "success": result.success,
        "converged": result.converged,
        "convergence_reason": result.convergence_reason,
        "steps": [
            {
                "iteration": step.iteration,
                "round": step.round,
                "tool": step.tool,
                "arguments": step.arguments,
                "result": step.result,
            }
            for step in result.steps
        ],
        "rounds": [
            {
                "round_number": r.round_number,
                "energy_savings_kwh": r.energy_savings_kwh,
                "energy_savings_pct": r.energy_savings_pct,
                "pmv_change": r.pmv_change,
                "ppd_change": r.ppd_change,
                "ecm": r.ecm,
                "baseline_analysis": r.baseline_analysis,
                "optimized_analysis": r.optimized_analysis,
            }
            for r in result.rounds
        ],
        "final_result": result.final_result,
        "error": result.error,
    }