from dataclasses import dataclass

from app.domain.enums.document_subsystem_enums import DocumentSubsystemStatus

@dataclass
class SubsystemDocument:
    id_ss: int
    id_doc: int
    status: DocumentSubsystemStatus = DocumentSubsystemStatus.NOT_UPLOADED
    
    @classmethod
    def from_db_row(cls, row: dict) -> "SubsystemDocument":
        return cls(
            id_ss=int(row["id_ss"]),
            id_doc=int(row["id_doc"]),
            status=DocumentSubsystemStatus(row["status"]),
        )
        