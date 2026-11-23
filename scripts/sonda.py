import requests, json, re
H = {"User-Agent": "RassegnaPersonale/1.0 (app personale non commerciale; https://github.com/francescocaruso487-tech/super-agente) python-requests"}
out = {}
def g(u, **p):
    try:
        r = requests.get(u, params=p, headers=H, timeout=40)
        return r.status_code, r.content.decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)
s, t = g("https://www.vaticannews.va/it/santo-del-giorno/11/23.html")
out["links_vangelo"] = sorted(set(re.findall(r'href="([^"]*(?:vangelo|liturgia|lettur)[^"]*)"', t, re.I)))[:30]
for k, u in {"vn_a": "https://www.vaticannews.va/it/vangelo-del-giorno-e-santo/2026/11/23.html",
             "vn_b": "https://www.vaticannews.va/it/vangelo-del-giorno-e-commento.html",
             "cei": "https://www.chiesacattolica.it/liturgia-del-giorno/?data-liturgia=20261123",
             "cei2": "https://www.chiesacattolica.it/liturgia-del-giorno/"}.items():
    s, t = g(u)
    out[k] = {"status": s, "len": len(t), "title": re.sub(r"\s+", " ", " ".join(re.findall(r"<title>(.*?)</title>", t, re.S)[:1]))[:150],
              "ctx": [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t[m.start()-100:m.start()+400])) for m in list(re.finditer(r"Vangelo", t))[:4]]}
for u in ["https://api.getbible.net/v2/riveduta/42/19.json", "https://api.getbible.net/v2/riveduta/42.json", "https://api.getbible.net/v2/riveduta/books.json"]:
    s, t = g(u)
    out[u] = {"status": s, "len": len(t), "head": t[:700]}
json.dump(out, open("docs/data/debug_sonda.json", "w"), ensure_ascii=False)
