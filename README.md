# ⚡ FocusTracker Pro — Intelligent Web Productivity Monitor

FocusTracker is a real-time, low-overhead browser web application that automatically tracks active Windows applications, classifies activity as **Productive / Intended Task** or **Distraction** using Machine Learning (TF-IDF + Naive Bayes), and provides interactive charts, tasks, and distraction alerts.

---

## 🚀 Getting Started

### 1. Install Dependencies
Make sure you are in the project folder and have your Python environment activated:

```bash
pip install -r requirements.txt
```

### 2. Launch the Web Application
Simply run:

```bash
python app.py
```

This will automatically:
1. Initialize the background window & idle monitoring engine.
2. Launch the FastAPI server at `http://localhost:8000`.
3. Open the dashboard directly in your default browser.

---

## 🌟 Key Features

1. **Ultra-Low CPU Overhead**: Replaced slow Tkinter GUI re-renders with an asynchronous FastAPI backend and a hardware-accelerated, lightweight web dashboard.
2. **🤖 70-Word AI Web Rail Guard**:
   - Automatically detects active browser windows (Chrome, Edge, Brave, Firefox, Opera, etc.) using Windows UIAutomation.
   - Extracts the active URL and asynchronously scrapes the first **70 words** of readable body text.
   - Guards against **misleading window titles** (e.g., a tab named "Work Research" that actually contains gaming/video streaming content) and overrules false positives.
   - Displays a live **Web Guard AI Inspector** preview on the dashboard with matched keywords and analysis tags.
3. **Active Window Radar**: Real-time live status banner showing current foreground window, app name, emoji badge, AI classification, and ticking duration timer.
4. **Live Metrics & Focus Score**: Instant feedback on Productive Time, Distraction Time, Total Active Time, and dynamic Focus Score (%).
5. **Interactive Analytics**:
   - Productive vs Distraction Ratio Doughnut Chart.
   - 24-Hour Productivity Timeline Bar Chart (hourly minute breakdown).
6. **Human-in-the-Loop AI Training**:
   - Reclassify any logged window activity with 1-click ("Mark Distraction" / "Mark Task").
   - Instant automated retraining of the Naive Bayes ML classifier.
7. **Focus Task Checklist**: Add daily tasks, toggle completion with progress indicators, and filter views.
8. **Distraction & 5-Hour Milestone Alerts**:
   - In-app visual warning modal with 5-minute snooze.
   - Synthesized Web Audio gentle warning chimes.
   - Desktop browser notifications.
9. **Configurable Settings**: Adjust system idle threshold and distraction alert timers via the settings modal.

---

## 🛠️ CLI Options

```bash
python app.py --help
python app.py --port 8080      # Run on custom port
python app.py --no-browser     # Do not auto-open browser
```

---

## 📚 Tech Stack & Architecture Reference

For an in-depth breakdown of every library used, alternatives, and foundational tools for upcoming projects, see [TECH_STACK_AND_GUIDE.md](file:///c:/Users/piyus/Downloads/Productivity-Tracker-main/Productivity-Tracker/TECH_STACK_AND_GUIDE.md).

