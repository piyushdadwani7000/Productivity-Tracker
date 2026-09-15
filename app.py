import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.pyplot as plt
from datetime import date
import threading
import database
from tracker import TrackingEngine

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

def format_seconds(seconds):
    """Helper to format seconds into readable strings (e.g. 1h 25m or 45s)."""
    secs = int(seconds)
    if secs < 60:
        return f"{secs}s"
    mins = secs // 60
    rem_secs = secs % 60
    if mins < 60:
        return f"{mins}m {rem_secs}s"
    hours = mins // 60
    rem_mins = mins % 60
    return f"{hours}h {rem_mins}m"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Intelligent Productivity & Distraction Tracker")
        self.geometry("1080x720")
        self.minsize(950, 620)

        # Set grid layout 1x2
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Initialize Database
        database.init_db()

        # Navigation Frame
        self.navigation_frame = ctk.CTkFrame(self, corner_radius=0)
        self.navigation_frame.grid(row=0, column=0, sticky="nsew")
        self.navigation_frame.grid_rowconfigure(4, weight=1)

        self.navigation_frame_label = ctk.CTkLabel(
            self.navigation_frame, 
            text="⚡ FocusTracker",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        self.navigation_frame_label.grid(row=0, column=0, padx=20, pady=20)

        self.home_button = ctk.CTkButton(
            self.navigation_frame, corner_radius=8, height=40, border_spacing=10, 
            text="📊 Dashboard",
            fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
            command=self.home_button_event
        )
        self.home_button.grid(row=1, column=0, padx=10, pady=5, sticky="ew")

        self.tasks_button = ctk.CTkButton(
            self.navigation_frame, corner_radius=8, height=40, border_spacing=10, 
            text="✅ Daily Tasks",
            fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
            command=self.tasks_button_event
        )
        self.tasks_button.grid(row=2, column=0, padx=10, pady=5, sticky="ew")

        self.keywords_button = ctk.CTkButton(
            self.navigation_frame, corner_radius=8, height=40, border_spacing=10, 
            text="🏷️ Keywords",
            fg_color="transparent", text_color=("gray10", "gray90"), hover_color=("gray70", "gray30"),
            command=self.keywords_button_event
        )
        self.keywords_button.grid(row=3, column=0, padx=10, pady=5, sticky="ew")

        # ==========================================
        # HOME / DASHBOARD FRAME
        # ==========================================
        self.home_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.home_frame.grid_columnconfigure(0, weight=1)
        self.home_frame.grid_rowconfigure(2, weight=1)
        
        # 1. LIVE STATUS BANNER (Real-time active window & category)
        self.live_card = ctk.CTkFrame(self.home_frame, corner_radius=10)
        self.live_card.grid(row=0, column=0, padx=20, pady=(20, 10), sticky="nsew")
        self.live_card.grid_columnconfigure(1, weight=1)

        self.live_title_label = ctk.CTkLabel(
            self.live_card, text="LIVE MONITOR",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="gray60"
        )
        self.live_title_label.grid(row=0, column=0, padx=15, pady=(10, 0), sticky="w")

        self.current_window_label = ctk.CTkLabel(
            self.live_card, text="Tracking active window...",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w"
        )
        self.current_window_label.grid(row=1, column=0, columnspan=2, padx=15, pady=(2, 10), sticky="ew")

        self.badge_frame = ctk.CTkFrame(self.live_card, fg_color="transparent")
        self.badge_frame.grid(row=0, column=1, padx=15, pady=(10, 0), sticky="e")

        self.live_badge = ctk.CTkLabel(
            self.badge_frame, text="READY",
            corner_radius=6, fg_color="#3498db", text_color="white",
            font=ctk.CTkFont(size=12, weight="bold"),
            padx=10, pady=4
        )
        self.live_badge.pack(side="right")

        self.confidence_label = ctk.CTkLabel(
            self.badge_frame, text="",
            font=ctk.CTkFont(size=12), text_color="gray60"
        )
        self.confidence_label.pack(side="right", padx=10)

        # 2. METRICS STAT CARDS ROW
        self.metrics_container = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        self.metrics_container.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        for i in range(4):
            self.metrics_container.grid_columnconfigure(i, weight=1)

        # Stat Card 1: Productive Time
        self.card_prod = ctk.CTkFrame(self.metrics_container, corner_radius=8)
        self.card_prod.grid(row=0, column=0, padx=(0, 5), pady=5, sticky="nsew")
        ctk.CTkLabel(self.card_prod, text="Productive Time", font=ctk.CTkFont(size=12), text_color="gray60").pack(pady=(10, 2))
        self.val_prod = ctk.CTkLabel(self.card_prod, text="0s", font=ctk.CTkFont(size=20, weight="bold"), text_color="#2ecc71")
        self.val_prod.pack(pady=(0, 10))

        # Stat Card 2: Distraction Time
        self.card_dist = ctk.CTkFrame(self.metrics_container, corner_radius=8)
        self.card_dist.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(self.card_dist, text="Distraction Time", font=ctk.CTkFont(size=12), text_color="gray60").pack(pady=(10, 2))
        self.val_dist = ctk.CTkLabel(self.card_dist, text="0s", font=ctk.CTkFont(size=20, weight="bold"), text_color="#e74c3c")
        self.val_dist.pack(pady=(0, 10))

        # Stat Card 3: Total Active Time
        self.card_total = ctk.CTkFrame(self.metrics_container, corner_radius=8)
        self.card_total.grid(row=0, column=2, padx=5, pady=5, sticky="nsew")
        ctk.CTkLabel(self.card_total, text="Total Active", font=ctk.CTkFont(size=12), text_color="gray60").pack(pady=(10, 2))
        self.val_total = ctk.CTkLabel(self.card_total, text="0s", font=ctk.CTkFont(size=20, weight="bold"))
        self.val_total.pack(pady=(0, 10))

        # Stat Card 4: Focus Score
        self.card_score = ctk.CTkFrame(self.metrics_container, corner_radius=8)
        self.card_score.grid(row=0, column=3, padx=(5, 0), pady=5, sticky="nsew")
        ctk.CTkLabel(self.card_score, text="Focus Score", font=ctk.CTkFont(size=12), text_color="gray60").pack(pady=(10, 2))
        self.val_score = ctk.CTkLabel(self.card_score, text="100%", font=ctk.CTkFont(size=20, weight="bold"), text_color="#3498db")
        self.val_score.pack(pady=(0, 10))

        # 3. SPLIT CONTENT: CHART + RECENT ACTIVITY FEED
        self.content_split = ctk.CTkFrame(self.home_frame, fg_color="transparent")
        self.content_split.grid(row=2, column=0, padx=20, pady=(5, 20), sticky="nsew")
        self.content_split.grid_columnconfigure(0, weight=1)
        self.content_split.grid_columnconfigure(1, weight=1)
        self.content_split.grid_rowconfigure(0, weight=1)

        # Left: Matplotlib Chart Frame
        self.chart_frame = ctk.CTkFrame(self.content_split, corner_radius=10)
        self.chart_frame.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        # Right: Recent Activity Log Feed
        self.feed_frame = ctk.CTkScrollableFrame(self.content_split, corner_radius=10, label_text="Recent Categorized Activity")
        self.feed_frame.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
        self.feed_frame.grid_columnconfigure(0, weight=1)

        # ==========================================
        # TASKS FRAME
        # ==========================================
        self.tasks_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.tasks_frame.grid_columnconfigure(0, weight=1)
        
        self.tasks_label = ctk.CTkLabel(self.tasks_frame, text="Daily Tasks", font=ctk.CTkFont(size=24, weight="bold"))
        self.tasks_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        self.new_task_entry = ctk.CTkEntry(self.tasks_frame, placeholder_text="Enter new task...")
        self.new_task_entry.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.add_task_btn = ctk.CTkButton(self.tasks_frame, text="Add Task", command=self.add_task)
        self.add_task_btn.grid(row=2, column=0, padx=20, pady=10, sticky="e")
        
        self.task_list_frame = ctk.CTkScrollableFrame(self.tasks_frame, label_text="Your Tasks")
        self.task_list_frame.grid(row=3, column=0, padx=20, pady=20, sticky="nsew", rowspan=4)
        self.tasks_frame.grid_rowconfigure(3, weight=1)

        # ==========================================
        # KEYWORDS FRAME
        # ==========================================
        self.keywords_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.keywords_frame.grid_columnconfigure(0, weight=1)
        
        self.kw_label = ctk.CTkLabel(self.keywords_frame, text="Classification Keywords", font=ctk.CTkFont(size=24, weight="bold"))
        self.kw_label.grid(row=0, column=0, padx=20, pady=20, sticky="w")
        
        self.new_kw_entry = ctk.CTkEntry(self.keywords_frame, placeholder_text="Keyword phrase (e.g. stackoverflow, blender, twitch)...")
        self.new_kw_entry.grid(row=1, column=0, padx=20, pady=10, sticky="ew")
        
        self.kw_options_frame = ctk.CTkFrame(self.keywords_frame, fg_color="transparent")
        self.kw_options_frame.grid(row=2, column=0, padx=20, pady=5, sticky="ew")
        self.kw_options_frame.grid_columnconfigure(1, weight=1)

        self.kw_cat_var = ctk.StringVar(value="Intended Task")
        self.kw_cat_menu = ctk.CTkOptionMenu(
            self.kw_options_frame, values=["Intended Task", "Distraction"], variable=self.kw_cat_var
        )
        self.kw_cat_menu.grid(row=0, column=0, sticky="w")
        
        self.add_kw_btn = ctk.CTkButton(self.kw_options_frame, text="Add Keyword", command=self.add_keyword)
        self.add_kw_btn.grid(row=0, column=1, sticky="e")
        
        self.kw_list_frame = ctk.CTkScrollableFrame(self.keywords_frame, label_text="Current Keywords (ML Model Training Data)")
        self.kw_list_frame.grid(row=3, column=0, padx=20, pady=20, sticky="nsew", rowspan=4)
        self.keywords_frame.grid_rowconfigure(3, weight=1)

        # ==========================================
        # INITIALIZE TRACKING ENGINE
        # ==========================================
        self.tracker = TrackingEngine(
            callback_update_dashboard=self.safe_update_dashboard,
            callback_distraction_alert=self.show_distraction_alert,
            callback_5hr_summary=self.show_5hr_summary,
            callback_status_update=self.safe_update_status
        )
        self.tracker.start()

        # Select Default Frame
        self.select_frame_by_name("home")
        
        # Initial Load
        self.load_tasks()
        self.load_keywords()
        self.update_dashboard()

    def select_frame_by_name(self, name):
        self.home_button.configure(fg_color=("gray75", "gray25") if name == "home" else "transparent")
        self.tasks_button.configure(fg_color=("gray75", "gray25") if name == "tasks" else "transparent")
        self.keywords_button.configure(fg_color=("gray75", "gray25") if name == "keywords" else "transparent")

        if name == "home":
            self.home_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.home_frame.grid_forget()
        if name == "tasks":
            self.tasks_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.tasks_frame.grid_forget()
        if name == "keywords":
            self.keywords_frame.grid(row=0, column=1, sticky="nsew")
        else:
            self.keywords_frame.grid_forget()

    def home_button_event(self):
        self.select_frame_by_name("home")
        self.update_dashboard()

    def tasks_button_event(self):
        self.select_frame_by_name("tasks")

    def keywords_button_event(self):
        self.select_frame_by_name("keywords")

    def safe_update_status(self, title, app, category, confidence):
        self.after(0, lambda: self.update_live_status(title, app, category, confidence))

    def update_live_status(self, title, app, category, confidence):
        display_title = title if len(title) <= 70 else title[:67] + "..."
        self.current_window_label.configure(text=f"[{app}] {display_title}")
        
        if category == "Intended Task":
            self.live_badge.configure(text="🎯 INTENDED TASK", fg_color="#2ecc71")
        elif category == "Distraction":
            self.live_badge.configure(text="⚠️ DISTRACTION", fg_color="#e74c3c")
        else:
            self.live_badge.configure(text="💤 IDLE", fg_color="#7f8c8d")
            
        if confidence > 0:
            self.confidence_label.configure(text=f"Confidence: {confidence * 100:.1f}%")
        else:
            self.confidence_label.configure(text="")

    def safe_update_dashboard(self):
        # Called from background thread, schedule on main thread
        self.after(0, self.update_dashboard)

    def update_dashboard(self):
        # Fetch stats from DB
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT total_active_time, total_distraction_time FROM daily_summary WHERE date = ?', (date.today().isoformat(),))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            active_time = row[0]
            distraction_time = row[1]
            productive_time = max(0.0, active_time - distraction_time)
        else:
            active_time = 0
            distraction_time = 0
            productive_time = 0
            
        score = (productive_time / active_time * 100) if active_time > 0 else 100.0

        # Update Stat Cards
        self.val_prod.configure(text=format_seconds(productive_time))
        self.val_dist.configure(text=format_seconds(distraction_time))
        self.val_total.configure(text=format_seconds(active_time))
        self.val_score.configure(text=f"{score:.1f}%")
        if score >= 75:
            self.val_score.configure(text_color="#2ecc71")
        elif score >= 50:
            self.val_score.configure(text_color="#f39c12")
        else:
            self.val_score.configure(text_color="#e74c3c")

        # Draw Pie Chart
        for widget in self.chart_frame.winfo_children():
            widget.destroy()
            
        fig, ax = plt.subplots(figsize=(4, 3.2), facecolor='#2b2b2b')
        labels = ['Productive', 'Distraction']
        sizes = [productive_time, distraction_time]
        if sum(sizes) == 0:
            sizes = [1, 0] # Default to 100% productive to show empty chart
            
        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, autopct='%1.1f%%', 
            colors=['#2ecc71', '#e74c3c'], 
            textprops={'color': "w", 'fontsize': 10},
            startangle=90
        )
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_weight('bold')
            
        ax.axis('equal')
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)

        # Update Recent Activity Feed
        self.update_activity_feed()

    def update_activity_feed(self):
        for widget in self.feed_frame.winfo_children():
            widget.destroy()

        activities = database.get_recent_activities(limit=15)
        if not activities:
            lbl = ctk.CTkLabel(self.feed_frame, text="No activity logged yet today.", text_color="gray60")
            lbl.pack(pady=20)
            return

        for act in activities:
            _, title, app, category, duration, start_time = act
            
            # Format time from ISO
            time_part = start_time.split("T")[1][:8] if "T" in start_time else start_time
            
            item_frame = ctk.CTkFrame(self.feed_frame, fg_color=("gray85", "gray20"), corner_radius=6)
            item_frame.pack(fill="x", padx=5, pady=3)
            item_frame.grid_columnconfigure(1, weight=1)

            # Category pill tag
            tag_color = "#2ecc71" if category == "Intended Task" else "#e74c3c"
            tag_text = "TASK" if category == "Intended Task" else "DISTRACT"
            tag_lbl = ctk.CTkLabel(
                item_frame, text=tag_text, text_color="white", fg_color=tag_color,
                corner_radius=4, font=ctk.CTkFont(size=10, weight="bold"),
                padx=6, pady=2
            )
            tag_lbl.grid(row=0, column=0, padx=(8, 6), pady=6)

            # Window Title & App
            display_title = title if len(title) <= 38 else title[:35] + "..."
            title_lbl = ctk.CTkLabel(
                item_frame, text=f"{display_title} ({app})", 
                font=ctk.CTkFont(size=12), anchor="w"
            )
            title_lbl.grid(row=0, column=1, sticky="w", padx=2, pady=6)

            # Duration & Timestamp
            meta_lbl = ctk.CTkLabel(
                item_frame, text=f"{format_seconds(duration)}  •  {time_part}",
                font=ctk.CTkFont(size=11), text_color="gray60"
            )
            meta_lbl.grid(row=0, column=2, sticky="e", padx=8, pady=6)

    def load_tasks(self):
        for widget in self.task_list_frame.winfo_children():
            widget.destroy()
            
        tasks = database.get_tasks(date.today().isoformat())
        if not tasks:
            ctk.CTkLabel(self.task_list_frame, text="No tasks planned for today. Add one above!", text_color="gray60").pack(pady=20)
            return

        for i, task in enumerate(tasks):
            t_id, t_name, t_status, _ = task
            chk = ctk.CTkCheckBox(self.task_list_frame, text=t_name, command=lambda id=t_id, st=t_status: self.toggle_task(id, st))
            if t_status == 'complete':
                chk.select()
            chk.grid(row=i, column=0, padx=10, pady=5, sticky="w")

    def add_task(self):
        task_text = self.new_task_entry.get()
        if task_text.strip():
            database.add_task(task_text.strip(), date.today().isoformat())
            self.new_task_entry.delete(0, "end")
            self.load_tasks()

    def toggle_task(self, task_id, current_status):
        new_status = 'pending' if current_status == 'complete' else 'complete'
        database.update_task_status(task_id, new_status)
        self.load_tasks()

    def load_keywords(self):
        for widget in self.kw_list_frame.winfo_children():
            widget.destroy()
            
        kws = database.get_keywords()
        for i, kw in enumerate(kws):
            phrase, category = kw
            color = "#2ecc71" if category == "Intended Task" else "#e74c3c"
            lbl = ctk.CTkLabel(self.kw_list_frame, text=f"• {phrase}  [{category}]", text_color=color, font=ctk.CTkFont(size=13))
            lbl.grid(row=i, column=0, padx=10, pady=3, sticky="w")

    def add_keyword(self):
        kw_text = self.new_kw_entry.get()
        category = self.kw_cat_var.get()
        if kw_text.strip():
            database.add_keyword(kw_text.strip(), category, by_user=True)
            self.tracker.force_retrain() # Retrain ML model
            self.new_kw_entry.delete(0, "end")
            self.load_keywords()

    def show_distraction_alert(self, window_title):
        self.after(0, lambda: self._popup("Distraction Alert!", f"You've been on '{window_title}' for over 2 minutes. Time to focus!"))

    def show_5hr_summary(self):
        self.after(0, lambda: self._popup("5-Hour Milestone", "You have been active for 5 hours. Take a look at your dashboard for your productivity score!"))

    def _popup(self, title, message):
        popup = ctk.CTkToplevel(self)
        popup.title(title)
        popup.geometry("400x200")
        popup.attributes("-topmost", True)
        
        lbl = ctk.CTkLabel(popup, text=message, wraplength=350, font=ctk.CTkFont(size=16))
        lbl.pack(pady=40, padx=20)
        
        btn = ctk.CTkButton(popup, text="OK", command=popup.destroy)
        btn.pack()

    def on_closing(self):
        self.tracker.stop()
        self.destroy()

if __name__ == "__main__":
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
