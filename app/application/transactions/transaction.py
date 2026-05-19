import shutil
from pathlib import Path
from datetime import datetime

from config.settings import DB_DIR


def create_db_backup() -> Path:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = DB_DIR.parent / "db_backups" / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)

    for file in DB_DIR.glob("*.xlsx"):
        shutil.copy2(file, backup_dir / file.name)

    return backup_dir


def restore_db_backup(backup_dir: Path):
    for file in backup_dir.glob("*.xlsx"):
        shutil.copy2(file, DB_DIR / file.name)
