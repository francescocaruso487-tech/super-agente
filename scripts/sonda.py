import json, re, html
from pathlib import Path
import requests
H = {"User-Agent": "RassegnaBot/1.0 (uso personale)", "Accept-Language": "it"}
D = Path("docs/data"); out = {}
def txt(t): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", t, flags=re.S))).strip()
for k, u in {"wq_main": "https://it.wikiquote.org/api/rest_v1/page/html/Pagina_principale",
             "wq_cit": "https://it.wikiquote.org/wiki/Template:Citazione_del_giorno",
             "wk_main": "https://it.wiktionary.org/api/rest_v1/page/html/Pagina_principale",
             "wk_feat": "https://it.wiktionary.org/api/rest_v1/feed/featured/2026/11/22",
             "wp_it_feat": "https://it.wikipedia.org/api/rest_v1/feed/featured/2026/11/22",
             "crusca": "https://accademiadellacrusca.it/it/parole-nuove",
             "sum": "https://it.wikipedia.org/api/rest_v1/page/summary/Caserta"}.items():
    try:
        r = requests.get(u, headers=H, timeout=30)
        out[k] = {"status": r.status_code, "n": len(r.text), "testo": txt(r.content.decode("utf-8", "replace"))[:1400]}
    except Exception as e:
        out[k] = {"err": str(e)[:100]}
try:
    q = 'SELECT ?c ?l (SAMPLE(?p) AS ?pop) WHERE { ?c wdt:P31 wd:Q747074; wdt:P17 wd:Q38. OPTIONAL{?c wdt:P1082 ?p} ?c rdfs:label ?l FILTER(lang(?l)="it") } GROUP BY ?c ?l LIMIT 9000'
    r = requests.get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"}, headers=H, timeout=120)
    b = r.json()["results"]["bindings"]
    out["comuni"] = {"status": r.status_code, "n": len(b), "es": [(x["l"]["value"]) for x in b[:5]]}
except Exception as e:
    out["comuni"] = {"err": str(e)[:150]}
(D / "debug_sonda.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
