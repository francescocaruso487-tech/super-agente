import json, re
from pathlib import Path
import requests
H = {"User-Agent": "Mozilla/5.0 (RassegnaBot uso personale)", "Accept-Language": "it"}
D = Path("docs/data")
r = requests.get("https://www.vaticannews.va/it/santo-del-giorno/11/22.html", headers=H, timeout=30)
t = r.content.decode("utf-8", "replace")
i = t.find("<main")
(D / "debug_vn.html").write_text(t[i:i + 30000] if i > 0 else t[20000:50000], encoding="utf-8")
r = requests.get("https://www.normattiva.it/uri-res/N2Ls?urn:nir:stato:costituzione:1947-12-27", headers=H, timeout=30)
t = r.content.decode("utf-8", "replace")
j = t.find("Art. 1")
(D / "debug_cost.html").write_text(t[max(0, j - 1500):j + 4000], encoding="utf-8")
r = requests.get("https://it.wikipedia.org/api/rest_v1/feed/onthisday/all/11/22", headers=H, timeout=30)
d = r.json()
(D / "debug_otd.json").write_text(json.dumps({k: [{"text": x.get("text"), "year": x.get("year")} for x in v[:4]] + [len(v)] for k, v in d.items()}, ensure_ascii=False, indent=1), encoding="utf-8")
