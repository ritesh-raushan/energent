import logging
import shutil
from pathlib import Path

from pydantic import BaseModel

from app.config import settings
from app.services.analysis.engine import analyze
from app.services.analysis.models import AnalysisResult
from app.services.energyplus.models import SimulationConfig, SimulationResult
from app.services.energyplus.parser import parse_csv
from app.services.energyplus.runner import EnergyPlusRunner
from app.services.loop.ecm_generator import ECMResult, generate_ecms
from app.services.loop.idf_parser import IDFData, modify_idf, parse_idf

logger = logging.getLogger(__name__)


class LoopResult(BaseModel):
    baseline_analysis: AnalysisResult
    optimized_analysis: AnalysisResult
    ecm: ECMResult
    baseline_simulation: SimulationResult
    optimized_simulation: SimulationResult
    energy_savings_kwh: float = 0.0
    energy_savings_pct: float = 0.0
    modified_idf_path: str = ""


def run_loop() -> LoopResult:
    idf_path = Path(settings.ENERGYPLUS_IDF_PATH)
    output_dir = Path(settings.ENERGYPLUS_OUTPUT_DIR)

    logger.info("=== Starting Closed-Loop Optimization ===")

    logger.info("Step 1: Parsing IDF file")
    idf_data = parse_idf(idf_path)
    logger.info("Current setpoints: heating=%s°C, cooling=%s°C", idf_data.heating_occupied_c, idf_data.cooling_occupied_c)

    logger.info("Step 2: Running baseline simulation")
    baseline_sim = _run_simulation(idf_path)
    if not baseline_sim.success:
        raise RuntimeError(f"Baseline simulation failed: {baseline_sim.stderr}")

    logger.info("Step 3: Parsing baseline results")
    baseline_analysis = _parse_and_analyze(baseline_sim.csv_path)

    logger.info("Step 4: Generating ECMs")
    ecm = generate_ecms(idf_data, baseline_analysis)
    logger.info("Proposed ECMs: heating=%s°C, cooling=%s°C", ecm.heating_occupied_c, ecm.cooling_occupied_c)

    logger.info("Step 5: Modifying IDF file")
    modified_idf_path = output_dir / "modified.idf"
    modify_idf(
        idf_path=idf_path,
        output_path=modified_idf_path,
        heating_occupied_c=ecm.heating_occupied_c,
        cooling_occupied_c=ecm.cooling_occupied_c,
    )

    logger.info("Step 6: Running optimized simulation")
    optimized_sim = _run_simulation(modified_idf_path)
    if not optimized_sim.success:
        raise RuntimeError(f"Optimized simulation failed: {optimized_sim.stderr}")

    logger.info("Step 7: Parsing optimized results")
    optimized_analysis = _parse_and_analyze(optimized_sim.csv_path)

    savings_kwh = baseline_analysis.energy_breakdown.total_electricity_kwh - optimized_analysis.energy_breakdown.total_electricity_kwh
    savings_pct = (savings_kwh / baseline_analysis.energy_breakdown.total_electricity_kwh * 100) if baseline_analysis.energy_breakdown.total_electricity_kwh > 0 else 0.0

    logger.info("=== Loop Complete ===")
    logger.info("Baseline: %.2f kWh | Optimized: %.2f kWh | Savings: %.2f kWh (%.1f%%)",
                baseline_analysis.energy_breakdown.total_electricity_kwh,
                optimized_analysis.energy_breakdown.total_electricity_kwh,
                savings_kwh, savings_pct)

    return LoopResult(
        baseline_analysis=baseline_analysis,
        optimized_analysis=optimized_analysis,
        ecm=ecm,
        baseline_simulation=baseline_sim,
        optimized_simulation=optimized_sim,
        energy_savings_kwh=round(savings_kwh, 2),
        energy_savings_pct=round(savings_pct, 1),
        modified_idf_path=str(modified_idf_path),
    )


def _run_simulation(idf_path: Path) -> SimulationResult:
    config = SimulationConfig(
        energyplus_exe=Path(settings.ENERGYPLUS_EXE_PATH),
        idf_path=idf_path,
        weather_path=Path(settings.ENERGYPLUS_WEATHER_PATH),
        output_dir=Path(settings.ENERGYPLUS_OUTPUT_DIR),
    )
    runner = EnergyPlusRunner(config)
    return runner.run()


def _parse_and_analyze(csv_path: Path | None) -> AnalysisResult:
    if csv_path is None or not csv_path.exists():
        raise FileNotFoundError("CSV output not found after simulation")
    parsed_data = parse_csv(csv_path)
    return analyze(parsed_data)
