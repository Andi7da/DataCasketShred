from dataclasses import dataclass
import json
from pathlib import Path


@dataclass
class AppState:
    last_archive_path: str = ""
    last_source_dir: str = ""


def _state_file_path() -> Path:
    return Path.home() / ".datacasketshred_state.json"


def load_state() -> AppState:
    state_path = _state_file_path()
    if not state_path.exists():
        return AppState()

    raw = json.loads(state_path.read_text(encoding="utf-8"))
    return AppState(
        last_archive_path=raw.get("last_archive_path", ""),
        last_source_dir=raw.get("last_source_dir", ""),
    )


def save_state(state: AppState) -> None:
    state_path = _state_file_path()
    state_path.write_text(
        json.dumps(
            {
                "last_archive_path": state.last_archive_path,
                "last_source_dir": state.last_source_dir,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
