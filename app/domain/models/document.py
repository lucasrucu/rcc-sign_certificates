from dataclasses import dataclass
from typing import Optional

from app.domain.enums.document_enums import DocumentDiscipline, DocumentStatus, DocumentType

@dataclass
class Document:
    id: int
    external_id: str
    status: DocumentStatus
    doc_type: DocumentType
    discipline: DocumentDiscipline = DocumentDiscipline.NO_DISC
    title: Optional[str] = None
    
    @classmethod
    def from_db_row(cls, row: dict) -> "Document":
        return cls(
            id=int(row["id"]),
            external_id=row["external_id"],
            status=DocumentStatus(row["status"]),
            doc_type=DocumentType(row["doc_type"]),
            discipline=DocumentDiscipline(row["disc"]),
            title=row.get("title"),
        )         
