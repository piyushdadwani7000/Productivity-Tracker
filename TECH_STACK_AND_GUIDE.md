# 📚 Tech Stack, Libraries & Architecture Guide

A complete reference guide explaining the libraries powering **FocusTracker Pro**, how they map to specific tasks, alternative libraries for future projects, and the core foundational toolbelt for building high-performance AI desktop/web apps.

---

## 📌 1. Library Mapping in FocusTracker

| Component / Task | Library / Tool | Role in this Application | Why It Was Chosen |
| :--- | :--- | :--- | :--- |
| **OS & Window Tracking** | `pywin32` (`win32gui`, `win32process`, `win32api`) | Retrieves the foreground window handle (`hwnd`), window title, and user idle tick count (`GetLastInputInfo`). | Native Windows API bindings with zero overhead and instantaneous C-level execution speed. |
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
- **`PyWebView`**: A lightweight Python wrapper that renders your web dashboard inside a native native OS window without needing full Electron.
- **`PyInstaller`**: For compiling Python scripts and virtual environments into a standalone single `.exe` for distribution.

---

## 🎯 3. The Fundamental Toolbelt for Upcoming Projects

To build fast, robust, modern tools, mastering these 5 core pillars is essential:

```
┌─────────────────────────────────────────────────────────────┐
│                   MODERN DEVELOPER TOOLBELT                 │
├─────────────────────────────────────────────────────────────┤
│ 1. Asynchronous Architecture   -> FastAPI + WebSockets      │
│ 2. OS & Hardware Integration   -> pywin32, psutil, uiauto   │
│ 3. Applied Machine Learning    -> scikit-learn, Embeddings  │
│ 4. Embedded Data Persistence   -> SQLite / DuckDB           │
│ 5. Glassmorphic Web Interfaces -> Modern CSS + Chart.js     │
└─────────────────────────────────────────────────────────────┘
```

### Pillar 1: Asynchronous Core (`FastAPI` + `asyncio`)
- **Why it matters**: Desktop background trackers must perform I/O (network scraping, database writes, OS polling) without freezing the UI.
- **Key Pattern**: Run heavy OS polling or scraping in worker threads (`ThreadPoolExecutor`), broadcast updates through WebSocket streams (`ConnectionManager`), and keep the event loop non-blocking.

### Pillar 2: Native OS Integration (`pywin32` / `psutil`)
- **Why it matters**: Bridges web technologies with the user's local operating system.
- **Key Pattern**: Use native Windows Win32 APIs for instantaneous polling (`GetForegroundWindow`, `GetLastInputInfo`) and UIAutomation for accessibility tree inspection.

### Pillar 3: Fast Lightweight AI (`scikit-learn` Pipeline)
- **Why it matters**: You don't always need a heavy 70-billion-parameter LLM. A fast TF-IDF Naive Bayes pipeline runs in **< 1ms**, trains in **15ms**, and delivers accurate real-time classifications on CPU.

### Pillar 4: Embedded Database Layer (`sqlite3` / `DuckDB`)
- **Why it matters**: Zero-maintenance, single-file databases that can store millions of rows without requiring external database servers (PostgreSQL/MySQL).

### Pillar 5: Hardware-Accelerated Web Frontend
- **Why it matters**: Browser engines (V8 + Chromium) leverage GPU hardware acceleration for smooth 60fps animations, glassmorphism filters, and dynamic charts—vastly outperforming traditional desktop GUI toolkits (Tkinter) in both aesthetics and CPU efficiency.
