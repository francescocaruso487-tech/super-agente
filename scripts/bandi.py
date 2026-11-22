#!/usr/bin/env python3
"""Rassegna - bandi e appalti pubblici in Campania (Caserta in evidenza).

Fonte ufficiale: TED (Tenders Electronic Daily), il giornale ufficiale degli appalti
dell'Unione europea (Ufficio delle pubblicazioni UE) - API pubblica, senza chiave.
Copre i bandi sopra soglia europea. Scrive docs/data/bandi.json e bandi_status.json.
Se la fonte non risponde o cambia formato NON si sovrascrive nulla.
"""
import html
import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "docs" / "data"
API = "https://api.ted.europa.eu/v3/notices/search"
PROVINCE = {"ITF31": "Caserta", "ITF32": "Benevento", "ITF33": "Napoli", "ITF34": "Avellino", "ITF35": "Salerno"}
CAMPI = ["publication-number", "notice-title", "buyer-name", "publication-date", "deadline-receipt-tender-date-lot",
         "place-of-performance", "notice-type", "estimated-value-lot"]


def ora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def testo(v):
    """I campi multilingua di TED sono {lingua: [testi]} oppure liste: prende l'italiano, poi l'inglese, poi il primo."""
    if v is None:
        return ""
    if isinstance(v, str):
        return v.strip()
    if isinstance(v, list):
        return testo(v[0]) if v else ""
    if isinstance(v, dict):
        for k in ("ita", "ITA", "it", "eng", "ENG", "en"):
            if k in v:
                return testo(v[k])
        return testo(next(iter(v.values()))) if v else ""
    return str(v)


def prima(v):
    if isinstance(v, list):
        return prima(v[0]) if v else ""
    return v


def valore(v):
    try:
        x = float(prima(v))
        return round(x) if x > 0 else None
    except (TypeError, ValueError):
        return None


def cerca_pagina(query, pagina, limite=250):
    return cerca(query, limite, pagina)


def cerca(query, limite=250, pagina=1):
    corpo = {"query": query, "fields": CAMPI, "limit": limite, "page": pagina, "scope": "ALL", "paginationMode": "PAGE_NUMBER"}
    r = requests.post(API, json=corpo, timeout=40, headers={"Accept": "application/json", "User-Agent": "RassegnaBot/1.0 (uso personale)"})
    if r.status_code != 200:
        raise RuntimeError(f"TED {r.status_code}: {r.text[:700]}")
    return r.json()


def main():
    stato = {"ultimo_tentativo": ora()}
    try:
        luoghi = " OR ".join(f"place-of-performance={c}" for c in PROVINCE)
        da = (datetime.now(timezone.utc) - timedelta(days=120)).strftime("%Y%m%d")
        oggi_q = datetime.now(timezone.utc).strftime("%Y%m%d")
        base = f"({luoghi}) AND buyer-country=ITA AND publication-date>={da} AND deadline-receipt-tender-date-lot>={oggi_q} AND (notice-type=cn-standard OR notice-type=cn-social OR notice-type=cn-desg)"
        try:
            dati = cerca(base)
        except RuntimeError:
            # se TED non accetta il filtro sulla scadenza, torno alla query senza e pagino
            base = base.replace(f" AND deadline-receipt-tender-date-lot>={oggi_q}", "")
            dati = cerca(base)
        notizie = list(dati.get("notices", []))
        totale = dati.get("totalNoticeCount") or len(notizie)
        pag = 2
        while len(notizie) < totale and pag <= 6:
            corpo = cerca_pagina(base, pag)
            nuove = corpo.get("notices", [])
            if not nuove:
                break
            notizie += nuove
            pag += 1
        (DATA / "debug_bandi.json").write_text(json.dumps({"totale": dati.get("totalNoticeCount"), "esempio": notizie[:2]}, ensure_ascii=False, indent=1), encoding="utf-8")
        if not notizie:
            raise RuntimeError("nessun bando restituito (formato cambiato o nessun bando attivo?)")
        out = []
        for n in notizie:
            num = prima(n.get("publication-number"))
            if not num:
                continue
            pl = n.get("place-of-performance") or []
            pl = pl if isinstance(pl, list) else [pl]
            prov = next((PROVINCE[c] for c in pl if c in PROVINCE), "Campania")
            titolo = testo(n.get("notice-title"))
            if not titolo:
                continue
            scad = prima(n.get("deadline-receipt-tender-date-lot")) or ""
            out.append({"id": num, "titolo": html.unescape(titolo)[:300], "ente": html.unescape(testo(n.get("buyer-name")))[:160], "provincia": prov,
                        "pubblicato": str(prima(n.get("publication-date")) or "")[:10], "scadenza": str(scad)[:10],
                        "importo": valore(n.get("estimated-value-lot")),
                        "link": f"https://ted.europa.eu/it/notice/-/detail/{num}"})
        oggi = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        out = [x for x in out if not x["scadenza"] or x["scadenza"] >= oggi]   # solo gare ancora aperte
        for x in out:
            x["titolo"] = re.sub(r"^Italia\s*[–-]\s*[^–]{3,80}?\s*[–-]\s*", "", x["titolo"]).strip() or x["titolo"]
        if not out:
            raise RuntimeError("nessun bando ancora aperto")
        out.sort(key=lambda x: (x["provincia"] != "Caserta", x["scadenza"] or "9999"))
        (DATA / "bandi.json").write_text(json.dumps({"aggiornato": ora(), "fonte": "TED - Gazzetta ufficiale degli appalti UE",
                                                       "totale": dati.get("totalNoticeCount", len(out)), "bandi": out}, ensure_ascii=False, indent=1), encoding="utf-8")
        stato.update({"ok": True, "ok_il": ora(), "letti": len(out)})
    except Exception as ex:  # noqa: BLE001
        stato.update({"ok": False, "errore": str(ex)[:1500]})
        print("ERRORE:", ex, file=sys.stderr)
    (DATA / "bandi_status.json").write_text(json.dumps(stato, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
