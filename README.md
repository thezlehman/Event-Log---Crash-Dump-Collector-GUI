# Event Log & Crash Dump Collector GUI

Collects Windows event logs (via `wevtutil`) and optional crash dump files into an output folder, with an option to create a ZIP bundle.

## Features

- **Event logs** – Export one or more Windows event logs (e.g. Application, System, Security, Setup) to `.evtx` files. Log names are comma-separated.
- **Crash dumps** – Optionally copy `.dmp` files from a folder (default: `%LOCALAPPDATA%\CrashDumps`) into the output folder under `CrashDumps`.
- **Output** – All files are written to a chosen output folder.
- **ZIP bundle** – Option to create a ZIP archive of the output folder (e.g. `OutputFolder_EventLogsAndDumps.zip`).

## Requirements

- Windows 10/11 (uses `wevtutil.exe`)
- Python 3.6+ (tkinter, subprocess, zipfile, shutil – standard library only)

**Note:** Exporting some logs (e.g. Security) may require running the app as Administrator.

## Running

From this folder:

```bash
python eventlog_collector_gui.py
```

Or on Windows, double-click `run_eventlog_collector.bat`.

## Notes

- This is a demo/portfolio app. Use for diagnostics and support bundles.
- Large logs can take a while to export; the UI may appear to hang until each export finishes.
