/* Tideline web app. Talks to the Python API (backend/app.py).
   Sections: helpers · state · API · onboarding · plan · checklist · help · map + reports · news · boot */
'use strict';

const CFG = window.APP_CONFIG || { name: 'Tideline', apiBase: '' };
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
const STORE = 'tideline.v1';
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
  ['83%+', 'chance of a strong to very strong El Niño this winter', 'NOAA, Oct 2026'],
  ['1–2 ft', 'higher ocean levels than tide tables predict in San Mateo County', 'San Mateo County, Oct 2026'],
  ['2', 'emergencies already declared: California (Sept 21) and San Mateo County (Oct 20)', 'State of California · San Mateo County']
].map(([b, t, s]) => `<div class="fact"><b>${b}</b><span>${t}<small>${s}</small></span></div>`).join('');
$('#langSelect').innerHTML = LANGS.map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('');
$('#langSelect').value = state.language;
$('#langSelect').addEventListener('change', (e) => { state.language = e.target.value; save(); });
$('#obStart').addEventListener('click', () => obShow(2));
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
  obShow(3);
});
$('#useLocation').addEventListener('click', () => {
  if (!navigator.geolocation) { toast('Location isn’t available here. Type your address instead.'); return; }
  const b = $('#useLocation');
  b.disabled = true;
  navigator.geolocation.getCurrentPosition((pos) => {
    b.disabled = false;
    pendingPlace = { lat: pos.coords.latitude, lon: pos.coords.longitude };
    obShow(3);
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
  if (!pendingPlace) { obShow(2); return; }
  obShow(4);
  const steps = BUILD_STEPS.slice();
  if (state.language !== 'en') steps[5] = ['Writing your checklist', `In ${LANGS.find((l) => l[0] === state.language)[1]}`];
  $('#buildSteps').innerHTML = steps.map(([t, s]) => `<li><span class="dot"></span><span>${esc(t)}<small>${esc(s)}</small></span></li>`).join('');
  const lis = $$('#buildSteps li');
  let i = 0;
  const tick = setInterval(() => { if (i < lis.length - 1) { lis[i].classList.add('on'); lis[i].querySelector('.dot').innerHTML = icon('check'); i++; } }, 650);
  try {
    const p = await api('/api/plan', { method: 'POST', body: { ...pendingPlace, language: state.language, household, label: $('#labelInput').value.trim() || 'Home' } });
    clearInterval(tick);
    lis.forEach((li) => { li.classList.add('on'); li.querySelector('.dot').innerHTML = icon('check'); });
    await new Promise((r) => setTimeout(r, 450));
    setPlan(p);
    showApp();
    switchView('plan');
  } catch (err) {
    clearInterval(tick);
    obShow(2);
    toast(err.message, 5000);
  }
});

/* ---------------- plan ---------------- */
function setPlan(p) {
  plan = p;
  state.current = p.id;
  state.cached = p;
  save();
  $('#placeName').textContent = p.label || p.place.city || 'Home';
  renderAll();
}
function renderAll() {
  renderPlan(); renderList(); renderHelp();
  if (currentView === 'map') renderMap();
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
    <div>${t.priority === 1 && !t.done ? '<span class="first">Do first</span>' : ''}<strong>${esc(t.title)}</strong><p>${esc(t.why)}</p>
    ${t.link ? `<a href="${esc(t.link)}" target="_blank" rel="noopener">Open link</a>` : ''}</div></li>`;
}

function renderPlan() {
  const page = $('#planPage');
  if (!plan) { page.innerHTML = ''; return; }
  const r = plan.risk;
  const placeLine = [plan.place.city, plan.place.county ? `${plan.place.county} County` : null, plan.place.state].filter(Boolean).join(', ');
  const storm = (plan.alerts || []).filter((a) => a.storm_related);
  const next = plan.checklist.filter((t) => !t.done).slice(0, 3);
  const tides = r.king_tides || [];
  const langName = (LANGS.find((l) => l[0] === plan.language) || [])[1];
  page.innerHTML = `
    <section class="risk">
      <div class="risk-top">
        ${gaugeHTML(r.score, r.level)}
        <div>
          <span class="risk-level lv-${r.level}">${LEVEL_TEXT[r.level]}</span>
          <h2>Storm risk for ${esc(plan.label || 'this home')}</h2>
          <p class="risk-place">${esc(placeLine)}</p>
        </div>
      </div>
      <p class="risk-summary">${esc(plan.summary)}</p>
      ${plan.translated ? `<span class="risk-lang">Plan written in ${esc(langName)}</span>` : ''}
    </section>

    ${storm.length ? storm.map(alertHTML).join('') : `<div class="alert alert-none">${icon('ok')}<div><strong>No storm alerts right now</strong><p>We check the National Weather Service every time you open the app.</p></div></div>`}

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
      ${plan.missing && plan.missing.length ? `<p class="fineprint">Couldn’t reach: ${esc(plan.missing.join(', '))}. Pull to refresh later.</p>` : ''}
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
  page.innerHTML = `
    <h2>Help near ${esc(plan.place.city || 'you')}</h2>
    <p class="muted">Where to get sandbags, alerts and support, closest first.</p>
    ${h.alert_system ? `<section class="card help-alert block">
      <p class="eyebrow" style="color:rgba(255,255,255,.7)">Step one for everyone</p>
      <h3>Sign up for ${esc(h.alert_system.name)}</h3>
      <p>${esc(plan.place.county)} County’s official emergency alerts: evacuations, road closures and shelters, by text or call.</p>
      <a class="btn" href="${esc(h.alert_system.url)}" target="_blank" rel="noopener">Sign up</a>
    </section>` : ''}

    <section class="block">
      <div class="section-head"><h3>Sandbags</h3>${sb.length ? `<span class="muted small">Checked ${esc(fmtDay(h.checked))}</span>` : ''}</div>
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
      : `<div class="notice">We haven’t checked sandbag sites for this area yet. Call 211 or search your city’s public works page.</div>`}
    </section>

    ${h.county && h.county.length ? `<section class="block"><div class="section-head"><h3>${esc(plan.place.county)} County</h3></div>
      <ul class="res-list">${h.county.map(resHTML).join('')}</ul></section>` : ''}
    <section class="block"><div class="section-head"><h3>Anywhere in California</h3></div>
      <ul class="res-list">${h.statewide.map(resHTML).join('')}</ul></section>
    <p class="fineprint center">In an emergency, call 911.</p>`;
}
function resHTML(r) {
  return `<li><div class="res-top"><strong>${esc(r.name)}</strong></div><p>${esc(r.what)}</p>
    <div class="res-actions">${r.phone ? `<a href="tel:${esc(r.phone)}">Call ${esc(r.phone)}</a>` : ''}${r.url ? `<a href="${esc(r.url)}" target="_blank" rel="noopener">Open</a>` : ''}</div></li>`;
}

/* ---------------- map + community reports ---------------- */
let map = null, layer = null, reports = [];
const KINDS = { flooding: 'Flooded street', drain: 'Clogged storm drain', landslide: 'Landslide or mudslide', tree: 'Fallen tree', power: 'Downed power line', road: 'Road damage', other: 'Other storm problem' };
function pinIcon(cls, svg) {
  return L.divIcon({ className: '', html: `<div class="pin ${cls}"><svg viewBox="0 0 24 24">${svg}</svg></div>`, iconSize: [30, 30], iconAnchor: [15, 30] });
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
  (plan.help.sandbags || []).forEach((s) => L.marker([s.lat, s.lon], { icon: pinIcon('pin-bag', ICON.bag) }).addTo(layer)
    .bindPopup(`<b>Sandbags: ${esc(s.name)}</b><br>${esc(s.address)}<br><a href="${mapsLink(s.address)}" target="_blank" rel="noopener">Directions</a>`));
  $('#mapCard').innerHTML = `<span><i style="background:var(--ocean)"></i>Your place</span><span><i style="background:#b86a00"></i>Sandbags</span><span><i style="background:#c0392b"></i>Neighbor reports</span>`;
  try {
    reports = await api(`/api/reports?lat=${plan.lat}&lon=${plan.lon}&miles=10`);
  } catch (e) { reports = []; }
  reports.forEach((r) => L.marker([r.lat, r.lon], { icon: pinIcon('pin-r' + r.severity, ICON.drop) }).addTo(layer).on('click', () => openReport(r)));
  setTimeout(() => map.invalidateSize(), 50);
}
async function openReport(r) {
  openSheet(`<h2 id="sheetTitle">${esc(r.title)}</h2>
    <div id="repPhoto"></div>
    <p class="muted small">${esc(KINDS[r.kind] || 'Storm problem')} · ${esc(fmtDay(r.created_at, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }))}${r.ai_checked ? ' · checked by AI' : ''}</p>
    ${r.note ? `<p>${esc(r.note)}</p>` : ''}
    <p><strong>${r.confirmations}</strong> ${r.confirmations === 1 ? 'neighbor has' : 'neighbors have'} confirmed this.</p>
    <button class="btn btn-primary btn-wide" type="button" id="confirmBtn">I see this too</button>
    <button class="btn btn-ghost btn-wide" type="button" id="clearBtn">It’s cleared now</button>`);
  if (r.has_photo) {
    api(`/api/reports/${r.id}/photo`).then((d) => { const el = $('#repPhoto'); if (el) el.innerHTML = `<img class="report-photo" src="${d.photo}" alt="Photo of ${esc(r.title)}">`; }).catch(() => {});
  }
  $('#confirmBtn').addEventListener('click', async () => {
    try { const d = await api(`/api/reports/${r.id}/confirm`, { method: 'POST' }); r.confirmations = d.confirmations; closeSheet(); toast('Thanks. Your neighbors can see it’s confirmed.'); } catch (e) { toast(e.message); }
  });
  $('#clearBtn').addEventListener('click', async () => {
    try { await api(`/api/reports/${r.id}/clear`, { method: 'POST' }); closeSheet(); renderMap(); toast('Marked as cleared.'); } catch (e) { toast(e.message); }
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
$('#reportFab').addEventListener('click', () => {
  const draft = { kind: 'flooding', severity: 2, photo: null, ai: false, lat: map ? map.getCenter().lat : plan.lat, lon: map ? map.getCenter().lng : plan.lon };
  openSheet(`<h2 id="sheetTitle">Report a storm problem</h2>
    <p class="muted small">It goes on the map where the map is centered, so neighbors can avoid it. Don’t take photos in dangerous spots.</p>
    <label class="photo-drop" id="drop"><input type="file" id="repFile" accept="image/*" capture="environment">${icon('camera')}<strong>Add a photo</strong><span class="small">AI will label it for you</span></label>
    <img class="photo-prev" id="repPrev" alt="" hidden>
    <div class="ai-note" id="aiNote" hidden></div>
    <label class="field-label" for="repKind">What is it?</label>
    <select id="repKind">${Object.entries(KINDS).map(([k, v]) => `<option value="${k}">${esc(v)}</option>`).join('')}</select>
    <label class="field-label" for="repTitle">Short title</label>
    <input id="repTitle" type="text" maxlength="60" placeholder="e.g. Water across Main St">
    <label class="field-label">How bad?</label>
    <div class="sev-row" id="sevRow">${[[1, 'Minor'], [2, 'Avoid it'], [3, 'Dangerous']].map(([v, t]) => `<button type="button" data-sev="${v}" aria-pressed="${v === 2}">${t}</button>`).join('')}</div>
    <button class="btn btn-primary btn-wide" type="button" id="repSend">Post to map</button>`);
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
  $('#repSend').addEventListener('click', async () => {
    const btn = $('#repSend');
    btn.disabled = true;
    try {
      await api('/api/reports', { method: 'POST', body: { lat: draft.lat, lon: draft.lon, kind: $('#repKind').value, title: $('#repTitle').value.trim(), severity: draft.severity, photo: draft.photo, ai_checked: draft.ai, county: plan.place.county } });
      closeSheet(); renderMap(); toast('Posted. Thanks for looking out for your neighbors.');
    } catch (err) { btn.disabled = false; toast(err.message); }
  });
});

/* ---------------- news ---------------- */
let newsTab = 'local', newsCache = null, regionsCache = null;
async function renderNews() {
  const page = $('#newsPage');
  if (!plan) return;
  page.innerHTML = `<h2>El Niño news</h2>
    <div class="seg" role="group" aria-label="News">${[['local', `Near ${plan.place.county || 'you'}`], ['world', 'Around the world']].map(([k, t]) => `<button type="button" data-news="${k}" aria-pressed="${k === newsTab}">${esc(t)}</button>`).join('')}</div>
    <div id="newsBody"><div class="card skeleton"><span></span><span></span><span></span></div></div>`;
  $$('[data-news]', page).forEach((b) => b.addEventListener('click', () => { newsTab = b.dataset.news; renderNews(); }));
  const body = $('#newsBody');
  if (newsTab === 'world') {
    try { regionsCache = regionsCache || await api('/api/regions'); } catch (e) { body.innerHTML = `<div class="notice">${esc(e.message)}</div>`; return; }
    body.innerHTML = `<p class="muted" style="margin-top:12px">The same El Niño brings different dangers to different places. ${esc(regionsCache.note)}</p>
      ${regionsCache.regions.map((r) => `<div class="region ${r.id === 'california' && plan.place.state === 'CA' ? 'mine' : ''}">
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

/* ---------------- shell ---------------- */
let currentView = 'plan';
function switchView(v) {
  currentView = v;
  $$('.view').forEach((el) => el.classList.toggle('active', el.id === `view-${v}`));
  $$('.tab').forEach((t) => t.classList.toggle('active', t.dataset.view === v));
  if (v === 'map') renderMap();
  if (v === 'news') renderNews();
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
  $('#addPlace').addEventListener('click', () => { closeSheet(); $('#addrInput').value = ''; $('#labelInput').value = ''; Object.keys(household).forEach((k) => { household[k] = false; }); $$('[data-hh]').forEach((b) => b.setAttribute('aria-pressed', 'false')); showOnboard(2); });
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
