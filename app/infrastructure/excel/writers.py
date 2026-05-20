from pathlib import Path
import pandas as pd

from config.settings import DB_DIR
from app.domain.models.document import Document
from app.domain.models.subsystem import Subsystem
from app.domain.models.subsystem_document import SubsystemDocument


def _write_text_excel(df: pd.DataFrame, path: Path, sheet_name: str):
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        ws = writer.sheets[sheet_name]
        for col in ws.columns:
            for cell in col:
                cell.number_format = "@"


def write_documents(documents: list[Document]) -> None:
    rows = [
        {
            "id": str(d.id),
            "external_id": d.external_id,
            "title": d.title,
            "disc": d.discipline.value,
            "status": d.status.value,
            "doc_type": d.doc_type.value,
        }
        for d in documents
    ]

    df = pd.DataFrame(rows)
    _write_text_excel(df, DB_DIR / "documents.xlsx", "documents")


def write_subsystems(subsystems: list[Subsystem]) -> None:
    rows = [
        {
            "id": str(s.id),
            "external_id": s.external_id,
            "rfcc_status": s.rfcc_status.value,
            "rfwcc_status": s.rfwcc_status.value,
        }
        for s in subsystems
    ]

    df = pd.DataFrame(rows)
    _write_text_excel(df, DB_DIR / "subsystems.xlsx", "subsystems")


def write_subsystem_document_links(links: list[SubsystemDocument]) -> None:
    rows = [
        {
            "id_ss": str(l.id_ss),
            "id_doc": str(l.id_doc),
            "status": l.status.value,
        }
        for l in links
    ]

    df = pd.DataFrame(rows)
    _write_text_excel(df, DB_DIR / "subsystem_document.xlsx", "links")