#!/usr/bin/env python3
"""
Event Log & Crash Dump Collector GUI

Collects Windows event logs (via wevtutil) and optional crash dump files
into an output folder and optionally creates a ZIP bundle.

This is intended as a portfolio/demo app. Exporting some logs (e.g. Security)
may require Administrator rights.
"""

import os
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import ttk, filedialog, messagebox, scrolledtext
import zipfile
import shutil
import threading


# Default Windows log names
DEFAULT_LOGS = ["Application", "System", "Security", "Setup"]


class EventLogCollectorGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Event Log & Crash Dump Collector")
        self.root.geometry("820x620")
        self.root.minsize(720, 520)

        self.log_names_var = tk.StringVar(value=", ".join(DEFAULT_LOGS))
        self.crash_dump_dir_var = tk.StringVar(
            value=os.path.join(os.environ.get("LOCALAPPDATA", ""), "CrashDumps")
        )
        self.include_crash_dumps_var = tk.BooleanVar(value=True)
        self.output_dir_var = tk.StringVar()
        self.create_zip_var = tk.BooleanVar(value=True)
        self.status_var = tk.StringVar(value="Ready")
        self.abort_flag = False

        self.create_widgets()

    def create_widgets(self) -> None:
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=tk.NSEW)
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)

        ttk.Label(
            main_frame,
            text="Event Log & Crash Dump Collector",
            font=("Arial", 14, "bold"),
        ).grid(row=0, column=0, sticky=tk.W, pady=(0, 8))

        # Event logs
        log_frame = ttk.LabelFrame(main_frame, text="Event logs to export", padding="8")
        log_frame.grid(row=1, column=0, sticky=tk.EW, pady=4)
        log_frame.columnconfigure(0, weight=1)
        ttk.Label(
            log_frame,
            text="Log names (comma-separated, e.g. Application, System, Security):",
        ).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(log_frame, textvariable=self.log_names_var).grid(
            row=1, column=0, sticky=tk.EW, pady=2
        )

        # Crash dumps
        crash_frame = ttk.LabelFrame(main_frame, text="Crash dumps", padding="8")
        crash_frame.grid(row=2, column=0, sticky=tk.EW, pady=4)
        crash_frame.columnconfigure(1, weight=1)
        ttk.Checkbutton(
            crash_frame,
            text="Include crash dumps from folder:",
            variable=self.include_crash_dumps_var,
        ).grid(row=0, column=0, sticky=tk.W, pady=2)
        ttk.Entry(crash_frame, textvariable=self.crash_dump_dir_var).grid(
            row=0, column=1, sticky=tk.EW, pady=2, padx=(8, 4)
        )
        ttk.Button(
            crash_frame,
            text="Browse...",
            command=self.browse_crash_dump_dir,
            width=10,
        ).grid(row=0, column=2, sticky=tk.W, pady=2)

        # Output
        out_frame = ttk.LabelFrame(main_frame, text="Output", padding="8")
        out_frame.grid(row=3, column=0, sticky=tk.EW, pady=4)
        out_frame.columnconfigure(1, weight=1)
        ttk.Label(out_frame, text="Output folder:", width=14).grid(
            row=0, column=0, sticky=tk.W, pady=3
        )
        ttk.Entry(out_frame, textvariable=self.output_dir_var).grid(
            row=0, column=1, sticky=tk.EW, pady=3, padx=(0, 4)
        )
        ttk.Button(
            out_frame,
            text="Browse...",
            command=self.browse_output_dir,
            width=10,
        ).grid(row=0, column=2, sticky=tk.W, pady=3)
        ttk.Checkbutton(
            out_frame,
            text="Create ZIP bundle after collection",
            variable=self.create_zip_var,
        ).grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=2)

        # Log
        log_out_frame = ttk.LabelFrame(main_frame, text="Log", padding="8")
        log_out_frame.grid(row=4, column=0, sticky=tk.NSEW, pady=4)
        log_out_frame.columnconfigure(0, weight=1)
        log_out_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(4, weight=1)
        self.log_text = scrolledtext.ScrolledText(
            log_out_frame, height=14, wrap=tk.WORD, font=("Consolas", 9)
        )
        self.log_text.grid(row=0, column=0, sticky=tk.NSEW)

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=5, column=0, sticky=tk.EW, pady=8)
        ttk.Button(
            btn_frame,
            text="Collect",
            command=self.start_collect,
            width=14,
        ).pack(side=tk.LEFT, padx=4)
        ttk.Label(btn_frame, textvariable=self.status_var, relief=tk.SUNKEN).pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=8
        )

    def log(self, msg: str) -> None:
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.root.update_idletasks()

    def browse_crash_dump_dir(self) -> None:
        folder = filedialog.askdirectory(title="Select crash dump folder")
        if folder:
            self.crash_dump_dir_var.set(folder)

    def browse_output_dir(self) -> None:
        folder = filedialog.askdirectory(title="Select output folder")
        if folder:
            self.output_dir_var.set(folder)

    def _parse_log_names(self) -> list[str]:
        raw = self.log_names_var.get().strip()
        if not raw:
            return []
        return [n.strip() for n in raw.split(",") if n.strip()]

    def _validate(self) -> bool:
        if not self._parse_log_names():
            messagebox.showerror("Validation", "Enter at least one event log name.")
            return False
        out = self.output_dir_var.get().strip()
        if not out:
            messagebox.showerror("Validation", "Select output folder.")
            return False
        return True

    def _collect_worker(self) -> None:
        if not self._validate():
            return
        out_dir = self.output_dir_var.get().strip()
        log_names = self._parse_log_names()
        include_crash = self.include_crash_dumps_var.get()
        crash_dir = self.crash_dump_dir_var.get().strip()
        create_zip = self.create_zip_var.get()

        self.root.after(0, lambda: self.status_var.set("Collecting..."))
        self.root.after(0, lambda: self.log("Creating output directory..."))
        os.makedirs(out_dir, exist_ok=True)

        # Export event logs via wevtutil (Windows)
        for log_name in log_names:
            if self.abort_flag:
                break
            safe_name = "".join(c if c.isalnum() or c in "._-" else "_" for c in log_name)
            evtx_path = os.path.join(out_dir, f"{safe_name}.evtx")
            self.root.after(0, lambda n=log_name, p=evtx_path: self.log(f"Exporting {n} -> {p}"))
            try:
                subprocess.run(
                    ["wevtutil", "epl", log_name, evtx_path, "/ow:true"],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                )
                self.root.after(0, lambda p=evtx_path: self.log(f"  -> {p}"))
            except FileNotFoundError:
                self.root.after(
                    0,
                    lambda n=log_name: self.log(f"  Skipped (wevtutil not found or not Windows): {n}"),
                )
            except subprocess.TimeoutExpired:
                self.root.after(0, lambda n=log_name: self.log(f"  Timeout: {n}"))
            except Exception as e:
                self.root.after(0, lambda e=e: self.log(f"  Error: {e}"))

        # Copy crash dumps
        if include_crash and crash_dir and os.path.isdir(crash_dir):
            self.root.after(0, lambda: self.log("Copying crash dumps..."))
            crash_out = os.path.join(out_dir, "CrashDumps")
            os.makedirs(crash_out, exist_ok=True)
            count = 0
            for f in Path(crash_dir).glob("*.dmp"):
                if self.abort_flag:
                    break
                try:
                    dest = os.path.join(crash_out, f.name)
                    shutil.copy2(f, dest)
                    count += 1
                except Exception as e:
                    self.root.after(0, lambda f=f, e=e: self.log(f"  Skip {f.name}: {e}"))
            self.root.after(0, lambda c=count: self.log(f"  Copied {c} crash dump(s)."))
        else:
            if include_crash and (not crash_dir or not os.path.isdir(crash_dir)):
                self.root.after(0, lambda: self.log("Crash dump folder missing or invalid; skipped."))

        # ZIP
        if create_zip and not self.abort_flag:
            zip_path = out_dir.rstrip(os.sep) + "_EventLogsAndDumps.zip"
            self.root.after(0, lambda: self.log(f"Creating ZIP: {zip_path}"))
            try:
                with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
                    for root_dir, _, files in os.walk(out_dir):
                        for f in files:
                            path = os.path.join(root_dir, f)
                            arcname = os.path.relpath(path, os.path.dirname(out_dir))
                            zf.write(path, arcname)
                self.root.after(0, lambda p=zip_path: self.log(f"  -> {p}"))
            except Exception as e:
                self.root.after(0, lambda e=e: self.log(f"  ZIP error: {e}"))

        self.root.after(0, lambda: self.status_var.set("Done."))

    def start_collect(self) -> None:
        self.abort_flag = False
        self.log_text.delete("1.0", tk.END)
        threading.Thread(target=self._collect_worker, daemon=True).start()


def main() -> None:
    root = tk.Tk()
    EventLogCollectorGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
