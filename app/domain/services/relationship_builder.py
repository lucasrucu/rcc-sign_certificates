from collections import defaultdict
from typing import Dict, List, Tuple

from app.domain.models.document import Document
from app.domain.models.subsystem import Subsystem
from app.domain.models.subsystem_document import SubsystemDocument


def build_relationships(
    subsystems: List[Subsystem],
    documents: List[Document],
    links: List[SubsystemDocument],
) -> Tuple[
    Dict[int, Subsystem],
    Dict[int, Document],
    Dict[int, List[Document]],
    Dict[int, List[Subsystem]],
]:
    """
    Builds in-memory many-to-many relationships.

    Returns:
    - subsystems_by_id
    - documents_by_id
    - documents_by_subsystem_id
    - subsystems_by_document_id
    """

    subsystems_by_id = {s.id: s for s in subsystems}
    documents_by_id = {d.id: d for d in documents}

    documents_by_subsystem_id = defaultdict(list)
    subsystems_by_document_id = defaultdict(list)

    for link in links:
        subsystem = subsystems_by_id.get(link.id_ss)
        document = documents_by_id.get(link.id_doc)

        if subsystem and document:
            documents_by_subsystem_id[subsystem.id].append(document)
            subsystems_by_document_id[document.id].append(subsystem)

    return (
        subsystems_by_id,
        documents_by_id,
        documents_by_subsystem_id,
        subsystems_by_document_id,
    )