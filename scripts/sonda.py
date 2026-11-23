import json, re, html
from pathlib import Path
import requests
H = {"User-Agent": "RassegnaPersonale/1.0 (app personale non commerciale; https://github.com/francescocaruso487-tech/super-agente) python-requests", "Accept-Language": "it"}
out = {}
for k, u in {"prov": "Proverbi_latini", "modi": "Modi_di_dire_latini"}.items():
    r = requests.get("https://it.wikiquote.org/api/rest_v1/page/html/" + u, headers=H, timeout=60)
    w = r.content.decode("utf-8", "replace")
    lis = re.findall(r"<li[^>]*>(.*?)</li>", w, re.S)
    ok = [x for x in lis if len(re.sub(r"<[^>]+>", "", x)) > 25]
    out[k] = {"status": r.status_code, "n_li": len(lis), "n_ok": len(ok), "html": [re.sub(r"\s+", " ", x)[:600] for x in ok[40:44]]}
Path("docs/data/debug_sonda.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
