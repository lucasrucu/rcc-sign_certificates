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
from app.domain.enums.document_enums import (
    DocumentStatus,
    DocumentType,
    DocumentDiscipline,
)
from app.domain.enums.subsystem_enums import SubsystemStatus


# ------------------------------------------------------------------
# ✅ Rehydrate DB rows → domain objects
# ------------------------------------------------------------------

def create_documents_from_db(rows: list[dict]) -> list[Document]:
    return [
        Document(
            id=int(r["id"]),
            external_id=r["external_id"],
            status=DocumentStatus(r["status"]),
            doc_type=DocumentType(r["doc_type"]),
            discipline=DocumentDiscipline(r["disc"]),
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


# ------------------------------------------------------------------
# ✅ Insert‑only import pipeline
# ------------------------------------------------------------------

def run_import_rfcc_pipeline(main_export: Path):
    backup_dir = create_db_backup()
    log = ImportLog()
    
    try:
        # --------------------------------------------------------------
        # 1️⃣ Import external Excel (raw, cleaned strings)
        # --------------------------------------------------------------
        raw_documents, raw_subsystems, raw_links, rejected_documents = import_main_export(main_export)

        # --------------------------------------------------------------
        # 2️⃣ Load existing DB (raw rows)
        # --------------------------------------------------------------
        existing_document_rows = load_documents()
        existing_subsystem_rows = load_subsystems()
        existing_link_rows = load_subsystem_document_links()

        # Rehydrate into domain objects
        existing_documents = create_documents_from_db(existing_document_rows)
        existing_subsystems = create_subsystems_from_db(existing_subsystem_rows)
        existing_links = create_links_from_db(existing_link_rows)

        # Build lookup maps
        docs_by_external = {d.external_id: d.id for d in existing_documents}
        subs_by_external = {s.external_id: s.id for s in existing_subsystems}
        existing_link_keys = {(l.id_ss, l.id_doc) for l in existing_links}
        
        # Log existing counts
        log.documents_seen = len(existing_documents)
        log.subsystems_seen = len(existing_subsystems)
        log.relationships_seen = len(existing_links)
        
        # Log rejected documents from import step
        for r in rejected_documents:
            log.rejected_documents.append(RejectedDocument(**r))
        
        # --------------------------------------------------------------
        # 3️⃣ FILTER: insert‑only (skip existing entities)
        # --------------------------------------------------------------
        raw_documents = [
            r for r in raw_documents
            if r["external_id"] not in docs_by_external
        ]

        raw_subsystems = [
            r for r in raw_subsystems
            if r["external_id"] not in subs_by_external
        ]
        
        # Log new counts after filtering
        log.documents_created = len(raw_documents)
        log.documents_skipped = log.documents_seen - log.documents_created
        
        log.subsystems_created = len(raw_subsystems)
        log.subsystems_skipped = log.subsystems_seen - log.subsystems_created

        # --------------------------------------------------------------
        # 4️⃣ Create ONLY new domain entities
        # --------------------------------------------------------------
        next_doc_id = get_next_id_from_db("documents.xlsx")
        next_ss_id = get_next_id_from_db("subsystems.xlsx")

        new_documents = create_documents(raw_documents, start_id=next_doc_id)
        new_subsystems = create_subsystems(raw_subsystems, start_id=next_ss_id)

        # Extend lookup maps
        for d in new_documents:
            docs_by_external[d.external_id] = d.id
        for s in new_subsystems:
            subs_by_external[s.external_id] = s.id

        # --------------------------------------------------------------
        # 5️⃣ Merge relationships (insert‑only)
        # --------------------------------------------------------------
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
            
        # Log relationship counts
        log.relationships_created = len(new_links)
        log.relationships_skipped = log.relationships_seen - log.relationships_created

        # --------------------------------------------------------------
        # 6️⃣ Persist MERGED DB (domain objects ONLY)
        # --------------------------------------------------------------
        write_documents(existing_documents + new_documents)
        write_subsystems(existing_subsystems + new_subsystems)
        write_subsystem_document_links(existing_links + new_links)
        
        # Success report
        write_import_report(log)
    
    except Exception as e:
        restore_db_backup(backup_dir)
        log.failed = True
        log.error = str(e)
        write_import_report(log)
        raise
    
    finally:
        print(log.summary())