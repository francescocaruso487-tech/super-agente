// Tema stile One UI 9: automatico chiaro/scuro + colori dinamici (da colore o da sfondo)
(function () {
  const K = "tema";
  const SW = [["Blu", 215, 72], ["Viola", 265, 55], ["Rosa", 335, 62], ["Rosso", 5, 68], ["Arancio", 25, 80], ["Verde", 145, 45], ["Acqua", 185, 60], ["Grafite", 220, 10]];
  const get = () => { try { return Object.assign({ mode: "auto", h: 215, s: 72 }, JSON.parse(localStorage.getItem(K) || "{}")); } catch (e) { return { mode: "auto", h: 215, s: 72 }; } };
  const put = (t) => { try { localStorage.setItem(K, JSON.stringify(t)); } catch (e) {} };
  const mq = window.matchMedia("(prefers-color-scheme: dark)");
  const hsl = (h, s, l) => `hsl(${Math.round(h)} ${Math.round(s)}% ${Math.round(l)}%)`;

  function applica(t) {
    const dark = t.mode === "dark" || (t.mode === "auto" && mq.matches);
    const r = document.documentElement.style, h = t.h, s = Math.min(t.s, 85), n = Math.min(t.s, 40);
    const v = dark ? {
      "--bg": hsl(h, n * .25, 6), "--card": hsl(h, n * .3, 11.5), "--ink": hsl(h, 15, 94), "--mute": hsl(h, 10, 66),
      "--line": hsl(h, n * .3, 18), "--chip": hsl(h, n * .45, 18), "--accent": hsl(h, s, 74), "--on-accent": hsl(h, 45, 12),
      "--accent-soft": hsl(h, n * .7, 24), "--brand": hsl(h, s, 74), "--shadow": "none", "--nav": hsl(h, n * .3, 14) + " / .82"
    } : {
      "--bg": hsl(h, n * .5, 96), "--card": hsl(h, n * .35, 99.3), "--ink": hsl(h, 30, 12), "--mute": hsl(h, 10, 42),
      "--line": hsl(h, n * .35, 91), "--chip": hsl(h, n * .6, 92), "--accent": hsl(h, s, 42), "--on-accent": "#fff",
      "--accent-soft": hsl(h, n * .9, 88), "--brand": hsl(h, s, 42), "--shadow": "0 1px 2px rgba(0,0,0,.03)", "--nav": hsl(h, n * .35, 99.3) + " / .85"
    };
    for (const k in v) r.setProperty(k, v[k]);
    r.setProperty("color-scheme", dark ? "dark" : "light");
    const m = document.querySelector('meta[name="theme-color"]');
    if (m) m.content = dark ? hsl(h, n * .25, 6) : hsl(h, n * .5, 96);
    document.body && document.body.classList.toggle("scuro", dark);
  }

  // colore dominante da un'immagine (sfondo del telefono)
  function daImmagine(file) {
    return new Promise((res, rej) => {
      const img = new Image(), url = URL.createObjectURL(file);
      img.onload = () => {
        const c = document.createElement("canvas"), W = 48, H = 48; c.width = W; c.height = H;
        const x = c.getContext("2d", { willReadFrequently: true }); x.drawImage(img, 0, 0, W, H);
        const d = x.getImageData(0, 0, W, H).data, B = Array.from({ length: 24 }, () => ({ w: 0, h: 0, s: 0, n: 0 }));
        for (let i = 0; i < d.length; i += 4) {
          const r = d[i] / 255, g = d[i + 1] / 255, b = d[i + 2] / 255, mx = Math.max(r, g, b), mn = Math.min(r, g, b), l = (mx + mn) / 2, c2 = mx - mn;
          if (c2 < .08 || l < .12 || l > .9) continue;
          const sat = c2 / (1 - Math.abs(2 * l - 1));
          let hh = mx === r ? ((g - b) / c2) % 6 : mx === g ? (b - r) / c2 + 2 : (r - g) / c2 + 4; hh = (hh * 60 + 360) % 360;
          const k = Math.floor(hh / 15) % 24, w = sat * (1 - Math.abs(l - .5));
          B[k].w += w; B[k].h += hh * w; B[k].s += sat * w; B[k].n++;
        }
        B.sort((a, b) => b.w - a.w);
        URL.revokeObjectURL(url);
        const t = B[0];
        if (!t || t.w <= 0) return res({ h: 220, s: 10 });
        res({ h: t.h / t.w, s: Math.max(30, Math.min(80, t.s / t.w * 100)) });
      };
      img.onerror = rej; img.src = url;
    });
  }

  function UI() {
    const sheet = document.getElementById("tema-sheet");
    if (!sheet) return;
    const t = get();
    const disegna = () => {
      const c = get();
      sheet.querySelector(".sw-mode").innerHTML = [["auto", "Automatico"], ["light", "Chiaro"], ["dark", "Scuro"]].map(([k, l]) => `<button data-mode="${k}" class="${c.mode === k ? "on" : ""}">${l}</button>`).join("");
      sheet.querySelector(".sw-col").innerHTML = SW.map(([n, h, s]) => `<button data-h="${h}" data-s="${s}" aria-label="${n}" class="${Math.round(c.h) === h ? "on" : ""}" style="background:${hsl(h, s, 52)}"></button>`).join("");
    };
    const apri = () => { disegna(); sheet.hidden = false; requestAnimationFrame(() => sheet.classList.add("open")); };
    const chiudi = () => { sheet.classList.remove("open"); setTimeout(() => (sheet.hidden = true), 280); };
    document.getElementById("btn-tema").addEventListener("click", apri);
    sheet.addEventListener("click", async (e) => {
      if (e.target.matches(".sheet-bg,.sheet-x")) return chiudi();
      const m = e.target.closest("[data-mode]"), c = e.target.closest("[data-h]");
      if (m) { const x = get(); x.mode = m.dataset.mode; put(x); applica(x); disegna(); }
      if (c) { const x = get(); x.h = +c.dataset.h; x.s = +c.dataset.s; put(x); applica(x); disegna(); }
    });
    sheet.querySelector("#tema-file").addEventListener("change", async (e) => {
      const f = e.target.files[0]; if (!f) return;
      const nota = sheet.querySelector(".sw-nota");
      try { const r = await daImmagine(f), x = get(); x.h = r.h; x.s = r.s; put(x); applica(x); disegna(); nota.textContent = "Colori presi dal tuo sfondo."; }
      catch (err) { nota.textContent = "Non riesco a leggere questa immagine."; }
      e.target.value = "";
    });
  }

  applica(get());
  mq.addEventListener("change", () => applica(get()));
  document.addEventListener("DOMContentLoaded", () => {
    applica(get()); UI();
  });
})();
