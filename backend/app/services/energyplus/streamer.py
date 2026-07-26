import asyncio
import json
import logging
import time
from pathlib import Path
from typing import AsyncGenerator, Optional

import pandas as pd

from app.constants import JOULES_PER_KWH
from app.services.analysis.thermal_comfort import calculate_pmv

logger = logging.getLogger(__name__)


class SimulationStreamer:
    def __init__(self, output_dir: Path, poll_interval: float = 2.0):
        self.output_dir = Path(output_dir)
        self.poll_interval = poll_interval
        self.csv_path: Optional[Path] = None
        self._running = False
        self._last_row = 0

    def find_csv(self) -> Optional[Path]:
        csv_files = list(self.output_dir.glob("eplusout*.csv"))
        if csv_files:
            return max(csv_files, key=lambda f: f.stat().st_mtime)
        return None

    def parse_latest_metrics(self) -> Optional[dict]:
        csv_path = self.find_csv()
        if not csv_path or not csv_path.exists():
            return None

        try:
            df = pd.read_csv(csv_path)
            if len(df) == 0:
                return None

            if len(df) <= self._last_row:
                return None

            new_rows = df.iloc[self._last_row:]
            self._last_row = len(df)

            latest = new_rows.iloc[-1]

            zone_temp = None
            for col in df.columns:
                if "Zone Mean Air Temperature" in col and "C]" in col:
                    val = latest.get(col)
                    if pd.notna(val):
                        zone_temp = float(val)
                        break

            outdoor_temp = None
            for col in df.columns:
                if "Site Outdoor Air Drybulb Temperature" in col and "C]" in col:
                    val = latest.get(col)
                    if pd.notna(val):
                        outdoor_temp = float(val)
                        break

            humidity = None
            for col in df.columns:
                if "Site Outdoor Air Relative Humidity" in col and "%]" in col:
                    val = latest.get(col)
                    if pd.notna(val):
                        humidity = float(val)
                        break

            electricity = 0.0
            for col in df.columns:
                if "Electricity:Facility" in col and "J]" in col:
                    val = latest.get(col)
                    if pd.notna(val):
                        electricity = float(val) / JOULES_PER_KWH
                        break

            heating = 0.0
            for col in df.columns:
                if "Heating:Electricity" in col and "J]" in col:
                    val = latest.get(col)
                    if pd.notna(val):
                        heating = float(val) / JOULES_PER_KWH
                        break

            cooling = 0.0
            for col in df.columns:
                if "Cooling:Electricity" in col and "J]" in col:
                    val = latest.get(col)
                    if pd.notna(val):
                        cooling = float(val) / JOULES_PER_KWH
                        break

            pmv_data = None
            if zone_temp is not None and humidity is not None:
                pmv_result = calculate_pmv(
                    air_temperature_c=zone_temp,
                    relative_humidity_pct=humidity,
                    air_velocity_ms=0.15,
                    metabolic_rate_met=1.2,
                    clothing_insulation_clo=0.7,
                )
                pmv_data = {
                    "pmv": pmv_result.pmv,
                    "ppd": pmv_result.ppd,
                    "comfort_status": pmv_result.comfort_status,
                }

            return {
                "timestamp": str(latest.get("Date/Time", "")),
                "zone_temp_c": zone_temp,
                "outdoor_temp_c": outdoor_temp,
                "humidity_pct": humidity,
                "electricity_kw": round(electricity, 3),
                "heating_kw": round(heating, 3),
                "cooling_kw": round(cooling, 3),
                "thermal_comfort": pmv_data,
                "sim_time_index": self._last_row,
            }

        except Exception as e:
            logger.error("Error parsing metrics: %s", e)
            return None

    async def stream_metrics(self) -> AsyncGenerator[dict, None]:
        self._running = True
        self._last_row = 0

        while self._running:
            metrics = self.parse_latest_metrics()
            if metrics:
                yield metrics
            await asyncio.sleep(self.poll_interval)

    def stop(self):
        self._running = False


async def create_streamer(output_dir: str, poll_interval: float = 2.0) -> SimulationStreamer:
    return SimulationStreamer(Path(output_dir), poll_interval)