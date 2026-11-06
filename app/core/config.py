from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = (
        "postgresql+psycopg://milk_app:milk_password@localhost:5432/milk_delivery"
    )
    auto_assign_radius_km: float = 5.0
    new_zone_radius_meters: int = 1000
    traffic_penalty_weight: int = 20

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
