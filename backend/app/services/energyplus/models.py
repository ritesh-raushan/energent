from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field


class SimulationConfig(BaseModel):
    idf_path: Path
    weather_path: Path
    output_dir: Path
    energyplus_exe: Path


class SimulationResult(BaseModel):
    success: bool
    idf_path: Path
    weather_path: Path
    output_dir: Path
    csv_path: Path | None = None
    stdout: str = ""
    stderr: str = ""
    return_code: int = -1


class EnergyRecord(BaseModel):
    timestamp: datetime
    outdoor_temp_c: float | None = None
    outdoor_humidity_ratio_kgkg: float | None = None
    outdoor_relative_humidity_pct: float | None = None
    zone_mean_air_temp_c: float | None = None
    electricity_facility_j: float | None = None
    fans_electricity_j: float | None = None
    cooling_electricity_j: float | None = None
    heating_electricity_j: float | None = None
    interior_lights_electricity_j: float | None = None
    interior_equipment_electricity_j: float | None = None
    natural_gas_facility_j: float | None = None
    heating_natural_gas_j: float | None = None


class EnergySummary(BaseModel):
    total_hours: int = 0
    total_electricity_kwh: float = 0.0
    total_natural_gas_kwh: float = 0.0
    peak_electricity_kw: float = 0.0
    avg_outdoor_temp_c: float = 0.0
    avg_zone_temp_c: float = 0.0
    min_zone_temp_c: float = 0.0
    max_zone_temp_c: float = 0.0


class ParsedSimulationData(BaseModel):
    records: list[EnergyRecord] = Field(default_factory=list)
    summary: EnergySummary = Field(default_factory=EnergySummary)
    raw_columns: list[str] = Field(default_factory=list)
    record_count: int = 0
