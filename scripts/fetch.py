#!/usr/bin/env python3
"""Super Agente - raccolta novita' (edilizia/ingegneria).

Ogni esecuzione:
  1. legge tutte le fonti di sources.json (RSS, con ricerca automatica del feed,
     e scraping di riserva);
  2. assegna ogni notizia a un'area con filtri a parole chiave (gratis);
  3. salva docs/data/news.json e docs/data/status.json (stato di ogni fonte);
  4. manda le notifiche push via ntfy.sh (se NTFY_TOPIC e' impostato).

Con --digest invia invece il riepilogo del mattino.
Costo IA: zero, salvo ANTHROPIC_API_KEY impostata (allora riassume solo le
novita' normative, massimo AI_MAX_PER_RUN per esecuzione).
"""
import argparse
import hashlib
import html
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode, quote_plus

import feedparser
import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
UA = "Mozilla/5.0 (compatible; SuperAgenteBot/1.0; uso personale)"
TIMEOUT = 20
RETENTION_DAYS = 60
MAX_ITEMS = 6000
MAX_AGE_NEW_DAYS = 30        # alla prima lettura ignora notizie piu' vecchie di cosi'
PUSH_NICCHIE = {"edilizia", "tech"}   # politica e auto: solo riepilogo del mattino
MAX_PUSH_SINGLE = 6          # oltre, un solo messaggio riassuntivo
AI_MAX_PER_RUN = int(os.environ.get("AI_MAX_PER_RUN", "15"))
FEED_GUESSES = ["feed/", "feed", "rss", "rss.xml", "feed.rss", "index.xml", "atom.xml"]
TRACKING = {"utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "fbclid", "gclid", "mc_cid", "mc_eid"}


# ---------------------------------------------------------------- utilita'
def now_utc():
    return datetime.now(timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def save_json(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(obj, ensure_ascii=False, indent=1), encoding="utf-8")


def clean(text):
    if not text:
        return ""
    text = BeautifulSoup(str(text), "lxml").get_text(" ")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def short(text, n=170):
    text = clean(text)
    if len(text) <= n:
        return text
    cut = text[:n]
    m = max(cut.rfind(". "), cut.rfind("; "))
    if m > n * 0.5:
        return cut[: m + 1]
    return cut[: cut.rfind(" ")].rstrip(",;:-") + "…"


def norm_url(url):
    p = urlparse(url.strip())
    q = [(k, v) for k, v in parse_qsl(p.query) if k.lower() not in TRACKING]
    path = p.path.rstrip("/") or "/"
    return urlunparse((p.scheme.lower(), p.netloc.lower(), path, "", urlencode(q), ""))


def item_id(url):
    return hashlib.sha1(norm_url(url).encode()).hexdigest()[:16]


def get(url):
    r = requests.get(url, headers={"User-Agent": UA, "Accept": "*/*"}, timeout=TIMEOUT, allow_redirects=True)
    r.raise_for_status()
    return r


# ---------------------------------------------------------------- lettura fonti
def parse_feed(content, base):
    fp = feedparser.parse(content)
    items = []
    for e in fp.entries:
        link = e.get("link")
        title = clean(e.get("title"))
        if not link or not title:
            continue
        dt = e.get("published_parsed") or e.get("updated_parsed")
        pub = iso(datetime(*dt[:6], tzinfo=timezone.utc)) if dt else None
        summ = e.get("summary") or e.get("description") or ""
        if not summ and e.get("content"):
            summ = e["content"][0].get("value", "")
        items.append({"titolo": title, "link": urljoin(base, link), "pubblicata": pub, "sintesi": short(summ)})
    return items


def discover_feeds(page_html, base):
    soup = BeautifulSoup(page_html, "lxml")
    found = []
    for l in soup.find_all("link", rel=lambda v: v and "alternate" in v):
        t = (l.get("type") or "").lower()
        if "rss" in t or "atom" in t:
            found.append(urljoin(base, l.get("href", "")))
    for guess in FEED_GUESSES:
        found.append(urljoin(base if base.endswith("/") else base + "/", guess))
    seen, out = set(), []
    for u in found:
        if u and u not in seen:
            seen.add(u)
            out.append(u)
    return out


CHROME_RX = re.compile(r"(^|[\s_-])(menu|navbar|nav|footer|breadcrumb|sidebar|toolbar|cookie|banner)([\s_-]|$)")


def in_chrome(a):
    """True se il link sta in menu, intestazione, piede o barre laterali."""
    for p in a.parents:
        if getattr(p, "name", None) in ("nav", "header", "footer", "aside"):
            return True
        cls = " ".join(p.get("class") or []).lower() + " " + (p.get("id") or "").lower() if hasattr(p, "get") else ""
        if CHROME_RX.search(cls):
            return True
    return False


def quality_ok(title):
    """Un titolo da notizia: abbastanza lungo e con almeno 6 parole (esclude voci di menu)."""
    t = clean(title)
    return len(t) >= 45 and len(t.split()) >= 6


def scrape_links(page_html, base):
    """Riserva: estrae i titoli di notizia dalla pagina, escludendo menu e piedi pagina."""
    soup = BeautifulSoup(page_html, "lxml")
    host = urlparse(base).netloc.replace("www.", "")
    items, seen = [], set()
    for a in soup.find_all("a", href=True):
        txt = clean(a.get_text(" "))
        if len(txt) > 260 or not quality_ok(txt) or in_chrome(a):
            continue
        href = urljoin(base, a["href"])
        p = urlparse(href)
        if p.scheme not in ("http", "https") or host not in p.netloc.replace("www.", ""):
            continue
        if norm_url(href) == norm_url(base) or norm_url(href) in seen:
            continue
        seen.add(norm_url(href))
        items.append({"titolo": txt, "link": href, "pubblicata": None, "sintesi": ""})
    return items[:60]


def try_feed(url):
    r = get(url)
    items = parse_feed(r.content, url)
    return items


def read_direct(src):
    """Lettura diretta: RSS, ricerca del feed, scraping. Ritorna (items, metodo, errore)."""
    errors = []
    tried = set()
    if src.get("feed"):
        tried.add(src["feed"])
        try:
            items = try_feed(src["feed"])
            if items:
                return items, "rss", None
            errors.append("feed vuoto")
        except Exception as ex:  # noqa: BLE001
            errors.append(f"feed: {type(ex).__name__}")
    page = None
    try:
        page = get(src.get("lista") or src["home"])
    except Exception as ex:  # noqa: BLE001
        errors.append(f"pagina: {type(ex).__name__}")
    if page is not None:
        for u in discover_feeds(page.text, page.url)[:8]:
            if u in tried:
                continue
            tried.add(u)
            try:
                items = try_feed(u)
                if items:
                    return items, "rss", None
            except Exception:  # noqa: BLE001
                continue
        items = scrape_links(page.text, page.url)
        if items:
            return items, "scraping", None
        errors.append("nessun elemento trovato")
    return [], "nessuno", "; ".join(errors) or "sconosciuto"



# ---------------------------------------------------------------- Gazzetta Ufficiale (sommari)
GU_ARCHIVE = "https://www.gazzettaufficiale.it/ricercaArchivioCompleto/serie_generale/{year}"
GU_ISSUE_RX = re.compile(r"dataPubblicazioneGazzetta=(\d{4}-\d{2}-\d{2})&numeroGazzetta=(\d+)")


def parse_gu_issue(page_html, base, date):
    """Un sommario di Gazzetta: ogni atto ha due link (tipo+data, descrizione)."""
    soup = BeautifulSoup(page_html, "lxml")
    acts, order = {}, []
    for a in soup.find_all("a", href=True):
        if "caricaDettaglioAtto" not in a["href"]:
            continue
        href, txt = urljoin(base, a["href"]), clean(a.get_text(" "))
        if not txt:
            continue
        if href not in acts:
            acts[href] = []
            order.append(href)
        acts[href].append(txt)
    items = []
    for href in order:
        ts = acts[href]
        desc = re.sub(r"\s*Pag\.\s*\d+\s*$", "", ts[1]).strip() if len(ts) > 1 else ""
        titolo = f"{ts[0]}: {desc}" if desc else ts[0]
        items.append({"titolo": short(titolo, 240), "link": href, "pubblicata": date + "T06:00:00Z", "sintesi": short(desc)})
    return items


def read_gu(n_issues=4):
    """Legge i sommari degli ultimi numeri della Serie Generale (precisa, atto per atto)."""
    template = os.environ.get("GU_ARCHIVE", GU_ARCHIVE)
    year = now_utc().year
    issues = {}
    for y in (year, year - 1):
        try:
            page = get(template.format(year=y))
        except Exception:  # noqa: BLE001
            if y == year:
                raise
            continue
        for a in BeautifulSoup(page.text, "lxml").find_all("a", href=True):
            m = GU_ISSUE_RX.search(a["href"])
            if m:
                issues[(m.group(1), int(m.group(2)))] = urljoin(page.url, a["href"])
        if len(issues) >= n_issues:
            break
    if not issues:
        raise RuntimeError("nessun numero trovato nell'archivio")
    items = []
    for key in sorted(issues)[-n_issues:]:
        try:
            p = get(issues[key])
        except Exception:  # noqa: BLE001
            continue
        items += parse_gu_issue(p.text, p.url, key[0])
    return items


# ---------------------------------------------------------------- riserva indiretta (Google News)
def read_gnews(query, when="14d"):
    """Per i siti che bloccano i lettori automatici: titoli indicizzati da Google News."""
    base = os.environ.get("GNEWS_BASE", "https://news.google.com/rss/search")
    url = f"{base}?q={quote_plus(query + ' when:' + when)}&hl=it&gl=IT&ceid=IT:it"
    items = try_feed(url)
    for it in items:
        m = re.match(r"^(.*\S)\s+-\s+([^-]{2,45})$", it["titolo"])
        if m:
            it["titolo"] = m.group(1)
    return items


def read_source(src):
    """Ritorna (items, metodo, errore). Ordine: gestore dedicato -> lettura diretta -> riserva Google News."""
    errors = []
    if src.get("handler") == "gu":
        try:
            items = read_gu()
            if items:
                return items, "ufficiale", None
            errors.append("sommari vuoti")
        except Exception as ex:  # noqa: BLE001
            errors.append(f"gazzetta: {type(ex).__name__}")
    else:
        items, metodo, err = read_direct(src)
        if items:
            return items, metodo, None
        errors.append(err)
    if src.get("gnews"):
        try:
            queries = src["gnews"] if isinstance(src["gnews"], list) else [src["gnews"]]
            items, seen = [], set()
            for q in queries:
                try:
                    for it in read_gnews(q, src.get("gnews_when", "14d")):
                        if it["link"] not in seen:
                            seen.add(it["link"])
                            items.append(it)
                except Exception:  # noqa: BLE001
                    continue
            if items:
                return items, "gnews", None
            errors.append("riserva vuota")
        except Exception as ex:  # noqa: BLE001
            errors.append(f"riserva: {type(ex).__name__}")
    return [], "nessuno", "; ".join(e for e in errors if e) or "sconosciuto"


# ---------------------------------------------------------------- classificazione
TASSONOMIA = "11"  # cambia questo valore per far riclassificare l'archivio


def _rx(kw):
    k = kw.lower()
    trail = k.endswith(" ") or len(k.strip()) <= 4
    body = re.escape(k.strip())
    return re.compile(r"(?<!\w)" + body + (r"(?!\w)" if trail else ""))


def build_matchers(aree_cfg):
    """Ritorna (matchers per area, matchers per sottosezione, urgenti, luoghi)."""
    area_rx, sotto_rx = {}, {}
    for a, v in aree_cfg["aree"].items():
        rxs = []
        for sid, sv in v.get("sotto", {}).items():
            lst = [_rx(k) for k in sv["parole"]]
            sotto_rx[f"{a}.{sid}"] = lst
            rxs += lst
        rxs += [_rx(k) for k in v.get("parole", [])]
        area_rx[a] = rxs
    luoghi = {n: [_rx(k) for k in kws] for n, kws in aree_cfg.get("luoghi", {}).items()}
    return area_rx, sotto_rx, [_rx(k) for k in aree_cfg["urgenti"]], luoghi


_EN = set("the of to and is for on with as at by after from its his her says how why what about will over into are be has have this that not more than new could would who when your you their they was were been but or an it us up out amid ahead against".split())
_IT = set("il lo la le gli i di del della dei delle degli da con per su un una uno e che non si è al alla alle ai nel nella nei nelle come più sul sulla sui sono dopo anche dal dalla tra fra ha hanno ma o se cosa quando già solo ecco nuovo nuova nuovi nuove contro verso".split())


def is_italiano(titolo, sintesi=""):
    """Scarta le notizie in inglese (o altre lingue): l'app deve essere solo in italiano."""
    words = re.findall(r"[a-zàèéìòù']+", (titolo + " " + sintesi[:200]).lower())
    if len(words) < 3:
        return True
    en = sum(w in _EN for w in words)
    it = sum(w in _IT for w in words)
    if en >= 2 and en > it:
        return False
    if it == 0 and ((en >= 1 and len(words) >= 5) or len(words) >= 8):
        return False
    return True


def classify(item, src, matchers, urgenti, aree_cfg):
    if not is_italiano(item["titolo"], item.get("sintesi", "")):
        return None
    area_rx, sotto_rx, luoghi = matchers
    nicchia = src.get("nicchia", "edilizia")
    text = (item["titolo"] + " " + item.get("sintesi", "")).lower()
    scored = []
    for area, rxs in area_rx.items():
        cfg_a = aree_cfg["aree"].get(area, {})
        if cfg_a.get("nicchia", "edilizia") != nicchia:
            continue
        if cfg_a.get("fonti_riservate") and not src.get(cfg_a["fonti_riservate"]):
            continue   # aree riservate (es. CAF): solo dalle fonti che le seguono
        n = sum(1 for r in rxs if r.search(text))
        if n:
            scored.append((n, area))
    scored.sort(reverse=True)
    aree = [a for _, a in scored[:2]]
    hint = src.get("aree") or []
    if not aree:
        if src.get("filtra"):
            return None
        aree = [hint[0]] if hint else ["altro"]
    elif hint and hint[0] not in aree and not src.get("filtra"):
        aree = aree[:1] + [hint[0]]
    # sottosezioni: la migliore per ciascuna area assegnata
    sotto = []
    for a in aree:
        best = max(((sum(1 for r in rxs if r.search(text)), k) for k, rxs in sotto_rx.items() if k.startswith(a + ".")), default=(0, None))
        if best[0]:
            sotto.append(best[1])
    # luogo: dalla fonte locale oppure da parole chiave (Caserta prevale su Campania)
    luogo = src.get("luogo")
    if not luogo and nicchia == "edilizia":
        for nome in ("Caserta", "Campania"):
            if any(r.search(text) for r in luoghi.get(nome, [])):
                luogo = nome
                break
    norm = (src["tipo"] == "ufficiale" or any(r.search(text) for r in urgenti)) if nicchia == "edilizia" else src["tipo"] == "ufficiale"
    return aree, norm, sotto, luogo


def build_prof(aree_cfg):
    return {k: [_rx(w) for w in v["parole"]] for k, v in aree_cfg.get("professioni", {}).items()}


def profili(item, src, aree, aree_cfg, prof_rx):
    """Professioni toccate da una notizia: parole chiave + fonte + professioni collegate alle aree."""
    if src.get("nicchia", "edilizia") != "edilizia" or not prof_rx:
        return []
    text = (item["titolo"] + " " + item.get("sintesi", "")).lower()
    trovate = [k for k, rxs in prof_rx.items() if any(r.search(text) for r in rxs)]
    tags = list(src.get("prof", [])) + trovate
    for a in aree:
        tags += aree_cfg["aree"].get(a, {}).get("prof", [])
    visti, out = set(), []
    for t in tags:
        if t in prof_rx and t not in visti:
            visti.add(t)
            out.append(t)
    return out[:8]


# ---------------------------------------------------------------- IA (facoltativa)
def ai_summary(item):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    prompt = (
        "Riassumi in italiano, in massimo 25 parole, per un ingegnere edile. "
        "Tono neutro, solo fatti presenti nel testo, niente invenzioni.\n"
        f"Titolo: {item['titolo']}\nTesto: {item.get('sintesi', '')}"
    )
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5"), "max_tokens": 80,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=30,
        )
        r.raise_for_status()
        return clean(r.json()["content"][0]["text"])
    except Exception as ex:  # noqa: BLE001
        print(f"  IA non disponibile: {type(ex).__name__}", file=sys.stderr)
        return None


# ---------------------------------------------------------------- notifiche
def ntfy(payload):
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        return False
    payload = dict(payload, topic=topic)
    try:
        r = requests.post(os.environ.get("NTFY_SERVER", "https://ntfy.sh"), json=payload, timeout=20)
        r.raise_for_status()
        return True
    except Exception as ex:  # noqa: BLE001
        print(f"  ntfy errore: {type(ex).__name__}", file=sys.stderr)
        return False


def app_url():
    if os.environ.get("APP_URL"):
        return os.environ["APP_URL"]
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if "/" in repo:
        owner, name = repo.split("/", 1)
        return f"https://{owner}.github.io/{name}/"
    return None


def notify_new(new_items, aree_cfg):
    alerts = [i for i in new_items if i["normativa"] and i.get("nicchia", "edilizia") in PUSH_NICCHIE]
    if not alerts:
        return 0
    if len(alerts) > MAX_PUSH_SINGLE:
        body = "\n".join(f"• {i['titolo'][:90]}" for i in alerts[:8])
        ntfy({"title": f"{len(alerts)} nuove novità normative", "message": body, "priority": 3,
              "tags": ["rotating_light"], **({"click": app_url()} if app_url() else {})})
        return len(alerts)
    for i in alerts:
        area = aree_cfg["aree"].get(i["aree"][0], {"nome": "Altro"})["nome"]
        msg = i["titolo"] + (f"\n{i['sintesi']}" if i.get("sintesi") else "")
        sigla = {"tech": "📱 "}.get(i.get("nicchia"), "")
        ntfy({"title": f"{sigla}{area} · {i['fonte_nome']}", "message": msg[:700], "click": i["link"],
              "priority": 4 if i["tipo"] == "ufficiale" else 3, "tags": ["rotating_light"] if i["tipo"] == "ufficiale" else ["newspaper"]})
    return len(alerts)


def send_digest(news, aree_cfg, ultimo=None):
    since = now_utc() - timedelta(hours=24)
    if ultimo:
        try:
            since = max(since, parse_iso(ultimo))
        except Exception:  # noqa: BLE001
            pass
    recent = [i for i in news if parse_iso(i["visto"]) >= since]
    etichette = {"edilizia": "Edilizia", "tech": "Tecnologia", "politica": "Politica", "auto": "Motori"}
    totale = 0
    for nic, etichetta in etichette.items():
        rec = [i for i in recent if i.get("nicchia", "edilizia") == nic]
        if not rec:
            ntfy({"title": f"{etichetta} · buongiorno", "message": "Nessuna novità nelle ultime 24 ore.", "priority": 2})
            continue
        lines = []
        for key, cfg in aree_cfg["aree"].items():
            if cfg.get("nicchia", "edilizia") != nic:
                continue
            grp = [i for i in rec if key in i["aree"]]
            grp.sort(key=lambda i: (not i["normativa"], i["visto"]))
            if not grp:
                continue
            lines.append(f"{cfg['nome'].upper()} ({len(grp)})")
            lines += [f"• {i['titolo'][:85]}" for i in grp[:3]]
        msg = "\n".join(lines) or "\n".join(f"• {i['titolo'][:85]}" for i in rec[:8])
        while len(msg.encode()) > 3800:
            msg = msg.rsplit("\n", 1)[0]
        ntfy({"title": f"{etichetta}: {len(rec)} novità nelle ultime 24h", "message": msg, "priority": 3,
              "tags": ["sunrise"], **({"click": app_url()} if app_url() else {})})
        totale += len(rec)
    return totale


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--digest", action="store_true", help="invia il riepilogo del mattino")
    ap.add_argument("--invia-notifiche", action="store_true", help="invia le notifiche in coda (dopo che i dati sono stati salvati)")
    ap.add_argument("--data-dir", default=str(ROOT / "docs" / "data"))
    ap.add_argument("--sources", default=str(ROOT / "sources.json"))
    ap.add_argument("--aree", default=str(ROOT / "aree.json"))
    args = ap.parse_args()

    data = Path(args.data_dir)
    aree_cfg = load_json(args.aree, None)
    news_file, status_file = data / "news.json", data / "status.json"
    news_doc = load_json(news_file, {"notizie": []})
    news = news_doc["notizie"]

    reg_file = data / "notificate.json"
    reg = load_json(reg_file, {"ids": [], "ultimo_riepilogo": None})

    if args.invia_notifiche:
        # Si invia solo cio' che e' gia' salvato nell'archivio e mai notificato prima.
        in_archivio = {i["id"] for i in news}
        gia = set(reg["ids"])
        coda = [i for i in load_json(ROOT / "da_notificare.json", []) if i["id"] in in_archivio and i["id"] not in gia]
        n = notify_new(coda, aree_cfg) if coda else 0
        reg["ids"] = (reg["ids"] + [i["id"] for i in coda])[-5000:]
        save_json(reg_file, reg)
        print(f"Notifiche inviate: {n}")
        return 0

    if args.digest:
        n = send_digest(news, aree_cfg, reg.get("ultimo_riepilogo"))
        reg["ultimo_riepilogo"] = iso(now_utc())
        save_json(reg_file, reg)
        print(f"Digest inviato: {n} notizie")
        return 0

    sources = load_json(args.sources, None)["fonti"]
    area_rx, sotto_rx, urgenti, luoghi = build_matchers(aree_cfg)
    matchers = (area_rx, sotto_rx, luoghi)
    prof_rx = build_prof(aree_cfg)
    prev_status = {s["id"]: s for s in load_json(status_file, {"fonti": []})["fonti"]}
    first_run = not news
    known = {i["id"]: i for i in news}
    ts = now_utc()

    # pulizia una tantum: toglie dall'archivio le voci di menu raccolte da fonti lette con scraping
    for iid, rec in list(known.items()):
        m = rec.get("metodo") or prev_status.get(rec["fonte"], {}).get("metodo")
        if m == "scraping" and (not quality_ok(rec["titolo"]) or rec["aree"] == ["altro"]):
            del known[iid]

    # nuova classificazione dell'archivio quando cambia la tassonomia
    if news_doc.get("tassonomia") != TASSONOMIA:
        by_id = {x["id"]: x for x in sources}
        for iid, rec in list(known.items()):
            src = by_id.get(rec["fonte"])
            if not src:
                continue
            cls = classify({"titolo": rec["titolo"], "sintesi": rec.get("sintesi", "")}, src, matchers, urgenti, aree_cfg)
            if cls is None or (rec.get("metodo") == "scraping" and cls[0] == ["altro"] and not cls[3]):
                del known[iid]
                continue
            rec["aree"], rec["normativa"], rec["sotto"], rec["luogo"] = cls
            rec["nicchia"] = src.get("nicchia", "edilizia")
            rec["prof"] = profili({"titolo": rec["titolo"], "sintesi": rec.get("sintesi", "")}, src, rec["aree"], aree_cfg, prof_rx)
        print(f"Archivio riclassificato (tassonomia {TASSONOMIA}): {len(known)} notizie")

    print(f"Lettura di {len(sources)} fonti…")
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(read_source, sources))

    new_items, statuses = [], []
    for src, (items, metodo, err) in zip(sources, results):
        prev = prev_status.get(src["id"], {})
        added = 0
        for it in items:
            iid = item_id(it["link"])
            if iid in known:
                continue
            if it["pubblicata"] and parse_iso(it["pubblicata"]) < ts - timedelta(days=MAX_AGE_NEW_DAYS):
                continue
            cls = classify(it, src, matchers, urgenti, aree_cfg)
            if cls is None:
                continue
            aree, normativa, sotto, luogo = cls
            if metodo == "scraping" and aree == ["altro"] and not luogo:
                continue
            rec = {"id": iid, "titolo": it["titolo"], "link": it["link"], "fonte": src["id"],
                   "fonte_nome": src["nome"], "tipo": src["tipo"], "aree": aree, "normativa": normativa,
                   "sintesi": it["sintesi"], "pubblicata": it["pubblicata"], "visto": iso(ts), "metodo": metodo,
                   "sotto": sotto, "luogo": luogo, "nicchia": src.get("nicchia", "edilizia"),
                   "prof": profili(it, src, aree, aree_cfg, prof_rx)}
            known[iid] = rec
            new_items.append(rec)
            added += 1
        if err:
            stato = "errore"
        elif not items:
            stato = "vuoto"
        else:
            stato = {"rss": "ok", "ufficiale": "ok", "gnews": "ok_indiretto"}.get(metodo, "ok_scraping")
        statuses.append({
            "id": src["id"], "nome": src["nome"], "tipo": src["tipo"], "home": src["home"],
            "stato": stato, "nicchia": src.get("nicchia", "edilizia"), "metodo": metodo, "letti": len(items), "nuovi": added,
            "ultimo_controllo": iso(ts),
            "ultimo_nuovo": iso(ts) if added else prev.get("ultimo_nuovo"),
            "errore": err, "nota": src.get("nota"),
            "falliti_di_fila": (prev.get("falliti_di_fila", 0) + 1) if stato in ("errore", "vuoto") else 0,
        })
        print(f"  [{stato:11}] {src['nome']}: letti {len(items)}, nuovi {added}" + (f" ({err})" if err else ""))

    # sintesi IA solo per novita' normative (se chiave presente)
    if os.environ.get("ANTHROPIC_API_KEY") and not first_run:
        for it in [i for i in new_items if i["normativa"]][:AI_MAX_PER_RUN]:
            s = ai_summary(it)
            if s:
                it["sintesi"], it["ia"] = s, True

    # conservazione e ordinamento
    limit = ts - timedelta(days=RETENTION_DAYS)
    allnews = [i for i in known.values() if parse_iso(i["pubblicata"] or i["visto"]) >= limit]
    allnews.sort(key=lambda i: i["pubblicata"] or i["visto"], reverse=True)
    allnews = allnews[:MAX_ITEMS]

    aree_pub = {k: {"nome": v["nome"], "colore": v["colore"], "nicchia": v.get("nicchia", "edilizia"), "gruppo": v.get("gruppo"), "sotto": {sk: sv["nome"] for sk, sv in v.get("sotto", {}).items()}}
                for k, v in aree_cfg["aree"].items()}
    aree_pub["locale"] = {"nome": "Locale · Campania e Caserta", "colore": "#c2185b", "sotto": {}, "speciale": True}
    aree_pub["altro"] = {"nome": "Altro", "colore": "#7b8794"}
    save_json(data / "aree.json", aree_pub)
    save_json(data / "professioni.json", {"gruppi": aree_cfg.get("gruppi_professioni", []), "professioni": {k: {"nome": v["nome"], "emoji": v.get("emoji", ""), "gruppo": v.get("gruppo", "")} for k, v in aree_cfg.get("professioni", {}).items()}})
    save_json(news_file, {"aggiornato": iso(ts), "tassonomia": TASSONOMIA, "notizie": allnews})
    ok = sum(1 for s in statuses if s["stato"] in ("ok", "ok_scraping", "ok_indiretto"))
    save_json(status_file, {"aggiornato": iso(ts), "fonti_ok": ok, "fonti_totale": len(statuses), "fonti": statuses})
    print(f"Nuove: {len(new_items)} | totale archivio: {len(allnews)} | fonti attive: {ok}/{len(statuses)}")

    if first_run:
        print("Prima esecuzione: nessuna notifica (per non inviare l'archivio intero).")
    else:
        # niente invio qui: le notifiche partono dopo il salvataggio dei dati (--invia-notifiche)
        # le fonti appena aggiunte non fanno scattare avvisi alla prima lettura (sarebbe un'ondata di vecchie notizie)
        coda = [i for i in new_items if i["normativa"] and i["fonte"] in prev_status]
        save_json(ROOT / "da_notificare.json", coda)
        print(f"Notifiche in coda: {len(coda)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
