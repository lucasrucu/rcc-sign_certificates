from typing import List, Set

from app.domain.models.document import Document
from app.domain.models.subsystem import Subsystem
from app.domain.models.subsystem_document import SubsystemDocument


def validate_unique_ids(documents: List[Document], subsystems: List[Subsystem]) -> None:
    doc_ids = [d.id for d in documents]
    ss_ids = [s.id for s in subsystems]

    if len(doc_ids) != len(set(doc_ids)):
        raise ValueError("Duplicate Document IDs detected")

    if len(ss_ids) != len(set(ss_ids)):
        raise ValueError("Duplicate Subsystem IDs detected")


def validate_relationship_integrity(
    documents: List[Document],
    subsystems: List[Subsystem],
    links: List[SubsystemDocument],
) -> None:
    document_ids: Set[int] = {d.id for d in documents}
    subsystem_ids: Set[int] = {s.id for s in subsystems}

    for link in links:
        if link.id_doc not in document_ids:
            raise ValueError(f"Relationship references missing Document ID {link.id_doc}")

        if link.id_ss not in subsystem_ids:
            raise ValueError(f"Relationship references missing Subsystem ID {link.id_ss}")


def validate_no_duplicate_links(links: List[SubsystemDocument]) -> None:
    seen = set()

    for link in links:
        key = (link.id_ss, link.id_doc)
        if key in seen:
            raise ValueError(
                f"Duplicate relationship detected: Subsystem {link.id_ss}, Document {link.id_doc}"
            )
        seen.add(key)
