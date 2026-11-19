"use strict";
// Super Agente - interfaccia. Nessuna dipendenza esterna.
const $ = (s) => document.querySelector(s);
// Salvataggio doppio (localStorage + IndexedDB) e richiesta di archivio "persistente",
// cosi' il telefono non cancella le notizie lette/le stelle anche dopo giorni o settimane.
const idb = {
  db: null,
  open() {
    return new Promise((ok) => {
      try {
        const r = indexedDB.open("super-agente", 1);
        r.onupgradeneeded = () => r.result.createObjectStore("kv");
        r.onsuccess = () => { idb.db = r.result; ok(idb.db); };
        r.onerror = () => ok(null);
      } catch { ok(null); }
    });
  },
  get(k) {
    return new Promise((ok) => {
      if (!idb.db) return ok(undefined);
      try { const q = idb.db.transaction("kv").objectStore("kv").get(k); q.onsuccess = () => ok(q.result); q.onerror = () => ok(undefined); } catch { ok(undefined); }
    });
  },
  set(k, v) { try { if (idb.db) idb.db.transaction("kv", "readwrite").objectStore("kv").put(v, k); } catch { /* ignora */ } },
};
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* ignora */ } idb.set(k, v); },
};
try { navigator.storage && navigator.storage.persist && navigator.storage.persist(); } catch { /* ignora */ }
// all'avvio recupera da IndexedDB eventuali dati che localStorage ha perso e li unisce
idb.open().then(async () => {
  let cambiato = false;
  for (const k of ["lette", "stelle"]) {
    const salvate = await idb.get(k);
    if (Array.isArray(salvate)) {
      const set = state[k];
      for (const id of salvate) if (!set.has(id)) { set.add(id); cambiato = true; }
    }
    store.set(k, [...state[k]]);
  }
  if (cambiato && state.news.length) renderTutto();
});
const state = {
  news: [], aree: {}, status: null, professioni: {}, gruppiProf: [], vista: "prof", prof: "tutte", nicchia: store.get("nicchia", "edilizia"),
  aperte: new Set(), limiti: {}, sotto: {}, areaArchivio: "tutte", soloNorm: false, query: "", mostrati: 40,
  lette: new Set(store.get("lette", [])), stelle: new Set(store.get("stelle", [])),
  ultimaVisita: store.get("ultimaVisita", null),
};

const GIORNI = ["domenica", "lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato"];
const MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];

const dataDi = (n) => new Date(n.pubblicata || n.visto);
function fa(d) {
  const m = Math.round((Date.now() - d.getTime()) / 60000);
  if (m < 1) return "ora";
  if (m < 60) return `${m} min fa`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h} h fa`;
  const g = Math.round(h / 24);
  return g === 1 ? "ieri" : `${g} giorni fa`;
}
function etichettaGiorno(d) {
  const oggi = new Date(); oggi.setHours(0, 0, 0, 0);
  const x = new Date(d); x.setHours(0, 0, 0, 0);
  const diff = Math.round((oggi - x) / 86400000);
  if (diff === 0) return "Oggi";
  if (diff === 1) return "Ieri";
  return `${GIORNI[d.getDay()]} ${d.getDate()} ${MESI[d.getMonth()]}`;
}
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const nome = (a) => (a.startsWith("p:") ? (state.professioni[a.slice(2)]?.emoji || "") + " " + (state.professioni[a.slice(2)]?.nome || a) : state.aree[a]?.nome || a);
const colore = (a) => state.aree[a]?.colore || "#4a6fa5";

function card(n) {
  const letta = state.lette.has(n.id);
  const nuovo = !letta && state.ultimaVisita && new Date(n.visto) > new Date(state.ultimaVisita);
  const stella = state.stelle.has(n.id);
  const luogoB = n.luogo ? `<span class="badge luogo">📍 ${esc(n.luogo)}</span>` : "";
  const badge = luogoB + n.aree.filter((a) => a !== "altro" || !n.luogo).map((a) => `<span class="badge" style="--c:${colore(a)}">${esc(nome(a))}</span>`).join("");
  return `<article class="card${letta ? " letta" : ""}" data-id="${n.id}" style="--c:${colore(n.aree[0])}">
    <div class="riga">${badge}${(n.prof || []).slice(0, 3).map((p) => state.professioni[p] ? `<span class="badge pf" title="${esc(state.professioni[p].nome)}">${state.professioni[p].emoji} ${esc(state.professioni[p].nome)}</span>` : "").join("")}${n.normativa ? `<span class="badge norm">${["edilizia"].includes(n.nicchia || "edilizia") ? "Normativa" : "Ufficiale"}</span>` : ""}${nuovo ? '<span class="nuovo" title="Nuova"></span>' : ""}</div>
    <h3 class="titolo">${esc(n.titolo)}</h3>
    ${n.sintesi ? `<p class="sintesi">${esc(n.sintesi)}</p>` : ""}
    <div class="piede"><span>${esc(n.fonte_nome)} · ${fa(dataDi(n))}</span>
      <button class="stella${stella ? " on" : ""}" data-star="${n.id}" aria-label="Salva">${stella ? "★" : "☆"}</button></div>
  </article>`;
}

// Suddivisione dell'Edilizia in gruppi (le aree dichiarano il proprio "gruppo" in aree.json)
const GRUPPI = { edilizia: [["soldi", "💶 Bonus, fisco e CAF"], ["pratiche", "📑 Pratiche e burocrazia"], ["tecnica", "🔧 Tecnica e cantiere"], ["mercato", "🏠 Immobiliare, energia e mobilità"], ["studi", "⚖️ Legale, management e lavoro"], ["altri", "🌐 Altri settori e professioni"]] };
const gruppoDi = (a) => (a === "locale" ? "pratiche" : state.aree[a]?.gruppo || null);
const PRIMA = { soldi: ["bonus", "imprese"], pratiche: ["locale", "edilizia", "catasto", "appalti"] };
const profOk = (n) => state.vista === "prof" || state.prof === "tutte" || (n.prof || []).includes(state.prof);
const inNicchia = (n) => (n.nicchia || "edilizia") === state.nicchia;
const areaNicchia = (a) => (state.aree[a]?.nicchia || "edilizia") === state.nicchia;

function filtra({ area, query, soloNorm }) {
  const q = query.trim().toLowerCase();
  return state.news.filter((n) => {
    if (area !== "stelle" && !inNicchia(n)) return false;
    if (area !== "stelle" && state.nicchia === "edilizia" && !profOk(n)) return false;
    if (area === "stelle") { if (!state.stelle.has(n.id)) return false; }
    else if (area === "tutte") { if (n.aree.length === 1 && n.aree[0] === "altro" && !n.luogo) return false; }
    else if (area.startsWith("p:")) { if (!(n.prof || []).includes(area.slice(2))) return false; }
    else if (area.startsWith("g:")) { const g = area.slice(2); if (!n.aree.some((a) => gruppoDi(a) === g) && !(g === "pratiche" && n.luogo)) return false; }
    else if (area === "locale") { if (!n.luogo) return false; }
    else if (area === "altro") { if (n.luogo || !n.aree.includes("altro")) return false; }
    else if (!n.aree.includes(area)) return false;
    if (soloNorm && !n.normativa) return false;
    if (q && !(n.titolo + " " + (n.sintesi || "") + " " + n.fonte_nome).toLowerCase().includes(q)) return false;
    return true;
  });
}

function chips(el, corrente, onPick) {
  const base = state.news.filter(inNicchia).filter((n) => state.nicchia !== "edilizia" || profOk(n));
  const conta = (a) => base.filter((n) => a === "locale" ? !!n.luogo : a === "altro" ? (!n.luogo && n.aree.includes("altro")) : n.aree.includes(a)).length;
  const voci = [["tutte", "Tutte", null, base.filter((n) => !(n.aree.length === 1 && n.aree[0] === "altro" && !n.luogo)).length],
    ["stelle", "★ Salvate", null, state.stelle.size]];
  (GRUPPI[state.nicchia] || []).forEach(([g, l]) => voci.push(["g:" + g, l, null, base.filter((n) => n.aree.some((a) => gruppoDi(a) === g) || (g === "pratiche" && n.luogo)).length]));
  if (state.aree.locale && state.nicchia === "edilizia") voci.push(["locale", nome("locale"), colore("locale"), conta("locale")]);
  Object.keys(state.aree).filter((a) => a !== "altro" && a !== "locale" && areaNicchia(a)).forEach((a) => voci.push([a, nome(a), colore(a), conta(a)]));
  voci.push(["altro", "Altro", colore("altro"), conta("altro")]);
  el.innerHTML = voci.map(([k, l, c, n]) =>
    `<button class="chip${k === corrente ? " on" : ""}" data-k="${k}">${c ? `<i style="background:${c}"></i>` : ""}${esc(l)} <small>${n}</small></button>`).join("");
  el.onclick = (e) => { const b = e.target.closest(".chip"); if (b) onPick(b.dataset.k); };
}

function vuoto(msg, sub) { return `<div class="vuoto"><b>${msg}</b>${sub || ""}</div>`; }

function sezione(k, listaTot) {
  const aperta = state.aperte.has(k);
  const sottoDef = state.aree[k]?.sotto || {};
  const selSotto = state.sotto[k] || "";
  let lista = listaTot;
  let chipsSotto = "";
  if (aperta && k.startsWith("p:")) {
    const sel = state.sotto[k] || "";
    if (sel) lista = listaTot.filter((n) => n.aree.includes(sel));
    const ar = {}; listaTot.forEach((n) => n.aree.forEach((a) => { if (a !== "altro" && state.aree[a]) ar[a] = (ar[a] || 0) + 1; }));
    chipsSotto = `<div class="sotto"><button class="chip s${sel ? "" : " on"}" data-sotto="${k}|">Tutte <small>${listaTot.length}</small></button>` +
      Object.entries(ar).sort((a, b) => b[1] - a[1]).map(([a, c]) => `<button class="chip s${sel === a ? " on" : ""}" data-sotto="${k}|${a}">${esc(nome(a))} <small>${c}</small></button>`).join("") + `</div>`;
  } else if (aperta && Object.keys(sottoDef).length) {
    if (selSotto) lista = listaTot.filter((n) => (n.sotto || []).includes(`${k}.${selSotto}`));
    const cnt = (sid) => listaTot.filter((n) => (n.sotto || []).includes(`${k}.${sid}`)).length;
    chipsSotto = `<div class="sotto">` +
      `<button class="chip s${selSotto ? "" : " on"}" data-sotto="${k}|">Tutte <small>${listaTot.length}</small></button>` +
      Object.entries(sottoDef).map(([sid, nm]) => `<button class="chip s${selSotto === sid ? " on" : ""}" data-sotto="${k}|${sid}">${esc(nm)} <small>${cnt(sid)}</small></button>`).join("") +
      `</div>`;
  }
  const nuovi = lista.filter((n) => !state.lette.has(n.id) && state.ultimaVisita && new Date(n.visto) > new Date(state.ultimaVisita)).length;
  const titolo = k === "stelle" ? "★ Salvate" : nome(k).trim();
  const col = k === "stelle" ? "#f0b429" : colore(k);
  let corpo = "";
  if (aperta) {
    const lim = state.limiti[k] || 25;
    let ultimo = "";
    for (const n of lista.slice(0, lim)) {
      const g = etichettaGiorno(dataDi(n));
      if (g !== ultimo) { corpo += `<div class="giorno">${esc(g)}</div>`; ultimo = g; }
      corpo += card(n);
    }
    if (lista.length > lim) corpo += `<button class="more" data-piu="${k}">Mostra altre ${Math.min(25, lista.length - lim)}</button>`;
    corpo = `<div class="sez-corpo">${chipsSotto}${corpo || vuoto("Nessuna notizia")}</div>`;
  }
  return `<section class="sez${aperta ? " aperta" : ""}" style="--c:${col}">
    <button class="sez-head" data-sez="${k}" aria-expanded="${aperta}">
      <span class="sez-titolo">${esc(titolo)}</span>
      <span class="sez-meta">${nuovi ? `<b class="pill">${nuovi} nuove</b>` : ""}<small>${lista.length}</small></span>
      <span class="freccia" aria-hidden="true">›</span>
    </button>${corpo}</section>`;
}

function renderNovita() {
  const box = $("#lista-novita");
  if (!state.news.length) { box.innerHTML = vuoto("Ancora nessuna notizia", "Il primo aggiornamento automatico è in arrivo (ogni ora)."); return; }
  const tutteAree = Object.keys(state.aree).filter((a) => a !== "altro" && a !== "locale" && areaNicchia(a));
  let chiavi = ["stelle"];
  if (state.nicchia === "edilizia" && state.vista === "prof" && state.gruppiProf.length) {
    for (const g of state.gruppiProf) {
      chiavi.push("#" + g.nome, ...Object.keys(state.professioni).filter((p) => state.professioni[p].gruppo === g.id).map((p) => "p:" + p));
    }
  } else if (GRUPPI[state.nicchia]) {
    for (const [g, l] of GRUPPI[state.nicchia]) {
      const lista = [...(g === "pratiche" ? ["locale"] : []), ...tutteAree.filter((a) => gruppoDi(a) === g)];
      const pri = PRIMA[g] || [];
      lista.sort((a, b) => (pri.indexOf(a) < 0 ? 99 : pri.indexOf(a)) - (pri.indexOf(b) < 0 ? 99 : pri.indexOf(b)));
      chiavi.push("#" + l, ...lista);
    }
    chiavi.push(...tutteAree.filter((a) => !gruppoDi(a)));
  } else chiavi.push(...tutteAree);
  if (!(state.nicchia === "edilizia" && state.vista === "prof")) chiavi.push("altro");
  let out = "";
  let titoloPendente = "";
  for (const k of chiavi) {
    if (k.startsWith("#")) { titoloPendente = k.slice(1); continue; }
    const lista = filtra({ area: k, query: "", soloNorm: state.soloNorm });
    if (!lista.length && k !== "stelle" && (k === "altro" || k.startsWith("p:"))) continue;
    if (k === "stelle" && !state.stelle.size) continue;
    if (k === "locale" && !state.aree.locale) continue;
    if (titoloPendente && lista.length) { out += `<div class="gruppo-titolo">${esc(titoloPendente)}</div>`; titoloPendente = ""; }
    out += sezione(k, lista);
  }
  box.innerHTML = out || vuoto("Nessuna notizia", "Togli il filtro \"Solo novità normative\".");
}

function renderArchivio() {
  chips($("#chips-archivio"), state.areaArchivio, (k) => { state.areaArchivio = k; state.mostrati = 40; renderArchivio(); });
  const lista = filtra({ area: state.areaArchivio, query: state.query, soloNorm: false });
  $("#lista-archivio").innerHTML = lista.length ? lista.slice(0, state.mostrati).map(card).join("") : vuoto("Nessun risultato");
  $("#piu").hidden = lista.length <= state.mostrati;
}

const ETICHETTE_TIPO = { ufficiale: "Fonti ufficiali", ente: "Enti", ordine: "Ordini e associazioni", stampa: "Stampa tecnica" };
const ETICHETTE_STATO = { ok: "Attiva (feed)", ok_scraping: "Attiva (lettura pagina, meno precisa)", ok_indiretto: "Attiva (indiretta via Google News: sito che blocca i lettori)", errore: "Non raggiungibile", vuoto: "Nessun contenuto letto" };
function renderFonti() {
  const s = state.status;
  const tutte = s ? s.fonti : [];
  if (s) { s.fonti = tutte.filter((f) => (f.nicchia || "edilizia") === state.nicchia); }
  if (!s || !s.fonti.length) { $("#fonti-riepilogo").innerHTML = vuoto("Nessun dato sulle fonti", "Compare dopo il primo aggiornamento."); return; }
  const problemi = s.fonti.filter((f) => f.stato === "errore" || f.stato === "vuoto").length;
  const scrap = s.fonti.filter((f) => f.stato === "ok_scraping" || f.stato === "ok_indiretto").length;
  $("#fonti-riepilogo").innerHTML = `<b>${s.fonti.filter((f) => ['ok', 'ok_scraping', 'ok_indiretto'].includes(f.stato)).length} / ${s.fonti.length} fonti attive</b>
    <p>${problemi ? `${problemi} da sistemare` : "Nessun problema"}${scrap ? ` · ${scrap} lette in modo approssimativo` : ""}. Ultimo controllo: ${s.aggiornato ? fa(new Date(s.aggiornato)) : "—"}.</p>`;
  let out = "";
  for (const tipo of Object.keys(ETICHETTE_TIPO)) {
    const gruppo = s.fonti.filter((f) => f.tipo === tipo);
    if (!gruppo.length) continue;
    out += `<div class="gruppo">${ETICHETTE_TIPO[tipo]}</div>`;
    out += gruppo.map((f) => `<div class="fonte"><span class="dot ${f.stato}"></span><div>
      <a href="${esc(f.home)}" target="_blank" rel="noopener">${esc(f.nome)}</a>
      <div class="m">${ETICHETTE_STATO[f.stato] || f.stato} · letti ${f.letti} · ultima novità: ${f.ultimo_nuovo ? fa(new Date(f.ultimo_nuovo)) : "mai"}</div>
      ${f.errore ? `<div class="m err">${esc(f.errore)}${f.falliti_di_fila > 3 ? ` (da ${f.falliti_di_fila} controlli)` : ""}</div>` : ""}
      ${f.nota ? `<div class="m">${esc(f.nota)}</div>` : ""}</div></div>`).join("");
  }
  $("#lista-fonti").innerHTML = out;
  s.fonti = tutte;
}

function renderProf() {
  const el = $("#prof-bar");
  const ids = Object.keys(state.professioni);
  if (state.nicchia !== "edilizia" || !ids.length) { el.hidden = true; return; }
  el.hidden = false;
  let h = `<button class="chip${state.vista === "prof" ? " on" : ""}" data-vista="prof">👤 Per professione</button><button class="chip${state.vista === "arg" ? " on" : ""}" data-vista="arg">📚 Per argomento</button>`;
  if (state.vista === "arg") {
    const base = state.news.filter(inNicchia);
    const conta = (p) => base.filter((n) => (n.prof || []).includes(p)).length;
    h += [["tutte", "Tutte le professioni", base.length]].concat(ids.map((p) => [p, `${state.professioni[p].emoji} ${state.professioni[p].nome}`, conta(p)]).filter((v) => v[2] > 0 || v[0] === state.prof))
      .map(([k, l, n]) => `<button class="chip${k === state.prof ? " on" : ""}" data-prof="${k}">${esc(l)} <small>${n}</small></button>`).join("");
  }
  el.innerHTML = h;
}
function renderTutto() { renderProf(); renderNovita(); renderArchivio(); renderFonti(); }

const VERSIONE_APP = "19";

async function carica(forza) {
  const q = `?t=${Date.now()}`;
  const j = async (f) => {
    const r = await fetch(`data/${f}.json${q}`, { cache: "no-store" });
    if (!r.ok) throw new Error(`${f}: ${r.status}`);
    return r.json();
  };
  try {
    const [news, aree, status, prof] = await Promise.all([j("news"), j("aree"), j("status").catch(() => null), j("professioni").catch(() => ({}))]);
    state.professioni = prof.professioni || {}; state.gruppiProf = prof.gruppi || [];
    if (!Array.isArray(news.notizie)) throw new Error("dati non validi");
    state.news = news.notizie; state.aree = aree; state.status = status;
    $("#aggiornato").textContent = (news.aggiornato ? `Aggiornato ${fa(new Date(news.aggiornato))}` : "Super Agente") + ` · v${VERSIONE_APP}`;
    renderTutto();
  } catch (err) {
    if (!state.news.length) {
      $("#lista-novita").innerHTML = vuoto("Non riesco a caricare le notizie", "Controlla la connessione e tocca ⟳ in alto.");
      $("#aggiornato").textContent = `Non aggiornato · v${VERSIONE_APP}`;
    }
  }
}

document.addEventListener("click", (e) => {
  const vi = e.target.closest("[data-vista]");
  if (vi) { state.vista = vi.dataset.vista; state.prof = "tutte"; state.aperte.clear(); renderTutto(); return; }
  const pf = e.target.closest("[data-prof]");
  if (pf) { state.prof = pf.dataset.prof; state.mostrati = 40; renderTutto(); return; }
  const sez = e.target.closest("[data-sez]");
  if (sez) {
    const k = sez.dataset.sez;
    state.aperte.has(k) ? state.aperte.delete(k) : state.aperte.add(k);
    renderNovita();
    return;
  }
  const so = e.target.closest("[data-sotto]");
  if (so) {
    const [k, sid] = so.dataset.sotto.split("|");
    state.sotto[k] = sid; state.limiti[k] = 25;
    renderNovita();
    return;
  }
  const piu = e.target.closest("[data-piu]");
  if (piu) { state.limiti[piu.dataset.piu] = (state.limiti[piu.dataset.piu] || 25) + 25; renderNovita(); return; }
  const star = e.target.closest("[data-star]");
  if (star) {
    e.stopPropagation();
    const id = star.dataset.star;
    state.stelle.has(id) ? state.stelle.delete(id) : state.stelle.add(id);
    store.set("stelle", [...state.stelle]);
    renderTutto();
    return;
  }
  const c = e.target.closest(".card");
  if (c) {
    const n = state.news.find((x) => x.id === c.dataset.id);
    if (!n) return;
    state.lette.add(n.id); store.set("lette", [...state.lette].slice(-20000));
    c.classList.add("letta");
    window.open(n.link, "_blank", "noopener");
  }
});
function aggiornaNicchie() {
  document.querySelectorAll("#nicchie button").forEach((b) => b.classList.toggle("on", b.dataset.n === state.nicchia));
  $("#solo-norm-label").hidden = !["edilizia"].includes(state.nicchia);
}
document.querySelectorAll("#nicchie button").forEach((b) => b.addEventListener("click", () => {
  state.nicchia = b.dataset.n; store.set("nicchia", state.nicchia);
  state.areaArchivio = "tutte"; state.mostrati = 40; state.aperte.clear(); state.prof = "tutte";
  aggiornaNicchie(); renderTutto(); window.scrollTo(0, 0);
}));
aggiornaNicchie();
$("#solo-norm").addEventListener("change", (e) => { state.soloNorm = e.target.checked; renderNovita(); });
$("#cerca").addEventListener("input", (e) => { state.query = e.target.value; state.mostrati = 40; renderArchivio(); });
$("#piu").addEventListener("click", () => { state.mostrati += 40; renderArchivio(); });
$("#btn-refresh").addEventListener("click", async (e) => {
  const b = e.currentTarget; b.classList.add("spin");
  try { await carica(true); } finally { b.classList.remove("spin"); }
});
document.querySelectorAll(".bottom button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll(".bottom button").forEach((x) => x.classList.toggle("on", x === b));
  document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t.id === `tab-${b.dataset.tab}`));
  window.scrollTo(0, 0);
}));

carica(false).then(() => store.set("ultimaVisita", new Date().toISOString()));
document.addEventListener("visibilitychange", () => { if (!document.hidden) carica(true); });
if ("serviceWorker" in navigator) {
  // quando esce una versione nuova, l'app si ricarica da sola una volta
  let primo = !navigator.serviceWorker.controller;
  navigator.serviceWorker.addEventListener("controllerchange", () => { if (primo) { primo = false; return; } location.reload(); });
  navigator.serviceWorker.register("sw.js", { updateViaCache: "none" }).then((r) => r.update()).catch(() => {});
}
