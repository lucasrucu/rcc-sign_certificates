from pathlib import Path
import pandas as pd

from app.domain.models.document import Document
from app.domain.models.subsystem import Subsystem
from app.domain.models.subsystem_document import SubsystemDocument


def generate_pims_subsystem_document_import(
    subsystems: list[Subsystem],
    documents: list[Document],
    subsystem_documents: list[SubsystemDocument],
    output_path: Path,
    *,
    project_code: str = "PR2ME-COM",
) -> bool:
    """
    Generates pims_subsystem_document.xlsx for PIMS import
    from subsystem-document links.
    """

    # --------------------------------------------------
    # Build lookup maps
    # --------------------------------------------------
    subsystem_by_id = {s.id: s for s in subsystems}
    document_by_id = {d.id: d for d in documents}

    # --------------------------------------------------
    # Build rows
    # --------------------------------------------------
    rows: list[dict] = []
    
    for link in subsystem_documents:
        try:
            ss_id = int(link.id_ss)
            doc_id = int(link.id_doc)
        except (TypeError, ValueError):
            continue
        
        subsystem = subsystem_by_id.get(ss_id)
        document = document_by_id.get(doc_id)

        if not subsystem or not document:
            continue
        
        if link.status.value == link.status.UPLOADED:
            continue

        rows.append({
            "Project": project_code,
            "DocumentID": document.external_id,
            "SubSystem": subsystem.external_id,
        })

    if not rows:
        raise RuntimeError("No subsystem-document links found for PIMS import")

    df = pd.DataFrame(rows)
    
    if df.empty:
        return False

    # --------------------------------------------------
    # Ensure output directory exists
    # --------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------
    # Write Excel with required 3-row header
    # --------------------------------------------------
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        # Write data starting at row 4 (row index 3)
        df.to_excel(
            writer,
            sheet_name="Sheet1",
            index=False,
            header=False,
            startrow=3,
        )

        ws = writer.book.active

        # Row 1: Field names
        ws["A1"] = "Project"
        ws["B1"] = "DocumentID"
        ws["C1"] = "SubSystem"

        # Row 2: Descriptions
        ws["A2"] = "Project"
        ws["B2"] = "Document ID"
        ws["C2"] = "SubSystem"

        # Row 3: Data types
        ws["A3"] = "(string 50)"
        ws["B3"] = "(string 50)"
        ws["C3"] = "(string 50)"