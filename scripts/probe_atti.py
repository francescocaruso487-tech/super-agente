import json, re
from pathlib import Path
import requests
H = {"User-Agent": "Mozilla/5.0 (RassegnaBot uso personale)"}
out = {}
def get(k, u):
    try:
        r = requests.get(u, headers=H, timeout=25)
        out[k] = {"url": r.url, "status": r.status_code, "bytes": len(r.text),
                  "links": re.findall(r'href="([^"#]+)"[^>]*>([^<]{3,80})<', r.text)[:60],
                  "head": re.sub(r"\s+", " ", r.text)[:1500]}
        return r.text
    except Exception as e:
        out[k] = {"errore": str(e)[:150]}
t = get("burc", "https://burc.regione.campania.it/eBurcWeb/publicContent/home/index.iface")
for k, u in {"gu_rss": "https://www.gazzettaufficiale.it/rss/SG", "regione_atti": "https://www.regione.campania.it/amministrazione-trasparente",
             "regione_giunta": "https://www.regione.campania.it/regione/it/la-giunta/delibere-della-giunta"}.items():
    get(k, u)
Path("docs/data/debug_atti.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
