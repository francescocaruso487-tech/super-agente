import json, re
from pathlib import Path
import requests
H = {"User-Agent": "RassegnaPersonale/1.0 (app personale non commerciale; https://github.com/francescocaruso487-tech/super-agente) python-requests", "Accept-Language": "it"}
w = requests.get("https://it.wikiquote.org/api/rest_v1/page/html/Proverbi_latini", headers=H, timeout=60).content.decode("utf-8", "replace")
w = re.sub(r' (id|about|typeof|rel|data-mw)="[^"]*"| data-mw=\'[^\']*\'', "", w)
i = w.find("Ab amico reconciliato")
j = w.find("Facit experientia")
Path("docs/data/debug_sonda.json").write_text(json.dumps({"a": w[i - 200:i + 1500], "b": w[j - 300:j + 900]}, ensure_ascii=False, indent=1), encoding="utf-8")
