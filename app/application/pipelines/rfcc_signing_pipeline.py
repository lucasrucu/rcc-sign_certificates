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

def get_subsystem_disciplines1(
    subsystem_id: int,
    documents: list[Document],
    doc_ss_rows: list[SubsystemDocument],
) -> set[int]:
    print("-" * 60)
    print(f"🔍 Finding disciplines for subsystem {subsystem_id}")

    print("\n🔗 Inspecting Subsystem–Document links (doc_ss_rows):")
    matched_rows = []
    
    counter = 0

    for r in doc_ss_rows:
        counter += 1
        print(
            f"  SS_LINK → id_ss={r.id_ss!r}, id_doc={r.id_doc!r} "
            f"(type id_ss={type(r.id_ss)}, type id_doc={type(r.id_doc)})"
        )
        if r.id_ss == subsystem_id:
            print("    ✅ MATCHED subsystem")
            matched_rows.append(r)
        else:
            print("    ❌ not this subsystem")
        if counter >= 10:
            print("⏸ Reached 10 rows, pausing for review...")
            input("Press Enter to continue...")
            counter = 0    
        

    doc_ids = {r.id_doc for r in matched_rows}
    print(f"\n📄 Collected document IDs for subsystem: {doc_ids}")

    print("\n📚 Inspecting Documents:")
    disciplines = set()

    for d in documents:
        print(
            f"  DOC → id={d.id!r}, external_id={d.external_id!r}, "
            f"discipline={d.disc!r}"
        )

        if d.id in doc_ids:
            print("    ✅ Document linked to subsystem")
            if d.disc and d.disc != DocumentDiscipline.NO_DISC:
                disciplines.add(d.disc)
                print(f"      ➕ Added discipline: {d.disc}")
            else:
                print("      ⚠ Document has NO_DISC or empty discipline")
        else:
            print("    ❌ Document not linked")

    print(f"\n✅ FINAL disciplines set: {disciplines}")
    input("⏸ DEBUG PAUSE – Press Enter to continue...")

    return disciplines

async def run_rfcc_signing_pipeline():
    ss_rows = load_subsystems()
    doc_rows = load_documents()
    ss_doc_rows = load_subsystem_document_links()
    all_subsystems = [Subsystem.from_db_row(r) for r in ss_rows]
    all_documents = [Document.from_db_row(r) for r in doc_rows]
    all_links = [SubsystemDocument.from_db_row(r) for r in ss_doc_rows]
    
    not_uploaded = [
        s for s in all_subsystems
        if s.status == SubsystemStatus.NOT_UPLOADED
    ]

    to_sign = [
        s for s in all_subsystems
        if s.status == SubsystemStatus.NOT_SIGNED
    ]

    # --------------------------------------------------
    # Inform user BEFORE signing
    # --------------------------------------------------
    if not_uploaded:
        print("\n=== Subsystems NOT UPLOADED (will be skipped) ===")
    for s in not_uploaded:
        print(f" - {s.external_id}")

    if not to_sign:
        print("\n✅ No subsystems pending RFCC signing.")
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
                        f"skipping signing."
                    )
                    continue
                
                result = await client.sign_rfcc_for_subsystem(
                    subsystem_external_id=subsystem.external_id,
                    disciplines=disciplines,
                )

                if result == "SIGNED":
                    subsystem.status = SubsystemStatus.SIGNED
                    print(f"✅ RFCC signed: {subsystem.external_id}")

                elif result == "NOT_FOUND":
                    subsystem.status = SubsystemStatus.NOT_UPLOADED
                    print(
                        f"⚠ Subsystem not found, marked NOT_UPLOADED: "
                        f"{subsystem.external_id}"
                    )

            except Exception as e:
                print(
                    f"❌ Error signing {subsystem.external_id}: {e}"
                )

            finally:
                batch_counter += 1
                if batch_counter >= 3:
                    write_subsystems(all_subsystems)
                    batch_counter = 0

        if batch_counter > 0:
            write_subsystems(all_subsystems)


    print("\n✅ RFCC signing pipeline completed.")