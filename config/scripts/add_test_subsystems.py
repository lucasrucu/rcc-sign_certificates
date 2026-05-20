import sys
from pathlib import Path
# Ensure project root is on sys.path when run as script
sys.path.append(str(Path(__file__).resolve().parents[1]))

from app.infrastructure.excel.loaders import load_subsystems, get_next_id_from_db
from app.infrastructure.excel.writers import write_subsystems
from app.domain.models.subsystem import Subsystem
from app.domain.enums.subsystem_enums import SubsystemStatus

# Load existing subsystems
rows = load_subsystems()
subsystems = [Subsystem.from_db_row(r) for r in rows]
existing = {s.external_id for s in subsystems}

# Test subsystems to add
to_add = ["2100-01-01", "2100-01-02", "2100-01-03"]

next_id = get_next_id_from_db("subsystems.xlsx", "id")
added = 0
for ext in to_add:
    if ext not in existing:
        subsystems.append(Subsystem(id=next_id, external_id=ext,
                                     rfcc_status=SubsystemStatus.NOT_UPLOADED,
                                     rfwcc_status=SubsystemStatus.NOT_UPLOADED))
        print(f"Added subsystem: {ext} (id={next_id})")
        next_id += 1
        added += 1

if added > 0:
    write_subsystems(subsystems)
    print("Wrote updated subsystems.xlsx")
else:
    print("No new subsystems needed")
