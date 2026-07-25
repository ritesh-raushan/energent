import logging
from pathlib import Path

import pandas as pd

from app.services.energyplus.models import (
    EnergyRecord,
    EnergySummary,
    ParsedSimulationData,
)

logger = logging.getLogger(__name__)

COLUMN_MAP = {
    "Date/Time": "timestamp",
    "Site Outdoor Air Drybulb Temperature [C]": "outdoor_temp_c",
    "Site Outdoor Air Humidity Ratio [kg/kg]": "outdoor_humidity_ratio_kgkg",
    "Site Outdoor Air Relative Humidity [%]": "outdoor_relative_humidity_pct",
    "Zone Mean Air Temperature [C]": "zone_mean_air_temp_c",
    "Electricity:Facility [J]": "electricity_facility_j",
    "Fans:Electricity [J]": "fans_electricity_j",
    "Cooling:Electricity [J]": "cooling_electricity_j",
    "Heating:Electricity [J]": "heating_electricity_j",
    "InteriorLights:Electricity [J]": "interior_lights_electricity_j",
    "InteriorEquipment:Electricity [J]": "interior_equipment_electricity_j",
    "NaturalGas:Facility [J]": "natural_gas_facility_j",
    "Heating:NaturalGas [J]": "heating_natural_gas_j",
}

JOULES_PER_KWH = 3_600_000


def parse_csv(csv_path: Path) -> ParsedSimulationData:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    logger.info("Parsing EnergyPlus CSV: %s", csv_path)
    df = pd.read_csv(csv_path)

    raw_columns = list(df.columns)
    logger.info("Found %d columns, %d rows", len(raw_columns), len(df))

    df = _rename_columns(df, raw_columns)
    df = _parse_timestamps(df)
    records = _build_records(df)
    summary = _build_summary(df)

    return ParsedSimulationData(
        records=records,
        summary=summary,
        raw_columns=raw_columns,
        record_count=len(records),
    )


def _rename_columns(df: pd.DataFrame, raw_columns: list[str]) -> pd.DataFrame:
    rename_map = {}
    for raw_col in raw_columns:
        cleaned = raw_col.strip()
        if cleaned in COLUMN_MAP:
            rename_map[raw_col] = COLUMN_MAP[cleaned]
    df = df.rename(columns=rename_map)
    return df


def _parse_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    if "timestamp" not in df.columns:
        return df

    ts_col = df["timestamp"].astype(str).str.strip()
    ts_col = ts_col.str.replace(r"\s+", " ", regex=True)

    df["timestamp"] = pd.to_datetime(
        ts_col,
        format="mixed",
        dayfirst=False,
        errors="coerce",
    )
    df = df.dropna(subset=["timestamp"])
    return df


def _build_records(df: pd.DataFrame) -> list[EnergyRecord]:
    records = []
    for _, row in df.iterrows():
        record = EnergyRecord(
            timestamp=row["timestamp"],
            outdoor_temp_c=_safe_float(row, "outdoor_temp_c"),
            outdoor_humidity_ratio_kgkg=_safe_float(row, "outdoor_humidity_ratio_kgkg"),
            outdoor_relative_humidity_pct=_safe_float(row, "outdoor_relative_humidity_pct"),
            zone_mean_air_temp_c=_safe_float(row, "zone_mean_air_temp_c"),
            electricity_facility_j=_safe_float(row, "electricity_facility_j"),
            fans_electricity_j=_safe_float(row, "fans_electricity_j"),
            cooling_electricity_j=_safe_float(row, "cooling_electricity_j"),
            heating_electricity_j=_safe_float(row, "heating_electricity_j"),
            interior_lights_electricity_j=_safe_float(row, "interior_lights_electricity_j"),
            interior_equipment_electricity_j=_safe_float(row, "interior_equipment_electricity_j"),
            natural_gas_facility_j=_safe_float(row, "natural_gas_facility_j"),
            heating_natural_gas_j=_safe_float(row, "heating_natural_gas_j"),
        )
        records.append(record)
    return records


def _build_summary(df: pd.DataFrame) -> EnergySummary:
    electricity_j = df["electricity_facility_j"].dropna() if "electricity_facility_j" in df.columns else pd.Series(dtype=float)
    natural_gas_j = df["natural_gas_facility_j"].dropna() if "natural_gas_facility_j" in df.columns else pd.Series(dtype=float)
    outdoor_temp = df["outdoor_temp_c"].dropna() if "outdoor_temp_c" in df.columns else pd.Series(dtype=float)
    zone_temp = df["zone_mean_air_temp_c"].dropna() if "zone_mean_air_temp_c" in df.columns else pd.Series(dtype=float)

    total_electricity_kwh = float(electricity_j.sum()) / JOULES_PER_KWH if len(electricity_j) > 0 else 0.0
    total_natural_gas_kwh = float(natural_gas_j.sum()) / JOULES_PER_KWH if len(natural_gas_j) > 0 else 0.0

    peak_electricity_kw = 0.0
    if len(electricity_j) > 0:
        peak_electricity_kw = float(electricity_j.max()) / JOULES_PER_KWH

    return EnergySummary(
        total_hours=len(df),
        total_electricity_kwh=round(total_electricity_kwh, 2),
        total_natural_gas_kwh=round(total_natural_gas_kwh, 2),
        peak_electricity_kw=round(peak_electricity_kw, 2),
        avg_outdoor_temp_c=round(float(outdoor_temp.mean()), 2) if len(outdoor_temp) > 0 else 0.0,
        avg_zone_temp_c=round(float(zone_temp.mean()), 2) if len(zone_temp) > 0 else 0.0,
        min_zone_temp_c=round(float(zone_temp.min()), 2) if len(zone_temp) > 0 else 0.0,
        max_zone_temp_c=round(float(zone_temp.max()), 2) if len(zone_temp) > 0 else 0.0,
    )


def _safe_float(row: pd.Series, col: str) -> float | None:
    if col in row.index:
        val = row[col]
        if pd.notna(val):
            return float(val)
    return None
