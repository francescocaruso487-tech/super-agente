import html, json, re, time
from pathlib import Path
import requests
H = {"User-Agent": "Mozilla/5.0 (RassegnaBot uso personale)", "Accept-Language": "it"}
D = Path("docs/data")
s = requests.Session(); s.headers.update(H)
s.get("https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:costituzione:1947-12-27", timeout=30)
art = {}
tent = []
for n in range(1, 160):
    u = f"https://www.normattiva.it/atto/caricaArticolo?art.versione=1&art.idGruppo=1&art.flagTipoArticolo=0&art.codiceRedazionale=047U0001&art.idArticolo={n}&art.idSottoArticolo=1&art.idSottoArticolo1=10&art.dataPubblicazioneGazzetta=1947-12-27%2000:00:00.0&art.progressivo=0&riferimenti=false&qId=&art.imUpdate=false"
    try:
        r = s.get(u, timeout=25)
        t = r.content.decode("utf-8", "replace")
        m = re.search(r'article-num-akn"[^>]*>\s*([^<]+?)\s*</h2>', t)
        b = re.search(r'art-just-text-akn">(.*?)</span>', t, re.S)
        if m and b:
            testo = html.unescape(re.sub(r"\s*\n\s*", "\n", re.sub(r"<br\s*/?>", "\n", re.sub(r"<[^>]+>", "", b.group(1))))).strip()
            art[m.group(1).strip()] = testo
        tent.append((n, r.status_code, m.group(1).strip() if m else None))
    except Exception as e:
        tent.append((n, "err", str(e)[:40]))
    time.sleep(0.15)
(D / "debug_cost.json").write_text(json.dumps({"n": len(art), "chiavi": list(art)[:200], "tentativi": tent[:160], "esempio": {k: art[k][:200] for k in list(art)[:3] + list(art)[-3:]}}, ensure_ascii=False, indent=0), encoding="utf-8")
if len(art) > 100:
    (D / "costituzione.json").write_text(json.dumps({"fonte": "Normattiva - Costituzione della Repubblica italiana (1947)", "articoli": art}, ensure_ascii=False, indent=0), encoding="utf-8")
r = requests.get("https://it.wikipedia.org/api/rest_v1/page/html/22_novembre", headers=H, timeout=30)
t = r.content.decode("utf-8", "replace")
sez = re.split(r"<h2 ", t)
res = {}
for x in sez[1:]:
    tit = re.sub(r"<[^>]+>", "", re.search(r">(.*?)</h2>", x, re.S).group(1)) if "</h2>" in x else "?"
    li = re.findall(r"<li[^>]*>(.*?)</li>", x, re.S)
    res[tit] = {"n": len(li), "es": [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", i))[:160] for i in li[:3]]}
(D / "debug_wiki.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
