import requests, json, re
H = {"User-Agent": "RassegnaPersonale/1.0 (app personale non commerciale; https://github.com/francescocaruso487-tech/super-agente) python-requests"}
out = {}
def g(u, **p):
    r = requests.get(u, params=p, headers=H, timeout=40)
    return r
for cat in ["Sostantivi in latino", "Sostantivi latini", "Latino-Sostantivi", "Lemmi in latino", "Verbi in latino", "Aggettivi in latino", "Parole latine", "Latino"]:
    r = g("https://it.wiktionary.org/w/api.php", action="query", titles="Categoria:" + cat, prop="categoryinfo", format="json")
    out["cat_" + cat] = r.json()
r = g("https://it.wiktionary.org/w/api.php", action="query", list="allcategories", acprefix="Latino", aclimit=50, format="json")
out["allcat_Latino"] = r.json()
r = g("https://it.wiktionary.org/w/api.php", action="query", list="allcategories", acprefix="Sostantivi", aclimit=50, format="json")
out["allcat_Sost"] = r.json()
for w in ["lupus", "lux", "aqua"]:
    r = g("https://it.wiktionary.org/api/rest_v1/page/html/" + w)
    t = r.content.decode("utf-8", "replace")
    i = t.find('id="Latino"')
    out["html_" + w] = {"status": r.status_code, "idx": i, "txt": t[i:i + 9000] if i >= 0 else t[:1500]}
json.dump(out, open("docs/data/debug_sonda.json", "w"), ensure_ascii=False)
