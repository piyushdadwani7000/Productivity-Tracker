# 📚 Tech Stack, Libraries & Architecture Guide

A complete reference guide explaining the libraries powering **FocusTracker Pro**, how they map to specific tasks, alternative libraries for future projects, and the core foundational toolbelt for building high-performance AI desktop/web apps.

---

## 📌 1. Library Mapping in FocusTracker

| Component / Task | Library / Tool | Role in this Application | Why It Was Chosen |
| :--- | :--- | :--- | :--- |
| **OS & Window Tracking** | `pywin32` (`win32gui`, `win32process`, `win32api`) | Retrieves foreground window handle (`hwnd`), window title, and user idle tick count (`GetLastInputInfo`). | Native Windows API bindings with zero overhead and instantaneous C-level execution speed. |
| **Process Inspection** | `psutil` | Converts process IDs (`pid`) to active executable names (`chrome.exe`, `Code.exe`, `spotify.exe`). | Cross-platform, reliable process metadata extraction with minimal memory usage. |
| **Window Geometry** | `pygetwindow` | Tracks window bounds and split-screen state. | Lightweight wrapper around native window rects. |
| **Browser Inspection** | `uiautomation` | Navigates the Windows accessibility tree to read active browser address bar URLs directly from Chrome, Edge, Brave, and Firefox. | Non-invasive: extracts URLs without requiring custom browser extensions or plugins. |
| **HTML Parsing & Cleaning** | `beautifulsoup4` (`bs4`) | Strips `<script>`, `<style>`, `<nav>`, `<header>` and extracts the first 70 words of readable text. | Robust HTML parser capable of handling malformed or incomplete HTML fragments. |
| **Machine Learning Classification** | `scikit-learn` | Powers the `WindowClassifier` using TF-IDF N-gram feature extraction (`TfidfVectorizer`) and Multinomial Naive Bayes (`MultinomialNB`). | Extremely fast training (< 15ms), lightweight footprint, and zero GPU requirement. |
| **Data Processing** | `pandas` | Formats keywords and training sets into structured dataframes for model fitting. | Standard high-performance data manipulation library in Python. |
| **Asynchronous Web Backend** | `fastapi` | Provides REST API endpoints and real-time WebSocket connection manager (`/ws`). | Asynchronous (ASGI), high concurrency, built-in validation via Pydantic, and low latency. |
| **ASGI Web Server** | `uvicorn[standard]` | High-performance ASGI web server hosting FastAPI with hardware event loops (`uvloop`/`websockets`). | Industry-standard async server capable of handling thousands of requests/sec. |
| **Data Validation** | `pydantic` | Validates JSON payloads for tasks, keywords, settings, and reclassification requests. | Type safety, auto serialization/deserialization, and fast Rust-backed core (`pydantic-core`). |
| **Persistent Storage** | `sqlite3` (Python Standard Library) | Stores activity logs, daily summaries, tasks, keywords, and feedback logs in `tracker.db`. | Zero-configuration, serverless, atomic, single-file embedded relational database. |
| **Native Distraction Alert** | `ctypes` (`MessageBoxTimeoutW`) | Fires a non-blocking, topmost Windows alert prompt that auto-dismisses after 7 seconds if the user stays distracted for 30s. | Uses unexported Windows User32 C-API directly without needing external GUI frameworks or extra dependencies. |
| **Packaging & Standalone EXE** | `PyInstaller` (`FocusTracker.spec`) | Compiles the Python runtime, dependencies, and `static/` web bundle into a single self-contained `.exe`. | Allows end-users to launch the full webapp with a double-click without installing Python or dependencies. |
| **Automated Installer** | Windows Batch + `PowerShell` (`WScript.Shell`) | Sets up environment, compiles dependencies, and generates Desktop & Start Menu `.lnk` shortcuts. | Native zero-dependency Windows installer script that runs on any modern Windows 10/11 system. |
| **Frontend Visualizations** | `Chart.js` (via CDN) | Renders responsive, hardware-accelerated Doughnut and 24-Hour Timeline Bar charts. | HTML5 Canvas-based rendering, smooth 60fps animations, and no heavy framework dependencies. |
| **Audio & Alerts Engine** | Web Audio API (Native Browser) | Synthesizes gentle audio frequency chimes for distraction warnings and milestones. | No external audio files needed; generated programmatically in the browser. |

---

## 🚀 2. Libraries & Frameworks for Similar Future Applications

If you want to build similar productivity monitors, AI agents, background trackers, or modern hybrid tools, here is the recommended ecosystem:

### A. Desktop Window & System Monitoring
- **`pynput`**: For global cross-platform mouse and keyboard event hooks (detecting keystroke volume, mouse travel distance, or custom hotkeys).
- **`pywinauto`**: A powerful alternative to `uiautomation` for deep Windows desktop automation and automated UI control.
- **`AppKit` / `Quartz` (macOS)** & **`python-xlib` (Linux)**: If expanding window title tracking across Mac and Linux platforms.

### B. Intelligent Text & Content Extraction
- **`trafilatura`**: The industry gold standard for Python web scraping and main text extraction (outperforms regular BeautifulSoup for articles and documentation).
- **`httpx`**: An async HTTP client supporting HTTP/2, connection pooling, and seamless async integration with FastAPI.
- **`selectolax`**: An ultra-fast C-based HTML parser (Modest/Lexbor engine) that is 5–10x faster than BeautifulSoup for high-throughput scraping.

### C. Advanced AI & NLP Classifiers
- **`fastembed`** / **`sentence-transformers`**: Generate local semantic vector embeddings for text (e.g. `all-MiniLM-L6-v2`) to compare semantic meaning instead of just keyword tokens.
- **`duckdb`** or **`sqlite-vec`**: Embedded vector search to query historical tasks and activities using semantic search (e.g. *"Show me everything related to debugging"*).
- **`ollama` / `litellm`**: For running local small language models (like Llama 3.2 1B or Phi-3.5) to produce detailed daily productivity summaries and actionable insights.

### D. Packaging & Hybrid Desktop Deployment
- **`Tauri` (Rust + Web)**: The modern replacement for Electron. Bundles your web frontend into a native desktop app with an ultra-lightweight memory footprint (~15MB RAM).
- **`PyWebView`**: A lightweight Python wrapper that renders your web dashboard inside a native OS window without needing full Electron.
- **`PyInstaller` / `Nuitka`**: Compiles Python scripts into standalone `.exe` binaries with optional C-level compilation.

---

## 🎯 3. The Fundamental Toolbelt for Upcoming Projects

To build fast, robust, modern tools, mastering these 6 core pillars is essential:

```
┌─────────────────────────────────────────────────────────────┐
│                   MODERN DEVELOPER TOOLBELT                 │
├─────────────────────────────────────────────────────────────┤
│ 1. Asynchronous Architecture   -> FastAPI + WebSockets      │
│ 2. OS & Hardware Integration   -> pywin32, psutil, uiauto   │
│ 3. Applied Machine Learning    -> scikit-learn, Embeddings  │
│ 4. Embedded Data Persistence   -> SQLite / DuckDB           │
│ 5. Glassmorphic Web Interfaces -> Modern CSS + Chart.js     │
│ 6. Self-Contained Distribution -> PyInstaller + PowerShell  │
└─────────────────────────────────────────────────────────────┘
```

### Pillar 1: Asynchronous Core (`FastAPI` + `asyncio`)
- **Why it matters**: Desktop background trackers must perform I/O (network scraping, database writes, OS polling) without freezing the UI.
- **Key Pattern**: Run heavy OS polling or scraping in worker threads (`ThreadPoolExecutor`), broadcast updates through WebSocket streams (`ConnectionManager`), and keep the event loop non-blocking.

### Pillar 2: Native OS Integration (`pywin32` / `psutil` / `ctypes`)
- **Why it matters**: Bridges web technologies with the user's local operating system.
- **Key Pattern**: Use native Windows Win32 APIs for instantaneous polling (`GetForegroundWindow`, `GetLastInputInfo`), UIAutomation for accessibility tree inspection, and `ctypes.windll.user32.MessageBoxTimeoutW` for non-blocking native prompts.

### Pillar 3: Fast Lightweight AI (`scikit-learn` Pipeline)
- **Why it matters**: You don't always need a heavy 70-billion-parameter LLM. A fast TF-IDF Naive Bayes pipeline runs in **< 1ms**, trains in **15ms**, and delivers accurate real-time classifications on CPU.

### Pillar 4: Embedded Database Layer (`sqlite3` / `DuckDB`)
- **Why it matters**: Zero-maintenance, single-file databases that can store millions of rows without requiring external database servers (PostgreSQL/MySQL).

### Pillar 5: Hardware-Accelerated Web Frontend
- **Why it matters**: Browser engines (V8 + Chromium) leverage GPU hardware acceleration for smooth 60fps animations, glassmorphism filters, and dynamic charts—vastly outperforming traditional desktop GUI toolkits (Tkinter) in both aesthetics and CPU efficiency.

### Pillar 6: One-Click Distribution & Packaging
- **Why it matters**: Great software must be effortless to install and launch without demanding technical knowledge from end-users.

---

## 📦 4. Distribution Architecture: PyInstaller & Installer Scripting

### A. How Frozen PyInstaller Bundling Works
When compiled with PyInstaller, Python extracts all bundled binaries and static assets to a temporary runtime folder accessible via `sys._MEIPASS`:

```python
import sys, os
from pathlib import Path

def get_bundle_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)  # Temp extracted bundle directory
    return Path(__file__).resolve().parent

STATIC_DIR = get_bundle_dir() / "static"
```

### B. Launching Uvicorn in Frozen Binaries
In standard Python scripts, `uvicorn.run("server:app")` resolves the module path dynamically. In a frozen `.exe`, module string imports fail because code is bundled in `PYZ-00.pyz`. The solution is passing the imported `app` instance directly:

```python
from server import app
uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
```

### C. Creating Desktop Shortcuts with Zero External Dependencies
Using Windows' built-in `WScript.Shell` via inline PowerShell inside a `.bat` file enables clean, automated shortcut creation without installing third-party installer software:

```batch
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
    "$ws = New-Object -ComObject WScript.Shell; " ^
    "$s = $ws.CreateShortcut('%USERPROFILE%\Desktop\FocusTracker.lnk'); " ^
    "$s.TargetPath = '%TARGET_EXE%'; " ^
    "$s.WorkingDirectory = '%APP_DIR%'; " ^
    "$s.Description = 'FocusTracker — AI Productivity Monitor'; " ^
    "$s.Save();"
```

### D. Non-Blocking Native Windows Prompts with Auto-Dismiss
To notify a user on their desktop without installing extra GUI frameworks, invoke the native Windows `MessageBoxTimeoutW` C-API in a background thread:

```python
import ctypes, threading

def show_topmost_alert(title: str, msg: str, timeout_ms: int = 7000):
    def _prompt():
        MB_ICONWARNING = 0x30
        MB_TOPMOST = 0x40000
        MB_SETFOREGROUND = 0x10000
        ctypes.windll.user32.MessageBoxTimeoutW(
            0, msg, title,
            MB_ICONWARNING | MB_TOPMOST | MB_SETFOREGROUND,
            0, timeout_ms
        )
    threading.Thread(target=_prompt, daemon=True).start()
```
