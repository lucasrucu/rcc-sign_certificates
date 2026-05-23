import argparse
import asyncio
import sys
import threading
import queue
from pathlib import Path
from typing import Optional

from app.application.orchestrations.full_sign_rfcc_flow import run_full_pims_flow
from app.application.pipelines.import_rfcc_pipeline import run_import_rfcc_pipeline
from app.application.pipelines.download_documents_pipeline import run_download_pipeline
from app.application.pipelines.rfcc_signing_pipeline import run_rfcc_signing_pipeline
from app.application.pipelines.upload_document_metadata_pipeline import run_upload_document_metadata_pipeline
from app.application.pipelines.upload_files_pipeline import run_upload_files_pipeline
from app.application.pipelines.upload_subsystem_document_pipeline import run_upload_subsystem_document_pipeline
from app.application.pipelines.import_rfwcc_pipeline import run_import_rfwcc_pipeline
from app.application.pipelines.rfwcc_signing_pipeline import run_rfwcc_signing_pipeline
from app.application.pipelines.sign_rfwcc_phase1_pipeline import run_sign_rfwcc_phase1_pipeline
from app.application.pipelines.rfwcc_complete_final_signature_pipeline import (
    run_rfwcc_complete_final_signature_pipeline,
)


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RFCC Automation v2")
    parser.add_argument("--gui", action="store_true", help="Launch GUI launcher")

    subparsers = parser.add_subparsers(dest="command")

    # --------------------------------------------------
    # FULL ORCHESTRATION command
    # --------------------------------------------------
    full_flow_parser = subparsers.add_parser(
        "full", help="Run the complete RFCC automation flow"
    )

    full_flow_parser.add_argument(
        "--main-export",
        type=Path,
        required=True,
        help="Path to main external export (CSV)",
    )

    # --------------------------------------------------
    # IMPORT command
    # --------------------------------------------------
    import_parser = subparsers.add_parser(
        "import", help="Import external Excel into DB"
    )

    import_parser.add_argument(
        "--main-export",
        type=Path,
        required=True,
        help="Path to main external export (CSV)",
    )

    # --------------------------------------------------
    # DOWNLOAD command
    # --------------------------------------------------
    download_parser = subparsers.add_parser(
        "download", help="Download documents from Aconex"
    )
    
    # --------------------------------------------------
    # UPLOAD-METADATA command
    # --------------------------------------------------
    upload_metadata_parser = subparsers.add_parser(
        "upload-doc-m", help="Upload document metadata to PIMS"
    )
    
    # --------------------------------------------------
    # UPLOAD-FILES command
    # --------------------------------------------------
    upload_files_parser = subparsers.add_parser(
        "upload-doc-f", help="Upload document files to PIMS"
    )
    
    # --------------------------------------------------
    # RFCC-SIGNING command
    # --------------------------------------------------
    rfcc_signing_parser = subparsers.add_parser(
        "sign-rfcc", help="Sign RFCC documents in PIMS"
    )
    
    # --------------------------------------------------
    # UPLOAD-SUBSYSTEM-DOCUMENT command
    # --------------------------------------------------
    upload_subsystem_document_parser = subparsers.add_parser(
        "upload-ss-doc-m", help="Upload subsystem-document links to PIMS"
    )

    # --------------------------------------------------
    # IMPORT-RFWCC command
    # --------------------------------------------------
    import_rfwcc_parser = subparsers.add_parser(
        "import-rfwcc", help="Import RFWCC document list"
    )

    import_rfwcc_parser.add_argument(
        "--rfwcc-file",
        type=Path,
        required=True,
        help="Path to RFWCC Excel file (one column with subsystem IDs)",
    )

    # --------------------------------------------------
    # SIGN-RFWCC-PHASE1 command (import + sign combined)
    # --------------------------------------------------
    sign_rfwcc_phase1_parser = subparsers.add_parser(
        "sign-rfwcc-phase1", help="Import RFWCC list and sign Phase 1"
    )

    sign_rfwcc_phase1_parser.add_argument(
        "--excel-file",
        type=Path,
        required=True,
        help="Path to Excel file (one column with subsystem IDs)",
    )

    # --------------------------------------------------
    # SIGN-RFWCC command
    # --------------------------------------------------
    rfwcc_signing_parser = subparsers.add_parser(
        "sign-rfwcc", help="Sign RFWCC documents in PIMS"
    )

    # --------------------------------------------------
    # SIGN-RFWCC-FINAL command
    # --------------------------------------------------
    rfwcc_final_parser = subparsers.add_parser(
        "sign-rfwcc-final", help="Complete final RFWCC signature step in PIMS"
    )

    rfwcc_final_parser.add_argument(
        "--excel-file",
        type=Path,
        required=True,
        help="Path to Excel file (one column with subsystem IDs) - gateway selection for final signature",
    )

    return parser


def _dispatch_cli(args: argparse.Namespace) -> None:
    # Dispatch
    if args.command == "full":
        asyncio.run(run_full_pims_flow(main_export=args.main_export))

    elif args.command == "import":
        asyncio.run(run_import_rfcc_pipeline(main_export=args.main_export))

    elif args.command == "download":
        asyncio.run(run_download_pipeline())

    elif args.command == "upload-doc-m":
        asyncio.run(run_upload_document_metadata_pipeline())

    elif args.command == "upload-doc-f":
        asyncio.run(run_upload_files_pipeline())

    elif args.command == "sign-rfcc":
        asyncio.run(run_rfcc_signing_pipeline())

    elif args.command == "upload-ss-doc-m":
        asyncio.run(run_upload_subsystem_document_pipeline())

    elif args.command == "import-rfwcc":
        asyncio.run(run_import_rfwcc_pipeline(rfwcc_file=args.rfwcc_file))

    elif args.command == "sign-rfwcc-phase1":
        asyncio.run(run_sign_rfwcc_phase1_pipeline(excel_file=args.excel_file))

    elif args.command == "sign-rfwcc":
        asyncio.run(run_rfwcc_signing_pipeline())

    elif args.command == "sign-rfwcc-final":
        asyncio.run(run_rfwcc_complete_final_signature_pipeline(excel_file=args.excel_file))


def launch_gui() -> None:
    """Simple Tkinter launcher that exposes the existing flows as buttons.

    Behavior:
    - Presents buttons for each main command.
    - For commands requiring a file, prompts the user.
    - Runs the selected flow in a background thread and streams text to the UI.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog, scrolledtext, messagebox
    except Exception as exc:
        print("Tkinter is required for GUI mode but is not available:", exc)
        return

    q: "queue.Queue[str]" = queue.Queue()

    root = tk.Tk()
    root.title("RFCC Automation Launcher")
    root.geometry("1400x750")

    # Create a main frame for buttons with scrolling capability
    button_frame = tk.Frame(root)
    button_frame.pack(fill=tk.X, padx=10, pady=10)

    # Row 1: Import & Full Flow
    row1 = tk.Frame(button_frame)
    row1.pack(fill=tk.X, pady=5)
    
    tk.Label(row1, text="📥 IMPORT & SETUP:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

    # Row 2: Download & Upload
    row2 = tk.Frame(button_frame)
    row2.pack(fill=tk.X, pady=5)
    
    tk.Label(row2, text="⬆️  PROCESS & UPLOAD:", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

    # Row 3: RFCC Signing
    row3 = tk.Frame(button_frame)
    row3.pack(fill=tk.X, pady=5)
    
    tk.Label(row3, text="🔐 RFCC (Phase 1):", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

    # Row 4: RFWCC Phases
    row4 = tk.Frame(button_frame)
    row4.pack(fill=tk.X, pady=5)
    
    tk.Label(row4, text="🔐 RFWCC (Phase 1 & Final):", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)

    text = scrolledtext.ScrolledText(root, state=tk.DISABLED, wrap=tk.WORD)
    text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0,10))

    def append(msg: str) -> None:
        text.configure(state=tk.NORMAL)
        text.insert(tk.END, msg + "\n")
        text.see(tk.END)
        text.configure(state=tk.DISABLED)

    def writer_for_queue() -> None:
        while True:
            try:
                line = q.get(block=True)
            except Exception:
                break
            if line is None:
                break
            root.after(0, append, line)

    threading.Thread(target=writer_for_queue, daemon=True).start()

    def run_target(coro_func, *coro_args):
        """Run coroutine in a thread and stream prints to queue."""
        def _runner():
            old_out, old_err = sys.stdout, sys.stderr
            try:
                class QWriter:
                    def write(self, s):
                        if s and not s.isspace():
                            for line in s.rstrip().splitlines():
                                q.put(line)
                    def flush(self):
                        pass

                sys.stdout = QWriter()
                sys.stderr = QWriter()

                asyncio.run(coro_func(*coro_args))
                q.put("[DONE]")
            except Exception as e:
                q.put(f"[ERROR] {e}")
            finally:
                sys.stdout, sys.stderr = old_out, old_err

        threading.Thread(target=_runner, daemon=True).start()

    def pick_file_and_run(coro_func):
        path = filedialog.askopenfilename(title="Select file")
        if not path:
            return
        append(f"Selected: {path}")
        run_target(coro_func, Path(path))

    def pick_none_and_run(coro_func):
        if not messagebox.askokcancel("Run", "Run selected flow?"):
            return
        run_target(coro_func)

    # ═════════════════════════════════════════════════════════════════
    # ROW 1: Import & Full Flow
    # ═════════════════════════════════════════════════════════════════
    btn_full = tk.Button(row1, text="Full Flow (CSV)", width=20,
                         command=lambda: pick_file_and_run(run_full_pims_flow))
    btn_full.pack(side=tk.LEFT, padx=5)

    btn_import = tk.Button(row1, text="Import (CSV)", width=16,
                          command=lambda: pick_file_and_run(run_import_rfcc_pipeline))
    btn_import.pack(side=tk.LEFT, padx=5)

    # ═════════════════════════════════════════════════════════════════
    # ROW 2: Download & Upload Operations
    # ═════════════════════════════════════════════════════════════════
    btn_download = tk.Button(row2, text="Download", width=16,
                             command=lambda: pick_none_and_run(run_download_pipeline))
    btn_download.pack(side=tk.LEFT, padx=5)

    btn_upload_meta = tk.Button(row2, text="Upload Metadata", width=16,
                                command=lambda: pick_none_and_run(run_upload_document_metadata_pipeline))
    btn_upload_meta.pack(side=tk.LEFT, padx=5)

    btn_upload_files = tk.Button(row2, text="Upload Files", width=16,
                                 command=lambda: pick_none_and_run(run_upload_files_pipeline))
    btn_upload_files.pack(side=tk.LEFT, padx=5)

    btn_upload_ss = tk.Button(row2, text="Upload Subsystem-Doc", width=20,
                              command=lambda: pick_none_and_run(run_upload_subsystem_document_pipeline))
    btn_upload_ss.pack(side=tk.LEFT, padx=5)

    # ═════════════════════════════════════════════════════════════════
    # ROW 3: RFCC Phase 1 Signing
    # ═════════════════════════════════════════════════════════════════
    btn_sign = tk.Button(row3, text="Sign RFCC", width=16,
                         command=lambda: pick_none_and_run(run_rfcc_signing_pipeline))
    btn_sign.pack(side=tk.LEFT, padx=5)

    # ═════════════════════════════════════════════════════════════════
    # ROW 4: RFWCC Phase 1 & Final Signing
    # ═════════════════════════════════════════════════════════════════
    btn_sign_rfwcc_phase1 = tk.Button(row4, text="Sign RFWCC Phase 1 (Excel)", width=24,
                                command=lambda: pick_file_and_run(run_sign_rfwcc_phase1_pipeline))
    btn_sign_rfwcc_phase1.pack(side=tk.LEFT, padx=5)

    btn_sign_rfwcc_final = tk.Button(row4, text="Finish RFWCC (Excel)", width=20,
                                     command=lambda: pick_file_and_run(run_rfwcc_complete_final_signature_pipeline))
    btn_sign_rfwcc_final.pack(side=tk.LEFT, padx=5)

    root.mainloop()


def main():
    parser = _build_arg_parser()
    args = parser.parse_args()

    if getattr(args, "gui", False):
        launch_gui()
        return

    if getattr(args, "command", None) is None:
        parser.print_help()
        return

    _dispatch_cli(args)


if __name__ == "__main__":
    main()