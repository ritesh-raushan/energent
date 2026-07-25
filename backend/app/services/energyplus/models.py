from pathlib import Path

from pydantic import BaseModel, Field


class SimulationConfig(BaseModel):
    idf_path: Path
    weather_path: Path
    output_dir: Path
    energyplus_exe: Path = Field(default_factory=lambda: Path("C:/EnergyPlus/EnergyPlus.exe"))


class SimulationResult(BaseModel):
    success: bool
    idf_path: Path
    weather_path: Path
    output_dir: Path
    csv_path: Path | None = None
    stdout: str = ""
    stderr: str = ""
    return_code: int = -1
