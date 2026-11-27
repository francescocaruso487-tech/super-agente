# Test Rassegna (27/11/2026, Chrome 412x915, service worker disattivato)

Script: `replica/test/e2e.py` (fumo, tab, errori) e `replica/test/flussi.py` (nicchie, schede, ricerca, Almanacco).

## Esito
- 4 tab in basso: ok, nessun overflow orizzontale.
- 4 nicchie: ok; in ognuna si apre un gruppo, compaiono le card e la scheda si apre con "Apri" e "Salva". 25 card visibili per nicchia.
- Almanacco: 19 sezioni, tutte chiuse all'apertura (come richiesto).
- Ricerca Archivio: ok (CILA 1, superbonus 5, bonus 40); "nessun risultato" mostrato.
- Errori JavaScript: 0.

## Bug trovati
| # | gravità | cosa | stato |
| --- | --- | --- | --- |
| 1 | bassa | 404 a ogni avvio: l'app chiedeva `data/senatori.json`, mai generato (`leggi_senatori` non è collegata) | corretto in v65 |
| 2 | bassa | La sezione "Partiti e senatori" non appare mai (codice presente, dati assenti) | aperto: collegare `leggi_senatori` in politica.py o togliere la sezione |
| 3 | nota | L'Archivio cerca solo nella nicchia attiva: chi cerca "superbonus" da Motori trova 0 senza spiegazione | da valutare: mostrare "cerchi solo in Motori" o cercare ovunque |
| 4 | nota | Gruppi con 1-2 notizie (Agronomo 1, Chimico 2, Biologo 1) occupano una riga ciascuno: rumore | design |

## Non coperto
Notifiche ntfy, installazione PWA, offline, calcolo costi auto, tema colori da file, Bandi/Atti con dati reali (richiedono rete o interazione su telefono).
