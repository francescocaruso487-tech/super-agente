import requests, json, re
H = {"User-Agent": "RassegnaPersonale/1.0 (app personale non commerciale; https://github.com/francescocaruso487-tech/super-agente) python-requests"}
out = {}
for d in ["20261123", "20261129", "20261127", "20261208"]:
    r = requests.get("https://www.chiesacattolica.it/liturgia-del-giorno/?data-liturgia=" + d, headers=H, timeout=40)
    t = r.content.decode("utf-8", "replace")
    out[d] = {"status": r.status_code, "title": re.findall(r"<title>(.*?)</title>", t, re.S)[:1]}
    i = t.find("Acclamazione al Vangelo")
    k = t.find("Prima Lettura")
    out[d]["htmlvang"] = t[max(0, i - 1200): i + 3500]
    out[d]["htmltop"] = t[max(0, k - 2500): k + 600]
json.dump(out, open("docs/data/debug_sonda.json", "w"), ensure_ascii=False)
