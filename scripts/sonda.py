import json, re, html
from pathlib import Path
import requests
H = {"User-Agent": "RassegnaPersonale/1.0 (app personale non commerciale; https://github.com/francescocaruso487-tech/super-agente) python-requests", "Accept-Language": "it"}
D = Path("docs/data"); out = {}
def g(u, **kw): return requests.get(u, headers=H, timeout=40, **kw)
r = g("https://it.wikipedia.org/w/api.php", params={"action": "query", "list": "search", "srsearch": "intitle:\"Locuzioni latine\"", "srlimit": 30, "format": "json"}).json()
out["titoli"] = [x["title"] for x in r["query"]["search"]]
t = g("https://it.wikipedia.org/api/rest_v1/page/html/Locuzioni_latine").content.decode("utf-8", "replace")
out["main_len"] = len(t)
out["main_links"] = re.findall(r'href="\./(Locuzioni_latine[^"#]*)"', t)[:40]
out["main_head"] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))[:800]
for tit in out["titoli"][:2]:
    p = g("https://it.wikipedia.org/api/rest_v1/page/html/" + requests.utils.quote(tit.replace(" ", "_"))).content.decode("utf-8", "replace")
    i = p.find("<li")
    out["pag_" + tit] = {"n_li": p.count("<li"), "n_tr": p.count("<tr"), "html": p[i:i + 1500] if i > 0 else p[:1500]}
(D / "debug_sonda.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
