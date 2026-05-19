from app.domain.enums.document_enums import DocumentStatus
from app.domain.models.document import Document
from app.infrastructure.excel.loaders import load_documents
from app.infrastructure.excel.writers import write_documents
from app.infrastructure.web.pims_client import PIMSClient
from config.settings import DATA_DIR, PIMS
from config.secrets import PIMS_CREDENTIALS

config = {
    "pims": {
        **PIMS,
        **PIMS_CREDENTIALS,
    }
}

async def run_upload_files_pipeline():
    # Load all documents
    rows = load_documents()
    all_documents = [Document.from_db_row(r) for r in rows]

    # Select docs ready for file upload
    to_upload = [
        d for d in all_documents
        if d.status == DocumentStatus.UPLOADED_METADATA
    ]

    if not to_upload:
        print("✅ No documents ready for file upload.")
        return

    async with PIMSClient(
        config=config,
        headless=PIMS["headless"],
        timeout=PIMS["default_timeout_ms"],
    ) as client:

        await client.login()
        await client.navigate("documents_url")

        batch_counter = 0

        for doc in to_upload:
            pdf_path = DATA_DIR / "downloads" / f"{doc.external_id}.pdf"

            if not pdf_path.exists():
                print(f"⚠ Missing PDF for {doc.external_id}, skipping")
                continue

            try:
                result = await client.upload_document_file(
                    document_id=doc.external_id,
                    pdf_path=pdf_path,
                )

                doc.status = DocumentStatus.UPLOADED_FILE

            except Exception as e:
                print(f"❌ Failed upload {doc.external_id}: {e}")

            finally:
                batch_counter += 1
                if batch_counter >= 3:
                    write_documents(all_documents)
                    batch_counter = 0

        if batch_counter > 0:
            write_documents(all_documents)

    print(f"✅ Uploaded files for {len(to_upload)} documents.")