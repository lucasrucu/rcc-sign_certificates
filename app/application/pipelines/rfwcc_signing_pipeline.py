from app.domain.enums.document_enums import DocumentDiscipline
from app.domain.enums.subsystem_enums import SubsystemStatus
from app.domain.models.document import Document
from app.domain.models.subsystem import Subsystem
from app.domain.models.subsystem_document import SubsystemDocument
from app.infrastructure.excel.loaders import load_documents, load_subsystem_document_links, load_subsystems
from app.infrastructure.excel.writers import write_subsystems
from app.infrastructure.web.pims_client import PIMSClient
from config.secrets import PIMS_CREDENTIALS
from config.settings import PIMS

config = {
    "pims": {
        **PIMS,
        **PIMS_CREDENTIALS,
    }
}


def get_subsystem_disciplines(
    subsystem_id: int,
    documents: list[Document],
    doc_ss_rows: list[SubsystemDocument],
) -> set[int]:
    """Get all disciplines associated with a subsystem via document links."""
    doc_ids = {
        r.id_doc
        for r in doc_ss_rows
            if r.id_ss == subsystem_id
    }

    disciplines = {
        d.discipline
        for d in documents
        if d.id in doc_ids and d.discipline
    }
    
    return disciplines


async def run_rfwcc_signing_pipeline():
    """
    Sign RFWCC certificates for subsystems marked with rfwcc_status=NOT_SIGNED.
    Similar to RFCC pipeline but uses sign_rfwcc_for_subsystem.
    """
    ss_rows = load_subsystems()
    doc_rows = load_documents()
    ss_doc_rows = load_subsystem_document_links()
    all_subsystems = [Subsystem.from_db_row(r) for r in ss_rows]
    all_documents = [Document.from_db_row(r) for r in doc_rows]
    all_links = [SubsystemDocument.from_db_row(r) for r in ss_doc_rows]
    
    not_uploaded = [
        s for s in all_subsystems
        if s.rfwcc_status == SubsystemStatus.NOT_UPLOADED
    ]

    to_sign = [
        s for s in all_subsystems
        if s.rfwcc_status == SubsystemStatus.NOT_SIGNED
    ]

    # --------------------------------------------------
    # Inform user BEFORE signing
    # --------------------------------------------------
    if not_uploaded:
        print("\n=== Subsystems NOT UPLOADED for RFWCC (will be skipped) ===")
    for s in not_uploaded:
        print(f" - {s.external_id}")

    if not to_sign:
        print("\n✅ No subsystems pending RFWCC signing.")
        return

    async with PIMSClient(
        config=config,
        headless=PIMS["headless"],
        timeout=PIMS["default_timeout_ms"],
    ) as client:

        await client.login()
        await client.navigate("certificates_url")
        await client.prepare_certificates_subsystem_page()

        batch_counter = 0

        for subsystem in to_sign:
            try:
                disciplines = get_subsystem_disciplines(
                    subsystem_id=subsystem.id,
                    documents=all_documents,
                    doc_ss_rows=all_links,
                )
                
                if not disciplines:
                    print(
                        f"⚠ No disciplines found for {subsystem.external_id}, "
                        f"continuing RFWCC signing with NA check items."
                    )
                
                result = await client.sign_rfwcc_for_subsystem(
                    subsystem_external_id=subsystem.external_id,
                    disciplines=disciplines,
                )

                if result == "SIGNED":
                    subsystem.rfwcc_status = SubsystemStatus.SIGNED
                    print(f"✅ RFWCC signed: {subsystem.external_id}")

                elif result == "PARTIAL":
                    subsystem.rfwcc_status = SubsystemStatus.PARTIALLY_SIGNED
                    print(
                        f"⚠ RFWCC initial signing completed for {subsystem.external_id}, "
                        f"marked PARTIALLY_SIGNED"
                    )

                elif result == "NOT_FOUND":
                    subsystem.rfwcc_status = SubsystemStatus.NOT_UPLOADED
                    print(
                        f"⚠ Subsystem not found for RFWCC, marked NOT_UPLOADED: "
                        f"{subsystem.external_id}"
                    )

            except Exception as e:
                print(
                    f"❌ Error signing RFWCC for {subsystem.external_id}: {e}"
                )

            finally:
                batch_counter += 1
                if batch_counter >= 3:
                    write_subsystems(all_subsystems)
                    batch_counter = 0

        if batch_counter > 0:
            write_subsystems(all_subsystems)

    print("\n✅ RFWCC signing pipeline completed.")
