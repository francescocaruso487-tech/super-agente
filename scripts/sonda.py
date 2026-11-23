import requests, json, re, html
H = {"User-Agent": "RassegnaPersonale/1.0 (app personale non commerciale; https://github.com/francescocaruso487-tech/super-agente) python-requests"}
out = {}
for d in ["20261123", "20261129", "20261208", "20261225"]:
    t = requests.get("https://www.chiesacattolica.it/liturgia-del-giorno/?data-liturgia=" + d, headers=H, timeout=40).content.decode("utf-8", "replace")
    secs = []
    for m in re.finditer(r'<h2[^>]*cci-liturgia-giorno-section-title[^>]*>(.*?)</h2>(.*?)(?=<h2[^>]*cci-liturgia-giorno-section-title|$)', t, re.S):
        blk = m.group(2)
        secs.append({"h2": re.sub(r"<[^>]+>", "", m.group(1)).strip(),
                     "h3": re.findall(r"<h3[^>]*>(.*?)</h3>", blk, re.S)[:1],
                     "links": re.findall(r'<a title="Leggi ([^"]+) su BibbiaEdu" href="([^"]+)"', blk)[:3],
                     "txt": re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", blk)))[:230]})
    out[d] = {"n_titles": len(re.findall("cci_content_single_title", t)), "secs": secs}
json.dump(out, open("docs/data/debug_sonda.json", "w"), ensure_ascii=False)
