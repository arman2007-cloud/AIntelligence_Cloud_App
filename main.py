"""
==============================================================================
AINTELLIGENCE ENTERPRISE SUITE v34.0 — CORE CONTROLLER (main.py)
==============================================================================
Arquitectura MVC & Concurrencia (Threading):
    Ejecutable principal. Construye la GUI y orquesta el Web-Scraping.
    100% alineado con la configuración por entorno (.env).
    (Modo Silencioso: Sin alertas sonoras).
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
import time, random, csv, os, json, urllib.parse, logging, sys, threading
from datetime import datetime

# === IMPORTACIONES DE NUESTRA ARQUITECTURA MODULAR ===
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
# CLASE PRINCIPAL: ESTADO GLOBAL Y RUTAS (ROUTING)
# ==============================================================================
class AIntelligenceApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("AIntelligence — Enterprise Suite")
        self.geometry("1340x860")
        self.minsize(1100, 760)
        self.configure(fg_color=BG)
        ctk.set_appearance_mode("dark")

        # Punteros de memoria y drivers
        self.driver = None
        self.bot_thread = None
        self.archivo_mod1_seleccionado = ""
        self.save_path_mod2 = ""
        self.save_path_mod3 = ""

        # Semáforos de concurrencia
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Pipeline Visual
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
    # VIEW BUILDERS (Constructor de Interfaz Gráfica)
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
                ctk.CTkLabel(logo_frame, image=ci, text="").pack(anchor="w")
                logo_ok = True
        except: pass
        if not logo_ok:
            ctk.CTkLabel(logo_frame, text="AIntelligence", font=("Calibri", 22, "bold"), text_color=TEXT).pack(anchor="w")
            ctk.CTkLabel(logo_frame, text="IT Consultancy — Malta", font=F_LABEL, text_color=CYAN).pack(anchor="w", pady=(2, 0))

        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).grid(row=1, column=0, sticky="ew", padx=28, pady=(0, 20))
        ctk.CTkLabel(self.sidebar, text="MÓDULOS OPERATIVOS", font=F_LABEL, text_color=TEXT_GHOST).grid(row=2, column=0, padx=32, sticky="w")

        nav_items = [
            ("home", "Conexión al Motor"),
            ("mod3", "Prospectar Leads"),
            ("mod1", "Bot Networking"),
            ("mod2", "Cazar Vacantes B2B"),
            ("tutorial", "Guía de Uso"),
        ]
        self._nav_btns = {}
        for r, (key, label) in enumerate(nav_items, start=3):
            btn = PillNavButton(self.sidebar, text=label, command=lambda k=key: self._show_frame(k))
            btn.grid(row=r, column=0, padx=20, pady=3, sticky="ew")
            self._nav_btns[key] = btn

        ctk.CTkFrame(self.sidebar, height=1, fg_color=BORDER).grid(row=8, column=0, sticky="ew", padx=28, pady=(8, 0))

        stats_outer = ctk.CTkFrame(self.sidebar, fg_color=CARD, corner_radius=16, border_width=1, border_color=BORDER)
        stats_outer.grid(row=9, column=0, padx=20, pady=24, sticky="sew")
        ctk.CTkLabel(stats_outer, text="RENDIMIENTO HOY", font=F_LABEL, text_color=TEXT_GHOST).pack(pady=(18, 12))
        stats_row = ctk.CTkFrame(stats_outer, fg_color="transparent")
        stats_row.pack(fill="x", padx=20, pady=(0, 12))
        stats_row.grid_columnconfigure((0, 1), weight=1)
        self._stat_labels = {}
        for col, (key, label, color) in enumerate([("conexiones", "Conectados", CYAN), ("seguidos", "Empresas", CORAL)]):
            sw = StatWidget(stats_row, label=label, color=color)
            sw.grid(row=0, column=col, padx=10, pady=5)
            self._stat_labels[key] = sw
        ctk.CTkFrame(stats_outer, height=1, fg_color=BORDER).pack(fill="x", padx=16, pady=(4, 12))

        self._dot_frame = ctk.CTkFrame(stats_outer, fg_color="transparent")
        self._dot_frame.pack(pady=(0, 18))
        self._dot = ctk.CTkFrame(self._dot_frame, width=8, height=8, corner_radius=4, fg_color=RED)
        self._dot.pack(side="left", padx=(0, 8))
        self.lbl_status = ctk.CTkLabel(self._dot_frame, text="Motor Apagado", font=F_UI_B, text_color=RED)
        self.lbl_status.pack(side="left")

    def _build_home(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["home"] = f
        f.grid_columnconfigure(0, weight=1)
        self._page_header(f, "🔌 Inicializar Sistema", "Conecta tu cuenta de LinkedIn para despertar el motor de automatización.")
        card = ctk.CTkFrame(f, fg_color=CARD, corner_radius=20, border_width=1, border_color=BORDER)
        card.grid(row=1, column=0, padx=60, pady=30, sticky="ew")
        card.grid_columnconfigure(0, weight=1)
        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.grid(row=0, column=0, padx=60, pady=50)
        ctk.CTkLabel(inner, text="Credenciales de Acceso", font=("Calibri", 20, "bold"), text_color=TEXT).pack(pady=(0, 25))
        form_width = 380
        ctk.CTkLabel(inner, text="CORREO ELECTRÓNICO", font=F_LABEL, text_color=TEXT_DIM).pack(anchor="w", padx=5, pady=(0, 5))
        self.e_email = PremiumInput(inner, width=form_width, placeholder_text="ejemplo@correo.com")
        self.e_email.pack(pady=(0, 20))
        ctk.CTkLabel(inner, text="CONTRASEÑA", font=F_LABEL, text_color=TEXT_DIM).pack(anchor="w", padx=5, pady=(0, 5))
        self.e_pass = PremiumInput(inner, width=form_width, placeholder_text="••••••••", show="*")
        self.e_pass.pack(pady=(0, 35))
        self.btn_arrancar = ctk.CTkButton(inner, text="Arrancar Motor 🚀", fg_color=CYAN, hover_color=CYAN_DIM, text_color="#000000", font=F_BTN, corner_radius=10, height=52, width=form_width, command=self._iniciar_navegador_thread)
        self.btn_arrancar.pack()
        note_frame = ctk.CTkFrame(inner, fg_color=BG, corner_radius=10, border_width=1, border_color=BORDER, width=form_width, height=60)
        note_frame.pack(pady=(25, 0))
        note_frame.pack_propagate(False)
        ctk.CTkLabel(note_frame, text="💡 Si LinkedIn pide un captcha o código PIN,\nresuélvelo manualmente en Chrome.", font=F_SUBTITLE, text_color=TEXT_DIM, justify="center").place(relx=0.5, rely=0.5, anchor="center")

    def _build_mod3(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["mod3"] = f
        f.grid_columnconfigure(0, weight=1)
        self._page_header(f, "🎯 Prospector de Leads", "Extrae candidatos de LinkedIn con ubicación en Malta.")
        card = AccentCard(f, accent_color=CYAN)
        card.grid(row=1, column=0, padx=60, pady=(8, 16), sticky="ew")
        content = card.inner
        self._section_label(content, "PARÁMETROS DE BÚSQUEDA", CYAN)
        g = ctk.CTkFrame(content, fg_color="transparent")
        g.pack(fill="x", pady=(10, 20))
        g.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkLabel(g, text="CARGO A BUSCAR", font=F_LABEL, text_color=TEXT_DIM).grid(row=0, column=0, padx=(0, 16), sticky="w")
        ctk.CTkLabel(g, text="PÁGINAS A RASPAR (1-5)", font=F_LABEL, text_color=TEXT_DIM).grid(row=0, column=1, sticky="w")
        self.e_m3_perfil = PremiumInput(g, placeholder_text="Ej: CTO, Software Engineer")
        self.e_m3_perfil.grid(row=1, column=0, padx=(0, 16), pady=(6, 0), sticky="ew")
        self.e_m3_pags = PremiumInput(g, placeholder_text="Ej: 2")
        self.e_m3_pags.grid(row=1, column=1, pady=(6, 0), sticky="ew")
        self._section_label(content, "FORMATO DE SALIDA", TEXT_DIM)
        fmt = ctk.CTkFrame(content, fg_color=BG, corner_radius=10, border_width=1, border_color=BORDER)
        fmt.pack(fill="x", pady=(8, 24))
        ctk.CTkLabel(fmt, text="Nombre   /   Cargo   /   Empresa_Actual   /   URL_Perfil", font=F_MON, text_color=CYAN).pack(padx=20, pady=12)
        self._section_label(content, "PROGRESO", TEXT_DIM)
        self.prog3 = GlowProgressBar(content, color=CYAN)
        self.prog3.pack(fill="x", pady=(8, 24))
        self.container_btn3 = ctk.CTkFrame(content, fg_color="transparent")
        self.container_btn3.pack(fill="x", pady=(4, 8))
        self.btn_start3 = ctk.CTkButton(self.container_btn3, text="Generar Base de Datos ⚡", fg_color=CYAN, hover_color=CYAN_DIM, text_color="#000", font=F_BTN, corner_radius=10, height=52, command=self._pre_run_mod3)
        self.btn_start3.pack(fill="x")
        self.ctrl_frame3 = ctk.CTkFrame(self.container_btn3, fg_color="transparent")
        self.btn_pause3 = ctk.CTkButton(self.ctrl_frame3, text="⏸ Pausar", fg_color=AMBER, hover_color="#e6a13c", text_color="#000", font=F_BTN, corner_radius=10, height=52, command=self._toggle_pause)
        self.btn_pause3.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.btn_stop3 = ctk.CTkButton(self.ctrl_frame3, text="⏹ Detener", fg_color=RED, hover_color="#cc2d4a", text_color="#fff", font=F_BTN, corner_radius=10, height=52, command=self._stop_task)
        self.btn_stop3.pack(side="left", fill="x", expand=True, padx=(6, 0))

    def _build_mod1(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["mod1"] = f
        f.grid_columnconfigure(0, weight=1)
        self._page_header(f, "🤖 Bot de Networking", "Automatiza invitaciones de conexión usando los CSV generados.")
        card = AccentCard(f, accent_color=EMERALD)
        card.grid(row=1, column=0, padx=60, pady=(8, 16), sticky="ew")
        content = card.inner
        self._section_label(content, "ARCHIVO CSV A PROCESAR", EMERALD)
        file_frame = ctk.CTkFrame(content, fg_color=BG, corner_radius=10, border_width=1, border_color=BORDER)
        file_frame.pack(fill="x", pady=(8, 28))
        file_frame.grid_columnconfigure(0, weight=1)
        self.lbl_archivo_mod1 = ctk.CTkLabel(file_frame, text="Ningún archivo seleccionado...", font=F_MON, text_color=TEXT_DIM, anchor="w")
        self.lbl_archivo_mod1.grid(row=0, column=0, padx=20, pady=16, sticky="w")
        btn_sel = ctk.CTkButton(file_frame, text="Seleccionar CSV", width=160, height=36, fg_color=CARD, hover_color=BORDER, border_width=1, border_color=BORDER_LT, font=F_UI_B, text_color=TEXT, corner_radius=8, command=self._seleccionar_archivo)
        btn_sel.grid(row=0, column=1, padx=16, pady=12)
        self._section_label(content, "PROGRESO DE CAMPAÑA", TEXT_DIM)
        self.prog1 = GlowProgressBar(content, color=EMERALD)
        self.prog1.pack(fill="x", pady=(8, 24))
        self.container_btn1 = ctk.CTkFrame(content, fg_color="transparent")
        self.container_btn1.pack(fill="x", pady=(4, 8))
        self.btn_start1 = ctk.CTkButton(self.container_btn1, text="Iniciar Automatización ⚡", fg_color=EMERALD, hover_color="#009970", text_color="#000", font=F_BTN, corner_radius=10, height=52, command=lambda: self._lanzar_modulo(1))
        self.btn_start1.pack(fill="x")
        self.ctrl_frame1 = ctk.CTkFrame(self.container_btn1, fg_color="transparent")
        self.btn_pause1 = ctk.CTkButton(self.ctrl_frame1, text="⏸ Pausar", fg_color=AMBER, hover_color="#e6a13c", text_color="#000", font=F_BTN, corner_radius=10, height=52, command=self._toggle_pause)
        self.btn_pause1.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.btn_stop1 = ctk.CTkButton(self.ctrl_frame1, text="⏹ Detener", fg_color=RED, hover_color="#cc2d4a", text_color="#fff", font=F_BTN, corner_radius=10, height=52, command=self._stop_task)
        self.btn_stop1.pack(side="left", fill="x", expand=True, padx=(6, 0))

    def _seleccionar_archivo(self):
        """Abre el explorador de archivos para cargar el CSV."""
        ruta = filedialog.askopenfilename(title="Selecciona tu archivo de Leads (CSV)", filetypes=[("Archivos CSV", "*.csv"), ("Todos los archivos", "*.*")])
        if ruta:
            self.archivo_mod1_seleccionado = ruta
            nombre = os.path.basename(ruta)
            self.lbl_archivo_mod1.configure(text=nombre, text_color=EMERALD)
            self._log(f"Archivo cargado: {nombre}")

    def _build_mod2(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["mod2"] = f
        f.grid_columnconfigure(0, weight=1)
        self._page_header(f, "🏢 Cazador de Vacantes B2B", "Extrae empresas que contratan, modalidad, volumen y Hiring Manager.")
        card = AccentCard(f, accent_color=CORAL)
        card.grid(row=1, column=0, padx=60, pady=(8, 16), sticky="ew")
        content = card.inner
        self._section_label(content, "FILTROS DE BÚSQUEDA", CORAL)
        g = ctk.CTkFrame(content, fg_color="transparent")
        g.pack(fill="x", pady=(10, 20))
        g.grid_columnconfigure((0, 1, 2, 3), weight=1)
        defs2 = [
            ("PALABRA CLAVE", "e_m2_puesto", PremiumInput, {"placeholder_text": "Ej: IT, Tech"}),
            ("MODALIDAD", "cb_m2_tipo", PremiumCombo, {"values": ["Todos", "Presencial", "Híbrido", "Remoto"]}),
            ("ANTIGÜEDAD", "cb_m2_tiempo", PremiumCombo, {"values": ["Cualquiera", "Últimas 24h", "Última semana"]}),
            ("PÁGINAS (x25)", "e_m2_pags", PremiumInput, {"placeholder_text": "Ej: 2"}),
        ]
        for col, (lbl, attr, Cls, kw) in enumerate(defs2):
            ctk.CTkLabel(g, text=lbl, font=F_LABEL, text_color=TEXT_DIM).grid(row=0, column=col, padx=12, sticky="w")
            widget = Cls(g, **kw)
            widget.grid(row=1, column=col, padx=12, pady=(6, 0), sticky="ew")
            setattr(self, attr, widget)
        self._section_label(content, "PROGRESO DE EXTRACCIÓN", TEXT_DIM)
        self.prog2 = GlowProgressBar(content, color=CORAL)
        self.prog2.pack(fill="x", pady=(8, 24))
        self.container_btn2 = ctk.CTkFrame(content, fg_color="transparent")
        self.container_btn2.pack(fill="x", pady=(4, 8))
        self.btn_start2 = ctk.CTkButton(self.container_btn2, text="Escanear Mercado ⚡", fg_color=CORAL, hover_color=CORAL_DIM, text_color="#fff", font=F_BTN, corner_radius=10, height=52, command=self._pre_run_mod2)
        self.btn_start2.pack(fill="x")
        self.ctrl_frame2 = ctk.CTkFrame(self.container_btn2, fg_color="transparent")
        self.btn_pause2 = ctk.CTkButton(self.ctrl_frame2, text="⏸ Pausar", fg_color=AMBER, hover_color="#e6a13c", text_color="#000", font=F_BTN, corner_radius=10, height=52, command=self._toggle_pause)
        self.btn_pause2.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self.btn_stop2 = ctk.CTkButton(self.ctrl_frame2, text="⏹ Detener", fg_color=RED, hover_color="#cc2d4a", text_color="#fff", font=F_BTN, corner_radius=10, height=52, command=self._stop_task)
        self.btn_stop2.pack(side="left", fill="x", expand=True, padx=(6, 0))

    def _build_tutorial(self):
        f = ctk.CTkFrame(self.content, fg_color="transparent")
        self.frames["tutorial"] = f
        f.grid_columnconfigure(0, weight=1)
        self._page_header(f, "📖 Guía de Uso", "Aprende a dominar la herramienta en cuatro pasos sencillos.")
        sf = ctk.CTkScrollableFrame(f, fg_color=CARD, corner_radius=20, border_width=1, border_color=BORDER)
        sf.grid(row=1, column=0, padx=60, pady=20, sticky="nsew")
        f.grid_rowconfigure(1, weight=1)
        pasos = [
            ("Paso 1 — Conexión y Motor", CYAN, "Ve a la primera pestaña, introduce tu correo y contraseña de LinkedIn y pulsa Arrancar Motor. Se abrirá una ventana de Chrome gestionada por el bot. Si LinkedIn pide un puzzle de seguridad o un código de verificación, resuélvelo manualmente en esa ventana. Cuando termines, el panel lateral dirá Motor En Línea."),
            ("Paso 2 — Prospectar Leads", CYAN, "Escribe el puesto que buscas en Malta (Ej: Software Engineer, Marketing Manager) y cuántas páginas quieres escanear (máximo 5). El bot navegará automáticamente, extraerá los perfiles y guardará un archivo CSV en la carpeta que tú elijas con Nombre, Cargo y Empresa."),
            ("Paso 3 — Bot Networking", EMERALD, "Ve a esta pestaña y pulsa Seleccionar CSV. Elige el archivo que generaste en el paso anterior. Al darle a Iniciar, el bot leerá tu lista e invitará a conectar a cada persona, haciendo pausas aleatorias e inteligentes para parecer humano y proteger tu cuenta."),
            ("Paso 4 — Cazar Vacantes B2B", CORAL, "Si prefieres buscar empresas que estén contratando ahora mismo, usa esta opción. Escribe un sector (Ej: IT, Finance) y el bot rastreará las ofertas de empleo de Malta, extrayendo la ubicación, modalidad y buscando los perfiles del equipo de Recursos Humanos (Hiring Manager)."),
        ]
        for titulo, color, texto in pasos:
            h = ctk.CTkFrame(sf, fg_color="transparent")
            h.pack(fill="x", padx=30, pady=(30, 0))
            h.grid_columnconfigure(1, weight=1)
            pill = ctk.CTkFrame(h, width=6, height=24, corner_radius=3, fg_color=color)
            pill.grid(row=0, column=0, padx=(0, 14), sticky="ns")
            ctk.CTkLabel(h, text=titulo, font=("Calibri", 16, "bold"), text_color=color).grid(row=0, column=1, sticky="w")
            ctk.CTkFrame(sf, height=1, fg_color=BORDER).pack(fill="x", padx=30, pady=(8, 12))
            ctk.CTkLabel(sf, text=texto, font=F_UI, text_color=TEXT, justify="left", wraplength=820, anchor="w").pack(fill="x", padx=44, pady=(0, 12))

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
        ctk.CTkLabel(hdr, text="TERMINAL DE EVENTOS", font=F_LABEL, text_color=TEXT_DIM).grid(row=0, column=1, sticky="w", padx=8)
        live_frame = ctk.CTkFrame(hdr, fg_color="transparent")
        live_frame.grid(row=0, column=2, padx=20, sticky="e")
        ctk.CTkFrame(live_frame, width=8, height=8, corner_radius=4, fg_color=EMERALD).pack(side="left", padx=(0, 6), pady=14)
        ctk.CTkLabel(live_frame, text="LIVE", font=F_LABEL, text_color=EMERALD).pack(side="left")

        # Interfaz de Log Virtual en solo lectura
        self.console = ctk.CTkTextbox(co, fg_color="#050508", text_color=EMERALD, font=F_MON, corner_radius=0, border_width=0, wrap="word")
        self.console.grid(row=1, column=0, sticky="nsew")

    # ----------------------------------------------------------------------
    # MÉTODOS AUXILIARES DE RENDERIZADO UI
    # ----------------------------------------------------------------------
    def _page_header(self, parent, title, subtitle):
        """Pinta los encabezados de página consistentes."""
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
        """Inyecta el texto a la terminal forzando la actualización en el Thread Principal."""
        def _do():
            self.console.insert(ctk.END, f"[{datetime.now().strftime('%H:%M:%S')}]  {msg}\n")
            self.console.see(ctk.END) # Auto-scroll hacia abajo
        self.after(0, _do)

    def _update_stats(self):
        def _do():
            for key, sw in self._stat_labels.items():
                sw.set_value(contadores[key])
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
        """Secuestra la consola de Python para mostrarla en la interfaz."""
        app = self
        class GUIHandler(logging.Handler):
            def emit(self, record): app._log(self.format(record))
        h = GUIHandler()
        h.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(h)

    def _show_frame(self, key):
        """Enrutador interno (Router) entre las pestañas del menú."""
        if key in ("mod1", "mod2", "mod3") and not self.driver:
            self._log("Debes arrancar el motor desde la primera pestaña primero.")
            key = "home"
        if key in ("mod1", "mod2", "mod3") and self.driver:
            url = self.driver.current_url
            if "login" in url or "authwall" in url:
                self._log("Sesión de LinkedIn expirada. Vuelve a Inicio.")
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
        """Destructor: Cierra la instancia de Chrome en RAM al salir."""
        if self.driver:
            try: self.driver.quit()
            except: pass
        self.destroy()

    # ----------------------------------------------------------------------
    # CONTROL DE CONCURRENCIA
    # ----------------------------------------------------------------------
    def _toggle_pause(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self._log("⏸ Tarea pausada. Pulsa Reanudar para continuar.")
            for btn in [self.btn_pause1, self.btn_pause2, self.btn_pause3]:
                btn.configure(text="▶ Reanudar", fg_color=EMERALD, hover_color="#009970")
        else:
            self.pause_event.set()
            self._log("▶ Tarea reanudada.")
            for btn in [self.btn_pause1, self.btn_pause2, self.btn_pause3]:
                btn.configure(text="⏸ Pausar", fg_color=AMBER, hover_color="#e6a13c")

    def _stop_task(self):
        self._log("⏹ Cancelando tarea... (El bot parará en cuanto acabe su acción actual)")
        self.stop_event.set()
        self.pause_event.set()

    def _check_stop_pause(self):
        if self.stop_event.is_set(): raise InterruptedError("Operación cancelada por el usuario.")
        self.pause_event.wait()

    def _pausa(self, a=8, b=14):
        """Pausa inteligente: divide la espera en fracciones para no bloquear el botón Pausa."""
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
        url = self.driver.current_url
        if any(x in url for x in ["captcha", "checkpoint", "challenge", "authwall"]):
            self._log("🔒 VERIFICACIÓN DE LINKEDIN DETECTADA")
            self._log("👉 Por favor, resuelve el Captcha/PIN en la ventana de Chrome.")
            self._log("   (El sistema se reanudará automáticamente cuando termines).")
            while any(x in self.driver.current_url for x in ["captcha", "checkpoint", "challenge", "authwall"]):
                self._check_stop_pause()
                time.sleep(2)
            self._log("✅ Verificación superada. Retomando automatización...")
            time.sleep(2)
            return True
        return False

    # ----------------------------------------------------------------------
    # INYECCIÓN DEL NAVEGADOR
    # ----------------------------------------------------------------------
    def _iniciar_navegador_thread(self):
        self.btn_arrancar.configure(state="disabled")
        self._log("Arrancando Chrome invisible...")
        threading.Thread(target=self._proceso_login, daemon=True).start()

    def _proceso_login(self):
        email = self.e_email.get().strip()
        password = self.e_pass.get().strip()
        try:
            opts = uc.ChromeOptions()
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_argument("--lang=es-ES")
            self.driver = uc.Chrome(options=opts, version_main=145)
            self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"})

            if os.path.isfile(ARCHIVO_COOKIES):
                with open(ARCHIVO_COOKIES, "r", encoding="utf-8") as f: cookies = json.load(f)
                self.driver.get("https://www.linkedin.com")
                pausa_aleatoria(2, 4)
                for ck in cookies:
                    try: self.driver.add_cookie(ck)
                    except: pass
                self.driver.refresh()
                pausa_aleatoria(4, 6)

                if "feed" in self.driver.current_url or "mynetwork" in self.driver.current_url:
                    self._log("Sesión restaurada correctamente. Motor listo.")
                    self._set_session_status("Motor En Línea", EMERALD)
                    self._encoger_ventana()
                    return
                else:
                    self._log("⚠️ Las cookies guardadas han caducado o pertenecen a otra cuenta.")
                    self._log("🧹 Limpiando sesión antigua...")
                    self.driver.delete_all_cookies()
                    try: os.remove(ARCHIVO_COOKIES)
                    except: pass
                    pausa_aleatoria(2, 3)

            self.driver.get("https://www.linkedin.com/login")
            pausa_aleatoria(2, 4)

            if email and password:
                self._log("Inyectando credenciales a nivel de código (Deep JS)...")
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
                    if exito: self._log("Credenciales inyectadas correctamente. Comprobando...")
                    else: self._log("No se encontraron los campos. Inicia sesión manualmente.")
                except Exception: self._log("Error al autocompletar. Inicia sesión manualmente.")
            else:
                self._log("Inicia sesión manualmente en la ventana de Chrome.")

            self._log("Esperando validación de LinkedIn...")
            intentos = 0
            while True:
                url = self.driver.current_url
                if any(x in url for x in ["feed", "mynetwork", "search", "in/"]): break
                if intentos > 60:
                    self._log("Sigo esperando... Asegúrate de resolver cualquier captcha.")
                    intentos = 0
                pausa_aleatoria(1.5, 2.5)
                intentos += 1

            cookies = self.driver.get_cookies()
            with open(ARCHIVO_COOKIES, "w", encoding="utf-8") as f: json.dump(cookies, f)
            self._log("Sesión guardada. Motor listo.")
            self._set_session_status("Motor En Línea", EMERALD)
            self._encoger_ventana()

        except Exception as e:
            self._log(f"Error al iniciar Chrome: {e}")
            self.after(0, lambda: self.btn_arrancar.configure(state="normal"))

    def _encoger_ventana(self):
        try:
            self.driver.set_window_position(0, 0)
            self.driver.set_window_size(600, 600)
            self._log("💡 Chrome se ha apartado a un lado para que puedas trabajar libremente.")
        except: pass

    # ----------------------------------------------------------------------
    # ORQUESTADOR DE MÓDULOS DE NEGOCIO
    # ----------------------------------------------------------------------
    def _lanzar_modulo(self, num):
        if self.bot_thread and self.bot_thread.is_alive():
            self._log("Ya hay una tarea en curso. Por favor, espera.")
            return
        self.stop_event.clear()
        self.pause_event.set()
        for btn in [self.btn_pause1, self.btn_pause2, self.btn_pause3]:
            btn.configure(text="⏸ Pausar", fg_color=AMBER, hover_color="#e6a13c")
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
        if not element: raise Exception("Elemento nulo.")
        try:
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center', inline:'center'});", element)
            time.sleep(0.5)
        except: pass

        try:
            self.driver.execute_script("arguments[0].focus();", element)
            time.sleep(0.2)
            element.send_keys(Keys.ENTER)
            if log_method: log_method("  [Engine] Focus+Enter (trusted) ejecutado.")
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
            raise Exception(f"Fallo absoluto de interacción: {e}")

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
                    self._log("  ✔ Invitación enviada instantáneamente (Sin modal).")
                    return True
                self._log(f"  ℹ️ Esperando aparición del modal (intento {intento_modal + 1})")
                time.sleep(1)
                continue

            html = modal_state.get("html", "")

            es_friccion = any(x in html for x in [
                "cómo conoces", "how do you know", "te invitamos a conectar",
                "invited to connect", "¿cómo conociste"
            ])

            if es_friccion:
                self._log("  🛡️ Modal de fricción (Shadow DOM) → seleccionando 'Otro'...")
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
                        self._log("  ✔ Fricción superada → botón primario pulsado")
                        time.sleep(2)
                        continue
                self._log("  ❌ No se pudo superar la fricción en Shadow DOM.")

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
                    self._log("  ✔ Enviado sin nota (Shadow DOM)")
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
                    self._log("  ✔ Confirmación enviada (Shadow DOM genérico)")
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
                    self._log("  ✔ Omitida la nota (Shadow DOM)")
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
                            self._log("  ⚠️ Backend Rejection: LinkedIn revirtió el botón a 'Conectar'.")
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
    # MÓDULO 1: BOT DE NETWORKING AUTOMATIZADO
    # ======================================================================
    def _run_mod1(self):
        archivo = self.archivo_mod1_seleccionado
        if not archivo or not os.path.isfile(archivo):
            self._log("Error: Debes seleccionar un archivo CSV válido.")
            self._set_modulo_buttons("normal"); return

        self._log(f"Bot Networking — {os.path.basename(archivo)}")
        procesados = cargar_procesados()
        filas = []

        # Auto-Encoding Shield contra la corrupción de Excel
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
                            nom = row.get(nom_col, "Usuario").strip() if nom_col else "Usuario"
                            if url.startswith("http") and url not in procesados:
                                filas.append((url, nom))
                lectura_exitosa = True
                break
            except UnicodeDecodeError:
                continue
            except Exception as e:
                self._log(f"Error inesperado al leer CSV: {e}")
                self._set_modulo_buttons("normal"); return

        if not lectura_exitosa:
            self._log("Error de codificación en el archivo CSV. Ábrelo con Excel y dale a Guardar como 'CSV UTF-8'.")
            self._set_modulo_buttons("normal"); return

        total = len(filas)
        if total == 0:
            self._log("CSV vacío o todos ya procesados.")
            self._set_modulo_buttons("normal"); return

        self._log(f"{total} perfiles nuevos en cola.")

        try:
            for i, (enlace, nombre) in enumerate(filas, 1):
                self._check_stop_pause()
                self._set_progress(self.prog1, i / max(total, 1), f"[{i}/{total}]  {nombre[:35]}")

                # Rate-Limiting: Evitamos un ban utilizando tu constante de config.py (.env)
                if contadores["conexiones"] >= MAX_CONEXIONES_DIA:
                    self._log("Límite diario alcanzado. Deteniendo para proteger la cuenta.")
                    break

                self.driver.get(enlace)
                self._pausa(4, 7)
                self._detectar_captcha()
                self._check_stop_pause()

                try:
                    if "/in/" in enlace.lower():
                        self._log(f"  → Navegando a perfil de {nombre}...")
                        self._esperar_zona_acciones()
                        self._check_stop_pause()

                        btn_connect = self._localizar_elemento_por_js('conectar')
                        clicked = False

                        if btn_connect:
                            self._log("  ✔ Botón Conectar localizado directamente")
                            try:
                                self._click_natively(btn_connect, self._log)
                                clicked = True
                            except Exception as e_click:
                                self._log(f"  ⚠️ Error en clic directo: {e_click}")
                        else:
                            self._log("  ℹ️ Botón directo no visible → probando 'Más opciones'...")
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
                                inc("conexiones")
                                self._log(f"  ✅ Invitación confirmada → {nombre}")
                            else:
                                exito_tardio = self._verificar_envio_exitoso()
                                if exito_tardio:
                                    inc("conexiones")
                                    self._log(f"  ✅ Invitación confirmada (tardía) → {nombre}")
                                else:
                                    self._log(f"  ⚠️ No se pudo confirmar el envío para: {nombre}")
                        else:
                            self._log(f"  ⛔ Sin botón Conectar disponible: {nombre} (ya conectados o perfil restringido)")

                    elif "/company/" in enlace.lower():
                        if contadores["seguidos"] < MAX_SEGUIR_DIA:
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
                                inc("seguidos")
                                self._log(f"Empresa seguida: {nombre}")

                    marcar_como_procesado(enlace)
                    procesados.add(enlace)

                except Exception as e:
                    inc("errores")
                    self._log(f"Error estructural con {nombre}: {e}")

                self._update_stats()
                self._pausa(8, 14)

            self._set_progress(self.prog1, 1.0, "Campaña finalizada.")
            self._log(f"Módulo 1 completado — {contadores['conexiones']} invitaciones enviadas.")

        except InterruptedError as e:
            self._log(f"⚠️ {e}")
            self._set_progress(self.prog1, 0, "Campaña detenida.")
        except Exception as e:
            self._log(f"Error inesperado: {e}")
        finally:
            self._set_modulo_buttons("normal")

    # ======================================================================
    # MÓDULO 2: CAZADOR DE VACANTES B2B Y RECLUTADORES
    # ======================================================================
    def _pre_run_mod2(self):
        keyword = self.e_m2_puesto.get().strip()
        if not keyword:
            self._log("Escribe un sector (Ej: IT, Tech, Software)"); return
        default_name = f"Vacantes_{keyword.replace(' ', '_')}_Malta.csv"
        path = filedialog.asksaveasfilename(
            title="Guardar Vacantes como...", initialfile=default_name,
            defaultextension=".csv", filetypes=[("CSV", "*.csv"), ("Todos", "*.*")])
        if not path:
            self._log("Operación cancelada."); return
        self.save_path_mod2 = path
        self._lanzar_modulo(2)

    def _run_mod2(self):
        try:
            keyword = self.e_m2_puesto.get().strip()
            tipo_str = self.cb_m2_tipo.get()
            tiempo_str = self.cb_m2_tiempo.get()
            pag_str = self.e_m2_pags.get().strip()
            paginas = int(pag_str) if pag_str.isdigit() else 1

            f_wt = {"Presencial": "&f_WT=1", "Híbrido": "&f_WT=3", "Remoto": "&f_WT=2", "Todos": ""}.get(tipo_str, "")
            f_tpr = {"Últimas 24h": "&f_TPR=r86400", "Última semana": "&f_TPR=r604800", "Cualquiera": ""}.get(tiempo_str, "")

            url_base = f"https://www.linkedin.com/jobs/search/?keywords={urllib.parse.quote(keyword)}&location=Malta&geoId=100768673"
            if tipo_str != "Remoto": url_base += "&distance=0"
            url_base += f"&sortBy=DD{f_wt}{f_tpr}"

            ofertas_data = {}
            self._log("FASE 1 — Escaneando ofertas de empleo en Malta...")

            for pag in range(paginas):
                self._check_stop_pause()
                self.driver.get(f"{url_base}&start={pag * 25}")
                self._pausa(4, 6)
                self._detectar_captcha()
                self._check_stop_pause()

                try:
                    WebDriverWait(self.driver, 6).until(EC.presence_of_element_located((By.XPATH, "//*[@data-occludable-job-id]")))
                except:
                    self._log("Sin resultados para estos filtros."); break

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
                    t_tit = extraer_texto_seguro(t, [".//strong", ".//h3", ".//a"])
                    lines = [l.strip() for l in t.text.split('\n') if l.strip()]
                    ofertas_data[jid] = {"titulo": t_tit, "empresa": lines[1] if len(lines) >= 2 else ""}

                self._set_progress(self.prog2, (pag + 1) / paginas, f"Escaneando Pág {pag + 1}/{paginas}")

            self._log(f"FASE 2 — Extracción Profunda de {len(ofertas_data)} ofertas...")
            cabeceras = ["Titulo", "Empresa", "Ubicacion", "Modalidad", "Tiempo_Publicado", "Tamano_Empresa", "Reclutador", "Link_Reclutador", "URL_Oferta"]
            vacantes = []

            for i, (job_id, data_card) in enumerate(ofertas_data.items()):
                self._check_stop_pause()
                self._set_progress(self.prog2, i / max(len(ofertas_data), 1), f"Analizando {i + 1}/{len(ofertas_data)}")
                url_oferta = f"https://www.linkedin.com/jobs/view/{job_id}/"

                try:
                    self.driver.get(url_oferta)
                    self._pausa(3, 5)
                    self._detectar_captcha()
                    self._check_stop_pause()

                    js_deep = """
                    var data = {
                        titulo: "", empresa: "", ubicacion: "No especificada", modalidad: "No especificada", 
                        tiempo_publicado: "No especificado", tamano_empresa: "No especificado",
                        reclutador: "No público", link_reclutador: "N/A", link_empresa: ""
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
                    
                    var allEls = document.querySelectorAll("span, div, li");
                    
                    var insights = document.querySelectorAll(".job-details-jobs-unified-top-card__job-insight, .tvm__text, li.job-details-jobs-unified-top-card__job-insight");
                    for(var el of insights) {
                        var txt = el.innerText.toLowerCase();
                        if(txt === "remoto" || txt === "remote" || txt === "híbrido" || txt === "hybrid" || txt === "presencial" || txt === "on-site" || txt === "in-person") {
                            data.modalidad = el.innerText.trim(); break;
                        } else if(txt.includes("remoto") || txt.includes("remote") || txt.includes("híbrido") || txt.includes("hybrid") || txt.includes("presencial") || txt.includes("on-site")) {
                            if (txt.length < 50 && data.modalidad === "No especificada") {
                                data.modalidad = el.innerText.trim().split("\\n")[0]; break;
                            }
                        }
                    }
                    if(data.modalidad === "No especificada" && data.titulo) {
                        var tLow = data.titulo.toLowerCase();
                        if(tLow.includes("remoto") || tLow.includes("remote")) data.modalidad = "Remoto (en título)";
                        else if(tLow.includes("híbrido") || tLow.includes("hybrid")) data.modalidad = "Híbrido (en título)";
                    }

                    for(var i=0; i<allEls.length; i++){
                        var t = allEls[i].innerText.toLowerCase();
                        if ((t.includes("empleado") || t.includes("employee") || t.includes("staff")) && (/\\d/.test(t)) && t.length < 30 && (t.includes("-") || t.includes("+") || t.includes(","))) {
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

                    titulo = deep_data.get("titulo") or data_card["titulo"] or "No extraído"
                    empresa = deep_data.get("empresa")
                    if not empresa or empresa.lower() == titulo.lower():
                        empresa = data_card["empresa"] or "Confidencial"
                    if empresa.lower() == titulo.lower(): empresa = "Confidencial"

                    ubicacion = deep_data.get("ubicacion", "No especificada")
                    modalidad = deep_data.get("modalidad", "No especificada")
                    tiempo_publicado = deep_data.get("tiempo_publicado", "No especificado")
                    tamano_empresa = deep_data.get("tamano_empresa", "No especificado")

                    reclutador = deep_data.get("reclutador", "No público")
                    reclutador_link = deep_data.get("link_reclutador", "N/A")
                    link_empresa = deep_data.get("link_empresa", "")

                    if reclutador == "No público" and link_empresa:
                        reclutador_link = f"{link_empresa.rstrip('/')}/people/"
                        reclutador = "Buscar en empresa ➔"

                    vacantes.append([titulo, empresa, ubicacion, modalidad, tiempo_publicado, tamano_empresa, reclutador, reclutador_link, url_oferta])
                    log_empresa = empresa if empresa != "Confidencial" else titulo[:30]
                    self._log(f"  {log_empresa} -> {modalidad} | {tamano_empresa}")

                except Exception as e:
                    inc("errores"); self._log(f"Error en oferta {job_id}: {e}")

            self._set_progress(self.prog2, 1.0, "Extracción completada.")
            if vacantes:
                ruta_final = guardar_en_csv(self.save_path_mod2, cabeceras, vacantes, "URL_Oferta")
                if ruta_final:
                    self._log(f"¡Éxito! {len(vacantes)} vacantes exportadas en: {os.path.basename(ruta_final)}")

        except InterruptedError as e:
            self._log(f"⚠️ {e}")
            self._set_progress(self.prog2, 0, "Extracción detenida.")
            if 'vacantes' in locals() and vacantes:
                ruta_final = guardar_en_csv(self.save_path_mod2, cabeceras, vacantes, "URL_Oferta")
                if ruta_final:
                    self._log(f"Se guardaron {len(vacantes)} vacantes extraídas hasta el momento.")
        except Exception as e:
            self._log(f"Error inesperado: {e}")
        finally:
            self._set_modulo_buttons("normal")

    # ======================================================================
    # MÓDULO 3: PROSPECTOR SEMÁNTICO DE PERFILES (LEAD GENERATION)
    # ======================================================================
    def _pre_run_mod3(self):
        keyword = self.e_m3_perfil.get().strip()
        if not keyword:
            self._log("Escribe qué perfil buscas (Ej: Marketing Manager)."); return
        default_name = f"Leads_{keyword.replace(' ', '_')}_Malta.csv"
        path = filedialog.asksaveasfilename(
            title="Guardar Base de Datos como...", initialfile=default_name,
            defaultextension=".csv", filetypes=[("CSV", "*.csv"), ("Todos", "*.*")])
        if not path:
            self._log("Operación cancelada."); return
        self.save_path_mod3 = path
        self._lanzar_modulo(3)

    def _run_mod3(self):
        try:
            keyword = self.e_m3_perfil.get().strip()
            pag_str = self.e_m3_pags.get().strip()
            paginas = max(1, min(5, int(pag_str) if pag_str.isdigit() else 2))
            leads = []; urls_batch = set()
            cabeceras = ["Nombre", "Cargo", "Empresa_Actual", "URL_Perfil"]

            for pag in range(1, paginas + 1):
                self._check_stop_pause()

                url = (f"https://www.linkedin.com/search/results/people/?"
                       f"geoUrn=%5B%22100768673%22%5D"
                       f"&keywords={urllib.parse.quote(keyword)}"
                       f"&page={pag}&origin=FACETED_SEARCH")

                self._log(f"Malta | Página {pag}/{paginas}")
                self.driver.get(url)
                self._pausa(5, 8)
                self._detectar_captcha()
                self._check_stop_pause()

                try:
                    WebDriverWait(self.driver, 10).until(EC.presence_of_element_located(
                        (By.XPATH, "//a[contains(@href,'/in/') and not(contains(@href,'miniProfile'))]")))
                except TimeoutException:
                    self._log(f"Sin resultados en página {pag}."); continue

                for paso in range(4):
                    self._check_stop_pause()
                    self.driver.execute_script(f"window.scrollTo(0,document.body.scrollHeight*{(paso + 1) / 4});")
                    self._pausa(1.5, 2.5)

                self._log("Extrayendo perfiles...")
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
                self._log(f"  {len(raw_leads)} perfiles detectados")

                for j, data in enumerate(raw_leads):
                    self._check_stop_pause()
                    self._set_progress(self.prog3, j / max(len(raw_leads), 1), f"Pág {pag}: procesando {j + 1}/{len(raw_leads)}")
                    url_perfil = data.get("url", "")
                    nombre_img = data.get("nombre", "")
                    raw_text = data.get("raw", "")
                    js_empresa = data.get("js_empresa", "")

                    if not url_perfil or "linkedin.com/in/" not in url_perfil: continue
                    url_norm = url_perfil.split('?')[0].rstrip("/").lower()
                    if url_norm in urls_batch: continue
                    urls_batch.add(url_norm)

                    lineas_raw = [l.strip() for l in raw_text.split('\n') if l.strip()]
                    resultado = parsear_bloque_perfil(nombre_img, lineas_raw, js_empresa)
                    if not resultado: continue

                    leads.append([resultado["nombre"], resultado["cargo"], resultado["empresa_actual"], url_perfil])
                    self._log(f"  {resultado['nombre']}  /  {resultado['cargo'][:36]}")

                self._pausa(5, 9)

            self._set_progress(self.prog3, 1.0, "Búsqueda finalizada.")

            vistos = set(); leads_unicos = []
            for fila in leads:
                clave = fila[-1].split('?')[0].rstrip("/").lower()
                if clave not in vistos:
                    vistos.add(clave); leads_unicos.append(fila)

            dup = len(leads) - len(leads_unicos)
            if dup > 0: self._log(f"Duplicados eliminados: {dup}")

            if leads_unicos:
                ruta_final = guardar_en_csv(self.save_path_mod3, cabeceras, leads_unicos, "URL_Perfil")
                if ruta_final:
                    self._log(f"Éxito — {len(leads_unicos)} perfiles guardados en: {os.path.basename(ruta_final)}")
            else:
                self._log("No se ha guardado a nadie en esta búsqueda.")

        except InterruptedError as e:
            self._log(f"⚠️ {e}")
            self._set_progress(self.prog3, 0, "Búsqueda detenida.")
            if 'leads_unicos' not in locals():
                vistos = set(); leads_unicos = []
                for fila in leads:
                    clave = fila[-1].split('?')[0].rstrip("/").lower()
                    if clave not in vistos:
                        vistos.add(clave); leads_unicos.append(fila)
            if leads_unicos:
                ruta_final = guardar_en_csv(self.save_path_mod3, cabeceras, leads_unicos, "URL_Perfil")
                self._log(f"Se guardaron {len(leads_unicos)} perfiles extraídos hasta el momento.")
        except Exception as e:
            self._log(f"Error inesperado: {e}")
        finally:
            self._set_modulo_buttons("normal")

if __name__ == "__main__":
    app = AIntelligenceApp()
    app.mainloop()