#!/usr/bin/env python3
"""Rassegna - atti ufficiali dalla Gazzetta Ufficiale (feed RSS ufficiali del Poligrafico).

Serie Generale (leggi, decreti), 1a Serie Speciale (Corte Costituzionale), 3a Serie Speciale (Regioni).
Accumula lo storico in docs/data/atti.json (120 giorni). Se la fonte non risponde non sovrascrive nulla.
"""
import html
import json
import os
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import requests

DATA = Path(__file__).resolve().parent.parent / "docs" / "data"
SERIE = {"SG": "Serie Generale", "S1": "Corte Costituzionale", "S3": "Regioni"}
H = {"User-Agent": "RassegnaBot/1.0 (uso personale)"}

# spiegazione fissa e verificabile per tipo di atto (non generata: descrive solo la natura giuridica)
TIPI = [
    (r"DECRETO-LEGGE", "Decreto d'urgenza del Governo: vale subito, ma il Parlamento deve convertirlo in legge entro 60 giorni."),
    (r"DECRETO LEGISLATIVO", "Norma con forza di legge emanata dal Governo su delega del Parlamento."),
    (r"^LEGGE REGIONALE|LEGGE REGIONALE", "Legge approvata dal Consiglio regionale: vale solo nel territorio della Regione."),
    (r"^LEGGE|\bLEGGE \d", "Legge approvata dal Parlamento."),
    (r"DECRETO DEL PRESIDENTE DEL CONSIGLIO", "Atto del Presidente del Consiglio: dà attuazione pratica a leggi e programmi del Governo."),
    (r"DECRETO DEL PRESIDENTE DELLA REPUBBLICA", "Atto firmato dal Presidente della Repubblica, in genere su proposta del Governo."),
    (r"REGOLAMENTO REGIONALE|DECRETO DEL PRESIDENTE DELLA GIUNTA", "Regolamento regionale: norma di dettaglio che attua una legge della Regione."),
    (r"DELIBERA", "Deliberazione di un organo pubblico (autorità, comitato, Regione): fissa regole o decisioni operative."),
    (r"SENTENZA", "La Corte Costituzionale ha deciso se una norma rispetta la Costituzione."),
    (r"ORDINANZA", "Provvedimento della Corte Costituzionale (o di altra autorità) che decide su una questione specifica."),
    (r"DECRETO", "Decreto ministeriale: applica una legge in modo concreto (procedure, importi, scadenze)."),
    (r"COMUNICATO", "Comunicazione ufficiale di un'amministrazione."),
]


def spiega(titolo):
    for pat, txt in TIPI:
        if re.search(pat, titolo.upper()):
            return txt
    return ""


def leggi(serie):
    r = requests.get(f"https://www.gazzettaufficiale.it/rss/{serie}", headers=H, timeout=30)
    r.raise_for_status()
    out = []
    for it in re.findall(r"<item>(.*?)</item>", r.text, re.S):
        g = lambda t: (re.search(rf"<{t}[^>]*>(.*?)</{t}>", it, re.S) or [None, ""])[1].strip()
        titolo, link, descr, pub = html.unescape(g("title")), g("link"), html.unescape(g("content:encoded")), g("pubDate")
        if not titolo or not link:
            continue
        try:
            d = parsedate_to_datetime(pub).astimezone(timezone(timedelta(hours=1))).strftime("%Y-%m-%d")
        except Exception:
            d = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        descr = re.sub(r"\s+", " ", descr).strip()
        descr = re.sub(r"\s*\(\d\dA\d{5}\)$|\s*\(\d\dR\d{5}\)$|\s*\(T-?\d+\)$", "", descr)
        out.append({"id": link.split("/eli/id/")[-1] if "/eli/id/" in link else link, "serie": serie,
                    "titolo": titolo, "descr": descr, "link": link.replace("http://", "https://"), "data": d,
                    "campania": bool(re.search(r"CAMPANIA", (titolo + " " + descr).upper())), "spiega": spiega(titolo)})
    return out


def main():
    f = DATA / "atti.json"
    vecchi = []
    if f.exists():
        try:
            vecchi = json.load(open(f, encoding="utf-8")).get("atti", [])
        except Exception:
            vecchi = []
    nuovi, errori = [], []
    for s in SERIE:
        try:
            nuovi += leggi(s)
        except Exception as e:
            errori.append(f"{s}: {str(e)[:80]}")
    if not nuovi:
        raise SystemExit("nessun atto letto: " + "; ".join(errori))
    noti = [a for a in nuovi if a["campania"] and a["id"] not in {v["id"] for v in vecchi}] if vecchi else []
    topic = os.environ.get("NTFY_TOPIC")
    for a in noti[:5]:
        if not topic:
            break
        try:
            requests.post("https://ntfy.sh", json={"topic": topic, "title": ("📍 " + (a["descr"] or a["titolo"]))[:140],
                "message": a["titolo"][:200] + " — Gazzetta Ufficiale", "click": a["link"], "priority": 3}, timeout=20)
        except Exception:
            pass
    per_id = {a["id"]: a for a in vecchi}
    per_id.update({a["id"]: a for a in nuovi})
    limite = (datetime.now(timezone.utc) - timedelta(days=120)).strftime("%Y-%m-%d")
    atti = sorted((a for a in per_id.values() if a["data"] >= limite), key=lambda a: (a["data"], a["id"]), reverse=True)[:600]
    (DATA / "atti.json").write_text(json.dumps({"aggiornato": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fonte": "Gazzetta Ufficiale della Repubblica Italiana", "atti": atti}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(len(nuovi), "letti,", len(atti), "totali", errori)


if __name__ == "__main__":
    main()
