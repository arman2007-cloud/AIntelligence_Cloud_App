"""
==============================================================================
DATA PROCESSING AND UTILITIES ENGINE (utils.py)
==============================================================================
Architecture:
    Decouples heavy data processing (Regex), file I/O (CSV), and thread-safe
    state management from the main GUI thread.
==============================================================================
"""

import os, csv, time, random, re, threading
from selenium.webdriver.common.by import By
from config import PROCESSED_FILE

# ------------------------------------------------------------------------------
# THREAD-SAFE STATE MANAGEMENT
# ------------------------------------------------------------------------------
_lock = threading.Lock()
counters = {"connections": 0, "followed": 0, "errors": 0}

def inc(key, n=1):
    """Increments a global counter safely across multiple background threads."""
    with _lock:
        counters[key] += n

# ------------------------------------------------------------------------------
# I/O: FILE AND STATE MANAGEMENT
# ------------------------------------------------------------------------------
def load_processed():
    """Loads the history of processed profiles into an O(1) lookup memory Set."""
    if not os.path.isfile(PROCESSED_FILE): return set()
    with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def mark_as_processed(url):
    """Appends a processed URL to the disk database."""
    with open(PROCESSED_FILE, "a", encoding="utf-8") as f:
        f.write(url.strip() + "\n")

def random_pause(a, b):
    """Injects non-deterministic pauses to emulate human jitter."""
    time.sleep(random.uniform(a, b))

def extract_safe_text(element, xpaths):
    """Fault-tolerant DOM text extraction. Tries multiple XPaths sequentially."""
    for xp in xpaths:
        try:
            t = element.find_element(By.XPATH, xp).text.strip()
            if t: return t
        except: continue
    return ""

# ------------------------------------------------------------------------------
# CSV EXPORT ENGINE (Version-Controlled)
# ------------------------------------------------------------------------------
def save_to_csv(file_path, headers, data, url_column=None):
    """Safely writes data to CSV using UTF-8-BOM for MS Excel compatibility."""
    idx = headers.index(url_column) if url_column and url_column in headers else -1
    existing_records = set()
    is_new_file = False

    if os.path.isfile(file_path):
        with open(file_path, "r", encoding="utf-8-sig") as f:
            rd = csv.reader(f)
            file_headers = next(rd, None)

            # Versioning shield: if headers changed, create a safe backup file
            if file_headers and [h.strip() for h in file_headers] != headers:
                base, ext = os.path.splitext(file_path)
                file_path = f"{base}_v34{ext}"
                is_new_file = True
            else:
                for row in rd:
                    try: existing_records.add(row[idx].strip())
                    except IndexError: pass
    else:
        is_new_file = True

    new_rows, batch = [], set()
    for d in data:
        try:
            u = d[idx].strip()
            if u not in existing_records and u not in batch:
                new_rows.append(d); batch.add(u)
        except IndexError: pass

    if new_rows:
        mode = "w" if is_new_file else "a"
        with open(file_path, mode, newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            if mode == "w": w.writerow(headers)
            w.writerows(new_rows)
        return file_path
    return None

# ------------------------------------------------------------------------------
# SEMANTIC DATA CLEANING ENGINE (Regex Heuristics)
# ------------------------------------------------------------------------------
DEGREE_PATTERN = re.compile(r'^(.+?)\s*[•·]\s*(1er|2º|2nd|3er\+|3rd\+|1st|1\.º|2\.º|3\.º)\s*$')
LOOSE_DEGREE_PATTERN = re.compile(r'^[•·]?\s*(1er|2º|2nd|3er\+|3rd\+|1st|1\.º|2\.º|3\.º)\s*$')
LOCATION_PATTERN = re.compile(r'\b(Malta|Valletta|Sliema|Julian|Paceville|Gzira|Birkirkara|Mosta|Qormi)\b', re.IGNORECASE)

ISOLATED_COUNTRIES = {'malta', 'valletta', 'sliema', 'paceville'}

# Bilingual Stop-Words (To handle users who navigate LinkedIn in Spanish or English)
EXACT_NOISE = {
    'conectar', 'connect', 'mensaje', 'message', 'seguir', 'follow', 'in', 'premium',
    'enviar mensaje', 'send message', 'solicitud enviada', 'invitation sent',
    'pendiente', 'pending', 'más opciones', 'more actions', 'guardar', 'save'
}
PARTIAL_NOISE = [
    'contacto en común', 'contactos en común', 'mutual connection', 'miembros en común',
    'connections in common', 'contactos', 'connections', 'seguidores', 'followers',
    'más de', '500+', 'ver perfil', 'view profile', 'compartido', 'shared', 'se unió',
    'joined', 'mensaje', 'message', 'conectar', 'connect', 'seguir', 'follow'
]
EDU_KEYWORDS = ['university', 'college', 'institute', 'academy', 'universidad', 'school', 'università', 'mcast']

def is_just_location(line):
    """Detects false positives where LinkedIn outputs the city instead of job title."""
    ll = line.lower().strip()
    if ll in ISOLATED_COUNTRIES: return True
    if ' at ' in ll or ' @ ' in ll or ' en ' in ll: return False

    job_keywords = ['developer', 'engineer', 'manager', 'officer', 'director',
                    'programmer', 'consultant', 'cto', 'ceo', 'founder',
                    'leader', 'specialist', 'expert', 'designer', 'architect', 'student']
    if any(kw in ll for kw in job_keywords): return False
    if len(ll.split()) <= 5 and LOCATION_PATTERN.search(line): return True
    return False

def parse_profile_block(img_name, raw_lines, js_company=""):
    """Heuristic pipeline: extracts Name, Job Title and Company from raw text nodes."""
    name = (img_name or "").strip()
    if not name or name.lower() in ("linkedin member", "miembro de linkedin"):
        return None

    lines = [l.strip() for l in raw_lines if l.strip()]
    lines = [l for l in lines if not LOOSE_DEGREE_PATTERN.match(l) and not DEGREE_PATTERN.match(l)]

    job_title = ""; current_company = ""; orphan_lines = []
    STRICT_SEPS = [' at ', ' @ ', '@', ' en ']
    LOOSE_SEPS = [' - ']

    for line in lines:
        ll = line.lower()
        if ll in EXACT_NOISE: continue
        if ll == name.lower(): continue
        if any(rp in ll for rp in PARTIAL_NOISE): continue

        if ll.startswith('actual:') or ll.startswith('current:'):
            content = line.split(':', 1)[1].strip().lstrip('…').strip()
            for sep in STRICT_SEPS + LOOSE_SEPS:
                idx = content.lower().find(sep)
                if idx != -1: current_company = content[idx + len(sep):].strip(); break
            if not current_company: current_company = content
            continue

        if any(ll.startswith(p) for p in ['resumen:', 'summary:', 'sobre:', 'about:', 'educacion:', 'education:', 'anterior:', 'previous:']):
            continue
        if is_just_location(line): continue
        if not job_title: job_title = line; continue
        orphan_lines.append(line)

    if not current_company and job_title:
        cl = job_title.lower()
        for sep in STRICT_SEPS:
            idx = cl.find(sep)
            if idx != -1: current_company = job_title[idx + len(sep):].strip(); break
        if not current_company:
            for sep in LOOSE_SEPS:
                parts = job_title.split(sep)
                if len(parts) > 1: current_company = parts[-1].strip(); break

    if not current_company and js_company:
        if not any(edu in js_company.lower() for edu in EDU_KEYWORDS):
            current_company = js_company

    if not current_company and orphan_lines:
        p = orphan_lines[0]
        if 2 < len(p) < 45 and not any(edu in p.lower() for edu in EDU_KEYWORDS):
            current_company = p

    if current_company:
        if current_company.endswith("..."): current_company = current_company[:-3].strip()
        if ' - ' in current_company: current_company = current_company.split(' - ')[0].strip()
        if '.' in current_company: current_company = current_company.split('.')[0].strip()
        if len(current_company) > 45: current_company = "Not specified"

    # Clean injection of '#OpenToWork' badge in names
    for noise in [" open to work", " hiring", " looking for opportunities", " busca empleo", " looking for work"]:
        name = re.sub(re.escape(noise), "", name, flags=re.IGNORECASE).strip()

    return {"name": name, "job_title": job_title or "Not specified", "current_company": current_company or "Not specified"}