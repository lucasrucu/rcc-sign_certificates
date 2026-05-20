from pathlib import Path

from app.application.logging.import_log import ImportLog, RejectedDocument
from app.application.logging.import_report import write_import_report
from app.application.transactions.transaction import create_db_backup, restore_db_backup
from app.infrastructure.excel.importers import import_main_export
from app.infrastructure.excel.loaders import (
    load_documents,
    load_subsystems,
    load_subsystem_document_links,
    get_next_id_from_db,
)
from app.infrastructure.excel.writers import (
    write_documents,
    write_subsystems,
    write_subsystem_document_links,
)
from app.domain.services.object_factory import (
    create_documents,
    create_subsystems,
)
from app.domain.models.subsystem_document import SubsystemDocument
from app.domain.models.document import Document
from app.domain.models.subsystem import Subsystem
from app.domain.enums.subsystem_enums import SubsystemStatus
from app.infrastructure.web.pims_client import PIMSClient
from config.secrets import PIMS_CREDENTIALS
from config.settings import PIMS

config = {
    "pims": {
        **PIMS,
        **PIMS_CREDENTIALS,
    }
}


def create_documents_from_db(rows: list[dict]) -> list[Document]:
    return [
        Document(
            id=int(r["id"]),
            external_id=r["external_id"],
            status=r["status"],
            doc_type=r["doc_type"],
            discipline=r["disc"],
            title=r.get("title"),
        )
        for r in rows
    ]


def create_subsystems_from_db(rows: list[dict]) -> list[Subsystem]:
    return [Subsystem.from_db_row(r) for r in rows]


def create_links_from_db(rows: list[dict]) -> list[SubsystemDocument]:
    return [
        SubsystemDocument(
            id_ss=int(r["id_ss"]),
            id_doc=int(r["id_doc"]),
        )
        for r in rows
    ]


def get_subsystem_disciplines(
    subsystem_id: int,
    documents: list[Document],
    doc_ss_rows: list[SubsystemDocument],
) -> set:
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


async def run_sign_rfcc_phase1_pipeline(main_export: Path):
    """
    Combined Phase 1 pipeline:
    1. Import documents and subsystems from CSV
    2. Automatically sign all newly imported subsystems
    
    Args:
        main_export: Path to main external export (CSV)
    """
    backup_dir = create_db_backup()
    log = ImportLog()
    
    try:
        # ──────────────────────────────────────────────────────────────
        # PHASE 1a: IMPORT
        # ──────────────────────────────────────────────────────────────
        print(f"📂 Importing RFCC from: {main_export.name}")
        
        raw_documents, raw_subsystems, raw_links, rejected_documents = import_main_export(main_export)

        # Load existing DB
        existing_document_rows = load_documents()
        existing_subsystem_rows = load_subsystems()
        existing_link_rows = load_subsystem_document_links()

        existing_documents = create_documents_from_db(existing_document_rows)
        existing_subsystems = create_subsystems_from_db(existing_subsystem_rows)
        existing_links = create_links_from_db(existing_link_rows)

        # Build lookup maps
        docs_by_external = {d.external_id: d.id for d in existing_documents}
        subs_by_external = {s.external_id: s.id for s in existing_subsystems}
        existing_link_keys = {(l.id_ss, l.id_doc) for l in existing_links}
        
        log.documents_seen = len(existing_documents)
        log.subsystems_seen = len(existing_subsystems)
        log.relationships_seen = len(existing_links)
        
        for r in rejected_documents:
            log.rejected_documents.append(RejectedDocument(**r))
        
        # Filter: insert-only
        raw_documents = [
            r for r in raw_documents
            if r["external_id"] not in docs_by_external
        ]

        raw_subsystems = [
            r for r in raw_subsystems
            if r["external_id"] not in subs_by_external
        ]
        
        log.documents_created = len(raw_documents)
        log.documents_skipped = log.documents_seen - log.documents_created
        
        log.subsystems_created = len(raw_subsystems)
        log.subsystems_skipped = log.subsystems_seen - log.subsystems_created

        # Create new domain entities
        next_doc_id = get_next_id_from_db("documents.xlsx")
        next_ss_id = get_next_id_from_db("subsystems.xlsx")

        new_documents = create_documents(raw_documents, start_id=next_doc_id)
        new_subsystems = create_subsystems(raw_subsystems, start_id=next_ss_id)

        # Extend lookup maps
        for d in new_documents:
            docs_by_external[d.external_id] = d.id
        for s in new_subsystems:
            subs_by_external[s.external_id] = s.id

        # Merge relationships (insert-only)
        new_links: list[SubsystemDocument] = []

        for link in raw_links:
            ss_ext = link["subsystem_external_id"]
            doc_ext = link["document_external_id"]

            if ss_ext not in subs_by_external or doc_ext not in docs_by_external:
                continue

            key = (subs_by_external[ss_ext], docs_by_external[doc_ext])

            if key in existing_link_keys:
                continue

            new_links.append(
                SubsystemDocument(id_ss=key[0], id_doc=key[1])
            )
            
        log.relationships_created = len(new_links)
        log.relationships_skipped = log.relationships_seen - log.relationships_created

        # Persist merged DB
        all_documents = existing_documents + new_documents
        all_subsystems = existing_subsystems + new_subsystems
        all_links = existing_links + new_links
        
        write_documents(all_documents)
        write_subsystems(all_subsystems)
        write_subsystem_document_links(all_links)
        
        print(f"\n✅ Import complete: {log.documents_created} docs, {log.subsystems_created} subsystems")

        # ──────────────────────────────────────────────────────────────
        # PHASE 1b: SIGN (automatically sign all newly imported subsystems)
        # ──────────────────────────────────────────────────────────────
        print(f"\n🔐 Starting RFCC signing phase...")

        # Reload to get newly created subsystems
        ss_rows = load_subsystems()
        all_subsystems = [Subsystem.from_db_row(r) for r in ss_rows]
        
        to_sign = [
            s for s in all_subsystems
            if s.rfcc_status == SubsystemStatus.NOT_SIGNED
        ]

        if not to_sign:
            print("\n✅ No subsystems to sign.")
            write_import_report(log)
            return

        print(f"✅ Signing {len(to_sign)} subsystems...")

        async with PIMSClient(
            config=config,
            headless=PIMS["headless"],
            timeout=PIMS["default_timeout_ms"],
        ) as client:

            await client.login()
            await client.navigate("certificates_url")
            await client.prepare_certificates_subsystem_page()

            batch_counter = 0
            signed_count = 0

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
                            f"skipping."
                        )
                        continue
                    
                    result = await client.sign_rfcc_for_subsystem(
                        subsystem_external_id=subsystem.external_id,
                        disciplines=disciplines,
                    )

                    if result == "SIGNED":
                        subsystem.rfcc_status = SubsystemStatus.SIGNED
                        signed_count += 1
                        print(f"✅ RFCC signed: {subsystem.external_id}")

                    elif result == "NOT_FOUND":
                        subsystem.rfcc_status = SubsystemStatus.NOT_UPLOADED
                        print(
                            f"⚠ Subsystem not found, marked NOT_UPLOADED: "
                            f"{subsystem.external_id}"
                        )

                except Exception as e:
                    print(f"❌ Error signing {subsystem.external_id}: {e}")

                finally:
                    batch_counter += 1
                    if batch_counter >= 3:
                        write_subsystems(all_subsystems)
                        batch_counter = 0

            if batch_counter > 0:
                write_subsystems(all_subsystems)

        print(f"\n✅ RFCC Phase 1 complete: {signed_count} signed")
        write_import_report(log)
    
    except Exception as e:
        restore_db_backup(backup_dir)
        log.failed = True
        log.error = str(e)
        write_import_report(log)
        raise
    
    finally:
        print(log.summary())
