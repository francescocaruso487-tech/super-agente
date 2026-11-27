# Recon: Rassegna (PWA personale)

**Scopo.** Mappa completa di Rassegna (docs/ su GitHub Pages, https://francescocaruso487-tech.github.io/super-agente/), usata come base per test, grafica e piano di miglioramenti.
**Nota di metodo.** Qui l'"originale" è l'app stessa dell'utente: schermate, codice e dati sono suoi. Nessuna app di terzi è stata copiata. Il confronto con app simili (Almanacco, lettori di notizie) viene dopo, da fonti pubbliche, in `replica-entrepreneur`.
**Piattaforma:** web mobile installabile (PWA, Samsung S25 Ultra). **Uso:** personale, costo zero. **Slice:** tutta l'app.

## Fonti
| fonte | cosa dà |
| --- | --- |
| https://github.com/francescocaruso487-tech/super-agente (docs/app.js, 1001 righe) | schermate, stato, flussi |
| docs/data/*.json | modello dati reale |
| .github/workflows/*.yml, scripts/*.py | pipeline di aggiornamento |
| sources.json (489 fonti), aree.json | elenco fonti e tassonomia |
| replica/screens/*.png (16 viste, 412x915) | riferimento visivo |

## Idea di base (core loop)
L'utente apre l'app → sceglie una delle 4 nicchie → vede le notizie raggruppate (per professione o argomento) → apre una scheda → va alla fonte. In più: una pagina "Oggi" (almanacco) e sezioni di dati ufficiali (bandi, atti, voti).

## Schermate (S)
| ID | schermata | come ci si arriva | scopo | componenti principali | stati visti |
| --- | --- | --- | --- | --- | --- |
| S01 | Guscio | sempre | titolo, ora ultimo aggiornamento, 🎨, ricarica, box Oggi, 4 nicchie, barra in basso | header, oggi-box, nicchie, bottom nav | caricamento, aggiornato |
| S02 | Professioni › Per professione | Professioni › Novità | notizie per professione (8 gruppi, 14+ professioni) | accordion, card notizia, switch "Solo novità normative" | chiuso, aperto |
| S03 | Professioni › Per argomento | chip | notizie per area/sotto-area | chip, accordion | idem |
| S04 | Bandi (Caserta/Campania) | chip 🏗️ Bandi | gare aperte da TED | card bando, scadenza, importo | con dati; vuoto non visto |
| S05 | Atti (Gazzetta Ufficiale) | chip 📜 Atti | atti con filtro Campania/serie | chip filtro, card atto | con dati |
| S06 | Salvate | chip ★ | notizie salvate (stella) | card | vuoto (0) visto |
| S07 | Archivio | tab Archivio | ricerca testuale + chip aree + "Mostra altre" | input ricerca, chip, lista paginata | iniziale |
| S08 | Link | tab Link | link utili con ricerca | input, lista link | da verificare |
| S09 | Fonti | tab Fonti | stato delle 283 fonti attive, errori, metodo | riepilogo, card fonte con pallino colore | con dati |
| S10 | Tecnologia › Novità | nicchia Tecnologia | notizie per area (Sicurezza, Smartphone, AI, Offerte...) | accordion | idem |
| S11 | Politica › Notizie | nicchia Politica | 7 aree (Governo, Partiti, Economia, UE, Esteri, Giustizia, Regioni) | accordion | idem |
| S12 | Politica › Quadro politico | chip 🏛️ | emiciclo Camera, governo, Campania, voti, proposte | grafico a emiciclo, schede voto/proposta | con dati |
| S13 | Politica › Atti ufficiali | chip 📜 | atti GU per la politica | come S05 | con dati |
| S14 | Motori › Notizie | nicchia Motori | 8+ aree (Novità, Elettriche, Mercato, Normativa, Richiami, Prove, Tecnica, Moto) | accordion | idem |
| S15 | Motori › Offerte e momento | chip 💸 | semaforo "è il momento di comprare", offerte, confronto modelli, calcolo costi | card semaforo, tabella costi, strumenti | da verificare a fondo |
| S16 | Oggi (Almanacco) | box "Oggi" | pagina a tutto schermo, 18 sezioni a tendina, giorno ±7 | accordion, frecce, avviso dati vecchi | tutte chiuse (default) |
| S17 | Scheda notizia | tocco su card | In breve, chip, utile per, dettagli, correlate, immagine | sheet, chip, bottoni | con/senza anteprima |
| S18 | Scheda bando | tocco | scadenza, importo, ente, procedura, CPV | sheet, riga info | con dati |
| S19 | Scheda atto | tocco | descrizione, ente, tipo | sheet | con dati |
| S20 | Scheda voto | tocco in S12 | esito per gruppi | sheet, barre | con dati |
| S21 | Scheda proposta | tocco in S12 | stato proposta di legge | sheet | con dati |
| S22 | Come verifichiamo | tocco su affidabilità | spiegazione del metodo | sheet | testo |
| S23 | Colori e tema | 🎨 | chiaro/scuro/auto, tinta, colori dallo sfondo | sheet, slider, file | con dati |

Non ancora aperte a fondo (da coprire in `replica-test`): S08, S15 (calcolo costi), S20, S21, S23.

## Flussi (F)
- **F01 Vedere le novità.** S01 → S02. Click: 0 per la lista, 1 per aprire un gruppo.
- **F02 Leggere una notizia.** S01 → (nicchia) → apri gruppo → tocca card → S17 → "Apri la fonte". **4 click.**
- **F03 Salvare e ritrovare.** S17 → ☆ Salva → S02/S03 → chip ★ Salvate. 3 click per ritrovarla.
- **F04 Cercare.** S07 → scrivi → chip area → "Mostra altre". Limite: cerca solo nelle notizie già caricate.
- **F05 Gare.** S04 → card → S18 → avviso TED. 3 click. Casi limite: nessuna gara aperta, scadenza passata (nascoste).
- **F06 Atti.** S05 → filtro → S19 → Gazzetta.
- **F07 Oggi.** box Oggi → S16 → apri sezione → (giorno ±). Dati aggiornati ogni 2 ore; avviso se più vecchi di 14 ore.
- **F08 Capire un voto.** S12 → scheda voto S20 → atto in Parlamento.
- **F09 Auto.** S14 → S15 → confronto/calcolo costi → offerte.
- **F10 Cambiare tema.** 🎨 → S23 → Fatto.
- **F11 Notifica.** (fuori app) ntfy: offerte auto, atti Campania, riepilogo 07:30 → apre l'app.
- **F12 Aggiornare.** ↻ → ricarica dati; aggiorna automaticamente quando l'app torna in primo piano.
- **F13 Offline.** service worker, ultimi dati salvati.

## Componenti
Card notizia (titolo, fonte, età, pallino affidabilità) · accordion (gruppo, sezione Almanacco) · chip (nicchie, aree, filtri) · sheet a scorrimento (S17–S23) · riga info `pRiga` · bottone primario/secondario `pBtn` · switch · input di ricerca · bottom nav con icone SVG · box "Oggi" (gradiente) · emiciclo SVG · semaforo auto · pulsante tondo (🎨, ↻) · avviso `alm-avviso` · badge/pillole.
Varianti e stati: chiaro/scuro/auto, tinta personalizzabile.

## Modello dati (dedotto dai JSON reali, confidenza alta)
- **Notizia** (6000, 4,8 MB): id, titolo, link, fonte, fonte_nome, tipo (ufficiale|ente|ordine|stampa), aree[], sotto[], normativa, sintesi, pubblicata?, visto, metodo (rss|scraping|gnews|ufficiale), luogo, nicchia, prof[], prezzo?, tradotto?, altre_fonti[].
- **Anteprima** (per id notizia): desc, autore, sezione, tag[], parole, img, v.
- **Bando**: id, titolo, ente, provincia, pubblicato, scadenza, importo, natura, cpv, procedura, link.
- **Atto**: id, serie, titolo, descr, link, data, campania, spiega.
- **Giorno Almanacco** (8 giorni): festività, astro, santi, vangelo/letture, accadde, nati, morti, costituzione, frase, latino, latparola, parola, modo, comune.
- **Politica**: governo, camera (gruppi/emiciclo), campania, votazioni, proposte, partiti, deputati.
- **Auto**: confronto modelli, ipotesi costi, profilo utente.
- **Fonte/stato**: 489 fonti (283 attive), esito ultimo controllo, errori.
- **Stato utente** (solo sul telefono, localStorage + IndexedDB): stelle, tema, scelte di vista.
Problema noto: ~2300 notizie senza data (scraping), in recupero.

## Pipeline
6 workflow GitHub Actions: aggiorna (3 volte/ora), politica (ogni 4 h), bandi (6 h), atti (3 h), almanacco (2 h), riepilogo (07:30). Backend: Python (feedparser, requests, ephem). Dati in `docs/data/` pubblicati con l'app. Notifiche: ntfy.sh (secret NTFY_TOPIC).

## Cosa non si può replicare / limiti
`skip`: testi CEI di Vangelo e letture (diritti), immagini e articoli dei giornali (solo link e anteprime), BURC Campania e albi dei Comuni (non leggibili in modo affidabile), gare sotto soglia europea (TED non le ha), "dichiarazioni vs voti" dei politici (non automatizzabile in modo affidabile).

## Osservazioni emerse (da passare a replica-test e replica-design)
1. Una risorsa dà 404 all'apertura (da trovare).
2. Chip "Altro 0" in Politica e gruppi con 1 sola notizia (es. "Maestranze e operatori 1"): rumore.
3. Barra in basso copre l'ultimo elemento delle liste (serve spazio sotto).
4. Nella nicchia Tecnologia/Motori la barra "Per professione/Bandi/Atti" resta nel DOM nascosta: verificare che non intercetti tocchi.
5. Nella scheda Fonti le etichette tecniche ("indiretta via Google News", "metodo approssimativo") sono poco comprensibili.
6. Emoji miste a icone SVG: stile non uniforme.
7. app.js è un file unico di ~1000 righe: manutenzione difficile.

## Dimensione
- Schermate: 23 (12 di navigazione + 7 sheet + guscio + Oggi + tema). Flussi: 13. Entità: 9.
- Parti difficili: (1) pipeline di 489 fonti con scraping fragile e date mancanti; (2) dati politici dalla Camera (formati aperti ma instabili); (3) notifiche push senza server (solo ntfy).
- Taglia complessiva già costruita: **L**. Miglioramenti previsti: **M**.

Prossimo passo: `/replica-test` e `/replica-design`, poi `/replica-entrepreneur`.
