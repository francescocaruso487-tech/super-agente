/* Chat con le fonti: risponde SOLO usando le notizie dell'archivio. La chiave resta sul telefono. */
(function () {
  const MODELLO = "claude-haiku-5-5";
  const MODELLO_GEMINI = "gemini-flash-latest";
  const $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const get = (k) => { try { return localStorage.getItem(k) || ""; } catch { return ""; } };
  const set = (k, v) => { try { v ? localStorage.setItem(k, v) : localStorage.removeItem(k); } catch { /* ok */ } };
  const STOP = new Set("il lo la le gli un una uno di del della dei delle da in con su per tra fra che chi cui come cosa quali quale quando dove sono sia essere hanno ha può puo posso devo ci mi si non più piu anche ma se è e o a al alla alle ai nel nella nelle negli sul sulla sulle degli dalla dalle novità novita ultime ultimo oggi".split(" "));
  let storico = [];

  function cerca(domanda, n = 24) {
    const notizie = (window.__state && window.__state.news) || [];
    const t = domanda.toLowerCase().replace(/[^\p{L}\p{N}\s/.-]/gu, " ").split(/\s+/).filter((w) => w.length > 2 && !STOP.has(w));
    const now = Date.now();
    const pt = notizie.map((x) => {
      const txt = (x.titolo + " " + (x.sintesi || "")).toLowerCase(), tit = x.titolo.toLowerCase();
      let s = 0;
      for (const w of t) { const rx = new RegExp("(?<![\\p{L}\\p{N}])" + w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "u"); if (rx.test(tit)) s += 3; else if (rx.test(txt)) s += 1.5; }
      if (!s && t.length) return null;
      const gg = (now - new Date(x.pubblicata || x.visto)) / 86400000;
      return { x, p: s + Math.max(0, 1 - gg / 60) + (x.normativa ? 0.3 : 0) };
    }).filter(Boolean).sort((a, b) => b.p - a.p).slice(0, n);
    return pt.map((q) => q.x);
  }

  function render() {
    const box = $("#chat-msgs");
    if (!storico.length) { box.innerHTML = `<div class="vuoto"><b>Chiedi alle tue fonti</b>Es. "Novità sul superbonus?", "Cosa è cambiato per i cambi di destinazione d'uso?", "Bandi per Caserta?". Rispondo solo con le notizie raccolte, citando le fonti.</div>`; return; }
    box.innerHTML = storico.map((m) => m.r === "u"
      ? `<div class="msg u">${esc(m.t)}</div>`
      : `<div class="msg a">${m.t}${m.fonti ? `<div class="fonti-chat">${m.fonti}</div>` : ""}</div>`).join("");
    window.scrollTo(0, document.body.scrollHeight);
  }

  function formatta(testo, usate) {
    let h = esc(testo).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\n/g, "<br>");
    h = h.replace(/\[(\d{1,2})\]/g, (m, i) => usate[i - 1] ? `<a class="rif" href="${esc(usate[i - 1].link)}" target="_blank" rel="noopener">[${i}]</a>` : m);
    return h;
  }

  async function inviaInterno(domanda) {
    const chiave = get("chiave_api");
    if (!chiave) { $("#chat-setup").hidden = false; return; }
    const usate = cerca(domanda);
    storico.push({ r: "u", t: domanda }); storico.push({ r: "a", t: "<i>Sto cercando nelle fonti…</i>" }); render();
    const elenco = usate.map((x, i) => `[${i + 1}] ${x.titolo} — ${x.fonte_nome}, ${(x.pubblicata || x.visto || "").slice(0, 10)}${x.luogo ? ", " + x.luogo : ""}${x.sintesi ? ". " + x.sintesi.slice(0, 220) : ""}`).join("\n");
    const sistema = "Sei l'assistente di un ingegnere edile che lavora in Campania (zona Caserta). Rispondi in italiano, in modo breve e pratico (max 150 parole), usando ESCLUSIVAMENTE le notizie numerate qui sotto. Cita le fonti con [n] accanto a ogni affermazione. Non inventare norme, date, importi o numeri di articolo. Se le notizie non bastano, dillo chiaramente e suggerisci cosa verificare (ente o documento ufficiale). Ricorda che sono notizie: per decisioni professionali va letta la fonte ufficiale.\n\nNOTIZIE:\n" + (elenco || "(nessuna notizia pertinente trovata)");
    const msgs = storico.slice(0, -1).slice(-8).map((m) => ({ role: m.r === "u" ? "user" : "assistant", content: m.r === "u" ? m.t : m.t.replace(/<[^>]+>/g, "") }));
    try {
      let testo;
      if (!chiave.startsWith("sk-ant-")) {
        // Google Gemini (piano gratuito)
        const contenuti = msgs.map((m) => ({ role: m.role === "user" ? "user" : "model", parts: [{ text: m.content }] }));
        const corpo = JSON.stringify({ systemInstruction: { parts: [{ text: sistema }] }, contents: contenuti, generationConfig: { maxOutputTokens: 900, temperature: 0.2 } });
        const url = `https://generativelanguage.googleapis.com/v1beta/models/${MODELLO_GEMINI}:generateContent`;
        let r = await fetch(url, { method: "POST", headers: { "x-goog-api-key": chiave, "content-type": "application/json" }, body: corpo });
        if (r.status === 401 || r.status === 403) r = await fetch(`${url}?key=${encodeURIComponent(chiave)}`, { method: "POST", headers: { "content-type": "application/json" }, body: corpo });
        if (!r.ok) {
          const e = await r.json().catch(() => ({}));
          throw new Error(r.status === 400 || r.status === 401 || r.status === 403 ? `Google ha rifiutato la chiave (${r.status}): ${e?.error?.message || "controllala nelle impostazioni (⚙)"}` : r.status === 429 ? "Limite gratuito di Google raggiunto: riprova tra qualche minuto (o domani)." : `Errore ${r.status}: ${e?.error?.message || "riprova"}`);
        }
        const j = await r.json();
        testo = (j.candidates?.[0]?.content?.parts || []).map((c) => c.text || "").join("");
        if (!testo) throw new Error("Risposta vuota: riprova con una domanda diversa.");
      } else {
        const r = await fetch("https://api.anthropic.com/v1/messages", {
          method: "POST",
          headers: { "x-api-key": chiave, "anthropic-version": "2023-06-01", "content-type": "application/json", "anthropic-dangerous-direct-browser-access": "true" },
          body: JSON.stringify({ model: MODELLO, max_tokens: 600, system: sistema, messages: msgs }),
        });
        if (!r.ok) {
          const e = await r.json().catch(() => ({}));
          throw new Error(r.status === 401 ? "Chiave non valida: controllala nelle impostazioni (⚙)." : r.status === 402 || /credit/i.test(e?.error?.message || "") ? "Credito esaurito sul conto Anthropic: ricarica da console.anthropic.com." : `Errore ${r.status}: ${e?.error?.message || "riprova"}`);
        }
        const j = await r.json();
        testo = (j.content || []).map((c) => c.text || "").join("");
      }
      const citati = [...new Set([...testo.matchAll(/\[(\d{1,2})\]/g)].map((m) => +m[1]))].filter((i) => usate[i - 1]).sort((a, b) => a - b);
      storico[storico.length - 1] = { r: "a", t: formatta(testo, usate), fonti: citati.map((i) => `<a href="${esc(usate[i - 1].link)}" target="_blank" rel="noopener">[${i}] ${esc(usate[i - 1].titolo.slice(0, 70))}</a>`).join("") };
    } catch (e) {
      storico[storico.length - 1] = { r: "a", t: `<span class="err">${esc(e.message === "Failed to fetch" ? "Nessuna connessione o chiave non accettata dal browser." : e.message)}</span>` };
    }
    render();
  }

  async function invia(domanda) {
    try {
      await Promise.race([inviaInterno(domanda), new Promise((_, rj) => setTimeout(() => rj(new Error("Nessuna risposta dopo 40 secondi. Controlla la connessione e riprova.")), 40000))]);
    } catch (e) {
      if (storico.length && storico[storico.length - 1].r === "a") storico[storico.length - 1] = { r: "a", t: `<span class="err">${esc(e.message || String(e))}</span>` };
      else storico.push({ r: "a", t: `<span class="err">${esc(e.message || String(e))}</span>` });
      render();
    }
  }

  function init() {
    if (!$("#chat-msgs")) return;
    render();
    $("#chat-setup").hidden = !!get("chiave_api");
    $("#chat-form").addEventListener("submit", (e) => {
      e.preventDefault();
      const i = $("#chat-input"), q = i.value.trim();
      if (!q) return; i.value = ""; invia(q);
    });
    $("#chat-key-salva").addEventListener("click", () => {
      const k = $("#chat-key").value.trim();
      if (k.length < 20 || /\s/.test(k)) { $("#chat-key-msg").textContent = "Chiave non valida: incollala per intero, senza spazi."; return; }
      set("chiave_api", k); $("#chat-key").value = ""; $("#chat-key-msg").textContent = ""; $("#chat-setup").hidden = true;
    });
    $("#chat-key-togli").addEventListener("click", () => { set("chiave_api", ""); $("#chat-setup").hidden = false; });
    $("#chat-ingranaggio").addEventListener("click", () => { $("#chat-setup").hidden = !$("#chat-setup").hidden; });
    $("#chat-nuova").addEventListener("click", () => { storico = []; render(); });
  }
  document.addEventListener("DOMContentLoaded", init);
})();
