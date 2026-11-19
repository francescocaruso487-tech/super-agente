"use strict";
// Super Agente - interfaccia. Nessuna dipendenza esterna.
const $ = (s) => document.querySelector(s);
const store = {
  get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* ignora */ } },
};
const state = {
  news: [], aree: {}, status: null,
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
const nome = (a) => state.aree[a]?.nome || a;
const colore = (a) => state.aree[a]?.colore || "#7b8794";

function card(n) {
  const letta = state.lette.has(n.id);
  const nuovo = !letta && state.ultimaVisita && new Date(n.visto) > new Date(state.ultimaVisita);
  const stella = state.stelle.has(n.id);
  const luogoB = n.luogo ? `<span class="badge luogo">📍 ${esc(n.luogo)}</span>` : "";
  const badge = luogoB + n.aree.filter((a) => a !== "altro" || !n.luogo).map((a) => `<span class="badge" style="--c:${colore(a)}">${esc(nome(a))}</span>`).join("");
  return `<article class="card${letta ? " letta" : ""}" data-id="${n.id}" style="--c:${colore(n.aree[0])}">
    <div class="riga">${badge}${n.normativa ? '<span class="badge norm">Normativa</span>' : ""}${nuovo ? '<span class="nuovo" title="Nuova"></span>' : ""}</div>
    <h3 class="titolo">${esc(n.titolo)}</h3>
    ${n.sintesi ? `<p class="sintesi">${esc(n.sintesi)}</p>` : ""}
    <div class="piede"><span>${esc(n.fonte_nome)} · ${fa(dataDi(n))}</span>
      <button class="stella${stella ? " on" : ""}" data-star="${n.id}" aria-label="Salva">${stella ? "★" : "☆"}</button></div>
  </article>`;
}

function filtra({ area, query, soloNorm }) {
  const q = query.trim().toLowerCase();
  return state.news.filter((n) => {
    if (area === "stelle") { if (!state.stelle.has(n.id)) return false; }
    else if (area === "tutte") { if (n.aree.length === 1 && n.aree[0] === "altro" && !n.luogo) return false; }
    else if (area === "locale") { if (!n.luogo) return false; }
    else if (area === "altro") { if (n.luogo || !n.aree.includes("altro")) return false; }
    else if (!n.aree.includes(area)) return false;
    if (soloNorm && !n.normativa) return false;
    if (q && !(n.titolo + " " + (n.sintesi || "") + " " + n.fonte_nome).toLowerCase().includes(q)) return false;
    return true;
  });
}

function chips(el, corrente, onPick) {
  const base = state.news;
  const conta = (a) => base.filter((n) => a === "locale" ? !!n.luogo : a === "altro" ? (!n.luogo && n.aree.includes("altro")) : n.aree.includes(a)).length;
  const voci = [["tutte", "Tutte", null, base.filter((n) => !(n.aree.length === 1 && n.aree[0] === "altro" && !n.luogo)).length],
    ["stelle", "★ Salvate", null, state.stelle.size]];
  if (state.aree.locale) voci.push(["locale", nome("locale"), colore("locale"), conta("locale")]);
  Object.keys(state.aree).filter((a) => a !== "altro" && a !== "locale").forEach((a) => voci.push([a, nome(a), colore(a), conta(a)]));
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
  if (aperta && Object.keys(sottoDef).length) {
    if (selSotto) lista = listaTot.filter((n) => (n.sotto || []).includes(`${k}.${selSotto}`));
    const cnt = (sid) => listaTot.filter((n) => (n.sotto || []).includes(`${k}.${sid}`)).length;
    chipsSotto = `<div class="sotto">` +
      `<button class="chip s${selSotto ? "" : " on"}" data-sotto="${k}|">Tutte <small>${listaTot.length}</small></button>` +
      Object.entries(sottoDef).map(([sid, nm]) => `<button class="chip s${selSotto === sid ? " on" : ""}" data-sotto="${k}|${sid}">${esc(nm)} <small>${cnt(sid)}</small></button>`).join("") +
      `</div>`;
  }
  const nuovi = lista.filter((n) => !state.lette.has(n.id) && state.ultimaVisita && new Date(n.visto) > new Date(state.ultimaVisita)).length;
  const titolo = k === "stelle" ? "★ Salvate" : nome(k);
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
  const chiavi = ["stelle", "bonus", "imprese", "locale", ...Object.keys(state.aree).filter((a) => !["altro", "locale", "bonus", "imprese"].includes(a)), "altro"];
  let out = "";
  for (const k of chiavi) {
    const lista = filtra({ area: k, query: "", soloNorm: state.soloNorm });
    if (!lista.length && k !== "stelle") { if (k === "altro") continue; }
    if (k === "stelle" && !state.stelle.size) continue;
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
  if (!s || !s.fonti.length) { $("#fonti-riepilogo").innerHTML = vuoto("Nessun dato sulle fonti", "Compare dopo il primo aggiornamento."); return; }
  const problemi = s.fonti.filter((f) => f.stato === "errore" || f.stato === "vuoto").length;
  const scrap = s.fonti.filter((f) => f.stato === "ok_scraping" || f.stato === "ok_indiretto").length;
  $("#fonti-riepilogo").innerHTML = `<b>${s.fonti_ok} / ${s.fonti_totale} fonti attive</b>
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
}

function renderTutto() { renderNovita(); renderArchivio(); renderFonti(); }

const VERSIONE_APP = "10";

async function carica(forza) {
  const q = `?t=${Date.now()}`;
  const j = async (f) => {
    const r = await fetch(`data/${f}.json${q}`, { cache: "no-store" });
    if (!r.ok) throw new Error(`${f}: ${r.status}`);
    return r.json();
  };
  try {
    const [news, aree, status] = await Promise.all([j("news"), j("aree"), j("status").catch(() => null)]);
    if (!Array.isArray(news.notizie)) throw new Error("dati non validi");
    state.news = news.notizie; window.__state = state; state.aree = aree; state.status = status;
    $("#aggiornato").textContent = (news.aggiornato ? `Aggiornato ${fa(new Date(news.aggiornato))}` : "Edilizia e ingegneria") + ` · v${VERSIONE_APP}`;
    renderTutto();
  } catch (err) {
    if (!state.news.length) {
      $("#lista-novita").innerHTML = vuoto("Non riesco a caricare le notizie", "Controlla la connessione e tocca ⟳ in alto.");
      $("#aggiornato").textContent = `Non aggiornato · v${VERSIONE_APP}`;
    }
  }
}

document.addEventListener("click", (e) => {
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
    state.lette.add(n.id); store.set("lette", [...state.lette].slice(-3000));
    c.classList.add("letta");
    window.open(n.link, "_blank", "noopener");
  }
});
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
  document.body.classList.toggle("in-chat", b.dataset.tab === "chat");
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
