"""
==============================================================================
AINTELLIGENCE ENTERPRISE SUITE v34.3 — CORE CONTROLLER (main.py)
==============================================================================
Architecture MVC & Concurrency (Threading):
    Primary executable. Builds the UI and orchestrates the Web-Scraping
    Daemon threads. Fully Localized to EN (UI) but adapted to ES (Scraping).

Hotfix v34.3:
    - Bilingual Scraper Engine: LinkedIn ES uses localized formats for
      company size (e.g., "51 a 200 empleados" instead of "51-200").
      The extraction regex now uses a broad "Word + Digit" bounding box.
    - Chrome Lang Override: Enforces es-ES natively for stable DOM rendering.
==============================================================================
"""

import customtkinter as ctk
from tkinter import filedialog
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time, random, csv, os, webbrowser, json, urllib.parse, logging, sys, threading
from datetime import datetime

# === MODULAR ARCHITECTURE IMPORTS ===
from config import *
from utils import *
from ui_widgets import *

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

# ------------------------------------------------------------------------------
# VIRTUAL LOGGING SYSTEM
# ------------------------------------------------------------------------------
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s", datefmt="%H:%M:%S", handlers=[logging.StreamHandler(sys.stdout)])
log = logging.getLogger(__name__)

# ==============================================================================
# MAIN APPLICATION CONTROLLER
# ==============================================================================
class AIntelligenceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AIntelligence — HR Automation Suite")
        self.geometry("1340x860")
        self.minsize(1100, 760)
        self.configure(fg_color=BG)
        ctk.set_appearance_mode("dark")

        self.driver = None
        self.bot_thread = None
        self.mod1_selected_file = ""
        self.mod2_save_path = ""
        self.mod3_save_path = ""

        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_layout()
        self._build_sidebar()
        self._build_home()
        self._build_mod3()
        self._build_mod1()
        self._build_mod2()
        self._build_tutorial()
        self._build_console()
        self._redirect_logs()
        self._show_frame("home")

    # ----------------------------------------------------------------------
    # VIEW BUILDERS (UI Construction)
    # ----------------------------------------------------------------------
    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.sidebar = ctk.CTkFrame(self, width=290, corner_radius=0, fg_color=PANEL, border_width=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(9, weight=1)
        sep = ctk.CTkFrame(self.sidebar, width=1, fg_color=BORDER)
        sep.place(relx=1.0, rely=0, relheight=1.0, anchor="ne")
        self.content = ctk.CTkFrame(self, corner_radius=0, fg_color=BG)
        self.content.grid(row=0, column=1, sticky="nsew")
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)
        self.frames = {}

    def _build_sidebar(self):
        logo_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        logo_frame.grid(row=0, column=0, padx=28, pady=(40, 8), sticky="ew")
        logo_ok = False
        try:
            if PIL_AVAILABLE and os.path.exists("logo.png"):
                img = Image.open("logo.png")
                w, h = img.size
                new_w = 192
                ci = ctk.CTkImage(light_image=img, dark_image=img, size=(new_w, int(new_w * h / w)))
                lbl_logo = ctk.CTkLabel(logo_frame, image=ci, text="", cursor="hand2")
                lbl_logo.pack(anchor="w")
                lbl_logo.bind("<Button-1>", lambda e: webbrowser.open("https://aintelligence.ai/"))
                logo_ok = True
        except: pass
        if not logo_ok:
            lbl_name = ctk.CTkLabel(logo_frame, text="AIntelligence", font=("Calibri", 22, "bold"), text_color=TEXT, cursor="hand2")
            lbl_name.pack(anchor="w")
            lbl_name.bind("<Button-1>", lambda e: webbrowser.open("https://aintelligence.ai/"))
            lbl_sub = ctk.CTkLabel(logo_frame, text="IT Consultancy — Malta", font=F_LABEL, text_color=CYAN, cursor="hand2")
            lbl_sub.pack(anchor="w", pady=(2, 0))
            lbl_sub.bind("<Button-1>", lambda e: webbrowser.open("https://aintelligence.ai/"))

        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 20))
        ctk.CTkLabel(self.sidebar, text="TOOLS", font=F_LABEL, text_color=TEXT_GHOST).grid(row=2, column=0, padx=32, sticky="w")

        nav_items = [
            ("home", "Connect to Engine"),
            ("mod3", "Find Candidates"),
            ("mod1", "Send Invitations"),
            ("mod2", "Find Open Roles"),
            ("tutorial", "How to Use"),
        ]
        self._nav_btns = {}
        for r, (key, label) in enumerate(nav_items, start=3):
            btn = PillNavButton(self.sidebar, text=label, command=lambda k=key: self._show_frame(k))
            btn.grid(row=r, column=0, padx=20, pady=3, sticky="ew")
            self._nav_btns[key] = btn

        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).grid(row=8, column=0, sticky="ew", padx=28, pady=(8, 0))

        stats_outer = ctk.CTkFrame(self.sidebar, fg_color=CARD, corner_radius=16, border_width=1, border_color=BORDER)
        stats_outer.grid(row=9, column=0, padx=20, pady=24, sticky="sew")
        ctk.CTkLabel(stats_outer, text="TODAY'S ACTIVITY", font=F_LABEL, text_color=TEXT_GHOST).pack(pady=(18, 12))
        stats_row = ctk.CTkFrame(stats_outer, fg_color="transparent")
        stats_row.pack(fill="x", padx=20, pady=(0, 12))
        stats_row.grid_columnconfigure((0, 1), weight=1)
        self._stat_labels = {}
        for col, (key, label, color) in enumerate([("connections", "Connected", CYAN), ("followed", "Companies", CORAL)]):
            sw = StatWidget(stats_row, label=label, color=color)
            sw.grid(row=0, column=col, padx=10, pady=5)
            self._stat_labels[key] = sw
        ctk.CTkFrame(stats_outer, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(4, 12))

        self._dot_frame = ctk.CTkFrame(stats_outer, fg_color="transparent")
        self._dot_frame.pack(pady=(0, 18))
        self._dot = ctk.CTkFrame(self._dot_frame, width=8, height=8, corner_radius=4, fg_color=RED)
        self._dot.pack(side="left", padx=(0, 8))
        self.lbl_status = ctk.CTkLabel(self._dot_frame, text="Engine Off", font=F_UI_B, text_color=RED)
        self.lbl_status.pack(side="left")

    def _build_home(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["home"] = f
        f.grid_columnconfigure(0, weight=1)
        self._page_header(f, "🔌 Connect Your Account", "Log in to your LinkedIn account to start the automation engine.")
        card = ctk.CTkFrame(f, fg_color=CARD, corner_radius=20, border_width=1, border_color=BORDER)
        card.grid(row=1, column=0, padx=60, pady=30, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.grid(row=0, column=0, padx=60, pady=50)
        ctk.CTkLabel(inner, text="Login Details", font=("Calibri", 20, "bold"), text_color=TEXT).pack(pady=(0, 25))
        form_width = 380
        ctk.CTkLabel(inner, text="EMAIL ADDRESS", font=F_LABEL, text_color=TEXT_DIM).pack(anchor="w", padx=5, pady=(0, 5))
        self.e_email = PremiumInput(inner, width=form_width, placeholder_text="example@email.com")
        self.e_email.pack(pady=(0, 20))
        ctk.CTkLabel(inner, text="PASSWORD", font=F_LABEL, text_color=TEXT_DIM).pack(anchor="w", padx=5, pady=(0, 5))
        self.e_pass = PremiumInput(inner, width=form_width, placeholder_text="••••••••", show="*")
        self.e_pass.pack(pady=(0, 35))
        self.btn_arrancar = ctk.CTkButton(inner, text="Start Engine 🚀", fg_color=CYAN, hover_color=CYAN_DIM, text_color="#000000", font=F_BTN, corner_radius=10, height=52, width=form_width, command=self._iniciar_navegador_thread)
        self.btn_arrancar.pack()
        note_frame = ctk.CTkFrame(inner, fg_color=BG, corner_radius=10, border_width=1, border_color=BORDER, width=form_width, height=60)
        note_frame.pack(pady=(25, 0))
        note_frame.pack_propagate(False)
        ctk.CTkLabel(note_frame, text="💡 If LinkedIn asks for a security check or PIN code,\nplease complete it manually in the Chrome window.", font=F_SUBTITLE, text_color=TEXT_DIM, justify="center").place(relx=0.5, rely=0.5, anchor="center")

    def _build_mod3(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["mod3"] = f
        f.grid_columnconfigure(0, weight=1)
        self._page_header(f, "🎯 Find Candidates", "Search LinkedIn for professionals based in Malta.")
        card = AccentCard(f, accent_color=CYAN)
        card.grid(row=1, column=0, padx=60, pady=(8, 16), sticky="ew")
        content = card.inner
        self._section_label(content, "SEARCH SETTINGS", CYAN)
        g = ctk.CTkFrame(content, fg_color="transparent")
        g.pack(fill="x", pady=(10, 20))
        g.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(g, text="JOB TITLE TO SEARCH", font=F_LABEL, text_color=TEXT_DIM).grid(row=0, column=0, padx=(0, 16), sticky="w")
        ctk.CTkLabel(g, text="PAGES TO SCAN (1-5)", font=F_LABEL, text_color=TEXT_DIM).grid(row=0, column=1, sticky="w")
        self.e_m3_perfil = PremiumInput(g, placeholder_text="e.g. CTO, Software Engineer")
        self.e_m3_perfil.grid(row=1, column=0, padx=(0, 16), pady=(6, 0), sticky="ew")
        self.e_m3_pags = PremiumInput(g, placeholder_text="e.g. 2")
        self.e_m3_pags.grid(row=1, column=1, pady=(6, 0), sticky="ew")
        self._section_label(content, "FILE COLUMNS", TEXT_DIM)
        fmt = ctk.CTkFrame(content, fg_color=BG, corner_radius=10, border_width=1, border_color=BORDER)
        fmt.pack(fill="x", pady=(8, 24))
        ctk.CTkLabel(fmt, text="Name   /   Job Title   /   Current Company   /   Profile URL", font=F_MON, text_color=CYAN).pack(padx=20, pady=12)
        self._section_label(content, "PROGRESS", TEXT_DIM)
        self.prog3 = GlowProgressBar(content, color=CYAN)
        self.prog3.pack(fill="x", pady=(8, 24))
        self.container_btn3 = ctk.CTkFrame(content, fg_color="transparent")
        self.container_btn3.pack(fill="x", pady=(4, 8))
        self.btn_start3 = ctk.CTkButton(self.container_btn3, text="Build Contact List ⚡", fg_color=CYAN, hover_color=CYAN_DIM, text_color="#000", font=F_BTN, corner_radius=10, height=52, command=self._pre_run_mod3)
        self.btn_start3.pack(fill="x")
        self.ctrl_frame3 = ctk.CTkFrame(self.container_btn3, fg_color="transparent")
        self.btn_pause3 = ctk.CTkButton(self.ctrl_frame3, text="⏸ Pause", fg_color=AMBER, hover_color="#e6a13c", text_color="#000", font=F_BTN, corner_radius=10, height=52, command=self._toggle_pause)
        self.btn_pause3.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.btn_stop3 = ctk.CTkButton(self.ctrl_frame3, text="⏹ Stop", fg_color=RED, hover_color="#cc2d4a", text_color="#fff", font=F_BTN, corner_radius=10, height=52, command=self._stop_task)
        self.btn_stop3.pack(side="left", fill="x", expand=True, padx=(6, 0))

    def _build_mod1(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["mod1"] = f
        f.grid_columnconfigure(0, weight=1)
        self._page_header(f, "🤖 Send Invitations", "Automatically send LinkedIn connection requests using your contact list.")
        card = AccentCard(f, accent_color=EMERALD)
        card.grid(row=1, column=0, padx=60, pady=(8, 16), sticky="ew")
        content = card.inner
        self._section_label(content, "CONTACT LIST FILE", EMERALD)
        file_frame = ctk.CTkFrame(content, fg_color=BG, corner_radius=10, border_width=1, border_color=BORDER)
        file_frame.pack(fill="x", pady=(8, 28))
        file_frame.grid_columnconfigure(0, weight=1)
        self.lbl_archivo_mod1 = ctk.CTkLabel(file_frame, text="No file selected...", font=F_MON, text_color=TEXT_DIM, anchor="w")
        self.lbl_archivo_mod1.grid(row=0, column=0, padx=20, pady=16, sticky="w")
        btn_sel = ctk.CTkButton(file_frame, text="Choose File", width=160, height=36, fg_color=CARD, hover_color=BORDER, border_width=1, border_color=BORDER_LT, font=F_UI_B, text_color=TEXT, corner_radius=8, command=self._seleccionar_archivo)
        btn_sel.grid(row=0, column=1, padx=16, pady=12)
        self._section_label(content, "SENDING PROGRESS", TEXT_DIM)
        self.prog1 = GlowProgressBar(content, color=EMERALD)
        self.prog1.pack(fill="x", pady=(8, 24))
        self.container_btn1 = ctk.CTkFrame(content, fg_color="transparent")
        self.container_btn1.pack(fill="x", pady=(4, 8))
        self.btn_start1 = ctk.CTkButton(self.container_btn1, text="Start Sending ⚡", fg_color=EMERALD, hover_color="#009970", text_color="#000", font=F_BTN, corner_radius=10, height=52, command=lambda: self._lanzar_modulo(1))
        self.btn_start1.pack(fill="x")
        self.ctrl_frame1 = ctk.CTkFrame(self.container_btn1, fg_color="transparent")
        self.btn_pause1 = ctk.CTkButton(self.ctrl_frame1, text="⏸ Pause", fg_color=AMBER, hover_color="#e6a13c", text_color="#000", font=F_BTN, corner_radius=10, height=52, command=self._toggle_pause)
        self.btn_pause1.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.btn_stop1 = ctk.CTkButton(self.ctrl_frame1, text="⏹ Stop", fg_color=RED, hover_color="#cc2d4a", text_color="#fff", font=F_BTN, corner_radius=10, height=52, command=self._stop_task)
        self.btn_stop1.pack(side="left", fill="x", expand=True, padx=(6, 0))

    def _seleccionar_archivo(self):
        """Opens the OS file browser to load the CSV."""
        path = filedialog.askopenfilename(title="Select your Contact List (CSV)", filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")])
        if path:
            self.mod1_selected_file = path
            name = os.path.basename(path)
            self.lbl_archivo_mod1.configure(text=name, text_color=EMERALD)
            self._log(f"File loaded: {name}")

    def _build_mod2(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["mod2"] = f
        f.grid_columnconfigure(0, weight=1)
        self._page_header(f, "🏢 Find Open Roles", "Find companies hiring in Malta and locate the Hiring Manager.")
        card = AccentCard(f, accent_color=CORAL)
        card.grid(row=1, column=0, padx=60, pady=(8, 16), sticky="ew")
        content = card.inner
        self._section_label(content, "SEARCH FILTERS", CORAL)
        g = ctk.CTkFrame(content, fg_color="transparent")
        g.pack(fill="x", pady=(10, 20))
        g.grid_columnconfigure((0, 1, 2, 3), weight=1)
        defs2 = [
            ("KEYWORD", "e_m2_puesto", PremiumInput, {"placeholder_text": "e.g. IT, Finance"}),
            ("WORK TYPE", "cb_m2_tipo", PremiumCombo, {"values": ["All", "On-site", "Hybrid", "Remote"]}),
            ("DATE POSTED", "cb_m2_tiempo", PremiumCombo, {"values": ["Any time", "Last 24h", "Last week"]}),
            ("PAGES (x25 results)", "e_m2_pags", PremiumInput, {"placeholder_text": "e.g. 2"}),
        ]
        for col, (lbl, attr, Cls, kw) in enumerate(defs2):
            ctk.CTkLabel(g, text=lbl, font=F_LABEL, text_color=TEXT_DIM).grid(row=0, column=col, padx=12, sticky="w")
            widget = Cls(g, **kw)
            widget.grid(row=1, column=col, padx=12, pady=(6, 0), sticky="ew")
            setattr(self, attr, widget)
        self._section_label(content, "SCAN PROGRESS", TEXT_DIM)
        self.prog2 = GlowProgressBar(content, color=CORAL)
        self.prog2.pack(fill="x", pady=(8, 24))
        self.container_btn2 = ctk.CTkFrame(content, fg_color="transparent")
        self.container_btn2.pack(fill="x", pady=(4, 8))
        self.btn_start2 = ctk.CTkButton(self.container_btn2, text="Scan for Open Roles ⚡", fg_color=CORAL, hover_color=CORAL_DIM, text_color="#fff", font=F_BTN, corner_radius=10, height=52, command=self._pre_run_mod2)
        self.btn_start2.pack(fill="x")
        self.ctrl_frame2 = ctk.CTkFrame(self.container_btn2, fg_color="transparent")
        self.btn_pause2 = ctk.CTkButton(self.ctrl_frame2, text="⏸ Pause", fg_color=AMBER, hover_color="#e6a13c", text_color="#000", font=F_BTN, corner_radius=10, height=52, command=self._toggle_pause)
        self.btn_pause2.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.btn_stop2 = ctk.CTkButton(self.ctrl_frame2, text="⏹ Stop", fg_color=RED, hover_color="#cc2d4a", text_color="#fff", font=F_BTN, corner_radius=10, height=52, command=self._stop_task)
        self.btn_stop2.pack(side="left", fill="x", expand=True, padx=(6, 0))

    def _build_tutorial(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["tutorial"] = f
        f.grid_columnconfigure(0, weight=1)
        self._page_header(f, "📖 How to Use", "Follow these four steps to get started quickly.")
        sf = ctk.CTkScrollableFrame(f, fg_color=CARD, corner_radius=20, border_width=1, border_color=BORDER)
        sf.grid(row=1, column=0, padx=60, pady=20, sticky="nsew")
        f.grid_rowconfigure(1, weight=1)
        pasos = [
            ("Step 1 — Log In", CYAN, "Go to the first tab, enter your LinkedIn email and password, then click Start Engine. A Chrome window will open — the tool uses it to browse LinkedIn on your behalf. If LinkedIn asks you to complete a security check or enter a code, just do it manually in that window. Once done, the left panel will show Engine Online."),
            ("Step 2 — Find Candidates", CYAN, "Type the job title you are looking for in Malta (e.g. Software Engineer, Marketing Manager) and choose how many pages to scan (up to 5). The tool will search LinkedIn automatically and save a spreadsheet file with each person's Name, Job Title and Company."),
            ("Step 3 — Send Invitations", EMERALD, "Go to this tab and click Choose File. Select the spreadsheet you created in the previous step. When you click Start Sending, the tool will visit each person's profile and send them a connection request. It pauses between requests to stay safe and avoid any account restrictions."),
            ("Step 4 — Find Open Roles", CORAL, "Use this option to find companies that are actively hiring. Type a sector (e.g. IT, Finance) and the tool will scan Malta's job listings, extracting the company name, work type and the contact details of the hiring team."),
        ]
        for title, color, text in pasos:
            h = ctk.CTkFrame(sf, fg_color="transparent")
            h.pack(fill="x", padx=30, pady=(30, 0))
            h.grid_columnconfigure(1, weight=1)
            pill = ctk.CTkFrame(h, width=6, height=24, corner_radius=3, fg_color=color)
            pill.grid(row=0, column=0, padx=(0, 14), sticky="ns")
            ctk.CTkLabel(h, text=title, font=("Calibri", 16, "bold"), text_color=color).grid(row=0, column=1, sticky="w")
            ctk.CTkFrame(sf, height=1, fg_color=BORDER).pack(fill="x", padx=30, pady=(8, 12))
            ctk.CTkLabel(sf, text=text, font=F_UI, text_color=TEXT, justify="left", wraplength=820, anchor="w").pack(fill="x", padx=44, pady=(0, 12))

    def _build_console(self):
        co = ctk.CTkFrame(self.content, fg_color=PANEL, corner_radius=0, height=230)
        co.grid(row=2, column=0, sticky="ew")
        co.grid_propagate(False)
        co.grid_columnconfigure(0, weight=1)
        co.grid_rowconfigure(1, weight=1)
        hdr = ctk.CTkFrame(co, fg_color=CARD, corner_radius=0, height=36)
        hdr.grid(row=0, column=0, sticky="ew")
        hdr.grid_columnconfigure(1, weight=1)
        hdr.grid_propagate(False)
        dots = ctk.CTkFrame(hdr, fg_color="transparent")
        dots.grid(row=0, column=0, padx=20, sticky="w")
        for dot_color in [CORAL, AMBER, EMERALD]:
            ctk.CTkFrame(dots, width=10, height=10, corner_radius=5, fg_color=dot_color).pack(side="left", padx=3, pady=12)
        ctk.CTkLabel(hdr, text="ACTIVITY LOG", font=F_LABEL, text_color=TEXT_DIM).grid(row=0, column=1, sticky="w", padx=8)
        live_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        live_frame.grid(row=0, column=2, padx=20, sticky="e")
        ctk.CTkFrame(live_frame, width=8, height=8, corner_radius=4, fg_color=EMERALD).pack(side="left", padx=(0, 6), pady=14)
        ctk.CTkLabel(live_frame, text="LIVE", font=F_LABEL, text_color=EMERALD).pack(side="left")

        # Read-only activity log terminal
        self.console = ctk.CTkTextbox(co, fg_color="#050508", text_color=EMERALD, font=F_MON, corner_radius=0, border_width=0, wrap="word")
        self.console.grid(row=1, column=0, sticky="nsew")

    # ----------------------------------------------------------------------
    # UI HELPER METHODS
    # ----------------------------------------------------------------------
    def _page_header(self, parent, title, subtitle):
        """Renders consistent page headers across all views."""
        header_frame = ctk.CTkFrame(parent, fg_color="transparent")
        header_frame.grid(row=0, column=0, padx=60, pady=(44, 0), sticky="ew")
        header_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header_frame, text=title, font=F_TITLE, text_color=TEXT, anchor="w").grid(row=0, column=0, sticky="w")
        line_frame = ctk.CTkFrame(header_frame, fg_color="transparent")
        line_frame.grid(row=1, column=0, sticky="ew", pady=(4, 0))
        line_frame.grid_columnconfigure(1, weight=1)
        ctk.CTkFrame(line_frame, width=40, height=2, corner_radius=1, fg_color=CYAN).grid(row=0, column=0)
        ctk.CTkFrame(line_frame, height=1, fg_color=BORDER).grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ctk.CTkLabel(header_frame, text=subtitle, font=F_SUBTITLE, text_color=TEXT_DIM, anchor="w").grid(row=2, column=0, sticky="w", pady=(8, 16))

    def _premium_card(self, parent, row=1, accent=CYAN):
        card = AccentCard(parent, accent_color=accent)
        card.grid(row=row, column=0, padx=60, pady=(8, 16), sticky="ew")
        card.inner.grid_columnconfigure(0, weight=1)
        return card

    def _section_label(self, parent, text, color=TEXT_DIM):
        frame = ctk.CTkFrame(parent, fg_color="transparent", height=22)
        frame.pack(fill="x", pady=(20, 0))
        frame.pack_propagate(False)
        frame.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(frame, text=text, font=F_LABEL, text_color=color).pack(side="left")
        ctk.CTkFrame(frame, height=1, fg_color=BORDER).pack(side="left", fill="x", expand=True, padx=(12, 0), pady=(2, 0))

    def _log(self, msg):
        """Injects text into the activity log via the Tkinter main thread."""
        def _do():
            self.console.insert(ctk.END, f"[{datetime.now().strftime('%H:%M:%S')}]  {msg}\n")
            self.console.see(ctk.END) # Auto-scroll to bottom
        self.after(0, _do)

    def _update_stats(self):
        def _do():
            for key, sw in self._stat_labels.items():
                sw.set_value(counters[key])
        self.after(0, _do)

    def _set_progress(self, bar, value, text):
        def _do(): bar.update(value, text)
        self.after(0, _do)

    def _set_session_status(self, texto, color):
        def _do():
            self._dot.configure(fg_color=color)
            self.lbl_status.configure(text=texto, text_color=color)
        self.after(0, _do)

    def _redirect_logs(self):
        """Hijacks Python's stdout to pipe native print/log messages to the UI Terminal."""
        app = self
        class GUIHandler(logging.Handler):
            def emit(self, record): app._log(self.format(record))
        h = GUIHandler()
        h.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(h)

    def _show_frame(self, key):
        """Internal router logic. Enforces login state before accessing tools."""
        if key in ("mod1", "mod2", "mod3") and not self.driver:
            self._log("Please start the engine from the first tab before using this section.")
            key = "home"
        if key in ("mod1", "mod2", "mod3") and self.driver:
            url = self.driver.current_url
            if "login" in url or "authwall" in url:
                self._log("LinkedIn session has expired. Please go back to the first tab and log in again.")
                key = "home"
        for btn in self._nav_btns.values(): btn.configure(text_color=TEXT_DIM, fg_color="transparent")
        if key in self._nav_btns: self._nav_btns[key].configure(text_color=TEXT, fg_color=CARD)
        for fr in self.frames.values(): fr.grid_forget()
        self.frames[key].grid(row=0, column=0, sticky="nsew")

    def _set_modulo_buttons(self, state):
        def _do():
            self.btn_arrancar.configure(state=state)
            if state == "normal":
                self.ctrl_frame1.pack_forget(); self.btn_start1.pack(fill="x")
                self.ctrl_frame2.pack_forget(); self.btn_start2.pack(fill="x")
                self.ctrl_frame3.pack_forget(); self.btn_start3.pack(fill="x")
            else:
                self.btn_start1.pack_forget(); self.btn_start2.pack_forget(); self.btn_start3.pack_forget()
        self.after(0, _do)

    def _on_close(self):
        """Garbage Collector: Kills the orphan Chrome instance in RAM upon exit."""
        if self.driver:
            try: self.driver.quit()
            except: pass
        self.destroy()

    # ----------------------------------------------------------------------
    # CONCURRENCY AND THREAD SEMAPHORES
    # ----------------------------------------------------------------------
    def _toggle_pause(self):
        """Event Semaphore control: Pauses the background thread without killing it."""
        if self.pause_event.is_set():
            self.pause_event.clear()
            self._log("⏸ Paused. Click Resume to continue.")
            for btn in [self.btn_pause1, self.btn_pause2, self.btn_pause3]:
                btn.configure(text="▶ Resume", fg_color=EMERALD, hover_color="#009970")
        else:
            self.pause_event.set()
            self._log("▶ Resumed.")
            for btn in [self.btn_pause1, self.btn_pause2, self.btn_pause3]:
                btn.configure(text="⏸ Pause", fg_color=AMBER, hover_color="#e6a13c")

    def _stop_task(self):
        self._log("⏹ Stopping... The tool will stop after finishing its current action.")
        self.stop_event.set()
        self.pause_event.set()

    def _check_stop_pause(self):
        """Checkpoint injected in heavy loops. Blocks if paused, kills thread if stopped."""
        if self.stop_event.is_set(): raise InterruptedError("Cancelled by user.")
        self.pause_event.wait()

    def _pausa(self, a=8, b=14):
        """Smart thread pause: slices the wait time to keep the GUI responsive."""
        t = random.uniform(a, b)
        steps = int(t / 0.5)
        for _ in range(steps):
            self._check_stop_pause()
            time.sleep(0.5)
        remainder = t - (steps * 0.5)
        if remainder > 0:
            self._check_stop_pause()
            time.sleep(remainder)

    def _detectar_captcha(self):
        """Security Watchdog: Halts execution if a LinkedIn Authwall is detected."""
        url = self.driver.current_url
        if any(x in url for x in ["captcha", "checkpoint", "challenge", "authwall"]):
            self._log("🔒 LINKEDIN SECURITY CHECK DETECTED")
            self._log("👉 Please complete the security check or enter the PIN code in the Chrome window.")
            self._log("   (The tool will continue automatically once you are done.)")
            while any(x in self.driver.current_url for x in ["captcha", "checkpoint", "challenge", "authwall"]):
                self._check_stop_pause()
                time.sleep(2)
            self._log("✅ Security check passed. Resuming...")
            time.sleep(2)
            return True
        return False

    # ----------------------------------------------------------------------
    # BROWSER LAUNCH AND SESSION MANAGEMENT
    # ----------------------------------------------------------------------
    def _iniciar_navegador_thread(self):
        self.btn_arrancar.configure(state="disabled")
        self._log("Starting Chrome engine...")
        threading.Thread(target=self._proceso_login, daemon=True).start()

    def _proceso_login(self):
        """Initializes Undetected ChromeDriver and manages persistent Cookies."""
        email = self.e_email.get().strip()
        password = self.e_pass.get().strip()
        try:
            opts = uc.ChromeOptions()
            opts.add_argument("--disable-blink-features=AutomationControlled")
            # Force Spanish localization in Chrome to match the user's actual LinkedIn account,
            # ensuring DOM selectors don't break when switching languages.
            opts.add_argument("--lang=es-ES")
            self.driver = uc.Chrome(options=opts, version_main=145)

            # Chrome DevTools Protocol command to strip webdriver flags
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"})

            if os.path.isfile(COOKIES_FILE):
                with open(COOKIES_FILE, "r", encoding="utf-8") as f: loaded_cookies = json.load(f)
                self.driver.get("https://www.linkedin.com")
                random_pause(2, 4)
                for ck in loaded_cookies:
                    try: self.driver.add_cookie(ck)
                    except: pass
                self.driver.refresh()
                random_pause(4, 6)

                if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
                    self._log("Session restored. Engine ready.")
                    self._set_session_status("Engine Online", EMERALD)
                    self._encoger_ventana()
                    return
                else:
                    self._log("⚠️ Saved session has expired or belongs to a different account.")
                    self._log("🧹 Clearing old session...")
                    self.driver.delete_all_cookies()
                    try: os.remove(COOKIES_FILE)
                    except: pass
                    random_pause(2, 3)

            self.driver.get("https://www.linkedin.com/login")
            random_pause(2, 4)

            if email and password:
                self._log("Injecting credentials...")
                try:
                    js_inject = """
                    var email = arguments[0]; var pwd = arguments[1];
                    var em_el = document.querySelector("#username") || document.querySelector("input[name='session_key']") || document.querySelector("input[autocomplete='username']");
                    var pw_el = document.querySelector("#password") || document.querySelector("input[name='session_password']") || document.querySelector("input[autocomplete='current-password']");
                    var btn   = document.querySelector("button[type='submit']") || document.querySelector("button[data-litms-control-urn='login-submit']");
                    if(em_el && pw_el && btn) {
                        em_el.focus(); em_el.value = email; em_el.dispatchEvent(new Event('input', { bubbles: true }));
                        pw_el.focus(); pw_el.value = pwd; pw_el.dispatchEvent(new Event('input', { bubbles: true }));
                        btn.click(); return true;
                    } return false;
                    """
                    exito = self.driver.execute_script(js_inject, email, password)
                    if exito: self._log("Credentials entered. Checking...")
                    else: self._log("Could not find login fields. Please log in manually in the Chrome window.")
                except Exception: self._log("Auto-login failed. Please do it manually.")
            else:
                self._log("Please log in manually in the Chrome window.")

            self._log("Waiting for LinkedIn to confirm login...")
            intentos = 0
            while True:
                url = self.driver.current_url
                if any(x in url for x in ["feed", "mynetwork", "search", "in/"]): break
                if intentos > 60:
                    self._log("Still waiting... Please complete any security check in the Chrome window.")
                    intentos = 0
                random_pause(1.5, 2.5)
                intentos += 1

            saved_cookies = self.driver.get_cookies()
            with open(COOKIES_FILE, "w", encoding="utf-8") as f: json.dump(saved_cookies, f)
            self._log("Session saved. Engine ready.")
            self._set_session_status("Engine Online", EMERALD)
            self._encoger_ventana()

        except Exception as e:
            self._log(f"Error starting Chrome: {e}")
            self.after(0, lambda: self.btn_arrancar.configure(state="normal"))

    def _encoger_ventana(self):
        """Moves Chrome to the corner to avoid Background Tab Throttling."""
        try:
            self.driver.set_window_position(0, 0)
            self.driver.set_window_size(600, 600)
            self._log("💡 Chrome has moved to the side so you can keep working here.")
        except: pass

    # ----------------------------------------------------------------------
    # MODULE ORCHESTRATOR
    # ----------------------------------------------------------------------
    def _lanzar_modulo(self, num):
        if self.bot_thread and self.bot_thread.is_alive():
            self._log("A task is already running. Please wait for it to finish.")
            return
        self.stop_event.clear()
        self.pause_event.set()
        for btn in [self.btn_pause1, self.btn_pause2, self.btn_pause3]:
            btn.configure(text="⏸ Pause", fg_color=AMBER, hover_color="#e6a13c")
        self._set_modulo_buttons("disabled")

        def _show_ctrl():
            if num == 1: self.ctrl_frame1.pack(fill="x")
            elif num == 2: self.ctrl_frame2.pack(fill="x")
            elif num == 3: self.ctrl_frame3.pack(fill="x")

        self.after(0, _show_ctrl)
        targets = {1: self._run_mod1, 2: self._run_mod2, 3: self._run_mod3}
        self.bot_thread = threading.Thread(target=targets[num], daemon=True)
        self.bot_thread.start()

    # ======================================================================
    # CONNECTION ENGINE v5 — SHADOW PIERCER & SCOPE RESTRICTION
    # ======================================================================
    def _click_natively(self, element, log_method=None):
        if not element: raise Exception("Element not found.")
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", element)
            time.sleep(0.5)
        except: pass

        try:
            self.driver.execute_script("arguments[0].focus();", element)
            time.sleep(0.2)
            element.send_keys(Keys.ENTER)
            if log_method: log_method("  [Engine] Click executed.")
            return
        except: pass

        try:
            ActionChains(self.driver).move_to_element(element).click().perform()
            return
        except: pass

        try:
            element.click()
            return
        except: pass

        try:
            self.driver.execute_script("arguments[0].click();", element)
            return
        except Exception as e:
            raise Exception(f"Click failed: {e}")

    def _esperar_zona_acciones(self):
        selectores = ["//div[contains(@class,'pvs-profile-actions')]", "//div[contains(@class,'pv-top-card-v2-ctas')]", "//div[contains(@class,'ph5') and .//button]"]
        for xp in selectores:
            try:
                WebDriverWait(self.driver, 8).until(EC.presence_of_element_located((By.XPATH, xp)))
                time.sleep(random.uniform(1.0, 1.8))
                return True
            except TimeoutException: continue
        time.sleep(3)
        return False

    def _localizar_elemento_por_js(self, tipo):
        if tipo == 'conectar':
            script = """
            var topCard = document.querySelector(".pv-top-card, .ph5");
            if(!topCard) topCard = document.querySelector("main");
            if(!topCard) return null;
            var els = topCard.querySelectorAll("button, a, [role='button']");
            for(var i=0; i<els.length; i++) {
                var el = els[i];
                var txt = (el.innerText || "").trim().toLowerCase();
                var aria = (el.getAttribute("aria-label") || "").trim().toLowerCase();
                if (txt === "conectar" || txt === "connect" || 
                   (aria.includes("invitar") && aria.includes("conectar")) ||
                   (aria.includes("invite") && aria.includes("connect"))) {
                   var rect = el.getBoundingClientRect();
                   if(rect.width > 5 && rect.height > 5 && window.getComputedStyle(el).visibility !== "hidden") {
                       return el;
                   }
                }
            }
            return null;
            """
            return self.driver.execute_script(script)

        elif tipo == 'mas':
            script = """
            var topCard = document.querySelector(".pv-top-card, .ph5");
            if(!topCard) topCard = document.querySelector("main");
            if(!topCard) return null;
            var els = topCard.querySelectorAll("button, a, [role='button']");
            for(var i=0; i<els.length; i++) {
                var el = els[i];
                var txt = (el.innerText || "").trim().toLowerCase();
                var aria = (el.getAttribute("aria-label") || "").trim().toLowerCase();
                if(txt === "más" || txt === "more" || aria.includes("más opciones") || aria.includes("more actions")) {
                    var rect = el.getBoundingClientRect();
                    if(rect.width > 5 && rect.height > 5 && window.getComputedStyle(el).visibility !== "hidden") {
                        return el;
                    }
                }
            }
            return null;
            """
            return self.driver.execute_script(script)

        elif tipo == 'conectar_en_menu':
            script = """
            var spans = document.querySelectorAll("div.artdeco-dropdown__content span, div.artdeco-dropdown__content div, div.artdeco-dropdown__content a");
            for(var i=0; i<spans.length; i++) {
                var txt = (spans[i].innerText || "").trim().toLowerCase();
                if(txt === "conectar" || txt === "connect") {
                    var rect = spans[i].getBoundingClientRect();
                    if(rect.width > 2) return spans[i];
                }
            }
            return null;
            """
            return self.driver.execute_script(script)
        return None

    def _manejar_modal_conexion(self, nombre):
        """Pierces the Shadow DOM to accept silent connections without user friction."""
        time.sleep(random.uniform(1.8, 2.8))

        for intento_modal in range(3):
            self._check_stop_pause()

            script_check_modal = """
            var host = document.querySelector('#interop-outlet');
            var root = (host && host.shadowRoot) ? host.shadowRoot : document;
            var modal = root.querySelector("div[role='dialog'], .artdeco-modal");
            if(!modal) return {exists: false, html: ""};
            return {exists: true, html: modal.innerHTML.toLowerCase()};
            """
            modal_state = self.driver.execute_script(script_check_modal)

            if not modal_state or not modal_state.get("exists"):
                if self._verificar_envio_exitoso(fast_check=True):
                    self._log("  ✔ Invitation sent instantly.")
                    return True
                self._log(f"  ℹ️ Waiting for confirmation window (attempt {intento_modal + 1})...")
                time.sleep(1)
                continue

            html = modal_state.get("html", "")

            es_friccion = any(x in html for x in [
                "cómo conoces", "how do you know", "te invitamos a conectar",
                "invited to connect", "¿cómo conociste"
            ])

            if es_friccion:
                self._log("  🛡️ LinkedIn asked how you know this person — selecting Other...")
                script_friccion = """
                var host = document.querySelector('#interop-outlet');
                var root = (host && host.shadowRoot) ? host.shadowRoot : document;
                var labels = root.querySelectorAll("label");
                var clicked = false;
                for(var i=0; i<labels.length; i++){
                    var txt = labels[i].innerText.toLowerCase();
                    if(txt.includes('otro') || txt.includes('other')){
                        labels[i].click();
                        clicked = true; break;
                    }
                }
                if(!clicked){
                    var radios = root.querySelectorAll("input[type='radio'][value='OTHER'], input[type='radio'][value='other'], input[type='radio'][value='Otro']");
                    if(radios.length > 0) { radios[0].click(); clicked = true; }
                }
                return clicked;
                """
                if self.driver.execute_script(script_friccion):
                    time.sleep(1)
                    script_primary = """
                    var host = document.querySelector('#interop-outlet');
                    var root = (host && host.shadowRoot) ? host.shadowRoot : document;
                    var btn = root.querySelector("button.artdeco-button--primary:not([disabled])");
                    if(btn){ btn.click(); return true; }
                    return false;
                    """
                    if self.driver.execute_script(script_primary):
                        self._log("  ✔ Question answered — clicking Send...")
                        time.sleep(2)
                        continue
                self._log("  ❌ Could not answer LinkedIn's question. Skipping this profile.")

                self.driver.execute_script("""
                var host = document.querySelector('#interop-outlet');
                var root = (host && host.shadowRoot) ? host.shadowRoot : document;
                var btn = root.querySelector("button[aria-label='Descartar'], button[aria-label='Dismiss'], button.artdeco-modal__dismiss");
                if(btn) btn.click();
                """)
                return False

            if any(x in html for x in ["sin nota", "without a note", "send without"]):
                script_sin_nota = """
                var host = document.querySelector('#interop-outlet');
                var root = (host && host.shadowRoot) ? host.shadowRoot : document;
                var btns = root.querySelectorAll("button");
                for(var i=0; i<btns.length; i++){
                    var txt = btns[i].innerText.toLowerCase();
                    var aria = (btns[i].getAttribute('aria-label') || '').toLowerCase();
                    if(txt.includes('sin nota') || txt.includes('without') || aria.includes('sin nota') || aria.includes('without')){
                        btns[i].focus();
                        btns[i].click();
                        return true;
                    }
                }
                return false;
                """
                if self.driver.execute_script(script_sin_nota):
                    self._log("  ✔ Sent without a note")
                    time.sleep(random.uniform(2.0, 3.0))
                    return True

            if any(x in html for x in ["enviar", "send", "conectar", "connect"]):
                script_send = """
                var host = document.querySelector('#interop-outlet');
                var root = (host && host.shadowRoot) ? host.shadowRoot : document;
                var btn = root.querySelector("button.artdeco-button--primary:not([disabled])");
                if(btn){ btn.focus(); btn.click(); return true; }
                return false;
                """
                if self.driver.execute_script(script_send):
                    self._log("  ✔ Invitation confirmed")
                    time.sleep(random.uniform(2.0, 3.0))
                    return True

            if "textarea" in html or "message" in html or "mensaje" in html:
                script_skip = """
                var host = document.querySelector('#interop-outlet');
                var root = (host && host.shadowRoot) ? host.shadowRoot : document;
                var btns = root.querySelectorAll("button");
                for(var i=0; i<btns.length; i++){
                    var aria = (btns[i].getAttribute('aria-label') || '').toLowerCase();
                    if(aria.includes('sin nota') || aria.includes('without')){
                        btns[i].focus(); btns[i].click(); return true;
                    }
                }
                return false;
                """
                if self.driver.execute_script(script_skip):
                    self._log("  ✔ Skipped note")
                    time.sleep(random.uniform(2.0, 3.0))
                    return True
            break

        return self._verificar_envio_exitoso()

    def _verificar_envio_exitoso(self, fast_check=False):
        intentos = 1 if fast_check else 4
        for _ in range(intentos):
            if not fast_check: time.sleep(1.0)

            script_check_modal = """
            var host = document.querySelector('#interop-outlet');
            var root = (host && host.shadowRoot) ? host.shadowRoot : document;
            var modal = root.querySelector("div[role='dialog'], .artdeco-modal");
            return modal !== null;
            """
            modal_exists = self.driver.execute_script(script_check_modal)
            if modal_exists:
                continue

            try:
                xp = "//main//*[self::button or self::a or @role='button'][contains(translate(normalize-space(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'pendiente') or contains(translate(normalize-space(),'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'pending')]"
                botones = self.driver.find_elements(By.XPATH, xp)
                for b in botones:
                    if b.is_displayed():
                        time.sleep(1.5)
                        botones_recheck = self.driver.find_elements(By.XPATH, xp)
                        if botones_recheck and botones_recheck[0].is_displayed():
                            return True
                        else:
                            self._log("  ⚠️ LinkedIn rejected the invitation. Skipping this profile.")
                            return False

                toasts = self.driver.find_elements(By.XPATH, "//*[contains(@class,'artdeco-toast') or contains(@class,'notification')]")
                for t in toasts:
                    if t.is_displayed():
                        txt = t.text.lower()
                        if any(x in txt for x in ["enviada", "sent", "éxito", "success", "invitación"]):
                            return True
            except Exception: pass
        return False

    # ======================================================================
    # MODULE 1: AUTOMATED NETWORKING BOT
    # ======================================================================
    def _run_mod1(self):
        archivo = self.mod1_selected_file
        if not archivo or not os.path.isfile(archivo):
            self._log("Error: Please select a valid CSV file first.")
            self._set_modulo_buttons("normal"); return

        self._log(f"Loading leads list — {os.path.basename(archivo)}")
        procesados = load_processed()
        filas = []

        # Auto-Encoding Shield: Prevents crash when MS Excel saves as ANSI/Latin1
        encodings_to_try = ["utf-8-sig", "latin1", "cp1252", "iso-8859-1"]
        lectura_exitosa = False

        for enc in encodings_to_try:
            try:
                filas.clear()
                with open(archivo, "r", encoding=enc) as f:
                    rd = csv.DictReader(f)
                    if rd.fieldnames: rd.fieldnames = [c.strip().lower() for c in rd.fieldnames]
                    for row in rd:
                        url_col = next((c for c in (rd.fieldnames or []) if "url" in c), None)
                        nom_col = next((c for c in (rd.fieldnames or []) if "nombre" in c or "name" in c), None)
                        if url_col:
                            url = row.get(url_col, "").strip()
                            nom = row.get(nom_col, "Unknown").strip() if nom_col else "Unknown"
                            if url.startswith("http") and url not in procesados:
                                filas.append((url, nom))
                lectura_exitosa = True
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                self._log(f"Unexpected error reading file: {e}")
                self._set_modulo_buttons("normal"); return

        if not lectura_exitosa:
            self._log("File encoding error. Please open the file in Excel and save it as 'CSV UTF-8'.")
            self._set_modulo_buttons("normal"); return

        total = len(filas)
        if total == 0:
            self._log("The file is empty or all profiles have already been processed.")
            self._set_modulo_buttons("normal"); return

        self._log(f"{total} new profiles queued.")

        try:
            for i, (enlace, nombre) in enumerate(filas, 1):
                self._check_stop_pause()
                self._set_progress(self.prog1, i / max(total, 1), f"[{i}/{total}]  {nombre[:35]}")

                # Environment fallback logic
                if counters["connections"] >= MAX_CONNECTIONS_PER_DAY:
                    self._log("Daily limit reached. Stopping to protect your account.")
                    break

                self.driver.get(enlace)
                self._pausa(4, 7)
                self._detectar_captcha()
                self._check_stop_pause()

                try:
                    if "/in/" in enlace.lower():
                        self._log(f"  → Navigating to: {nombre}...")
                        self._esperar_zona_acciones()
                        self._check_stop_pause()

                        btn_connect = self._localizar_elemento_por_js('conectar')
                        clicked = False

                        if btn_connect:
                            self._log("  ✔ Connect button found")
                            try:
                                self._click_natively(btn_connect, self._log)
                                clicked = True
                            except Exception as e_click:
                                self._log(f"  ⚠️ Click error: {e_click}")
                        else:
                            self._log("  ℹ️ Direct button hidden — Searching in 'More'...")
                            btn_mas = self._localizar_elemento_por_js('mas')
                            if btn_mas:
                                try:
                                    self._click_natively(btn_mas, self._log)
                                    time.sleep(1.5)
                                    btn_connect_menu = self._localizar_elemento_por_js('conectar_en_menu')
                                    if btn_connect_menu:
                                        self._click_natively(btn_connect_menu, self._log)
                                        clicked = True
                                    else:
                                        self.driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                                except Exception: pass

                        if clicked:
                            exito = self._manejar_modal_conexion(nombre)
                            if exito:
                                inc("connections")
                                self._log(f"  ✅ Invitation confirmed for → {nombre}")
                            else:
                                exito_tardio = self._verificar_envio_exitoso()
                                if exito_tardio:
                                    inc("connections")
                                    self._log(f"  ✅ Invitation confirmed after checking → {nombre}")
                                else:
                                    self._log(f"  ⚠️ Could not confirm invitation for: {nombre}")
                        else:
                            self._log(f"  ⛔ No Connect button available (Already connected or restricted profile)")

                    elif "/company/" in enlace.lower():
                        if counters["followed"] < MAX_FOLLOWS_PER_DAY:
                            script_empresa = """
                            var els = document.querySelectorAll("button, a");
                            for(var i=0; i<els.length; i++) {
                                var txt = (els[i].innerText || "").trim().toLowerCase();
                                if(txt === 'seguir' || txt === 'follow') {
                                    els[i].click(); return true;
                                }
                            } return false;
                            """
                            if self.driver.execute_script(script_empresa):
                                inc("followed")
                                self._log(f"Company successfully followed: {nombre}")

                    mark_as_processed(enlace)
                    procesados.add(enlace)

                except Exception as e:
                    inc("errors")
                    self._log(f"Error processing {nombre}: {e}")

                self._update_stats()
                self._pausa(8, 14)

            self._set_progress(self.prog1, 1.0, "Campaign finished.")
            self._log(f"Done! {counters['connections']} invitations sent.")

        except InterruptedError as e:
            self._log(f"⚠️ {e}")
            self._set_progress(self.prog1, 0, "Campaign stopped manually.")
        except Exception as e:
            self._log(f"Unexpected error: {e}")
        finally:
            self._set_modulo_buttons("normal")

    # ======================================================================
    # MODULE 2: JOB & RECRUITER FINDER
    # ======================================================================
    def _pre_run_mod2(self):
        keyword = self.e_m2_puesto.get().strip()
        if not keyword:
            self._log("Please type something to search (e.g. IT, Finance, Tech)"); return
        default_name = f"Job_Openings_{keyword.replace(' ', '_')}_Malta.csv"
        path = filedialog.asksaveasfilename(
            title="Save Job Results as...", initialfile=default_name,
            defaultextension=".csv", filetypes=[("CSV", "*.csv"), ("All Files", "*.*")])
        if not path:
            self._log("Cancelled."); return
        self.mod2_save_path = path
        self._lanzar_modulo(2)

    def _run_mod2(self):
        try:
            keyword = self.e_m2_puesto.get().strip()
            tipo_str = self.cb_m2_tipo.get()
            tiempo_str = self.cb_m2_tiempo.get()
            pag_str = self.e_m2_pags.get().strip()
            paginas = int(pag_str) if pag_str.isdigit() else 1

            f_wt = {"On-site": "&f_WT=1", "Hybrid": "&f_WT=3", "Remote": "&f_WT=2", "All": ""}.get(tipo_str, "")
            f_tpr = {"Last 24h": "&f_TPR=r86400", "Last week": "&f_TPR=r604800", "Any time": ""}.get(tiempo_str, "")

            kw_final = keyword if "malta" in keyword.lower() else f"{keyword} Malta"
            url_base = f"https://www.linkedin.com/jobs/search/?keywords={urllib.parse.quote(kw_final)}&sortBy=DD{f_wt}{f_tpr}"

            ofertas_data = {}
            self._log("STEP 1 — Scanning job list in Malta...")

            for pag in range(paginas):
                self._check_stop_pause()
                self.driver.get(f"{url_base}&start={pag * 25}")
                self._pausa(4, 6)
                self._detectar_captcha()
                self._check_stop_pause()

                try:
                    WebDriverWait(self.driver, 6).until(EC.presence_of_element_located((By.XPATH, "//*[@data-occludable-job-id]")))
                except:
                    self._log("No results found for these filters."); break

                for _ in range(10):
                    self._check_stop_pause()
                    self.driver.execute_script("""
                        var cards = document.querySelectorAll('li[data-occludable-job-id]');
                        if(cards.length > 0) {
                            cards[cards.length - 1].scrollIntoView({behavior: 'smooth', block: 'center'});
                        }
                    """)
                    self._pausa(1.5, 2.5)

                for t in self.driver.find_elements(By.XPATH, "//*[@data-occludable-job-id]"):
                    jid = (t.get_attribute("data-occludable-job-id") or "").strip()
                    if not jid or jid in ofertas_data: continue
                    t_tit = extract_safe_text(t, [".//strong", ".//h3", ".//a"])
                    lines = [l.strip() for l in t.text.split('\n') if l.strip()]
                    ofertas_data[jid] = {"titulo": t_tit, "empresa": lines[1] if len(lines) >= 2 else ""}

                self._set_progress(self.prog2, (pag + 1) / paginas, f"Scanning Page {pag + 1}/{paginas}")

            self._log(f"STEP 2 — Opening {len(ofertas_data)} job listings to extract details...")
            cabeceras = ["Job Title", "Company", "Location", "Work Model", "Time Posted", "Company Size", "Recruiter", "Recruiter Link", "Job URL"]
            vacantes = []

            for i, (job_id, data_card) in enumerate(ofertas_data.items()):
                self._check_stop_pause()
                self._set_progress(self.prog2, i / max(len(ofertas_data), 1), f"Analyzing {i + 1}/{len(ofertas_data)}")
                url_oferta = f"https://www.linkedin.com/jobs/view/{job_id}/"

                try:
                    self.driver.get(url_oferta)
                    self._pausa(3, 5)
                    self._detectar_captcha()
                    self._check_stop_pause()

                    js_deep = """
                    var data = {
                        titulo: "", empresa: "", ubicacion: "Not specified", modalidad: "Not specified", 
                        tiempo_publicado: "Not specified", tamano_empresa: "Not specified",
                        reclutador: "Not public", link_reclutador: "N/A", link_empresa: ""
                    };
                    
                    var h1 = document.querySelector("h1");
                    if(h1) data.titulo = h1.innerText.trim();
                    
                    var comp = document.querySelector(".job-details-jobs-unified-top-card__company-name");
                    if(comp) data.empresa = comp.innerText.replace(/with verification/gi, "").replace(/con verificación/gi, "").trim();
                    
                    var primDesc = document.querySelector(".job-details-jobs-unified-top-card__primary-description-container");
                    if(primDesc) {
                        var parts = primDesc.innerText.split("·").map(s => s.trim());
                        if(parts.length > 0) data.ubicacion = parts[0];
                        for(var i=1; i<parts.length; i++) {
                            var p = parts[i].toLowerCase();
                            if (p.includes("hace") || p.includes("ago") || p.includes("hour") || p.includes("minute") || p.includes("day") || p.includes("días") || p.includes("horas") || p.includes("semana") || p.includes("week")) {
                                data.tiempo_publicado = parts[i];
                            }
                        }
                    }
                    
                    var insights = document.querySelectorAll(".job-details-jobs-unified-top-card__job-insight, .tvm__text, li.job-details-jobs-unified-top-card__job-insight");
                    for(var el of insights) {
                        var txt = el.innerText.toLowerCase();
                        if(txt === "remoto" || txt === "remote" || txt === "híbrido" || txt === "hybrid" || txt === "presencial" || txt === "on-site" || txt === "in-person") {
                            data.modalidad = el.innerText.trim(); break;
                        } else if(txt.includes("remoto") || txt.includes("remote") || txt.includes("híbrido") || txt.includes("hybrid") || txt.includes("presencial") || txt.includes("on-site")) {
                            if (txt.length < 50 && data.modalidad === "Not specified") {
                                data.modalidad = el.innerText.trim().split("\\n")[0]; break;
                            }
                        }
                    }
                    if(data.modalidad === "Not specified" && data.titulo) {
                        var tLow = data.titulo.toLowerCase();
                        if(tLow.includes("remoto") || tLow.includes("remote")) data.modalidad = "Remote (in title)";
                        else if(tLow.includes("híbrido") || tLow.includes("hybrid")) data.modalidad = "Hybrid (in title)";
                    }

                    // Bilingual Universal Scanner for Company Size
                    var allEls = document.querySelectorAll("span, div, li");
                    for(var i=0; i<allEls.length; i++){
                        var t = allEls[i].innerText.toLowerCase();
                        // This accepts ANY format, even localized Spanish (e.g., "51 a 200 empleados") 
                        // as long as it has a digit and the target keyword.
                        if ((t.includes("empleado") || t.includes("employee") || t.includes("staff") || t.includes("trabajador")) && 
                            (/\\d/.test(t)) && 
                            t.length < 40) {
                            data.tamano_empresa = allEls[i].innerText.trim().replace(/\\n/g, ' '); 
                            break;
                        }
                    }
                    
                    var hirerCard = document.querySelector(".hirer-card__container") || document.querySelector(".jobs-poster");
                    if(hirerCard) {
                        var a = hirerCard.querySelector("a[href*='/in/']");
                        if(a) {
                            data.link_reclutador = a.href.split('?')[0];
                            var nameSpan = hirerCard.querySelector("strong") || hirerCard.querySelector("h3");
                            if(nameSpan) data.reclutador = nameSpan.innerText.trim();
                        }
                    } else {
                        var sections = document.querySelectorAll("section");
                        for(var s of sections) {
                            if((s.innerText||"").toLowerCase().includes("hiring team") || (s.innerText||"").toLowerCase().includes("equipo de contrataci")) {
                                var a = s.querySelector("a[href*='/in/']");
                                if(a) {
                                    data.link_reclutador = a.href.split('?')[0];
                                    var nameSpan = s.querySelector("strong");
                                    if(nameSpan) data.reclutador = nameSpan.innerText.trim();
                                    break;
                                }
                            }
                        }
                    }
                    
                    var compLink = document.querySelector(".job-details-jobs-unified-top-card__company-name a") || document.querySelector("a[href*='/company/']");
                    if (compLink) {
                        data.link_empresa = compLink.href.split('?')[0];
                    }
                    
                    return data;
                    """
                    deep_data = self.driver.execute_script(js_deep) or {}

                    titulo = deep_data.get("titulo") or data_card["titulo"] or "Not extracted"
                    empresa = deep_data.get("empresa")
                    if not empresa or empresa.lower() == titulo.lower():
                        empresa = data_card["empresa"] or "Confidential"
                    if empresa.lower() == titulo.lower(): empresa = "Confidential"

                    ubicacion = deep_data.get("ubicacion", "Not specified")
                    modalidad = deep_data.get("modalidad", "Not specified")
                    tiempo_publicado = deep_data.get("tiempo_publicado", "Not specified")
                    tamano_empresa = deep_data.get("tamano_empresa", "Not specified")

                    reclutador = deep_data.get("reclutador", "Not public")
                    reclutador_link = deep_data.get("link_reclutador", "N/A")
                    link_empresa = deep_data.get("link_empresa", "")

                    if reclutador == "Not public" and link_empresa:
                        reclutador_link = f"{link_empresa.rstrip('/')}/people/"
                        reclutador = "Search in company directory ➔"

                    vacantes.append([titulo, empresa, ubicacion, modalidad, tiempo_publicado, tamano_empresa, reclutador, reclutador_link, url_oferta])
                    log_empresa = empresa if empresa != "Confidential" else titulo[:30]
                    self._log(f"  {log_empresa} -> {modalidad} | {tamano_empresa}")

                except Exception as e:
                    inc("errors"); self._log(f"Error reading job {job_id}: {e}")

            self._set_progress(self.prog2, 1.0, "Scan complete.")
            if vacantes:
                ruta_final = save_to_csv(self.mod2_save_path, cabeceras, vacantes, "Job URL")
                if ruta_final:
                    self._log(f"Success! {len(vacantes)} job listings saved to: {os.path.basename(ruta_final)}")

        except InterruptedError as e:
            self._log(f"⚠️ {e}")
            self._set_progress(self.prog2, 0, "Scan stopped.")
            if 'vacantes' in locals() and vacantes:
                ruta_final = save_to_csv(self.mod2_save_path, cabeceras, vacantes, "Job URL")
                if ruta_final:
                    self._log(f"Saved {len(vacantes)} job listings collected so far.")
        except Exception as e:
            self._log(f"Unexpected error: {e}")
        finally:
            self._set_modulo_buttons("normal")

    # ======================================================================
    # MODULE 3: PROFILE PROSPECTOR
    # ======================================================================
    def _pre_run_mod3(self):
        keyword = self.e_m3_perfil.get().strip()
        if not keyword:
            self._log("Please type the job title you are looking for (e.g. Marketing Manager)."); return
        default_name = f"Leads_{keyword.replace(' ', '_')}_Malta.csv"
        path = filedialog.asksaveasfilename(
            title="Save Contact List as...", initialfile=default_name,
            defaultextension=".csv", filetypes=[("CSV", "*.csv"), ("All Files", "*.*")])
        if not path:
            self._log("Cancelled."); return
        self.mod3_save_path = path
        self._lanzar_modulo(3)

    def _run_mod3(self):
        try:
            keyword = self.e_m3_perfil.get().strip()
            pag_str = self.e_m3_pags.get().strip()
            paginas = max(1, min(5, int(pag_str) if pag_str.isdigit() else 2))
            leads = []; urls_batch = set()
            cabeceras = ["Name", "Job Title", "Current Company", "Profile URL"]

            for pag in range(1, paginas + 1):
                self._check_stop_pause()

                kw_final = keyword if "malta" in keyword.lower() else f"{keyword} Malta"
                url = (f"https://www.linkedin.com/search/results/people/?"
                       f"keywords={urllib.parse.quote(kw_final)}"
                       f"&page={pag}&origin=GLOBAL_SEARCH_HEADER")

                self._log(f"Malta | Page {pag}/{paginas}")
                self.driver.get(url)
                self._pausa(5, 8)
                self._detectar_captcha()
                self._check_stop_pause()

                try:
                    WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(
                        (By.XPATH, "//a[contains(@href,'/in/') and not(contains(@href,'miniProfile'))]")))
                except TimeoutException:
                    self._log(f"No results on page {pag}."); continue

                for paso in range(4):
                    self._check_stop_pause()
                    self.driver.execute_script(f"window.scrollTo(0,document.body.scrollHeight*{(paso + 1) / 4});")
                    self._pausa(1.5, 2.5)

                self._log("Reading profiles...")
                js_extractor = """
                var leads = []; var processedUrls = new Set(); var processedCards = new Set();
                var links = document.querySelectorAll("a[href*='/in/']");
                links.forEach(function(link) {
                    var href = link.href.split('?')[0].replace(/\\/+$/, '').toLowerCase();
                    if (!href.includes('/in/') || processedUrls.has(href) ||
                        href.includes('miniprofile') || href.includes('/search/') ||
                        href.includes('/company/') || href.includes('/in/linkedin')) return;
                    var card = null; var curr = link;
                    for (var i=0; i<10; i++) {
                        if (!curr.parentElement) break;
                        curr = curr.parentElement;
                        var tag = curr.tagName.toLowerCase();
                        var cls = (curr.className || "").toLowerCase();
                        if (tag === 'li' || cls.includes('result-container') ||
                            cls.includes('reusable-search') || curr.getAttribute('data-view-name')) {
                            card = curr; break;
                        }
                    }
                    if (!card || processedCards.has(card)) return;
                    processedUrls.add(href); processedCards.add(card);
                    var raw = card.innerText || "";
                    var nombre = "";
                    var nameSpan = card.querySelector("span[dir='ltr']");
                    if (nameSpan && nameSpan.innerText) { nombre = nameSpan.innerText.split('\\n')[0].trim(); }
                    if (!nombre) {
                        var img = card.querySelector("img[alt]");
                        if (img && img.alt && img.alt !== "LinkedIn Member" &&
                            img.alt !== "Miembro de LinkedIn" && img.alt.length > 2) {
                            nombre = img.alt.trim();
                        }
                    }
                    var js_empresa = "";
                    var insights = card.querySelectorAll(".entity-result__simple-insight-text");
                    if (insights.length > 0 && insights[0].innerText) {
                        js_empresa = insights[0].innerText.split('\\n')[0].trim();
                    }
                    leads.push({ url: href, nombre: nombre, raw: raw, js_empresa: js_empresa });
                });
                return leads;
                """
                raw_leads = self.driver.execute_script(js_extractor) or []
                self._log(f"  {len(raw_leads)} profiles found")

                for j, data in enumerate(raw_leads):
                    self._check_stop_pause()
                    self._set_progress(self.prog3, j / max(len(raw_leads), 1), f"Page {pag}: reading {j + 1}/{len(raw_leads)}")
                    url_perfil = data.get("url", "")
                    nombre_img = data.get("nombre", "")
                    raw_text = data.get("raw", "")
                    js_empresa = data.get("js_empresa", "")

                    if not url_perfil or "linkedin.com/in/" not in url_perfil: continue
                    url_norm = url_perfil.split('?')[0].rstrip("/").lower()
                    if url_norm in urls_batch: continue
                    urls_batch.add(url_norm)

                    lineas_raw = [l.strip() for l in raw_text.split('\n') if l.strip()]
                    result = parse_profile_block(nombre_img, lineas_raw, js_empresa)
                    if not result: continue

                    leads.append([result["name"], result["job_title"], result["current_company"], url_perfil])
                    self._log(f"  {result['name']}  /  {result['job_title'][:36]}")

                self._pausa(5, 9)

            self._set_progress(self.prog3, 1.0, "Search complete.")

            vistos = set(); leads_unicos = []
            for fila in leads:
                clave = fila[-1].split('?')[0].rstrip("/").lower()
                if clave not in vistos:
                    vistos.add(clave); leads_unicos.append(fila)

            dup = len(leads) - len(leads_unicos)
            if dup > 0: self._log(f"Duplicates removed: {dup}")

            if leads_unicos:
                ruta_final = save_to_csv(self.mod3_save_path, cabeceras, leads_unicos, "Profile URL")
                if ruta_final:
                    self._log(f"Done — {len(leads_unicos)} profiles saved to: {os.path.basename(ruta_final)}")
            else:
                self._log("No profiles were found for this search.")

        except InterruptedError as e:
            self._log(f"⚠️ {e}")
            self._set_progress(self.prog3, 0, "Search stopped.")
            if 'leads_unicos' not in locals():
                vistos = set(); leads_unicos = []
                for fila in leads:
                    clave = fila[-1].split('?')[0].rstrip("/").lower()
                    if clave not in vistos:
                        vistos.add(clave); leads_unicos.append(fila)
            if leads_unicos:
                ruta_final = save_to_csv(self.mod3_save_path, cabeceras, leads_unicos, "Profile URL")
                self._log(f"Saved {len(leads_unicos)} profiles collected so far.")
        except Exception as e:
            self._log(f"Unexpected error: {e}")
        finally:
            self._set_modulo_buttons("normal")

if __name__ == "__main__":
    app = AIntelligenceApp()
    app.mainloop()