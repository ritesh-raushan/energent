import logging

from fastapi import APIRouter, HTTPException

from app.services.loop.runner import run_loop

logger = logging.getLogger(__name__)

router = APIRouter(tags=["loop"])


@router.post("/loop/run")
def run_closed_loop() -> dict:
    try:
        result = run_loop()
    except Exception as e:
        logger.error("Closed-loop failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Closed-loop failed: {e}")

    return {
        "status": "success",
        "baseline": {
            "summary": result.baseline_analysis.energy_breakdown.model_dump(),
            "score": result.baseline_analysis.overall_score,
            "recommendations": [r.model_dump() for r in result.baseline_analysis.recommendations],
        },
        "optimized": {
            "summary": result.optimized_analysis.energy_breakdown.model_dump(),
            "score": result.optimized_analysis.overall_score,
            "recommendations": [r.model_dump() for r in result.optimized_analysis.recommendations],
        },
        "ecm": result.ecm.model_dump(),
        "savings": {
            "kwh": result.energy_savings_kwh,
            "percent": result.energy_savings_pct,
            "baseline_kwh": result.baseline_analysis.energy_breakdown.total_electricity_kwh,
            "optimized_kwh": result.optimized_analysis.energy_breakdown.total_electricity_kwh,
        },
    }
