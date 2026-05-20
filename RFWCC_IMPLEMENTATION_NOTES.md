# RFWCC Certificate Support - Implementation Summary

## Overview

Added dual-certificate support to the RFCC Automation system. The system now handles both RFCC and RFWCC certificates with independent signing workflows.

## Changes Made

### 1. **Database Schema Updates**

- **File:** `app/domain/models/subsystem.py`
- Changed from single `status` field to dual fields: `rfcc_status` and `rfwcc_status`
- Both track the same states: NOT_UPLOADED, NOT_SIGNED, SIGNED
- Backward compatible: `.from_db_row()` defaults to NOT_SIGNED for missing columns

### 2. **Data Persistence Layer**

- **File:** `app/infrastructure/excel/writers.py`
  - Updated `write_subsystems()` to persist both status columns
- **File:** `app/application/pipelines/import_rfcc_pipeline.py`
  - Fixed `create_subsystems_from_db()` to use the new model

### 3. **PIMS Web Client**

- **File:** `app/infrastructure/web/pims_client.py`
  - Added `sign_rfwcc_for_subsystem()` method (mirrors RFCC signing workflow)
  - Identical signing steps: dossier, check items, signatures
  - Only difference: looks for "RFWCC" tab instead of "RFCC"

### 4. **RFCC Pipeline Updates**

- **File:** `app/application/pipelines/rfcc_signing_pipeline.py`
  - Updated to use `rfcc_status` instead of `status`
  - No workflow changes; same signing logic

### 5. **RFWCC Pipelines (NEW)**

- **File:** `app/application/pipelines/import_rfwcc_pipeline.py` (NEW)
  - Loads Excel file with one column of subsystem IDs
  - Marks matching subsystems for RFWCC signing (`rfwcc_status = NOT_SIGNED`)
  - Ensures non-matching subsystems have `rfwcc_status = NOT_UPLOADED`

- **File:** `app/application/pipelines/rfwcc_signing_pipeline.py` (NEW)
  - Parallel to RFCC signing pipeline
  - Filters subsystems by `rfwcc_status = NOT_SIGNED`
  - Calls `sign_rfwcc_for_subsystem()` for each subsystem

### 6. **CLI & GUI Updates**

- **File:** `main.py`
  - Added imports for RFWCC pipelines
  - Added CLI commands: `import-rfwcc`, `sign-rfwcc`
  - Added GUI buttons on second row: "Import RFWCC (requires Excel)", "Sign RFWCC"
  - File picker for RFWCC Excel file import

### 7. **Documentation**

- **File:** `copilot-instructions.md`
  - Added database schema documentation
  - Added RFWCC-specific maintenance notes
  - Documented the dual-certificate architecture

## Key Design Decisions

### Why Separate Status Columns?

- Each certificate can be signed independently
- Supports phased workflows (RFCC first, then RFWCC later)
- Easy to query subsystems by certificate state

### Why Identical Signing Workflows?

- Same PIMS UI components for both certificates
- Same dossier, check items, and signature steps
- Future-proof if UI changes apply to both

### Why Excel Import for RFWCC?

- User provided: RFWCC list is a simple one-column Excel file (vs. full CSV for RFCC)
- Filter-based: only subsystems in the list get signed
- Non-invasive: doesn't modify RFCC status

## Usage

### CLI

```bash
# Import RFWCC list
python main.py import-rfwcc --rfwcc-file "path/to/rfwcc_list.xlsx"

# Sign RFWCC certificates
python main.py sign-rfwcc

# RFCC workflow unchanged
python main.py import --main-export "path/to/export.csv"
python main.py sign-rfcc
```

### GUI

```bash
# Launch GUI
python main.py --gui
```

- Two new buttons on bottom row: Import RFWCC, Sign RFWCC
- Import RFWCC button opens file picker for Excel file

## Testing Recommendations

1. **Backward compatibility:** Load existing subsystems.xlsx (with old `status` column) and verify migration to dual columns
2. **RFWCC import:** Load test Excel file, verify subsystems marked NOT_SIGNED
3. **RFWCC signing:** Verify workflow steps (dossier, check items, signatures) execute correctly
4. **Independent workflows:** Sign RFCC without affecting RFWCC status and vice versa

## Files Modified

- `main.py`
- `app/domain/models/subsystem.py`
- `app/infrastructure/excel/writers.py`
- `app/infrastructure/web/pims_client.py`
- `app/application/pipelines/import_rfcc_pipeline.py`
- `app/application/pipelines/rfcc_signing_pipeline.py`
- `copilot-instructions.md`

## Files Created

- `app/application/pipelines/import_rfwcc_pipeline.py`
- `app/application/pipelines/rfwcc_signing_pipeline.py`

## Next Steps (Optional)

1. Add unit tests for RFWCC pipeline logic
2. Add integration tests for PIMS RFWCC signing
3. Migration script for existing databases with old schema
4. Documentation for end-users on RFWCC workflow
