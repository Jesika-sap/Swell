/* Swell web app. Talks to the Python API (backend/app.py).
   Sections: helpers · state · API · onboarding · plan · checklist · help · map + reports · news · boot */
'use strict';

const CFG = window.APP_CONFIG || { name: 'Swell', apiBase: '' };
const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => Array.from(r.querySelectorAll(s));
const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
const ICON = {
  check: '<path d="M5 12.5l4.5 4.5L19 7.5"/>',
  warn: '<path d="M12 3l9 16H3z"/><path d="M12 10v4M12 17h.01"/>',
  ok: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l3 3 5-6"/>',
  home: '<path d="M4 11l8-7 8 7v9H4z"/>',
  bag: '<path d="M6 8h12l-1 12H7z"/><path d="M9 8a3 3 0 0 1 6 0"/>',
  drop: '<path d="M12 3s6 6.5 6 11a6 6 0 0 1-12 0c0-4.5 6-11 6-11z"/>',
  phone: '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a1 1 0 0 1-1 1A16 16 0 0 1 4 5a1 1 0 0 1 1-1z"/>',
  camera: '<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>',
  spark: '<path d="M12 3l1.8 4.2L18 9l-4.2 1.8L12 15l-1.8-4.2L6 9l4.2-1.8z"/>'
};
const icon = (k) => `<svg viewBox="0 0 24 24" aria-hidden="true">${ICON[k] || ''}</svg>`;

let toastT;
function toast(msg, ms = 3200) {
  const t = $('#toast');
  t.textContent = msg; t.hidden = false;
  clearTimeout(toastT); toastT = setTimeout(() => { t.hidden = true; }, ms);
}
function fmtDay(iso, opts = { month: 'short', day: 'numeric' }) {
  if (!iso) return '';
  return new Date(iso.length === 10 ? iso + 'T12:00:00' : iso).toLocaleDateString(undefined, opts);
}

/* ---------------- state (this device only) ---------------- */
const STORE = 'swell.v1';
function load() {
  try { return JSON.parse(localStorage.getItem(STORE)) || {}; } catch (e) { return {}; }
}
const state = Object.assign({ deviceId: '', language: 'en', current: null, cached: null }, load());
function save() { try { localStorage.setItem(STORE, JSON.stringify(state)); } catch (e) { /* private mode */ } }
if (!state.deviceId) {
  state.deviceId = (crypto.randomUUID ? crypto.randomUUID() : 'd-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 12));
  save();
}
let plan = state.cached || null;

/* ---------------- API ---------------- */
async function api(path, opts = {}) {
  const res = await fetch((CFG.apiBase || '') + path, {
    method: opts.method || 'GET',
    headers: { 'Content-Type': 'application/json', 'X-Device-Id': state.deviceId },
    body: opts.body ? JSON.stringify(opts.body) : undefined
  });
  let data = null;
  try { data = await res.json(); } catch (e) { /* not JSON */ }
  if (!res.ok) throw new Error((data && data.error) || `Server error (${res.status})`);
  return data;
}

/* ---------------- onboarding ---------------- */
const LANGS = [['en', 'English'], ['es', 'Español'], ['ne', 'नेपाली (Nepali)'], ['zh', '中文 (Chinese)'], ['tl', 'Tagalog'],
  ['vi', 'Tiếng Việt'], ['ko', '한국어 (Korean)'], ['hi', 'हिन्दी (Hindi)'], ['ar', 'العربية (Arabic)'], ['ru', 'Русский']];
const HOUSEHOLD = [
  ['kids', 'Kids', 'Under 18', '<circle cx="12" cy="7" r="3"/><path d="M7 21v-5a5 5 0 0 1 10 0v5"/>'],
  ['older_adult', 'Older adult', '65 or older', '<circle cx="11" cy="5" r="2.5"/><path d="M11 8v6l-3 7M11 14l3 7M15 11l2 10"/>'],
  ['disability', 'Disability or health need', 'Mobility, vision, hearing, chronic illness', '<circle cx="12" cy="5" r="2"/><path d="M10 9h4v5h-4zM12 14v7M8 21a5 5 0 0 0 8-6"/>'],
  ['medical_device', 'Powered medical device', 'Oxygen, CPAP, dialysis...', '<path d="M12 3v4M8 7h8l-1 13H9z"/><path d="M10 12h4M12 10v4"/>'],
  ['pets', 'Pets', 'Dogs, cats, others', '<circle cx="7" cy="9" r="2"/><circle cx="17" cy="9" r="2"/><circle cx="10" cy="5" r="2"/><circle cx="14" cy="5" r="2"/><path d="M8 17a4 4 0 0 1 8 0c0 2-2 3-4 3s-4-1-4-3z"/>'],
  ['no_car', 'No car', 'Would need a ride to leave', '<path d="M5 13l2-5h10l2 5v5H5z"/><path d="M3 3l18 18"/>'],
  ['renter', 'We rent', 'Apartment or house', '<path d="M4 21V9l8-6 8 6v12"/><path d="M9 21v-6h6v6"/>'],
  ['lives_alone', 'Lives alone', 'Nobody else at home', '<circle cx="12" cy="8" r="3.5"/><path d="M5 21a7 7 0 0 1 14 0"/>'],
  ['hillside', 'On a hillside', 'Or below a slope', '<path d="M3 20l7-11 4 6 2-3 5 8z"/>']
];
const household = {};
let pendingPlace = null;
let role = 'household';
const farm = { grows: [], workers: false, creek: false };
const FARM_GROWS = [['vegetables', 'Vegetables'], ['field', 'Grains or field crops'], ['orchard', 'Orchards or vineyards'], ['livestock', 'Animals or poultry'], ['nursery', 'Flowers or nursery']];
const FARM_MORE = [['workers', 'I have farmworkers'], ['creek', 'Fields near a creek or low ground']];

function obShow(n) {
  $$('.ob-step').forEach((s) => { s.hidden = s.dataset.step !== String(n); });
  window.scrollTo(0, 0);
}
function showOnboard(step = 1) {
  $('#onboard').hidden = false;
  ['#topbar', '#main', '#tabbar'].forEach((s) => { $(s).hidden = true; });
  obShow(step);
}
function showApp() {
  $('#onboard').hidden = true;
  ['#topbar', '#main', '#tabbar'].forEach((s) => { $(s).hidden = false; });
}

$('#obFacts').innerHTML = [
  ['83%+', 'chance of a strong to very strong El Niño this winter', 'NOAA Climate Prediction Center, Oct 2026'],
  ['2–7 yrs', 'how often El Niño comes back, bringing floods to some places and drought to others', 'NOAA'],
  ['$5.7T', 'lost by the world economy after the last very strong El Niño, in 1997–98', 'Callahan & Mankin, Science, 2023']
].map(([b, t, s]) => `<div class="fact"><b>${b}</b><span>${t}<small>${s}</small></span></div>`).join('');
$('#langSelect').innerHTML = LANGS.map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('');
$('#langSelect').value = state.language;
$('#langSelect').addEventListener('change', (e) => { state.language = e.target.value; save(); });
$('#obStart').addEventListener('click', () => obShow(state.account ? 2 : 9));
$$('[data-role]').forEach((b) => b.addEventListener('click', () => { role = b.dataset.role; obShow(3); }));
$('#farmPick').innerHTML = FARM_GROWS.map(([k, t]) => `<button class="pick" type="button" data-grow="${k}" aria-pressed="false"><strong>${esc(t)}</strong></button>`).join('');
$('#farmMore').innerHTML = FARM_MORE.map(([k, t]) => `<button class="pick" type="button" data-farm="${k}" aria-pressed="false"><strong>${esc(t)}</strong></button>`).join('');
$$('[data-grow]').forEach((b) => b.addEventListener('click', () => {
  const k = b.dataset.grow, i = farm.grows.indexOf(k);
  if (i >= 0) farm.grows.splice(i, 1); else farm.grows.push(k);
  b.setAttribute('aria-pressed', String(i < 0));
}));
$$('[data-farm]').forEach((b) => b.addEventListener('click', () => { farm[b.dataset.farm] = !farm[b.dataset.farm]; b.setAttribute('aria-pressed', String(farm[b.dataset.farm])); }));
$('#farmNext').addEventListener('click', () => obShow(5));
$('#hhBack').addEventListener('click', () => obShow(role === 'farmer' ? 4 : 3));
const afterPlace = () => obShow(role === 'farmer' ? 4 : 5);
$$('[data-ob-back]').forEach((b) => b.addEventListener('click', () => obShow(b.dataset.obBack)));
$('#householdPick').innerHTML = HOUSEHOLD.map(([k, t, s, svg]) =>
  `<button class="pick" type="button" data-hh="${k}" aria-pressed="false"><svg viewBox="0 0 24 24" aria-hidden="true">${svg}</svg><strong>${esc(t)}</strong><small>${esc(s)}</small></button>`).join('');
$$('[data-hh]').forEach((b) => b.addEventListener('click', () => {
  household[b.dataset.hh] = !household[b.dataset.hh];
  b.setAttribute('aria-pressed', String(household[b.dataset.hh]));
}));

$('#addrForm').addEventListener('submit', (e) => {
  e.preventDefault();
  const v = $('#addrInput').value.trim();
  if (v.length < 5) { toast('Type your full address, with the city.'); return; }
  pendingPlace = { address: v };
  afterPlace();
});
$('#useLocation').addEventListener('click', () => {
  if (!navigator.geolocation) { toast('Location isn’t available here. Type your address instead.'); return; }
  const b = $('#useLocation');
  b.disabled = true;
  navigator.geolocation.getCurrentPosition((pos) => {
    b.disabled = false;
    pendingPlace = { lat: pos.coords.latitude, lon: pos.coords.longitude };
    afterPlace();
  }, () => { b.disabled = false; toast('Couldn’t get your location. Type your address instead.'); }, { enableHighAccuracy: true, timeout: 12000 });
});

const BUILD_STEPS = [
  ['Finding your address', 'U.S. Census Geocoder'],
  ['Checking the official flood map', 'FEMA National Flood Hazard Layer'],
  ['Measuring how high your ground is', 'USGS elevation data'],
  ['Checking live weather alerts', 'National Weather Service'],
  ['Finding sandbags and help nearby', 'County and city sources'],
  ['Writing your checklist', 'Made for your household']
];
$('#buildPlan').addEventListener('click', async () => {
  if (!pendingPlace) { obShow(3); return; }
  obShow(6);
  const steps = BUILD_STEPS.slice();
  if (state.language !== 'en') steps[5] = ['Writing your checklist', `In ${LANGS.find((l) => l[0] === state.language)[1]}`];
  if (role === 'farmer') steps.splice(5, 0, ['Adding steps for your farm', 'Crops, animals, workers and records']);
  $('#buildSteps').innerHTML = steps.map(([t, s]) => `<li><span class="dot"></span><span>${esc(t)}<small>${esc(s)}</small></span></li>`).join('');
  const lis = $$('#buildSteps li');
  let i = 0;
  const tick = setInterval(() => { if (i < lis.length - 1) { lis[i].classList.add('on'); lis[i].querySelector('.dot').innerHTML = icon('check'); i++; } }, 650);
  try {
    const p = await api('/api/plan', { method: 'POST', body: { ...pendingPlace, language: state.language, household, role, farm, label: $('#labelInput').value.trim() || (role === 'farmer' ? 'My farm' : 'Home') } });
    clearInterval(tick);
    lis.forEach((li) => { li.classList.add('on'); li.querySelector('.dot').innerHTML = icon('check'); });
    await new Promise((r) => setTimeout(r, 450));
    setPlan(p);
    showApp();
    switchView('plan');
  } catch (err) {
    clearInterval(tick);
    obShow(3);
    toast(err.message, 5000);
  }
});

/* ---------------- plan ---------------- */
function setPlan(p) {
  plan = p;
  state.current = p.id;
  state.cached = p;
  save();
  $('#placeName').textContent = [p.label, p.place.city].filter(Boolean).filter((x, i, a) => a.indexOf(x) === i).join(' · ') || 'Home';
  renderAll();
}
function renderAll() {
  renderPlan(); renderList(); renderHelp();
  if (currentView === 'map') renderMap();
  if (currentView === 'community') renderCommunity();
  if (currentView === 'news') renderNews();
}
const LEVEL_TEXT = { high: 'High risk', elevated: 'Elevated risk', lower: 'Lower risk' };
const LEVEL_COLOR = { high: '#ff8a73', elevated: '#ffc061', lower: '#63d69b' };

function gaugeHTML(score, level) {
  const c = 2 * Math.PI * 42;
  return `<div class="gauge"><svg viewBox="0 0 104 104"><circle class="track" cx="52" cy="52" r="42"/><circle class="val" cx="52" cy="52" r="42" stroke="${LEVEL_COLOR[level]}" stroke-dasharray="${c}" stroke-dashoffset="${c}" data-target="${c * (1 - score / 100)}"/></svg><b>${score}</b><small>out of 100</small></div>`;
}
function ringHTML(done, total) {
  const c = 2 * Math.PI * 24;
  return `<div class="ring"><svg viewBox="0 0 58 58"><circle class="track" cx="29" cy="29" r="24"/><circle class="val" cx="29" cy="29" r="24" stroke-dasharray="${c}" stroke-dashoffset="${c * (1 - (total ? done / total : 0))}"/></svg><b>${done}/${total}</b></div>`;
}
function alertHTML(a) {
  return `<div class="alert alert-${a.kind}">${icon('warn')}<div><strong>${esc(a.event)}</strong><p>${esc(a.headline)}</p>
    ${a.instruction || a.description ? `<details><summary>What to do</summary><p>${esc(a.instruction || a.description)}</p></details>` : ''}
    <p class="src">National Weather Service</p></div></div>`;
}
function taskHTML(t) {
  return `<li class="task ${t.done ? 'done' : ''}" data-task="${esc(t.id)}">
    <button class="box" type="button" aria-label="${t.done ? 'Mark not done' : 'Mark done'}: ${esc(t.title)}" aria-pressed="${t.done}">${icon('check')}</button>
    <div>${t.source === 'scan' ? '<span class="from-scan">From your photo</span>' : ''}${t.priority === 1 && !t.done ? '<span class="first">Do first</span>' : ''}<strong>${esc(t.title)}</strong><p>${esc(t.why)}</p>
    ${t.link ? `<a href="${esc(t.link)}" target="_blank" rel="noopener">Open link</a>` : ''}</div></li>`;
}

function renderPlan() {
  const page = $('#planPage');
  if (!plan) { page.innerHTML = ''; return; }
  const r = plan.risk;
  const intl = plan.place.country && plan.place.country !== 'US';
  const placeLine = intl ? [plan.place.city, plan.place.county, plan.place.country].filter(Boolean).join(', ')
    : [plan.place.city, plan.place.county ? `${plan.place.county} County` : null, plan.place.state].filter(Boolean).join(', ');
  const hazard = r.hazard || 'flood';
  const reg = r.region;
  const storm = (plan.alerts || []).filter((a) => a.storm_related);
  const next = plan.checklist.filter((t) => !t.done).slice(0, 3);
  const tides = r.king_tides || [];
  const langName = (LANGS.find((l) => l[0] === plan.language) || [])[1];
  page.innerHTML = `
    <section class="risk">
      <div class="risk-top">
        ${gaugeHTML(r.score, r.level)}
        <div>
          <div class="risk-tags"><span class="risk-level lv-${r.level}">${LEVEL_TEXT[r.level]}</span>${plan.role === 'farmer' ? '<span class="risk-tag">Farm plan</span>' : ''}<span class="risk-tag">${hazard === 'drought' ? 'Drought and heat' : 'Floods and storms'}</span></div>
          <h2>El Niño risk for ${esc(plan.label || 'this home')}</h2>
          <p class="risk-place">${esc(placeLine)}</p>
        </div>
      </div>
      <p class="risk-summary">${esc(plan.summary)}</p>
      ${plan.translated ? `<span class="risk-lang">Plan written in ${esc(langName)}</span>` : (plan.language && plan.language !== 'en' && (plan.missing || []).includes('ai') ? `<span class="risk-lang">Couldn’t translate this plan right now, so it’s in English. Make the plan again in a minute.</span>` : '')}
    </section>

    ${intl ? (reg ? `<section class="card region-card block"><p class="eyebrow">What El Niño usually does here</p><h3>${esc(reg.name)}</h3><span class="effect ${/wet/.test(reg.effect) ? 'eff-wet' : 'eff-dry'}">${esc(reg.effect)} · ${esc(reg.season)}</span><p class="small" style="margin:0">Live alerts and flood maps are U.S.-only for now. Follow your national weather office for warnings.</p></section>` : '')
      : storm.length ? storm.map(alertHTML).join('') : `<div class="alert alert-none">${icon('ok')}<div><strong>No storm alerts right now</strong><p>We check the National Weather Service every time you open the app.</p></div></div>`}

    <section class="block card scan-card">
      <div class="scan-ic">${icon('camera')}</div>
      <div><h3>AI Scan</h3><p class="small" style="margin:2px 0 0">Take a photo of your ${plan.role === 'farmer' ? 'field, barn or equipment' : 'home, yard or street'}. AI spots risks you can fix and adds them to your checklist.</p></div>
      <button class="btn btn-primary" type="button" id="scanBtn">Scan a photo</button>
    </section>

    <section class="block card">
      <div class="progress-row">
        ${ringHTML(plan.progress.done, plan.progress.total)}
        <div><h3>${plan.progress.done ? 'Keep going' : 'Start here'}</h3><p class="muted small" style="margin:2px 0 0">${plan.progress.done} of ${plan.progress.total} steps done</p></div>
      </div>
      <ul class="tasks next-tasks" style="margin-top:12px">${next.map(taskHTML).join('')}</ul>
      <button class="btn btn-ghost btn-wide" type="button" data-go="list">See the full checklist</button>
    </section>

    <section class="block">
      <div class="section-head"><h3>Why this score</h3><span class="muted small">Every point has a source</span></div>
      <ul class="factors card">${r.factors.map((f) => `<li><span class="pts ${f.points >= 25 ? 'hot' : f.points >= 10 ? 'warm' : ''}">+${f.points}</span><div><strong>${esc(f.label)}</strong><p>${esc(f.detail)}</p><small>${esc(f.source)}</small></div></li>`).join('')}</ul>
      ${plan.missing && plan.missing.length ? `<p class="fineprint">Couldn’t reach: ${esc(plan.missing.map((m) => m === 'ai' ? 'AI translation' : m).join(', '))}. Pull to refresh later.</p>` : ''}
    </section>

    ${plan.forecast && plan.forecast.length ? `<section class="block">
      <div class="section-head"><h3>Next few days</h3><span class="muted small">${esc(plan.rain ? plan.rain.summary : '')}</span></div>
      <div class="fc">${plan.forecast.map((p) => `<div class="${p.rain_chance >= 50 ? 'wet' : ''}"><b>${esc(p.name)}</b><span>${esc(p.short)}</span><span class="rain">${p.rain_chance}% rain</span></div>`).join('')}</div>
    </section>` : ''}

    ${tides.length ? `<section class="block">
      <div class="section-head"><h3>King tides</h3><span class="muted small">Extra-high tides</span></div>
      <div class="tides">${tides.map((w) => `<div class="tide ${w.active ? 'active' : ''}"><b>${esc(fmtDay(w.start))}–${esc(fmtDay(w.end, { day: 'numeric' }))}</b><span>${w.active ? 'Happening now' : fmtDay(w.start, { year: 'numeric' })}</span></div>`).join('')}</div>
      <p class="fineprint">Low streets near the Bay can flood even on sunny days. Source: San Mateo County Parks.</p>
    </section>` : ''}

    <section class="block card enso-card">
      <p class="eyebrow">El Niño 2026–27</p>
      <h3>${esc(plan.enso.status)}</h3>
      <p class="small" style="margin:0">${esc(plan.enso.detail)}</p>
      <ul class="events">${plan.enso.events.map((e) => `<li>${esc(e.text)}<small>${esc(fmtDay(e.date, { month: 'long', day: 'numeric', year: 'numeric' }))} · <a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.source)}</a></small></li>`).join('')}</ul>
    </section>
    <p class="fineprint center">This plan helps you prepare. In an emergency, follow official orders and call 911.</p>`;
  requestAnimationFrame(() => $$('.gauge .val', page).forEach((c) => { c.style.strokeDashoffset = c.dataset.target; }));
  bindTasks(page);
  $$('[data-go]', page).forEach((b) => b.addEventListener('click', () => switchView(b.dataset.go)));
  $('#scanBtn').addEventListener('click', openScan);
}

function openScan() {
  openSheet(`<h2 id="sheetTitle">AI Scan</h2>
    <p class="muted small">Point your camera at a ${plan.role === 'farmer' ? 'field, ditch, barn or equipment' : 'front door, gutter, yard, garage or the street outside'}. The AI only reports what it can see. Photos aren’t saved.</p>
    <label class="photo-drop" id="scanDrop"><input type="file" id="scanFile" accept="image/*" capture="environment">${icon('camera')}<strong>Take or choose a photo</strong></label>
    <img class="photo-prev" id="scanPrev" alt="" hidden>
    <div id="scanOut"></div>`);
  $('#scanFile').addEventListener('change', async (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    const out = $('#scanOut');
    try {
      const photo = await compress(f);
      $('#scanPrev').src = photo; $('#scanPrev').hidden = false; $('#scanDrop').hidden = true;
      out.innerHTML = '<p class="ai-note"><span class="spinner"></span> Looking for risks…</p>';
      const d = await api(`/api/plan/${plan.id}/scan`, { method: 'POST', body: { photo } });
      setPlan(d.plan);
      out.innerHTML = `<p class="small muted" style="margin-top:12px">${esc(d.seen)}</p>
        ${d.added.length ? `<h3 style="margin:10px 0 8px">Added ${d.added.length} ${d.added.length === 1 ? 'task' : 'tasks'} to your checklist</h3><ul class="tasks">${d.added.map((t) => `<li class="task"><span class="box" style="cursor:default"></span><div><strong>${esc(t.title)}</strong><p>${esc(t.why)}</p></div></li>`).join('')}</ul>`
          : '<p class="notice" style="margin-top:10px">No new risks found in this photo. Try another spot.</p>'}
        ${(d.good || []).length ? `<h3 style="margin:14px 0 6px">Already done right</h3><ul class="small" style="margin:0 0 8px;padding-left:18px">${d.good.map((g) => `<li>${esc(g)}</li>`).join('')}</ul>` : ''}
        ${d.next_photo ? `<p class="ai-note small">Next, take a photo of: <strong>${esc(d.next_photo)}</strong></p>` : ''}
        <button class="btn btn-ghost btn-wide" type="button" id="scanAgain">Scan another photo</button>`;
      $('#scanAgain').addEventListener('click', openScan);
    } catch (err) { out.innerHTML = `<p class="notice">${esc(err.message)}</p>`; }
  });
}

/* ---------------- checklist ---------------- */
let listGroup = 'now';
const GROUPS = [['now', 'Do this week'], ['kit', 'Have at home'], ['storm', 'If a storm hits']];
function renderList() {
  const page = $('#listPage');
  if (!plan) return;
  const items = plan.checklist.filter((t) => t.group === listGroup);
  page.innerHTML = `
    <div class="list-head">${ringHTML(plan.progress.done, plan.progress.total)}<div><h2>Your checklist</h2><p class="muted small" style="margin:2px 0 0">Made for ${esc(plan.label || 'your home')}. Tap a box when it’s done.</p></div></div>
    <div class="seg" role="group" aria-label="Checklist section">${GROUPS.map(([k, t]) => {
      const n = plan.checklist.filter((x) => x.group === k);
      return `<button type="button" data-group="${k}" aria-pressed="${k === listGroup}">${t}<span class="n">${n.filter((x) => x.done).length}/${n.length}</span></button>`;
    }).join('')}</div>
    <ul class="tasks">${items.map(taskHTML).join('')}</ul>`;
  bindTasks(page);
  $$('[data-group]', page).forEach((b) => b.addEventListener('click', () => { listGroup = b.dataset.group; renderList(); }));
}
function bindTasks(root) {
  $$('.task .box', root).forEach((b) => b.addEventListener('click', async () => {
    const id = b.closest('.task').dataset.task;
    const t = plan.checklist.find((x) => x.id === id);
    if (!t) return;
    t.done = !t.done;
    plan.progress.done += t.done ? 1 : -1;
    state.cached = plan; save();
    renderPlan(); renderList();
    try {
      await api(`/api/plan/${plan.id}/check`, { method: 'POST', body: { item_id: id, done: t.done } });
      if (t.done && plan.progress.done === plan.progress.total) toast('Every step done. Your home is ready.');
    } catch (e) {
      t.done = !t.done; plan.progress.done += t.done ? 1 : -1; renderPlan(); renderList();
      toast('Couldn’t save that. Check your connection.');
    }
  }));
}

/* ---------------- help ---------------- */
const mapsLink = (q) => `https://www.google.com/maps/dir/?api=1&destination=${encodeURIComponent(q)}`;
function renderHelp() {
  const page = $('#helpPage');
  if (!plan) return;
  const h = plan.help;
  const sb = h.sandbags || [];
  const intl = plan.place.country && plan.place.country !== 'US';
  page.innerHTML = `
    <h2>Help near ${esc(plan.place.city || 'you')}</h2>
    <p class="muted">Ask for help, find local groups, sandbags and alerts.</p>
    <section class="card ask-card block">
      <h3>Need a hand?</h3>
      <p class="small" style="margin:0">Ask local organizations for a ride, sandbags, a check-in call, farm help and more. Only groups that offer that help can see your request, and only the one that accepts it sees your contact.</p>
      <button class="btn btn-primary" type="button" id="askHelp">Ask for help</button>
      <div id="myRequests"></div>
    </section>
    <section class="block" id="orgSection"><div class="section-head"><h3>Organizations near you</h3></div><div id="orgList"><div class="card skeleton"><span></span><span></span></div></div></section>
    ${h.alert_system ? `<section class="card help-alert block">
      <p class="eyebrow" style="color:rgba(255,255,255,.7)">Step one for everyone</p>
      <h3>Sign up for ${esc(h.alert_system.name)}</h3>
      <p>${esc(plan.place.county)} County’s official emergency alerts: evacuations, road closures and shelters, by text or call.</p>
      <a class="btn" href="${esc(h.alert_system.url)}" target="_blank" rel="noopener">Sign up</a>
    </section>` : ''}

    ${plan.risk.hazard === 'drought' ? '' : `<section class="block">
      <div class="section-head"><h3>Sandbags</h3>${sb.length ? `<span class="muted small">Checked ${esc(fmtDay(h.checked))}</span>` : ''}</div>
      <p class="small muted" style="margin:-4px 0 10px">Sandbags are heavy bags of sand. Stacked in front of doors and garage openings, they keep shallow floodwater out.</p>
      ${sb.length ? `<ul class="res-list">${sb.map((s) => `<li>
        <div class="res-top"><strong>${esc(s.name)}</strong><span class="miles">${s.miles} mi</span></div>
        <p>${esc(s.address)}</p><p>${esc(s.notes)}</p>
        <div class="res-actions"><a href="${mapsLink(s.address)}" target="_blank" rel="noopener">Directions</a>${s.phone ? `<a href="tel:${esc(s.phone.replace(/[^0-9]/g, ''))}">Call ${esc(s.phone)}</a>` : ''}<a href="${esc(s.source)}" target="_blank" rel="noopener">Source</a></div>
      </li>`).join('')}</ul>`
      : h.ai && h.ai.sites.length ? `<ul class="res-list">${h.ai.sites.map((s) => `<li>
        <div class="res-top"><strong>${esc(s.name)}</strong><span class="ai-tag">Found by AI search</span></div>
        ${s.address ? `<p>${esc(s.address)}</p>` : ''}${s.notes ? `<p>${esc(s.notes)}</p>` : ''}
        ${s.address ? `<div class="res-actions"><a href="${mapsLink(s.address)}" target="_blank" rel="noopener">Directions</a></div>` : ''}
      </li>`).join('')}</ul>
      <p class="fineprint">AI found these from the sources below. Confirm with your city before you go.</p>
      <div class="sources">${h.ai.sources.map((s) => `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>`).join('')}</div>`
      : `<div class="notice">${intl ? 'Sandbag sites are listed for California for now.' : 'We haven’t checked sandbag sites for this area yet. Call 211 or search your city’s public works page.'}</div>`}
    </section>`}

    ${h.county && h.county.length ? `<section class="block"><div class="section-head"><h3>${esc(plan.place.county)} County</h3></div>
      <ul class="res-list">${h.county.map(resHTML).join('')}</ul></section>` : ''}
    ${h.country && h.country.length ? `<section class="block"><div class="section-head"><h3>Official sources</h3></div><ul class="res-list">${h.country.map(resHTML).join('')}</ul></section>` : ''}
    ${h.statewide && h.statewide.length ? `<section class="block"><div class="section-head"><h3>${plan.place.state === 'CA' ? 'Anywhere in California' : 'Anywhere'}</h3></div>
      <ul class="res-list">${h.statewide.map(resHTML).join('')}</ul></section>` : ''}
    <div class="org-join"><strong>Are you an organization?</strong><span class="small muted">List the help you offer and see requests from people nearby.</span><button class="link-btn" type="button" id="orgJoin">${state.org ? 'Open your organization dashboard' : 'Join as an organization'}</button></div>
    <p class="fineprint center">${plan.place.country && plan.place.country !== 'US' ? 'In an emergency, call your local emergency number.' : 'In an emergency, call 911.'}</p>`;
  $('#askHelp').addEventListener('click', openAskHelp);
  $('#orgJoin').addEventListener('click', () => (state.org ? openOrgDashboard() : openOrgSignup()));
  loadHelpExtras();
}
/* ---------------- help requests + organizations ---------------- */
let SERVICES = null;
const STATUS_TEXT = { open: 'Waiting for a helper', accepted: 'Help is on the way', done: 'Done' };
async function services() {
  if (!SERVICES) SERVICES = await api('/api/services');
  return SERVICES;
}
function orgHTML(o) {
  return `<li class="org"><div class="org-top"><strong>${esc(o.name)}</strong>${o.example ? '<span class="badge badge-wait">Example</span>' : o.verified ? '<span class="badge badge-ok">Verified</span>' : '<span class="badge badge-wait">Not verified yet</span>'}</div>
    ${o.about ? `<p>${esc(o.about)}</p>` : ''}
    <div class="svc">${o.services.map((k) => `<span>${esc((SERVICES || {})[k] || k)}</span>`).join('')}</div>
    <p class="small">${esc(o.area || '')}${o.miles != null ? ` · ${o.miles} mi away` : ''}</p>
    <div class="res-actions">${o.website ? `<a href="${esc(o.website)}" target="_blank" rel="noopener">Website</a>` : ''}${o.email ? `<a href="mailto:${esc(o.email)}">Email</a>` : ''}${o.phone ? `<a href="tel:${esc(o.phone)}">Call</a>` : ''}</div></li>`;
}
function requestHTML(r) {
  return `<div class="req"><div class="req-top"><strong>${esc(r.need_label)}</strong><span class="status st-${r.status}">${STATUS_TEXT[r.status] || r.status}</span></div>
    ${r.details ? `<p class="small" style="margin:0">${esc(r.details)}</p>` : ''}
    ${r.org ? `<p class="small" style="margin:0">${esc(r.org.name)} is helping${r.org.phone ? ` · <a href="tel:${esc(r.org.phone)}">${esc(r.org.phone)}</a>` : ''}${r.org.email ? ` · <a href="mailto:${esc(r.org.email)}">${esc(r.org.email)}</a>` : ''}</p>` : ''}
    ${r.status === 'open' ? `<button class="link-btn" type="button" data-cancel="${r.id}">Cancel request</button>` : ''}</div>`;
}
function renderMyRequests(list) {
  const el = $('#myRequests');
  if (!el) return;
  el.innerHTML = list.length ? `<div style="margin-top:6px">${list.map(requestHTML).join('')}</div>` : '';
  $$('[data-cancel]', el).forEach((b) => b.addEventListener('click', async () => {
    try { renderMyRequests(await api(`/api/plan/${plan.id}/help/${b.dataset.cancel}/cancel`, { method: 'POST' })); } catch (e) { toast(e.message); }
  }));
}
async function loadHelpExtras() {
  try { await services(); } catch (e) { /* labels fall back to keys */ }
  try { renderMyRequests(await api(`/api/plan/${plan.id}/help`)); } catch (e) { /* offline */ }
  try {
    const orgs = await api(`/api/orgs?lat=${plan.lat}&lon=${plan.lon}`);
    const el = $('#orgList');
    if (el) el.innerHTML = orgs.length ? `<ul class="res-list">${orgs.map(orgHTML).join('')}</ul>` : '<div class="notice">No organizations have joined near here yet.</div>';
  } catch (e) { const el = $('#orgList'); if (el) el.innerHTML = `<div class="notice">${esc(e.message)}</div>`; }
}
async function openAskHelp() {
  let svc;
  try { svc = await services(); } catch (e) { toast(e.message); return; }
  let need = plan.role === 'farmer' ? 'farm' : 'checks';
  openSheet(`<h2 id="sheetTitle">Ask for help</h2>
    <p class="muted small">Organizations near ${esc(plan.place.city || 'you')} that offer this kind of help will see your request. This isn’t for emergencies: if you’re in danger, call 911.</p>
    <p class="field-label">What do you need?</p>
    <div class="need-grid">${Object.entries(svc).map(([k, v]) => `<button type="button" data-need="${k}" aria-pressed="${k === need}">${esc(v)}</button>`).join('')}</div>
    <label class="field-label" for="helpDetails">Details <span class="opt">optional</span></label>
    <textarea id="helpDetails" maxlength="500" placeholder="e.g. My garage floods. I'm 72 and can't lift sandbags."></textarea>
    <label class="field-label" for="helpContact">Phone or email</label>
    <input id="helpContact" type="text" maxlength="120" placeholder="Only the group that accepts will see this">
    <button class="btn btn-primary btn-wide" type="button" id="helpSend">Send request</button>`);
  $$('[data-need]').forEach((b) => b.addEventListener('click', () => { need = b.dataset.need; $$('[data-need]').forEach((x) => x.setAttribute('aria-pressed', String(x === b))); }));
  $('#helpSend').addEventListener('click', async () => {
    const btn = $('#helpSend'); btn.disabled = true;
    try {
      const list = await api(`/api/plan/${plan.id}/help`, { method: 'POST', body: { need, details: $('#helpDetails').value.trim(), contact: $('#helpContact').value.trim() } });
      closeSheet(); renderMyRequests(list); toast('Sent. You’ll see here when someone accepts.');
    } catch (e) { btn.disabled = false; toast(e.message); }
  });
}
async function openOrgSignup() {
  let svc;
  try { svc = await services(); } catch (e) { toast(e.message); return; }
  const picked = new Set();
  openSheet(`<h2 id="sheetTitle">Join as an organization</h2>
    <p class="muted small">List the help you offer. People nearby can find you, and you’ll see their requests. New organizations show as “Not verified yet” until we check them.</p>
    <label class="field-label" for="oName">Organization name</label><input id="oName" type="text" maxlength="80">
    <label class="field-label" for="oAbout">What you do <span class="opt">optional</span></label><textarea id="oAbout" maxlength="400"></textarea>
    <p class="field-label">Help you can offer</p>
    <div class="need-grid">${Object.entries(svc).map(([k, v]) => `<button type="button" data-svc="${k}" aria-pressed="false">${esc(v)}</button>`).join('')}</div>
    <label class="field-label" for="oAddr">Where you’re based</label><input id="oAddr" type="text" placeholder="City and state, or address" maxlength="200">
    <label class="field-label" for="oRadius">How far you can help (miles)</label><input id="oRadius" type="text" inputmode="numeric" value="25">
    <label class="field-label" for="oEmail">Email</label><input id="oEmail" type="text" maxlength="120">
    <label class="field-label" for="oWeb">Website <span class="opt">optional</span></label><input id="oWeb" type="text" maxlength="200">
    <label class="field-label" for="oPhone">Phone <span class="opt">optional</span></label><input id="oPhone" type="text" maxlength="40">
    <button class="btn btn-primary btn-wide" type="button" id="oSend">Create organization</button>`);
  $$('[data-svc]').forEach((b) => b.addEventListener('click', () => { const k = b.dataset.svc; if (picked.has(k)) picked.delete(k); else picked.add(k); b.setAttribute('aria-pressed', String(picked.has(k))); }));
  $('#oSend').addEventListener('click', async () => {
    const btn = $('#oSend'); btn.disabled = true;
    try {
      const res = await api('/api/orgs', { method: 'POST', body: { name: $('#oName').value.trim(), about: $('#oAbout').value.trim(), services: [...picked], address: $('#oAddr').value.trim() || undefined, lat: plan.lat, lon: plan.lon, radius_miles: $('#oRadius').value, email: $('#oEmail').value.trim(), website: $('#oWeb').value.trim(), phone: $('#oPhone').value.trim() } });
      state.org = { id: res.org.id, key: res.key, name: res.org.name }; save();
      openSheet(`<h2 id="sheetTitle">You’re on ${esc(CFG.name)}</h2><p>Save this key. It’s the only way to open your dashboard on another device.</p><div class="keybox">${esc(res.key)}</div>
        <button class="btn btn-primary btn-wide" type="button" id="toDash">Open dashboard</button>`);
      $('#toDash').addEventListener('click', () => { closeSheet(); openOrgDashboard(); });
    } catch (e) { btn.disabled = false; toast(e.message); }
  });
}
async function openOrgDashboard() {
  switchView('org');
  const page = $('#orgPage');
  page.innerHTML = '<div class="card skeleton"><span></span><span></span><span></span></div>';
  let d;
  try {
    await services();
    const res = await fetch((CFG.apiBase || '') + `/api/orgs/${state.org.id}/dashboard`, { headers: { 'X-Org-Key': state.org.key } });
    if (!res.ok) throw new Error('Couldn’t open the dashboard. Check your key.');
    d = await res.json();
  } catch (e) { page.innerHTML = `<div class="notice">${esc(e.message)}</div>`; return; }
  const open = d.requests.filter((r) => r.status === 'open'), mine = d.requests.filter((r) => r.mine && r.status === 'accepted');
  page.innerHTML = `<button class="back-link" type="button" id="orgBack">← Back to my plan</button>
    <section class="card org-hero"><p class="eyebrow" style="color:rgba(255,255,255,.7)">Organization dashboard</p><h2 style="color:#fff">${esc(d.org.name)}</h2>
      <p>${d.org.verified ? 'Verified' : 'Not verified yet'} · helping within ${d.org.radius_miles} miles</p>
      <div class="org-stats"><div><b>${open.length}</b><span>new requests</span></div><div><b>${mine.length}</b><span>you’re helping</span></div><div><b>${d.helped}</b><span>helped so far</span></div></div></section>
    <section class="block"><div class="section-head"><h3>You’re helping</h3></div>${mine.length ? mine.map((r) => orgReqHTML(r)).join('') : '<div class="notice">Accept a request below to see the person’s contact.</div>'}</section>
    <section class="block"><div class="section-head"><h3>New requests near you</h3></div>${open.length ? open.map((r) => orgReqHTML(r)).join('') : '<div class="notice">No open requests right now.</div>'}</section>`;
  $('#orgBack').addEventListener('click', () => switchView('help'));
  $$('[data-act]', page).forEach((b) => b.addEventListener('click', async () => {
    try {
      const res = await fetch((CFG.apiBase || '') + `/api/orgs/${state.org.id}/requests/${b.dataset.id}/${b.dataset.act}`, { method: 'POST', headers: { 'X-Org-Key': state.org.key } });
      const j = await res.json();
      if (!res.ok) throw new Error(j.error || 'Something went wrong');
      openOrgDashboard();
    } catch (e) { toast(e.message); }
  }));
}
function orgReqHTML(r) {
  return `<div class="req"><div class="req-top"><strong>${esc(r.need_label)}</strong><span class="status st-${r.status}">${r.status === 'open' ? 'New' : 'Accepted'}</span></div>
    <p class="small" style="margin:0">${esc(r.area || 'Nearby')} · ${esc(fmtDay(r.created_at, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }))}</p>
    ${r.details ? `<p style="margin:0">${esc(r.details)}</p>` : ''}
    ${r.contact ? `<p style="margin:0"><strong>Contact:</strong> ${esc(r.contact)}</p><div class="res-actions"><a href="${mapsLink(r.lat + ',' + r.lon)}" target="_blank" rel="noopener">Directions</a></div>` : ''}
    <div class="res-actions">${r.status === 'open' ? `<button class="btn btn-primary btn-sm" type="button" data-act="accept" data-id="${r.id}">I can help</button>` : `<button class="btn btn-primary btn-sm" type="button" data-act="done" data-id="${r.id}">Mark done</button><button class="btn btn-ghost btn-sm" type="button" data-act="release" data-id="${r.id}">Can’t help after all</button>`}</div></div>`;
}

function resHTML(r) {
  return `<li><div class="res-top"><strong>${esc(r.name)}</strong></div><p>${esc(r.what)}</p>
    <div class="res-actions">${r.phone ? `<a href="tel:${esc(r.phone)}">Call ${esc(r.phone)}</a>` : ''}${r.url ? `<a href="${esc(r.url)}" target="_blank" rel="noopener">Open</a>` : ''}</div></li>`;
}

/* ---------------- map + community reports ---------------- */
/* ---------------- accounts ---------------- */
function newDeviceId() {
  return crypto.randomUUID ? crypto.randomUUID() : 'd-' + Date.now().toString(36) + Math.random().toString(36).slice(2, 12);
}
async function submitAccount(mode, name, email, password) {
  if (mode === 'signup') {
    const d = await api('/api/account/signup', { method: 'POST', body: { name, email, password } });
    state.account = d.account; save();
    return { account: d.account, plans: [] };
  }
  const d = await api('/api/account/login', { method: 'POST', body: { email, password } });
  state.deviceId = d.device_id; state.account = d.account; save();
  const plans = await api('/api/plans');
  return { account: d.account, plans };
}
function accountFormHTML(mode, prefix) {
  const signup = mode === 'signup';
  return `${signup ? `<label class="field-label" for="${prefix}Name">First name</label><input id="${prefix}Name" type="text" maxlength="40" autocomplete="given-name">` : ''}
    <label class="field-label" for="${prefix}Email">Email</label><input id="${prefix}Email" type="email" maxlength="120" autocomplete="email">
    <label class="field-label" for="${prefix}Pw">Password</label><input id="${prefix}Pw" type="password" autocomplete="${signup ? 'new-password' : 'current-password'}">
    ${signup ? '<p class="fineprint" style="margin-top:6px">At least 8 characters. We store only a scrambled version of it.</p>' : ''}`;
}

// Onboarding account step
let acctMode = 'signup';
function setAcctMode(m) {
  acctMode = m;
  const signup = m === 'signup';
  $('#acctTitle').textContent = signup ? 'Create your account' : 'Welcome back';
  $('#acctLead').textContent = signup ? 'Your plans follow you to any phone or computer. You’re added to your county and city, and you can start neighborhood and family groups.' : 'Log in to see your plans and communities.';
  $('#nameWrap').hidden = !signup;
  $('#pwHint').hidden = !signup;
  $('#acctPw').setAttribute('autocomplete', signup ? 'new-password' : 'current-password');
  $('#acctSubmit').textContent = signup ? 'Create account' : 'Log in';
  $('#acctSwitch').textContent = signup ? 'Already have an account? Log in' : 'New here? Create an account';
}
$('#acctSwitch').addEventListener('click', () => setAcctMode(acctMode === 'signup' ? 'login' : 'signup'));
$('#acctSkip').addEventListener('click', () => obShow(2));
$('#acctForm').addEventListener('submit', async (e) => {
  e.preventDefault();
  const btn = $('#acctSubmit'); btn.disabled = true;
  try {
    const r = await submitAccount(acctMode, $('#acctName').value.trim(), $('#acctEmail').value.trim(), $('#acctPw').value);
    toast(acctMode === 'signup' ? `Welcome, ${r.account.name}!` : `Welcome back, ${r.account.name}!`);
    if (r.plans.length) { showApp(); setPlan(await api(`/api/plan/${r.plans[0].id}`)); switchView('plan'); }
    else obShow(2);
  } catch (err) { toast(err.message); }
  btn.disabled = false;
});

function openAccountSheet(mode = 'signup') {
  openSheet(`<h2 id="sheetTitle">${mode === 'signup' ? 'Create your account' : 'Log in'}</h2>
    <p class="muted small">${mode === 'signup' ? 'Your plans on this device move into your account. You’re added to your county and city, and you can start neighborhood and family groups.' : 'Plans you made on this device move into your account.'}</p>
    ${accountFormHTML(mode, 'sh')}
    <button class="btn btn-primary btn-wide" type="button" id="shGo">${mode === 'signup' ? 'Create account' : 'Log in'}</button>
    <button class="link-btn" type="button" id="shSwitch" style="margin-top:12px">${mode === 'signup' ? 'Already have an account? Log in' : 'New here? Create an account'}</button>`);
  $('#shSwitch').addEventListener('click', () => openAccountSheet(mode === 'signup' ? 'login' : 'signup'));
  $('#shGo').addEventListener('click', async () => {
    const b = $('#shGo'); b.disabled = true;
    try {
      const r = await submitAccount(mode, mode === 'signup' ? $('#shName').value.trim() : '', $('#shEmail').value.trim(), $('#shPw').value);
      closeSheet();
      toast(mode === 'signup' ? `Welcome, ${r.account.name}!` : `Welcome back, ${r.account.name}!`);
      if (mode === 'login' && r.plans.length && !r.plans.some((p) => p.id === state.current)) setPlan(await api(`/api/plan/${r.plans[0].id}`));
      renderCommunity();
    } catch (err) { b.disabled = false; toast(err.message); }
  });
}
function openLogout() {
  openSheet(`<h2 id="sheetTitle">Log out?</h2>
    <p class="muted">Your plans and communities stay in your account. Log in again on any device to get them back.</p>
    <button class="btn btn-primary btn-wide" type="button" id="logoutGo">Log out</button>`);
  $('#logoutGo').addEventListener('click', () => {
    Object.assign(state, { account: null, deviceId: newDeviceId(), current: null, cached: null, org: null });
    save(); location.reload();
  });
}

/* ---------------- map ---------------- */
let map = null, layer = null;
function pinIcon(cls, svg) {
  return L.divIcon({ className: '', html: `<div class="pin ${cls}"><svg viewBox="0 0 24 24">${svg}</svg></div>`, iconSize: [30, 30], iconAnchor: [15, 30] });
}
function reportPins(lyr, reports) {
  reports.forEach((r) => L.marker([r.lat, r.lon], { icon: pinIcon('pin-r' + r.severity, ICON.drop) }).addTo(lyr).on('click', () => openReport(r)));
}
async function renderMap() {
  if (!plan || typeof L === 'undefined') return;
  if (!map) {
    map = L.map('map', { zoomControl: false }).setView([plan.lat, plan.lon], 14);
    L.control.zoom({ position: 'bottomleft' }).addTo(map);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap' }).addTo(map);
    layer = L.layerGroup().addTo(map);
  } else {
    map.invalidateSize();
  }
  layer.clearLayers();
  L.marker([plan.lat, plan.lon], { icon: pinIcon('pin-home', ICON.home) }).addTo(layer).bindPopup(`<b>${esc(plan.label)}</b>`);
  const bags = plan.risk.hazard === 'drought' ? [] : (plan.help.sandbags || []);
  bags.forEach((s) => L.marker([s.lat, s.lon], { icon: pinIcon('pin-bag', ICON.bag) }).addTo(layer)
    .bindPopup(`<b>Sandbags: ${esc(s.name)}</b><br>${esc(s.address)}<br><a href="${mapsLink(s.address)}" target="_blank" rel="noopener">Directions</a>`));
  $('#mapCard').innerHTML = `<span><i style="background:var(--ocean)"></i>Your place</span>${bags.length ? '<span><i style="background:#b86a00"></i>Sandbags</span>' : ''}<span><i style="background:#c0392b"></i>Storm reports</span>`;
  let reports = [];
  try { reports = await api(`/api/reports?lat=${plan.lat}&lon=${plan.lon}&miles=10`); } catch (e) { reports = []; }
  reportPins(layer, reports);
  setTimeout(() => map.invalidateSize(), 50);
}
$('#reportFab').addEventListener('click', () => openReportForm(() => renderMap(), map ? { lat: map.getCenter().lat, lon: map.getCenter().lng } : null));

/* ---------------- communities ---------------- */
const KINDS = { flooding: 'Flooded street', drain: 'Clogged storm drain', landslide: 'Landslide or mudslide', tree: 'Fallen tree', power: 'Downed power line', road: 'Road damage', other: 'Other storm problem' };
const COMM_KIND = { county: 'County · official updates', city: 'City · official updates', neighborhood: 'Neighborhood group', family: 'Private family group' };
const GROUP_KINDS = ['family', 'neighborhood'];
const COMM_ICON = {
  county: '<path d="M3 20l5-14 5 8 3-4 5 10z"/>',
  city: '<path d="M4 21V9l5-3v15M9 21V4l6 3v14M15 21v-9l5 2v7"/>',
  family: '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3 20a6 6 0 0 1 12 0M14 20a4.5 4.5 0 0 1 7-3.7"/>',
  neighborhood: '<path d="M3 11l5-4 5 4v9H3zM13 11l4-3 4 3v9h-8"/><path d="M7 20v-4h2v4"/>'
};
let commOpen = null;
function milesBetween(a, b, c, d) {
  const r = 3958.8, p1 = a * Math.PI / 180, p2 = c * Math.PI / 180, dp = p2 - p1, dl = (d - b) * Math.PI / 180;
  const h = Math.sin(dp / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dl / 2) ** 2;
  return 2 * r * Math.asin(Math.sqrt(h));
}
function commRowHTML(c) {
  return `<li><button type="button" data-comm="${c.id}"><span class="comm-ic k-${c.kind}"><svg viewBox="0 0 24 24" aria-hidden="true">${COMM_ICON[c.kind]}</svg></span>
    <span class="comm-txt"><strong>${esc(c.name)}</strong><small>${COMM_KIND[c.kind]} · ${c.members} ${c.members === 1 ? 'member' : 'members'}</small></span>
    <svg class="chev-r" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg></button></li>`;
}
async function renderCommunity() {
  const page = $('#communityPage');
  if (commOpen) { renderCommunityDetail(commOpen); return; }
  page.innerHTML = '<h2>Community</h2><div class="card skeleton block"><span></span><span></span></div>';
  let d;
  try { d = await api('/api/communities'); } catch (e) { page.innerHTML = `<h2>Community</h2><div class="notice">${esc(e.message)}</div>`; return; }
  state.account = d.account; save();
  if (!d.account) {
    page.innerHTML = `<h2>Community</h2>
      <p class="muted">With a free account, you’re added to your county and city, where officials post updates. Then start or join a neighborhood or family group, where everyone can post storm reports.</p>
      <section class="card block comm-hero">
        <h3>Create a free account to join</h3>
        <p class="small" style="margin:0 0 12px">Your plans on this device come with you.</p>
        <button class="btn btn-primary btn-wide" type="button" id="cSignup">Create account</button>
        <button class="btn btn-ghost btn-wide" type="button" id="cLogin">Log in</button>
      </section>`;
    $('#cSignup').addEventListener('click', () => openAccountSheet('signup'));
    $('#cLogin').addEventListener('click', () => openAccountSheet('login'));
    return;
  }
  page.innerHTML = `
    <div class="acct-row"><span class="small">Signed in as <strong>${esc(d.account.name)}</strong></span><button class="link-btn" type="button" id="logoutBtn">Log out</button></div>
    <h2>Community</h2>
    <p class="muted">You’re in your county and city automatically, where officials post updates. In neighborhood and family groups, everyone can post storm reports.</p>
    <section class="block"><div class="section-head"><h3>Your communities</h3></div>
      ${d.mine.length ? `<ul class="comm-list">${d.mine.map(commRowHTML).join('')}</ul>` : '<div class="notice">Make a plan for your home first, and you’ll be added to your county and city.</div>'}</section>
    <section class="card block fam-card">
      <h3>Start a group</h3>
      <p class="small"><strong>Neighborhood group:</strong> for your street or block. Everyone in it can post storm reports, like a flooded corner or a blocked drain.</p>
      <p class="small"><strong>Family group:</strong> private, as big as you want. See each other’s places and checklist progress, and tap “I’m safe” after a storm.</p>
      <div class="btn-row"><button class="btn btn-primary" type="button" data-new="neighborhood">Neighborhood</button><button class="btn btn-primary" type="button" data-new="family">Family</button></div>
      <button class="btn btn-ghost btn-wide" type="button" id="joinFam">Join with a code</button>
    </section>
    <button class="btn btn-ghost btn-wide" type="button" id="reportBtn">${icon('camera')} Report a storm problem</button>`;
  $('#logoutBtn').addEventListener('click', openLogout);
  $$('[data-comm]', page).forEach((b) => b.addEventListener('click', () => { commOpen = b.dataset.comm; renderCommunity(); }));
  $$('[data-new]', page).forEach((b) => b.addEventListener('click', () => {
    const kind = b.dataset.new, fam = kind === 'family';
    openSheet(`<h2 id="sheetTitle">Start a ${fam ? 'family' : 'neighborhood'} group</h2><p class="muted small">${fam ? 'Add as many people as you want.' : 'Invite the neighbors on your street or block.'} You’ll get a code to share with them.</p>
      <label class="field-label" for="famName">Group name</label><input id="famName" type="text" maxlength="40" placeholder="${fam ? `${esc(d.account.name)}’s family` : 'e.g. Murchison Drive neighbors'}">
      <button class="btn btn-primary btn-wide" type="button" id="famGo">Create group</button>`);
    $('#famGo').addEventListener('click', async () => {
      try { const c = await api('/api/communities', { method: 'POST', body: { kind, name: $('#famName').value.trim() } }); closeSheet(); commOpen = c.id; renderCommunity(); }
      catch (e) { toast(e.message); }
    });
  }));
  $('#joinFam').addEventListener('click', () => {
    openSheet(`<h2 id="sheetTitle">Join a group</h2><p class="muted small">Ask the person who made the neighborhood or family group for its 6-letter code.</p>
      <label class="field-label" for="famCode">Invite code</label><input id="famCode" type="text" maxlength="8" autocapitalize="characters" placeholder="e.g. K7Q2MX">
      <button class="btn btn-primary btn-wide" type="button" id="codeGo">Join</button>`);
    $('#codeGo').addEventListener('click', async () => {
      try { const c = await api('/api/communities/join', { method: 'POST', body: { code: $('#famCode').value } }); closeSheet(); toast(`You joined ${c.name}.`); commOpen = c.id; renderCommunity(); }
      catch (e) { toast(e.message); }
    });
  });
  $('#reportBtn').addEventListener('click', () => openReportForm());
}
async function renderCommunityDetail(id) {
  const page = $('#communityPage');
  page.innerHTML = '<div class="card skeleton block"><span></span><span></span></div>';
  let c;
  try { c = await api(`/api/communities/${id}`); } catch (e) { commOpen = null; renderCommunity(); return; }
  const fam = c.kind === 'family', group = GROUP_KINDS.includes(c.kind), official = !group;
  const dist = (r) => plan ? milesBetween(plan.lat, plan.lon, r.lat, r.lon) : null;
  page.innerHTML = `
    <button class="back-link" type="button" id="commBack">← All communities</button>
    <div class="comm-head"><span class="comm-ic big k-${c.kind}"><svg viewBox="0 0 24 24" aria-hidden="true">${COMM_ICON[c.kind]}</svg></span>
      <div><h2 style="margin:0">${esc(c.name)}</h2><p class="muted small" style="margin:2px 0 0">${COMM_KIND[c.kind]} · ${c.members} ${c.members === 1 ? 'member' : 'members'}</p></div></div>
    <div class="comm-map" id="commMap" role="img" aria-label="Map of storm reports in ${esc(c.name)}"></div>
    ${fam ? `<section class="card block">
      <div class="section-head"><h3>Members</h3></div>
      <ul class="people">${c.people.map((p) => `<li><span class="avatar">${esc(p.name.slice(0, 1).toUpperCase())}</span><div>
        <strong>${esc(p.name)}${p.you ? ' (you)' : ''}</strong>
        <small class="${p.safe_at ? 'safe' : ''}">${p.safe_at ? `Safe · checked in ${esc(fmtDay(p.safe_at, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }))}` : 'No check-in yet'}</small>
        ${p.places.length ? `<div class="place-chips">${p.places.map((pl) => `<span class="place-chip"><i class="dot lv-${pl.level}"></i>${esc(pl.label)}${pl.city ? `, ${esc(pl.city)}` : ''} · ${pl.done}/${pl.total} done</span>`).join('')}</div>` : '<small>No plan yet</small>'}
      </div></li>`).join('')}</ul>
      <button class="btn btn-primary btn-wide" type="button" id="safeBtn">I’m safe</button>
    </section>` : ''}
    ${group ? `<section class="card block"><div class="invite"><span>Invite code</span><b>${esc(c.invite_code)}</b><button class="pill-btn" type="button" id="copyCode">Copy</button></div>
      <p class="fineprint">Send this code to ${fam ? 'family' : 'neighbors'}. They create a free account and tap “Join with a code.”</p></section>` : ''}
    <section class="block">
      <div class="section-head"><h3>${official ? 'Official updates' : 'Storm reports from this group'}</h3>${c.can_post ? '<button class="link-btn" type="button" id="reportHere">+ Post</button>' : ''}</div>
      ${official ? `<p class="small muted" style="margin:-4px 0 10px">${c.can_post ? 'You’re a verified official here, so you can post updates everyone in the area will see.' : `Only verified officials, like the county’s emergency office or the city, can post here. To share what you see, post in a neighborhood or family group.`}</p>` : ''}
      ${c.reports.length ? `<ul class="rep-list">${c.reports.map((r) => `<li><button type="button" data-rep="${r.id}"><span class="sev-dot s${r.severity}"></span>
        <span class="comm-txt"><strong>${esc(r.title)}</strong><small>${esc(r.kind_label)} · ${esc(fmtDay(r.created_at, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }))}${dist(r) != null ? ` · ${dist(r).toFixed(1)} mi from ${esc(plan.label)}` : ''}${r.confirmations ? ` · ${r.confirmations} confirmed` : ''}</small></span>
        <svg class="chev-r" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg></button></li>`).join('')}</ul>`
      : `<div class="notice">${official ? 'No official updates right now.' : `No storm reports yet. If you see flooding, a clogged drain or a fallen tree, post it so ${fam ? 'your family knows' : 'your neighbors know'}.`}</div>`}
    </section>
    ${group ? '<button class="link-btn danger" type="button" id="leaveBtn">Leave this group</button>' : ''}`;
  drawCommunityMap(c);
  $('#commBack').addEventListener('click', () => { commOpen = null; renderCommunity(); });
  if ($('#reportHere')) $('#reportHere').addEventListener('click', () => openReportForm(() => renderCommunity(), null, c.id));
  $$('[data-rep]', page).forEach((b) => b.addEventListener('click', () => openReport(c.reports.find((r) => r.id === b.dataset.rep))));
  if ($('#leaveBtn')) $('#leaveBtn').addEventListener('click', async () => {
    try { await api(`/api/communities/${id}/leave`, { method: 'POST' }); commOpen = null; toast(`You left ${c.name}.`); renderCommunity(); } catch (e) { toast(e.message); }
  });
  if (fam) {
    $('#safeBtn').addEventListener('click', async () => {
      try { await api(`/api/communities/${id}/safe`, { method: 'POST', body: { safe: true } }); toast('Your family can see you’re safe.'); renderCommunity(); } catch (e) { toast(e.message); }
    });
  }
  const cp = $('#copyCode');
  if (cp) cp.addEventListener('click', () => { try { navigator.clipboard.writeText(c.invite_code); toast('Code copied.'); } catch (e) { toast(c.invite_code); } });
}
let commMap = null;
function drawCommunityMap(c) {
  if (typeof L === 'undefined' || !$('#commMap')) return;
  if (commMap) { commMap.remove(); commMap = null; }
  commMap = L.map('commMap', { zoomControl: false, attributionControl: true, scrollWheelZoom: false });
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; OpenStreetMap' }).addTo(commMap);
  const lyr = L.layerGroup().addTo(commMap);
  const pts = [];
  (c.places || []).forEach((p) => { L.marker([p.lat, p.lon], { icon: pinIcon('pin-home', ICON.home) }).addTo(lyr).bindPopup(`<b>${esc(p.who)}</b><br>${esc(p.label)}`); pts.push([p.lat, p.lon]); });
  if (!pts.length && plan) { L.marker([plan.lat, plan.lon], { icon: pinIcon('pin-home', ICON.home) }).addTo(lyr).bindPopup(`<b>${esc(plan.label)}</b>`); pts.push([plan.lat, plan.lon]); }
  reportPins(lyr, c.reports);
  c.reports.forEach((r) => pts.push([r.lat, r.lon]));
  const zoom = c.kind === 'county' ? 10 : c.kind === 'city' ? 13 : 13;
  if (c.center) pts.push([c.center.lat, c.center.lon]);
  if (pts.length > 1) commMap.fitBounds(pts, { padding: [30, 30], maxZoom: 15 });
  else commMap.setView(pts[0] || [c.center.lat, c.center.lon], zoom);
  setTimeout(() => commMap && commMap.invalidateSize(), 60);
}
async function openReport(r) {
  openSheet(`<h2 id="sheetTitle">${esc(r.title)}</h2>
    <div id="repPhoto"></div>
    ${r.community_name ? `<p class="small"><strong>${r.official ? `Official update from ${esc(r.community_name)}` : `Posted in ${esc(r.community_name)}`}</strong></p>` : ''}
    <p class="muted small">${esc(KINDS[r.kind] || 'Storm problem')} · ${esc(fmtDay(r.created_at, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }))}${r.ai_checked ? ' · checked by AI' : ''}</p>
    ${r.note ? `<p>${esc(r.note)}</p>` : ''}
    <p><strong>${r.confirmations}</strong> ${r.confirmations === 1 ? 'person has' : 'people have'} confirmed this.</p>
    <div class="res-actions" style="margin-bottom:12px"><a href="https://www.google.com/maps/search/?api=1&query=${r.lat},${r.lon}" target="_blank" rel="noopener">See where it is</a></div>
    <button class="btn btn-primary btn-wide" type="button" id="confirmBtn">I see this too</button>
    <button class="btn btn-ghost btn-wide" type="button" id="clearBtn">It’s cleared now</button>`);
  if (r.has_photo) {
    api(`/api/reports/${r.id}/photo`).then((d) => { const el = $('#repPhoto'); if (el) el.innerHTML = `<img class="report-photo" src="${d.photo}" alt="Photo of ${esc(r.title)}">`; }).catch(() => {});
  }
  $('#confirmBtn').addEventListener('click', async () => {
    try { const d = await api(`/api/reports/${r.id}/confirm`, { method: 'POST' }); r.confirmations = d.confirmations; closeSheet(); toast('Thanks. Others can see it’s confirmed.'); renderCommunity(); } catch (e) { toast(e.message); }
  });
  $('#clearBtn').addEventListener('click', async () => {
    try { await api(`/api/reports/${r.id}/clear`, { method: 'POST' }); closeSheet(); renderCommunity(); toast('Marked as cleared.'); } catch (e) { toast(e.message); }
  });
}

function compress(file, max = 1280, q = 0.72) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      const s = Math.min(1, max / Math.max(img.width, img.height));
      const c = document.createElement('canvas');
      c.width = Math.round(img.width * s); c.height = Math.round(img.height * s);
      c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
      URL.revokeObjectURL(url);
      resolve(c.toDataURL('image/jpeg', q));
    };
    img.onerror = () => { URL.revokeObjectURL(url); reject(new Error('That file isn’t a photo.')); };
    img.src = url;
  });
}
async function openReportForm(after, center, communityId) {
  if (!plan) return;
  let groups = [];
  try { groups = ((await api('/api/communities')).mine || []).filter((c) => c.can_post); } catch (e) { groups = []; }
  if (!state.account) {
    openSheet(`<h2 id="sheetTitle">Create a free account to post</h2><p class="muted">Storm reports go to a neighborhood or family group, so the people near you see them.</p>
      <button class="btn btn-primary btn-wide" type="button" id="rSignup">Create account</button><button class="btn btn-ghost btn-wide" type="button" id="rLogin">Log in</button>`);
    $('#rSignup').addEventListener('click', () => openAccountSheet('signup'));
    $('#rLogin').addEventListener('click', () => openAccountSheet('login'));
    return;
  }
  if (!groups.length) {
    openSheet(`<h2 id="sheetTitle">Join a group to post</h2><p class="muted">County and city communities are for official updates. To post a storm report, start or join a neighborhood or family group in the Community tab.</p>
      <button class="btn btn-primary btn-wide" type="button" id="goComm">Go to Community</button>`);
    $('#goComm').addEventListener('click', () => { closeSheet(); commOpen = null; switchView('community'); });
    return;
  }
  const draft = { kind: 'flooding', severity: 2, photo: null, ai: false, where: center ? 'map' : 'here' };
  openSheet(`<h2 id="sheetTitle">Report a storm problem</h2>
    <p class="muted small">Everyone in the group you pick will see it. Don’t take photos in dangerous spots.</p>
    <label class="field-label" for="repGroup">Post to</label>
    <select id="repGroup">${groups.map((g) => `<option value="${g.id}" ${g.id === communityId ? 'selected' : ''}>${esc(g.name)} (${esc(COMM_KIND[g.kind])})</option>`).join('')}</select>
    <label class="field-label">Where is it?</label>
    <div class="sev-row ${center ? 'three' : ''}" id="whereRow">${center ? '<button type="button" data-where="map" aria-pressed="true">Center of the map</button>' : ''}<button type="button" data-where="here" aria-pressed="${!center}">Where I am now</button><button type="button" data-where="place" aria-pressed="false">At ${esc(plan.label || 'my place')}</button></div>
    <label class="photo-drop" id="drop"><input type="file" id="repFile" accept="image/*" capture="environment">${icon('camera')}<strong>Add a photo</strong><span class="small">AI will label it for you</span></label>
    <img class="photo-prev" id="repPrev" alt="" hidden>
    <div class="ai-note" id="aiNote" hidden></div>
    <label class="field-label" for="repKind">What is it?</label>
    <select id="repKind">${Object.entries(KINDS).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('')}</select>
    <label class="field-label" for="repTitle">Short title</label>
    <input id="repTitle" type="text" maxlength="60" placeholder="e.g. Water across Main St">
    <label class="field-label">How bad?</label>
    <div class="sev-row" id="sevRow">${[[1, 'Minor'], [2, 'Avoid it'], [3, 'Dangerous']].map(([v, t]) => `<button type="button" data-sev="${v}" aria-pressed="${v === 2}">${t}</button>`).join('')}</div>
    <button class="btn btn-primary btn-wide" type="button" id="repSend">Post report</button>`);
  $$('#whereRow button').forEach((b) => b.addEventListener('click', () => { draft.where = b.dataset.where; $$('#whereRow button').forEach((x) => x.setAttribute('aria-pressed', String(x === b))); }));
  $('#repFile').addEventListener('change', async (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    try {
      draft.photo = await compress(f);
      $('#repPrev').src = draft.photo; $('#repPrev').hidden = false; $('#drop').hidden = true;
      const note = $('#aiNote');
      note.hidden = false; note.innerHTML = '<span class="spinner"></span> AI is looking at your photo…';
      const a = await api('/api/reports/analyze', { method: 'POST', body: { photo: draft.photo } });
      if (a.ai) {
        draft.ai = true;
        $('#repKind').value = a.kind; $('#repTitle').value = a.title; setSev(a.severity);
        note.innerHTML = `${icon('spark')} ${esc(a.advice || 'AI filled this in. Change anything that’s wrong.')}`;
      } else note.hidden = true;
    } catch (err) { $('#aiNote').hidden = true; toast(err.message); }
  });
  function setSev(v) { draft.severity = v; $$('#sevRow button').forEach((b) => b.setAttribute('aria-pressed', String(+b.dataset.sev === v))); }
  $$('#sevRow button').forEach((b) => b.addEventListener('click', () => setSev(+b.dataset.sev)));
  const here = () => new Promise((resolve) => {
    if (!navigator.geolocation) { resolve(null); return; }
    navigator.geolocation.getCurrentPosition((p) => resolve({ lat: p.coords.latitude, lon: p.coords.longitude }), () => resolve(null), { enableHighAccuracy: true, timeout: 10000 });
  });
  $('#repSend').addEventListener('click', async () => {
    const btn = $('#repSend');
    btn.disabled = true;
    let spot = { lat: plan.lat, lon: plan.lon };
    if (draft.where === 'map' && center) spot = center;
    if (draft.where === 'here') {
      const h = await here();
      if (h) spot = h; else toast(`Couldn’t get your location, so it’s posted at ${plan.label || 'your place'}.`);
    }
    try {
      await api('/api/reports', { method: 'POST', body: { ...spot, community_id: $('#repGroup').value, kind: $('#repKind').value, title: $('#repTitle').value.trim(), severity: draft.severity, photo: draft.photo, ai_checked: draft.ai } });
      closeSheet(); toast('Posted. Thanks for looking out for your community.');
      if (after) after(); else if (currentView === 'community') renderCommunity();
    } catch (err) { btn.disabled = false; toast(err.message); }
  });
}

/* ---------------- news ---------------- */
let newsTab = 'local', newsCache = null, regionsCache = null;
async function renderNews() {
  const page = $('#newsPage');
  if (!plan) return;
  page.innerHTML = `<h2>El Niño news</h2>
    <div class="seg" role="group" aria-label="News">${[['local', `Near ${plan.place.county || 'you'}`], ['tracker', 'El Niño tracker'], ['world', 'Around the world']].map(([k, t]) => `<button type="button" data-news="${k}" aria-pressed="${k === newsTab}">${esc(t)}</button>`).join('')}</div>
    <div id="newsBody"><div class="card skeleton"><span></span><span></span><span></span></div></div>`;
  $$('[data-news]', page).forEach((b) => b.addEventListener('click', () => { newsTab = b.dataset.news; renderNews(); }));
  const body = $('#newsBody');
  if (newsTab === 'tracker') { renderTracker(body); return; }
  if (newsTab === 'world') {
    try { regionsCache = regionsCache || await api('/api/regions'); } catch (e) { body.innerHTML = `<div class="notice">${esc(e.message)}</div>`; return; }
    body.innerHTML = `<p class="muted" style="margin-top:12px">The same El Niño brings different dangers to different places. ${esc(regionsCache.note)}</p>
      ${regionsCache.regions.map((r) => `<div class="region ${plan.risk.region && r.id === plan.risk.region.id ? 'mine' : ''}">
        <div class="region-top"><strong>${esc(r.name)}</strong><span class="effect ${/wet/.test(r.effect) ? 'eff-wet' : 'eff-dry'}">${esc(r.effect)}</span></div>
        <small>${esc(r.season)}</small><p>${esc(r.impact)}</p><p class="small"><strong>Get ready:</strong> ${esc(r.prepare)}</p></div>`).join('')}
      <p class="fineprint">Source: <a href="${esc(regionsCache.source.url)}" target="_blank" rel="noopener">${esc(regionsCache.source.title)}</a></p>`;
    return;
  }
  const key = `${plan.place.county}|${plan.language}`;
  try {
    if (!newsCache || newsCache.key !== key) newsCache = { key, data: await api(`/api/news?county=${encodeURIComponent(plan.place.county || '')}&state=${encodeURIComponent(plan.place.state || 'CA')}&lang=${plan.language}`) };
  } catch (e) { body.innerHTML = `<div class="notice">${esc(e.message)}</div>`; return; }
  const n = newsCache.data;
  body.innerHTML = `${n.headline ? `<p class="headline" style="margin-top:12px">${esc(n.headline)}</p>` : ''}
    ${n.items && n.items.length ? `<div class="card block">${n.items.map((i) => `<article class="news-item">${i.date ? `<span class="date">${esc(i.date)}</span>` : ''}<h4>${esc(i.title)}</h4><p>${esc(i.summary)}</p>${i.action ? `<p class="act">${esc(i.action)}</p>` : ''}</article>`).join('')}</div>
      <div class="sources">${(n.sources || []).map((s) => `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>`).join('')}</div>
      <p class="fineprint">Summaries are written by AI from the news sources above and can contain mistakes. Check the sources.</p>`
    : `<div class="card enso-card block"><h3>${esc(n.enso.status)}</h3><p class="small">${esc(n.enso.detail)}</p><ul class="events">${n.enso.events.map((e) => `<li>${esc(e.text)}<small><a href="${esc(e.url)}" target="_blank" rel="noopener">${esc(e.source)}</a></small></li>`).join('')}</ul></div>
      <p class="fineprint">Live news needs the server’s AI key.</p>`}`;
}

let ensoCache = null;
async function renderTracker(body) {
  try { ensoCache = ensoCache || await api('/api/enso'); } catch (e) { body.innerHTML = `<div class="notice">${esc(e.message)}</div>`; return; }
  const t = ensoCache.tracker;
  if (!t) { body.innerHTML = '<div class="notice">Tracker data isn’t available.</div>'; return; }
  const max = 3, W = 320, H = 170, bw = W / (t.history.length + 1);
  const bars = t.history.map((h, i) => {
    const bh = (h.peak / max) * (H - 40), x = i * bw + 4, y = H - 22 - bh;
    const cls = h.strength === 'very strong' ? 'bar-vs' : 'bar-s';
    return `<rect class="${cls}" x="${x}" y="${y}" width="${bw - 8}" height="${bh}" rx="3"/><text class="bar-val" x="${x + (bw - 8) / 2}" y="${y - 4}">${h.peak.toFixed(1)}</text><text class="bar-lab" x="${x + (bw - 8) / 2}" y="${H - 8}">${esc(h.season.slice(2, 4))}</text>`;
  }).join('');
  const fx = t.history.length * bw + 4;
  const forecast = `<rect class="bar-fc" x="${fx}" y="${H - 22 - (2.0 / max) * (H - 40)}" width="${bw - 8}" height="${(2.0 / max) * (H - 40)}" rx="3"/><text class="bar-val" x="${fx + (bw - 8) / 2}" y="${H - 26 - (2.0 / max) * (H - 40)}">?</text><text class="bar-lab" x="${fx + (bw - 8) / 2}" y="${H - 8}">26</text>`;
  const mine = plan.risk.region ? `<div class="card block"><strong>What it means for ${esc(plan.place.city || 'you')}</strong><p class="small" style="margin:6px 0 0">${esc(plan.risk.region.name)}: El Niño usually makes it <strong>${esc(plan.risk.region.effect)}</strong> (${esc(plan.risk.region.season)}).</p></div>` : '';
  body.innerHTML = `<div class="card enso-card block" style="margin-top:12px">
      <span class="eyebrow">El Niño ${esc(t.current.season)}</span>
      <h3>${esc(t.current.headline)}</h3>
      <p class="small" style="margin:0"><strong>${esc(t.current.chance)}</strong> chance of a strong to very strong El Niño. Timing: ${esc(t.current.peak)}.</p>
      <p class="fineprint" style="margin:6px 0 0">${esc(t.current.source)}</p></div>
    <div class="tracker-facts">${t.facts.map((f) => `<div class="fact"><strong>${esc(f.big)}</strong><span>${esc(f.text)}</span><small>${esc(f.source)}</small></div>`).join('')}</div>
    <div class="card block"><strong>Every strong El Niño since 1950</strong>
      <svg class="oni-chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="Peak strength of strong El Niños since 1950">${bars}${forecast}</svg>
      <p class="small" style="margin:4px 0 0"><span class="key key-vs"></span>Very strong <span class="key key-s"></span>Strong <span class="key key-fc"></span>2026–27 forecast</p>
      <p class="fineprint">${esc(t.history_note)}</p></div>
    ${mine}
    <div class="sources">${t.sources.map((s) => `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>`).join('')}</div>`;
}

/* ---------------- shell ---------------- */
let currentView = 'plan';
function switchView(v) {
  currentView = v;
  $$('.view').forEach((el) => el.classList.toggle('active', el.id === `view-${v}`));
  $$('.tab').forEach((t) => t.classList.toggle('active', t.dataset.view === (v === 'org' ? 'help' : v)));
  if (v === 'map') renderMap();
  if (v === 'community') renderCommunity();
  if (v === 'news') renderNews();
  if (v === 'help' && plan) renderHelp();
  const sc = $(`#view-${v}`);
  if (sc) sc.scrollTop = 0;
}
$$('.tab').forEach((t) => t.addEventListener('click', () => switchView(t.dataset.view)));

function openSheet(html) {
  $('#sheetBody').innerHTML = html;
  $('#sheet').hidden = false;
}
function closeSheet() { $('#sheet').hidden = true; }
$$('#sheet [data-close]').forEach((el) => el.addEventListener('click', closeSheet));
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeSheet(); });

$('#placeBtn').addEventListener('click', async () => {
  openSheet(`<h2 id="sheetTitle">Your places</h2><p class="muted small">Make a plan for each place you care about, like a grandparent’s home.</p><ul class="plans-list" id="plansList"><li class="skeleton"><span></span></li></ul>
    <button class="btn btn-primary btn-wide" type="button" id="addPlace">Add another place</button>`);
  $('#addPlace').addEventListener('click', () => { closeSheet(); $('#addrInput').value = ''; $('#labelInput').value = ''; Object.keys(household).forEach((k) => { household[k] = false; }); $$('[data-hh]').forEach((b) => b.setAttribute('aria-pressed', 'false')); farm.grows = []; farm.workers = false; farm.creek = false; $$('[data-grow],[data-farm]').forEach((b) => b.setAttribute('aria-pressed', 'false')); showOnboard(2); });
  try {
    const list = await api('/api/plans');
    $('#plansList').innerHTML = list.map((p) => `<li><button type="button" data-plan="${p.id}" class="${p.id === state.current ? 'cur' : ''}"><span><strong>${esc(p.label)}</strong><small>${esc([p.city, p.state].filter(Boolean).join(', '))}</small></span><span class="risk-level lv-${p.level}">${p.score}</span></button></li>`).join('');
    $$('[data-plan]').forEach((b) => b.addEventListener('click', async () => {
      closeSheet();
      try { setPlan(await api(`/api/plan/${b.dataset.plan}`)); newsCache = null; switchView('plan'); } catch (e) { toast(e.message); }
    }));
  } catch (e) { $('#plansList').innerHTML = `<li class="notice">${esc(e.message)}</li>`; }
});
$('#refreshBtn').addEventListener('click', async () => {
  if (!plan) return;
  const b = $('#refreshBtn'); b.disabled = true;
  try { setPlan(await api(`/api/plan/${plan.id}`)); toast('Updated with the latest alerts.'); } catch (e) { toast(e.message); }
  b.disabled = false;
});

/* ---------------- boot ---------------- */
document.title = CFG.name;
$$('.app-name').forEach((el) => { el.textContent = CFG.name; });
(async function boot() {
  if (!state.current) { showOnboard(1); return; }
  showApp();
  if (plan) renderAll();
  try { setPlan(await api(`/api/plan/${state.current}`)); }
  catch (e) {
    if (/not found/i.test(e.message)) { state.current = null; state.cached = null; save(); plan = null; showOnboard(1); }
    else if (plan) toast('Offline. Showing your saved plan.');
    else showOnboard(1);
  }
})();
if ('serviceWorker' in navigator && location.protocol === 'https:') navigator.serviceWorker.register('sw.js').catch(() => {});
