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


BLOCCHI = {"camera": leggi_camera, "senato": leggi_senato, "governo": leggi_governo}


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
