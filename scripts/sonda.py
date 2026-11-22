import json, re
from pathlib import Path
import requests
H = {"User-Agent": "Mozilla/5.0 (RassegnaBot uso personale)", "Accept-Language": "it"}
U = {
 "vn_santo": "https://www.vaticannews.va/it/santo-del-giorno/11/22.html",
 "vn_santo2": "https://www.vaticannews.va/it/santo-del-giorno.html",
 "wiki_otd": "https://it.wikipedia.org/api/rest_v1/feed/onthisday/all/11/22",
 "wiki_otd_en": "https://api.wikimedia.org/feed/v1/wikipedia/it/onthisday/all/11/22",
 "costituzione": "https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:costituzione:1947-12-27",
 "cei_liturgia": "https://www.chiesacattolica.it/liturgia-del-giorno/",
 "santiebeati": "https://www.santiebeati.it/",
 "wiki_santi": "https://it.wikipedia.org/api/rest_v1/page/html/22_novembre",
 "wikizionario": "https://it.wiktionary.org/api/rest_v1/feed/featured/2026/11/22",
}
out = {}
for k, u in U.items():
    try:
        r = requests.get(u, headers=H, timeout=25)
        t = r.text
        out[k] = {"url": r.url, "status": r.status_code, "bytes": len(t), "head": re.sub(r"\s+", " ", t)[:700]}
        if k == "vn_santo":
            out[k]["testo"] = re.sub(r"\s+", " ", re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", t, flags=re.S))[:2500]
        if k == "wiki_santi":
            i = t.find("Santi")
            out[k]["testo"] = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t[t.find("Ricorrenze"):]))[:1800]
    except Exception as e:
        out[k] = {"errore": str(e)[:150]}
Path("docs/data/debug_sonda.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
