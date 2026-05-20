from pathlib import Path

from app.domain.models.subsystem import Subsystem
from app.domain.enums.subsystem_enums import SubsystemStatus
from app.infrastructure.excel.loaders import load_subsystems
from app.infrastructure.excel.writers import write_subsystems
import pandas as pd


async def run_mark_rfwcc_subsystems_for_final_signature_pipeline(excel_file: Path) -> None:
    """
    Mark subsystems for RFWCC final signature completion.
    Takes an Excel file with one column of subsystem IDs and marks matching 
    subsystems with rfwcc_status=PARTIALLY_SIGNED (ready for final phase).
    
    Args:
        excel_file: Path to Excel file with one column header containing subsystem IDs
    """
    if not excel_file.exists():
        raise FileNotFoundError(f"Excel file not found: {excel_file}")

    print(f"📂 Marking subsystems for RFWCC final signature from: {excel_file.name}")

    # ──────────────────────────────────────────────────────────────
    # 1️⃣ Load subsystem list from Excel (one column)
    # ──────────────────────────────────────────────────────────────
    try:
        df_excel = pd.read_excel(excel_file, dtype=str)
        df_excel = df_excel.fillna("").apply(
            lambda column: column.map(lambda v: v.strip() if isinstance(v, str) else v)
        )
        subsystem_ids = set(df_excel.iloc[:, 0].values)
        subsystem_ids.discard("")  # Remove empty rows
        
        print(f"✅ Loaded {len(subsystem_ids)} subsystem IDs from Excel")
    except Exception as e:
        raise RuntimeError(f"Failed to read Excel file: {e}")

    # ──────────────────────────────────────────────────────────────
    # 2️⃣ Load current DB subsystems
    # ──────────────────────────────────────────────────────────────
    ss_rows = load_subsystems()
    all_subsystems = [Subsystem.from_db_row(r) for r in ss_rows]

    print(f"📊 Loaded {len(all_subsystems)} subsystems from DB")

    # ──────────────────────────────────────────────────────────────
    # 3️⃣ Mark subsystems for final RFWCC signature
    # ──────────────────────────────────────────────────────────────
    marked_count = 0
    not_found_count = 0

    for subsystem in all_subsystems:
        if subsystem.external_id in subsystem_ids:
            subsystem.rfwcc_status = SubsystemStatus.PARTIALLY_SIGNED
            marked_count += 1
            print(f"✅ Marked for final RFWCC signature: {subsystem.external_id}")
        else:
            not_found_count += 1

    # ──────────────────────────────────────────────────────────────
    # 4️⃣ Persist updated subsystems
    # ──────────────────────────────────────────────────────────────
    write_subsystems(all_subsystems)

    print(f"\n✅ Final signature marking complete:")
    print(f"   - {marked_count} subsystems marked for final RFWCC signature")
    print(f"   - {not_found_count} subsystems not in list")
