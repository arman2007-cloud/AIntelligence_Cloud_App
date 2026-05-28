// static/js/main.js
// ── VARIABLES GLOBALES ──
const metaToken = document.querySelector('meta[name="api-token"]');
const SYSTEM_TOKEN = metaToken ? metaToken.getAttribute('content') : "";

// 🛡️ FIX MULTI-TENANT: Prefijo único para aislar la memoria caché del navegador por usuario
const USER_PREFIX = SYSTEM_TOKEN ? SYSTEM_TOKEN.substring(0, 10) + '_' : '';

if (!SYSTEM_TOKEN) {
    console.error("⚠️ Bloqueo de Seguridad: No se encontró el token dinámico en el HTML.");
}

let invitesSentToday = 0;
const MAX_INVITES = 15;
let selectedCandidatesCount = 0;
window.activePolls = {}; 
let sniperCurrentName = "";
let sniperCurrentUrl = "";

// ── INICIALIZACIÓN ──
window.addEventListener('DOMContentLoaded', () => {
    injectTaskManager();

    const hr = new Date().getHours();
    let greeting = "Good evening";
    if (hr < 12) greeting = "Good morning";
    else if (hr < 18) greeting = "Good afternoon";
    const greetingTitle = document.getElementById('greetingTitle');
    if(greetingTitle) greetingTitle.innerText = `${greeting}, HR Team`;

    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    const dateSubtitle = document.getElementById('dateSubtitle');
    if(dateSubtitle) dateSubtitle.innerText = new Date().toLocaleDateString('en-US', options);

    // El tema oscuro lo dejamos global (sin prefijo) para que la pantalla no pegue pantallazos blancos al cambiar de usuario
    if (localStorage.getItem('aintel_theme') === 'dark') {
        document.body.classList.add('dark-theme');
        const themeIcon = document.getElementById('themeIcon');
        const themeText = document.getElementById('themeText');
        if(themeIcon) themeIcon.innerHTML = '<i class="fa-solid fa-sun"></i>';
        if(themeText) themeText.innerText = 'Light Theme';
    }

    // 🛡️ Memoria de inputs aislada por usuario
    const memInputs = ['outreachMessage', 'inputMessage', 'inputSheetUrl', 'inputCargo', 'inputLocation', 'inputJobTitle', 'inputJobLocation'];
    memInputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            const saved = localStorage.getItem(USER_PREFIX + 'aintel_' + id);
            if (saved) el.value = saved;
            el.addEventListener('input', () => localStorage.setItem(USER_PREFIX + 'aintel_' + id, el.value));
        }
    });

    const enterSelectors = [
        { id: 'inputCargo', fn: runCandidates },
        { id: 'inputLocation', fn: runCandidates },
        { id: 'inputPagesCandidates', fn: runCandidates },
        { id: 'inputSheetUrl', fn: () => handleOutreachClick('manual') },
        { id: 'inputJobTitle', fn: runJobs },
        { id: 'inputJobLocation', fn: runJobs }
    ];

    enterSelectors.forEach(item => {
        const el = document.getElementById(item.id);
        if (el) {
            el.addEventListener('keypress', e => {
                if (e.key === 'Enter') {
                    e.preventDefault();
                    if(!el.disabled) item.fn();
                }
            });
        }
    });

    const msgAuto = document.getElementById('outreachMessage');
    const countAuto = document.getElementById('charCounterAuto');
    if (msgAuto && countAuto) {
        msgAuto.addEventListener('input', () => {
            const len = msgAuto.value.length;
            countAuto.innerText = `${len}/200`;
            if(len > 200) countAuto.classList.add('limit-reached');
            else countAuto.classList.remove('limit-reached');
            updateOutreachBtn();
        });
        msgAuto.dispatchEvent(new Event('input'));
    }

    const msgManual = document.getElementById('inputMessage');
    const countManual = document.getElementById('charCounterManual');
    if (msgManual && countManual) {
        msgManual.addEventListener('input', () => {
            const len = msgManual.value.length;
            countManual.innerText = `${len}/200`;
            if(len > 200) countManual.classList.add('limit-reached');
            else countManual.classList.remove('limit-reached');
            updateManualBtn();
        });
        msgManual.dispatchEvent(new Event('input'));
    }

    const msgSniper = document.getElementById('sniperMessageArea');
    const countSniper = document.getElementById('sniperCharCounter');
    if (msgSniper && countSniper) {
        msgSniper.addEventListener('input', () => {
            const len = msgSniper.value.length;
            countSniper.innerText = `${len}/200`;
            const btnSniper = document.getElementById('btnSendSniper');
            const warnSniper = document.getElementById('sniperWarningText');
            
            if(len > 200) {
                countSniper.classList.add('limit-reached');
                if(btnSniper) btnSniper.disabled = true;
                if(warnSniper) warnSniper.style.display = 'block';
            } else {
                countSniper.classList.remove('limit-reached');
                if(btnSniper) btnSniper.disabled = false;
                if(warnSniper) warnSniper.style.display = 'none';
            }
        });
    }

    restoreSavedResults();

    fetch('/api/stats', { headers: {'X-API-Token': SYSTEM_TOKEN} }).then(r=>r.json()).then(data => {
        invitesSentToday = data.connections || 0;
        updateCounterUI();
    }).catch(e=>console.log(e));

    setEngineOnline(true);

    setInterval(() => {
        fetch('/api/health', { 
            method: 'GET', 
            headers: {'X-API-Token': SYSTEM_TOKEN} 
        }).catch(() => {});
    }, 5000);

    loadFavorites();
});

// ==========================================================================
// RECUPERACIÓN DE MEMORIA (LOCALSTORAGE)
// ==========================================================================
function restoreSavedResults() {
    try {
        // Restaurar Candidatos con Prefijo de Usuario
        const savedCandidates = localStorage.getItem(USER_PREFIX + 'aintel_candidates_data');
        if (savedCandidates) {
            const parsedCands = JSON.parse(savedCandidates);
            if (parsedCands && parsedCands.length > 0) {
                document.getElementById('emptyCandidates').style.display = 'none';
                document.getElementById('reviewOutreachPanel').style.display = 'block';
                const driveLink = localStorage.getItem(USER_PREFIX + 'aintel_candidates_drive');
                if (driveLink) document.getElementById('driveLinkAnchor').href = driveLink;
                renderCandidates(parsedCands);
            }
        }

        // Restaurar Ofertas de Empleo (Jobs) con Prefijo de Usuario
        const savedJobs = localStorage.getItem(USER_PREFIX + 'aintel_jobs_data');
        if (savedJobs) {
            const parsedJobs = JSON.parse(savedJobs);
            if (parsedJobs && parsedJobs.length > 0) {
                document.getElementById('emptyJobs').style.display = 'none';
                const driveLink = localStorage.getItem(USER_PREFIX + 'aintel_jobs_drive');
                if (driveLink) {
                    const driveBtn = document.getElementById('btnOpenDriveJobs');
                    if (driveBtn) driveBtn.href = driveLink;
                    document.getElementById('driveActionsJobs').style.display = 'flex';
                }
                renderJobs(parsedJobs);
            }
        }
    } catch (e) {
        console.error("Error restaurando datos de LocalStorage:", e);
    }
}

// ==========================================================================
// CONTROL DE TAREAS (PAUSE, RESUME, STOP) PARA CELERY
// ==========================================================================
function controlTask(action) {
    fetch('/api/control', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-API-Token': SYSTEM_TOKEN},
        body: JSON.stringify({ action: action })
    })
    .then(r => r.json())
    .then(res => {
        if(res.status === 'success') {
            const pauseBtns = document.querySelectorAll('.btn-pause');
            
            if(action === 'pause') {
                showToast('Campaign Paused. Click Resume to continue.', '<i class="fa-solid fa-pause"></i>', 'var(--text-2)');
                pauseBtns.forEach(btn => {
                    btn.innerHTML = '<i class="fa-solid fa-play"></i> Resume';
                    btn.setAttribute('onclick', "controlTask('resume')");
                });
            } else if (action === 'resume') {
                showToast('Campaign Resumed.', '<i class="fa-solid fa-play"></i>', 'var(--sage)');
                pauseBtns.forEach(btn => {
                    btn.innerHTML = '<i class="fa-solid fa-pause"></i> Pause';
                    btn.setAttribute('onclick', "controlTask('pause')");
                });
            } else if (action === 'stop') {
                showToast('Campaign Stopped.', '<i class="fa-solid fa-stop"></i>', 'var(--rose)');
                pauseBtns.forEach(btn => {
                    btn.innerHTML = '<i class="fa-solid fa-pause"></i> Pause';
                    btn.setAttribute('onclick', "controlTask('pause')");
                });
            }
        }
    });
}
// ==========================================================================
// SISTEMA DE FAVORITOS (TARGET COMPANIES)
// ==========================================================================
function loadFavorites() {
    fetch('/api/favorites', { headers: {'X-API-Token': SYSTEM_TOKEN} })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            renderFavorites(data.favorites);
        }
    }).catch(e => console.error(e));
}

function addFavorite() {
    const input = document.getElementById('inputFavorite');
    const company = input.value.trim();
    if (!company) return;

    fetch('/api/favorites', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-API-Token': SYSTEM_TOKEN },
        body: JSON.stringify({ company: company })
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            input.value = '';
            renderFavorites(data.favorites);
            showToast(`${company} added to Target Companies`, '<i class="fa-solid fa-star"></i>', 'var(--mauve)');
        }
    });
}

function removeFavorite(company) {
    fetch(`/api/favorites/${encodeURIComponent(company)}`, {
        method: 'DELETE',
        headers: { 'X-API-Token': SYSTEM_TOKEN }
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'success') {
            renderFavorites(data.favorites);
            showToast(`${company} removed`, '<i class="fa-solid fa-trash"></i>', 'var(--text-3)');
        }
    });
}

function renderFavorites(favs) {
    const list = document.getElementById('favoritesList');
    if (!list) return;

    if (favs.length === 0) {
        list.innerHTML = `<span style="font-size: 12px; color: var(--text-3); font-style: italic;">No companies added yet.</span>`;
        return;
    }

    let html = '';
    favs.forEach(f => {
        html += `
        <div style="background: rgba(155, 110, 168, 0.1); border: 1px solid rgba(155, 110, 168, 0.3); color: var(--mauve); padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: 500; display: flex; align-items: center; gap: 6px;">
            ${f}
            <i class="fa-solid fa-xmark" style="cursor: pointer; opacity: 0.7;" onclick="removeFavorite('${f}')" onmouseover="this.style.opacity='1'" onmouseout="this.style.opacity='0.7'"></i>
        </div>`;
    });
    list.innerHTML = html;
}

// ── WIDGET FLOTANTE (ADMINISTRADOR DE TAREAS) ──
function injectTaskManager() {
    if(document.getElementById('tm-container')) return;
    const tm = document.createElement('div');
    tm.id = 'tm-container';
    tm.style.cssText = 'position: fixed; bottom: 20px; right: 20px; z-index: 9999; display: flex; flex-direction: column; gap: 12px; width: 340px; pointer-events: none;';
    document.body.appendChild(tm);

    const style = document.createElement('style');
    style.innerHTML = `
        .tm-card { background: var(--bg-card, #12121A); border: 1px solid var(--border-lit, #252535); border-radius: 10px; padding: 16px; box-shadow: 0 10px 40px rgba(0,0,0,0.7); pointer-events: auto; animation: tmSlideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1); position:relative; overflow:hidden;}
        @keyframes tmSlideUp { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
        .tm-title { font-size: 14px; font-weight: 600; color: #fff; margin-bottom: 6px; display: flex; justify-content: space-between; align-items:center; }
        .tm-sub { font-size: 12px; color: #888; margin-bottom: 12px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .tm-bar-bg { background: rgba(255,255,255,0.05); height: 6px; border-radius: 6px; overflow: hidden; }
        .tm-bar-fill { height: 100%; width: 0%; transition: width 0.4s ease; }
        .tm-theme-candidates .tm-bar-fill { background: var(--rose); box-shadow: 0 0 10px var(--rose-dim); }
        .tm-theme-jobs .tm-bar-fill { background: var(--mauve); box-shadow: 0 0 10px var(--mauve-dim); }
        .tm-theme-outreach .tm-bar-fill, .tm-theme-manual .tm-bar-fill { background: var(--sage); box-shadow: 0 0 10px var(--sage-dim); }
        .tm-theme-analyze .tm-bar-fill { background: var(--rose); box-shadow: 0 0 10px var(--rose-dim); }
    `;
    document.head.appendChild(style);
}

function updateWidget(taskId, type, title, pct, sub) {
    let container = document.getElementById('tm-container');
    if(!container) return;
    let w = document.getElementById(`tw-${taskId}`);
    if(!w) {
        w = document.createElement('div');
        w.id = `tw-${taskId}`;
        w.className = `tm-card tm-theme-${type}`;
        w.innerHTML = `
            <div class="tm-title">
                <span><i class="fa-solid fa-circle-notch fa-spin"></i> ${title}</span>
                <span class="tm-pct" style="color:var(--text-2); font-size: 12px;">0%</span>
            </div>
            <div class="tm-sub">Initializing...</div>
            <div class="tm-bar-bg"><div class="tm-bar-fill"></div></div>
        `;
        container.appendChild(w);
    }
    w.querySelector('.tm-pct').innerText = pct + '%';
    w.querySelector('.tm-sub').innerText = sub;
    w.querySelector('.tm-bar-fill').style.width = pct + '%';

    if(pct >= 100 || sub.includes('✅') || sub.includes('❌') || sub.includes('completado') || sub.includes('Análisis completado')) {
        w.querySelector('.tm-title span').innerHTML = `<i class="fa-solid fa-check"></i> Completed`;
        setTimeout(() => {
            w.style.opacity = '0';
            w.style.transition = 'opacity 0.4s';
            setTimeout(() => w.remove(), 400);
        }, 5000);
    }
}

// ── MULTITAREA ASÍNCRONA (POLLER) Y CORTOCIRCUITO GLOBAL ──
function restoreButtonUI(taskType) {
    if(taskType === 'candidates') {
        const btn = document.getElementById('btnScan');
        if(btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-radar"></i> Run AI Radar'; }
    } else if(taskType === 'jobs') {
        const btn = document.getElementById('btnScanJobs');
        if(btn) { btn.disabled = false; btn.innerHTML = '<i class="fa-solid fa-radar"></i> Scan Market & Save to Drive'; }
    } else if(taskType === 'outreach') {
        updateOutreachBtn();
    } else if(taskType === 'manual') {
        const btn = document.getElementById('btnInvite');
        if(btn) { btn.disabled = false; btn.innerHTML = 'Start Campaign'; }
        updateManualBtn();
    }
}

function pollTask(taskType, widgetTitle, onCompleteCallback) {
    if (window.activePolls[taskType]) clearInterval(window.activePolls[taskType]);
    let ticks = 0; const maxTicks = 1200; 

    window.activePolls[taskType] = setInterval(() => {
        ticks++;
        if (ticks > maxTicks) {
            clearInterval(window.activePolls[taskType]);
            showToast("Process timed out.", '<i class="fa-solid fa-clock"></i>', 'var(--peach)');
            restoreButtonUI(taskType);
            if(taskType === 'analyze') closeSniperModal();
            return;
        }

        fetch('/api/status', { headers: {'X-API-Token': SYSTEM_TOKEN} })
        .then(r => r.json())
        .then(data => {
            const tData = data.tasks && data.tasks[taskType] ? data.tasks[taskType] : null;
            if (!tData) return; 

            if (tData.error) {
                console.error(`Error en la tarea ${taskType}:`, tData.error);
                showToast("Process stopped automatically.", '<i class="fa-solid fa-triangle-exclamation"></i>', 'var(--peach)');
                
                clearInterval(window.activePolls[taskType]);
                restoreButtonUI(taskType);
                if(taskType === 'analyze') closeSniperModal();
                
                let w = document.getElementById(`tw-${tData.task_id || taskType}`);
                if(w) {
                    w.style.borderColor = 'var(--peach)';
                    w.querySelector('.tm-title span').innerHTML = '<i class="fa-solid fa-triangle-exclamation"></i> Error';
                    w.querySelector('.tm-sub').innerText = 'Process Aborted';
                    w.querySelector('.tm-bar-fill').style.background = 'var(--peach)';
                    setTimeout(() => { w.style.opacity = '0'; setTimeout(() => w.remove(), 400); }, 3000);
                }
                
                fetch('/api/clear_results', { method: 'POST', headers: {'X-API-Token': SYSTEM_TOKEN} });
                return;
            }

            updateWidget(tData.task_id || taskType, taskType, widgetTitle, tData.progress_pct, tData.message);

            if (!tData.is_running) {
                clearInterval(window.activePolls[taskType]);
                restoreButtonUI(taskType);
                
                if (!tData.error) { 
                    playDing();
                    onCompleteCallback(tData);
                }
            }
        }).catch(err => console.error("Polling error", err));
    }, 1000);
}

// ── HIDRATACIÓN INMORTAL ──
function setEngineOnline(isAutoRestore = false){
  document.getElementById('statusDotInner').style.background='var(--sage)';
  document.getElementById('statusPing').style.background='var(--sage)';
  document.getElementById('statusText').textContent='System Ready';
  document.getElementById('statusText').style.color='var(--sage)';
  updateManualBtn();

  fetch('/api/status', { headers: {'X-API-Token': SYSTEM_TOKEN} })
  .then(r=>r.json())
  .then(data => {
      if(!data.tasks) return;

      const cTask = data.tasks['candidates'];
      if (cTask) {
          if (cTask.is_running) {
              const btn = document.getElementById('btnScan');
              if(btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Radar Active...'; }
              pollTask('candidates', 'Sourcing Candidates', (res) => {
                  showToast('Radar complete! Review candidates below.','<i class="fa-solid fa-wand-magic-sparkles"></i>','var(--rose)');
                  document.getElementById('reviewOutreachPanel').style.display='block';
                  
                  if(res.results) localStorage.setItem(USER_PREFIX + 'aintel_candidates_data', JSON.stringify(res.results));
                  if(res.drive_link) {
                      localStorage.setItem(USER_PREFIX + 'aintel_candidates_drive', res.drive_link);
                      document.getElementById('driveLinkAnchor').href = res.drive_link;
                  }
                  
                  renderCandidates(res.results);
              });
          } else if (cTask.results && cTask.results.length > 0) {
              document.getElementById('emptyCandidates').style.display = 'none';
              document.getElementById('reviewOutreachPanel').style.display = 'block';
              if(cTask.drive_link) document.getElementById('driveLinkAnchor').href = cTask.drive_link;
              
              localStorage.setItem(USER_PREFIX + 'aintel_candidates_data', JSON.stringify(cTask.results));
              if(cTask.drive_link) localStorage.setItem(USER_PREFIX + 'aintel_candidates_drive', cTask.drive_link);
              
              renderCandidates(cTask.results);
          }
      }

      const jTask = data.tasks['jobs'];
      if (jTask) {
          if (jTask.is_running) {
              const btn = document.getElementById('btnScanJobs');
              if(btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Scanning Market...'; }
              pollTask('jobs', 'Scanning Job Market', (res) => {
                  if (res.results && res.results.length > 0) {
                      showToast('Market report saved!','<i class="fa-solid fa-chart-line"></i>','var(--mauve)');
                      
                      localStorage.setItem(USER_PREFIX + 'aintel_jobs_data', JSON.stringify(res.results));
                      
                      if(res.drive_link) {
                          localStorage.setItem(USER_PREFIX + 'aintel_jobs_drive', res.drive_link);
                          const dBtn = document.getElementById('btnOpenDriveJobs');
                          dBtn.href = res.drive_link;
                          document.getElementById('driveActionsJobs').style.display='flex';
                      }
                  }
                  renderJobs(res.results);
              });
          } else if (jTask.results && jTask.results.length > 0) {
              document.getElementById('emptyJobs').style.display = 'none';
              
              localStorage.setItem(USER_PREFIX + 'aintel_jobs_data', JSON.stringify(jTask.results));
              
              if(jTask.drive_link) {
                  localStorage.setItem(USER_PREFIX + 'aintel_jobs_drive', jTask.drive_link);
                  const driveBtn = document.getElementById('btnOpenDriveJobs');
                  driveBtn.href = jTask.drive_link;
                  document.getElementById('driveActionsJobs').style.display='flex';
              }
              renderJobs(jTask.results);
          }
      }

      const oTask = data.tasks['outreach'];
      if (oTask && oTask.is_running) {
          const btn = document.getElementById('btnStartPipeline');
          if(btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Sending Campaign...'; }
          pollTask('outreach', 'Batch Outreach', (res) => { updateCounterUI(); });
      }

      const mTask = data.tasks['manual'];
      if (mTask && mTask.is_running) {
          const btn = document.getElementById('btnInvite');
          if(btn) { btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Sending Invites...'; }
          pollTask('manual', 'Manual Outreach', (res) => { updateCounterUI(); });
      }

      const aTask = data.tasks['analyze'];
      if (aTask && aTask.is_running) {
          pollTask('analyze', 'AI Sniper Drafting', (res) => {
              showToast('AI Draft ready in background.', '<i class="fa-solid fa-wand-magic-sparkles"></i>', 'var(--rose)');
          });
      }
  }).catch(e=>console.log("Error hidratación:", e));
}

// ── FLUJOS PRINCIPALES ──
function runCandidates(){
  const cargo=document.getElementById('inputCargo').value.trim();
  const location=document.getElementById('inputLocation').value.trim();
  const pages=parseInt(document.getElementById('inputPagesCandidates').value) || 1;

  if(!cargo){
      showToast('Please enter a Job Title first.','<i class="fa-solid fa-circle-info"></i>','var(--peach)');
      document.getElementById('inputCargo').focus();
      return;
  }

  const btn = document.getElementById('btnScan');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Radar Active...';
  
  document.getElementById('emptyCandidates').style.display='none';
  document.getElementById('reviewOutreachPanel').style.display='none';
  document.getElementById('candidateResults').innerHTML='';

  fetch('/api/search_candidates', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-API-Token': SYSTEM_TOKEN},
      body: JSON.stringify({ cargo: cargo, location: location, pages: pages })
  }).then(r => r.json()).then(res => {
      if(res.status === 'error') {
          showToast(res.message, '<i class="fa-solid fa-triangle-exclamation"></i>', 'var(--peach)');
          restoreButtonUI('candidates');
          return;
      }
      pollTask('candidates', 'Sourcing Candidates', (data) => {
          showToast('Radar complete! Review candidates below.','<i class="fa-solid fa-wand-magic-sparkles"></i>','var(--rose)');
          document.getElementById('reviewOutreachPanel').style.display='block';
          
          if(data.results) localStorage.setItem(USER_PREFIX + 'aintel_candidates_data', JSON.stringify(data.results));
          if(data.drive_link) {
              localStorage.setItem(USER_PREFIX + 'aintel_candidates_drive', data.drive_link);
              document.getElementById('driveLinkAnchor').href = data.drive_link;
          }
          
          renderCandidates(data.results);
      });
  });
}

function runJobs(){
  const title=document.getElementById('inputJobTitle').value.trim();
  const location=document.getElementById('inputJobLocation').value.trim();

  if(!title){
      showToast('Please enter a Job Title first.','<i class="fa-solid fa-circle-info"></i>','var(--peach)');
      document.getElementById('inputJobTitle').focus();
      return;
  }

  const btn = document.getElementById('btnScanJobs');
  btn.disabled = true;
  btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Scanning Market...';

  document.getElementById('emptyJobs').style.display='none';
  document.getElementById('jobResults').innerHTML='';
  document.getElementById('driveActionsJobs').style.display='none';
  document.getElementById('btnClearJobs').style.display='none';

  fetch('/api/search_jobs', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-API-Token': SYSTEM_TOKEN},
      body: JSON.stringify({ cargo: title, location: location })
  }).then(r => r.json()).then(res => {
      if(res.status === 'error') {
          showToast(res.message, '<i class="fa-solid fa-triangle-exclamation"></i>', 'var(--peach)');
          restoreButtonUI('jobs');
          return;
      }
      pollTask('jobs', 'Scanning Job Market', (data) => {
          if (data.results && data.results.length > 0) {
              showToast('Market report saved to your HR Drive folder!','<i class="fa-solid fa-chart-line"></i>','var(--mauve)');
              
              localStorage.setItem(USER_PREFIX + 'aintel_jobs_data', JSON.stringify(data.results));
              
              if(data.drive_link) {
                  localStorage.setItem(USER_PREFIX + 'aintel_jobs_drive', data.drive_link);
                  const driveBtn = document.getElementById('btnOpenDriveJobs');
                  driveBtn.href = data.drive_link;
                  document.getElementById('driveActionsJobs').style.display='flex';
              }
          } else {
              showToast('Scan complete, but no roles found matching criteria.','<i class="fa-solid fa-circle-exclamation"></i>','var(--peach)');
          }
          renderJobs(data.results);
      });
  });
}

function handleOutreachClick(actionType) {
    if (actionType === 'auto') {
        startOutreachPipeline();
    } else if (actionType === 'manual') {
        runManualInvitations();
    }
}

function startOutreachPipeline() {
    if(selectedCandidatesCount === 0 || invitesSentToday + selectedCandidatesCount > MAX_INVITES) return;

    const btn = document.getElementById('btnStartPipeline');
    const msg = document.getElementById('outreachMessage').value;
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Sending Campaign...';

    showToast('Outreach Sequence Started!','<i class="fa-solid fa-paper-plane"></i>','var(--sage)');

    let selectedNames = [];
    document.querySelectorAll('.cand-cb').forEach(cb => {
        if(cb.checked) selectedNames.push(cb.getAttribute('data-name'));
    });

    fetch('/api/run_outreach', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-API-Token': SYSTEM_TOKEN},
        body: JSON.stringify({ selected_candidates: selectedNames, message: msg })
    }).then(r => r.json()).then(res => {
        if(res.status === 'error') {
            showToast(res.message, '<i class="fa-solid fa-triangle-exclamation"></i>', 'var(--peach)');
            restoreButtonUI('outreach');
            return;
        }
        pollTask('outreach', 'Batch Outreach', (data) => {
            fetch('/api/stats', { headers: {'X-API-Token': SYSTEM_TOKEN} }).then(r=>r.json()).then(d => {
                invitesSentToday = d.connections !== undefined ? d.connections : invitesSentToday;
                updateCounterUI();
            });
            document.querySelectorAll('.cand-cb').forEach(cb => { if(cb.checked) cb.disabled = true; });
        });
    });
}

function runManualInvitations(){
    const url = document.getElementById('inputSheetUrl').value.trim();
    const msg = document.getElementById('inputMessage').value;

    if(!url || !url.includes('docs.google.com/spreadsheets')){
        showToast('Please provide a valid Google Sheets link.','<i class="fa-solid fa-circle-exclamation"></i>','var(--peach)');
        return;
    }

    const btn = document.getElementById('btnInvite');
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Sending Invites...';

    showToast('Manual Outreach started!','<i class="fa-solid fa-paper-plane"></i>','var(--sage)');

    fetch('/api/run_manual_outreach', {
        method: 'POST',
        headers: {'Content-Type': 'application/json', 'X-API-Token': SYSTEM_TOKEN},
        body: JSON.stringify({ url: url, message: msg })
    }).then(r => r.json()).then(res => {
        if(res.status === 'error') {
            showToast(res.message, '<i class="fa-solid fa-triangle-exclamation"></i>', 'var(--peach)');
            restoreButtonUI('manual');
            return;
        }
        pollTask('manual', 'Manual Outreach', (data) => {
            fetch('/api/stats', { headers: {'X-API-Token': SYSTEM_TOKEN} }).then(r=>r.json()).then(d => {
                invitesSentToday = d.connections !== undefined ? d.connections : invitesSentToday;
                updateCounterUI();
            });
        });
    });
}

// ── FUNCIONES DE RENDERIZADO ──
function renderCandidates(data){
  const list=document.getElementById('candidateResults');
  if(!data || data.length === 0) {
      list.innerHTML = '<p style="text-align:center; color:var(--text-3); font-size:14px; margin:20px 0;">No candidates found.</p>';
      updateOutreachBtn();
      return;
  }
  let html = '';
  selectedCandidatesCount = 0;
  data.forEach((c,i) => {
    const cls = c.score >= 70 ? 'score-high' : c.score >= 50 ? 'score-mid' : 'score-low';
    const isChecked = c.score >= 70 ? 'checked' : '';
    if (isChecked) selectedCandidatesCount++;
    html += `
    <div class="candidate-row" style="animation-delay:${i*.05}s">
        <input type="checkbox" class="custom-checkbox cand-cb" data-name="${c.name}" ${isChecked} onchange="updateOutreachBtn()">
        <div class="score-badge ${cls}">${c.score}</div>
        <div style="flex:1;">
            <a href="${c.url}" target="_blank" class="candidate-name" title="Open LinkedIn Profile">${c.name} <i class="fa-solid fa-arrow-up-right-from-square" style="font-size: 11px; margin-left: 5px; opacity: 0.5;"></i></a>
            <div class="candidate-meta">${c.meta}</div>
        </div>
        <button class="btn-var" onclick="openAISniper('${c.name}', '${c.url}')" style="border-color:var(--rose-dim); color:var(--rose); margin-left:10px;"><i class="fa-solid fa-wand-magic-sparkles"></i> AI Draft</button>
    </div>`;
  });
  list.innerHTML = html;
  updateOutreachBtn();
}
function renderJobs(data){
  const list=document.getElementById('jobResults');
  if(!data || data.length === 0) {
      list.innerHTML = '<p style="text-align:center; color:var(--text-3); font-size:14px; margin:20px 0;">No roles found.</p>';
      document.getElementById('btnClearJobs').style.display = 'inline-flex';
      return;
  }
  let html = '';
  
  data.forEach((c,i) => {
    const isFav = c.is_favorite;
    const badgeStyle = isFav 
        ? 'background: linear-gradient(135deg, #ffd700, #ffaa00); color: #000; border: none; box-shadow: 0 0 10px rgba(255,215,0,0.5);' 
        : 'background: var(--mauve-dim); color: var(--mauve); border: 1px solid rgba(155,110,168,0.2);';
        
    const icon = isFav ? '<i class="fa-solid fa-star"></i>' : '<i class="fa-solid fa-building"></i>';
    const favBadgeHtml = isFav ? '<span style="color:#ffaa00; font-weight:bold; font-size:11px; margin-left:8px; border: 1px solid #ffaa00; padding: 2px 6px; border-radius: 4px; background: rgba(255,215,0,0.1);"><i class="fa-solid fa-star"></i> TARGET COMPANY</span>' : '';
    const rowBorder = isFav ? 'border-left: 3px solid #ffaa00; background: rgba(255,215,0,0.02);' : '';

    html += `<div class="candidate-row" style="animation-delay:${i*.05}s; ${rowBorder}">
        <div class="score-badge" style="${badgeStyle}">${icon}</div>
        <div>
            <a href="${c.url}" target="_blank" class="candidate-name" title="Open Link">${c.name} <i class="fa-solid fa-arrow-up-right-from-square" style="font-size: 11px; margin-left: 5px; opacity: 0.5;"></i></a>
            <div class="candidate-meta">${c.meta} ${favBadgeHtml}</div>
        </div>
    </div>`;
  });
  
  list.innerHTML = html;
  document.getElementById('btnClearJobs').style.display = 'inline-flex';
}

function updateOutreachBtn() {
    const checkboxes = document.querySelectorAll('.cand-cb');
    const msgLen = document.getElementById('outreachMessage') ? document.getElementById('outreachMessage').value.length : 0;
    let count = 0; 
    let allDisabled = true;

    checkboxes.forEach(cb => {
        if(cb.checked) count++;
        if(!cb.disabled) allDisabled = false;
    });
    selectedCandidatesCount = count;

    const btn = document.getElementById('btnStartPipeline');
    const warning = document.getElementById('pipelineWarningText');
    const estText = document.getElementById('estimatedTimeText');
    const estSpan = document.getElementById('estTimeSpan');
    if (!btn) return;

    if (!allDisabled) {
        let anyUnchecked = false;
        checkboxes.forEach(cb => { if(!cb.checked && !cb.disabled) anyUnchecked = true; });
        document.getElementById('btnSelectAll').innerHTML = anyUnchecked ? '<i class="fa-solid fa-check-double"></i> Select All' : '<i class="fa-regular fa-square"></i> Deselect All';
    }

    btn.className = 'btn btn-sage btn-full btn-lg';

    if (count === 0) {
        btn.disabled = true;
        btn.innerHTML = '<i class="fa-solid fa-paper-plane"></i> Select candidates to start';
        warning.style.display = 'none';
        estText.style.display = 'none';
    } else if (msgLen > 200) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Send Batch Outreach (${count} Selected)`;
        warning.style.display = 'block';
        warning.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Message exceeds LinkedIn's 200 characters limit.`;
        estText.style.display = 'none';
    } else if (invitesSentToday + count > MAX_INVITES) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Send Batch Outreach (${count} Selected)`;
        warning.style.display = 'block';
        warning.innerHTML = `<i class="fa-solid fa-shield"></i> Safety Limit: You can only send ${MAX_INVITES - invitesSentToday} more invites today.`;
        estText.style.display = 'none';
    } else {
        btn.disabled = false;
        btn.innerHTML = `<i class="fa-solid fa-paper-plane"></i> Send Batch Outreach (${count} Selected)`;
        warning.style.display = 'none';
        estSpan.innerText = `~${Math.ceil((count * 12) / 60)} min`;
        estText.style.display = 'block';
    }
}

function updateManualBtn() {
    const msgLen = document.getElementById('inputMessage') ? document.getElementById('inputMessage').value.length : 0;
    const btn = document.getElementById('btnInvite');
    const warningMan = document.getElementById('manualWarningText');
    if(!btn) return;

    if (msgLen > 200) {
        btn.disabled = true;
        warningMan.style.display = 'block';
        warningMan.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> Message exceeds LinkedIn's 200 characters limit.`;
    } else {
        warningMan.style.display = 'none';
        btn.disabled = false;
    }
}

// ── RESTO DE UTILIDADES Y MODALES ──
function insertTagAuto(tag) { insertAtCursor(document.getElementById('outreachMessage'), tag); }
function insertTagManual(tag) { insertAtCursor(document.getElementById('inputMessage'), tag); }
function insertAtCursor(myField, myValue) {
    if(!myField) return;
    if (document.selection) {
        myField.focus(); sel = document.selection.createRange(); sel.text = myValue;
    } else if (myField.selectionStart || myField.selectionStart == '0') {
        var startPos = myField.selectionStart; var endPos = myField.selectionEnd;
        myField.value = myField.value.substring(0, startPos) + myValue + myField.value.substring(endPos, myField.value.length);
        myField.selectionStart = startPos + myValue.length; myField.selectionEnd = startPos + myValue.length;
    } else { myField.value += myValue; }
    myField.dispatchEvent(new Event('input')); myField.focus();
}

function copyDriveLink(type) {
    let url = type === 'jobs' ? document.getElementById('btnOpenDriveJobs').href : document.getElementById('driveLinkAnchor').href;
    if(url && url !== '#' && !url.endsWith('drive.google.com')) {
        navigator.clipboard.writeText(url).then(() => showToast('Link copied!', '<i class="fa-solid fa-copy"></i>', 'var(--sage)'));
    }
}

function playDing() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        const osc = ctx.createOscillator(); const gainNode = ctx.createGain();
        osc.connect(gainNode); gainNode.connect(ctx.destination);
        osc.type = 'sine'; osc.frequency.setValueAtTime(880, ctx.currentTime);
        gainNode.gain.setValueAtTime(0.1, ctx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.00001, ctx.currentTime + 1);
        osc.start(); osc.stop(ctx.currentTime + 1);
    } catch(e) { }
}

function toggleTheme() {
    const isDark = document.body.classList.toggle('dark-theme');
    const icon = document.getElementById('themeIcon'); const text = document.getElementById('themeText');
    if (isDark) {
        localStorage.setItem('aintel_theme', 'dark');
        icon.innerHTML = '<i class="fa-solid fa-sun"></i>'; text.innerText = 'Light Theme';
    } else {
        localStorage.setItem('aintel_theme', 'light');
        icon.innerHTML = '<i class="fa-solid fa-moon"></i>'; text.innerText = 'Obsidian Theme';
    }
}

function switchTab(tabId,btn,activeClass){
  document.querySelectorAll('.tab-content').forEach(el=>el.classList.remove('active'));
  document.getElementById(tabId).classList.add('active');
  document.querySelectorAll('.nav-btn').forEach(b=>b.classList.remove('active','active-sage','active-mauve'));
  if(btn) btn.classList.add(activeClass||'active');
  if(window.innerWidth <= 1024) closeSidebar();
}

function toggleSidebar(){ document.getElementById('sidebar').classList.toggle('open'); document.getElementById('sidebarOverlay').classList.toggle('open'); }
function closeSidebar(){ document.getElementById('sidebar').classList.remove('open'); document.getElementById('sidebarOverlay').classList.remove('open'); }
function toggleDesktopSidebar() { document.getElementById('sidebar').classList.toggle('collapsed'); }

function showToast(msg,iconHtml='<i class="fa-solid fa-check"></i>',color='var(--sage)'){
  const c=document.getElementById('toastContainer');
  const t=document.createElement('div'); t.className='toast';
  t.innerHTML=`<span style="font-size:17px;color:${color};">${iconHtml}</span> ${msg}`;
  c.appendChild(t);
  setTimeout(()=>{t.classList.add('out');setTimeout(()=>t.remove(),300);},3500);
}

function updateCounterUI() {
    document.getElementById('inviteCountTxt').innerText = `${invitesSentToday} / ${MAX_INVITES}`;
    const pct = (invitesSentToday / MAX_INVITES) * 100;
    const bar = document.getElementById('inviteCountBar');
    if(bar) { bar.style.width = `${pct}%`; if (invitesSentToday >= MAX_INVITES) bar.classList.add('danger'); else bar.classList.remove('danger'); }
    document.getElementById('inviteCountTxt').style.color = (invitesSentToday >= MAX_INVITES) ? 'var(--rose-dark)' : 'var(--text-1)';
}

function editCounter() {
    let newVal = prompt("How many invites have you sent manually today?", invitesSentToday);
    if (newVal !== null && !isNaN(newVal)) setCounterBackend(Math.max(0, parseInt(newVal)));
}

function resetCounter() { if (confirm("Reset today's invite counter to 0?")) setCounterBackend(0); }

function setCounterBackend(count) {
    fetch('/api/set_counter', { method: 'POST', headers: {'Content-Type': 'application/json', 'X-API-Token': SYSTEM_TOKEN}, body: JSON.stringify({ count: count }) })
    .then(r => r.json()).then(d => {
        if(d.status === 'success') {
            invitesSentToday = d.invites_today; updateCounterUI(); updateOutreachBtn(); updateManualBtn();
            showToast(`Counter updated to ${count}`, '<i class="fa-solid fa-pen"></i>', 'var(--mauve)');
        }
    });
}
function toggleSelectAll() {
    const checkboxes = document.querySelectorAll('.cand-cb:not([disabled])');
    let anyUnchecked = false; checkboxes.forEach(cb => { if(!cb.checked) anyUnchecked = true; });
    checkboxes.forEach(cb => cb.checked = anyUnchecked);
    document.getElementById('btnSelectAll').innerHTML = anyUnchecked ? '<i class="fa-regular fa-square"></i> Deselect All' : '<i class="fa-solid fa-check-double"></i> Select All';
    updateOutreachBtn();
}

function clearResults(type) {
    if(!confirm("Are you sure you want to clear these results?")) return;
    
    fetch('/api/clear_results', { method: 'POST', headers: {'X-API-Token': SYSTEM_TOKEN} }).then(r => r.json()).then(res => {
        if(res.status === 'success') {
            if(type === 'candidates') {
                localStorage.removeItem(USER_PREFIX + 'aintel_candidates_data');
                localStorage.removeItem(USER_PREFIX + 'aintel_candidates_drive');
                document.getElementById('reviewOutreachPanel').style.display = 'none';
                document.getElementById('emptyCandidates').style.display = 'block';
                document.getElementById('candidateResults').innerHTML = '';
            } else if(type === 'jobs') {
                localStorage.removeItem(USER_PREFIX + 'aintel_jobs_data');
                localStorage.removeItem(USER_PREFIX + 'aintel_jobs_drive');
                document.getElementById('jobResults').innerHTML = '';
                document.getElementById('emptyJobs').style.display = 'block';
                document.getElementById('driveActionsJobs').style.display = 'none';
                document.getElementById('btnClearJobs').style.display = 'none';
            }
            showToast('Results cleared.', '<i class="fa-solid fa-trash"></i>', 'var(--text-3)');
        }
    });
}

function openAISniper(name, url) {
    sniperCurrentName = name; sniperCurrentUrl = url;
    document.getElementById('sniperCandidateName').innerText = `Drafting for ${name.split(" ")[0]}`;
    document.getElementById('sniperLoading').style.display = 'flex'; 
    document.getElementById('sniperContent').style.display = 'none';
    document.getElementById('sniperModal').classList.add('active');

    fetch('/api/analyze_profile', { 
        method: 'POST', 
        headers: {'Content-Type': 'application/json', 'X-API-Token': SYSTEM_TOKEN}, 
        body: JSON.stringify({ name: name, url: url }) 
    })
    .then(r => r.json())
    .then(data => {
        if (data.status === 'accepted' && data.task_id) {
            pollTask('analyze', 'AI Sniper Drafting', (res) => {
                document.getElementById('sniperLoading').style.display = 'none'; 
                document.getElementById('sniperContent').style.display = 'block';
                
                let tabsHtml = '';
                if (res.results && res.results.opciones) {
                    window.sniperOpciones = res.results.opciones;
                    res.results.opciones.forEach((op, index) => { 
                        tabsHtml += `<button class="sniper-tab-btn" onclick="selectSniperOption(${index}, this)">🪄 ${op.enfoque}</button>`; 
                    });
                }
                tabsHtml += `<button class="sniper-tab-btn" onclick="selectSniperOption('default', this)" style="border-color: var(--border-lit); color: var(--text-2);">Default Msg</button>`;
                document.getElementById('sniperTabsArea').innerHTML = tabsHtml;
                
                if (res.results && res.results.opciones) {
                    selectSniperOption(0, document.getElementById('sniperTabsArea').firstElementChild);
                } else {
                    selectSniperOption('default', document.getElementById('sniperTabsArea').lastElementChild);
                }
            });
        } else {
            showToast("Failed to analyze profile.", '<i class="fa-solid fa-triangle-exclamation"></i>', 'var(--peach)'); 
            closeSniperModal();
        }
    }).catch(err => { 
        showToast("Failed to connect with server.", '<i class="fa-solid fa-triangle-exclamation"></i>', 'var(--peach)'); 
        closeSniperModal(); 
    });
}

function selectSniperOption(index, btnElement) {
    document.querySelectorAll('.sniper-tab-btn').forEach(t => t.classList.remove('active'));
    if(btnElement) btnElement.classList.add('active');
    const textArea = document.getElementById('sniperMessageArea');
    if (index === 'default') {
        textArea.value = document.getElementById('outreachMessage').value.replace(/{name}/g, sniperCurrentName.split(" ")[0]);
    } else {
        textArea.value = window.sniperOpciones[index].mensaje;
    }
    textArea.dispatchEvent(new Event('input'));
}

function closeSniperModal() { document.getElementById('sniperModal').classList.remove('active'); }

function sendSniperMessage() {
    const customMsg = document.getElementById('sniperMessageArea').value; closeSniperModal();
    const btn = document.getElementById('btnStartPipeline');
    btn.disabled = true; btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Sending Campaign...';
    showToast(`Sniper Mode: Engaging ${sniperCurrentName}`, '<i class="fa-solid fa-crosshairs"></i>', 'var(--rose)');

    fetch('/api/run_outreach', { method: 'POST', headers: {'Content-Type': 'application/json', 'X-API-Token': SYSTEM_TOKEN}, body: JSON.stringify({ selected_candidates: [sniperCurrentName], message: customMsg }) })
    .then(r => r.json()).then(res => {
        pollTask('outreach', 'Sniper Outreach', () => {
            fetch('/api/stats', { headers: {'X-API-Token': SYSTEM_TOKEN} }).then(r=>r.json()).then(d => { invitesSentToday = d.connections || invitesSentToday; updateCounterUI(); });
            document.querySelectorAll('.cand-cb').forEach(cb => { 
                if(cb.getAttribute('data-name') === sniperCurrentName) {
                    cb.checked = false; cb.disabled = true; cb.parentElement.style.opacity = '0.6';
                    cb.parentElement.querySelector('.candidate-meta').innerHTML += ' <span style="color:var(--sage);"><i class="fa-solid fa-check"></i> Sniper sent</span>';
                }
            });
            updateOutreachBtn();
        });
    });
}

function resetDefaultMessage() {
    const defaultMsg = `Hello {name}, I noticed your tech background. At AIntelligence Research, we help leaders automate processes. Let’s connect and follow our updates for actionable insights. —Ana`;
    const textArea = document.getElementById('outreachMessage'); textArea.value = defaultMsg;
    localStorage.setItem(USER_PREFIX + 'aintel_outreachMessage', defaultMsg); textArea.dispatchEvent(new Event('input'));
    showToast('Message reset to default', '<i class="fa-solid fa-rotate-left"></i>', 'var(--text-2)');
}

function resetManualMessage() {
    const defaultMsg = `Hello {name}, I noticed your tech background. At AIntelligence Research, we help leaders automate processes. Let’s connect and follow our updates for actionable insights. —Ana`;
    const textArea = document.getElementById('inputMessage'); textArea.value = defaultMsg;
    localStorage.setItem(USER_PREFIX + 'aintel_inputMessage', defaultMsg); textArea.dispatchEvent(new Event('input')); 
    showToast('Manual message reset', '<i class="fa-solid fa-rotate-left"></i>', 'var(--text-2)');
}