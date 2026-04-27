from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppSettings:
    app_name: str
    environment: str
    log_level: str
    log_to_file: bool
    default_locale: str
    seven_zip_exe_path: str
    seven_zip_fm_path: str
    shred_passes: int


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> AppSettings:
    project_root = Path(__file__).resolve().parents[3]
    load_dotenv(dotenv_path=project_root / ".env", override=False)

    return AppSettings(
        app_name=os.getenv("APP_NAME", "DataCasketShred"),
        environment=os.getenv("APP_ENV", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        log_to_file=_to_bool(os.getenv("LOG_TO_FILE"), default=False),
        default_locale=os.getenv("DEFAULT_LOCALE", "en"),
        seven_zip_exe_path=os.getenv("SEVEN_ZIP_EXE_PATH", r"C:\Program Files\7-Zip\7z.exe"),
        seven_zip_fm_path=os.getenv("SEVEN_ZIP_FM_PATH", r"C:\Program Files\7-Zip\7zFM.exe"),
        shred_passes=int(os.getenv("SHRED_PASSES", "1")),
    )
