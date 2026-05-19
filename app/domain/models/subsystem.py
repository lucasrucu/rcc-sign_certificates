from dataclasses import dataclass

from app.domain.enums.subsystem_enums import SubsystemStatus

@dataclass
class Subsystem:
    id: int
    external_id: str
    status: SubsystemStatus = SubsystemStatus.NOT_SIGNED
    
    @classmethod
    def from_db_row(cls, row: dict) -> "Subsystem":
        return cls(
            id=int(row["id"]),   
            external_id=row["external_id"],
            status=SubsystemStatus(row["status"]),
        )
