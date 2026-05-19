from pathlib import Path
from datetime import datetime

from config.settings import DATA_DIR
from app.application.logging.import_log import ImportLog


def write_import_report(log: ImportLog) -> Path:
    """
    Writes a simple human-readable import report to data/logs/import/.
    """
    logs_dir = DATA_DIR / "logs" / "import"
    logs_dir.mkdir(parents=True, exist_ok=True)

    timestamp = log.started_at.strftime("%Y%m%d_%H%M%S")
    report_path = logs_dir / f"import_{timestamp}.txt"

    content = f"""
IMPORT REPORT
=============

Started at: {log.started_at.isoformat()}
Status: {"FAILED" if log.failed else "SUCCESS"}

Documents
---------
Seen     : {log.documents_seen}
Created  : {log.documents_created}
Skipped  : {log.documents_skipped}

Subsystems
----------
Seen     : {log.subsystems_seen}
Created  : {log.subsystems_created}
Skipped  : {log.subsystems_skipped}

Relationships
-------------
Seen     : {log.relationships_seen}
Created  : {log.relationships_created}
Skipped  : {log.relationships_skipped}

""".strip()

    # --------------------------------------------------
    # Rejected documents (explicit listing)
    # --------------------------------------------------
    if log.rejected_documents:
        content += "\n\nRejected Documents\n------------------"

        for r in log.rejected_documents:
            content += (
                f"\n- {r.external_id or '<empty>'}\n"
                f"  Reason: {r.reason}"
            )

    if log.failed and log.error:
        content += f"\n\nERROR\n-----\n{log.error}"

    report_path.write_text(content, encoding="utf-8")
    return report_path