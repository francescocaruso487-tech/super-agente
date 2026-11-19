/* Link utili: portali di servizio e fonti, raggruppati. Si aprono con un tocco. */
(function () {
  const G = [
    ["Pratiche, catasto ed energia", [
      ["SISTER · Catasto e ipotecarie", "Visure, volture e ispezioni (accesso con le tue credenziali)", "https://sister.agenziaentrate.gov.it"],
      ["Agenzia delle Entrate", "Fisconline/Entratel, Fatture e Corrispettivi, guide sui bonus", "https://agenziaentrate.gov.it"],
      ["Impresa in un Giorno (SUAP)", "Pratiche per le attività produttive e modulistica", "https://impresainungiorno.gov.it"],
      ["GSE · Area Clienti", "Conto Termico, incentivi e rinnovabili", "https://gse.it"],
      ["ENEA · Efficienza energetica", "Detrazioni fiscali e trasmissione pratiche", "https://enea.it"],
      ["Registro Imprese · Telemaco", "Visure camerali e pratiche (InfoCamere)", "https://registroimprese.it"],
    ]],
    ["Lavoro, previdenza e sicurezza", [
      ["INPS", "Circolari, messaggi, DURC e contributi", "https://inps.it"],
      ["INAIL", "Sicurezza sul lavoro, bando ISI, CIVA", "https://inail.it"],
    ]],
    ["Norme e certificazioni", [
      ["UNI Store", "Norme UNI/ISO", "https://uni.com"],
      ["MyNorma · CEI", "Norme elettriche CEI", "https://ceinorme.it"],
      ["Gazzetta Ufficiale", "Atti dello Stato, ogni giorno", "https://www.gazzettaufficiale.it"],
      ["Normattiva", "Testi di legge aggiornati (vigenti)", "https://www.normattiva.it"],
      ["EUR-Lex", "Normativa dell'Unione Europea", "https://eur-lex.europa.eu/homepage.html?locale=it"],
    ]],
    ["Fisco e consulenza", [
      ["IPSOA", "Fisco, lavoro, bonus (Wolters Kluwer)", "https://ipsoa.it"],
      ["Eutekne.info", "Fisco e bonus edilizi", "https://eutekne.info"],
      ["Fisco e Tasse", "Guide fiscali", "https://fiscoetasse.com"],
    ]],
    ["Informazione tecnica, software e listini", [
      ["Edilportale", "Notizie e prodotti per l'edilizia", "https://edilportale.com"],
      ["Ediltecnico", "Normativa e news tecniche", "https://ediltecnico.it"],
      ["BibLus · ACCA", "Software e notizie tecniche", "https://acca.it"],
      ["Voltimum", "Impianti elettrici e prodotti", "https://voltimum.it"],
      ["ReteIngegneri", "Rete e news per ingegneri", "https://www.reteingegneri.it"],
      ["Il Portale del Tecnico", "Informazione per tecnici", "https://ilportaledeltecnico.it"],
      ["Tecnico Hub", "Portale tecnici", "https://tecnico-hub.com"],
      ["Edilnet", "Rete operativa edilizia", "https://edilnet.it"],
    ]],
    ["CAF, patronati e commercialisti", [
      ["Consulta Nazionale CAF", "Coordinamento dei CAF", "https://www.consultanazionalecaf.it"],
      ["CAF ACLI", "730, ISEE e servizi", "https://www.acli.it"],
      ["CAF CGIL", "Assistenza fiscale", "https://www.cafcgil.it"],
      ["CAF CISL", "Assistenza fiscale", "https://www.cafcisl.it"],
      ["CAF UIL", "Assistenza fiscale", "https://www.cafuil.it"],
      ["CNDCEC · Commercialisti", "Consiglio Nazionale", "https://www.commercialisti.it"],
      ["Consulenti del Lavoro", "Fondazione Studi e news", "https://www.consulentidellavoro.it"],
      ["Agenzia Entrate-Riscossione", "Cartelle, rottamazione e rate", "https://www.agenziaentrateriscossione.gov.it"],
    ]],
    ["Campania e Caserta", [
      ["Comune di Caserta", "Albo, urbanistica, SUE/SUAP", "https://www.comune.caserta.it"],
      ["BURC · Regione Campania", "Bollettino Ufficiale regionale", "https://burc.regione.campania.it"],
      ["Portale Sismica Campania", "Genio Civile: circolari e pratiche sismiche", "https://portalesismica.regione.campania.it"],
      ["Ordine Ingegneri Caserta", "Avvisi e comunicazioni dell'Ordine", "https://caserta.ordingegneri.it"],
    ]],
  ];
  const T = [
    ["Notizie tech", [
      ["HDblog", "Smartphone, tablet e PC", "https://www.hdblog.it"],
      ["Tom's Hardware Italia", "Hardware, recensioni e guide", "https://www.tomshw.it"],
      ["Punto Informatico", "Informatica, sicurezza e software", "https://www.punto-informatico.it"],
      ["Webnews", "Tecnologia e web", "https://www.webnews.it"],
      ["DDay.it", "Hardware e tecnologia", "https://www.dday.it"],
      ["AndroidWorld", "Android e app", "https://www.androidworld.it"],
      ["TuttoAndroid", "Android e smartphone", "https://www.tuttoandroid.net"],
      ["SamMobile", "Samsung Galaxy e One UI", "https://www.sammobile.com"],
    ]],
    ["Samsung e supporto", [
      ["Samsung Italia", "Prodotti, offerte e supporto", "https://www.samsung.com/it"],
      ["Samsung Members", "Aggiornamenti e assistenza", "https://www.samsung.com/it/support"],
    ]],
    ["Sicurezza e privacy", [
      ["ACN · Cybersicurezza", "Agenzia per la Cybersicurezza Nazionale", "https://www.acn.gov.it"],
      ["Garante Privacy", "Provvedimenti e news", "https://www.garanteprivacy.it"],
    ]],
    ["Offerte", [
      ["Amazon Offerte", "Offerte del giorno", "https://www.amazon.it/deals"],
      ["Trovaprezzi", "Confronto prezzi", "https://www.trovaprezzi.it"],
    ]],
  ];
  const POLITICA = [
    ["Istituzioni", [
      ["Quirinale", "Presidenza della Repubblica", "https://www.quirinale.it"],
      ["Governo", "Consiglio dei Ministri e comunicati", "https://www.governo.it"],
      ["Camera dei Deputati", "Lavori e votazioni", "https://www.camera.it"],
      ["Senato della Repubblica", "Lavori e votazioni", "https://www.senato.it"],
      ["Corte Costituzionale", "Sentenze e comunicati", "https://www.cortecostituzionale.it"],
      ["Parlamento europeo", "Notizie e plenarie", "https://www.europarl.europa.eu/italy/it/home"],
      ["Regione Campania", "Giunta e consiglio regionale", "https://www.regione.campania.it"],
    ]],
    ["Agenzie e informazione", [
      ["ANSA Politica", "Agenzia stampa", "https://www.ansa.it/sito/notizie/politica/politica.shtml"],
      ["Adnkronos", "Agenzia stampa", "https://www.adnkronos.com/politica"],
      ["AGI", "Agenzia Giornalistica Italia", "https://www.agi.it/politica/"],
      ["Il Post", "Notizie e approfondimenti", "https://www.ilpost.it"],
      ["Rai News", "Informazione pubblica", "https://www.rainews.it"],
      ["Il Mattino", "Napoli e Campania", "https://www.ilmattino.it"],
    ]],
  ];
  const AUTO = [
    ["Servizi e normativa", [
      ["ACI", "Bollo, PRA, passaggi di proprietà", "https://www.aci.it"],
      ["Portale dell'Automobilista", "Motorizzazione: patente e veicoli", "https://www.ilportaledellautomobilista.it"],
      ["IVASS · Preventivass", "Confronto RC auto", "https://www.ivass.it"],
      ["Euro NCAP", "Crash test e sicurezza", "https://www.euroncap.com/it"],
      ["UNRAE", "Immatricolazioni e mercato", "https://www.unrae.it"],
      ["Motus-E", "Mobilità elettrica e ricarica", "https://www.motus-e.org"],
    ]],
    ["Riviste e portali", [
      ["Quattroruote", "Novità, prove e listino", "https://www.quattroruote.it"],
      ["Motor1 Italia", "Notizie e prove", "https://it.motor1.com"],
      ["Alvolante", "Prove e guide", "https://www.alvolante.it"],
      ["Autoblog", "Novità e mercato", "https://www.autoblog.it"],
      ["OmniAuto", "Notizie auto", "https://www.omniauto.it"],
      ["Automoto", "Notizie e prove", "https://www.automoto.it"],
    ]],
    ["Moto, bici e motorsport", [
      ["Moto.it", "Moto e scooter", "https://www.moto.it"],
      ["Motociclismo", "Prove e novità moto", "https://www.motociclismo.it"],
      ["Bike Channel", "Bici ed e-bike", "https://www.bikechannel.it"],
      ["FIAB", "Bici e cicloturismo", "https://fiab-onlus.it"],
      ["MotoGP", "Campionato mondiale", "https://www.motogp.com/it"],
      ["FormulaPassion", "Formula 1", "https://www.formulapassion.it"],
      ["Autosprint", "Motorsport", "https://www.autosprint.it"],
    ]],
  ];
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  function render(q) {
    const box = document.querySelector("#lista-link"); if (!box) return;
    q = (q || "").trim().toLowerCase();
    let out = "";
    const nic = (function(){ try { return JSON.parse(localStorage.getItem('nicchia')) || 'edilizia'; } catch (e) { return localStorage.getItem('nicchia') || 'edilizia'; } })();
    for (const [titolo, voci] of ({ tech: T, politica: POLITICA, auto: AUTO }[nic] || G)) {
      const v = voci.filter(([n, d, u]) => !q || (n + " " + d + " " + u).toLowerCase().includes(q));
      if (!v.length) continue;
      out += `<div class="gruppo">${esc(titolo)}</div>` + v.map(([n, d, u]) =>
        `<a class="linkbox" href="${esc(u)}" target="_blank" rel="noopener"><b>${esc(n)}</b><span>${esc(d)}</span><i>↗</i></a>`).join("");
    }
    box.innerHTML = out || `<div class="vuoto"><b>Nessun link trovato</b></div>`;
  }
  document.addEventListener("DOMContentLoaded", () => {
    render("");
    const i = document.querySelector("#cerca-link");
    if (i) i.addEventListener("input", (e) => render(e.target.value));
    document.querySelectorAll("#nicchie button").forEach((b) => b.addEventListener("click", () => setTimeout(() => render(i ? i.value : ""), 0)));
  });
})();
