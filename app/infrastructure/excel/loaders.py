from pathlib import Path
from config.settings import DB_DIR
import pandas as pd


def load_documents() -> list[dict]:
    """
    Load documents.xlsx as raw records.
    No domain logic here.
    """
    path = DB_DIR / "documents.xlsx"
    df = pd.read_excel(path, sheet_name="documents", dtype=str)
    df = df.fillna("")
    return df.to_dict(orient="records")


def load_subsystems() -> list[dict]:
    """
    Load subsystems.xlsx as raw records.
    """
    path = DB_DIR / "subsystems.xlsx"
    df = pd.read_excel(path, sheet_name="subsystems", dtype=str)
    df = df.fillna("")
    return df.to_dict(orient="records")


def load_subsystem_document_links() -> list[dict]:
    """
    Load subsystem_document.xlsx (many-to-many).
    """
    path = DB_DIR / "subsystem_document.xlsx"
    df = pd.read_excel(path, sheet_name="links", dtype=str)
    df = df.fillna("")
    return df.to_dict(orient="records")


def get_next_id_from_db(file_name: str, id_column: str = "id") -> int:
    """
    Reads an internal DB Excel file and returns next available ID.
    """
    path = DB_DIR / file_name

    if not path.exists():
        return 1

    df = pd.read_excel(path, dtype=str)

    if df.empty or id_column not in df.columns:
        return 1

    return max(df[id_column].astype(int))