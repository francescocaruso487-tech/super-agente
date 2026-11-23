import requests, json
H = {"User-Agent": "RassegnaPersonale/1.0 (app personale non commerciale)", "Content-Type": "application/json"}
base = ["publication-number", "notice-title"]
out = {}
for f in ["contract-nature", "classification-cpv", "procedure-type", "notice-type", "main-activity", "legal-basis", "framework-agreement", "duration-period-value-lot", "contract-nature-main", "lot-count", "deadline-receipt-tender-date-lot", "buyer-city", "buyer-country"]:
    r = requests.post("https://api.ted.europa.eu/v3/notices/search", headers=H, timeout=40, json={"query": "buyer-country=ITA AND publication-date>=20261101", "fields": base + [f], "limit": 3, "page": 1, "scope": "ALL", "paginationMode": "PAGE_NUMBER"})
    out[f] = {"status": r.status_code, "sample": (r.json().get("notices", [])[:2] if r.status_code == 200 else r.text[:200])}
json.dump(out, open("docs/data/debug_sonda.json", "w"), ensure_ascii=False)
