from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class RejectedDocument:
    external_id: str
    reason: str

@dataclass
class ImportLog:
    started_at: datetime = field(default_factory=datetime.now)

    documents_seen: int = 0
    documents_created: int = 0
    documents_skipped: int = 0

    subsystems_seen: int = 0
    subsystems_created: int = 0
    subsystems_skipped: int = 0

    relationships_seen: int = 0
    relationships_created: int = 0
    relationships_skipped: int = 0
    
    rejected_documents: list[RejectedDocument] = field(default_factory=list)

    failed: bool = False
    error: str | None = None

    def summary(self) -> str:
        return f"""
Import Summary
--------------
Documents: {self.documents_created} created, {self.documents_skipped} skipped
Subsystems: {self.subsystems_created} created, {self.subsystems_skipped} skipped
Relationships: {self.relationships_created} created, {self.relationships_skipped} skipped
Rejected Documents: {len(self.rejected_documents)}
Status: {"FAILED" if self.failed else "SUCCESS"}
""".strip()