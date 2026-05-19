from typing import List, Dict

from app.domain.models.document import Document
from app.domain.models.subsystem import Subsystem
from app.domain.models.subsystem_document import SubsystemDocument


def map_external_links_to_internal(
    raw_links: List[dict],
    documents: List[Document],
    subsystems: List[Subsystem],
) -> List[SubsystemDocument]:
    """
    Maps external ID relationships to internal ID relationships.

    raw_links example:
    {
        "subsystem_external_id": "SS-001",
        "document_external_id": "DOC-123"
    }
    """

    # Build lookup tables
    doc_by_external_id: Dict[str, Document] = {
        d.external_id: d for d in documents
    }

    ss_by_external_id: Dict[str, Subsystem] = {
        s.external_id: s for s in subsystems
    }

    links: List[SubsystemDocument] = []

    for row in raw_links:
        ss_ext = row["subsystem_external_id"]
        doc_ext = row["document_external_id"]

        subsystem = ss_by_external_id.get(ss_ext)
        document = doc_by_external_id.get(doc_ext)

        # Skip silently or raise later via validation
        if not subsystem or not document:
            continue

        links.append(
            SubsystemDocument(
                id_ss=subsystem.id,
                id_doc=document.id,
            )
        )

    return links