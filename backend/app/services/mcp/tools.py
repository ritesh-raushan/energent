import logging
import subprocess
from pathlib import Path

from pydantic import BaseModel

from app.config import settings
from app.services.analysis.engine import analyze
from app.services.analysis.thermal_comfort import calculate_pmv
from app.services.energyplus.models import SimulationConfig, SimulationResult
from app.services.energyplus.parser import parse_csv
from app.services.energyplus.runner import EnergyPlusRunner
from app.services.loop.ecm_generator import generate_ecms
from app.services.loop.idf_parser import modify_idf, parse_idf as parse_idf_file
from app.services.loop.runner import _run_simulation

logger = logging.getLogger(__name__)


class Tool:
    def __init__(self, name: str, description: str, handler, parameters: dict):
        self.name = name
        self.description = description
        self.handler = handler
        self.parameters = parameters

    def to_openai_format(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


def parse_idf(idf_path: str) -> dict:
    """Parse an IDF file to extract thermostat setpoint schedules."""
    try:
        data = parse_idf_file(Path(idf_path))
        return {
            "success": True,
            "heating_occupied_c": data.heating_occupied_c,
            "heating_unoccupied_c": data.heating_unoccupied_c,
            "cooling_occupied_c": data.cooling_occupied_c,
            "cooling_unoccupied_c": data.cooling_unoccupied_c,
        }
    except Exception as e:
        logger.error("parse_idf failed: %s", e)
        return {"success": False, "error": str(e)}


def run_simulation(
    idf_path: str,
    weather_path: str | None = None,
    output_dir: str | None = None,
) -> dict:
    """Run EnergyPlus simulation."""
    try:
        config = SimulationConfig(
            energyplus_exe=Path(settings.ENERGYPLUS_EXE_PATH),
            idf_path=Path(idf_path),
            weather_path=Path(weather_path or settings.ENERGYPLUS_WEATHER_PATH),
            output_dir=Path(output_dir or settings.ENERGYPLUS_OUTPUT_DIR),
        )
        runner = EnergyPlusRunner(config)
        result: SimulationResult = runner.run()
        return {
            "success": result.success,
            "csv_path": str(result.csv_path) if result.csv_path else None,
            "stdout": result.stdout[-500:] if result.stdout else "",
            "stderr": result.stderr[-500:] if result.stderr else "",
            "return_code": result.return_code,
        }
    except Exception as e:
        logger.error("run_simulation failed: %s", e)
        return {"success": False, "error": str(e)}


def analyze_results(csv_path: str) -> dict:
    """Parse CSV output and compute energy/comfort metrics."""
    try:
        parsed = parse_csv(Path(csv_path))
        analysis = analyze(parsed)
        return {
            "success": True,
            "energy_breakdown": analysis.energy_breakdown.model_dump(),
            "peak_load": analysis.peak_load.model_dump(),
            "hvac_summary": analysis.hvac_summary.model_dump(),
            "thermal_comfort": analysis.thermal_comfort.model_dump(),
            "recommendations": [r.model_dump() for r in analysis.recommendations],
            "overall_score": analysis.overall_score,
            "total_potential_savings_kwh": analysis.total_potential_savings_kwh,
        }
    except Exception as e:
        logger.error("analyze_results failed: %s", e)
        return {"success": False, "error": str(e)}


def modify_setpoints(
    idf_path: str,
    output_path: str,
    heating_occupied_c: float | None = None,
    cooling_occupied_c: float | None = None,
    heating_unoccupied_c: float | None = None,
    cooling_unoccupied_c: float | None = None,
) -> dict:
    """Modify thermostat setpoint schedules in an IDF file."""
    try:
        out_path = modify_idf(
            idf_path=Path(idf_path),
            output_path=Path(output_path),
            heating_occupied_c=heating_occupied_c,
            cooling_occupied_c=cooling_occupied_c,
        )
        new_data = parse_idf_file(out_path)
        return {
            "success": True,
            "output_path": str(out_path),
            "heating_occupied_c": new_data.heating_occupied_c,
            "heating_unoccupied_c": new_data.heating_unoccupied_c,
            "cooling_occupied_c": new_data.cooling_occupied_c,
            "cooling_unoccupied_c": new_data.cooling_unoccupied_c,
        }
    except Exception as e:
        logger.error("modify_setpoints failed: %s", e)
        return {"success": False, "error": str(e)}


def generate_ecms_tool(analysis: dict) -> dict:
    """Generate Energy Conservation Measures based on analysis."""
    try:
        from app.services.analysis.models import AnalysisResult
        from app.services.loop.ecm_generator import generate_ecms as gen_ecms
        from app.services.loop.idf_parser import IDFData
        analysis_obj = AnalysisResult(**analysis)
        # Create default IDFData for the ECM generator
        idf_data = IDFData()
        ecm = gen_ecms(idf_data, analysis_obj)
        return {
            "success": True,
            "heating_occupied_c": ecm.heating_occupied_c,
            "cooling_occupied_c": ecm.cooling_occupied_c,
            "reasoning": ecm.reasoning,
            "estimated_savings_pct": ecm.estimated_savings_pct,
        }
    except Exception as e:
        logger.error("generate_ecms failed: %s", e)
        return {"success": False, "error": str(e)}


def get_errors(output_dir: str) -> dict:
    """Check EnergyPlus error and warning files."""
    try:
        errors = []
        warnings = []
        output_path = Path(output_dir)

        for err_file in ["eplusout.err", "sqlite.err"]:
            f = output_path / err_file
            if f.exists():
                content = f.read_text()
                for line in content.splitlines():
                    if "**  Error  **" in line or "**  Severe  **" in line:
                        errors.append(line)
                    elif "**  Warning  **" in line:
                        warnings.append(line)

        return {
            "success": True,
            "errors": errors[:50],
            "warnings": warnings[:50],
        }
    except Exception as e:
        logger.error("get_errors failed: %s", e)
        return {"success": False, "error": str(e)}


def get_tool_definitions() -> list[Tool]:
    return [
        Tool(
            name="parse_idf",
            description="Parse an IDF file to extract thermostat setpoint schedules (heating/cooling, occupied/unoccupied)",
            handler=parse_idf,
            parameters={
                "type": "object",
                "properties": {
                    "idf_path": {"type": "string", "description": "Path to the IDF file"},
                },
                "required": ["idf_path"],
            },
        ),
        Tool(
            name="run_simulation",
            description="Run an EnergyPlus simulation with the given IDF and weather files",
            handler=run_simulation,
            parameters={
                "type": "object",
                "properties": {
                    "idf_path": {"type": "string", "description": "Path to the IDF file"},
                    "weather_path": {"type": "string", "description": "Path to the EPW weather file"},
                    "output_dir": {"type": "string", "description": "Output directory for simulation results"},
                },
                "required": ["idf_path"],
            },
        ),
        Tool(
            name="analyze_results",
            description="Parse EnergyPlus CSV output and compute energy breakdown, peak load, HVAC summary, and thermal comfort (PMV/PPD)",
            handler=analyze_results,
            parameters={
                "type": "object",
                "properties": {
                    "csv_path": {"type": "string", "description": "Path to the EnergyPlus CSV output file"},
                },
                "required": ["csv_path"],
            },
        ),
        Tool(
            name="modify_setpoints",
            description="Modify thermostat setpoint schedules in an IDF file and save as a new file",
            handler=modify_setpoints,
            parameters={
                "type": "object",
                "properties": {
                    "idf_path": {"type": "string", "description": "Path to the source IDF file"},
                    "output_path": {"type": "string", "description": "Path to save the modified IDF file"},
                    "heating_occupied_c": {"type": "number", "description": "Heating setpoint during occupied hours (°C)"},
                    "cooling_occupied_c": {"type": "number", "description": "Cooling setpoint during occupied hours (°C)"},
                    "heating_unoccupied_c": {"type": "number", "description": "Heating setpoint during unoccupied hours (°C)"},
                    "cooling_unoccupied_c": {"type": "number", "description": "Cooling setpoint during unoccupied hours (°C)"},
                },
                "required": ["idf_path", "output_path"],
            },
        ),
        Tool(
            name="generate_ecms",
            description="Generate Energy Conservation Measures (optimal setpoints) based on analysis results",
            handler=generate_ecms_tool,
            parameters={
                "type": "object",
                "properties": {
                    "analysis": {"type": "object", "description": "Analysis result object from analyze_results"},
                },
                "required": ["analysis"],
            },
        ),
        Tool(
            name="get_errors",
            description="Check EnergyPlus error and warning files for issues",
            handler=get_errors,
            parameters={
                "type": "object",
                "properties": {
                    "output_dir": {"type": "string", "description": "Directory containing EnergyPlus output files"},
                },
                "required": ["output_dir"],
            },
        ),
    ]