from pathlib import Path
import re
import pandas as pd

INVALID_VALUES = {"", "N/A", "NA", "NAN", "NONE"}
SUBSYSTEM_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SPLIT_PATTERN = re.compile(r"[,\n;]+")
PAREN_PATTERN = re.compile(r"\s*\(.*?\)\s*$")
DOC_PATTERN = re.compile(
    r"PR2ME(?:-[A-Z0-9]+)*-HOP(?:-[A-Z0-9]+)*"
)


def normalize_document_ids(raw_value: str) -> set[str]:
    """
    Normalize a messy Excel cell into a deduplicated set
    of canonical document IDs.
    """
    if not raw_value:
        return set()

    candidates: set[str] = set()

    for chunk in SPLIT_PATTERN.split(raw_value):
        chunk = chunk.strip()

        if not chunk:
            continue

        # Remove labels before colon (e.g. "3100-HI-005: DOC-ID")
        if ":" in chunk:
            _, chunk = chunk.split(":", 1)
            chunk = chunk.strip()

        # Remove trailing parentheses and their contents
        chunk = re.sub(PAREN_PATTERN, "", chunk)
        
        if not chunk:
            continue

        # Extract valid document ID from inside the chunk
        match = DOC_PATTERN.search(chunk.upper())
        if match:
            candidates.add(match.group(0))


    return candidates


def import_main_export(path: Path):
    """
    Import main export CSV and return:
    - raw_documents
    - raw_subsystems
    - raw_links

    Discipline is derived ONLY from column position.
    """

    df = pd.read_csv(path, header=11, dtype=str, skip_blank_lines=True)
    df.columns = [str(c).strip().replace("\n", " ").replace("\r", " ") for c in df.columns]
    df = df.fillna("")

    # Fixed column indexes (confirmed)
    STATUS_COL = 31
    SUBSYSTEM_COL = 5
    MECH_COL = 20
    PIP_COL = 21
    EI_COL = 22

    # Filter ready subsystems
    df = df[df.iloc[:, STATUS_COL].str.strip() == "Subsystem C1C Ready"]

    raw_documents = []
    raw_subsystems = {}
    raw_links = []
    rejected = []

    for _, row in df.iterrows():
        subsystem = str(row.iloc[SUBSYSTEM_COL]).strip()
        if not subsystem or subsystem.upper() in INVALID_VALUES:
            continue

        raw_subsystems[subsystem] = {
            "external_id": subsystem
        }

        def handle_doc(doc_value: str, discipline: str):
            doc = doc_value.strip()            
            doc_ids = normalize_document_ids(doc_value)

            if not doc or doc.upper() in INVALID_VALUES:
                return
            
            if not SUBSYSTEM_PATTERN.match(subsystem):
                return
            
            for doc in doc_ids:
                doc_str = str(doc)
                
                if len(doc_str) > 50:
                    rejected.append({
                        "external_id": doc,
                        "reason": "Document ID too long",
                    })
                    continue

                raw_documents.append({
                    "external_id": doc,
                    "disc": discipline,
                    "doc_type": "HOP",
                })

                raw_links.append({
                    "subsystem_external_id": subsystem,
                    "document_external_id": doc,
                    "status": "NOT_UPLOADED"
                })

        # Mechanical
        handle_doc(str(row.iloc[MECH_COL]), "Mechanical")

        # Piping
        handle_doc(str(row.iloc[PIP_COL]), "Piping")

        # E&I → always No Discipline (even if multiple)
        handle_doc(str(row.iloc[EI_COL]), "No Discipline")

    return (
        list(raw_documents),
        list(raw_subsystems.values()),
        raw_links,
        rejected
    )