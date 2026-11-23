import requests, json, re
H = {"User-Agent": "RassegnaPersonale/1.0 (app personale non commerciale; https://github.com/francescocaruso487-tech/super-agente) python-requests"}
out = {}
def g(u, **p):
    return requests.get(u, params=p, headers=H, timeout=40)
for w in ["lupus", "lux", "aqua", "amicus"]:
    t = g("https://it.wiktionary.org/api/rest_v1/page/html/" + w).content.decode("utf-8", "replace")
    i = t.find('id="Latino"')
    sec = t[i:]
    j = re.search(r'<section[^>]*data-mw-section-id[^>]*>\s*<h2', sec[20:])
    sec = sec[: j.start() + 20] if j else sec
    sec = re.sub(r"<img[^>]*>|<style.*?</style>", "", sec, flags=re.S)
    out["sec_" + w] = {"ids": re.findall(r'<h[2-4][^>]*id="([^"]+)"', sec), "len": len(sec), "tail": sec[-3500:]}
    r = g("https://it.wiktionary.org/w/api.php", action="query", list="search", srsearch='"dal latino ' + w + '"', srlimit=15, format="json", srnamespace=0)
    out["srch_" + w] = [x["title"] for x in r.json()["query"]["search"]]
    r = g("https://it.wiktionary.org/w/api.php", action="query", list="search", srsearch='"dal latino ' + w + '" -latino', srlimit=15, format="json", srnamespace=0)
    out["srch2_" + w] = [x["title"] for x in r.json()["query"]["search"]]
json.dump(out, open("docs/data/debug_sonda.json", "w"), ensure_ascii=False)
