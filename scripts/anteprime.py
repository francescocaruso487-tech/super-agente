"""Anteprime degli articoli: per le notizie recenti legge la pagina e ne ricava
descrizione dell'editore, autore, sezione, tag e tempo di lettura.
Non copia il testo degli articoli: solo i dati che l'editore stesso pubblica per le anteprime."""
import html
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
NEWS = ROOT / "docs" / "data" / "news.json"
OUT = ROOT / "docs" / "data" / "anteprime.json"
UA = "Mozilla/5.0 (compatible; RassegnaPersonale/1.0; app personale non commerciale; +https://github.com/francescocaruso487-tech/super-agente)"
GIORNI = 3
MAX_RUN = 140
BUDGET_S = 240


def txt(s, n=420):
    s = re.sub(r"\s+", " ", html.unescape(s or "")).strip()
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def meta(soup, *chiavi):
    for k in chiavi:
        t = soup.find("meta", attrs={"property": k}) or soup.find("meta", attrs={"name": k})
        if t and t.get("content"):
            return t["content"].strip()
    return None


def leggi(item):
    url = item["link"]
    host = urlparse(url).netloc.lower()
    if "google." in host or url.lower().endswith(".pdf"):
        return item["id"], {"x": 1}
    try:
        r = requests.get(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"}, timeout=9)
        if r.status_code != 200 or "html" not in r.headers.get("content-type", "").lower():
            return item["id"], {"x": 1}
        soup = BeautifulSoup(r.content[:900_000], "html.parser")
    except Exception:  # noqa: BLE001
        return item["id"], {"x": 1}
    out = {}
    d = txt(meta(soup, "og:description", "description", "twitter:description") or "", 600)
    if len(d) < 160:
        # descrizione corta: aggiungo l'attacco dell'articolo (primo paragrafo, breve)
        box0 = soup.find("article") or soup
        for p_ in box0.find_all("p"):
            t_ = p_.get_text(" ", strip=True)
            if len(t_) >= 120 and t_[:40] not in d:
                d = txt((d + " " + t_).strip(), 520)
                break
    if len(d) >= 50:
        out["desc"] = d
    im = meta(soup, "og:image", "twitter:image", "og:image:url")
    if im:
        im = urljoin(url, im.strip())
        if im.startswith("https://") and len(im) < 500 and not re.search(r"logo|favicon|placeholder|default", im, re.I):
            out["img"] = im
    a = meta(soup, "author", "article:author", "twitter:creator")
    if not a:
        ra = soup.find(attrs={"rel": "author"})
        a = ra.get_text(" ", strip=True) if ra else None
    if a and not a.startswith("http") and 3 <= len(a) <= 60 and "@" not in a:
        out["autore"] = txt(a, 60)
    sez = meta(soup, "article:section")
    if sez and len(sez) <= 40:
        out["sezione"] = txt(sez, 40)
    tags = [t["content"].strip() for t in soup.find_all("meta", attrs={"property": "article:tag"}) if t.get("content")]
    if not tags:
        kw = meta(soup, "keywords", "news_keywords") or ""
        tags = [k.strip() for k in kw.split(",")]
    tags = [t for t in dict.fromkeys(tags) if 2 < len(t) <= 28][:5]
    if tags:
        out["tag"] = tags
    box = soup.find("article") or soup
    parole = sum(len(p.get_text(" ", strip=True).split()) for p in box.find_all("p") if len(p.get_text(strip=True)) > 60)
    if parole >= 120:
        out["parole"] = parole
    out["v"] = 2
    return item["id"], out if len(out) > 1 else {"x": 1}


def main():
    news = json.loads(NEWS.read_text(encoding="utf-8"))["notizie"]
    try:
        cache = json.loads(OUT.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        cache = {}
    ids = {n["id"] for n in news}
    cache = {k: v for k, v in cache.items() if k in ids}
    limite = (datetime.now(timezone.utc) - timedelta(days=GIORNI)).strftime("%Y-%m-%dT%H:%M:%SZ")
    quando = lambda n: n.get("pubblicata") or n["visto"]  # noqa: E731
    cand = [n for n in news if (n["id"] not in cache or (cache[n["id"]].get("v") != 2 and "x" not in cache[n["id"]])) and quando(n) >= limite]
    # prima le notizie professionali e politiche, poi il resto; dentro ogni gruppo le piu' recenti
    cand.sort(key=lambda n: quando(n), reverse=True)
    cand.sort(key=lambda n: n.get("nicchia") not in ("edilizia", "tech", "politica"))
    cand = cand[:MAX_RUN]
    t0 = time.time()
    fatti = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i, v in pool.map(leggi, cand):
            cache[i] = v
            fatti += 1
    ok = sum(1 for v in cache.values() if "x" not in v)
    print(f"anteprime: lette {fatti} in {time.time() - t0:.0f}s; in cache {len(cache)} ({ok} con dati)")
    OUT.write_text(json.dumps(cache, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


if __name__ == "__main__":
    sys.exit(main())
