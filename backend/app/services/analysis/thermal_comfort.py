import math
from pydantic import BaseModel


class ThermalComfort(BaseModel):
    pmv: float = 0.0
    ppd: float = 5.0
    comfort_status: str = "neutral"
    air_temperature_c: float = 0.0
    mean_radiant_temperature_c: float = 0.0
    air_velocity_ms: float = 0.0
    relative_humidity_pct: float = 0.0
    metabolic_rate_met: float = 1.0
    clothing_insulation_clo: float = 0.7


def calculate_pmv(
    air_temperature_c: float,
    mean_radiant_temperature_c: float | None = None,
    air_velocity_ms: float = 0.15,
    relative_humidity_pct: float = 50.0,
    metabolic_rate_met: float = 1.0,
    clothing_insulation_clo: float = 0.7,
) -> ThermalComfort:
    if mean_radiant_temperature_c is None:
        mean_radiant_temperature_c = air_temperature_c

    Ta = air_temperature_c
    Tr = mean_radiant_temperature_c
    v = air_velocity_ms
    RH = relative_humidity_pct

    # Metabolic rate in W/m² (1 met = 58.15 W/m²)
    M = metabolic_rate_met * 58.15

    # Clothing insulation in m²·K/W (1 clo = 0.155 m²·K/W)
    Icl = clothing_insulation_clo * 0.155

    # Vapor pressure (Pa)
    Pa = RH * 0.01 * math.exp(16.6536 - 4030.183 / (Ta + 235.0))

    # Clothing area factor
    fcl = 1.0 + 1.29 * Icl if Icl <= 0.078 else 1.05 + 0.645 * Icl

    # Convective heat transfer coefficient for still air (W/m²·K)
    hcf = 12.1 * math.sqrt(v)

    Tk_offset = 273.15
    Tr_k = Tr + Tk_offset
    Ta_k = Ta + Tk_offset

    # Iterative solution for clothing surface temperature
    # Initialize close to air temperature
    Tcl = Ta

    for _ in range(200):
        Tcl_k = Tcl + Tk_offset
        hc = max(2.38 * abs(Tcl - Ta) ** 0.25, hcf)

        # Radiation term
        rad = 3.96e-8 * fcl * (Tr_k ** 4 - Tcl_k ** 4)

        # Convection term
        conv = hc * (Ta - Tcl)

        # Metabolic heat
        met = 0.07 * max(M, 0.0)

        # New Tcl from heat balance at clothing surface
        numerator = 33.35 + Icl * (rad + met + conv)
        denominator = 1.0 + Icl * fcl * 1.8 + Icl * fcl * v

        if abs(denominator) < 1e-10:
            break

        Tcl_new = numerator / denominator

        # Clamp to prevent divergence
        Tcl_new = max(Ta - 15.0, min(Ta + 15.0, Tcl_new))

        if abs(Tcl_new - Tcl) < 0.0001:
            Tcl = Tcl_new
            break

        # Damped update for stability
        Tcl = 0.5 * Tcl + 0.5 * Tcl_new

    # Final heat loss calculation
    Tcl_k = Tcl + Tk_offset
    hc = max(2.38 * abs(Tcl - Ta) ** 0.25, hcf)

    # Heat loss components (W/m²)
    hl1 = 3.05e-3 * (5733.0 - 6.99 * M - Pa)          # Diffusion through skin
    hl2 = 0.42 * max(M - 58.15, 0.0)                    # Sweating
    hl3 = 1.7e-5 * M * (5867.0 - Pa)                    # Latent respiration
    hl4 = 0.0014 * M * (34.0 - Ta)                      # Dry respiration
    hl5 = 3.96e-8 * fcl * (Tcl_k ** 4 - Tr_k ** 4)    # Radiation from clothed body
    hl6 = fcl * hc * (Tcl - Ta)                          # Convection from clothed body

    # PMV
    ts = M - hl1 - hl2 - hl3 - hl4 - hl5 - hl6
    PMV = (0.303 * math.exp(-0.036 * M) + 0.028) * ts

    # PPD
    PPD = 100.0 - 95.0 * math.exp(-0.03353 * PMV ** 4 - 0.2179 * PMV ** 2)
    PPD = max(5.0, min(100.0, PPD))
    PMV = max(-3.0, min(3.0, PMV))

    if PMV < -2.0:
        status = "cold"
    elif PMV < -1.0:
        status = "cool"
    elif PMV < -0.5:
        status = "slightly cool"
    elif PMV <= 0.5:
        status = "neutral"
    elif PMV <= 1.0:
        status = "slightly warm"
    elif PMV <= 2.0:
        status = "warm"
    else:
        status = "hot"

    return ThermalComfort(
        pmv=round(PMV, 2),
        ppd=round(PPD, 1),
        comfort_status=status,
        air_temperature_c=air_temperature_c,
        mean_radiant_temperature_c=mean_radiant_temperature_c,
        air_velocity_ms=air_velocity_ms,
        relative_humidity_pct=relative_humidity_pct,
        metabolic_rate_met=metabolic_rate_met,
        clothing_insulation_clo=clothing_insulation_clo,
    )
