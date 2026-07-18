import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Mapping, Optional


TRUTHY_VALUES = {"1", "true", "yes", "on"}
FALSY_VALUES = {"0", "false", "no", "off"}
LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


@dataclass(frozen=True)
class Settings:
    app_name: str
    app_version: str
    environment: str
    debug: bool
    host: str
    port: int
    log_level: str
    api_prefix: str
    data_dir: Path


def parse_bool(value: str, variable_name: str) -> bool:
    normalized = value.strip().lower()
    if normalized in TRUTHY_VALUES:
        return True
    if normalized in FALSY_VALUES:
        return False
    raise ValueError(f"{variable_name} must be a boolean value")


def parse_int(value: str, variable_name: str) -> int:
    try:
        return int(value.strip())
    except ValueError as error:
        raise ValueError(f"{variable_name} must be an integer") from error


def load_settings(env: Optional[Mapping[str, str]] = None) -> Settings:
    source = env if env is not None else os.environ
    port = parse_int(source.get("BBIOS_PORT", "8000"), "BBIOS_PORT")
    if not 1 <= port <= 65535:
        raise ValueError("BBIOS_PORT must be between 1 and 65535")

    log_level = source.get("BBIOS_LOG_LEVEL", "INFO").strip().upper()
    if log_level not in LOG_LEVELS:
        raise ValueError("BBIOS_LOG_LEVEL must be a standard logging level")

    api_prefix = source.get("BBIOS_API_PREFIX", "/cockpit").strip()
    if not api_prefix.startswith("/"):
        raise ValueError("BBIOS_API_PREFIX must start with /")

    return Settings(
        app_name=source.get("BBIOS_APP_NAME", "BBIOS OS").strip() or "BBIOS OS",
        app_version=source.get("BBIOS_APP_VERSION", "1.0").strip() or "1.0",
        environment=source.get("BBIOS_ENVIRONMENT", "local").strip() or "local",
        debug=parse_bool(source.get("BBIOS_DEBUG", "false"), "BBIOS_DEBUG"),
        host=source.get("BBIOS_HOST", "127.0.0.1").strip() or "127.0.0.1",
        port=port,
        log_level=log_level,
        api_prefix=api_prefix.rstrip("/") or "/",
        data_dir=Path(source.get("BBIOS_DATA_DIR", "data").strip() or "data"),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return load_settings()


def reset_settings_cache() -> None:
    get_settings.cache_clear()
