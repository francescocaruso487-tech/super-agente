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
H = {"User-Agent": "RassegnaBot/1.0 (uso personale)", "Accept-Language": "it"}
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
SPORT = re.compile(r"\b(rugby|calcio|campionat|olimpi|mondial|coppa|gran premio|formula 1|giro d'italia|tour de france|tennis|ciclismo|maratona|nba|nfl|scudetto|record|medaglia|atleta|squadra|pallavolo|basket|pallacanestro|boxe|pugilato|nuoto)\w*", re.I)


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


def get(url, **kw):
    r = requests.get(url, headers=H, timeout=30, **kw)
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
        for nome, fn in (("santi", lambda: santo(d)),):
            try:
                r[nome] = fn()
            except Exception as e:  # noqa: BLE001
                errori.append(f"{d} {nome}: {str(e)[:60]}")
                r[nome] = []
        try:
            ev, ric = wiki_it(d)
            r["accadde"] = ev
            r["sport"] = [e for e in ev if SPORT.search(e["testo"])]
            r["ricorrenze"] = ric
        except Exception as e:  # noqa: BLE001
            errori.append(f"{d} wiki: {str(e)[:60]}")
            r["accadde"], r["sport"], r["ricorrenze"] = [], [], []
        for chiave, nome in (("births", "nati"), ("deaths", "morti")):
            try:
                voci = wiki_en_persone(d, chiave)
                lab = wikidata_it([q for _, q in voci])
                lista = [{"anno": a, "nome": lab[q][0], "descr": lab[q][1]} for a, q in voci if q in lab]
                lista.sort(key=lambda x: x["anno"])
                r[nome] = lista[:60]
            except Exception as e:  # noqa: BLE001
                errori.append(f"{d} {nome}: {str(e)[:60]}")
                r[nome] = []
        giorni[d.isoformat()] = r
    # "nei prossimi giorni": festività e feste mobili entro 45 giorni
    prossime = [{"data": d.isoformat(), "nome": n} for d, (n, t) in sorted(fest.items()) if 0 < (d - oggi).days <= 45]
    if not any(g["santi"] for g in giorni.values()) and not any(g["accadde"] for g in giorni.values()):
        raise SystemExit("nessun dato letto: " + "; ".join(errori))
    out = {"aggiornato": datetime.now(timezone.utc).isoformat(timespec="seconds"), "luogo": "Caserta", "giorni": giorni, "prossime": prossime,
           "fonti": {"santi": "Vatican News", "astro": "calcolo astronomico per Caserta", "festivita": "calcolate dalle regole di legge e liturgiche",
                     "costituzione": "Normattiva", "storia": "Wikipedia e Wikidata (non istituzionali)"}}
    (DATA / "almanacco.json").write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    print("ok", len(giorni), "giorni; errori:", errori)


if __name__ == "__main__":
    sys.exit(main())
