from pathlib import Path

from app.domain.models.subsystem import Subsystem
from app.domain.enums.subsystem_enums import SubsystemStatus
from app.infrastructure.excel.loaders import load_subsystems
from app.infrastructure.excel.writers import write_subsystems
import pandas as pd


async def run_import_rfwcc_pipeline(rfwcc_file: Path) -> None:
    """
    Import RFWCC document list (Excel file with one column of subsystem IDs).
    Mark matching subsystems with rfwcc_status=NOT_SIGNED so they can be signed.
    
    Args:
        rfwcc_file: Path to Excel file with one column header containing subsystem IDs
    """
    if not rfwcc_file.exists():
        raise FileNotFoundError(f"RFWCC file not found: {rfwcc_file}")

    print(f"📂 Importing RFWCC list from: {rfwcc_file.name}")

    # ──────────────────────────────────────────────────────────────
    # 1️⃣ Load RFWCC document list (Excel with one column)
    # ──────────────────────────────────────────────────────────────
    try:
        df_rfwcc = pd.read_excel(rfwcc_file, dtype=str)
        df_rfwcc = df_rfwcc.fillna("").apply(
            lambda column: column.map(lambda v: v.strip() if isinstance(v, str) else v)
        )
        rfwcc_subsystem_ids = set(df_rfwcc.iloc[:, 0].values)
        rfwcc_subsystem_ids.discard("")  # Remove empty rows
        
        print(f"✅ Loaded {len(rfwcc_subsystem_ids)} RFWCC subsystem IDs")
    except Exception as e:
        raise RuntimeError(f"Failed to read RFWCC file: {e}")

    # ──────────────────────────────────────────────────────────────
    # 2️⃣ Load current DB subsystems
    # ──────────────────────────────────────────────────────────────
    ss_rows = load_subsystems()
    all_subsystems = [Subsystem.from_db_row(r) for r in ss_rows]

    print(f"📊 Loaded {len(all_subsystems)} subsystems from DB")

    # ──────────────────────────────────────────────────────────────
    # 3️⃣ Mark RFWCC subsystems for signing
    # ──────────────────────────────────────────────────────────────
    marked_count = 0
    not_found_count = 0

    for subsystem in all_subsystems:
        if subsystem.external_id in rfwcc_subsystem_ids:
            subsystem.rfwcc_status = SubsystemStatus.NOT_SIGNED
            marked_count += 1
            print(f"✅ Marked for RFWCC: {subsystem.external_id}")
        else:
            # Ensure RFWCC status is NOT_UPLOADED if not in list
            if subsystem.rfwcc_status != SubsystemStatus.SIGNED:
                subsystem.rfwcc_status = SubsystemStatus.NOT_UPLOADED
                not_found_count += 1

    # ──────────────────────────────────────────────────────────────
    # 4️⃣ Persist updated subsystems
    # ──────────────────────────────────────────────────────────────
    write_subsystems(all_subsystems)

    print(f"\n✅ RFWCC import complete:")
    print(f"   - {marked_count} subsystems marked for RFWCC signing")
    print(f"   - {not_found_count} subsystems not in RFWCC list")
