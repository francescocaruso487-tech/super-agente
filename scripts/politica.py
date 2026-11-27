#!/usr/bin/env python3
"""Rassegna - aggiornamento automatico del quadro politico.

Legge le pagine ufficiali (Camera, Senato, Governo) e scrive
docs/data/politica_auto.json + docs/data/politica_status.json.

Regole di sicurezza:
  - se una fonte non risponde, cambia formato o da' numeri incoerenti, NON si
    sovrascrive nulla: restano gli ultimi dati buoni e lo stato registra l'errore
    (con un estratto della pagina, utile per correggere il lettore);
  - i dati scritti a mano (docs/data/politica.json) restano la base di riserva.
Uso: python scripts/politica.py [--forza]
"""
import argparse
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
UA = "Mozilla/5.0 (compatible; RassegnaBot/1.0; uso personale)"
TIMEOUT = 30
ORE_MINIME = 6   # non rileggere se l'ultimo successo e' piu' recente di cosi' (salvo --forza)

URL_CAMERA = "https://www.camera.it/leg19/46"
URL_SENATO = "https://www.senato.it/composizione/gruppi-parlamentari/riepilogo-della-composizione"
URL_GOVERNO = "https://www.senato.it/composizione/il-governo"


def ora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def norm(s):
    s = (s or "").replace("’", "'").replace("‘", "'").replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


BROWSER = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "it-IT,it;q=0.9,en;q=0.5"}


def scarica(url):
    # i siti del Senato rifiutano i programmi che si dichiarano bot: intestazioni da normale browser
    h = BROWSER if "senato.it" in url else {"User-Agent": UA, "Accept-Language": "it"}
    r = requests.get(url, headers=h, timeout=TIMEOUT)
    r.raise_for_status()
    if "senato.it" in url and len(r.text) < 2000:
        raise ValueError(f"risposta vuota/anomala da {url}: HTTP {r.status_code}, {len(r.text)} caratteri: {r.text[:200]!r}")
    return r.text


# ---------------------------------------------------------------- gruppi
# (parola chiave in minuscolo, sigla, blocco, colore, ordine nell'emiciclo, nome)
CAMERA = [
    ("alleanza verdi", "AVS", "opp", "#be185d", 10, "Alleanza Verdi e Sinistra"),
    ("movimento 5", "M5S", "opp", "#f59e0b", 20, "Movimento 5 Stelle"),
    ("partito democratico", "PD", "opp", "#dc2626", 30, "Partito Democratico"),
    ("+europa", "+Eu", "opp", "#6366f1", 40, "+Europa (Misto)"),
    ("italia viva", "IV", "opp", "#c084fc", 50, "Italia Viva"),
    ("azione", "Az", "opp", "#8b5cf6", 60, "Azione"),
    ("futuro nazionale", "FN", "altri", "#64748b", 80, "Futuro Nazionale - Vannacci (Misto)"),
    ("noi moderati", "NM", "magg", "#7dd3fc", 100, "Noi Moderati - MAIE"),
    ("forza italia", "FI", "magg", "#0ea5e9", 110, "Forza Italia"),
    ("fratelli d", "FdI", "magg", "#1e40af", 120, "Fratelli d'Italia"),
    ("lega", "Lega", "magg", "#0d9488", 130, "Lega"),
]
SENATO = [
    ("movimento 5", "M5S", "opp", "#f59e0b", 20, "Movimento 5 Stelle"),
    ("partito democratico", "PD", "opp", "#dc2626", 30, "Partito Democratico"),
    ("italia viva", "IV", "opp", "#c084fc", 50, "Italia Viva"),
    ("azione", "Az", "opp", "#8b5cf6", 60, "Azione"),
    ("autonomie", "Aut", "altri", "#a3a3a3", 70, "Per le Autonomie"),
    ("misto", "Misto", "altri", "#94a3b8", 75, "Misto (include AVS)"),
    ("civici d", "NM", "magg", "#7dd3fc", 100, "Civici d'Italia - Noi Moderati - MAIE"),
    ("noi moderati", "NM", "magg", "#7dd3fc", 100, "Civici d'Italia - Noi Moderati - MAIE"),
    ("forza italia", "FI", "magg", "#0ea5e9", 110, "Forza Italia"),
    ("fratelli d", "FdI", "magg", "#1e40af", 120, "Fratelli d'Italia"),
    ("lega", "Lega", "magg", "#0d9488", 130, "Lega"),
]
ALTRI = ("Altri", "altri", "#94a3b8", 70, "Altri: minoranze, non iscritti")


def righe_tabella(html):
    """Coppie (etichetta, numero) lette da tabelle; se non ci sono tabelle, dalle righe di testo."""
    soup = BeautifulSoup(html, "lxml")
    out = []
    for tr in soup.find_all("tr"):
        celle = [norm(c.get_text(" ")) for c in tr.find_all(["td", "th"])]
        celle = [c for c in celle if c]
        num = next((c for c in celle[1:] if re.fullmatch(r"\d{1,3}", c)), None)
        if len(celle) >= 2 and num:
            out.append((celle[0], int(num)))
    if out:
        return out
    testo = soup.get_text("\n")
    righe = [norm(r) for r in testo.split("\n") if norm(r)]
    for i, r in enumerate(righe):
        m = re.match(r"^(.*\D)\s+(\d{1,3})$", r)
        if m:
            out.append((m.group(1), int(m.group(2))))
        elif re.fullmatch(r"\d{1,3}", r) and i > 0 and not re.fullmatch(r"\d{1,3}", righe[i - 1]):
            out.append((righe[i - 1], int(r)))
    return out


def costruisci(righe, tabella, giuste, minimo, massimo):
    """Raggruppa le righe nei gruppi noti; solleva ValueError se i numeri non tornano."""
    gruppi, totale_pagina, trovate = {}, None, set()
    ha_componenti = any(norm(l).lower().startswith("misto-") for l, _ in righe)
    for label, n in righe:
        l = norm(label).lower()
        if re.fullmatch(r"totale.*", l):
            totale_pagina = n
            continue
        if l in ("misto", "misto (totale componenti, sotto elencate)") and ha_componenti:
            continue
        if "deputati non iscritti" in l or "minoranze linguistiche" in l or "sud chiama nord" in l:
            sig, blocco, col, ordine, nome = ALTRI
            g = gruppi.setdefault(sig, {"sigla": sig, "nome": nome, "n": 0, "blocco": blocco, "colore": col, "_o": ordine})
            g["n"] += n
            continue
        # vince la parola chiave che compare per prima nel nome (es. "Lega ... d'Azione" e' la Lega)
        cand = [(l.index(t[0]), -len(t[0]), t) for t in tabella if t[0] in l]
        if cand:
            _, _, (chiave, sig, blocco, col, ordine, nome) = min(cand)
            g = gruppi.setdefault(sig, {"sigla": sig, "nome": nome, "n": 0, "blocco": blocco, "colore": col, "_o": ordine})
            g["n"] += n
            trovate.add(sig)
    for s in giuste:
        if s not in trovate:
            raise ValueError(f"gruppo non trovato: {s}")
    tot = sum(g["n"] for g in gruppi.values())
    if not (minimo <= tot <= massimo):
        raise ValueError(f"totale seggi incoerente: {tot}")
    if totale_pagina and abs(totale_pagina - tot) > 3 and totale_pagina >= minimo:
        raise ValueError(f"somma {tot} diversa dal totale della pagina {totale_pagina}")
    lista = sorted(gruppi.values(), key=lambda g: g["_o"])
    for g in lista:
        g.pop("_o")
    return lista, tot


def _debug_camera(html):
    """Solo diagnostica: link della pagina dei gruppi e estratto di una pagina di gruppo (per trovare i capigruppo)."""
    try:
        soup = BeautifulSoup(html, "lxml")
        ancore = [(norm(a.get_text(" "))[:60], requests.compat.urljoin(URL_CAMERA, a["href"])) for a in soup.find_all("a", href=True)
                  if re.search(r"gruppi|leg19/\d+", a["href"]) and norm(a.get_text(" "))][:40]
        pagina = next((u for t, u in ancore if "fratelli" in t.lower()), None)
        estratto = norm(BeautifulSoup(scarica(pagina), "lxml").get_text(" "))[:1500] if pagina else ""
        (DATA / "debug_camera_gruppi.json").write_text(json.dumps({"link": ancore, "pagina": pagina, "estratto": estratto},
                                                                    ensure_ascii=False, indent=1), "utf-8")
    except Exception:  # noqa: BLE001
        pass


def leggi_camera():
    html = scarica(URL_CAMERA)
    _debug_camera(html)
    lista, tot = costruisci(righe_tabella(html), CAMERA, {"FdI", "PD", "Lega", "FI", "M5S"}, 380, 405)
    return {"totale": tot, "maggioranza_soglia": tot // 2 + 1, "gruppi": lista, "link": URL_CAMERA}


RUOLO = re.compile(r"^(presidente del consiglio|vicepresidente|ministr[oa]|sottosegretari)", re.I)


LEG19 = "<http://dati.camera.it/ocd/legislatura.rdf/repubblica_19>"
FOAF = "http://xmlns.com/foaf/0.1/"


def _nome_proprio(nome, cognome):
    return norm(f"{nome} {cognome}").title().replace("'S ", "'s ")


def leggi_governo():
    """Governo in carica dai dati aperti della Camera: presidente, vicepresidenti, ministri (l'ultimo per ogni dicastero)."""
    g = sparql(f"SELECT ?g WHERE {{ ?g a ocd:governo ; ocd:rif_leg {LEG19} . FILTER NOT EXISTS {{ ?g ocd:endDate ?e }} }}")
    if not g:
        raise ValueError("governo in carica non trovato nei dati aperti")
    righe = sparql(f"""SELECT ?t ?fn ?sn ?sd WHERE {{ ?m a ocd:membroGoverno ; ocd:rif_governo <{g[0]['g']['value']}> ;
        dc:title ?t ; <{FOAF}firstName> ?fn ; <{FOAF}surname> ?sn ; ocd:startDate ?sd .
        FILTER NOT EXISTS {{ ?m ocd:endDate ?e }} }}""")
    ultimi = {}
    for b in righe:
        t = re.sub(r"\s*\(\d{2}\.\d{2}\.\d{4}\)\s*$", "", norm(b["t"]["value"]))
        if not re.match(r"(vice )?presidente del consiglio|ministr", t, re.I) or re.match(r"vice ?ministr", t, re.I):
            continue
        nome = _nome_proprio(b["fn"]["value"], b["sn"]["value"])
        chiave = (t, nome) if re.match(r"vice ?presidente", t, re.I) else (t,)  # i vicepresidenti sono piu' di uno
        if chiave not in ultimi or b["sd"]["value"] > ultimi[chiave][0]:
            ultimi[chiave] = (b["sd"]["value"], t, nome)
    persone = [{"nome": n, "ruolo": t} for _, t, n in sorted(ultimi.values(), key=lambda x: (not x[1].lower().startswith("presidente"), x[1]))]
    uniche = {x["nome"] for x in persone}
    if len(uniche) < 18 or not any(re.match(r"presidente del consiglio", x["ruolo"], re.I) for x in persone):
        raise ValueError(f"governo non riconosciuto: {len(uniche)} nomi, ruoli: " + "; ".join(x["ruolo"][:40] for x in persone[:6]))
    return {"persone": persone, "link": "https://www.governo.it/it/i-ministri"}


def leggi_capigruppo():
    """Presidente (capogruppo) di ogni gruppo della Camera, dagli incarichi dei dati aperti; li scrive in deputati.json."""
    righe = sparql(f"""SELECT ?lab ?sd WHERE {{ ?i a ocd:incarico ; ocd:rif_leg {LEG19} ; ocd:ruolo ?r ; rdfs:label ?lab ;
        ocd:rif_gruppoParlamentare ?g ; ocd:startDate ?sd .
        FILTER(UCASE(STR(?r)) = "PRESIDENTE") FILTER NOT EXISTS {{ ?i ocd:endDate ?e }} }}""".replace("rdfs:label", "<http://www.w3.org/2000/01/rdf-schema#label>"))
    if not righe:
        ruoli = sparql(f"SELECT DISTINCT ?r WHERE {{ ?i a ocd:incarico ; ocd:rif_leg {LEG19} ; ocd:ruolo ?r }} LIMIT 25")
        raise ValueError("nessun presidente di gruppo trovato; ruoli presenti: " + ", ".join(b["r"]["value"] for b in ruoli))
    capi = {}
    for b in righe:
        m = re.match(r"(?i)presidente del gruppo (.+?),\s*(.+?)\s*\(", norm(b["lab"]["value"]))
        if m and (m.group(1).lower() not in capi or b["sd"]["value"] > capi[m.group(1).lower()][0]):
            capi[m.group(1).lower()] = (b["sd"]["value"], norm(m.group(2)).title())
    f = DATA / "deputati.json"
    if not f.exists():
        raise ValueError("deputati.json non ancora disponibile")
    d = json.loads(f.read_text("utf-8"))
    n = 0
    for g in d["gruppi"]:
        nome = g["gruppo"].lower()
        if nome.startswith("misto-"):  # le componenti del Misto non hanno un proprio capogruppo
            continue
        # i gruppi Misto/componenti: si confronta con la parte prima del trattino
        for chiave, (_, persona) in capi.items():
            if chiave == nome or chiave.startswith(nome) or nome.startswith(chiave):
                g["presidente"] = persona
                n += 1
                break
    f.write_text(json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
    return {"totale": n}


def leggi_proposte():
    """Ultimi atti (proposte e disegni di legge) con chi li presenta e a che punto sono."""
    righe = sparql(f"""SELECT ?a ?lab ?ini ?dt WHERE {{ ?a a ocd:atto ; ocd:rif_leg {LEG19} ; dc:date ?dt ;
        <http://www.w3.org/2000/01/rdf-schema#label> ?lab ; ocd:iniziativa ?ini }} ORDER BY DESC(?dt) LIMIT 40""")
    out, visti = [], set()
    for b in righe:
        titolo_atto = norm(b["lab"]["value"]).strip(' "')
        if titolo_atto in visti:
            continue
        visti.add(titolo_atto)
        voce = {"data": data_it(b["dt"]["value"]), "titolo": titolo_atto[:260], "iniziativa": norm(b["ini"]["value"])}
        try:
            st = sparql(f"""SELECT ?l WHERE {{ <{b['a']['value']}> ocd:rif_statoIter ?si . ?si <http://www.w3.org/2000/01/rdf-schema#label> ?l ;
                dc:date ?d }} ORDER BY DESC(?d) LIMIT 1""")
            if st:
                voce["stato"] = norm(st[0]["l"]["value"])[:120]
        except Exception:  # noqa: BLE001
            pass
        out.append(voce)
        if len(out) >= 15:
            break
    if not out:
        raise ValueError("nessun atto leggibile")
    (DATA / "proposte.json").write_text(json.dumps({"aggiornato": ora(), "proposte": out,
        "link": "https://www.camera.it/leg19/126"}, ensure_ascii=False, indent=1), "utf-8")
    return {"totale": len(out)}


def trova(tabella, low):
    """Riga della tabella la cui parola chiave compare per prima nel nome (a parita': la piu' lunga)."""
    c = [(low.index(r[0]), -len(r[0]), i) for i, r in enumerate(tabella) if r[0] in low]
    return tabella[min(c)[2]] if c else None


LETTERE = "ABCDEFGIKLMNOPQRSTUVZ"


def titolo(nome):
    return norm(nome).title().replace("'S", "'s")


def leggi_deputati():
    """Elenco dei deputati in carica con il loro gruppo (pagine 'Elenco deputati' della Camera).
    Confronta con la lettura precedente e registra i passaggi di gruppo."""
    persone = {}
    for lt in LETTERE:
        html = scarica(f"https://www.camera.it/deputati/elenco?leg=19&lettera={lt}")
        corrente = None
        for a in BeautifulSoup(html, "lxml").find_all("a", href=True):
            m = re.search(r"/deputati/elenco/19-(\d+)", a["href"])
            testo = norm(a.get_text(" "))
            if m and testo and not testo.lower().startswith(("immagine", "scrivi")):
                if corrente is None or corrente["id"] != m.group(1):
                    corrente = {"id": m.group(1), "nome": titolo(testo), "gruppo": None}
                    persone[corrente["id"]] = corrente
            elif "shadow_gruppi_parlamentari" in a["href"] and corrente and not corrente["gruppo"] and testo:
                corrente["gruppo"] = testo
    attivi = {k: v for k, v in persone.items() if v["gruppo"]}
    if not 380 <= len(attivi) <= 405:
        raise ValueError(f"numero di deputati incoerente: {len(attivi)} (trovati {len(persone)} nomi)")
    gruppi = {}
    for v in attivi.values():
        g = gruppi.setdefault(v["gruppo"], {"gruppo": v["gruppo"], "deputati": []})
        g["deputati"].append({"id": v["id"], "nome": v["nome"]})
    elenco = []
    for g in gruppi.values():
        low = g["gruppo"].lower()
        riga = trova(CAMERA, low)
        g.update({"sigla": riga[1] if riga else g["gruppo"][:8], "blocco": riga[2] if riga else "altri",
                  "colore": riga[3] if riga else "#94a3b8", "ordine": riga[4] if riga else 75})
        g["n"] = len(g["deputati"])
        g["deputati"].sort(key=lambda d: d["nome"])
        elenco.append(g)
    elenco.sort(key=lambda g: -g["n"])
    # passaggi di gruppo rispetto alla lettura precedente
    f = DATA / "deputati.json"
    prec = json.loads(f.read_text("utf-8")) if f.exists() else {}
    vecchi = {d["id"]: (d["nome"], g["gruppo"]) for g in prec.get("gruppi", []) for d in g["deputati"]}
    variazioni = list(prec.get("variazioni", []))
    oggi = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    if vecchi:
        for k, v in attivi.items():
            if k in vecchi and vecchi[k][1] != v["gruppo"]:
                variazioni.insert(0, {"data": oggi, "nome": v["nome"], "tipo": "passaggio", "da": vecchi[k][1], "a": v["gruppo"]})
            elif k not in vecchi:
                variazioni.insert(0, {"data": oggi, "nome": v["nome"], "tipo": "subentro", "a": v["gruppo"]})
        for k, (nome, gr) in vecchi.items():
            if k not in attivi:
                variazioni.insert(0, {"data": oggi, "nome": nome, "tipo": "cessato", "da": gr})
    f.write_text(json.dumps({"aggiornato": ora(), "totale": len(attivi), "gruppi": elenco,
                             "variazioni": variazioni[:40], "link": "https://www.camera.it/deputati/elenco?leg=19"},
                            ensure_ascii=False, indent=1), "utf-8")
    return {"totale": len(attivi)}


SIGLE_SENATO = [("fdi", "FdI"), ("lsp", "Lega"), ("fi", "FI"), ("pd", "PD"), ("m5s", "M5S"), ("misto", "Misto"),
                ("aut", "Aut"), ("noi", "NM"), ("nm", "NM"), ("civici", "NM"), ("iv", "IV"), ("az", "Az")]


PARTITI = [  # (sigla, nome, titoli possibili della pagina su it.wikipedia)
    ("FdI", "Fratelli d'Italia", ["Fratelli d'Italia"]),
    ("PD", "Partito Democratico", ["Partito Democratico (Italia)", "Partito Democratico"]),
    ("Lega", "Lega per Salvini Premier", ["Lega per Salvini Premier", "Lega (partito politico)"]),
    ("FI", "Forza Italia", ["Forza Italia (2013)", "Forza Italia"]),
    ("M5S", "Movimento 5 Stelle", ["Movimento 5 Stelle"]),
    ("AVS", "Alleanza Verdi e Sinistra", ["Alleanza Verdi e Sinistra"]),
    ("Az", "Azione", ["Azione (partito politico)", "Azione (partito)"]),
    ("IV", "Italia Viva", ["Italia Viva"]),
    ("NM", "Noi Moderati", ["Noi Moderati"]),
    ("+Eu", "+Europa", ["+Europa"]),
    ("FN", "Futuro Nazionale", ["Futuro Nazionale", "Futuro Nazionale (partito)"]),
]
CAMPI_GUIDA = ["segretario generale", "segretario", "leader", "presidente", "portavoce", "coordinatore", "reggente", "capo politico"]
ETICHETTE_WD = {"FdI": ["Fratelli d'Italia"], "M5S": ["Movimento 5 Stelle"], "AVS": ["Alleanza Verdi e Sinistra"], "FN": ["Futuro Nazionale"], "NM": ["Noi Moderati"]}


GUIDA_DI_RISERVA = {"M5S": ("Presidente", "Giuseppe Conte"), "FdI": ("Presidente", "Giorgia Meloni")}
ESCLUSI_GUIDA = {"Beppe Grillo"}


def guida_da_wikipedia(titolo_pagina, prima=None):
    r = requests.get("https://it.wikipedia.org/w/api.php", headers={"User-Agent": UA}, timeout=30, params={
        "action": "query", "prop": "revisions", "rvprop": "content", "rvslots": "main", "titles": titolo_pagina,
        "redirects": 1, "format": "json", "formatversion": 2})
    r.raise_for_status()
    pagine = r.json().get("query", {}).get("pages", [])
    if not pagine or pagine[0].get("missing"):
        return None
    testo = pagine[0]["revisions"][0]["slots"]["main"]["content"][:8000]
    out = []
    for m in re.finditer(r"^\s*\|\s*([A-Za-zàèéìòù _]+?)\s*=\s*(.*?)(?=\n\s*\||\n\s*\}\})", testo, re.S | re.M):
        chiave = m.group(1).strip().lower().replace("_", " ")
        if chiave not in CAMPI_GUIDA:
            continue
        valore = re.sub(r"<ref[^>]*?/>|<ref.*?</ref>|<!--.*?-->", "", m.group(2), flags=re.S)
        links = re.findall(r"\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]", valore)[:1]
        if not links:  # valore scritto come semplice testo
            txt = norm(re.sub(r"\{\{.*?\}\}|<[^>]+>|'{2,}", "", valore).split("\n")[0].split("(")[0])
            if re.fullmatch(r"[A-ZÀ-Ü][\w'’.-]+(?: [A-ZÀ-Üa-zà-ü][\w'’.-]+){1,3}", txt):
                links = [(txt, "")]
        for link in links:
            nome = norm(link[1] or link[0])
            if nome and not re.match(r"(file|immagine|categoria):", nome, re.I) and re.search(r"[a-z]", nome):
                voce = {"ruolo": chiave.capitalize(), "nome": nome}
                if voce not in out:
                    out.append(voce)
    ordine = prima or ["leader", "segretario generale", "segretario", "presidente", "coordinatore", "portavoce", "reggente", "capo politico"]
    out.sort(key=lambda v: ordine.index(v["ruolo"].lower()) if v["ruolo"].lower() in ordine else 99)
    out = [v for v in out if v["nome"] not in ESCLUSI_GUIDA]  # fondatori/garanti che non guidano il partito
    return out[:1] or None


def guida_da_wikidata(etichette):
    """Piano B per i partiti senza infobox leggibile: incarichi 'chairperson' senza data di fine e persona in vita."""
    valori = " ".join(f'"{e}"@it' for e in etichette)
    q = f"""SELECT ?personaLabel WHERE {{ VALUES ?lab {{ {valori} }}
      ?p rdfs:label ?lab ; wdt:P31/wdt:P279* wd:Q7278 ; wdt:P17 wd:Q38 . ?p p:P488 ?st . ?st ps:P488 ?persona .
      FILTER NOT EXISTS {{ ?st pq:P582 ?fine }} FILTER NOT EXISTS {{ ?persona wdt:P570 ?morte }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "it,en". }} }}"""
    r = requests.get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"},
                     headers={"User-Agent": UA, "Accept": "application/sparql-results+json"}, timeout=60)
    r.raise_for_status()
    nomi = []
    for b in r.json()["results"]["bindings"]:
        n = norm(b["personaLabel"]["value"])
        if n and not re.fullmatch(r"Q\d+", n) and n not in nomi and n not in ESCLUSI_GUIDA:
            nomi.append(n)
    return [{"ruolo": "Guida", "nome": n} for n in nomi[:1]] or None


def leggi_segretari():
    """Chi guida ogni partito, dall'infobox della pagina Wikipedia del partito (campi segretario/leader/presidente...)."""
    trovati, mancanti = [], []
    for sig, nome, titoli in PARTITI:
        guida = None
        for t in titoli:
            try:
                guida = guida_da_wikipedia(t, ["presidente", "leader", "segretario generale", "segretario", "coordinatore", "portavoce", "reggente", "capo politico"] if sig == "M5S" else None)
            except requests.RequestException:
                guida = None
            if guida:
                break
        if not guida and sig in ETICHETTE_WD:
            try:
                guida = guida_da_wikidata(ETICHETTE_WD[sig])
            except requests.RequestException:
                guida = None
        if not guida and sig in GUIDA_DI_RISERVA:  # ultima spiaggia, da rivedere a mano se cambia
            guida = [{"ruolo": GUIDA_DI_RISERVA[sig][0], "nome": GUIDA_DI_RISERVA[sig][1]}]
        if guida:
            trovati.append({"sigla": sig, "nome": nome, "guida": guida})
        else:
            mancanti.append(sig)
    if len(trovati) < 6:
        raise ValueError(f"partiti con un capo trovati: {len(trovati)} su {len(PARTITI)}; mancanti: {mancanti}")
    (DATA / "partiti.json").write_text(json.dumps({"aggiornato": ora(), "fonte": "Wikipedia e Wikidata",
        "partiti": trovati, "mancanti": mancanti}, ensure_ascii=False, indent=1), "utf-8")
    return {"totale": len(trovati)}


SPARQL_CAMERA = "https://dati.camera.it/sparql"
PREFISSI = ("PREFIX ocd: <http://dati.camera.it/ocd/> PREFIX dc: <http://purl.org/dc/elements/1.1/> "
            "PREFIX xsd: <http://www.w3.org/2001/XMLSchema#> ")


def sparql(q):
    r = requests.get(SPARQL_CAMERA, params={"query": PREFISSI + q, "format": "application/sparql-results+json"},
                     headers={"User-Agent": UA, "Accept": "application/sparql-results+json"}, timeout=90)
    r.raise_for_status()
    return r.json()["results"]["bindings"]


def data_it(v):
    v = str(v)
    m = re.match(r"(\d{4})-?(\d{2})-?(\d{2})", v)
    return f"{m.group(3)}/{m.group(2)}/{m.group(1)}" if m else v


def leggi_votazioni():
    """Ultime votazioni finali della Camera (XIX leg.): titolo, data, favorevoli/contrari/astenuti, esito."""
    base = """SELECT ?v ?titolo ?descr ?appr ?data ?fav ?con ?ast ?vot WHERE {
      ?v a ocd:votazione ; dc:date ?data ; ocd:favorevoli ?fav ; ocd:contrari ?con ; ocd:astenuti ?ast ; ocd:votanti ?vot .
      OPTIONAL { ?v dc:title ?titolo } OPTIONAL { ?v dc:description ?descr } OPTIONAL { ?v ocd:approvato ?appr } %s } ORDER BY DESC(?data) LIMIT 60"""
    try:
        righe = sparql(base % 'FILTER(CONTAINS(LCASE(STR(?titolo)), "votazione finale"))')
        if len(righe) < 3:
            righe = sparql(base % "")
    except Exception:
        try:  # aiuto per correggere il lettore: quali campi esistono davvero?
            campi = sparql("SELECT DISTINCT ?p WHERE { ?v a ocd:votazione ; ?p ?o } LIMIT 40")
            raise ValueError("lettura fallita; campi trovati: " + ", ".join(c["p"]["value"].rsplit("/", 1)[-1] for c in campi))
        except ValueError:
            raise
        except Exception as e2:  # noqa: BLE001
            raise ValueError(f"endpoint non raggiungibile o schema diverso ({type(e2).__name__})") from e2
    voti, visti = [], set()
    for b in righe:
        try:
            fav, con, ast, vot = (int(float(b[k]["value"])) for k in ("fav", "con", "ast", "vot"))
        except (KeyError, ValueError):
            continue
        chiave = (b["data"]["value"], fav, con, ast, vot)
        if chiave in visti:
            continue
        visti.add(chiave)
        t = norm(b.get("titolo", {}).get("value", "Votazione"))
        d = norm(b.get("descr", {}).get("value", ""))
        voti.append({"id": b["v"]["value"].rsplit("/", 1)[-1], "uri": b["v"]["value"], "data": data_it(b["data"]["value"]),
                     "titolo": (d if len(d) > len(t) else t)[:300], "fav": fav, "con": con, "ast": ast,
                     "votanti": vot, "esito": ("approvata" if b["appr"]["value"] == "1" else "respinta") if "appr" in b else ("approvata" if fav > con else "respinta")})
    if not voti:
        raise ValueError("nessuna votazione leggibile")
    try:  # diagnostica: tutti i campi della votazione piu' recente e un esempio di voto individuale
        uri = voti[0]["uri"]
        prop = sparql(f"SELECT ?p ?o WHERE {{ <{uri}> ?p ?o }} LIMIT 60")
        x = sparql(f"SELECT ?x WHERE {{ ?x ocd:rif_votazione <{uri}> }} LIMIT 1")
        altri = sparql(f"SELECT ?q ?p ?o WHERE {{ <{x[0]['x']['value']}> ?p ?o }} LIMIT 40") if x else []
        altri = [{"q": {"value": "voto"}, "p": b["p"], "o": b["o"]} for b in altri]
        (DATA / "debug_votazioni.json").write_text(json.dumps({
            "votazione": [[b["p"]["value"].rsplit("/", 1)[-1], b["o"]["value"][:150]] for b in prop],
            "risorse_collegate": [[b["q"]["value"].rsplit("/", 1)[-1], b["p"]["value"].rsplit("/", 1)[-1], b["o"]["value"][:100]] for b in altri],
        }, ensure_ascii=False, indent=1), "utf-8")
    except Exception:  # noqa: BLE001
        pass
    for v in voti[:10]:  # come ha votato ciascun gruppo (voti individuali dei deputati, raggruppati)
        try:
            righe_g = sparql(f"SELECT ?sg ?t (COUNT(DISTINCT ?x) AS ?n) WHERE {{ ?x a ocd:voto ; ocd:rif_votazione <{v['uri']}> ; "
                             f"ocd:siglaGruppo ?sg ; dc:type ?t }} GROUP BY ?sg ?t")
            g = {}
            for b in righe_g:
                t = b["t"]["value"].lower()
                k = "fav" if t.startswith("favorev") else "con" if t.startswith("contrar") else "ast" if t.startswith("astenut") else "altro"
                g.setdefault(b["sg"]["value"], {"fav": 0, "con": 0, "ast": 0, "altro": 0})[k] += int(float(b["n"]["value"]))
            v["gruppi"] = sorted(({"sigla": k, **x} for k, x in g.items()), key=lambda x: -(x["fav"] + x["con"] + x["ast"] + x["altro"]))
        except Exception:  # noqa: BLE001
            pass
    for v in voti[:10]:  # scheda ufficiale della votazione e titolo ufficiale dell'atto votato
        try:
            r = sparql(f"SELECT ?r WHERE {{ <{v['uri']}> dc:relation ?r }} LIMIT 1")
            if r:
                v["scheda"] = r[0]["r"]["value"]
        except Exception:  # noqa: BLE001
            pass
        m = re.match(r"(?i)(?:DDL|PDL|DL|DOC\.?)\s*(\d{1,5})", v["titolo"])
        if not m:
            continue
        num = m.group(1)
        for filtro in (f'?a dc:identifier "{num}"', f'?a dc:identifier "C.{num}"', ""):
            try:
                if filtro:
                    q = f"SELECT ?lab ?ini WHERE {{ ?a a ocd:atto ; ocd:rif_leg {LEG19} ; <http://www.w3.org/2000/01/rdf-schema#label> ?lab . {filtro} . OPTIONAL {{ ?a ocd:iniziativa ?ini }} }} LIMIT 3"
                else:
                    q = (f"SELECT ?lab ?ini WHERE {{ ?a a ocd:atto ; ocd:rif_leg {LEG19} ; <http://www.w3.org/2000/01/rdf-schema#label> ?lab . "
                         f"OPTIONAL {{ ?a ocd:iniziativa ?ini }} FILTER(CONTAINS(STR(?lab), \"C. {num}.\") || STRSTARTS(STR(?lab), \"{num}.\")) }} LIMIT 3")
                rr = sparql(q)
                if rr:
                    v["atto"] = {"titolo": norm(rr[0]["lab"]["value"]).strip(' "')[:500],
                                 "iniziativa": norm(rr[0]["ini"]["value"]) if "ini" in rr[0] else ""}
                    break
            except Exception:  # noqa: BLE001
                continue
        v["scheda_atto"] = f"https://www.camera.it/leg19/126?leg=19&idDocumento={num}"
    for v in voti:
        v.pop("uri", None)
    (DATA / "votazioni.json").write_text(json.dumps({"aggiornato": ora(), "voti": voti[:20],
        "link": "https://www.camera.it/deputati/statistiche_voto"}, ensure_ascii=False, indent=1), "utf-8")
    return {"totale": len(voti)}


# Il sito del Senato mostra una verifica anti-robot e i suoi dati aperti non hanno i gruppi attuali: Senato a mano (politica.json).
BLOCCHI = {"camera": leggi_camera, "governo": leggi_governo, "deputati": leggi_deputati, "capigruppo": leggi_capigruppo,
           "segretari": leggi_segretari, "votazioni": leggi_votazioni, "proposte": leggi_proposte}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--forza", action="store_true")
    args = ap.parse_args()
    DATA.mkdir(parents=True, exist_ok=True)
    pa, ps = DATA / "politica_auto.json", DATA / "politica_status.json"
    auto = json.loads(pa.read_text("utf-8")) if pa.exists() else {}
    stato = json.loads(ps.read_text("utf-8")) if ps.exists() else {}
    adesso = datetime.now(timezone.utc)
    for nome, fn in BLOCCHI.items():
        s = stato.setdefault(nome, {})
        ultimo = s.get("ok_il")
        if ultimo and not args.forza:
            try:
                if adesso - datetime.strptime(ultimo, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc) < timedelta(hours=ORE_MINIME):
                    continue
            except ValueError:
                pass
        try:
            dati = fn()
            dati["aggiornato"] = ora()
            auto[nome] = dati
            s.update({"ok": True, "ok_il": dati["aggiornato"], "errore": None})
            print(f"[ok] {nome}")
        except Exception as e:  # noqa: BLE001  (qualunque errore: si tengono i dati vecchi)
            s.update({"ok": False, "ultimo_tentativo": ora(), "errore": f"{type(e).__name__}: {e}"[:1600]})
            print(f"[errore] {nome}: {e}", file=sys.stderr)
    pa.write_text(json.dumps(auto, ensure_ascii=False, indent=1), "utf-8")
    ps.write_text(json.dumps(stato, ensure_ascii=False, indent=1), "utf-8")


if __name__ == "__main__":
    main()
