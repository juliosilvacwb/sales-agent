"""Domain entity for a Session Context."""
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass(frozen=True)
class SessionContext:
    """Encapsulates metadata for a conversational session.
    
    Zero framework dependencies - pure Python dataclass.
    """
    session_id: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
