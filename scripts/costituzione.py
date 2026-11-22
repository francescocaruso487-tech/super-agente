#!/usr/bin/env python3
"""Scarica una volta il testo della Costituzione da Normattiva (Poligrafico dello Stato), seguendo la catena 'articolo successivo'."""
import html
import json
import re
import time
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parent.parent / "docs" / "data" / "costituzione.json"
BASE = "https://www.normattiva.it"
H = {"User-Agent": "Mozilla/5.0 (RassegnaBot uso personale)", "Accept-Language": "it"}


def main():
    s = requests.Session(); s.headers.update(H)
    s.get(BASE + "/uri-res/N2Ls?urn:nir:stato:costituzione:1947-12-27", timeout=30)
    url = "/atto/caricaArticolo?art.versione=1&art.idGruppo=1&art.flagTipoArticolo=0&art.codiceRedazionale=047U0001&art.idArticolo=1&art.idSottoArticolo=1&art.idSottoArticolo1=10&art.dataPubblicazioneGazzetta=1947-12-27%2000:00:00.0&art.progressivo=0&riferimenti=false&qId=&art.imUpdate=false"
    art, visti = {}, set()
    for _ in range(260):
        if url in visti:
            break
        visti.add(url)
        r = s.get(BASE + url, timeout=30)
        t = r.content.decode("utf-8", "replace")
        m = re.search(r'article-num-akn"[^>]*>\s*([^<]+?)\s*</h2>', t)
        b = re.search(r'art-just-text-akn">(.*?)</span>', t, re.S)
        if m and b:
            testo = re.sub(r"<br\s*/?>", "\n", b.group(1))
            testo = html.unescape(re.sub(r"<[^>]+>", "", testo))
            testo = "\n".join(x.strip() for x in testo.split("\n") if x.strip())
            art.setdefault(m.group(1).strip(), testo)
        nx = re.findall(r"showArticle\('([^']+)'\)", t)
        nx = [html.unescape(x).replace(" ", "%20") for x in nx if "idArticolo" in x]
        nx = [x for x in nx if x not in visti]
        if not nx:
            break
        url = nx[-1]
        time.sleep(0.2)
    print(len(art), list(art)[:3], list(art)[-3:])
    if len(art) >= 100:
        OUT.write_text(json.dumps({"fonte": "Normattiva (Istituto Poligrafico e Zecca dello Stato) - Costituzione della Repubblica italiana", "articoli": art}, ensure_ascii=False, indent=0), encoding="utf-8")
    else:
        raise SystemExit(f"solo {len(art)} articoli letti: non salvo")


if __name__ == "__main__":
    main()
