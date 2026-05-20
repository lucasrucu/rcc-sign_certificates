from app.domain.models.document import Document
from app.domain.models.subsystem import Subsystem
from app.domain.models.subsystem_document import SubsystemDocument

from app.domain.enums.document_enums import (
    DocumentStatus,
    DocumentType,
    DocumentDiscipline,
)

from app.domain.enums.subsystem_enums import SubsystemStatus


def create_documents(raw_documents: list, start_id: int) -> list:
    documents = []
    seen_external_ids = set()
    current_id = start_id

    for row in raw_documents:
        ext_id = row["external_id"]
        if ext_id in seen_external_ids:
            continue
        seen_external_ids.add(ext_id)

        documents.append(
            Document(
                id=current_id,
                external_id=ext_id,
                discipline=DocumentDiscipline(row["disc"]),
                doc_type=DocumentType(row["doc_type"]),
                status=DocumentStatus.NEW,
            )
        )
        current_id += 1

    return documents


def create_subsystems(raw_subsystems: list, start_id: int) -> list:
    subsystems = []
    seen_external_ids = set()
    current_id = start_id

    for row in raw_subsystems:
        ext_id = row["external_id"]
        if ext_id in seen_external_ids:
            continue
        seen_external_ids.add(ext_id)

        subsystems.append(
            Subsystem(
                id=current_id,
                external_id=ext_id,
                rfcc_status=SubsystemStatus.NOT_SIGNED,
                rfwcc_status=SubsystemStatus.NOT_SIGNED,
            )
        )
        current_id += 1

    return subsystems


def create_subsystem_document_links(raw_links: list) -> list[SubsystemDocument]:
    return [
        SubsystemDocument(
            id_ss=row["id_ss"],
            id_doc=row["id_doc"],
        )
        for row in raw_links
    ]