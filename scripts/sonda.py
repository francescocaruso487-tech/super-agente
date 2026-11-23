import requests, json, re, time
H = {"User-Agent": "RassegnaPersonale/1.0 (app personale non commerciale; https://github.com/francescocaruso487-tech/super-agente) python-requests"}
out = {}
def g(u, **p):
    time.sleep(1)
    return requests.get(u, params=p, headers=H, timeout=40)
qs = {
 "A": 'incategory:"Sostantivi in italiano" "dal latino {w}"',
 "B": 'incategory:"Sostantivi in italiano|Verbi in italiano|Aggettivi in italiano" "dal latino {w}"',
 "C": 'incategory:"Lemmi in italiano" "dal latino {w}"',
}
for w in ["lux", "aqua", "pater", "lupus", "rex"]:
    for k, q in qs.items():
        try:
            r = g("https://it.wiktionary.org/w/api.php", action="query", list="search", srsearch=q.format(w=w), srlimit=12, srnamespace=0, format="json", srprop="snippet")
            out[f"{k}_{w}"] = [(x["title"], re.sub(r"<[^>]+>", "", x["snippet"])[:90]) for x in r.json()["query"]["search"]]
        except Exception as e:
            out[f"{k}_{w}"] = str(e)
json.dump(out, open("docs/data/debug_sonda.json", "w"), ensure_ascii=False)
