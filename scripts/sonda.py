import json, re, html
from pathlib import Path
import requests
H = {"User-Agent": "RassegnaBot/1.0 (uso personale)", "Accept-Language": "it"}
D = Path("docs/data"); out = {}
def txt(t): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", t, flags=re.S))).strip()
for k, u in {"wk": "https://it.wiktionary.org/api/rest_v1/page/html/Pagina_principale", "wq": "https://it.wikiquote.org/api/rest_v1/page/html/Pagina_principale"}.items():
    t = requests.get(u, headers=H, timeout=30).content.decode("utf-8", "replace")
    T = txt(t)
    ctx = {}
    for w in ["del giorno", "Vetrina", "roverbi", "ocuzion", "Parola", "modi di dire", "Lemma"]:
        ctx[w] = [T[max(0, m.start() - 120):m.start() + 260] for m in re.finditer(w, T)][:3]
    out[k] = {"ctx": ctx, "links": re.findall(r'href="\./([^"#]+)"', t)[:60]}
    i = t.find("Citazione del giorno") if k == "wq" else t.find("giorno")
    out[k]["html"] = t[i - 300:i + 1800] if i > 0 else ""
(D / "debug_sonda.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
