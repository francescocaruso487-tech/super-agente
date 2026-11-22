import json, re
from pathlib import Path
import requests
H = {"User-Agent": "Mozilla/5.0 (RassegnaBot uso personale)"}
out = {}
for k in ["SG", "S1", "S3"]:
    try:
        r = requests.get(f"https://www.gazzettaufficiale.it/rss/{k}", headers=H, timeout=25)
        items = re.findall(r"<item>(.*?)</item>", r.text, re.S)
        out[k] = {"status": r.status_code, "n": len(items), "head": r.text[:500], "items": [re.sub(r"\s+", " ", i)[:420] for i in items[:60]]}
    except Exception as e:
        out[k] = {"errore": str(e)[:150]}
Path("docs/data/debug_atti.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
