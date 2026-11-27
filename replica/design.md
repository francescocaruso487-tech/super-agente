# Design Rassegna: token e audit (27/11/2026)

## Token
Colori (chiaro): sfondo #f3f5f9, card #fff, testo #14213a, grigio #5a6880 (era #66748b), brand #111e34, accento #f07e26 (solo riempimenti), testo-accento #a94f0c (nuovo). Scuro: sfondo #0b1322, card #142038, testo #e8eef9, grigio #97a6bf.
Tipografia: system-ui, base 16px; tante misure (11-22 px, 17 valori diversi): da ridurre a una scala 12/14/16/18/22.
Raggi: 999 (chip), 12-16 (card), 22-26 (sheet). Spaziatura: 8/10/12/16.
Componenti: card con barra colore a sinistra, chip, accordion, sheet, bottone tondo 40px, nav in basso.

## Audit contrasto (WCAG AA 4,5:1)
Corretti in v66: grigio su sfondo chiaro 4,34 → 5,16; testo arancione su bianco 2,72 → 5,51 (22 usi); chiusura scheda 34 → 40 px.
Aperti: accento arancione come sfondo con testo bianco (2,72) dove presente; 10 testi a 11-11,5 px; emoji miste a icone SVG; scala dei corpi testo da unificare.
