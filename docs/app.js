"use strict";
// Rassegna - interfaccia. Nessuna dipendenza esterna.
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
const nome = (a) => (a === "p:_altre" ? "Notizie generali" : a.startsWith("p:") ? (state.professioni[a.slice(2)]?.emoji || "") + " " + (state.professioni[a.slice(2)]?.nome || a) : state.aree[a]?.nome || a);
const colore = (a) => state.aree[a]?.colore || "#4a6fa5";

function card(n) {
  const letta = state.lette.has(n.id);
  const nuovo = !letta && state.ultimaVisita && new Date(n.visto) > new Date(state.ultimaVisita);
  const stella = state.stelle.has(n.id);
  const luogoB = n.luogo ? `<span class="badge luogo">📍 ${esc(n.luogo)}</span>` : "";
  const badge = luogoB + n.aree.filter((a) => a !== "altro" || !n.luogo).map((a) => `<span class="badge" style="--c:${colore(a)}">${esc(nome(a))}</span>`).join("");
  return `<article class="card${letta ? " letta" : ""}" data-id="${n.id}" style="--c:${colore(n.aree[0])}">
    <div class="riga">${badge}${n.prezzo ? `<span class="badge prezzo">${esc(n.prezzo)}</span>` : ""}${(n.prof || []).slice(0, 3).map((p) => state.professioni[p] ? `<span class="badge pf" title="${esc(state.professioni[p].nome)}">${state.professioni[p].emoji} ${esc(state.professioni[p].nome)}</span>` : "").join("")}${n.tradotto ? '<span class="badge pf" title="Fonte straniera, titolo tradotto automaticamente">🌐 Tradotto</span>' : ""}${n.normativa ? `<span class="badge norm">${["edilizia"].includes(n.nicchia || "edilizia") ? "Normativa" : "Ufficiale"}</span>` : ""}${nuovo ? '<span class="nuovo" title="Nuova"></span>' : ""}</div>
    <h3 class="titolo">${esc(n.titolo)}</h3>
    ${n.sintesi ? `<p class="sintesi">${esc(n.sintesi)}</p>` : ""}
    <div class="piede"><span>${esc(n.fonte_nome)}${(n.altre_fonti || []).length ? ` +${n.altre_fonti.length}` : ""} · ${fa(dataDi(n))}</span>
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

// Ogni notizia compare in UNA sola sezione di Novità: la sua "sezione principale"
function sezPrincipale(n) {
  if (state.nicchia === "edilizia" && state.vista === "prof") return "p:" + ((n.prof || [])[0] || "_altre");
  if (n.luogo && state.aree.locale && state.nicchia === "edilizia") return "locale";
  const a = (n.aree || []).find((x) => x !== "altro" && state.aree[x]);
  return a || "altro";
}

function filtra({ area, query, soloNorm, primario }) {
  const q = query.trim().toLowerCase();
  return state.news.filter((n) => {
    if (area !== "stelle" && !inNicchia(n)) return false;
    if (area !== "stelle" && state.nicchia === "edilizia" && !profOk(n)) return false;
    if (area === "stelle") { if (!state.stelle.has(n.id)) return false; }
    else if (area === "tutte") { if (n.aree.length === 1 && n.aree[0] === "altro" && !n.luogo) return false; }
    else if (area.startsWith("p:")) { const id = area.slice(2); if (id === "_altre" ? (n.prof || []).length : !(n.prof || []).includes(id)) return false; }
    else if (area.startsWith("g:")) { const g = area.slice(2); if (!n.aree.some((a) => gruppoDi(a) === g) && !(g === "pratiche" && n.luogo)) return false; }
    else if (area === "locale") { if (!n.luogo) return false; }
    else if (area === "altro") { if (n.luogo || !n.aree.includes("altro")) return false; }
    else if (!n.aree.includes(area)) return false;
    if (primario && area !== "stelle" && sezPrincipale(n) !== area) return false;
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
  document.body.classList.toggle("pol-quadro", state.nicchia === "politica" && state.vistaPol === "quadro");
  if (state.nicchia === "politica" && state.vistaPol === "quadro") { box.innerHTML = renderPolitica(); return; }
  if (state.nicchia === "auto" && state.vistaAuto !== "notizie" && state.news.length) { box.innerHTML = renderOfferte(); return; }
  if (!state.news.length) { box.innerHTML = vuoto("Ancora nessuna notizia", "Il primo aggiornamento automatico è in arrivo (ogni ora)."); return; }
  const tutteAree = Object.keys(state.aree).filter((a) => a !== "altro" && a !== "locale" && areaNicchia(a));
  let chiavi = ["stelle"];
  if (state.nicchia === "edilizia" && state.vista === "prof" && state.gruppiProf.length) {
    for (const g of state.gruppiProf) {
      chiavi.push("#" + g.nome, ...Object.keys(state.professioni).filter((p) => state.professioni[p].gruppo === g.id).map((p) => "p:" + p));
    }
    chiavi.push("#📰 Generali", "p:_altre");
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
    const lista = filtra({ area: k, query: "", soloNorm: state.soloNorm, primario: true });
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
    out += gruppo.map((f) => `<div class="fonte tap" ${reg(`<h2 class="pop-t">${esc(f.nome)}</h2><div class="pop-box">${pRiga("Stato", esc(ETICHETTE_STATO[f.stato] || f.stato))}${pRiga("Articoli letti", f.letti)}${pRiga("Ultima novità", f.ultimo_nuovo ? fa(new Date(f.ultimo_nuovo)) : "mai")}${pRiga("Tipo", esc(ETICHETTE_TIPO[f.tipo] || f.tipo || ""))}</div>${f.errore ? `<p class="pop-p mute">Problema rilevato: ${esc(f.errore)}</p>` : ""}${f.nota ? `<p class="pop-p">${esc(f.nota)}</p>` : ""}<div class="pop-az">${pBtn(f.home, "Apri il sito ↗")}</div>`)}><span class="dot ${f.stato}"></span><div>
      <b>${esc(f.nome)}</b>
      <div class="m">${ETICHETTE_STATO[f.stato] || f.stato} · letti ${f.letti} · ultima novità: ${f.ultimo_nuovo ? fa(new Date(f.ultimo_nuovo)) : "mai"}</div>
      ${f.errore ? `<div class="m err">${esc(f.errore)}${f.falliti_di_fila > 3 ? ` (da ${f.falliti_di_fila} controlli)` : ""}</div>` : ""}
      ${f.nota ? `<div class="m">${esc(f.nota)}</div>` : ""}</div></div>`).join("");
  }
  $("#lista-fonti").innerHTML = out;
  s.fonti = tutte;
}


// ============ Motori: momento giusto, super offerte, strumenti ============
const MESI_AUTO = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];
function valutaGiorno(d) {
  const g = d.getDate(), m = d.getMonth() + 1, ult = new Date(d.getFullYear(), m, 0).getDate();
  let p = 0; const motivi = [];
  if (g >= ult - 6) { p += 2; motivi.push("Fine mese: i concessionari chiudono gli obiettivi mensili e trattano di più."); }
  else if (g <= 3) { p -= 1; motivi.push("Inizio mese: gli obiettivi ripartono da zero, di solito c'è meno margine."); }
  if ([3, 6, 9, 12].includes(m) && g >= ult - 14) { p += 1; motivi.push("Fine trimestre: chiusura degli obiettivi trimestrali delle case auto."); }
  if (m === 12) { p += g >= 15 ? 3 : 2; motivi.push("Dicembre: fine anno, ultime immatricolazioni da fare e auto dell'anno in corso da smaltire."); }
  if (m === 1 || m === 2) { p += 1; motivi.push("Gennaio-febbraio: domanda debole e stock dell'anno precedente da vendere."); }
  if (m === 7) { p += 1; motivi.push("Luglio: chiusura del semestre e promozioni estive."); }
  if (m === 11 && g >= 20) { p += 1; motivi.push("Black Friday: molte promozioni su auto in pronta consegna."); }
  if ([3, 4, 5].includes(m)) { p -= 1; motivi.push("Primavera: la domanda è più alta, i margini di sconto di solito si riducono."); }
  return { p, motivi };
}
function semaforoAuto(oggi = new Date()) {
  const { p, motivi } = valutaGiorno(oggi);
  const voto = p >= 3 ? ["🟢", "Ottimo momento per trattare"] : p >= 1 ? ["🟡", "Momento discreto"] : ["🔴", "Di solito meglio aspettare"];
  let prossimo = null;
  for (let i = 1; i <= 150 && !prossimo; i++) {
    const d = new Date(oggi.getFullYear(), oggi.getMonth(), oggi.getDate() + i);
    if (valutaGiorno(d).p >= 3) prossimo = d;
  }
  return { p, voto, motivi, prossimo };
}
function cardSemaforo(completo) {
  const s = semaforoAuto();
  const prox = s.prossimo && s.p < 3 ? `Prossima finestra buona: da <b>${s.prossimo.getDate()} ${MESI_AUTO[s.prossimo.getMonth()]}</b>.` : "";
  return `<div class="semaforo sem-${s.p >= 3 ? "v" : s.p >= 1 ? "g" : "r"}">
    <div class="sem-top"><span class="sem-ico">${s.voto[0]}</span><div><b>${s.voto[1]}</b><small>Indicazione dal calendario (tendenze del mercato, non una garanzia)</small></div></div>
    ${completo ? `<ul>${s.motivi.map((m) => `<li>${esc(m)}</li>`).join("") || "<li>Nessun fattore particolare in questi giorni.</li>"}</ul>` : ""}
    ${prox ? `<p>${prox}</p>` : ""}</div>`;
}
state.vistaAuto = "offerte"; state.offFiltro = "tutte"; state.modelli = store.get("modelli", null); state.profilo = {};
const OFF_FILTRI = [["tutte", "Tutte"], ["sconti", "Sconti"], ["km0", "Km0 e usato"], ["noleggio", "Noleggio e rate"], ["incentivi", "Incentivi"]];
const eOfferta = (n) => n.nicchia === "auto" && (n.aree.includes("offerte_auto") || n.aree.includes("incentivi_auto"));
function cardProfilo() {
  const p = state.profilo || {};
  if (!p.zona) return "";
  return `<div class="mod-box"><b>📌 Il tuo profilo d'uso</b><p class="calc-n">${esc(p.zona)} · ${esc(p.uso || "")} · circa ${p.km_giorno || "?"} km al giorno (${(p.km_anno || 0).toLocaleString("it-IT")} km/anno) · motore preferito: ${esc(p.alimentazione_preferita || "—")}${p.ricarica_casa === null || p.ricarica_casa === undefined ? " · ricarica a casa: da definire" : p.ricarica_casa ? " · ricarica a casa: sì" : " · ricarica a casa: no"}.<br><small>Il calcolatore e gli avvisi usano questi dati. Per cambiarli dimmelo in chat.</small></p></div>`;
}
function renderOfferte() {
  const mod = state.modelli || [];
  let h = cardSemaforo(false) + cardProfilo();
  h += `<div class="mod-box"><b>⭐ I tuoi modelli</b><div class="mod-add"><input id="mod-in" type="text" placeholder="Es. Panda, Clio, Tesla Model 3" autocomplete="off"><button class="chip on" data-mod-add>Aggiungi</button></div>
    <div class="mod-list">${mod.map((x, i) => `<button class="chip" data-mod-del="${i}">${esc(x)} ✕</button>`).join("") || "<small>Aggiungi i modelli che ti interessano: qui compaiono tutte le notizie e offerte che li citano.</small>"}</div>
    ${(state.profilo.modelli || []).length ? `<button class="mini" data-mod-reset>↺ Ripristina i miei modelli</button>` : ""}</div>`;
  if (mod.length) {
    const limite = Date.now() - 30 * 864e5;
    const mie = state.news.filter((n) => n.nicchia === "auto" && new Date(n.pubblicata || n.visto) > limite && mod.some((x) => (n.titolo + " " + (n.sintesi || "")).toLowerCase().includes(x.toLowerCase()))).slice(0, 15);
    h += `<div class="gruppo-titolo">⭐ Sui tuoi modelli (${mie.length})</div>` + (mie.length ? mie.map(card).join("") : vuoto("Nessuna notizia sui tuoi modelli", "negli ultimi 30 giorni"));
  }
  h += `<div class="chips fil">${OFF_FILTRI.map(([k, l]) => `<button class="chip${state.offFiltro === k ? " on" : ""}" data-off="${k}">${l}</button>`).join("")}</div>`;
  let lista = state.news.filter(eOfferta);
  const f = state.offFiltro;
  if (f === "incentivi") lista = lista.filter((n) => n.aree.includes("incentivi_auto"));
  else if (f !== "tutte") lista = lista.filter((n) => (n.sotto || []).includes("offerte_auto." + f));
  const lim = state.limiti.off || 25;
  h += `<div class="gruppo-titolo">💸 Offerte e incentivi (${lista.length})</div>`;
  h += lista.length ? lista.slice(0, lim).map(card).join("") + (lista.length > lim ? `<button class="more" data-piu="off">Mostra altre</button>` : "") : vuoto("Ancora nessuna offerta", "Compaiono dopo il prossimo aggiornamento.");
  return h;
}

// ---- Confronto modelli (dati verificati in docs/data/confronto.json)
function costoModello(m, ip, kmAnno) {
  const q = (m.quota || 0) / 100;
  const energia = kmAnno * q / 100 * m.kwh100 * ip.kwh_prezzo + kmAnno * (1 - q) / 100 * m.l100 * ip.benz_prezzo;
  const perdita = m.prezzo * (1 - ip.residuo / 100);
  const tot = perdita + (energia + ip.assic + ip.manut + ip.bollo) * ip.anni;
  return { tot, mese: tot / (ip.anni * 12), km: tot / (kmAnno * ip.anni), energia };
}
function renderConfronto() {
  const c = state.confronto;
  if (!c || !c.modelli) return "";
  const ip = Object.assign({}, c.ipotesi, store.get("ipotesi", {}));
  const prezzi = store.get("prezziModelli", {});
  const km = (state.profilo && state.profilo.km_anno) || 15000;
  const M = c.modelli.map((m) => Object.assign({}, m, { prezzo: prezzi[m.id] || m.prezzo }));
  const righe = [["Tipo", "tipo"], ["Potenza", "potenza"], ["Batteria", "batteria"], ["Autonomia WLTP", "wltp"], ["Autonomia reale", "reale"], ["Ricarica AC", "ac"], ["Ricarica rapida", "dc"], ["Bagagliaio", "bagagliaio"]];
  let h = `<div class="gruppo-titolo">🔍 Confronto modelli</div><p class="calc-n">Verificato il ${esc(c.verificato)}. ${esc(c.nota)}</p>
    <div class="tab-scroll"><table class="conf"><thead><tr><th></th>${M.map((m) => `<th>${esc(m.nome)}</th>`).join("")}</tr></thead><tbody>
    <tr><th>Prezzo (modifica)</th>${M.map((m) => `<td><input type="number" inputmode="numeric" data-prezzo="${m.id}" value="${m.prezzo}"><small>${esc(m.prezzo_nota)}</small></td>`).join("")}</tr>
    ${righe.map(([l, k]) => `<tr><th>${l}</th>${M.map((m) => `<td>${esc(m[k])}</td>`).join("")}</tr>`).join("")}
    <tr><th>Punti di forza</th>${M.map((m) => `<td><ul>${m.pro.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></td>`).join("")}</tr>
    <tr><th>Da considerare</th>${M.map((m) => `<td><ul>${m.contro.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></td>`).join("")}</tr>
    <tr><th>Fonti</th>${M.map((m) => `<td>${m.fonti.map((u, i) => `<a href="${esc(u)}" target="_blank" rel="noopener">${i + 1}</a>`).join(" · ")}</td>`).join("")}</tr>
    </tbody></table></div>
    <div class="gruppo-titolo">💶 Costo reale in ${ip.anni} anni (${km.toLocaleString("it-IT")} km/anno, ricarica a casa)</div>
    <div class="calc">${[["anni", "Anni di possesso"], ["kwh_prezzo", "Costo energia a casa (€/kWh)"], ["benz_prezzo", "Benzina (€/l)"], ["residuo", "Valore a fine periodo (%)"], ["assic", "Assicurazione (€/anno)"], ["manut", "Manutenzione (€/anno)"], ["bollo", "Bollo (€/anno)"]].map(([k, l]) => `<label>${l}<input type="number" inputmode="decimal" data-ip="${k}" value="${ip[k]}"></label>`).join("")}</div>
    <div id="conf-out">${tabellaCosti(M, ip, km)}</div>
    <p class="calc-n"><small>Stime modificabili: consumo elettrico reale circa 16-17 kWh/100 km, 90% dei km in elettrico sulle plug-in (con 50 km al giorno e wallbox), benzina 5,5 l/100 km nel resto. Il valore residuo è un'ipotesi: sulle elettriche può essere più incerto.</small></p>`;
  return h;
}
function tabellaCosti(M, ip, km) {
  const R = M.map((m) => [m, costoModello(m, ip, km)]).sort((a, b) => a[1].tot - b[1].tot);
  return `<div class="tab-scroll"><table class="conf"><thead><tr><th>Modello</th><th>Totale ${ip.anni} anni</th><th>Al mese</th><th>€/km</th></tr></thead><tbody>${R.map(([m, r], i) => `<tr><th>${i === 0 ? "🏆 " : ""}${esc(m.nome)}</th><td>${eur(r.tot)}</td><td>${eur(r.mese)}</td><td>${r.km.toFixed(2).replace(".", ",")} €</td></tr>`).join("")}</tbody></table></div>`;
}
document.addEventListener("input", (e) => {
  const ipEl = e.target.closest("[data-ip]"), pz = e.target.closest("[data-prezzo]");
  if (!ipEl && !pz) return;
  if (ipEl) { const cur = store.get("ipotesi", {}); cur[ipEl.dataset.ip] = parseFloat(String(ipEl.value).replace(",", ".")) || 0; store.set("ipotesi", cur); }
  if (pz) { const cur = store.get("prezziModelli", {}); cur[pz.dataset.prezzo] = parseFloat(pz.value) || 0; store.set("prezziModelli", cur); }
  const c = state.confronto, ip = Object.assign({}, c.ipotesi, store.get("ipotesi", {})), prezzi = store.get("prezziModelli", {});
  const M = c.modelli.map((m) => Object.assign({}, m, { prezzo: prezzi[m.id] || m.prezzo }));
  $("#conf-out").innerHTML = tabellaCosti(M, ip, (state.profilo && state.profilo.km_anno) || 15000);
});

const GUIDA = [
  ["📅 Quando comprare", ["Fine mese, fine trimestre e dicembre sono di solito i momenti in cui i concessionari trattano di più.", "Le auto dell'anno precedente ancora in stock (gennaio-febbraio) tendono a essere scontate.", "Chiedi sempre la disponibilità immediata: pronta consegna spesso significa sconto maggiore."]],
  ["🆕 Nuova, km0 o usato?", ["Nuova: garanzia piena e scelta di allestimento, ma la svalutazione dei primi anni è alta.", "Km0 / aziendale: già immatricolata (la prima svalutazione l'ha fatta qualcun altro) ma quasi nuova.", "Usato: controlla storico tagliandi e chilometri; dal professionista c'è la garanzia legale di conformità (2 anni, riducibile a 1 sull'usato se pattuito).", "Elettrica usata: fai verificare lo stato di salute della batteria."]],
  ["🤝 Come trattare", ["Chiedi il prezzo chiavi in mano (messa su strada, imposta di trascrizione, spese): è l'unico confrontabile.", "Fai 3-4 preventivi scritti in concessionarie diverse, anche via email.", "Tratta la permuta a parte: fatti una valutazione indipendente del tuo usato prima.", "Gli optional e i pacchetti 'obbligatori' sono spesso il punto dove si recupera margine: chiedi cosa si può togliere."]],
  ["💳 Finanziamento e noleggio", ["Guarda il TAEG, non solo la rata. Attenzione a maxi-rata finale, assicurazioni e servizi abbinati.", "Noleggio lungo termine: verifica franchigie, chilometri inclusi, penali di uscita e cosa succede a fine contratto.", "Confronta sempre il costo totale (usa il calcolatore qui sotto) e non solo il costo mensile."]],
  ["🔎 Prima di firmare", ["Rileggi il contratto: data di consegna, penali, garanzie, accessori inclusi.", "Verifica incentivi e bonus ancora attivi e i requisiti (ISEE, rottamazione, fondi disponibili).", "Non farti mettere fretta da 'offerta valida solo oggi': a fine mese ne trovi di simili."]],
];
const CALC_DEF = { prezzo: 22000, anticipo: 3000, mesi: 48, tan: 6.5, km: 15000, consumo: 6, carb: 1.9, assic: 700, bollo: 200, manut: 400, residuo: 45, canone: 320, antNol: 3000 };
const CALC_CAMPI = [["prezzo", "Prezzo auto (€)"], ["anticipo", "Anticipo (€)"], ["mesi", "Durata (mesi)"], ["tan", "TAN finanziamento (%)"], ["km", "Km all'anno"], ["consumo", "Consumo (l/100 km)"], ["carb", "Carburante (€/l)"], ["assic", "Assicurazione (€/anno)"], ["bollo", "Bollo (€/anno)"], ["manut", "Manutenzione (€/anno)"], ["residuo", "Valore a fine periodo (%)"], ["canone", "NOLEGGIO: canone (€/mese)"], ["antNol", "NOLEGGIO: anticipo (€)"]];
const eur = (v) => Math.round(v).toLocaleString("it-IT") + " €";
function calcolaAuto() {
  const c = Object.assign({}, CALC_DEF, state.profilo && state.profilo.km_anno ? { km: state.profilo.km_anno } : {}, store.get("calc", {}));
  const n = Math.max(1, c.mesi), anni = n / 12, fin = Math.max(0, c.prezzo - c.anticipo), r = c.tan / 1200;
  const rata = r > 0 ? fin * r / (1 - Math.pow(1 + r, -n)) : fin / n;
  const carb = c.km * c.consumo / 100 * c.carb * anni;
  const gestione = (c.assic + c.bollo + c.manut) * anni;
  const residuo = c.prezzo * c.residuo / 100;
  const acq = c.anticipo + rata * n + carb + gestione - residuo;
  const nol = c.antNol + c.canone * n + carb;
  return `<div class="calc-ris"><div><small>Comprare (finanziato)</small><b>${eur(acq)}</b><small>${eur(acq / n)} al mese · rata ${eur(rata)}</small></div>
    <div><small>Noleggio lungo termine</small><b>${eur(nol)}</b><small>${eur(nol / n)} al mese · assicurazione e manutenzione incluse</small></div></div>
    <p class="calc-n">${acq < nol ? "Con questi numeri conviene <b>comprare</b>" : "Con questi numeri conviene il <b>noleggio</b>"}: differenza di ${eur(Math.abs(acq - nol))} sull'intero periodo. Nell'acquisto è sottratto il valore dell'auto che ti resta a fine periodo.</p>`;
}
function renderStrumenti() {
  const c = Object.assign({}, CALC_DEF, state.profilo && state.profilo.km_anno ? { km: state.profilo.km_anno } : {}, store.get("calc", {}));
  return cardSemaforo(true) +
    renderConfronto() + `<div class="gruppo-titolo">🧮 Comprare o noleggiare?</div><div class="calc">${CALC_CAMPI.map(([k, l]) => `<label>${l}<input type="number" inputmode="decimal" data-calc="${k}" value="${c[k]}"></label>`).join("")}</div><div id="calc-out">${calcolaAuto()}</div>
     <div class="gruppo-titolo">📖 Guida all'acquisto</div>` +
    GUIDA.map(([t, voci]) => `<details class="guida"><summary>${t}</summary><ul>${voci.map((v) => `<li>${esc(v)}</li>`).join("")}</ul></details>`).join("");
}
document.addEventListener("input", (e) => {
  const c = e.target.closest("[data-calc]");
  if (!c) return;
  const cur = store.get("calc", {}); cur[c.dataset.calc] = parseFloat(String(c.value).replace(",", ".")) || 0; store.set("calc", cur);
  $("#calc-out").innerHTML = calcolaAuto();
});
document.addEventListener("click", (e) => {
  const va = e.target.closest("[data-vauto]");
  const vp = e.target.closest("[data-vpol]");
  if (vp) { state.vistaPol = vp.dataset.vpol; renderTutto(); window.scrollTo(0, 0); return; }
  if (va) { state.vistaAuto = va.dataset.vauto; renderTutto(); window.scrollTo(0, 0); return; }
  const of = e.target.closest("[data-off]");
  if (of) { state.offFiltro = of.dataset.off; state.limiti.off = 25; renderNovita(); return; }
  if (e.target.closest("[data-mod-add]")) {
    const v = ($("#mod-in").value || "").trim();
    if (v && !state.modelli.some((x) => x.toLowerCase() === v.toLowerCase())) { state.modelli.push(v); store.set("modelli", state.modelli); }
    renderNovita(); return;
  }
  if (e.target.closest("[data-mod-reset]")) { state.modelli = [...(state.profilo.modelli || [])]; store.set("modelli", state.modelli); renderNovita(); return; }
  const md = e.target.closest("[data-mod-del]");
  if (md) { state.modelli.splice(+md.dataset.modDel, 1); store.set("modelli", state.modelli); renderNovita(); }
}, true);



// ============ Pop-up (bottom sheet) per tutta l'app ============
const dec = (s) => { const t = document.createElement("textarea"); t.innerHTML = String(s ?? ""); return t.value; };
const te = (s) => esc(dec(s));
state.pop = {}; let popN = 0;
const reg = (html) => { const k = "p" + (++popN); state.pop[k] = html; return `data-pop="${k}" role="button" tabindex="0"`; };
let popAperto = false;
function chiudiPop(daStorico) {
  const ov = document.getElementById("pop"); if (!ov || !popAperto) return;
  popAperto = false; ov.classList.remove("on"); document.body.classList.remove("pop-open");
  if (!daStorico && history.state && history.state.pop) history.back();
}
function apriPop(html) {
  let ov = document.getElementById("pop");
  if (!ov) {
    ov = document.createElement("div"); ov.id = "pop"; ov.className = "pop";
    ov.innerHTML = `<div class="pop-bg" data-pop-x></div><div class="pop-sh" role="dialog" aria-modal="true"><div class="pop-top"><i class="pop-h"></i><button class="pop-x" data-pop-x aria-label="Chiudi">✕</button></div><div class="pop-c"></div></div>`;
    document.body.appendChild(ov);
    const sh = ov.querySelector(".pop-sh"), c = ov.querySelector(".pop-c"); let y0 = null, dy = 0;
    sh.addEventListener("touchstart", (e) => { if (c.scrollTop <= 0) { y0 = e.touches[0].clientY; dy = 0; sh.style.transition = "none"; } }, { passive: true });
    sh.addEventListener("touchmove", (e) => { if (y0 === null) return; dy = Math.max(0, e.touches[0].clientY - y0); sh.style.transform = `translateY(${dy}px)`; }, { passive: true });
    sh.addEventListener("touchend", () => { if (y0 === null) return; sh.style.transition = ""; sh.style.transform = ""; if (dy > 110) chiudiPop(); y0 = null; });
  }
  ov.querySelector(".pop-c").innerHTML = html; ov.querySelector(".pop-c").scrollTop = 0;
  if (!popAperto) { history.pushState({ pop: 1 }, ""); }
  popAperto = true; document.body.classList.add("pop-open");
  requestAnimationFrame(() => ov.classList.add("on"));
}
window.addEventListener("popstate", () => chiudiPop(true));
document.addEventListener("keydown", (e) => { if (e.key === "Escape") chiudiPop(); if ((e.key === "Enter" || e.key === " ") && e.target.dataset && e.target.dataset.pop) { e.preventDefault(); apriPop(state.pop[e.target.dataset.pop] || ""); } });
document.addEventListener("click", (e) => {
  if (e.target.closest("[data-pop-x]")) { chiudiPop(); return; }
  if (e.target.closest("#pop a, #pop button")) return;
  const d = e.target.closest("[data-pop]");
  if (d && !e.target.closest("[data-star]")) { e.stopPropagation(); e.preventDefault(); apriPop(state.pop[d.dataset.pop] || ""); }
}, true);
const pBtn = (u, t) => `<a class="pop-btn" href="${esc(u)}" target="_blank" rel="noopener">${t}</a>`;
const pRiga = (k, v) => v ? `<div class="pop-r"><span>${k}</span><b>${v}</b></div>` : "";
function apriNews(n) {
  const stella = state.stelle.has(n.id);
  const badge = (n.luogo ? `<span class="badge luogo">📍 ${esc(n.luogo)}</span>` : "") + n.aree.map((a) => `<span class="badge" style="--c:${colore(a)}">${esc(nome(a))}</span>`).join("");
  apriPop(`<div class="riga">${badge}${n.normativa ? '<span class="badge norm">Ufficiale</span>' : ""}</div>
    <h2 class="pop-t">${te(n.titolo)}</h2>
    ${n.sintesi ? `<p class="pop-p">${te(n.sintesi)}</p>` : '<p class="pop-p mute">Questa fonte non fornisce un riassunto: apri l\'articolo per leggerlo.</p>'}
    <div class="pop-box">${pRiga("Fonte", esc(n.fonte_nome))}${(n.altre_fonti || []).length ? pRiga("Riportata anche da", esc(n.altre_fonti.join(", "))) : ""}${pRiga("Pubblicata", fa(dataDi(n)))}${n.tradotto ? pRiga("Titolo", "tradotto automaticamente") : ""}</div>
    <div class="pop-az">${pBtn(n.link, "Apri la fonte ↗")}<button class="pop-btn sec" data-star="${n.id}">${stella ? "★ Salvata" : "☆ Salva"}</button></div>`);
}

// ============ Politica: quadro grafico (dati in data/politica.json) ============
state.vistaPol = "quadro"; state.politica = null; state.politicaAuto = {}; state.politicaStato = {};
function hemi(gruppi, W) {
  const N = gruppi.reduce((s, g) => s + g.n, 0), H = Math.round(W * 0.56), cx = W / 2, cy = H - 9;
  const R = N > 200 ? 9 : N > 60 ? 6 : 4, r0 = W * 0.2, r1 = W * 0.47, dr = R > 1 ? (r1 - r0) / (R - 1) : 0;
  const rad = (i) => r0 + i * dr, tot = Array.from({ length: R }, (_, i) => rad(i)).reduce((a, b) => a + b, 0);
  let seats = [], left = N;
  for (let i = 0; i < R; i++) {
    const n = i === R - 1 ? left : Math.round(N * rad(i) / tot); left -= n;
    for (let k = 0; k < n; k++) seats.push({ a: Math.PI - (n === 1 ? Math.PI / 2 : k * Math.PI / (n - 1)), r: rad(i) });
  }
  seats.sort((x, y) => y.a - x.a || x.r - y.r);
  const sz = Math.max(2.2, Math.min(7, dr * 0.38 * (N > 200 ? 1 : 1.6)));
  let idx = 0, dots = "";
  for (const g of gruppi) for (let k = 0; k < g.n; k++, idx++) {
    const s = seats[idx]; if (!s) break;
    dots += `<circle cx="${(cx + s.r * Math.cos(s.a)).toFixed(1)}" cy="${(cy - s.r * Math.sin(s.a)).toFixed(1)}" r="${sz}" fill="${g.colore}"/>`;
  }
  return `<svg viewBox="0 0 ${W} ${H}" class="hemi" role="img" aria-label="Seggi">${dots}</svg>`;
}
function legenda(gruppi) {
  const tot = gruppi.reduce((a, g) => a + g.n, 0) || 1;
  return `<div class="leg">${gruppi.slice().reverse().map((g) => `<span class="tap" ${reg(`<h2 class="pop-t">${esc(g.nome || g.sigla)}</h2><div class="pop-box">${pRiga("Seggi", g.n + " su " + tot)}${pRiga("Quota", Math.round((g.n / tot) * 1000) / 10 + "%")}${g.blocco ? pRiga("Posizione", g.blocco === "magg" ? "Maggioranza di governo" : g.blocco === "opp" ? "Opposizione" : "Altri") : ""}</div>`)}><i style="background:${g.colore}"></i>${esc(g.sigla)} <b>${g.n}</b></span>`).join("")}</div>`;
}
const nomeGruppoVoto = (s) => { const l = String(s).toLowerCase(); const m = [["fdi", "Fratelli d'Italia"], ["pd", "Partito Democratico"], ["lega", "Lega"], ["fi", "Forza Italia"], ["m5s", "Movimento 5 Stelle"], ["avs", "AVS"], ["a-", "Azione"], ["az", "Azione"], ["iv", "Italia Viva"], ["nm", "Noi Moderati"], ["misto", "Misto"]].find(([k]) => l.startsWith(k)); return m ? m[1] : String(s); };

const BLOCCO_VOTO = { FDI: "magg", LEGA: "magg", "FI-PPE": "magg", "NM-M-C": "magg", "PD-IDP": "opp", M5S: "opp", AVS: "opp", "IV-CR": "opp", APERRE: "opp", "M-+E-S": "opp" };
function cosaE(titolo, atto) {
  const T = dec(atto || ""), V = dec(titolo || "");
  let tipo = "";
  if (/conversione in legge.*decreto-legge/i.test(T)) tipo = "È la conversione di un <b>decreto-legge</b>: un provvedimento d'urgenza che il Governo ha già emanato e che è già in vigore. Il Parlamento deve trasformarlo in legge entro 60 giorni, altrimenti decade.";
  else if (/ratifica ed esecuzione|ratifica/i.test(T)) tipo = "Il Parlamento <b>autorizza la ratifica</b> di un accordo o trattato internazionale firmato dall'Italia.";
  else if (/delega al governo|deleg[ah]/i.test(T)) tipo = "È una <b>legge di delega</b>: il Parlamento fissa i principi e incarica il Governo di scrivere le norme di dettaglio (decreti legislativi).";
  else if (/bilancio|rendiconto|assestamento/i.test(T)) tipo = "Riguarda i <b>conti dello Stato</b> (bilancio, entrate e spese).";
  else if (/^\s*(modifica|modifiche|disposizioni|norme|istituzione|introduzione)/i.test(T)) tipo = "È una proposta di <b>legge ordinaria</b>: se approvata da entrambe le Camere nello stesso testo, diventa legge.";
  const fin = /voto finale/i.test(V) ? "È il <b>voto finale</b>: dopo l'esame degli articoli e degli emendamenti, l'Aula vota il testo nel suo insieme. Se passa, il testo va all'altra Camera; se l'ha già approvato identico, diventa legge." : "";
  return [tipo, fin].filter(Boolean).map((x) => `<p class="pop-p">${x}</p>`).join("");
}
function popVoto(x) {
  const t = x.fav + x.con + x.ast || 1, ok = x.esito === "approvata";
  const gr = (x.gruppi || []).filter((g) => g.fav + g.con + g.ast > 0);
  const lista = (k) => gr.filter((g) => g[k] > 0 && g[k] >= (g.fav + g.con + g.ast) / 2);
  const riga = (g, k) => `<span class="pop-chip ${BLOCCO_VOTO[g.sigla] || ""}">${esc(nomeGruppoVoto(g.sigla))} <b>${g[k]}</b></span>`;
  const sez = (tit, k) => { const l = lista(k); return l.length ? `<div class="pop-sub">${tit}</div><div class="pop-chips">${l.map((g) => riga(g, k)).join("")}</div>` : ""; };
  const magg = gr.filter((g) => BLOCCO_VOTO[g.sigla] === "magg"), opp = gr.filter((g) => BLOCCO_VOTO[g.sigla] === "opp");
  const somma = (a, k) => a.reduce((s, g) => s + g[k], 0);
  const lettura = magg.length && opp.length ? `<p class="pop-p">Maggioranza di governo: <b>${somma(magg, "fav")}</b> sì, <b>${somma(magg, "con")}</b> no. Opposizioni: <b>${somma(opp, "fav")}</b> sì, <b>${somma(opp, "con")}</b> no.</p>` : "";
  return `<div class="riga"><span class="esito ${ok ? "si" : "no"}">${ok ? "✅ Approvata" : "❌ Respinta"}</span><span class="mute">${esc(x.data)}</span></div>
    <h2 class="pop-t">${te(x.titolo)}</h2>
    <div class="pop-sub">Di cosa si tratta</div>
    ${x.atto ? `<p class="pop-p"><b>Titolo ufficiale:</b> ${te(x.atto.titolo)}</p>` : '<p class="pop-p mute">Il titolo esteso non è stato letto in automatico: lo trovi nella scheda ufficiale qui sotto.</p>'}
    ${cosaE(x.titolo, x.atto && x.atto.titolo)}
    ${x.atto && x.atto.iniziativa ? `<p class="pop-p mute">Presentato da: ${te(x.atto.iniziativa)}</p>` : ""}
    <div class="pop-sub">Com'è andata</div>
    <div class="barra"><span style="flex:${x.fav};background:#1f9d6b">${x.fav}</span><span style="flex:${x.ast || 0.0001};background:#94a3b8"></span><span style="flex:${x.con};background:#dc2626">${x.con}</span></div>
    <div class="voto-l"><span>👍 Sì ${Math.round((x.fav / t) * 100)}%</span><span>Astenuti ${x.ast}</span><span>👎 No ${Math.round((x.con / t) * 100)}%</span></div>
    <p class="pop-p mute">Votanti ${x.votanti}. I voti sono quelli registrati dalla Camera; chi era in missione o assente non è contato.</p>
    ${gr.length ? `<div class="pop-sub">Chi ha votato cosa</div>${lettura}${sez("👍 A favore", "fav")}${sez("👎 Contro", "con")}${sez("⚪ Astenuti", "ast")}<p class="pop-leg"><i class="magg"></i>maggioranza <i class="opp"></i>opposizione</p>` : ""}
    <div class="pop-sub">Perché hanno votato così</div>
    <p class="pop-p mute">Le motivazioni sono nelle <b>dichiarazioni di voto</b> che ogni gruppo pronuncia in Aula: non le riassumo in automatico per non attribuire ai partiti intenzioni non verificate. Le trovi nel resoconto della seduta, collegato alla scheda ufficiale.</p>
    <div class="pop-az">${x.scheda ? pBtn(x.scheda, "Scheda ufficiale del voto ↗") : ""}${x.scheda_atto ? pBtn(x.scheda_atto, "Scheda dell'atto ↗") : ""}</div>
    <p class="pop-fonte">Fonte: Camera dei deputati, dati aperti (dati.camera.it)</p>`;
}
function popProposta(x, link) {
  const g = x.iniziativa === "Governo";
  const spiega = g ? "Presentata dal <b>Governo</b>." : /region/i.test(x.iniziativa) ? "Proposta da un <b>Consiglio regionale</b>." : "Presentata da <b>parlamentari</b>.";
  return `<div class="riga"><span class="esito ${g ? "si" : ""}">${g ? "🏛️ Governo" : "👥 " + esc(x.iniziativa)}</span><span class="mute">${esc(x.data)}</span></div>
    <h2 class="pop-t">${te(x.titolo)}</h2><p class="pop-p">${spiega}</p>${cosaE("", x.titolo)}
    <div class="pop-box">${pRiga("Stato", te(x.stato || "non indicato"))}${pRiga("Presentata il", esc(x.data))}</div>
    <p class="pop-p mute">Una proposta di legge diventa legge solo se entrambe le Camere approvano lo stesso testo.</p>
    <div class="pop-az">${pBtn(link, "Atti della Camera ↗")}</div><p class="pop-fonte">Fonte: Camera dei deputati, dati aperti (dati.camera.it)</p>`;
}

function renderPolitica() {
  state.pop = {}; popN = 0;
  const p = state.politica;
  if (!p) return vuoto("Dati non disponibili", "Il quadro politico non si è caricato: riprova tra poco.");
  const link = (u, t) => `<a class="lk" href="${esc(u)}" target="_blank" rel="noopener">${t}</a>`;
  const fonti = (arr) => (arr && arr.length ? `<div class="fon">Fonti: ${arr.map((u, i) => link(u, i + 1)).join(" · ")}</div>` : "");
  const pers = (x, url) => `<div class="pers tap" ${reg(`<h2 class="pop-t">${esc(x.nome)}</h2><p class="pop-p">${esc(x.ruolo || "")}</p><div class="pop-box">${pRiga("Partito", esc(x.partito || "non indicato"))}</div>${url ? `<div class="pop-az">${pBtn(url, "Pagina ufficiale ↗")}</div>` : ""}`)}><b>${esc(x.nome)}</b><span>${esc(x.ruolo || "")}</span>${x.partito ? `<em>${esc(x.partito)}</em>` : ""}</div>`;
  const A = state.politicaAuto || {}, S = state.politicaStato || {};
  const stampa = (b) => {
    const au = A[b], st = S[b] || {};
    if (au && au.aggiornato && st.ok !== false) return `<div class="stamp ok">✅ Aggiornato automaticamente ${fa(new Date(au.aggiornato))}</div>`;
    if (au && au.aggiornato) return `<div class="stamp warn">⚠️ Ultima lettura riuscita ${fa(new Date(au.aggiornato))}; l'ultimo tentativo non è andato a buon fine</div>`;
    if (st.errore) return `<div class="stamp warn">⚠️ Lettura automatica non riuscita: dato inserito a mano il ${esc(p.verificato)}</div>`;
    return `<div class="stamp">✋ Dato inserito a mano il ${esc(p.verificato)}</div>`;
  };
  const [gg, mm, aa] = String(p.verificato).split("/").map(Number), dalla = new Date(aa, (mm || 1) - 1, gg || 1).getTime();
  const segnali = (re) => {
    const t = (state.news || []).filter((n) => Date.parse(n.pubblicata) > dalla && re.test(`${n.titolo} ${n.sintesi || ""}`)).slice(0, 3);
    return t.length ? `<div class="alert">🔔 Possibili novità da controllare<ul>${t.map((n) => `<li><a href="${esc(n.link)}" target="_blank" rel="noopener">${esc(n.titolo)}</a></li>`).join("")}</ul></div>` : "";
  };
  const g = Object.assign({}, p.governo), c = Object.assign({}, p.camera, A.camera || {}), rc = p.campania, ce = p.caserta, eu = p.europa;
  if (A.governo && A.governo.persone && A.governo.persone.length) {
    const cognome = (s) => String(s).toLowerCase().split(" ").slice(-1)[0];
    const noti = {}; [g.premier].concat(p.governo.persone).forEach((x) => { noti[cognome(x.nome)] = x.partito; });
    const lista = A.governo.persone.map((x) => ({ nome: x.nome, ruolo: x.ruolo, partito: noti[cognome(x.nome)] || "" }));
    const pr = lista.find((x) => /presidente del consiglio/i.test(x.ruolo) && !/vice/i.test(x.ruolo));
    if (pr) { g.premier = pr; g.persone = lista.filter((x) => x !== pr); }
  }
  const mg = c.gruppi.filter((x) => x.blocco === "magg").reduce((s, x) => s + x.n, 0), op = c.gruppi.filter((x) => x.blocco === "opp").reduce((s, x) => s + x.n, 0), al = c.totale - mg - op;
  let h = `<p class="calc-n">Aggiornato al ${esc(p.verificato)}. ${esc(p.nota)}</p>`;
  h += `<div class="gruppo-titolo">🏛️ ${esc(g.nome)}</div><div class="pcard"><div class="premier">${pers(Object.assign({}, g.premier), g.link)}</div><div class="pgrid">${g.persone.map((x) => pers(x, g.link)).join("")}</div>
    <ul class="nov">${g.novita.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>${segnali(/(ministr[oa]|governo|meloni).*(dimission|rimpasto|giura|nuovo ministro|nuova ministra|sfiducia|crisi di governo)/i)}${stampa("governo")}${link(g.link, "Elenco completo dei ministri →")}${fonti(g.fonti)}</div>`;
  h += `<div class="gruppo-titolo">📊 ${esc(c.titolo)} (${c.totale} seggi)</div><div class="pcard">${hemi(c.gruppi, 340)}
    <div class="soglia">Maggioranza assoluta: ${c.maggioranza_soglia} seggi</div>${legenda(c.gruppi)}
    <div class="barra"><span style="flex:${mg};background:#1e40af">Maggioranza ${mg}</span><span style="flex:${al};background:#94a3b8"></span><span style="flex:${op};background:#dc2626">Opposizione ${op}</span></div>
    <p class="calc-n">Altri/non allineati: ${al}. ${esc(c.nota || "")}</p>${stampa("camera")}${link(c.link, "Composizione ufficiale →")}</div>`;
  if ((A.senato || p.senato) && (A.senato || p.senato).gruppi) {
    const sn = A.senato || p.senato, sm = sn.gruppi.filter((x) => x.blocco === "magg").reduce((s, x) => s + x.n, 0), so = sn.gruppi.filter((x) => x.blocco === "opp").reduce((s, x) => s + x.n, 0), sa = sn.totale - sm - so;
    h += `<div class="gruppo-titolo">📊 Senato della Repubblica (${sn.totale} seggi)</div><div class="pcard">${hemi(sn.gruppi, 340)}<div class="soglia">Maggioranza assoluta: ${sn.maggioranza_soglia} seggi</div>${legenda(sn.gruppi)}<div class="barra"><span style="flex:${sm};background:#1e40af">Maggioranza ${sm}</span><span style="flex:${sa};background:#94a3b8"></span><span style="flex:${so};background:#dc2626">Opposizione ${so}</span></div><p class="calc-n">${esc(sn.nota || "")}</p>${stampa("senato")}${link(sn.link, "Composizione ufficiale →")}</div>`;
  }
  const elencoGruppi = (D, titolo, chiave, ruolo) => {
    if (!D || !D.gruppi || !D.gruppi.length) return "";
    const sg = (s) => { let t = String(s).replace(/^MISTO-/i, "Misto · ").replace(/ - .*/, "").replace(/-[A-Z].*$/, "").replace(/\(.*$/, "").trim(); if (t === t.toUpperCase()) t = t.toLowerCase().replace(/(^|\s)\S/g, (c) => c.toUpperCase()); return esc(t); };
    const vt = (v) => v.tipo === "passaggio" ? `${esc(v.nome)}: da ${sg(v.da)} a ${sg(v.a)}` : v.tipo === "subentro" ? `${esc(v.nome)} subentra (${sg(v.a)})` : `${esc(v.nome)} non è più ${ruolo} (${sg(v.da)})`;
    return `<div class="gruppo-titolo">${titolo} (${D.totale})</div><div class="pcard">`
      + D.gruppi.map((g) => `<details class="grp"><summary><i style="background:${esc(g.colore)}"></i><span>${sg(g.gruppo)}</span><b>${g.n}</b></summary>${g.presidente ? `<p class="dep" style="padding-bottom:0"><b>Capogruppo:</b> ${esc(g.presidente)}</p>` : ""}<p class="dep">${g.deputati.map((d) => esc(d.nome)).join(" · ")}</p></details>`).join("")
      + `<div class="calc-n"><b>🔄 Ultimi cambiamenti</b></div>`
      + ((D.variazioni || []).length ? `<ul class="nov">${D.variazioni.slice(0, 8).map((v) => `<li>${vt(v)} <span class="mute">· ${esc(v.data)}</span></li>`).join("")}</ul>` : `<p class="calc-n">Nessun passaggio di gruppo registrato dall'avvio del controllo automatico.</p>`)
      + stampa(chiave) + link(D.link, "Elenco ufficiale →") + `</div>`;
  };
  const PT = state.partiti;
  if (PT && PT.partiti && PT.partiti.length) {
    h += `<div class="gruppo-titolo">🎙️ Chi guida i partiti</div><div class="pcard"><div class="pgrid">${PT.partiti.map((x) => { const gd = x.guida.map((g) => (typeof g === "string" ? { nome: g, ruolo: "" } : g)); const gdep = ((state.deputati && state.deputati.gruppi) || []).find((q) => String(q.sigla || "").toLowerCase() === x.sigla.toLowerCase() || String(q.gruppo).toLowerCase().startsWith(x.nome.toLowerCase().slice(0, 8)));
      const pp = reg(`<h2 class="pop-t">${esc(x.nome)}</h2><p class="pop-p">${gd.map((g) => `<b>${esc(g.nome)}</b>${g.ruolo ? " – " + esc(g.ruolo) : ""}`).join("<br>")}</p><div class="pop-box">${gdep ? pRiga("Deputati alla Camera", gdep.n) + pRiga("Capogruppo alla Camera", esc(gdep.presidente || "non rilevato")) : pRiga("Deputati alla Camera", "gruppo non individuato")}</div><p class="pop-fonte">Fonte del vertice: Wikipedia (pagina del partito), può avere qualche giorno di ritardo. Deputati e capogruppo: Camera dei deputati.</p>`);
      return `<div class="pers tap" ${pp}><b>${esc(gd.map((g) => g.nome).join(" · "))}</b><span>${esc([...new Set(gd.map((g) => g.ruolo).filter(Boolean))].join(" · "))}${gd.some((g) => g.ruolo) ? " – " : ""}${esc(x.nome)}</span></div>`; }).join("")}</div>${(PT.mancanti || []).length ? `<p class="calc-n">Non trovati in automatico: ${esc(PT.mancanti.join(", "))}.</p>` : ""}<p class="calc-n">Fonte: Wikipedia (letta dalla pagina Wikipedia di ogni partito: un cambio può comparire con qualche giorno di ritardo).</p>${stampa("segretari")}</div>`;
  }
  h += elencoGruppi(state.deputati, "👥 Partiti e deputati", "deputati", "deputato");
  h += elencoGruppi(state.senatori, "👥 Partiti e senatori", "senatori", "senatore");
  const VT = state.votazioni;
  if (VT && VT.voti && VT.voti.length) {
    h += `<div class="gruppo-titolo">🗳️ Ultime votazioni della Camera</div><div class="pcard">${VT.voti.slice(0, 8).map((x) => {
      const t = x.fav + x.con + x.ast || 1, ok = x.esito === "approvata";
      return `<div class="voto tap" ${reg(popVoto(x))}><div class="voto-t">${te(x.titolo)}</div><div class="voto-m"><span class="esito ${ok ? "si" : "no"}">${ok ? "✅ Approvata" : "❌ Respinta"}</span><span class="mute">${esc(x.data)}</span></div><div class="barra"><span style="flex:${x.fav};background:#1f9d6b">${x.fav}</span><span style="flex:${x.ast || 0.0001};background:#94a3b8"></span><span style="flex:${x.con};background:#dc2626">${x.con}</span></div><div class="voto-l"><span>👍 Favorevoli ${Math.round((x.fav / t) * 100)}%</span><span>Astenuti ${x.ast}</span><span>👎 Contrari ${Math.round((x.con / t) * 100)}%</span></div><div class="tocca">Tocca per spiegazione e voti dei gruppi ›</div></div>`;
    }).join("")}${stampa("votazioni")}${link(VT.link, "Votazioni sul sito della Camera →")}</div>`;
  }
  const PR = state.proposte;
  if (PR && PR.proposte && PR.proposte.length) {
    h += `<div class="gruppo-titolo">📜 Ultime proposte di legge</div><div class="pcard">${PR.proposte.slice(0, 8).map((x) => `<div class="voto tap" ${reg(popProposta(x, PR.link))}><div class="voto-t">${te(x.titolo)}</div><div class="voto-m"><span class="esito ${x.iniziativa === "Governo" ? "si" : ""}">${x.iniziativa === "Governo" ? "🏛️ Governo" : "👥 " + esc(x.iniziativa)}</span><span class="mute">${esc(x.data)}</span></div>${x.stato ? `<div class="calc-n" style="margin:0">Stato: ${te(x.stato)}</div>` : ""}<div class="tocca">Tocca per i dettagli ›</div></div>`).join("")}${stampa("proposte")}${link(PR.link, "Atti della Camera →")}</div>`;
  }
  h += `<div class="gruppo-titolo">📍 ${esc(rc.titolo)}</div><div class="pcard">${pers({ nome: rc.presidente.nome, ruolo: "Presidente della Regione", partito: rc.presidente.partito })}<p class="calc-n">${esc(rc.presidente.nota)}</p>
    ${hemi([{ n: rc.consiglio.maggioranza, colore: "#dc2626" }, { n: rc.consiglio.opposizione, colore: "#1e40af" }], 280)}
    <div class="barra"><span style="flex:${rc.consiglio.maggioranza};background:#dc2626">Maggioranza ${rc.consiglio.maggioranza}</span><span style="flex:${rc.consiglio.opposizione};background:#1e40af">Opposizione ${rc.consiglio.opposizione}</span></div>
    <p class="calc-n">Presidente del Consiglio regionale: ${esc(rc.consiglio.presidente)}. Capo dell'opposizione: ${esc(rc.consiglio.capo_opposizione)}.</p>
    <div class="pgrid">${rc.giunta.map((x) => pers(x, rc.link)).join("")}</div><p class="calc-n">${esc(rc.giunta_nota)}</p>${segnali(/(fico|giunta regionale|consiglio regionale|regione campania).*(dimission|nuov[oa] assessor|rimpasto|azzerat|decad)/i)}<div class="stamp">✋ Dato inserito a mano il ${esc(p.verificato)}, controllato con le notizie</div>${link(rc.link, "Sito della Regione →")}${fonti(rc.fonti)}</div>`;
  h += `<div class="gruppo-titolo">🏙️ ${esc(ce.titolo)}</div><div class="pcard"><b>${esc(ce.stato)}</b><p class="calc-n">${esc(ce.testo)}</p>${segnali(/caserta.*(commissari|elezioni comunali|sindaco|scioglimento)/i)}<div class="stamp">✋ Dato inserito a mano il ${esc(p.verificato)}, controllato con le notizie</div>${link(ce.link, "Sito del Comune →")}${fonti(ce.fonti)}</div>`;
  h += `<div class="gruppo-titolo">🇪🇺 ${esc(eu.titolo)} (${eu.totale} eletti)</div><div class="pcard">${hemi(eu.gruppi, 340)}${legenda(eu.gruppi)}<p class="calc-n">${esc(eu.partiti)}</p><div class="stamp">Risultato delle elezioni 2024: cambia solo con subentri o cambi di gruppo</div>${link(eu.link, "Risultati ufficiali →")}</div>`;
  h += `<div class="gruppo-titolo">Prossimamente</div><div class="pcard"><ul class="nov">${p.prossimi.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></div>`;
  return h;
}

function renderProf() {
  const el = $("#prof-bar");
  const ids = Object.keys(state.professioni);
  if (state.nicchia === "auto") {
    el.hidden = false;
    el.innerHTML = [["offerte", "💸 Offerte e momento"], ["notizie", "📰 Notizie"]].map(([k, l]) => `<button class="chip${state.vistaAuto === k ? " on" : ""}" data-vauto="${k}">${l}</button>`).join("");
    return;
  }
  if (state.nicchia === "politica") {
    el.hidden = false;
    el.innerHTML = [["quadro", "🏛️ Quadro politico"], ["notizie", "📰 Notizie"]].map(([k, l]) => `<button class="chip${state.vistaPol === k ? " on" : ""}" data-vpol="${k}">${l}</button>`).join("");
    return;
  }
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

const VERSIONE_APP = "39";

async function carica(forza) {
  const q = `?t=${Date.now()}`;
  const j = async (f) => {
    const r = await fetch(`data/${f}.json${q}`, { cache: "no-store" });
    if (!r.ok) throw new Error(`${f}: ${r.status}`);
    return r.json();
  };
  try {
    const [news, aree, status, prof, profilo, confronto, politica, politicaAuto, politicaStato, deputati, senatori, partiti, votazioni, proposte] = await Promise.all([j("news"), j("aree"), j("status").catch(() => null), j("professioni").catch(() => ({})), j("profilo").catch(() => ({})), j("confronto").catch(() => null), j("politica").catch(() => null), j("politica_auto").catch(() => ({})), j("politica_status").catch(() => ({})), j("deputati").catch(() => null), j("senatori").catch(() => null), j("partiti").catch(() => null), j("votazioni").catch(() => null), j("proposte").catch(() => null)]);
    state.confronto = confronto; state.politica = politica; state.politicaAuto = politicaAuto || {}; state.politicaStato = politicaStato || {}; state.deputati = deputati; state.senatori = senatori; state.partiti = partiti; state.votazioni = votazioni; state.proposte = proposte;
    state.profilo = profilo || {};
    if (!Array.isArray(state.modelli)) state.modelli = [...(state.profilo.modelli || [])];
    state.professioni = prof.professioni || {}; state.gruppiProf = prof.gruppi || [];
    if (!Array.isArray(news.notizie)) throw new Error("dati non validi");
    state.news = news.notizie; state.aree = aree; state.status = status;
    $("#aggiornato").textContent = (news.aggiornato ? `Aggiornato ${fa(new Date(news.aggiornato))}` : "Rassegna") + ` · v${VERSIONE_APP}`;
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
    apriNews(n);
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
