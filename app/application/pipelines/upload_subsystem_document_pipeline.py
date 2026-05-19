from pathlib import Path

from app.infrastructure.excel.loaders import (
    load_documents,
    load_subsystems,
    load_subsystem_document_links,
)
from app.infrastructure.excel.writers import write_subsystem_document_links

from app.domain.models.document import Document
from app.domain.models.subsystem import Subsystem
from app.domain.models.subsystem_document import SubsystemDocument
from app.domain.enums.document_subsystem_enums import DocumentSubsystemStatus

from app.application.services.document_subsystem_generator import (
    generate_pims_subsystem_document_import,
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


async def run_upload_subsystem_document_pipeline():
    # --------------------------------------------------
    # 1️⃣ Load ALL required data
    # --------------------------------------------------
    document_rows = load_documents()
    subsystem_rows = load_subsystems()
    ss_doc_rows = load_subsystem_document_links()

    all_documents = [Document.from_db_row(r) for r in document_rows]
    all_subsystems = [Subsystem.from_db_row(r) for r in subsystem_rows]
    all_links = [SubsystemDocument.from_db_row(r) for r in ss_doc_rows]

    # --------------------------------------------------
    # 2️⃣ Generate subsystem–document Excel
    #    (generator internally skips already-UPLOADED)
    # --------------------------------------------------
    output_path = DATA_DIR / "processed" / "pims_subsystem_document.xlsx"

    if not generate_pims_subsystem_document_import(
        subsystems=all_subsystems,
        documents=all_documents,
        subsystem_documents=all_links,
        output_path=output_path,
    ):
        print("✅ No subsystem–document links to upload.")
        return

    # --------------------------------------------------
    # 3️⃣ Upload Excel to PIMS
    # --------------------------------------------------
    async with PIMSClient(
        config=config,
        headless=PIMS["headless"],
        timeout=PIMS["default_timeout_ms"],
    ) as client:

        await client.login()
        await client.navigate("document_subsystem_url")
        await client.upload_document_metadata(output_path, "dsDocumentsSubSystem")

    # --------------------------------------------------
    # 4️⃣ Update link statuses
    # --------------------------------------------------
    updated = 0
    for link in all_links:
        if link.status == DocumentSubsystemStatus.NOT_UPLOADED:
            link.status = DocumentSubsystemStatus.UPLOADED
            updated += 1

    # --------------------------------------------------
    # 5️⃣ Persist DB
    # --------------------------------------------------
    write_subsystem_document_links(all_links)

    print(f"✅ Uploaded subsystem–document links: {updated}")