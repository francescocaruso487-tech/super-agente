#!/usr/bin/env python3
"""Sonda temporanea: quali fonti ufficiali di atti sono leggibili da un runner."""
import json, re
from pathlib import Path
import requests
URLS = {
 "burc_home": "https://burc.regione.campania.it/",
 "burc_it": "https://burc.regione.campania.it/eBurcWeb/publicContent/home.iface",
 "regione_delibere": "https://www.regione.campania.it/",
 "comune_caserta": "https://www.comune.caserta.it/",
 "caserta_albo": "https://www.comune.caserta.it/albo-pretorio",
 "caserta_trasp": "https://www.comune.caserta.it/amministrazione-trasparente",
 "provincia_caserta": "https://www.provincia.caserta.it/",
 "provincia_albo": "https://www.provincia.caserta.it/albo-pretorio",
 "gu_serie": "https://www.gazzettaufficiale.it/",
 "normattiva": "https://www.normattiva.it/",
 "anac_open": "https://dati.anticorruzione.it/",
 "opencoesione": "https://opencoesione.gov.it/",
}
H = {"User-Agent": "Mozilla/5.0 (RassegnaBot uso personale)", "Accept": "text/html,application/xhtml+xml"}
out = {}
for k, u in URLS.items():
    try:
        r = requests.get(u, headers=H, timeout=25, allow_redirects=True)
        t = r.text
        title = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I)
        out[k] = {"url": r.url, "status": r.status_code, "bytes": len(t),
                  "title": (title.group(1).strip()[:100] if title else None),
                  "rss": re.findall(r'href="([^"]*(?:rss|feed|xml)[^"]*)"', t, re.I)[:5],
                  "albo": re.findall(r'href="([^"]*(?:albo|delibere|determine|ordinanze)[^"]*)"', t, re.I)[:8]}
    except Exception as e:
        out[k] = {"errore": str(e)[:150]}
Path("docs/data/debug_atti.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
