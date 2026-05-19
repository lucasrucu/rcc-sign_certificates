import asyncio
from pathlib import Path

from app.application.transactions.transaction import create_db_backup

from app.application.logging.import_log import ImportLog
from app.application.logging.import_report import write_import_report

from app.infrastructure.excel.loaders import load_documents
from app.infrastructure.excel.writers import write_documents

from app.domain.models.document import Document
from app.domain.enums.document_enums import DocumentStatus, DocumentDiscipline
from app.infrastructure.web.aconex_client import AconexClient
from config.settings import DATA_DIR
from config.settings import ACONEX
from config.secrets import ACONEX_CREDENTIALS

config = {
    "aconex": {
        **ACONEX,
        **ACONEX_CREDENTIALS,
    }
}

DOWNLOADS_DIR = DATA_DIR / "downloads"

async def run_download_pipeline():
    log = ImportLog()

    try:
        # ----------------------------------------------------------
        # 1️⃣ Load documents from DB (NO FILTERING)
        # ----------------------------------------------------------
        document_rows = load_documents()

        all_documents: list[Document] = [
            Document.from_db_row(row) for row in document_rows
        ]

        documents_to_download = [
            d for d in all_documents
            if d.status == DocumentStatus.NEW
        ]

        log.documents_seen = len(all_documents)
        log.documents_created = 0

        if not documents_to_download:
            print("✅ No documents to download.")
            return

        # ----------------------------------------------------------
        # 2️⃣ Download & enrich
        # ----------------------------------------------------------
        async with AconexClient(
            config=config,
            downloads_dir=DOWNLOADS_DIR,
            headless=ACONEX["headless"],
            timeout=ACONEX["default_timeout_ms"],
        ) as client:

            await client.login()
            await asyncio.sleep(5)

            for document in documents_to_download:
                try:
                    path, title, discipline = await client.download_document(
                        document.external_id
                    )

                    if title and not document.title:
                        document.title = title

                    if discipline and document.discipline == DocumentDiscipline.NO_DISC:
                        document.discipline = DocumentDiscipline(discipline)

                    document.status = DocumentStatus.DOWNLOADED
                    write_documents(all_documents) 
                    log.documents_created += 1

                except Exception as e:
                    log.documents_skipped += 1
                    log.rejected_documents.append({
                        "external_id": document.external_id,
                        "reason": str(e),
                    })


    except Exception as e:
        log.failed = True
        log.error = str(e)
        raise

    finally:
        print(log.summary())