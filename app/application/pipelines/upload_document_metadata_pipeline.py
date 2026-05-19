from pathlib import Path

from app.infrastructure.excel.loaders import load_documents
from app.infrastructure.excel.writers import write_documents

from app.domain.models.document import Document
from app.domain.enums.document_enums import DocumentStatus

from app.application.services.document_metadata_generator import (
    generate_document_metadata,
)
from app.infrastructure.web.pims_client import PIMSClient

from config.settings import DATA_DIR, PIMS
from config.secrets import PIMS_CREDENTIALS

config = {
    "pims": {
        **PIMS,
        **PIMS_CREDENTIALS,
    }
}

async def run_upload_document_metadata_pipeline():
    # --------------------------------------------------
    # 1️⃣ Load ALL documents
    # --------------------------------------------------
    document_rows = load_documents()
    all_documents = [Document.from_db_row(row) for row in document_rows]

    # --------------------------------------------------
    # 2️⃣ Filter DOWNLOADED documents
    # --------------------------------------------------
    documents_to_upload = [
        d for d in all_documents
        if d.status == DocumentStatus.DOWNLOADED
        and d.title
    ]

    if not documents_to_upload:
        print("✅ No documents to upload.")
        return

    # --------------------------------------------------
    # 3️⃣ Generate metadata Excel
    # --------------------------------------------------
    metadata_path = DATA_DIR / "processed" / "document_metadata.xlsx"

    generate_document_metadata(
        documents=all_documents,
        output_path=metadata_path,
    )

    # --------------------------------------------------
    # 4️⃣ Upload metadata to PIMS
    # --------------------------------------------------
    async with PIMSClient(
        config=config,
        headless=PIMS["headless"],
        timeout=PIMS["default_timeout_ms"],
    ) as client:

        await client.login()
        await client.navigate("documents_url")
        await client.upload_document_metadata(metadata_path)

    # --------------------------------------------------
    # 5️⃣ Update document statuses
    # --------------------------------------------------
    for doc in documents_to_upload:
        doc.status = DocumentStatus.UPLOADED_METADATA

    # --------------------------------------------------
    # 6️⃣ Persist DB
    # --------------------------------------------------
    write_documents(all_documents)

    print(f"✅ Uploaded metadata for {len(documents_to_upload)} documents.")