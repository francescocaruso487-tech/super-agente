import json, re, html
from pathlib import Path
import requests
H = {"User-Agent": "RassegnaBot/1.0 (uso personale)", "Accept-Language": "it"}
D = Path("docs/data"); out = {}
def txt(t): return re.sub(r"\s+", " ", html.unescape(re.sub(r"<script.*?</script>|<style.*?</style>|<[^>]+>", " ", t, flags=re.S))).strip()
def g(u, **kw): return requests.get(u, headers=H, timeout=40, **kw)
t = g("https://it.wikiquote.org/api/rest_v1/page/html/Wikiquote:Archivio_delle_citazioni_del_giorno").content.decode("utf-8", "replace")
out["arch"] = {"n": len(t), "testo": txt(t)[:1500], "links": re.findall(r'href="\./(Wikiquote:[^"#]+)"', t)[:30]}
t = g("https://it.wiktionary.org/api/rest_v1/page/html/Wikizionario:Parola_del_giorno").content.decode("utf-8", "replace")
out["pdg"] = {"n": len(t), "testo": txt(t)[:1500], "links": re.findall(r'href="\./([^"#:]+)"', t)[:40]}
for pre in ["Locuz", "Prover", "Modi", "Espress", "Detti"]:
    r = g("https://it.wiktionary.org/w/api.php", params={"action": "query", "list": "allcategories", "acprefix": pre, "aclimit": 30, "acprop": "size", "format": "json"}).json()
    out["cat_" + pre] = [(c["*"], c["size"]) for c in r["query"]["allcategories"]]
(D / "debug_sonda.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
