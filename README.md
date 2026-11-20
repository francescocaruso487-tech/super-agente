# Rassegna

App personale (installabile su Android) che segue ogni giorno le novità normative e tecniche
in **edilizia e ingegneria**: titoli abilitativi, antincendio, catasto, strutture, impianti/energia,
capannoni, Europa.

## Come funziona
- `sources.json` – registro di tutte le fonti (ufficiali, enti, ordini, stampa tecnica).
- `aree.json` – aree seguite e parole chiave del filtro (gratuito, senza IA).
- `scripts/fetch.py` – ogni ora legge le fonti, smista le notizie, aggiorna `docs/data/` e manda le notifiche.
- `docs/` – l'app (PWA) pubblicata con GitHub Pages.
- Notifiche push con [ntfy](https://ntfy.sh) (gratuito); riepilogo ogni mattina.

## Impostazione (una volta sola)
1. **Pages**: Settings → Pages → Source: *Deploy from a branch* → `main` / `/docs`.
2. **Notifiche**: installa l'app *ntfy* da Play Store, iscriviti a un argomento con nome lungo e casuale,
   poi Settings → Secrets and variables → Actions → New secret: `NTFY_TOPIC` = quel nome.
3. **Facoltativo (IA)**: secret `ANTHROPIC_API_KEY`: riassume solo le novità normative (max 15 per ora).
   Senza chiave il costo è zero e si usa la sintesi fornita dalle fonti.
4. Apri `https://<utente>.github.io/super-agente/` con Chrome sul telefono → menu ⋮ → *Installa app*.

## Aggiungere o correggere una fonte
Modifica `sources.json` (campo `feed` per un RSS noto, `lista` per la pagina elenco). La scheda
**Fonti** dell'app mostra per ognuna se è attiva, letta in modo approssimativo o non raggiungibile.
