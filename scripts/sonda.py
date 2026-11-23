import requests, json, re
H = {"User-Agent": "RassegnaPersonale/1.0 (app personale non commerciale; https://github.com/francescocaruso487-tech/super-agente) python-requests"}
out = {}
def g(u, **p):
    try:
        r = requests.get(u, params=p, headers=H, timeout=40)
        return r.status_code, r.content.decode("utf-8", "replace")
    except Exception as e:
        return 0, str(e)
for k, u in {"vn1": "https://www.vaticannews.va/it/vangelo-del-giorno/2026/11/23.html",
             "vn2": "https://www.vaticannews.va/it/vangelo-del-giorno.html",
             "vn3": "https://www.vaticannews.va/it/santo-del-giorno/11/23.html"}.items():
    s, t = g(u)
    i = t.find("Vangelo")
    out[k] = {"status": s, "len": len(t), "title": re.findall(r"<title>(.*?)</title>", t, re.S)[:1], "ctx": [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t[m.start()-200:m.start()+500])) for m in list(re.finditer(r"Vangelo", t))[:6]]}
    out[k]["sections"] = re.findall(r'<section[^>]*class="([^"]+)"', t)[:15]
s, t = g("https://api.getbible.net/v2/diodati/42/19.json")
out["getbible"] = {"status": s, "len": len(t), "head": t[:600]}
s, t = g("https://api.getbible.net/v2/translations.json")
out["translations_it"] = {"status": s, "it": [k for k in (json.loads(t) if s == 200 else {}) if k in ("diodati", "riveduta", "luzzi")]}
json.dump(out, open("docs/data/debug_sonda.json", "w"), ensure_ascii=False)
