"""
==============================================================================
MÓDULO DE PROCESAMIENTO DE DATOS Y UTILIDADES (utils.py)
==============================================================================
"""

import os, csv, time, random, re, threading
from selenium.webdriver.common.by import By
from config import ARCHIVO_PROCESADOS

# ------------------------------------------------------------------------------
# GESTIÓN DE ESTADO MULTI-HILO (Thread-Safety)
# ------------------------------------------------------------------------------
_lock = threading.Lock()
contadores = {"conexiones": 0, "seguidos": 0, "errores": 0}

def inc(clave, n=1):
    """Incrementa un KPI global bloqueando temporalmente a otros hilos."""
    with _lock:
        contadores[clave] += n

# ------------------------------------------------------------------------------
# I/O: LECTURA Y ESCRITURA DE ESTADO
# ------------------------------------------------------------------------------
def cargar_procesados():
    """Carga el historial de interacciones en un 'Set' de memoria."""
    if not os.path.isfile(ARCHIVO_PROCESADOS): return set()
    with open(ARCHIVO_PROCESADOS, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def marcar_como_procesado(url):
    """Añade una URL al disco duro para evitar re-procesos."""
    with open(ARCHIVO_PROCESADOS, "a", encoding="utf-8") as f:
        f.write(url.strip() + "\n")

def pausa_aleatoria(a, b):
    """Emula la cadencia de clic humana."""
    time.sleep(random.uniform(a, b))

def extraer_texto_seguro(elemento, xpaths):
    """Intenta múltiples selectores DOM para evitar Crash de Selenium."""
    for xp in xpaths:
        try:
            t = elemento.find_element(By.XPATH, xp).text.strip()
            if t: return t
        except: continue
    return ""

# ------------------------------------------------------------------------------
# MOTOR DE EXPORTACIÓN CSV (Con escudo de versión)
# ------------------------------------------------------------------------------
def guardar_en_csv(ruta_archivo, cabeceras, datos, columna_url=None):
    """Guarda los datos en disco forzando utf-8-sig para compatibilidad con Excel."""
    idx = cabeceras.index(columna_url) if columna_url and columna_url in cabeceras else -1
    existentes = set()
    es_nuevo = False

    if os.path.isfile(ruta_archivo):
        with open(ruta_archivo, "r", encoding="utf-8-sig") as f:
            rd = csv.reader(f)
            file_headers = next(rd, None)

            if file_headers and [h.strip() for h in file_headers] != cabeceras:
                base, ext = os.path.splitext(ruta_archivo)
                ruta_archivo = f"{base}_v34{ext}"
                es_nuevo = True
            else:
                for row in rd:
                    try: existentes.add(row[idx].strip())
                    except IndexError: pass
    else:
        es_nuevo = True

    nuevos, batch = [], set()
    for d in datos:
        try:
            u = d[idx].strip()
            if u not in existentes and u not in batch:
                nuevos.append(d); batch.add(u)
        except IndexError: pass

    if nuevos:
        modo = "w" if es_nuevo else "a"
        with open(ruta_archivo, modo, newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            if modo == "w": w.writerow(cabeceras)
            w.writerows(nuevos)
        return ruta_archivo
    return None

# ------------------------------------------------------------------------------
# MOTOR DE SANITIZACIÓN DE DATOS (Regex)
# ------------------------------------------------------------------------------
PATRON_GRADO = re.compile(r'^(.+?)\s*[•·]\s*(1er|2º|2nd|3er\+|3rd\+|1st|1\.º|2\.º|3\.º)\s*$')
PATRON_GRADO_SUELTO = re.compile(r'^[•·]?\s*(1er|2º|2nd|3er\+|3rd\+|1st|1\.º|2\.º|3\.º)\s*$')
PATRON_UBICACION = re.compile(r'\b(Malta|Valletta|Sliema|Julian|Paceville|Gzira|Birkirkara|Mosta|Qormi)\b', re.IGNORECASE)
PAISES_SOLOS = {'malta', 'valletta', 'sliema', 'paceville'}
RUIDO_EXACTO = {
    'conectar', 'connect', 'mensaje', 'message', 'seguir', 'follow', 'in', 'premium',
    'enviar mensaje', 'send message', 'solicitud enviada', 'invitation sent',
    'pendiente', 'pending', 'más opciones', 'more actions', 'guardar', 'save'
}
RUIDO_PARCIAL = [
    'contacto en común', 'contactos en común', 'mutual connection', 'miembros en común',
    'connections in common', 'contactos', 'connections', 'seguidores', 'followers',
    'más de', '500+', 'ver perfil', 'view profile', 'compartido', 'shared', 'se unió',
    'joined', 'mensaje', 'message', 'conectar', 'connect', 'seguir', 'follow'
]
EDU_KEYWORDS = ['university', 'college', 'institute', 'academy', 'universidad', 'school', 'università', 'mcast']

def es_solo_ubicacion(linea):
    ll = linea.lower().strip()
    if ll in PAISES_SOLOS: return True
    if ' at ' in ll or ' @ ' in ll or ' en ' in ll: return False
    job_keywords = ['developer', 'engineer', 'manager', 'officer', 'director',
                    'programmer', 'consultant', 'cto', 'ceo', 'founder',
                    'leader', 'specialist', 'expert', 'designer', 'architect', 'student']
    if any(kw in ll for kw in job_keywords): return False
    if len(ll.split()) <= 5 and PATRON_UBICACION.search(linea): return True
    return False

def parsear_bloque_perfil(nombre_img, lineas_raw, js_empresa=""):
    """Algoritmo de limpieza de texto. Aísla Nombre, Cargo y Empresa."""
    nombre = (nombre_img or "").strip()
    if not nombre or nombre.lower() in ("linkedin member", "miembro de linkedin"):
        return None

    lineas = [l.strip() for l in lineas_raw if l.strip()]
    lineas = [l for l in lineas if not PATRON_GRADO_SUELTO.match(l) and not PATRON_GRADO.match(l)]

    cargo = ""; empresa_actual = ""; lineas_huerfanas = []
    SEPS_STRICT = [' at ', ' @ ', '@', ' en ']
    SEPS_LOOSE = [' - ']

    for linea in lineas:
        ll = linea.lower()
        if ll in RUIDO_EXACTO: continue
        if ll == nombre.lower(): continue
        if any(rp in ll for rp in RUIDO_PARCIAL): continue

        if ll.startswith('actual:') or ll.startswith('current:'):
            contenido = linea.split(':', 1)[1].strip().lstrip('…').strip()
            for sep in SEPS_STRICT + SEPS_LOOSE:
                idx = contenido.lower().find(sep)
                if idx != -1: empresa_actual = contenido[idx + len(sep):].strip(); break
            if not empresa_actual: empresa_actual = contenido
            continue

        if any(ll.startswith(p) for p in ['resumen:', 'summary:', 'sobre:', 'about:', 'educacion:', 'education:', 'anterior:', 'previous:']):
            continue
        if es_solo_ubicacion(linea): continue
        if not cargo: cargo = linea; continue
        lineas_huerfanas.append(linea)

    if not empresa_actual and cargo:
        cl = cargo.lower()
        for sep in SEPS_STRICT:
            idx = cl.find(sep)
            if idx != -1: empresa_actual = cargo[idx + len(sep):].strip(); break
        if not empresa_actual:
            for sep in SEPS_LOOSE:
                parts = cargo.split(sep)
                if len(parts) > 1: empresa_actual = parts[-1].strip(); break

    if not empresa_actual and js_empresa:
        if not any(edu in js_empresa.lower() for edu in EDU_KEYWORDS):
            empresa_actual = js_empresa

    if not empresa_actual and lineas_huerfanas:
        p = lineas_huerfanas[0]
        if 2 < len(p) < 45 and not any(edu in p.lower() for edu in EDU_KEYWORDS):
            empresa_actual = p

    if empresa_actual:
        if empresa_actual.endswith("..."): empresa_actual = empresa_actual[:-3].strip()
        if ' - ' in empresa_actual: empresa_actual = empresa_actual.split(' - ')[0].strip()
        if '.' in empresa_actual: empresa_actual = empresa_actual.split('.')[0].strip()
        if len(empresa_actual) > 45: empresa_actual = "No especificada"

    for ruido in [" open to work", " hiring", " looking for opportunities", " busca empleo", " looking for work"]:
        nombre = re.sub(re.escape(ruido), "", nombre, flags=re.IGNORECASE).strip()

    return {"nombre": nombre, "cargo": cargo or "No especificado", "empresa_actual": empresa_actual or "No especificada"}