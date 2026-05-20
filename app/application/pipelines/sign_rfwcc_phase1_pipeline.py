from pathlib import Path

from app.domain.models.subsystem import Subsystem
from app.domain.enums.subsystem_enums import SubsystemStatus
from app.infrastructure.excel.loaders import load_subsystems
from app.infrastructure.excel.writers import write_subsystems
from app.infrastructure.web.pims_client import PIMSClient
from config.secrets import PIMS_CREDENTIALS
from config.settings import PIMS
import pandas as pd

config = {
    "pims": {
        **PIMS,
        **PIMS_CREDENTIALS,
    }
}


async def run_sign_rfwcc_phase1_pipeline(excel_file: Path) -> None:
    """
    Combined RFWCC Phase 1 pipeline:
    1. Load subsystem list from Excel
    2. Mark matching subsystems as NOT_SIGNED (ready for Phase 1 signing)
    3. Automatically sign all marked subsystems
    
    Args:
        excel_file: Path to Excel file with one column header containing subsystem IDs
    """
    if not excel_file.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_file}")

    print(f"📂 RFWCC Phase 1 from: {excel_file.name}")

    # ──────────────────────────────────────────────────────────────
    # PHASE 1a: MARK FOR SIGNING (like import_rfwcc_pipeline)
    # ──────────────────────────────────────────────────────────────
    try:
        df_rfwcc = pd.read_excel(excel_file, dtype=str)
        df_rfwcc = df_rfwcc.fillna("").apply(
            lambda column: column.map(lambda v: v.strip() if isinstance(v, str) else v)
        )
        rfwcc_subsystem_ids = set(df_rfwcc.iloc[:, 0].values)
        rfwcc_subsystem_ids.discard("")  # Remove empty rows
        
        print(f"✅ Loaded {len(rfwcc_subsystem_ids)} subsystem IDs from Excel")
    except Exception as e:
        raise RuntimeError(f"Failed to read Excel file: {e}")

    # Load current DB subsystems
    ss_rows = load_subsystems()
    all_subsystems = [Subsystem.from_db_row(r) for r in ss_rows]

    print(f"📊 Loaded {len(all_subsystems)} subsystems from DB")

    # Mark matching subsystems for signing
    marked_count = 0

    for subsystem in all_subsystems:
        if subsystem.external_id in rfwcc_subsystem_ids:
            subsystem.rfwcc_status = SubsystemStatus.NOT_SIGNED
            marked_count += 1
        else:
            # Ensure RFWCC status is NOT_UPLOADED if not in list
            if subsystem.rfwcc_status != SubsystemStatus.SIGNED:
                subsystem.rfwcc_status = SubsystemStatus.NOT_UPLOADED

    # Persist after marking
    write_subsystems(all_subsystems)
    print(f"✅ Marked {marked_count} subsystems for RFWCC Phase 1 signing")

    # ──────────────────────────────────────────────────────────────
    # PHASE 1b: SIGN (like rfwcc_signing_pipeline)
    # ──────────────────────────────────────────────────────────────
    print(f"\n🔐 Starting RFWCC Phase 1 signing...")

    to_sign = [
        s for s in all_subsystems
        if s.rfwcc_status == SubsystemStatus.NOT_SIGNED
    ]

    if not to_sign:
        print("\n✅ No subsystems to sign.")
        return

    print(f"✅ Signing {len(to_sign)} subsystems...")

    async with PIMSClient(
        config=config,
        headless=PIMS["headless"],
        timeout=PIMS["default_timeout_ms"],
    ) as client:

        await client.login()

        batch_counter = 0
        signed_count = 0

        for subsystem in to_sign:
            try:
                result = await client.sign_rfwcc_for_subsystem(
                    subsystem_external_id=subsystem.external_id,
                )

                if result == "SIGNED":
                    subsystem.rfwcc_status = SubsystemStatus.PARTIALLY_SIGNED
                    signed_count += 1
                    print(f"✅ RFWCC Phase 1 signed: {subsystem.external_id}")

                elif result == "NOT_FOUND":
                    subsystem.rfwcc_status = SubsystemStatus.NOT_UPLOADED
                    print(
                        f"⚠ Subsystem not found, marked NOT_UPLOADED: "
                        f"{subsystem.external_id}"
                    )
                else:
                    print(f"❌ RFWCC Phase 1 signing failed for {subsystem.external_id}: {result}")

            except Exception as e:
                print(f"❌ Error signing {subsystem.external_id}: {e}")

            finally:
                batch_counter += 1
                if batch_counter >= 3:
                    write_subsystems(all_subsystems)
                    batch_counter = 0

        if batch_counter > 0:
            write_subsystems(all_subsystems)

    print(f"\n✅ RFWCC Phase 1 complete: {signed_count} signed")
