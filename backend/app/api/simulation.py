import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

from app.services.analysis.engine import analyze
from app.services.energyplus.parser import parse_csv
from app.services.energyplus.runner import EnergyPlusRunner

logger = logging.getLogger(__name__)

router = APIRouter(tags=["simulation"])


@router.post("/simulation/run")
def run_simulation() -> dict:
    try:
        runner = EnergyPlusRunner()
        sim_result = runner.run()
    except Exception as e:
        logger.error("Failed to run simulation: %s", e)
        raise HTTPException(status_code=500, detail=f"Simulation failed: {e}")

    if not sim_result.success:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "EnergyPlus simulation failed",
                "return_code": sim_result.return_code,
                "stderr": sim_result.stderr,
                "stdout": sim_result.stdout,
            },
        )

    if sim_result.csv_path is None or not sim_result.csv_path.exists():
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Simulation completed but CSV output not found",
                "output_dir": str(sim_result.output_dir),
            },
        )

    try:
        parsed_data = parse_csv(sim_result.csv_path)
    except Exception as e:
        logger.error("Failed to parse simulation output: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to parse simulation output: {e}")

    try:
        analysis = analyze(parsed_data)
    except Exception as e:
        logger.error("Failed to analyze simulation data: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to analyze simulation data: {e}")

    return {
        "status": "success",
        "simulation": {
            "idf_path": str(sim_result.idf_path),
            "weather_path": str(sim_result.weather_path),
            "output_dir": str(sim_result.output_dir),
            "csv_path": str(sim_result.csv_path),
        },
        "summary": parsed_data.summary.model_dump(),
        "analysis": analysis.model_dump(),
        "record_count": parsed_data.record_count,
    }
