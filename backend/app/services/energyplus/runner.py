import logging
import subprocess
from pathlib import Path

from app.config import settings
from app.services.energyplus.models import SimulationConfig, SimulationResult

logger = logging.getLogger(__name__)


class EnergyPlusRunner:
    def __init__(self, config: SimulationConfig | None = None) -> None:
        self.config = config or self._default_config()

    def _default_config(self) -> SimulationConfig:
        return SimulationConfig(
            energyplus_exe=Path(settings.ENERGYPLUS_EXE_PATH),
            idf_path=Path(settings.SIMULATION_IDF_PATH),
            weather_path=Path(settings.SIMULATION_WEATHER_PATH),
            output_dir=Path(settings.ENERGYPLUS_WORK_DIR),
        )

    def run(self) -> SimulationResult:
        self._validate_paths()
        self._ensure_output_dir()

        cmd = [
            str(self.config.energyplus_exe),
            "-w", str(self.config.weather_path),
            "-d", str(self.config.output_dir),
            str(self.config.idf_path),
        ]

        logger.info("Running EnergyPlus simulation: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )

            csv_path = self._find_csv_output()

            return SimulationResult(
                success=result.returncode == 0,
                idf_path=self.config.idf_path,
                weather_path=self.config.weather_path,
                output_dir=self.config.output_dir,
                csv_path=csv_path,
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
            )

        except subprocess.TimeoutExpired:
            logger.error("EnergyPlus simulation timed out after 300 seconds")
            return SimulationResult(
                success=False,
                idf_path=self.config.idf_path,
                weather_path=self.config.weather_path,
                output_dir=self.config.output_dir,
                stderr="Simulation timed out after 300 seconds",
                return_code=-1,
            )
        except FileNotFoundError:
            logger.error("EnergyPlus executable not found: %s", self.config.energyplus_exe)
            return SimulationResult(
                success=False,
                idf_path=self.config.idf_path,
                weather_path=self.config.weather_path,
                output_dir=self.config.output_dir,
                stderr=f"EnergyPlus executable not found: {self.config.energyplus_exe}",
                return_code=-1,
            )
        except Exception as e:
            logger.error("Unexpected error running EnergyPlus: %s", e)
            return SimulationResult(
                success=False,
                idf_path=self.config.idf_path,
                weather_path=self.config.weather_path,
                output_dir=self.config.output_dir,
                stderr=str(e),
                return_code=-1,
            )

    def _validate_paths(self) -> None:
        if not self.config.energyplus_exe.exists():
            raise FileNotFoundError(f"EnergyPlus executable not found: {self.config.energyplus_exe}")
        if not self.config.idf_path.exists():
            raise FileNotFoundError(f"IDF file not found: {self.config.idf_path}")
        if not self.config.weather_path.exists():
            raise FileNotFoundError(f"Weather file not found: {self.config.weather_path}")

    def _ensure_output_dir(self) -> None:
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

    def _find_csv_output(self) -> Path | None:
        csv_files = list(self.config.output_dir.glob("eplusout*.csv"))
        if csv_files:
            return csv_files[0]
        return None
