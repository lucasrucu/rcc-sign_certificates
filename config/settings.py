from pathlib import Path

# --------------------------------------------------
# Project paths
# --------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
DB_DIR = DATA_DIR / "db"
DOWNLOADS_DIR = DATA_DIR / "downloads"
LOGS_DIR = DATA_DIR / "logs"

# --------------------------------------------------
# Aconex (non-secret settings)
# --------------------------------------------------

ACONEX = {
    "base_url": "https://constructionandengineering.oraclecloud.com",
    "login_url": "https://constructionandengineering.oraclecloud.com/idcsLogin",
    "projects_url": "https://constructionandengineering.oraclecloud.com/web/home/projects",
    "project_name": "BATU HIJAU EP",
    "headless": False, # Set to True if you don't want to see the browser during downloads
    "default_timeout_ms": 5_000, # 5 seconds timeout for Playwright actions
}

PIMS = {
    "login_url": "https://amnt-pr2me.pimshosting.com/login",
    "documents_url": "https://amnt-pr2me.pimshosting.com/cms-documents?Domain=PR2ME",
    "certificates_url": "https://amnt-pr2me.pimshosting.com/cms-certificates?Domain=PR2ME",
    "document_subsystem_url": "https://amnt-pr2me.pimshosting.com/cms-documents-subsystems?Domain=PR2ME",
    "headless": False, # Set to True if you don't want to see the browser during uploads
    "default_timeout_ms": 5_000, # 5 seconds timeout for Playwright actions
}