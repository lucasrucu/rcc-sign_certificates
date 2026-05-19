from pathlib import Path

from app.application.pipelines.download_documents_pipeline import run_download_pipeline
from app.application.pipelines.import_rfcc_pipeline import run_import_rfcc_pipeline
from app.application.pipelines.upload_document_metadata_pipeline import (
    run_upload_document_metadata_pipeline,
)
from app.application.pipelines.upload_files_pipeline import run_upload_files_pipeline
from app.application.pipelines.upload_subsystem_document_pipeline import (
    run_upload_subsystem_document_pipeline,
)
from app.application.pipelines.rfcc_signing_pipeline import (
    run_rfcc_signing_pipeline,
)


async def run_full_pims_flow(main_export: Path):
    """
    Runs the complete PIMS workflow end-to-end.
    Order is intentional and must not be changed.
    """

    print("\n🚀 Starting full PIMS automation flow\n")

    # 1️⃣ Import RFCC
    run_import_rfcc_pipeline(main_export=main_export)

    # 2️⃣ Download from Aconex
    await run_download_pipeline()
    
    # 3️⃣ Upload document metadata to PIMS
    await run_upload_document_metadata_pipeline()
    
    # 4️⃣ Upload subsystem–document links to PIMS
    await run_upload_subsystem_document_pipeline()
    
    # 5️⃣ Upload files to PIMS
    await run_upload_files_pipeline()
    
    # 6️⃣ Perform RFCC signing in PIMS
    await run_rfcc_signing_pipeline()

    print("\n✅ Full PIMS automation flow completed successfully\n")