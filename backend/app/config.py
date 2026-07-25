from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Energent"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    LOG_LEVEL: str = "INFO"

    ENERGYPLUS_EXE_PATH: str = "C:/EnergyPlus/EnergyPlus.exe"
    ENERGYPLUS_WORK_DIR: str = "./simulation/output"

    SIMULATION_IDF_PATH: str = "./simulation/idf/RefBldgSmallOfficeNew2004_Chicago.idf"
    SIMULATION_WEATHER_PATH: str = "./simulation/weather/USA_IL_Chicago-OHare.Intl.AP.725300_TMY3.epw"

    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "qwen/qwen3-8b"

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
    }


settings = Settings()
