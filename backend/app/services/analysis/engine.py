import logging

from app.constants import COMFORT_TEMP_MAX_C, COMFORT_TEMP_MIN_C, JOULES_PER_KWH
from app.services.analysis.models import (
    AnalysisResult,
    EnergyBreakdown,
    HVACSummary,
    PeakLoadAnalysis,
    Recommendation,
)
from app.services.analysis.thermal_comfort import calculate_pmv
from app.services.energyplus.models import ParsedSimulationData

logger = logging.getLogger(__name__)


def analyze(data: ParsedSimulationData) -> AnalysisResult:
    logger.info("Running analysis on %d records", data.record_count)

    breakdown = _energy_breakdown(data)
    peak = _peak_load_analysis(data)
    hvac = _hvac_summary(data)
    thermal = _compute_thermal_comfort(data)
    recommendations = _generate_recommendations(breakdown, peak, hvac, thermal, data)

    total_savings = sum(r.estimated_savings_kwh for r in recommendations)
    score = _compute_score(breakdown, peak, hvac, thermal)

    return AnalysisResult(
        energy_breakdown=breakdown,
        peak_load=peak,
        hvac_summary=hvac,
        thermal_comfort=thermal,
        recommendations=recommendations,
        overall_score=round(score, 1),
        total_potential_savings_kwh=round(total_savings, 2),
    )


def _energy_breakdown(data: ParsedSimulationData) -> EnergyBreakdown:
    heating_j = sum(r.heating_electricity_j or 0.0 for r in data.records)
    cooling_j = sum(r.cooling_electricity_j or 0.0 for r in data.records)
    fans_j = sum(r.fans_electricity_j or 0.0 for r in data.records)
    lighting_j = sum(r.interior_lights_electricity_j or 0.0 for r in data.records)
    equipment_j = sum(r.interior_equipment_electricity_j or 0.0 for r in data.records)

    heating_kwh = round(heating_j / JOULES_PER_KWH, 2)
    cooling_kwh = round(cooling_j / JOULES_PER_KWH, 2)
    fans_kwh = round(fans_j / JOULES_PER_KWH, 2)
    lighting_kwh = round(lighting_j / JOULES_PER_KWH, 2)
    equipment_kwh = round(equipment_j / JOULES_PER_KWH, 2)
    total = heating_kwh + cooling_kwh + fans_kwh + lighting_kwh + equipment_kwh

    if total > 0:
        heating_pct = round(heating_kwh / total * 100, 1)
        cooling_pct = round(cooling_kwh / total * 100, 1)
        fans_pct = round(fans_kwh / total * 100, 1)
        lighting_pct = round(lighting_kwh / total * 100, 1)
        equipment_pct = round(equipment_kwh / total * 100, 1)
    else:
        heating_pct = cooling_pct = fans_pct = lighting_pct = equipment_pct = 0.0

    return EnergyBreakdown(
        heating_kwh=heating_kwh,
        cooling_kwh=cooling_kwh,
        fans_kwh=fans_kwh,
        lighting_kwh=lighting_kwh,
        equipment_kwh=equipment_kwh,
        total_electricity_kwh=round(total, 2),
        heating_pct=heating_pct,
        cooling_pct=cooling_pct,
        fans_pct=fans_pct,
        lighting_pct=lighting_pct,
        equipment_pct=equipment_pct,
    )


def _peak_load_analysis(data: ParsedSimulationData) -> PeakLoadAnalysis:
    if not data.records:
        return PeakLoadAnalysis()

    max_kw = 0.0
    peak_record = data.records[0]
    for r in data.records:
        kw = (r.electricity_facility_j or 0.0) / JOULES_PER_KWH
        if kw > max_kw:
            max_kw = kw
            peak_record = r

    peak_heating = (peak_record.heating_electricity_j or 0.0) / JOULES_PER_KWH
    peak_cooling = (peak_record.cooling_electricity_j or 0.0) / JOULES_PER_KWH
    peak_fans = (peak_record.fans_electricity_j or 0.0) / JOULES_PER_KWH
    peak_lighting = (peak_record.interior_lights_electricity_j or 0.0) / JOULES_PER_KWH
    peak_equipment = (peak_record.interior_equipment_electricity_j or 0.0) / JOULES_PER_KWH

    total_elec = sum(r.electricity_facility_j or 0.0 for r in data.records) / JOULES_PER_KWH
    avg_kw = total_elec / len(data.records) if data.records else 0.0
    load_factor = round(avg_kw / max_kw, 3) if max_kw > 0 else 0.0

    peak_hours = sum(1 for r in data.records if (r.electricity_facility_j or 0.0) / JOULES_PER_KWH > max_kw * 0.9)

    return PeakLoadAnalysis(
        peak_kw=round(max_kw, 2),
        peak_timestamp=peak_record.timestamp.isoformat(),
        peak_heating_pct=round(peak_heating / max_kw * 100, 1) if max_kw > 0 else 0.0,
        peak_cooling_pct=round(peak_cooling / max_kw * 100, 1) if max_kw > 0 else 0.0,
        peak_fans_pct=round(peak_fans / max_kw * 100, 1) if max_kw > 0 else 0.0,
        peak_lighting_pct=round(peak_lighting / max_kw * 100, 1) if max_kw > 0 else 0.0,
        peak_equipment_pct=round(peak_equipment / max_kw * 100, 1) if max_kw > 0 else 0.0,
        peak_hours_count=peak_hours,
        avg_load_kw=round(avg_kw, 2),
        load_factor=load_factor,
    )


def _hvac_summary(data: ParsedSimulationData) -> HVACSummary:
    heating_j = sum(r.heating_electricity_j or 0.0 for r in data.records)
    cooling_j = sum(r.cooling_electricity_j or 0.0 for r in data.records)

    heating_hours = sum(1 for r in data.records if (r.heating_electricity_j or 0.0) > 0)
    cooling_hours = sum(1 for r in data.records if (r.cooling_electricity_j or 0.0) > 0)

    zone_temps = [r.zone_mean_air_temp_c for r in data.records if r.zone_mean_air_temp_c is not None]

    return HVACSummary(
        total_heating_energy_kwh=round(heating_j / JOULES_PER_KWH, 2),
        total_cooling_energy_kwh=round(cooling_j / JOULES_PER_KWH, 2),
        heating_hours=heating_hours,
        cooling_hours=cooling_hours,
        avg_zone_temp_c=round(sum(zone_temps) / len(zone_temps), 2) if zone_temps else 0.0,
        min_zone_temp_c=round(min(zone_temps), 2) if zone_temps else 0.0,
        max_zone_temp_c=round(max(zone_temps), 2) if zone_temps else 0.0,
    )


def _compute_thermal_comfort(data: ParsedSimulationData):
    zone_temps = [r.zone_mean_air_temp_c for r in data.records if r.zone_mean_air_temp_c is not None]
    if not zone_temps:
        return calculate_pmv(22.0)

    avg_temp = sum(zone_temps) / len(zone_temps)
    outdoor_humidities = [r.outdoor_relative_humidity_pct for r in data.records if r.outdoor_relative_humidity_pct is not None]
    avg_humidity = sum(outdoor_humidities) / len(outdoor_humidities) if outdoor_humidities else 50.0

    heating_active = any((r.heating_electricity_j or 0.0) > 0 for r in data.records)
    cooling_active = any((r.cooling_electricity_j or 0.0) > 0 for r in data.records)

    if heating_active and not cooling_active:
        clothing = 1.0
    elif cooling_active and not heating_active:
        clothing = 0.5
    else:
        clothing = 0.7

    return calculate_pmv(
        air_temperature_c=avg_temp,
        relative_humidity_pct=avg_humidity,
        air_velocity_ms=0.15,
        metabolic_rate_met=1.2,
        clothing_insulation_clo=clothing,
    )


def _generate_recommendations(
    breakdown: EnergyBreakdown,
    peak: PeakLoadAnalysis,
    hvac: HVACSummary,
    thermal,
    data: ParsedSimulationData,
) -> list[Recommendation]:
    recs: list[Recommendation] = []

    if breakdown.heating_pct > 40:
        savings = breakdown.heating_kwh * 0.15
        recs.append(Recommendation(
            category="HVAC",
            priority="high",
            title="High heating energy consumption",
            description=f"Heating accounts for {breakdown.heating_pct}% of total electricity. Consider lowering setpoint by 1-2°C or improving insulation.",
            estimated_savings_kwh=round(savings, 2),
            estimated_savings_pct=15.0,
        ))

    if breakdown.cooling_pct > 30:
        savings = breakdown.cooling_kwh * 0.12
        recs.append(Recommendation(
            category="HVAC",
            priority="high",
            title="High cooling energy consumption",
            description=f"Cooling accounts for {breakdown.cooling_pct}% of total electricity. Consider raising setpoint by 1-2°C or improving shading.",
            estimated_savings_kwh=round(savings, 2),
            estimated_savings_pct=12.0,
        ))

    if hvac.avg_zone_temp_c > COMFORT_TEMP_MAX_C:
        recs.append(Recommendation(
            category="Comfort",
            priority="medium",
            title="Zone temperature above comfort range",
            description=f"Average zone temperature is {hvac.avg_zone_temp_c}°C, exceeding the {COMFORT_TEMP_MAX_C}°C upper comfort limit.",
        ))
    elif hvac.avg_zone_temp_c < COMFORT_TEMP_MIN_C and hvac.avg_zone_temp_c > 0:
        recs.append(Recommendation(
            category="Comfort",
            priority="medium",
            title="Zone temperature below comfort range",
            description=f"Average zone temperature is {hvac.avg_zone_temp_c}°C, below the {COMFORT_TEMP_MIN_C}°C lower comfort limit.",
        ))

    if abs(thermal.pmv) > 1.0:
        recs.append(Recommendation(
            category="Thermal Comfort",
            priority="high" if abs(thermal.pmv) > 2.0 else "medium",
            title=f"PMV indicates {thermal.comfort_status} conditions",
            description=f"Predicted Mean Vote is {thermal.pmv} ({thermal.comfort_status}) with {thermal.ppd}% dissatisfied occupants. Adjust setpoints or air velocity to improve comfort.",
        ))

    if thermal.ppd > 20:
        recs.append(Recommendation(
            category="Thermal Comfort",
            priority="medium",
            title="High predicted percentage of dissatisfied occupants",
            description=f"PPD is {thermal.ppd}%, indicating significant occupant discomfort. Target PPD below 10% for acceptable comfort.",
        ))

    if peak.load_factor < 0.5:
        savings = breakdown.total_electricity_kwh * 0.05
        recs.append(Recommendation(
            category="Load Management",
            priority="medium",
            title="Low load factor indicates peaky demand",
            description=f"Load factor is {peak.load_factor}. Consider load shifting or demand response strategies to flatten the demand profile.",
            estimated_savings_kwh=round(savings, 2),
            estimated_savings_pct=5.0,
        ))

    if breakdown.fans_pct > 20:
        savings = breakdown.fans_kwh * 0.10
        recs.append(Recommendation(
            category="HVAC",
            priority="medium",
            title="High fan energy consumption",
            description=f"Fans account for {breakdown.fans_pct}% of total electricity. Consider variable speed drives or reduced airflow schedules.",
            estimated_savings_kwh=round(savings, 2),
            estimated_savings_pct=10.0,
        ))

    if breakdown.lighting_pct > 20:
        savings = breakdown.lighting_kwh * 0.20
        recs.append(Recommendation(
            category="Lighting",
            priority="low",
            title="High lighting energy consumption",
            description=f"Lighting accounts for {breakdown.lighting_pct}% of total electricity. Consider LED upgrades or daylight harvesting controls.",
            estimated_savings_kwh=round(savings, 2),
            estimated_savings_pct=20.0,
        ))

    outdoor_temps = [r.outdoor_temp_c for r in data.records if r.outdoor_temp_c is not None]
    if outdoor_temps:
        avg_outdoor = sum(outdoor_temps) / len(outdoor_temps)
        if avg_outdoor > 15 and hvac.cooling_hours == 0 and hvac.heating_hours > 100:
            recs.append(Recommendation(
                category="Optimization",
                priority="high",
                title="Heating during mild weather detected",
                description=f"Average outdoor temperature is {avg_outdoor:.1f}°C but heating is still active. Consider economizer controls or free cooling.",
            ))

    return recs


def _compute_score(breakdown: EnergyBreakdown, peak: PeakLoadAnalysis, hvac: HVACSummary, thermal) -> float:
    score = 100.0

    if hvac.avg_zone_temp_c > 0:
        if hvac.avg_zone_temp_c < COMFORT_TEMP_MIN_C:
            score -= (COMFORT_TEMP_MIN_C - hvac.avg_zone_temp_c) * 5
        elif hvac.avg_zone_temp_c > COMFORT_TEMP_MAX_C:
            score -= (hvac.avg_zone_temp_c - COMFORT_TEMP_MAX_C) * 5

    if abs(thermal.pmv) > 0.5:
        score -= abs(thermal.pmv) * 10

    if thermal.ppd > 10:
        score -= (thermal.ppd - 10) * 0.5

    if peak.load_factor < 0.5:
        score -= (0.5 - peak.load_factor) * 20

    if breakdown.heating_pct > 50:
        score -= 10
    if breakdown.cooling_pct > 40:
        score -= 10

    return max(0.0, min(100.0, score))
