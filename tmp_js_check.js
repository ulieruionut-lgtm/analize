
// ─── Tab-uri dinamice pacienti ───────────────────────────────────────────────
const _tabPacienti = {};   // { cnp: { nume, html } }
let _tabPacientActiv = null;

function deschideTabPacient(cnp, nume, htmlContent) {
  const baraDinamica = document.getElementById('tabs-dinamice');
  const continutDinamic = document.getElementById('continut-pacienti-dinamici');

  // Verifica atat in cache cat si in DOM (evita duplicate la stergere/reincarca)
  const btnExistent = document.querySelector('.tab-pacient-btn[data-cnp="' + cnp + '"]');

  if (!_tabPacienti[cnp] && !btnExistent) {
    // Tab nou - nu exista nici in cache, nici in DOM
    _tabPacienti[cnp] = { nume, html: htmlContent };

    const btn = document.createElement('button');
    btn.className = 'tab-pacient-btn';
    btn.setAttribute('data-cnp', cnp);
    btn.innerHTML =
      '<span class="tab-nume">👤 ' + escHtml(nume) + '</span>' +
      '<span class="close-tab" title="Inchide">×</span>';

    btn.querySelector('.close-tab').addEventListener('click', function(e) {
      e.stopPropagation();
      inchideTabPacient(cnp);
    });
    btn.addEventListener('click', function() {
      activeazaTabPacient(cnp);
    });
    baraDinamica.appendChild(btn);
    baraDinamica.style.display = 'flex';
  } else {
    // Tab existent - actualizeaza doar continutul si eventual numele
    if (!_tabPacienti[cnp]) _tabPacienti[cnp] = { nume, html: htmlContent };
    else _tabPacienti[cnp].html = htmlContent;

    // Actualizeaza numele daca e mai bun (nu mai e CNP-ul gol)
    if (nume && nume !== cnp) {
      _tabPacienti[cnp].nume = nume;
      const tabBtn = document.querySelector('.tab-pacient-btn[data-cnp="' + cnp + '"]');
      if (tabBtn) {
        const span = tabBtn.querySelector('.tab-nume');
        if (span) span.textContent = '👤 ' + nume;
      }
    }
  }

  activeazaTabPacient(cnp);
}

function activeazaTabPacient(cnp) {
  const continutDinamic = document.getElementById('continut-pacienti-dinamici');

  // Dezactiveaza tab-urile principale
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('activ'));
  document.querySelectorAll('.sectiune').forEach(s => s.classList.remove('activa'));
  document.getElementById('continut-pacienti-dinamici').style.display = '';

  // Marcheaza tab-ul activ
  document.querySelectorAll('.tab-pacient-btn').forEach(b => b.classList.remove('activ'));
  const btn = document.querySelector('.tab-pacient-btn[data-cnp="' + cnp + '"]');
  if (btn) btn.classList.add('activ');

  // Afiseaza continutul
  continutDinamic.innerHTML = _tabPacienti[cnp]?.html || '';
  _tabPacientActiv = cnp;
}

function inchideTabPacient(cnp) {
  const btn = document.querySelector('.tab-pacient-btn[data-cnp="' + cnp + '"]');
  if (btn) btn.remove();
  delete _tabPacienti[cnp];

  const baraDinamica = document.getElementById('tabs-dinamice');
  const continutDinamic = document.getElementById('continut-pacienti-dinamici');
  const tabRamas = Object.keys(_tabPacienti);

  if (tabRamas.length === 0) {
    baraDinamica.style.display = 'none';
    continutDinamic.style.display = 'none';
    continutDinamic.innerHTML = '';
    _tabPacientActiv = null;
    // Revine la tab-ul Pacient
    schimbTab('pacient');
  } else if (_tabPacientActiv === cnp) {
    // Activeaza ultimul tab ramas
    activeazaTabPacient(tabRamas[tabRamas.length - 1]);
  }
}

// ─── Autentificare ───────────────────────────────────────────────────────────
const AUTH_KEY = 'analize_token';

function getToken() { return localStorage.getItem(AUTH_KEY); }
function setToken(t) { localStorage.setItem(AUTH_KEY, t); }
function clearToken() { localStorage.removeItem(AUTH_KEY); }
function getAuthHeaders() {
  const t = getToken();
  return t ? { 'Authorization': 'Bearer ' + t } : {};
}

async function checkAuth() {
  const token = getToken();
  if (!token) { document.getElementById('login-screen').style.display='block'; return; }
  try {
    const r = await fetch('/me', { headers: getAuthHeaders() });
    if (r.ok) {
      const u = await r.json();
      document.getElementById('login-screen').style.display = 'none';
      document.getElementById('app-container').style.display = 'block';
      document.getElementById('user-display').textContent = 'Logat: ' + (u.username || '');
      const btnBackup = document.getElementById('btn-header-backup');
      if (btnBackup) btnBackup.style.display = (u.username || '').toLowerCase() === 'admin' ? 'inline-block' : 'none';
      return;
    }
  } catch {}
  clearToken();
  document.getElementById('login-screen').style.display = 'block';
  document.getElementById('app-container').style.display = 'none';
}

async function doLogin(ev) {
  ev.preventDefault();
  const username = document.getElementById('login-username').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl = document.getElementById('login-err');
  errEl.style.display = 'none';
  try {
    const form = new URLSearchParams();
    form.append('username', username);
    form.append('password', password);
    const r = await fetch('/login', { method: 'POST', body: form, headers: { 'Content-Type': 'application/x-www-form-urlencoded' } });
    const data = await r.json().catch(() => ({}));
    if (r.ok) {
      setToken(data.access_token);
      document.getElementById('login-password').value = '';
      checkAuth();
    } else {
      errEl.textContent = data.detail || 'Eroare la logare';
      errEl.style.display = 'block';
    }
  } catch (e) {
    errEl.textContent = 'Eroare: ' + e.message;
    errEl.style.display = 'block';
  }
  return false;
}

function logout() {
  clearToken();
  document.getElementById('login-screen').style.display = 'block';
  document.getElementById('app-container').style.display = 'none';
}

// ─── Tab Setari ─────────────────────────────────────────────────────────────
async function incarcaSetari() {
  document.getElementById('setari-msg-parola').style.display = 'none';
  document.getElementById('setari-msg-users').style.display = 'none';
  const card = document.getElementById('card-user-management');
  const cardBackup = document.getElementById('card-backup');
  try {
    const r = await fetch('/me', { headers: getAuthHeaders() });
    if (!r.ok) return;
    const u = await r.json();
    if ((u.username || '').toLowerCase() === 'admin') {
      card.style.display = 'block';
      if (cardBackup) cardBackup.style.display = 'block';
      incarcaListaUtilizatori();
    } else {
      card.style.display = 'none';
      if (cardBackup) cardBackup.style.display = 'none';
    }
  } catch { card.style.display = 'none'; if (cardBackup) cardBackup.style.display = 'none'; }
}

async function exportBackup(btnEl) {
  const btns = [
    document.getElementById('btn-export-backup'),
    document.getElementById('btn-header-backup'),
    btnEl || null
  ].filter(Boolean);
  btns.forEach(b => { b.disabled = true; b._txt = b.textContent; b.textContent = 'Se descarcă…'; });
  try {
    const r = await fetch('/api/backup', { headers: getAuthHeaders() });
    if (!r.ok) {
      const j = await r.json().catch(() => ({}));
      alert('Eroare la backup: ' + (j.detail || r.status));
      return;
    }
    const blob = await r.blob();
    const disp = r.headers.get('Content-Disposition');
    let filename = 'analize_backup.json';
    if (disp) {
      const m = disp.match(/filename="?([^";\n]+)"?/);
      if (m) filename = m[1].trim();
    }
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(a.href);
  } catch (e) {
    alert('Eroare: ' + (e.message || ''));
  } finally {
    btns.forEach(b => { b.disabled = false; b.textContent = b._txt || 'Exportă backup'; });
  }
}

async function incarcaListaUtilizatori() {
  const tbody = document.getElementById('lista-utilizatori');
  tbody.innerHTML = '<tr><td colspan="4" style="color:var(--gri)">Se încarcă…</td></tr>';
  try {
    const r = await fetch('/users', { headers: getAuthHeaders() });
    const users = r.ok ? await r.json() : [];
    tbody.innerHTML = '';
    if (!Array.isArray(users) || users.length === 0) {
      tbody.innerHTML = '<tr><td colspan="4" style="color:var(--gri)">Niciun utilizator</td></tr>';
      return;
    }
    users.forEach(u => {
      const d = u.created_at ? (typeof u.created_at === 'string' ? u.created_at.slice(0,10) : '') : '';
      const btn = '<button class="btn btn-secondary" style="padding:4px 8px;font-size:0.8rem" onclick="stergeUtilizator(' + u.id + ')">Șterge</button>';
      tbody.innerHTML += '<tr><td>' + u.id + '</td><td>' + (u.username||'') + '</td><td>' + d + '</td><td>' + btn + '</td></tr>';
    });
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="4" style="color:var(--rosu)">Eroare: ' + (e.message||'') + '</td></tr>';
  }
}

async function schimbaParola() {
  const curr = document.getElementById('setari-parola-curenta').value;
  const noua = document.getElementById('setari-parola-noua').value;
  const conf = document.getElementById('setari-parola-confirma').value;
  const msg = document.getElementById('setari-msg-parola');
  msg.style.display = 'block';
  msg.style.color = 'var(--rosu)';
  if (!curr || !noua || !conf) {
    msg.textContent = 'Completează toate câmpurile.';
    return;
  }
  if (noua.length < 4) {
    msg.textContent = 'Parola nouă trebuie să aibă minim 4 caractere.';
    return;
  }
  if (noua !== conf) {
    msg.textContent = 'Parola nouă și confirmarea nu coincid.';
    return;
  }
  try {
    const r = await fetch('/change-password', {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ current_password: curr, new_password: noua })
    });
    const j = await r.json().catch(() => ({}));
    if (r.ok) {
      msg.style.color = 'var(--verde)';
      msg.textContent = 'Parola a fost actualizată.';
      document.getElementById('setari-parola-curenta').value = '';
      document.getElementById('setari-parola-noua').value = '';
      document.getElementById('setari-parola-confirma').value = '';
    } else {
      msg.textContent = j.detail || 'Eroare la actualizare.';
    }
  } catch (e) {
    msg.textContent = 'Eroare: ' + (e.message || '');
  }
}

async function adaugaUtilizator() {
  const username = document.getElementById('setari-nou-username').value.trim();
  const parola = document.getElementById('setari-nou-parola').value;
  const msg = document.getElementById('setari-msg-users');
  msg.style.display = 'block';
  msg.style.color = 'var(--rosu)';
  if (!username) {
    msg.textContent = 'Introdu username-ul.';
    return;
  }
  if ((parola || '').length < 4) {
    msg.textContent = 'Parola trebuie să aibă minim 4 caractere.';
    return;
  }
  try {
    const r = await fetch('/users', {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password: parola })
    });
    const j = await r.json().catch(() => ({}));
    if (r.ok) {
      msg.style.color = 'var(--verde)';
      msg.textContent = 'Utilizator adăugat.';
      document.getElementById('setari-nou-username').value = '';
      document.getElementById('setari-nou-parola').value = '';
      incarcaListaUtilizatori();
    } else {
      msg.textContent = j.detail || 'Eroare la adăugare.';
    }
  } catch (e) {
    msg.textContent = 'Eroare: ' + (e.message || '');
  }
}

async function stergeUtilizator(id) {
  if (!confirm('Ștergi acest utilizator?')) return;
  try {
    const r = await fetch('/users/' + id, { method: 'DELETE', headers: getAuthHeaders() });
    const j = await r.json().catch(() => ({}));
    if (r.ok) {
      incarcaListaUtilizatori();
      document.getElementById('setari-msg-users').style.display = 'block';
      document.getElementById('setari-msg-users').style.color = 'var(--verde)';
      document.getElementById('setari-msg-users').textContent = 'Utilizator șters.';
    } else {
      document.getElementById('setari-msg-users').style.display = 'block';
      document.getElementById('setari-msg-users').style.color = 'var(--rosu)';
      document.getElementById('setari-msg-users').textContent = j.detail || 'Eroare la ștergere.';
    }
  } catch (e) {
    document.getElementById('setari-msg-users').style.display = 'block';
    document.getElementById('setari-msg-users').style.color = 'var(--rosu)';
    document.getElementById('setari-msg-users').textContent = 'Eroare: ' + (e.message || '');
  }
}

// La incarcare: verifica auth
(async function initAuth() {
  await checkAuth();
})();

// ─── Navigare tab-uri ─────────────────────────────────────────────────────────
function schimbTab(id) {
  document.querySelectorAll('.tab-btn').forEach((b,i) => b.classList.toggle('activ', ['upload','pacient','analiza','alias','setari'][i] === id));
  document.querySelectorAll('.sectiune').forEach(s => s.classList.remove('activa'));
  document.getElementById('tab-' + id).classList.add('activa');
  // Ascunde zona dinamica si dezactiveaza tab-urile de pacienti
  document.getElementById('continut-pacienti-dinamici').style.display = 'none';
  document.querySelectorAll('.tab-pacient-btn').forEach(b => b.classList.remove('activ'));
  _tabPacientActiv = null;
  if (id === 'pacient') incarcaListaPacienti('');
  if (id === 'alias') incarcaNecunoscute();
  if (id === 'setari') incarcaSetari();
  if (id === 'analiza') incarcaAnalizeleStandard();
}

// ─── Upload ──────────────────────────────────────────────────────────────────
const dropZone = document.getElementById('drop-zone');
const fileInput = document.getElementById('file-input');
let fisierSelectat = [];

fileInput.onchange = e => selecteazaFisiere(Array.from(e.target.files));

dropZone.addEventListener('dragover', e => { e.preventDefault(); dropZone.classList.add('drag-over'); });
dropZone.addEventListener('dragleave', () => dropZone.classList.remove('drag-over'));
dropZone.addEventListener('drop', e => {
  e.preventDefault(); dropZone.classList.remove('drag-over');
  selecteazaFisiere(Array.from(e.dataTransfer.files));
});

function selecteazaFisiere(files) {
  if (!files || !files.length) return;
  const pdfs = files.filter(f => f.name.toLowerCase().endsWith('.pdf'));
  const nonPdf = files.length - pdfs.length;
  if (!pdfs.length) {
    afiseazaMesaj('upload-out','eroare','Fișierele trebuie să fie PDF.');
    return;
  }
  fisierSelectat = pdfs;
  const totalKB = pdfs.reduce((s, f) => s + f.size, 0) / 1024;
  let info = pdfs.length === 1
    ? '📎 ' + pdfs[0].name + ' (' + (pdfs[0].size/1024).toFixed(1) + ' KB)'
    : '📎 ' + pdfs.length + ' fișiere selectate (' + totalKB.toFixed(1) + ' KB total)';
  if (nonPdf > 0) info += ' · <span style="color:var(--rosu)">' + nonPdf + ' ignorate (nu sunt PDF)</span>';
  document.getElementById('file-name').innerHTML = info;
  document.getElementById('btn-upload').disabled = false;
  document.getElementById('btn-text').textContent = pdfs.length === 1 ? 'Procesează PDF' : 'Procesează ' + pdfs.length + ' PDF-uri';
  document.getElementById('upload-out').innerHTML = '';
}

async function trimite() {
  if (!fisierSelectat.length) return;
  const btn = document.getElementById('btn-upload');
  const btnText = document.getElementById('btn-text');
  const prog = document.getElementById('prog');
  btn.disabled = true;
  const out = document.getElementById('upload-out');
  out.innerHTML = '';

  const total = fisierSelectat.length;
  let reusit = 0, esuat = 0;
  const rezultate = [];

  for (let i = 0; i < total; i++) {
    const f = fisierSelectat[i];
    btnText.innerHTML = '<span class="spinner"></span> ' + (i+1) + ' / ' + total + '…';
    prog.textContent = f.size > 500000 ? f.name + ' – fișier mare, OCR poate dura 30-60 sec…' : f.name;

    const fd = new FormData();
    fd.append('file', f);
    let status = 'ok', mesaj = '', pacientInfo = null;
    try {
      const r = await fetch('/upload', { method: 'POST', body: fd, headers: getAuthHeaders() });
      const txt = await r.text();
      let j;
      try { j = JSON.parse(txt); } catch {
        // Serverul a returnat non-JSON (ex: 503 la restart) - reincercam o data
        if (r.status === 503 || r.status === 502 || r.status === 504) {
          j = { detail: 'Serverul se restartează (eroare ' + r.status + '). Încearcă din nou în 10-20 secunde.' };
        } else {
          j = { detail: 'Răspuns neașteptat de la server (status ' + r.status + '). Încearcă din nou.' };
        }
      }
      if (r.ok) {
        reusit++;
        pacientInfo = j.pacient || {};
        mesaj = 'Pacient: <strong>' + escHtml(pacientInfo.nume||'') + '</strong>'
          + ' (CNP: ' + escHtml(pacientInfo.cnp||'') + ')'
          + ' · ' + (j.tip_extragere==='ocr'?'🔍 OCR':'📝 text')
          + ' · <strong>' + (j.numar_analize||0) + ' analize</strong>';
      } else {
        esuat++;
        status = 'err';
        mesaj = (j && j.detail) ? (Array.isArray(j.detail) ? j.detail.join(' ') : j.detail) : 'Eroare ' + r.status;
      }
    } catch(err) {
      esuat++;
      status = 'err';
      mesaj = 'Eroare rețea: ' + err.message + '. Verifică conexiunea și încearcă din nou.';
    }
    rezultate.push({ nume: f.name, status, mesaj, pacientInfo });

    // Afișează progresul live
    out.innerHTML = rezultate.map(rz =>
      '<div style="display:flex;gap:10px;align-items:flex-start;padding:8px 0;border-bottom:1px solid var(--border)">' +
        '<span style="font-size:1.1rem">' + (rz.status==='ok' ? '✅' : '❌') + '</span>' +
        '<div style="flex:1;min-width:0">' +
          '<div style="font-weight:500;font-size:0.88rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="' + escHtml(rz.nume) + '">' + escHtml(rz.nume) + '</div>' +
          '<div style="font-size:0.82rem;color:' + (rz.status==='ok'?'var(--verde)':'var(--rosu)') + '">' + rz.mesaj + '</div>' +
        '</div>' +
        (rz.status==='ok' && rz.pacientInfo ? '<button class="btn btn-secondary" style="padding:4px 10px;font-size:0.78rem;white-space:nowrap" onclick="veziPacient(\'' + escHtml(rz.pacientInfo.cnp||'') + '\')">👤 Vezi</button>' : '') +
      '</div>'
    ).join('') +
    (i < total-1 ? '<div style="padding:8px 0;color:var(--gri);font-size:0.83rem">Se procesează fișierul ' + (i+2) + '/' + total + '…</div>' : '');
  }

  // Sumar final
  const sumar = total === 1
    ? (reusit ? '<span style="color:var(--verde)">✅ PDF procesat cu succes.</span>' : '<span style="color:var(--rosu)">❌ Procesare eșuată.</span>')
    : '<strong>' + reusit + '/' + total + ' PDF-uri procesate cu succes' + (esuat ? ' · ' + esuat + ' erori' : '') + '</strong>';
  out.insertAdjacentHTML('afterbegin', '<div style="padding:10px 0 12px;font-size:0.9rem">' + sumar + '</div>');

  incarcaRecenti();
  btn.disabled = false;
  btnText.textContent = total === 1 ? 'Procesează PDF' : 'Procesează ' + total + ' PDF-uri';
  prog.textContent = '';
  fisierSelectat = [];
  document.getElementById('file-name').innerHTML = '';
  fileInput.value = '';
}

async function incarcaRecenti() {
  try {
    const r = await fetch('/pacienti', { headers: getAuthHeaders() });
    const lista = await r.json();
    if (!lista.length) return;
    document.getElementById('card-pacienti-recenti').style.display = '';
    const top5 = lista.slice(0,5);
    document.getElementById('lista-recenti').innerHTML =
      top5.map(p => `<div style="display:flex;justify-content:space-between;align-items:center;padding:8px 0;border-bottom:1px solid var(--border)">
        <span><strong>${escHtml(p.nume||'')}</strong> <span style="color:var(--gri);font-size:0.82rem">CNP: ${escHtml(p.cnp)}</span></span>
        <button class="btn btn-secondary" style="padding:6px 14px;font-size:0.8rem" onclick="veziPacient('${escHtml(p.cnp)}')">Vezi</button>
      </div>`).join('');
  } catch {}
}

// ─── Pacient ─────────────────────────────────────────────────────────────────
let _cautaPacientTimer = null;
function cautaPacient(q) {
  clearTimeout(_cautaPacientTimer);
  _cautaPacientTimer = setTimeout(() => incarcaListaPacienti(q), 320);
}

async function incarcaListaPacienti(q) {
  const el = document.getElementById('lista-pacienti');
  el.innerHTML = '<span style="color:var(--gri);font-size:0.9rem">Se încarcă…</span>';
  try {
    const url = q ? '/pacienti?q=' + encodeURIComponent(q) : '/pacienti';
    const r = await fetch(url, { headers: getAuthHeaders() });
    const lista = await r.json();
    if (!lista.length) {
      el.innerHTML = '<p style="color:var(--gri);text-align:center;padding:20px">Niciun pacient găsit.</p>';
      return;
    }
    el.innerHTML = `<div class="tabel-container"><table>
      <thead><tr><th>Nume</th><th>CNP</th><th>Buletine</th><th>Acțiune</th></tr></thead>
      <tbody>` +
      lista.map(p => `<tr>
        <td><strong>${escHtml(p.nume||'')}</strong>${p.prenume?' <span style="color:var(--gri);font-size:0.82rem">'+escHtml(p.prenume)+'</span>':''}</td>
        <td style="font-family:monospace">${escHtml(p.cnp)}</td>
        <td><span class="badge badge-norm">${p.nr_buletine||0} buletin${p.nr_buletine==1?'':'e'}</span></td>
        <td><button class="btn btn-secondary" style="padding:6px 14px;font-size:0.82rem" onclick="veziPacient('${escHtml(p.cnp)}')">👤 Analize</button></td>
      </tr>`).join('') +
      '</tbody></table></div>';
  } catch(e) {
    el.innerHTML = '<p style="color:red">Eroare: ' + e.message + '</p>';
  }
}

async function veziPacient(cnp) {
  // Daca tab-ul pacientului e deja deschis, doar il activeaza
  if (_tabPacienti[cnp]) {
    activeazaTabPacient(cnp);
    return;
  }

  // Arata placeholder in tab dinamic temporar
  const numeTemporar = cnp;
  deschideTabPacient(cnp, numeTemporar,
    '<div class="card"><p style="color:var(--gri)">Se încarcă datele pacientului…</p></div>');

  try {
    const r = await fetch('/pacient/' + encodeURIComponent(cnp) + '/evolutie-matrice', { headers: getAuthHeaders() });
    if (!r.ok) {
      deschideTabPacient(cnp, cnp,
        '<div class="card"><p style="color:red">Pacientul nu a fost găsit.</p></div>');
      return;
    }

    const data = await r.json();
    const numePacient = (data.pacient.nume||'') + (data.pacient.prenume ? ' ' + data.pacient.prenume : '');
    const initiale = (data.pacient.nume||'?').substring(0,1);

    // Header pacient
    let html = `<div class="card">
      <div class="pacient-header">
        <div class="pacient-avatar">${escHtml(initiale)}</div>
        <div class="pacient-info">
          <h3>${escHtml(data.pacient.nume||'')}${data.pacient.prenume?' '+escHtml(data.pacient.prenume):''}</h3>
          <p>CNP: <strong style="font-family:monospace">${escHtml(data.pacient.cnp)}</strong></p>
          <p>Buletine: <strong>${data.date_buletine.length}</strong> &nbsp;|&nbsp; Analize: <strong>${data.analize.length}</strong></p>
        </div>
        <div style="margin-left:auto">
          <button class="btn" style="background:var(--rosu);color:white;padding:8px 16px;font-size:0.82rem"
            onclick="stergePacient(${data.pacient.id},'${escHtml(data.pacient.nume||'')}','${escHtml(cnp)}')">
            🗑️ Șterge pacient
          </button>
        </div>
      </div>`;

    if (!data.analize.length) {
      html += '<p style="color:var(--gri);padding:20px;text-align:center">Nicio analiză găsită pentru acest pacient.</p></div>';
      deschideTabPacient(cnp, numePacient, html);
      return;
    }

    // Tabel evoluție
    html += '<div class="tabel-evolutie-container"><table class="tabel-evolutie">';

    // Header cu date + butoane editare/stergere buletin
    html += '<thead><tr><th class="col-analiza">Tip Analize / Data</th>';
    data.date_buletine.forEach((d, i) => {
      const bId = data.buletine_ids ? data.buletine_ids[i] : null;
      const editBtn = bId ? `<button onclick="editBuletin(${bId},'${escHtml(cnp)}')" title="Editeaza analizele din acest buletin" style="background:none;border:none;cursor:pointer;color:var(--albastru);font-size:0.75rem;padding:2px 4px">✏️ editează</button>` : '';
      const delBtn = bId ? `<button onclick="stergeBuletin(${bId},'${escHtml(cnp)}')" title="Sterge acest buletin" style="background:none;border:none;cursor:pointer;color:var(--rosu);font-size:0.75rem;padding:2px 4px">🗑️ șterge</button>` : '';
      html += `<th style="white-space:nowrap">${escHtml(d)}<br><span style="display:flex;gap:4px;justify-content:center">${editBtn}${delBtn}</span></th>`;
    });
    html += '</tr></thead><tbody>';

    // Rânduri analize
    data.analize.forEach(a => {
      const titleComplet = a.denumire_standard + (a.unitate ? ' (' + a.unitate + ')' : '');
      html += `<tr><td class="col-analiza" title="${escHtml(titleComplet)}">`;
      html += escHtml(a.denumire_standard);
      if (a.unitate) {
        html += ` <span style="color:var(--gri);font-size:0.85rem;font-weight:400">(${escHtml(a.unitate)})</span>`;
      }
      html += '</td>';
      a.valori.forEach((v, i) => {
        if (v == null) {
          html += '<td style="color:var(--gri)">—</td>';
        } else {
          const flag = a.flags[i] || '';
          if (flag === 'H' || flag === 'L') {
            const cls = flag === 'H' ? 'val-H' : 'val-L';
            html += `<td style="text-align:center"><span class="${cls}">${escHtml(String(v))}</span></td>`;
          } else {
            html += `<td class="val-ok">${escHtml(String(v))}</td>`;
          }
        }
      });
      html += '</tr>';
    });

    html += '</tbody></table></div></div>';
    deschideTabPacient(cnp, numePacient, html);

    // Actualizeaza numele tab-ului cu numele real
    const tabBtn = document.querySelector('.tab-pacient-btn[data-cnp="' + cnp + '"]');
    if (tabBtn) {
      tabBtn.querySelector('.tab-nume').textContent = '👤 ' + (data.pacient.nume||cnp);
    }

  } catch(e) {
    deschideTabPacient(cnp, cnp,
      '<div class="card"><p style="color:red">Eroare: ' + escHtml(e.message) + '</p></div>');
  }
}

function toggleBuletin(id) {
  const el = document.getElementById('buletin-' + id);
  if (el) el.classList.toggle('deschis');
}

async function stergeBuletin(buletinId, cnp) {
  if (!confirm('Ștergi acest buletin cu TOATE analizele din el? Acțiunea nu poate fi anulată!')) return;
  try {
    const r = await fetch('/buletin/' + buletinId, { method: 'DELETE', headers: getAuthHeaders() });
    const j = await r.json().catch(() => ({}));
    if (r.ok) {
      delete _tabPacienti[cnp];
      await veziPacient(cnp);
    } else {
      alert('Eroare: ' + (j.detail || 'Nu s-a putut șterge buletinul.'));
    }
  } catch(e) {
    alert('Eroare: ' + e.message);
  }
}

// ======= EDITARE BULETIN =======
let _editBuletinId = null;
let _editCnp = null;
let _analizeLista = [];

async function editBuletin(buletinId, cnp) {
  _editBuletinId = buletinId;
  _editCnp = cnp;

  // Incarca lista analize standard (pentru dropdown)
  if (!_analizeLista.length) {
    const r = await fetch('/analize-standard', { headers: getAuthHeaders() });
    _analizeLista = r.ok ? await r.json() : [];
  }

  // Incarca rezultatele buletinului
  const r = await fetch('/buletin/' + buletinId + '/rezultate', { headers: getAuthHeaders() });
  if (!r.ok) { alert('Nu s-au putut încărca datele buletinului.'); return; }
  const rezultate = await r.json();

  // Construieste dropdown analize
  let opts = '<option value="">— fara mapare —</option>';
  _analizeLista.forEach(a => {
    opts += `<option value="${a.id}">${escHtml(a.denumire_standard)} (${escHtml(a.cod_standard||'')})</option>`;
  });

  // Construieste tabel rezultate
  let rows = '';
  rezultate.forEach(rz => {
    const selOpts = opts.replace(`value="${rz.analiza_standard_id}"`, `value="${rz.analiza_standard_id}" selected`);
    rows += `<tr id="erow-${rz.id}">
      <td style="min-width:200px">
        <select style="width:100%;font-size:0.8rem;padding:3px" onchange="editField(${rz.id},'analiza_standard_id',this.value||null)">
          ${selOpts}
        </select>
        <div style="font-size:0.72rem;color:var(--gri);margin-top:2px">${escHtml(rz.denumire_raw||'')}</div>
      </td>
      <td><input type="number" step="any" value="${rz.valoare??''}" style="width:80px;padding:3px;font-size:0.85rem"
          onchange="editField(${rz.id},'valoare',parseFloat(this.value)||null)" /></td>
      <td><input type="text" value="${escHtml(rz.unitate||'')}" style="width:60px;padding:3px;font-size:0.85rem"
          onchange="editField(${rz.id},'unitate',this.value)" /></td>
      <td>
        <select style="width:55px;padding:3px;font-size:0.85rem" onchange="editField(${rz.id},'flag',this.value||null)">
          <option value="" ${!rz.flag?'selected':''}>—</option>
          <option value="H" ${rz.flag==='H'?'selected':''}>H</option>
          <option value="L" ${rz.flag==='L'?'selected':''}>L</option>
        </select>
      </td>
      <td>
        <button onclick="stergeRezultat(${rz.id})" style="background:var(--rosu);color:white;border:none;border-radius:4px;padding:3px 8px;cursor:pointer;font-size:0.8rem">✕</button>
      </td>
    </tr>`;
  });

  // Modal
  let modal = document.getElementById('modal-edit-buletin');
  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'modal-edit-buletin';
    modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.55);z-index:1000;display:flex;align-items:flex-start;justify-content:center;padding-top:40px;overflow-y:auto';
    document.body.appendChild(modal);
  }
  modal.innerHTML = `
    <div style="background:white;border-radius:12px;padding:24px;width:min(900px,96vw);max-height:82vh;overflow-y:auto;box-shadow:0 8px 40px rgba(0,0,0,0.25)">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">
        <h3 style="margin:0">✏️ Editare buletin #${buletinId}</h3>
        <button onclick="inchideModalEdit()" style="background:none;border:none;font-size:1.5rem;cursor:pointer;color:var(--gri)">✕</button>
      </div>
      <div id="edit-msg" style="margin-bottom:8px;min-height:20px"></div>
      <div style="overflow-x:auto">
        <table style="width:100%;border-collapse:collapse;font-size:0.85rem">
          <thead><tr style="background:var(--fundal)">
            <th style="padding:8px;text-align:left;border-bottom:2px solid var(--border)">Analiză</th>
            <th style="padding:8px;border-bottom:2px solid var(--border)">Valoare</th>
            <th style="padding:8px;border-bottom:2px solid var(--border)">Unitate</th>
            <th style="padding:8px;border-bottom:2px solid var(--border)">Flag</th>
            <th style="padding:8px;border-bottom:2px solid var(--border)"></th>
          </tr></thead>
          <tbody id="edit-tbody">${rows}</tbody>
        </table>
      </div>
      <div style="margin-top:20px;padding-top:16px;border-top:1px solid var(--border)">
        <strong style="font-size:0.9rem">➕ Adaugă analiză lipsă</strong>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:10px;align-items:flex-end">
          <div style="position:relative">
            <div style="font-size:0.75rem;color:var(--gri);margin-bottom:3px">Tip analiză <span style="color:#aaa">(caută după nume sau cod)</span></div>
            <input type="text" id="new-analiza-search"
              placeholder="🔍 ex: Hemoglobina, TSH, ALT..."
              autocomplete="off"
              style="padding:6px 10px;font-size:0.85rem;min-width:260px;border:1.5px solid #ccc;border-radius:6px;outline:none"
              oninput="filtreazaAnalizeSearch(this.value)"
              onfocus="filtreazaAnalizeSearch(this.value)"
              onblur="setTimeout(()=>ascundeAnalizeSearch(),200)"
            />
            <input type="hidden" id="new-analiza-id" value="" />
            <div id="new-analiza-dropdown"
              style="display:none;position:fixed;z-index:99999;background:white;border:1.5px solid #1a73e8;border-radius:6px;box-shadow:0 6px 24px rgba(0,0,0,0.2);max-height:350px;overflow-y:auto;min-width:320px">
            </div>
          </div>
          <div>
            <div style="font-size:0.75rem;color:var(--gri);margin-bottom:3px">Valoare *</div>
            <input type="number" step="any" id="new-valoare" placeholder="ex: 15.9" style="padding:6px;width:90px;font-size:0.85rem;border:1.5px solid #ccc;border-radius:6px" />
          </div>
          <div>
            <div style="font-size:0.75rem;color:var(--gri);margin-bottom:3px">Unitate</div>
            <input type="text" id="new-unitate" placeholder="ex: g/dL" style="padding:6px;width:80px;font-size:0.85rem;border:1.5px solid #ccc;border-radius:6px" />
          </div>
          <div>
            <div style="font-size:0.75rem;color:var(--gri);margin-bottom:3px">Flag</div>
            <select id="new-flag" style="padding:6px;font-size:0.85rem;border:1.5px solid #ccc;border-radius:6px">
              <option value="">—</option>
              <option value="H">H (Ridicat)</option>
              <option value="L">L (Scăzut)</option>
            </select>
          </div>
          <button id="btn-adauga-rez" onclick="adaugaRezultatNou()" style="background:var(--verde);color:white;border:none;border-radius:6px;padding:7px 16px;cursor:pointer;font-size:0.85rem;font-weight:600">➕ Adaugă în buletin</button>
        </div>
        <div id="edit-msg-add" style="margin-top:10px;padding:8px 12px;border-radius:6px;display:none;font-size:0.9rem"></div>
        <div style="margin-top:6px;font-size:0.78rem;color:#888">⚠️ Apasă <strong>➕ Adaugă în buletin</strong> pentru fiecare analiză nouă, înainte de a da Gata.</div>
      </div>
      <div style="margin-top:20px;text-align:right">
        <button onclick="inchideModalEditSiReincarca()" style="background:var(--albastru);color:white;border:none;border-radius:6px;padding:10px 24px;cursor:pointer;font-size:0.9rem;font-weight:600">✅ Gata — Închide</button>
      </div>
    </div>`;
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';
}

let _editPending = {};  // { rezultat_id: {field: value} }

function editField(rzId, field, value) {
  if (!_editPending[rzId]) _editPending[rzId] = {};
  _editPending[rzId][field] = value;
  // Salveaza automat dupa 600ms (debounce)
  clearTimeout(_editPending[rzId]._timer);
  _editPending[rzId]._timer = setTimeout(() => saveRezultat(rzId), 600);
}

async function saveRezultat(rzId) {
  const changes = _editPending[rzId];
  if (!changes) return;
  const {_timer, ...body} = changes;
  if (Object.keys(body).length === 0) { delete _editPending[rzId]; return; }
  const row = document.getElementById('erow-' + rzId);
  try {
    const r = await fetch('/rezultat/' + rzId, {
      method: 'PUT',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    if (r.ok) {
      if (row) {
        row.style.background = '#e8f5e9';
        setTimeout(() => { if(row) row.style.background = ''; }, 1200);
      }
      delete _editPending[rzId];
    } else {
      const j = await r.json().catch(() => ({}));
      showEditMsg('❌ Eroare salvare: ' + (j.detail || r.status), true);
      if (row) { row.style.background = '#fdecea'; setTimeout(() => { if(row) row.style.background = ''; }, 2000); }
    }
  } catch(e) {
    showEditMsg('❌ Eroare rețea: ' + e.message, true);
    if (row) { row.style.background = '#fdecea'; setTimeout(() => { if(row) row.style.background = ''; }, 2000); }
  }
}

async function stergeRezultat(rzId) {
  if (!confirm('Ștergi această analiză din buletin?')) return;
  const r = await fetch('/rezultat/' + rzId, { method: 'DELETE', headers: getAuthHeaders() });
  if (r.ok) {
    const row = document.getElementById('erow-' + rzId);
    if (row) row.remove();
    showEditMsg('Analiză ștearsă.', false);
  } else {
    showEditMsg('Eroare la ștergere.', true);
  }
}

async function adaugaRezultatNou() {
  const aid = document.getElementById('new-analiza-id').value;
  const val = document.getElementById('new-valoare').value.trim();
  const unit = document.getElementById('new-unitate').value.trim();
  const flag = document.getElementById('new-flag').value;

  if (!val) {
    showAddMsg('⚠️ Introduceți valoarea numerică (ex: 15.9)!', true);
    document.getElementById('new-valoare').focus();
    return;
  }
  if (!aid) {
    showAddMsg('⚠️ Selectați tipul de analiză din lista de mai sus!', true);
    return;
  }

  const btn = document.getElementById('btn-adauga-rez');
  if (btn) { btn.disabled = true; btn.textContent = '⏳ Se salvează...'; }

  try {
    const analiza = _analizeLista.find(a => String(a.id) === String(aid));
    const denumire = analiza ? analiza.denumire_standard : (unit || 'Analiză adăugată manual');

    const body = {
      analiza_standard_id: parseInt(aid),
      denumire_raw: denumire,
      valoare: parseFloat(val.replace(',', '.')),
      unitate: unit || null,
      flag: flag || null,
    };

    const r = await fetch('/buletin/' + _editBuletinId + '/rezultat', {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify(body)
    });
    const j = await r.json().catch(() => ({}));

    if (r.ok) {
      const invatMsg = j.alias_salvat
        ? ' Sistemul a învățat-o și o va recunoaște automat la upload-uri viitoare.'
        : '';
      showAddMsg('✅ ' + escHtml(denumire) + ' (' + val + ' ' + (unit||'') + ') adăugat cu succes!' + invatMsg, false);
      document.getElementById('new-valoare').value = '';
      document.getElementById('new-unitate').value = '';
      document.getElementById('new-flag').value = '';
      document.getElementById('new-analiza-id').value = '';
      const srch = document.getElementById('new-analiza-search');
      if (srch) { srch.value = ''; srch.style.borderColor = '#ccc'; }
    } else {
      showAddMsg('❌ Eroare: ' + (j.detail || 'Nu s-a putut salva. Verifică că ești autentificat.'), true);
    }
  } catch(e) {
    showAddMsg('❌ Eroare rețea: ' + e.message, true);
  } finally {
    if (btn) { btn.disabled = false; btn.textContent = '➕ Adaugă'; }
  }
}

function showAddMsg(msg, isErr) {
  // Mesaj langa butonul de adaugare (vizibil fara scroll)
  const el = document.getElementById('edit-msg-add');
  if (el) {
    el.textContent = msg;
    el.style.display = 'block';
    el.style.background = isErr ? '#fdecea' : '#e8f5e9';
    el.style.color = isErr ? '#c62828' : '#2e7d32';
    el.style.border = '1px solid ' + (isErr ? '#ef9a9a' : '#a5d6a7');
    el.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    // Auto-ascunde dupa 6 secunde daca e succes
    if (!isErr) setTimeout(() => { el.style.display = 'none'; }, 6000);
  }
}

function showEditMsg(msg, isErr) {
  const el = document.getElementById('edit-msg');
  if (el) {
    el.textContent = msg;
    el.style.color = isErr ? 'var(--rosu)' : 'var(--verde)';
  }
}

function filtreazaAnalizeSearch(query) {
  const dropdown = document.getElementById('new-analiza-dropdown');
  const searchInput = document.getElementById('new-analiza-search');
  if (!dropdown || !searchInput) return;
  // Pozitioneaza dropdown fix sub input
  const rect = searchInput.getBoundingClientRect();
  dropdown.style.left = rect.left + 'px';
  dropdown.style.top = (rect.bottom + 2) + 'px';
  dropdown.style.width = rect.width + 'px';
  const q = query.trim().toLowerCase();
  const lista = _analizeLista || [];

  const filtrate = q.length === 0
    ? lista
    : lista.filter(a => {
        const den = (a.denumire_standard || '').toLowerCase();
        const cod = (a.cod_standard || '').toLowerCase();
        return den.includes(q) || cod.includes(q);
      });

  if (filtrate.length === 0) {
    dropdown.innerHTML = '<div style="padding:10px;color:#999;font-size:0.85rem">Niciun rezultat</div>';
  } else {
    dropdown.innerHTML = filtrate.map(a => {
      const den = escHtml(a.denumire_standard || '');
      const cod = escHtml(a.cod_standard || '');
      const qEsc = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const highlight = q ? den.replace(new RegExp(qEsc, 'gi'),
        m => '<mark style="background:#fff176;padding:0">' + m + '</mark>'
      ) : den;
      return '<div' +
        ' data-id="' + a.id + '" data-den="' + den + '" data-cod="' + cod + '"' +
        ' style="padding:8px 12px;cursor:pointer;font-size:0.85rem;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between;align-items:center"' +
        ' onmousedown="selecteazaAnaliza(this.dataset.id, this.dataset.den, this.dataset.cod)"' +
        ' onmouseover="this.style.background=\'#e3f2fd\'"' +
        ' onmouseout="this.style.background=\'\'"' +
        '><span>' + highlight + '</span><span style="color:#999;font-size:0.75rem;margin-left:8px">' + cod + '</span></div>';
    }).join('');
  }
  dropdown.style.display = 'block';
}

function selecteazaAnaliza(id, denumire, cod) {
  const searchEl = document.getElementById('new-analiza-search');
  const hiddenEl = document.getElementById('new-analiza-id');
  const dropdown = document.getElementById('new-analiza-dropdown');
  if (searchEl) {
    searchEl.value = denumire + (cod ? ' (' + cod + ')' : '');
    searchEl.style.borderColor = 'var(--verde)';
  }
  if (hiddenEl) hiddenEl.value = id;
  if (dropdown) dropdown.style.display = 'none';
  // Focus pe valoare
  const valEl = document.getElementById('new-valoare');
  if (valEl) valEl.focus();
}

function ascundeAnalizeSearch() {
  const dropdown = document.getElementById('new-analiza-dropdown');
  if (dropdown) dropdown.style.display = 'none';
}

function inchideModalEdit() {
  const modal = document.getElementById('modal-edit-buletin');
  if (modal) modal.style.display = 'none';
  document.body.style.overflow = '';
  _editPending = {};
}

async function inchideModalEditSiReincarca() {
  // Verifica daca formularul de adaugare are date nesalvate
  const newVal = (document.getElementById('new-valoare') || {}).value || '';
  const newAid = (document.getElementById('new-analiza-id') || {}).value || '';
  if (newVal.trim()) {
    if (newAid) {
      // Salveaza automat analiza din formular
      await adaugaRezultatNou();
      // Asteapta putin sa se proceseze
      await new Promise(res => setTimeout(res, 400));
    } else {
      // Are valoare dar nu are tip selectat
      showAddMsg('⚠️ Ai introdus o valoare dar nu ai selectat tipul de analiză! Caută și selectează tipul din lista de mai sus.', true);
      const srch = document.getElementById('new-analiza-search');
      if (srch) srch.focus();
      return; // Nu inchide modalul
    }
  }

  // Salveaza orice modificari nesalvate din tabel
  for (const rzId of Object.keys(_editPending)) {
    await saveRezultat(parseInt(rzId));
  }
  inchideModalEdit();
  // Reincarca vizualizarea pacientului
  if (_editCnp) {
    delete _tabPacienti[_editCnp];
    await veziPacient(_editCnp);
  }
}

async function stergePacient(pacientId, numePacient, cnp) {
  if (!confirm('Ștergi pacientul "' + numePacient + '" cu TOATE buletinele și analizele lui? Acțiunea nu poate fi anulată!')) return;
  try {
    const r = await fetch('/pacient/' + pacientId, { method: 'DELETE', headers: getAuthHeaders() });
    const j = await r.json().catch(() => ({}));
    if (r.ok) {
      inchideTabPacient(cnp);
      incarcaListaPacienti('');
    } else {
      alert('Eroare: ' + (j.detail || 'Nu s-a putut șterge pacientul.'));
    }
  } catch(e) {
    alert('Eroare: ' + e.message);
  }
}

// ─── Tab 3: Evolutie analiza pentru un pacient ───────────────────────────────
let _pacientAnaliza = null;   // datele pacientului selectat in tab 3

let _cautaAnalizaTimer = null;
function cautaPacientPentruAnaliza(q) {
  clearTimeout(_cautaAnalizaTimer);
  _cautaAnalizaTimer = setTimeout(() => incarcaListaPacientiAnaliza(q), 320);
}

async function incarcaListaPacientiAnaliza(q) {
  const el = document.getElementById('lista-pacienti-analiza');
  if (!q || !q.trim()) { el.innerHTML = ''; return; }
  el.innerHTML = '<span style="color:var(--gri);font-size:0.9rem">Se caută…</span>';
  try {
    const r = await fetch('/pacienti?q=' + encodeURIComponent(q.trim()), { headers: getAuthHeaders() });
    const lista = await r.json();
    if (!lista.length) {
      el.innerHTML = '<p style="color:var(--gri);padding:12px 0">Niciun pacient găsit.</p>';
      return;
    }
    el.innerHTML = '<div class="tabel-container"><table>' +
      '<thead><tr><th>Nume</th><th>CNP</th><th>Buletine</th><th></th></tr></thead><tbody>' +
      lista.map(p => `<tr>
        <td><strong>${escHtml(p.nume||'')}</strong></td>
        <td style="font-family:monospace">${escHtml(p.cnp)}</td>
        <td>${p.nr_buletine||0}</td>
        <td><button class="btn btn-secondary" style="padding:6px 14px;font-size:0.82rem"
            onclick="selecteazaPacientAnaliza('${escHtml(p.cnp)}','${escHtml(p.nume||'')}')">Selectează</button></td>
      </tr>`).join('') +
      '</tbody></table></div>';
  } catch(e) {
    el.innerHTML = '<p style="color:red">' + e.message + '</p>';
  }
}

async function selecteazaPacientAnaliza(cnp, numeDisplay) {
  // Ascunde lista de cautare
  document.getElementById('lista-pacienti-analiza').innerHTML = '';
  document.getElementById('q-analiza-pacient').value = numeDisplay;

  const card = document.getElementById('card-analiza-pacient');
  const header = document.getElementById('pacient-analiza-header');
  const sel = document.getElementById('sel-analiza-pacient');
  const rezult = document.getElementById('rezult-analiza');

  card.style.display = '';
  rezult.innerHTML = '';
  header.innerHTML = '<p style="color:var(--gri);font-size:0.9rem">Se încarcă datele…</p>';

  try {
    const r = await fetch('/pacient/' + encodeURIComponent(cnp), { headers: getAuthHeaders() });
    if (!r.ok) { header.innerHTML = '<p style="color:red">Eroare la încărcare pacient.</p>'; return; }
    _pacientAnaliza = await r.json();

    // Header pacient
    const initiale = (_pacientAnaliza.nume||'?')[0];
    header.innerHTML = `
      <div class="pacient-header" style="margin-bottom:0">
        <div class="pacient-avatar">${escHtml(initiale)}</div>
        <div class="pacient-info">
          <h3>${escHtml(_pacientAnaliza.nume||'')}${_pacientAnaliza.prenume?' '+escHtml(_pacientAnaliza.prenume):''}</h3>
          <p>CNP: <strong style="font-family:monospace">${escHtml(_pacientAnaliza.cnp)}</strong>
          &nbsp;·&nbsp; ${(_pacientAnaliza.buletine||[]).length} buletine în baza de date</p>
        </div>
        <button class="btn btn-secondary" style="margin-left:auto;padding:6px 14px;font-size:0.82rem"
          onclick="resetTabAnaliza()">✕ Schimbă pacientul</button>
      </div>`;

    // Construieste lista de analize unice ale pacientului
    const analize = {};  // denumire_raw -> {list de rezultate}
    (_pacientAnaliza.buletine||[]).forEach(b => {
      (b.rezultate||[]).forEach(rz => {
        const cheie = rz.denumire_standard || rz.denumire_raw || '—';
        if (!analize[cheie]) analize[cheie] = [];
        analize[cheie].push({ ...rz, data_buletin: (b.data_buletin || b.created_at), fisier: b.fisier_original });
      });
    });

    // Populeza selectul cu analizele pacientului
    sel.innerHTML = '<option value="">— Selectați analiza —</option>';
    Object.keys(analize).sort().forEach(k => {
      const o = document.createElement('option');
      o.value = k;
      o.textContent = k + (analize[k].length > 1 ? ' (' + analize[k].length + ' rezultate)' : '');
      sel.appendChild(o);
    });

    // Salveaza harta
    sel._analize = analize;

  } catch(e) {
    header.innerHTML = '<p style="color:red">Eroare: ' + e.message + '</p>';
  }
}

function incarcaEvolPacient() {
  const sel = document.getElementById('sel-analiza-pacient');
  const el = document.getElementById('rezult-analiza');
  const cheie = sel.value;
  const analize = sel._analize || {};

  if (!cheie) { el.innerHTML = ''; return; }

  const lista = analize[cheie] || [];
  if (!lista.length) {
    el.innerHTML = '<p style="color:var(--gri);padding:16px 0">Niciun rezultat găsit.</p>';
    return;
  }

  // Sortare cronologica
  lista.sort((a,b) => (a.data_buletin||'') < (b.data_buletin||'') ? -1 : 1);

  const valori = lista.map(r => r.valoare).filter(v => v!=null);
  const vMin = Math.min(...valori), vMax = Math.max(...valori);
  const intervalRef = lista.find(r => r.interval_min!=null);

  let html = '';

  // Mini-grafic vizual daca sunt multiple valori
  if (valori.length > 1) {
    html += `<div style="margin-bottom:20px;padding:16px;background:var(--gri-deschis);border-radius:10px">
      <p style="font-size:0.82rem;color:var(--gri);margin-bottom:12px">
        Evoluție ${escHtml(cheie)}: min <strong>${Math.min(...valori)}</strong> → max <strong>${Math.max(...valori)}</strong>
        ${intervalRef?' &nbsp;|&nbsp; Interval normal: '+intervalRef.interval_min+' – '+intervalRef.interval_max+' '+escHtml(intervalRef.unitate||''):''}
      </p>
      <div style="display:flex;align-items:flex-end;gap:8px;height:70px">`;
    lista.forEach((r,i) => {
      if (r.valoare == null) return;
      const pct = vMax > vMin ? Math.max(10, ((r.valoare-vMin)/(vMax-vMin))*100) : 60;
      const col = r.flag==='H'?'var(--rosu)':r.flag==='L'?'var(--albastru)':'var(--verde)';
      const data = formatDateOnly(r.data_buletin) || ('Nr.'+(i+1));
      html += `<div style="display:flex;flex-direction:column;align-items:center;flex:1;gap:4px">
        <span style="font-size:0.72rem;font-weight:600;color:${col}">${r.valoare}</span>
        <div style="width:100%;height:${pct}%;background:${col};border-radius:4px 4px 0 0;min-height:6px"></div>
        <span style="font-size:0.68rem;color:var(--gri);text-align:center;white-space:nowrap">${escHtml(data)}</span>
      </div>`;
    });
    html += '</div></div>';
  }

  // Tabel detaliat
  html += `<div class="tabel-container"><table>
    <thead><tr><th>#</th><th>Data buletin</th><th>Fișier</th><th>Valoare</th><th>UM</th><th>Interval ref.</th><th>Status</th></tr></thead><tbody>` +
    lista.map((r,i) => {
      const cls = r.flag==='H'?'val-H':r.flag==='L'?'val-L':'val-ok';
      const badge = r.flag
        ? `<span class="badge badge-${r.flag}">${r.flag==='H'?'↑ Crescut':'↓ Scăzut'}</span>`
        : '<span class="badge badge-norm">Normal</span>';
      const interval = (r.interval_min!=null && r.interval_max!=null)
        ? r.interval_min + ' – ' + r.interval_max : '—';
      const data = formatDateOnly(r.data_buletin) || '—';
      return `<tr>
        <td style="color:var(--gri)">${i+1}</td>
        <td>${data}</td>
        <td style="font-size:0.82rem;color:var(--gri)">${escHtml(r.fisier||'')}</td>
        <td class="${cls}"><strong>${r.valoare!=null?r.valoare:escHtml(r.valoare_text||'—')}</strong></td>
        <td>${escHtml(r.unitate||'')}</td>
        <td style="color:var(--gri)">${interval}</td>
        <td>${badge}</td>
      </tr>`;
    }).join('') +
    '</tbody></table></div>';

  el.innerHTML = html;
}

function resetTabAnaliza() {
  _pacientAnaliza = null;
  document.getElementById('card-analiza-pacient').style.display = 'none';
  document.getElementById('q-analiza-pacient').value = '';
  document.getElementById('lista-pacienti-analiza').innerHTML = '';
  document.getElementById('rezult-analiza').innerHTML = '';
}

// ─── Tab 3b: Gestionare analize standard ─────────────────────────────────────
let _analize_std_toate = [];

async function incarcaAnalizeleStandard() {
  const r = await fetch('/analize-standard', { headers: getAuthHeaders() });
  const lista = await r.json();
  _analize_std_toate = lista;
  document.getElementById('cnt-std').textContent = lista.length;
  afiseazaListaStd(lista);
}

function filtreazaStd(q) {
  const qlow = q.trim().toLowerCase();
  const filtrate = qlow
    ? _analize_std_toate.filter(a =>
        (a.denumire_standard || '').toLowerCase().includes(qlow) ||
        (a.cod_standard || '').toLowerCase().includes(qlow))
    : _analize_std_toate;
  afiseazaListaStd(filtrate);
}

function afiseazaListaStd(lista) {
  const el = document.getElementById('lista-std');
  if (!lista.length) {
    el.innerHTML = '<p style="padding:12px;color:var(--gri)">Niciun rezultat.</p>';
    return;
  }
  el.innerHTML = lista.map(a =>
    '<div style="padding:7px 12px;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between;font-size:0.85rem">' +
    '<span>' + escHtml(a.denumire_standard) + '</span>' +
    '<span style="color:#999;font-family:monospace">' + escHtml(a.cod_standard) + '</span>' +
    '</div>'
  ).join('');
}

async function adaugaAnalizaStandard() {
  const denumire = document.getElementById('new-std-denumire').value.trim();
  const cod = document.getElementById('new-std-cod').value.trim().toUpperCase();
  const msg = document.getElementById('msg-new-std');
  if (!denumire || !cod) {
    msg.textContent = 'Completează denumirea și codul.';
    msg.style.color = 'var(--rosu)';
    return;
  }
  const r = await fetch('/analize-standard', {
    method: 'POST',
    headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ denumire, cod })
  });
  const j = await r.json();
  if (r.ok) {
    msg.textContent = 'Adăugat: ' + j.denumire_standard + ' (' + j.cod_standard + ')';
    msg.style.color = 'var(--verde)';
    document.getElementById('new-std-denumire').value = '';
    document.getElementById('new-std-cod').value = '';
    await incarcaAnalizeleStandard();
    // Reincarca si lista din dropdown editare
    _analizeLista = null;
    incarcaAnalizeLista();
  } else {
    msg.textContent = j.detail || 'Eroare.';
    msg.style.color = 'var(--rosu)';
  }
  setTimeout(() => { msg.textContent = ''; }, 4000);
}

// ─── Tab 4: Analize necunoscute ───────────────────────────────────────────────
let _analize_std_cache = null;

async function incarcaStandardeCache() {
  if (_analize_std_cache) return _analize_std_cache;
  try {
    const r = await fetch('/analize-standard', { headers: getAuthHeaders() });
    _analize_std_cache = await r.json();
  } catch { _analize_std_cache = []; }
  return _analize_std_cache;
}

async function incarcaNecunoscute() {
  const el = document.getElementById('lista-necunoscute');
  el.innerHTML = '<p style="color:var(--gri)">Se încarcă…</p>';
  try {
    const [nec, std] = await Promise.all([
      fetch('/analize-necunoscute', { headers: getAuthHeaders() }).then(r => r.json()),
      incarcaStandardeCache()
    ]);

    // Actualizeaza badge
    const badge = document.getElementById('badge-nec');
    if (nec.length > 0) {
      badge.textContent = nec.length;
      badge.style.display = '';
    } else {
      badge.style.display = 'none';
    }

    if (!nec.length) {
      el.innerHTML = '<div class="mesaj succes"><strong>✅ Toate analizele sunt recunoscute!</strong><br>Nicio analiză necunoscută în baza de date.</div>';
      return;
    }

    // Construieste optiunile pentru select
    const optStd = std.map(s => `<option value="${s.id}">${escHtml(s.denumire_standard)} (${escHtml(s.cod_standard)})</option>`).join('');

    el.innerHTML = `
      <p style="font-size:0.85rem;color:var(--gri);margin-bottom:12px">
        ${nec.length} analize nerecunoscute. Asociați-le cu analiza standard corectă:
      </p>
      <div class="tabel-container"><table>
      <thead><tr>
        <th>Denumire din PDF</th>
        <th>Apariții</th>
        <th>Asociază cu analiza standard</th>
        <th>Acțiuni</th>
      </tr></thead>
      <tbody>` +
      nec.map(n => `<tr id="nec-row-${n.id}">
        <td>
          <strong>${escHtml(n.denumire_raw)}</strong>
          <div style="font-size:0.75rem;color:var(--gri);margin-top:2px">Prima apariție: ${(n.created_at||'').substring(0,10)}</div>
        </td>
        <td><span class="badge badge-norm">${n.aparitii}×</span></td>
        <td>
          <select id="sel-std-${n.id}" style="width:100%;padding:6px 10px;border:1px solid var(--border);border-radius:6px;font-size:0.85rem">
            <option value="">— Selectați —</option>
            ${optStd}
          </select>
        </td>
        <td style="white-space:nowrap">
          <button class="btn btn-primary" style="padding:6px 12px;font-size:0.82rem;margin-right:4px"
            onclick="aprobaAlias(${n.id}, '${escHtml(n.denumire_raw).replace(/'/g,"\\'")}')">✓ Asociază</button>
          <button class="btn btn-secondary" style="padding:6px 10px;font-size:0.82rem"
            title="Șterge (zgomot / artefact OCR)"
            onclick="stergeNecunoscuta(${n.id})">🗑</button>
        </td>
      </tr>`).join('') +
      '</tbody></table></div>';

  } catch(e) {
    el.innerHTML = '<p style="color:red">Eroare: ' + e.message + '</p>';
  }
}

async function aprobaAlias(id, denumireRaw) {
  const sel = document.getElementById('sel-std-' + id);
  const aid = sel ? sel.value : '';
  if (!aid) { alert('Selectați mai întâi analiza standard!'); return; }

  try {
    const r = await fetch('/aproba-alias', {
      method: 'POST',
      headers: { ...getAuthHeaders(), 'Content-Type': 'application/json' },
      body: JSON.stringify({ denumire_raw: denumireRaw, analiza_standard_id: parseInt(aid) })
    });
    const j = await r.json();
    if (r.ok) {
      const row = document.getElementById('nec-row-' + id);
      if (row) {
        row.innerHTML = `<td colspan="4">
          <span style="color:var(--verde)">✅ <strong>${escHtml(denumireRaw)}</strong> a fost asociat cu succes. Toate rezultatele existente au fost actualizate și va fi recunoscut automat la orice upload viitor.</span>
        </td>`;
      }
      // Actualizeaza badge
      const badge = document.getElementById('badge-nec');
      const cnt = parseInt(badge.textContent||'0') - 1;
      if (cnt > 0) { badge.textContent = cnt; } else { badge.style.display = 'none'; }
    } else {
      alert('Eroare: ' + (j.detail || 'Necunoscut'));
    }
  } catch(e) {
    alert('Eroare rețea: ' + e.message);
  }
}

async function stergeNecunoscuta(id) {
  if (!confirm('Ștergeți această intrare? (Ex: artefact OCR, nu este o analiză reală)')) return;
  try {
    await fetch('/analiza-necunoscuta/' + id, { method: 'DELETE', headers: getAuthHeaders() });
    const row = document.getElementById('nec-row-' + id);
    if (row) row.remove();
    const badge = document.getElementById('badge-nec');
    const cnt = parseInt(badge.textContent||'0') - 1;
    if (cnt > 0) { badge.textContent = cnt; } else { badge.style.display = 'none'; }
  } catch(e) {
    alert('Eroare: ' + e.message);
  }
}

// ─── Util ─────────────────────────────────────────────────────────────────────
function formatDateOnly(s) {
  if (!s) return '';
  const txt = String(s).trim();
  // DD.MM.YYYY (+ optional time)
  let m = txt.match(/(\d{2})[./-](\d{2})[./-](\d{4})/);
  if (m) return `${m[1]}.${m[2]}.${m[3]}`;
  // YYYY-MM-DD / YYYY.MM.DD
  m = txt.match(/(\d{4})[./-](\d{2})[./-](\d{2})/);
  if (m) return `${m[3]}.${m[2]}.${m[1]}`;
  // ISO datetime fallback
  if (txt.includes('T') && txt.length >= 10) {
    const iso = txt.substring(0, 10);
    const p = iso.split('-');
    if (p.length === 3) return `${p[2]}.${p[1]}.${p[0]}`;
    return iso;
  }
  return txt.substring(0, 10);
}

function escHtml(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function afiseazaMesaj(containerId, tip, html) {
  document.getElementById(containerId).innerHTML = `<div class="mesaj ${tip}">${html}</div>`;
}

// La incarcare initiala
incarcaRecenti();
// Verifica daca exista analize necunoscute si actualizeaza badge
(async () => {
  try {
    const r = await fetch('/analize-necunoscute', { headers: getAuthHeaders() });
    const lista = await r.json();
    const badge = document.getElementById('badge-nec');
    if (lista.length > 0) { badge.textContent = lista.length; badge.style.display = ''; }
  } catch {}
})();
