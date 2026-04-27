from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class HistoryEntry:
    action: str
    actor: str
    target: str
    timestamp_utc: str


class HistoryService:
    def create_entry(self, action: str, actor: str, target: str) -> HistoryEntry:
        return HistoryEntry(
            action=action,
            actor=actor,
            target=target,
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
        )
