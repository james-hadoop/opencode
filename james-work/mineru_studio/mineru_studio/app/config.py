"""Application configuration."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class AppConfig(BaseSettings):
    port: int = 3000
    sqlite_path: str = "/tmp/mineru-studio.sqlite"
    artifact_root_dir: str = "/tmp/mineru-studio-artifacts"
    recover_runs_on_startup: bool = True
    polling_scan_enabled: bool = True
    polling_scan_interval_ms: int = 1000
    timeout_scan_enabled: bool = True
    timeout_scan_interval_ms: int = 1000
    current_user_id: str = "default_user"
    current_team_id: str = "default_team"

    class Config:
        env_prefix = "MINERU_"


@lru_cache
def get_config() -> AppConfig:
    return AppConfig()