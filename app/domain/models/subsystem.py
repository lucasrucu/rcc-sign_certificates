from dataclasses import dataclass

from app.domain.enums.subsystem_enums import SubsystemStatus

@dataclass
class Subsystem:
    id: int
    external_id: str
    rfcc_status: SubsystemStatus = SubsystemStatus.NOT_SIGNED
    rfwcc_status: SubsystemStatus = SubsystemStatus.NOT_SIGNED
    
    @classmethod
    def from_db_row(cls, row: dict) -> "Subsystem":
        return cls(
            id=int(row["id"]),   
            external_id=row["external_id"],
            rfcc_status=SubsystemStatus(row.get("rfcc_status", row.get("status", "NOT_SIGNED"))),
            rfwcc_status=SubsystemStatus(row.get("rfwcc_status", "NOT_SIGNED")),
        )
