import json, re, html
from pathlib import Path
import requests
H = {"User-Agent": "RassegnaPersonale/1.0 (app personale non commerciale; https://github.com/francescocaruso487-tech/super-agente) python-requests", "Accept-Language": "it"}
def txt(t): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", t))).strip()
out = {}
t = requests.get("https://it.wikipedia.org/api/rest_v1/page/html/Locuzioni_latine", headers=H, timeout=60).content.decode("utf-8", "replace")
T = txt(t)
i = T.find("Ab ovo", 2000)
out["wp"] = T[i - 300:i + 1200]
j = t.find(">Ab ovo<")
out["wp_html"] = t[j - 400:j + 1500]
r = requests.get("https://it.wikiquote.org/api/rest_v1/page/html/Proverbi_latini", headers=H, timeout=60)
out["wq_status"] = r.status_code
w = r.content.decode("utf-8", "replace")
out["wq_len"] = len(w); out["wq_li"] = w.count("<li")
out["wq_txt"] = txt(w)[:1500]
Path("docs/data/debug_sonda.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
