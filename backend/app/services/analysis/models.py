from pydantic import BaseModel, Field


class EnergyBreakdown(BaseModel):
    heating_kwh: float = 0.0
    cooling_kwh: float = 0.0
    fans_kwh: float = 0.0
    lighting_kwh: float = 0.0
    equipment_kwh: float = 0.0
    other_kwh: float = 0.0
    total_electricity_kwh: float = 0.0
    heating_pct: float = 0.0
    cooling_pct: float = 0.0
    fans_pct: float = 0.0
    lighting_pct: float = 0.0
    equipment_pct: float = 0.0


class PeakLoadAnalysis(BaseModel):
    peak_kw: float = 0.0
    peak_timestamp: str = ""
    peak_heating_pct: float = 0.0
    peak_cooling_pct: float = 0.0
    peak_fans_pct: float = 0.0
    peak_lighting_pct: float = 0.0
    peak_equipment_pct: float = 0.0
    peak_hours_count: int = 0
    avg_load_kw: float = 0.0
    load_factor: float = 0.0


class HVACSummary(BaseModel):
    total_heating_energy_kwh: float = 0.0
    total_cooling_energy_kwh: float = 0.0
    heating_hours: int = 0
    cooling_hours: int = 0
    avg_zone_temp_c: float = 0.0
    min_zone_temp_c: float = 0.0
    max_zone_temp_c: float = 0.0
    heating_cop_estimate: float = 0.0
    cooling_cop_estimate: float = 0.0


class Recommendation(BaseModel):
    category: str
    priority: str
    title: str
    description: str
    estimated_savings_kwh: float = 0.0
    estimated_savings_pct: float = 0.0


class AnalysisResult(BaseModel):
    energy_breakdown: EnergyBreakdown = Field(default_factory=EnergyBreakdown)
    peak_load: PeakLoadAnalysis = Field(default_factory=PeakLoadAnalysis)
    hvac_summary: HVACSummary = Field(default_factory=HVACSummary)
    recommendations: list[Recommendation] = Field(default_factory=list)
    overall_score: float = 0.0
    total_potential_savings_kwh: float = 0.0
