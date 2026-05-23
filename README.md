# RFCC Automation v2

Python automation for RFCC document handling.

This project uses Excel (`.xlsx`) as its persistence layer and Playwright
to automate external systems (Aconex, PIMs).

---

## Architecture (Simplified Clean Architecture)

This project follows a **lean Clean Architecture**, adapted for automation.
app/
├── domain/ # Business meaning and rules
│ ├── models/ # Document, Subsystem, relationships
│ ├── enums/ # Status and type enums
│ └── services/ # Object creation, relationships, validation
│
├── infrastructure/ # External systems and I/O
│ ├── excel/ # Excel loaders and writers
│ ├── web/ # Playwright clients (Aconex, PIMs)
│ └── reporting/ # PDF / report generation
│
├── application/ # Workflow orchestration
│ └── pipeline.py
│
└── main.py # Entry point

---

## Core Principles

- **Domain is the source of truth**
- **Excel is persistence, not logic**
- **Infrastructure moves data**
- **Application controls execution order**

---

## Data Storage

Excel files act as a lightweight database and live here:

data/db/
├── documents.xlsx
├── subsystems.xlsx
└── subsystem_document.xlsx

- All IDs are stored as **TEXT**
- Relationships use **internal IDs only**

---

## Data Flow

Excel (.xlsx)
↓
Infrastructure loaders (raw dicts)
↓
Domain services (objects, rules, relationships)
↓
Application pipeline (workflow)
↓
Infrastructure writers / automation / reports

---

## Scope (Current)

- Document and Subsystem entities
- Many-to-many relationships
- Excel-based persistence
- Playwright-based automation
- Status-driven workflow

Detailed rules and edge cases are added incrementally as needed.

---

## Run

Start the command-line entry point with:

```powershell
python main.py
```

Launch the GUI launcher with:

```powershell
python main.py --gui
```

GUI mode is a normal Tkinter application, so the terminal will stay attached while the window is open. Close the window to return to the prompt.
