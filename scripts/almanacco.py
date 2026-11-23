#!/usr/bin/env python3
"""Rassegna - Almanacco del giorno (oggi + prossimi 7 giorni) -> docs/data/almanacco.json

Fonti:
- Santo del giorno: Vatican News (fonte ufficiale della Santa Sede)
- Sole e Luna: calcolo astronomico per Caserta (libreria ephem), nessuna fonte esterna
- Festività, feste mobili, ora legale: calcolate dalle regole di legge (nessuna fonte esterna)
- Costituzione: Normattiva (Poligrafico dello Stato) -> docs/data/costituzione.json
- Accadde oggi / Nati / Morti / Ricorrenze: Wikipedia e Wikidata (NON istituzionali, dichiarato nell'app)
"""
import html
import json
import re
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

try:
    import ephem
except ImportError:
    ephem = None

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
TZ = ZoneInfo("Europe/Rome")
H = {"User-Agent": "RassegnaPersonale/1.0 (app personale non commerciale; https://github.com/francescocaruso487-tech/super-agente) python-requests", "Accept-Language": "it"}
GIORNI = 8
MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"]
GIORNO = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]

STAGIONE = {  # calendario indicativo della stagionalità in Italia (frutta, verdura)
    1: (["arance", "clementine", "mandarini", "kiwi", "mele", "pere", "pompelmo", "limoni"], ["broccoli", "carciofi", "cavolfiore", "cavolo", "cicoria", "finocchi", "radicchio", "spinaci", "verza", "zucca"]),
    2: (["arance", "clementine", "kiwi", "mele", "pere", "pompelmo", "limoni"], ["broccoli", "carciofi", "cavolfiore", "cicoria", "finocchi", "radicchio", "spinaci", "verza", "bietole"]),
    3: (["arance", "kiwi", "mele", "pere", "limoni", "pompelmo"], ["asparagi", "carciofi", "cavolfiore", "cicoria", "finocchi", "piselli", "radicchio", "spinaci", "bietole"]),
    4: (["arance", "fragole", "kiwi", "mele", "nespole"], ["asparagi", "carciofi", "fave", "lattuga", "piselli", "radicchio", "rucola", "spinaci"]),
    5: (["albicocche", "ciliegie", "fragole", "nespole", "pesche"], ["asparagi", "carciofi", "cetrioli", "fagiolini", "fave", "lattuga", "piselli", "zucchine"]),
    6: (["albicocche", "ciliegie", "fragole", "lamponi", "meloni", "pesche", "susine"], ["cetrioli", "fagiolini", "melanzane", "peperoni", "pomodori", "zucchine", "rucola"]),
    7: (["albicocche", "anguria", "fichi", "meloni", "pesche", "prugne", "susine"], ["cetrioli", "fagiolini", "melanzane", "peperoni", "pomodori", "zucchine"]),
    8: (["anguria", "fichi", "meloni", "pesche", "pere", "susine", "uva"], ["cetrioli", "fagiolini", "melanzane", "peperoni", "pomodori", "zucchine"]),
    9: (["fichi", "mele", "pere", "prugne", "uva", "melograno"], ["fagiolini", "funghi", "melanzane", "peperoni", "pomodori", "zucca", "cavolfiore"]),
    10: (["castagne", "cachi", "mele", "pere", "uva", "melograno", "kiwi"], ["broccoli", "cavolfiore", "funghi", "radicchio", "spinaci", "zucca", "finocchi"]),
    11: (["arance", "castagne", "cachi", "kiwi", "mele", "pere", "melograno", "clementine"], ["broccoli", "carciofi", "cavolfiore", "cavolo", "finocchi", "radicchio", "spinaci", "zucca", "verza"]),
    12: (["arance", "clementine", "kiwi", "mandarini", "mele", "pere", "pompelmo", "limoni"], ["broccoli", "carciofi", "cavolfiore", "cavolo", "cicoria", "finocchi", "radicchio", "verza", "zucca"]),
}
NOME_MESE = {
    1: "Gennaio deriva da Ianuarius, il mese dedicato a Giano, dio romano delle porte e degli inizi.",
    2: "Febbraio deriva da februa, le feste di purificazione dell'antica Roma celebrate in questo mese.",
    3: "Marzo deriva da Martius, il mese dedicato a Marte, dio romano della guerra. Era il primo mese dell'antico calendario romano.",
    4: "Aprile deriva probabilmente dal latino aperire (aprire), perché in questo mese la natura si schiude.",
    5: "Maggio deriva da Maius, il mese legato alla dea Maia, divinità della crescita.",
    6: "Giugno deriva da Iunius, il mese dedicato a Giunone, regina degli dèi romani.",
    7: "Luglio prende il nome da Giulio Cesare (Iulius), che nacque in questo mese; prima si chiamava Quintilis, il quinto.",
    8: "Agosto prende il nome dall'imperatore Augusto; prima si chiamava Sextilis, il sesto mese.",
    9: "Settembre deriva da septem (sette): era il settimo mese del calendario romano, che iniziava a marzo.",
    10: "Ottobre deriva da octo (otto): era l'ottavo mese del calendario romano.",
    11: "Novembre deriva da novem (nove): era il nono mese del calendario romano.",
    12: "Dicembre deriva da decem (dieci): era il decimo e ultimo mese del calendario romano.",
}
SPORT = re.compile(r"\b(rugby|calcio|campionat|olimpi|coppa|gran premio|formula 1|giro d'italia|tour de france|tennis|ciclismo|maratona|nba|nfl|scudetto|record|medaglia|atleta|squadra|pallavolo|basket|pallacanestro|boxe|pugilato|nuoto)\w*", re.I)


def pasqua(a):
    A, B, C = a % 19, a // 100, a % 100
    D, E = B // 4, B % 4
    F = (B + 8) // 25
    G = (B - F + 1) // 3
    Hh = (19 * A + B - D - G + 15) % 30
    I, K = C // 4, C % 4
    L = (32 + 2 * E + 2 * I - Hh - K) % 7
    M = (A + 11 * Hh + 22 * L) // 451
    mese = (Hh + L - 7 * M + 114) // 31
    giorno = ((Hh + L - 7 * M + 114) % 31) + 1
    return date(a, mese, giorno)


def ultima_domenica(a, m):
    d = date(a, m, 31)
    while d.weekday() != 6:
        d -= timedelta(days=1)
    return d


def festivita(a):
    p = pasqua(a)
    f = {
        date(a, 1, 1): ("Capodanno", "festa"), date(a, 1, 6): ("Epifania", "festa"), p: ("Pasqua", "festa"),
        p + timedelta(days=1): ("Lunedì dell'Angelo (Pasquetta)", "festa"), date(a, 4, 25): ("Festa della Liberazione", "festa"),
        date(a, 5, 1): ("Festa dei Lavoratori", "festa"), date(a, 6, 2): ("Festa della Repubblica", "festa"),
        date(a, 8, 15): ("Assunzione di Maria (Ferragosto)", "festa"), date(a, 11, 1): ("Ognissanti", "festa"),
        date(a, 12, 8): ("Immacolata Concezione", "festa"), date(a, 12, 25): ("Natale", "festa"), date(a, 12, 26): ("Santo Stefano", "festa"),
        p - timedelta(days=47): ("Martedì grasso (Carnevale)", "mobile"), p - timedelta(days=46): ("Mercoledì delle Ceneri, inizio della Quaresima", "mobile"),
        p - timedelta(days=7): ("Domenica delle Palme", "mobile"), p - timedelta(days=2): ("Venerdì Santo", "mobile"),
        p + timedelta(days=39): ("Ascensione", "mobile"), p + timedelta(days=49): ("Pentecoste", "mobile"),
        ultima_domenica(a, 3): ("Inizia l'ora legale: le lancette avanzano di un'ora (alle 2 diventano le 3)", "ora"),
        ultima_domenica(a, 10): ("Finisce l'ora legale: le lancette tornano indietro di un'ora (alle 3 diventano le 2)", "ora"),
    }
    # prima domenica di Avvento: la domenica più vicina al 30 novembre
    n = date(a, 11, 30)
    off = (n.weekday() + 1) % 7
    avv = n - timedelta(days=off) if off <= 3 else n + timedelta(days=7 - off)
    f[avv] = ("Prima domenica di Avvento", "mobile")
    return f


def hhmm(dt):
    return dt.astimezone(TZ).strftime("%H:%M") if dt else None


def astro(d):
    if not ephem:
        return None
    o = ephem.Observer()
    o.lat, o.lon, o.elevation, o.pressure = "41.0732", "14.3320", 68, 0
    inizio = datetime(d.year, d.month, d.day, 0, 0, tzinfo=TZ).astimezone(timezone.utc)
    fine = inizio + timedelta(days=1)
    out = {}

    def evento(corpo, orizz, funz):
        o.horizon = orizz
        o.date = ephem.Date(inizio.replace(tzinfo=None))
        try:
            t = getattr(o, funz)(corpo).datetime().replace(tzinfo=timezone.utc)
            return t if inizio <= t < fine else None
        except Exception:
            return None

    sole, luna = ephem.Sun(), ephem.Moon()
    alba, tram = evento(sole, "-0:34", "next_rising"), evento(sole, "-0:34", "next_setting")
    out["alba"], out["tramonto"] = hhmm(alba), hhmm(tram)
    if alba and tram:
        m = int((tram - alba).total_seconds() // 60)
        out["durata"] = f"{m // 60} ore e {m % 60} minuti"
    out["sorge_luna"], out["tramonta_luna"] = hhmm(evento(luna, "0", "next_rising")), hhmm(evento(luna, "0", "next_setting"))
    mezzo = ephem.Date((inizio + timedelta(hours=12)).replace(tzinfo=None))
    luna.compute(mezzo)
    eta = float(mezzo - ephem.previous_new_moon(mezzo))
    nomi = [(1.84, "Luna nuova"), (5.53, "Luna crescente (falce)"), (9.22, "Primo quarto"), (12.91, "Gibbosa crescente"), (16.61, "Luna piena"), (20.30, "Gibbosa calante"), (23.99, "Ultimo quarto"), (27.68, "Luna calante (falce)")]
    out["fase"] = next((n for lim, n in nomi if eta < lim), "Luna nuova")
    if out["fase"] == "Luna piena" and luna.phase < 97:
        out["fase"] = "Gibbosa crescente (quasi piena)" if eta < 14.77 else "Gibbosa calante (appena passata la piena)"
    out["illuminazione"] = round(luna.phase)
    out["eta_giorni"] = round(eta, 1)
    return out


_ULTIMA = [0.0]


def get(url, **kw):
    import time
    for tent in range(6):
        att = 0.9 - (time.time() - _ULTIMA[0])
        if att > 0:
            time.sleep(att)
        _ULTIMA[0] = time.time()
        r = requests.get(url, headers=H, timeout=40, **kw)
        if r.status_code in (429, 500, 502, 503, 504):
            try:
                w = float(r.headers.get("Retry-After", 0))
            except ValueError:
                w = 0
            time.sleep(min(max(w, 4 * 2 ** tent), 60))
            continue
        r.raise_for_status()
        return r
    r.raise_for_status()
    return r


def santo(d):
    t = get(f"https://www.vaticannews.va/it/santo-del-giorno/{d.month:02d}/{d.day:02d}.html").content.decode("utf-8", "replace")
    out = []
    for sez in re.findall(r'<section class="section section--evidence section--isStatic">(.*?)</section>', t, re.S):
        h = re.search(r"<h2>\s*(.*?)\s*</h2>", sez, re.S)
        p = re.search(r"<p[^>]*>(.*?)</p>", sez, re.S)
        a = re.search(r'href="(/it/santo-del-giorno/[^"]+)"', sez)
        if h:
            txt = re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", p.group(1) if p else ""))).strip()
            out.append({"nome": html.unescape(re.sub(r"<[^>]+>", "", h.group(1))).strip(), "testo": txt, "link": "https://www.vaticannews.va" + a.group(1) if a else None})
    return out


def pulisci(x):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", x or ""))).strip()


def wiki_it(d):
    """Eventi e ricorrenze dalla pagina italiana del giorno; accadde oggi dal feed."""
    j = get(f"https://it.wikipedia.org/api/rest_v1/feed/onthisday/all/{d.month:02d}/{d.day:02d}").json()
    ev, visti = [], set()
    for k in ("selected", "events"):
        for e in j.get(k, []):
            t = pulisci(e.get("text"))
            if t and t not in visti and e.get("year") is not None:
                visti.add(t)
                ev.append({"anno": e["year"], "testo": t})
    ev.sort(key=lambda x: x["anno"])
    t = get(f"https://it.wikipedia.org/api/rest_v1/page/html/{d.day if d.day > 1 else '1%C2%BA'}_{MESI[d.month - 1]}").content.decode("utf-8", "replace")
    ric = []
    for sez in re.split(r"<h2 ", t)[1:]:
        if re.search(r">\s*Feste e ricorrenze", sez[:200]):
            for li in re.findall(r"<li[^>]*>(.*?)</li>", sez, re.S):
                x = pulisci(li)
                if x and len(x) < 200:
                    ric.append(x)
    return ev, ric


def wiki_en_persone(d, chiave):
    j = get(f"https://api.wikimedia.org/feed/v1/wikipedia/en/onthisday/{chiave}/{d.month:02d}/{d.day:02d}").json()
    voci = []
    for e in j.get(chiave, []):
        q = next((p.get("wikibase_item") for p in e.get("pages", []) if p.get("wikibase_item")), None)
        if q and e.get("year") is not None:
            voci.append((e["year"], q))
    return voci


def wikidata_it(qs):
    out = {}
    qs = list(dict.fromkeys(qs))
    for i in range(0, len(qs), 50):
        r = get("https://www.wikidata.org/w/api.php", params={"action": "wbgetentities", "ids": "|".join(qs[i:i + 50]), "props": "labels|descriptions", "languages": "it", "format": "json"}).json()
        for q, e in r.get("entities", {}).items():
            n = e.get("labels", {}).get("it", {}).get("value")
            if n:
                out[q] = (n, e.get("descriptions", {}).get("it", {}).get("value", ""))
    return out


# ---------------------------------------------------------------- cultura (Wikiquote / Wikizionario / Wikipedia)
import hashlib

CACHE = DATA / "cultura_cache.json"


def pick(chiave, n):
    return int(hashlib.md5(chiave.encode()).hexdigest(), 16) % max(n, 1)


def frasi_archivio():
    """Citazioni del giorno dall'archivio di Wikiquote: {(giorno, mese): (testo, autore)}."""
    t = get("https://it.wikiquote.org/api/rest_v1/page/html/Wikiquote:Archivio_delle_citazioni_del_giorno").content.decode("utf-8", "replace")
    T = pulisci(re.sub(r"<(script|style).*?</\1>", " ", t, flags=re.S))
    out = {}
    rx = re.compile(r"(\d{1,2})º? (" + "|".join(MESI) + r") : (.+?) \( ([^()]{3,80}?) \)(?= \d{1,2}º? (?:" + "|".join(MESI) + r") :|$)")
    for m in rx.finditer(T):
        out[(int(m.group(1)), MESI.index(m.group(2)) + 1)] = (m.group(3).strip(), m.group(4).strip())
    return out


def frase_oggi_home():
    t = get("https://it.wikiquote.org/api/rest_v1/page/html/Pagina_principale").content.decode("utf-8", "replace")
    i = t.find("Citazione del giorno</div>")
    seg = t[i:i + 3500]
    q = re.search(r"<i>(.*?)</i>", seg, re.S)
    a = re.search(r'<b><a rel="mw:WikiLink" href="\./([^"]+)"[^>]*>([^<]+)</a></b>', seg)
    if q and a:
        return pulisci(q.group(1)), pulisci(a.group(2))
    return None


def parola_del_giorno():
    t = get("https://it.wiktionary.org/api/rest_v1/page/html/Pagina_principale").content.decode("utf-8", "replace")
    i = t.find("Wikizionario:Parola_del_giorno")
    if i < 0:
        return None
    chunk = t[i:i + 14000]
    parola = None
    for m in re.finditer(r"<b[^>]*>(.*?)</b>", chunk, re.S):
        w = pulisci(m.group(1))
        if w and len(w.split()) <= 3 and re.fullmatch(r"[A-Za-zÀ-ÿ'’\- ]{2,40}", w):
            parola, pos = w, m.start()
            break
    if not parola:
        return None
    testo = pulisci(chunk[pos:pos + 5000])
    testo = re.sub(r"\s*(Sei appena arrivato|Comunità).*$", "", testo)
    if len(testo) > 480:
        testo = testo[:480].rsplit(" ", 1)[0] + "…"
    return {"parola": parola, "testo": testo, "link": "https://it.wiktionary.org/wiki/" + parola.replace(" ", "_")}


def modi_di_dire():
    for cat in ("Locuzioni_verbali_in_italiano", "Locuzioni_nominali_in_italiano", "Espressioni_familiari-IT"):
        voci, cont = [], {}
        for _ in range(8):
            r = get("https://it.wiktionary.org/w/api.php", params={"action": "query", "list": "categorymembers", "cmtitle": "Categoria:" + cat, "cmlimit": 500, "cmnamespace": 0, "format": "json", **cont}).json()
            voci += [x["title"] for x in r.get("query", {}).get("categorymembers", [])]
            if "continue" not in r:
                break
            cont = r["continue"]
        voci = [v for v in voci if " " in v]
        if len(voci) > 50:
            return sorted(voci)
    return []


def significato_modo(titolo):
    t = get("https://it.wiktionary.org/api/rest_v1/page/html/" + requests.utils.quote(titolo.replace(" ", "_"))).content.decode("utf-8", "replace")
    ol = re.search(r"<ol[^>]*>(.*?)</ol>", t, re.S)
    if not ol:
        return None
    defs = []
    for li in re.findall(r"<li[^>]*>(.*?)</li>", ol.group(1), re.S):
        li = re.sub(r"<ul.*?</ul>|<dl.*?</dl>|<ol.*?</ol>", " ", li, flags=re.S)
        x = pulisci(li)
        if x:
            defs.append(x[:260])
    return defs[:3] or None


def comuni_lista():
    q = ('SELECT ?c ?title WHERE { ?c wdt:P31 wd:Q747074; wdt:P17 wd:Q38. ?a schema:about ?c; schema:isPartOf <https://it.wikipedia.org/>; schema:name ?title }')
    b = get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"}).json()["results"]["bindings"]
    return sorted({x["title"]["value"] for x in b})


def comune_info(titolo):
    j = get("https://it.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(titolo.replace(" ", "_"), safe="")).json()
    ex = pulisci(j.get("extract", ""))
    if len(ex) < 60 or j.get("type") == "disambiguation":
        return None
    frasi = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ý])", ex)
    testo = ""
    for f in frasi:
        if len(testo) + len(f) > 700 and testo:
            break
        testo += (" " if testo else "") + f
    return {"nome": j.get("title", titolo), "descr": j.get("description", ""), "testo": testo, "link": (j.get("content_urls", {}).get("desktop", {}) or {}).get("page")}


def latini():
    """Proverbi latini con traduzione italiana da Wikiquote: [{latino, traduzione, autore}]."""
    t = get("https://it.wikiquote.org/api/rest_v1/page/html/Proverbi_latini").content.decode("utf-8", "replace")
    t = re.sub(r"<sup[^>]*>.*?</sup>", "", t, flags=re.S)
    voci = []
    for m in re.finditer(r"<ul[^>]*>\s*<li[^>]*>\s*<i[^>]*>\s*<b[^>]*>(.*?)</b>\s*</i>(.*?)</li>\s*</ul>\s*<dl[^>]*>(.*?)</dl>", t, re.S):
        lat = pulisci(m.group(1)).strip(" .")
        dds = [pulisci(x) for x in re.findall(r"<dd[^>]*>(.*?)</dd>", m.group(3), re.S)]
        dds = [x for x in dds if x]
        if not dds:
            continue
        tr = dds[0].strip(" ,;:-–")
        aut = None
        for x in dds[1:]:
            a2 = re.fullmatch(r"\(\s*(.{3,70}?)\s*\)\.?", x)
            if a2:
                aut = a2.group(1)
                break
        a3 = re.search(r"\(\s*([^()]{3,60}?)\s*\)\s*$", tr)
        if a3 and not aut:
            aut, tr = a3.group(1), tr[:a3.start()].strip(" .,;:-–")
        if not (2 <= len(lat.split()) <= 18) or re.search(r"\d", lat):
            continue
        if not (10 <= len(tr) <= 260) or not tr[0].isupper():
            continue
        voci.append({"latino": lat + ".", "traduzione": tr + ("" if tr[-1] in ".!?" else "."), "autore": aut})
    if len(voci) < 50:
        raise RuntimeError(f"proverbi latini letti: {len(voci)}")
    return voci


def parole_latine():
    voci = []
    for cat, tipo in (("Sostantivi_in_latino", "sostantivo"), ("Verbi_in_latino", "verbo"), ("Aggettivi_in_latino", "aggettivo")):
        cont = {}
        for _ in range(10):
            r = get("https://it.wiktionary.org/w/api.php", params={"action": "query", "list": "categorymembers", "cmtitle": "Categoria:" + cat, "cmlimit": 500, "cmnamespace": 0, "cmtype": "page", "format": "json", **cont}).json()
            voci += [(x["title"], tipo) for x in r.get("query", {}).get("categorymembers", [])]
            if "continue" not in r:
                break
            cont = r["continue"]
    voci = [v for v in voci if re.fullmatch(r"[a-z]{4,12}", v[0])]
    if len(voci) < 200:
        raise RuntimeError("poche parole latine")
    return sorted(set(voci))


def _senza_accenti(x):
    import unicodedata
    return "".join(ch for ch in unicodedata.normalize("NFD", x.lower()) if not unicodedata.combining(ch))


def parola_latina(titolo, tipo):
    t = get("https://it.wiktionary.org/api/rest_v1/page/html/" + requests.utils.quote(titolo)).content.decode("utf-8", "replace")
    i = t.find('id="Latino"')
    if i < 0:
        return None
    sec = t[i:]
    j = re.search(r"<h2", sec[30:])
    sec = sec[: j.start() + 30] if j else sec
    sec = re.sub(r"<style.*?</style>|<img[^>]*>|<sup[^>]*>.*?</sup>", "", sec, flags=re.S)
    ol = re.search(r"<ol[^>]*>(.*?)</ol>", sec, re.S)
    if not ol:
        return None
    defs = []
    for li in re.findall(r"<li[^>]*>(.*?)</li>", ol.group(1), re.S):
        li = re.sub(r"<ul.*?</ul>|<dl.*?</dl>|<ol.*?</ol>", " ", li, flags=re.S)
        x = pulisci(li)
        if x and len(x) < 160:
            defs.append(x)
    if not defs:
        return None

    def blocco(prefisso):
        m = re.search(r'<h[2-4][^>]*id="' + prefisso + r'[^"]*"[^>]*>.*?</h[2-4]>(.*?)(?=<h[2-4]|$)', sec, re.S)
        return pulisci(m.group(1)) if m else ""
    orig = blocco("Etimologia")
    coll = [w for w in re.split(r"[,\s]+", blocco("Parole_derivate")) if re.fullmatch(r"[a-zæœ]{3,20}", w)][:8]
    r = get("https://it.wiktionary.org/w/api.php", params={"action": "query", "list": "search", "srsearch": 'incategory:"Sostantivi in italiano|Verbi in italiano|Aggettivi in italiano" "dal latino ' + titolo + '"',
                                                         "srlimit": 12, "srnamespace": 0, "srprop": "snippet", "format": "json"}).json()
    der = []
    for x in r.get("query", {}).get("search", []):
        if " " in x["title"] or x["title"].lower() == titolo:
            continue
        sn = _senza_accenti(pulisci(x.get("snippet", "")))
        if re.search(r"latino\s+" + re.escape(titolo) + r"\b", sn):
            der.append(x["title"])
    if not der and not coll:
        return None
    return {"latino": titolo, "tipo": tipo, "significati": defs[:3], "origine": orig[:200] if 10 < len(orig) < 400 else None, "derivati": der[:8], "collegati": coll,
            "link": "https://it.wiktionary.org/wiki/" + titolo}


def costituzione(d):
    f = DATA / "costituzione.json"
    if not f.exists():
        return None
    art = json.load(open(f, encoding="utf-8"))["articoli"]
    chiavi = [k for k in art if re.match(r"Art\.\s*\d+", k)] or list(art)
    k = chiavi[(d.timetuple().tm_yday - 1) % len(chiavi)]
    return {"articolo": k, "testo": art[k][:1800], "fonte": "Normattiva"}


def main():
    oggi = datetime.now(TZ).date()
    fest = {**festivita(oggi.year), **festivita(oggi.year + 1)}
    giorni, errori = {}, []
    try:
        cache = json.load(open(CACHE, encoding="utf-8")) if CACHE.exists() else {}
    except Exception:
        cache = {}
    limite = (oggi - timedelta(days=30)).isoformat()
    cache = {k: v for k, v in cache.items() if k >= limite}
    def tenta(fn, nome):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            errori.append(f"{nome}: {str(e)[:60]}")
            return None
    archivio = tenta(frasi_archivio, "archivio frasi") or {}
    modi = tenta(modi_di_dire, "modi di dire") or []
    comuni = tenta(comuni_lista, "comuni") or []
    lat = tenta(latini, "latino") or []
    plat = tenta(parole_latine, "parole latine") or []
    for i in range(GIORNI):
        d = oggi + timedelta(days=i)
        r = {"data": d.isoformat(), "giorno_settimana": GIORNO[d.weekday()], "settimana": d.isocalendar()[1], "giorno_anno": d.timetuple().tm_yday,
             "giorni_alla_fine_anno": (date(d.year, 12, 31) - d).days}
        r["festivita"] = [{"nome": fest[d][0], "tipo": fest[d][1]}] if d in fest else []
        if d.weekday() == 6 and not any(x["tipo"] == "festa" for x in r["festivita"]):
            r["festivita"].append({"nome": "Domenica", "tipo": "domenica"})
        r["astro"] = astro(d)
        r["stagione"] = {"frutta": STAGIONE[d.month][0], "verdura": STAGIONE[d.month][1]}
        r["nome_mese"] = NOME_MESE[d.month]
        r["costituzione"] = costituzione(d)
        iso = d.isoformat()
        c = cache.setdefault(iso, {})
        if not c.get("santi"):
            try:
                c["santi"] = santo(d)
            except Exception as e:  # noqa: BLE001
                errori.append(f"{d} santi: {str(e)[:60]}")
        r["santi"] = c.get("santi") or []
        if not c.get("accadde"):
            try:
                ev, ric = wiki_it(d)
                c["accadde"], c["ricorrenze"] = ev, ric
                c["sport"] = [e for e in ev if SPORT.search(e["testo"])]
            except Exception as e:  # noqa: BLE001
                errori.append(f"{d} wiki: {str(e)[:60]}")
        visti_ev, ev_ok = set(), []
        for e in c.get("accadde") or []:
            chiave = (e["anno"], re.sub(r"[^a-zà-ÿ0-9]", "", e["testo"].lower())[:45])
            if chiave not in visti_ev:
                visti_ev.add(chiave)
                ev_ok.append(e)
        c["accadde"] = ev_ok
        c["sport"] = [e for e in ev_ok if SPORT.search(e["testo"])]
        r["accadde"], r["sport"], r["ricorrenze"] = c["accadde"], c["sport"], c.get("ricorrenze") or []
        for chiave, nome in (("births", "nati"), ("deaths", "morti")):
            if not c.get(nome):
                try:
                    voci = wiki_en_persone(d, chiave)
                    lab = wikidata_it([q for _, q in voci])
                    lista = [{"anno": a, "nome": lab[q][0], "descr": lab[q][1]} for a, q in voci if q in lab and not re.fullmatch(r"[\d\s]+", lab[q][0]) and lab[q][1] not in ("anno", "")]
                    lista.sort(key=lambda x: x["anno"])
                    c[nome] = lista[:60]
                except Exception as e:  # noqa: BLE001
                    errori.append(f"{d} {nome}: {str(e)[:60]}")
            r[nome] = c.get(nome) or []
        # cultura: frase, parola, modo di dire, comune
        if "frase" not in c:
            try:
                fr = archivio.get((d.day, d.month)) if archivio else None
                if not fr and i == 0:
                    fr = frase_oggi_home()
                if fr:
                    c["frase"] = {"testo": fr[0], "autore": fr[1]}
            except Exception as e:  # noqa: BLE001
                errori.append(f"{d} frase: {str(e)[:60]}")
        if c.get("parola") and (c["parola"].get("testo", "").startswith("class=") or len(c["parola"].get("testo", "")) < 20):
            del c["parola"]
        if "parola" not in c and i == 0:
            try:
                pdg = parola_del_giorno()
                if pdg:
                    c["parola"] = pdg
            except Exception as e:  # noqa: BLE001
                errori.append(f"{d} parola: {str(e)[:60]}")
        if "modo" not in c and modi:
            try:
                tit = modi[pick("modo" + iso, len(modi))]
                df = significato_modo(tit)
                if df:
                    c["modo"] = {"espressione": tit, "significati": df, "link": "https://it.wiktionary.org/wiki/" + tit.replace(" ", "_")}
            except Exception as e:  # noqa: BLE001
                errori.append(f"{d} modo: {str(e)[:60]}")
        if "comune" not in c and comuni:
            for k in range(6):
                try:
                    inf = comune_info(comuni[pick(f"comune{iso}{k}", len(comuni))])
                    if inf:
                        c["comune"] = inf
                        break
                except Exception as e:  # noqa: BLE001
                    errori.append(f"{d} comune: {str(e)[:60]}")
        if "latino" not in c and lat:
            c["latino"] = lat[pick("latino" + iso, len(lat))]
        if "latparola" not in c and plat:
            for k in range(10):
                try:
                    tit, tp = plat[pick(f"latparola{iso}{k}", len(plat))]
                    pl = parola_latina(tit, tp)
                    if pl:
                        c["latparola"] = pl
                        break
                except Exception as e:  # noqa: BLE001
                    errori.append(f"{d} latparola: {str(e)[:60]}")
        for kk in ("frase", "parola", "modo", "comune", "latino", "latparola"):
            r[kk] = c.get(kk)
        giorni[iso] = r
    # "nei prossimi giorni": festività e feste mobili entro 45 giorni
    prossime = [{"data": d.isoformat(), "nome": n} for d, (n, t) in sorted(fest.items()) if 0 < (d - oggi).days <= 45]
    if not any(g["santi"] for g in giorni.values()) and not any(g["accadde"] for g in giorni.values()):
        raise SystemExit("nessun dato letto: " + "; ".join(errori))
    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=0), encoding="utf-8")
    out = {"aggiornato": datetime.now(timezone.utc).isoformat(timespec="seconds"), "luogo": "Caserta", "giorni": giorni, "prossime": prossime,
           "fonti": {"santi": "Vatican News", "astro": "calcolo astronomico per Caserta", "festivita": "calcolate dalle regole di legge e liturgiche",
                     "costituzione": "Normattiva", "storia": "Wikipedia e Wikidata (non istituzionali)", "cultura": "Wikiquote, Wikizionario, Wikipedia (non istituzionali)"}}
    (DATA / "almanacco.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    print("ok", len(giorni), "giorni; errori:", errori)


if __name__ == "__main__":
    sys.exit(main())
