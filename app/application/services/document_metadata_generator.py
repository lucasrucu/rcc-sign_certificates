from pathlib import Path
import pandas as pd

from app.domain.models.document import Document
from app.domain.enums.document_enums import DocumentStatus


def generate_document_metadata(
    documents: list[Document],
    output_path: Path,
):
    """
    Generates document_metadata.xlsx for PIMS import
    from documents with status == DOWNLOADED.
    """

    # --------------------------------------------------
    # Filter eligible documents
    # --------------------------------------------------
    rows: list[dict] = []

    for doc in documents:
        if doc.status != DocumentStatus.DOWNLOADED:
            continue

        rows.append({
            "DocumentID": doc.external_id,
            "DocumentType": doc.doc_type.value,   # e.g. "HOP"
            "Title": doc.title or "",
        })

    if not rows:
        raise RuntimeError("No DOWNLOADED documents found for metadata upload")

    df = pd.DataFrame(rows)

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
        ws["A1"] = "DocumentID"
        ws["B1"] = "DocumentType"
        ws["C1"] = "Title"

        # Row 2: Descriptions
        ws["A2"] = "Document ID"
        ws["B2"] = "Document Type"
        ws["C2"] = "Title"

        # Row 3: Data types
        ws["A3"] = "(string 50)"
        ws["B3"] = "(string 16)"
        ws["C3"] = "(string 255)"