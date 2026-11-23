import json, re
from pathlib import Path
import requests
H = {"User-Agent": "RassegnaPersonale/1.0 (app personale non commerciale; https://github.com/francescocaruso487-tech/super-agente) python-requests", "Accept-Language": "it"}
t = requests.get("https://it.wikipedia.org/api/rest_v1/page/html/Locuzioni_latine", headers=H, timeout=60).content.decode("utf-8", "replace")
lis = re.findall(r"<li[^>]*>(.*?)</li>", t, re.S)
cand = [x for x in lis if "<b" in x or "<dfn" in x or "<i>" in x]
out = {"n": len(lis), "cand": len(cand), "campioni": [re.sub(r"\s+", " ", x)[:500] for x in cand[300:306]],
       "primi": [re.sub(r"\s+", " ", x)[:300] for x in lis[60:66]],
       "dl": t.count("<dt"), "dd": t.count("<dd"), "h2": re.findall(r"<h2[^>]*>(.*?)</h2>", t, re.S)[:6]}
i = t.find("<dt")
out["dt_html"] = t[i:i + 1200] if i > 0 else ""
Path("docs/data/debug_sonda.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
