from pathlib import Path
import pandas as pd

# --------------------------------------------------
# Output directory: RFCC Automation v2/data/db
# --------------------------------------------------
BASE_DIR = Path(__file__).resolve().parents[2] / "data" / "db"
BASE_DIR.mkdir(parents=True, exist_ok=True)


def save_text_excel(df: pd.DataFrame, path: Path, sheet_name: str):
    """
    Save DataFrame to Excel ensuring all cells are TEXT.
    """
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name=sheet_name, index=False)
        ws = writer.sheets[sheet_name]
        for col in ws.columns:
            for cell in col:
                cell.number_format = "@"


# --------------------------------------------------
# 1️⃣ Documents table
# --------------------------------------------------
documents_df = pd.DataFrame(columns=[
    "id",            # internal ID
    "external_id",   # external system ID (string)
    "title",
    "disc",
    "status",        # DocumentStatus enum value
    "doc_type",      # DocumentType enum value (HOP / SDD)
])

save_text_excel(
    documents_df,
    BASE_DIR / "documents.xlsx",
    "documents"
)


# --------------------------------------------------
# 2️⃣ Subsystems table
# --------------------------------------------------
subsystems_df = pd.DataFrame(columns=[
    "id",            # internal ID
    "external_id",   # external system ID (string)
    "status",        # SubsystemStatus enum value
])

save_text_excel(
    subsystems_df,
    BASE_DIR / "subsystems.xlsx",
    "subsystems"
)


# --------------------------------------------------
# 3️⃣ Subsystem–Document relationship table
# (internal IDs only, NO extra metadata)
# --------------------------------------------------
links_df = pd.DataFrame(columns=[
    "id_ss",         # internal Subsystem ID
    "id_doc",        # internal Document ID
])

save_text_excel(
    links_df,
    BASE_DIR / "subsystem_document.xlsx",
    "links"
)


print("✅ Excel schema files created successfully in:", BASE_DIR)
