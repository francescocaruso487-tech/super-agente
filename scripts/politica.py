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
URL_GOVERNO = "https://www.governo.it/it/i-ministri"


def ora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def norm(s):
    s = (s or "").replace("’", "'").replace("‘", "'").replace("\xa0", " ")
    return re.sub(r"\s+", " ", s).strip()


def scarica(url):
    r = requests.get(url, headers={"User-Agent": UA, "Accept-Language": "it"}, timeout=TIMEOUT)
    r.raise_for_status()
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
        if len(celle) >= 2 and re.fullmatch(r"\d{1,3}", celle[-1]):
            out.append((celle[0], int(celle[-1])))
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


def leggi_camera():
    html = scarica(URL_CAMERA)
    lista, tot = costruisci(righe_tabella(html), CAMERA, {"FdI", "PD", "Lega", "FI", "M5S"}, 380, 405)
    return {"totale": tot, "maggioranza_soglia": tot // 2 + 1, "gruppi": lista, "link": URL_CAMERA}


def leggi_senato():
    html = scarica(URL_SENATO)
    righe = [(l, n) for l, n in righe_tabella(html) if any(k in norm(l).lower() for k, *_ in SENATO)]
    lista, tot = costruisci(righe, SENATO, {"FdI", "PD", "Lega", "FI", "M5S"}, 190, 215)
    return {"totale": tot, "maggioranza_soglia": tot // 2 + 1, "gruppi": lista, "link": URL_SENATO,
            "nota": "Il totale comprende i senatori a vita. AVS siede nel gruppo Misto."}


RUOLO = re.compile(r"^(presidente del consiglio|vicepresidente|ministr[oa]|sottosegretari)", re.I)


def leggi_governo():
    html = scarica(URL_GOVERNO)
    soup = BeautifulSoup(html, "lxml")
    trovati, visti = [], set()
    for el in soup.find_all(["article", "li", "div"]):
        righe = [norm(r) for r in el.get_text("\n").split("\n") if norm(r)]
        if not (2 <= len(righe) <= 6):
            continue
        ruoli = [r for r in righe if RUOLO.match(r)]
        nomi = [r for r in righe if not RUOLO.match(r) and re.fullmatch(r"[A-ZÀ-Ü][\w'’.-]+( [A-Za-zÀ-ü][\w'’.-]+){1,4}", r) and len(r) < 45]
        if ruoli and nomi:
            chiave = (nomi[0], ruoli[0])
            if chiave not in visti:
                visti.add(chiave)
                trovati.append({"nome": nomi[0], "ruolo": ruoli[0]})
    nomi_unici = {t["nome"] for t in trovati}
    if len(nomi_unici) < 18 or not any(re.match(r"presidente del consiglio", t["ruolo"], re.I) for t in trovati):
        estratto = norm(soup.get_text(" "))[:500]
        raise ValueError(f"elenco ministri non riconosciuto ({len(nomi_unici)} nomi). Estratto: {estratto}")
    return {"persone": trovati, "link": URL_GOVERNO}


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


def leggi_senatori():
    """Senatori per gruppo: parte dalla pagina riepilogo e legge la pagina di ogni gruppo.
    Registra i passaggi rispetto alla lettura precedente."""
    home = BeautifulSoup(scarica(URL_SENATO), "lxml")
    gruppi_url = {}
    for a in home.find_all("a", href=True):
        if "composizione?did=" in a["href"]:
            nome = re.sub(r"\s+\d+$", "", norm(a.get_text(" ")))
            if nome:
                gruppi_url.setdefault(nome, requests.compat.urljoin(URL_SENATO, a["href"]))
    if len(gruppi_url) < 5:
        raise ValueError(f"gruppi del Senato trovati: {len(gruppi_url)}")
    attivi, per_gruppo, capi = {}, {}, {}
    for nome, url in gruppi_url.items():
        soup = BeautifulSoup(scarica(url), "lxml")
        nomi, primo = {}, None
        for img in soup.find_all("img", alt=True):
            m = re.match(r"\s*Foto sen\.\s+(.+)", img["alt"])
            if m:
                n = titolo(m.group(1))
                nomi[n.lower()] = n
                primo = primo or n
        capi[nome] = primo if primo and "presidente" in soup.get_text(" ").lower() else None
        per_gruppo[nome] = sorted(nomi.values())
        for n in nomi.values():
            attivi[n.lower()] = (n, nome)
    if not 190 <= len(attivi) <= 206:
        raise ValueError(f"numero di senatori incoerente: {len(attivi)}")
    elenco = []
    for nome, persone in per_gruppo.items():
        if not persone:
            continue
        low = nome.lower()
        riga = trova(SENATO, low)
        elenco.append({"gruppo": nome, "sigla": riga[1] if riga else nome[:8], "blocco": riga[2] if riga else "altri",
                       "colore": riga[3] if riga else "#94a3b8", "n": len(persone), "presidente": capi.get(nome),
                       "deputati": [{"id": x.lower(), "nome": x} for x in persone]})
    elenco.sort(key=lambda g: -g["n"])
    f = DATA / "senatori.json"
    prec = json.loads(f.read_text("utf-8")) if f.exists() else {}
    vecchi = {d["id"]: (d["nome"], g["gruppo"]) for g in prec.get("gruppi", []) for d in g["deputati"]}
    variazioni = list(prec.get("variazioni", []))
    oggi = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    if vecchi:
        for k, (n, gr) in attivi.items():
            if k in vecchi and vecchi[k][1] != gr:
                variazioni.insert(0, {"data": oggi, "nome": n, "tipo": "passaggio", "da": vecchi[k][1], "a": gr})
            elif k not in vecchi:
                variazioni.insert(0, {"data": oggi, "nome": n, "tipo": "subentro", "a": gr})
        for k, (n, gr) in vecchi.items():
            if k not in attivi:
                variazioni.insert(0, {"data": oggi, "nome": n, "tipo": "cessato", "da": gr})
    f.write_text(json.dumps({"aggiornato": ora(), "totale": len(attivi), "gruppi": elenco, "variazioni": variazioni[:40],
                             "link": URL_SENATO}, ensure_ascii=False, indent=1), "utf-8")
    return {"totale": len(attivi)}


PARTITI = [  # (etichette in italiano su Wikidata, sigla)
    (["Fratelli d'Italia"], "FdI"), (["Partito Democratico"], "PD"),
    (["Lega per Salvini Premier", "Lega"], "Lega"), (["Forza Italia"], "FI"),
    (["Movimento 5 Stelle"], "M5S"), (["Alleanza Verdi e Sinistra"], "AVS"),
    (["Azione"], "Az"), (["Italia Viva"], "IV"), (["Noi Moderati"], "NM"),
    (["+Europa"], "+Eu"), (["Futuro Nazionale"], "FN"),
]


def leggi_segretari():
    """Chi guida ogni partito (segretario/presidente) da Wikidata: incarichi senza data di fine."""
    etichette = {e: sig for lab, sig in PARTITI for e in lab}
    valori = " ".join(f'"{e}"@it' for e in etichette)
    q = f"""SELECT ?lab ?personaLabel WHERE {{
      VALUES ?lab {{ {valori} }}
      ?p rdfs:label ?lab ; wdt:P31/wdt:P279* wd:Q7278 ; wdt:P17 wd:Q38 .
      ?p p:P488 ?st . ?st ps:P488 ?persona .
      FILTER NOT EXISTS {{ ?st pq:P582 ?fine }}
      SERVICE wikibase:label {{ bd:serviceParam wikibase:language "it,en". }} }}"""
    r = requests.get("https://query.wikidata.org/sparql", params={"query": q, "format": "json"},
                     headers={"User-Agent": UA, "Accept": "application/sparql-results+json"}, timeout=60)
    r.raise_for_status()
    trovati = {}
    for b in r.json()["results"]["bindings"]:
        sig = etichette.get(b["lab"]["value"])
        nome = norm(b["personaLabel"]["value"])
        if sig and nome and not re.fullmatch(r"Q\d+", nome):
            trovati.setdefault(sig, [])
            if nome not in trovati[sig]:
                trovati[sig].append(nome)
    if len(trovati) < 6:
        raise ValueError(f"partiti con un capo trovati: {len(trovati)} su {len(PARTITI)}")
    nomi = {sig: lab[0] for lab, sig in PARTITI}
    (DATA / "partiti.json").write_text(json.dumps({
        "aggiornato": ora(), "fonte": "Wikidata",
        "partiti": [{"sigla": sig, "nome": nomi[sig], "guida": trovati[sig]} for _, sig in PARTITI if sig in trovati],
        "mancanti": [sig for _, sig in PARTITI if sig not in trovati]}, ensure_ascii=False, indent=1), "utf-8")
    return {"totale": len(trovati)}


BLOCCHI = {"camera": leggi_camera, "senato": leggi_senato, "governo": leggi_governo, "deputati": leggi_deputati, "senatori": leggi_senatori, "segretari": leggi_segretari}


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
            s.update({"ok": False, "ultimo_tentativo": ora(), "errore": f"{type(e).__name__}: {e}"[:700]})
            print(f"[errore] {nome}: {e}", file=sys.stderr)
    pa.write_text(json.dumps(auto, ensure_ascii=False, indent=1), "utf-8")
    ps.write_text(json.dumps(stato, ensure_ascii=False, indent=1), "utf-8")


if __name__ == "__main__":
    main()
