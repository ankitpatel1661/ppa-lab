"""Texts of the dashboard in English, German and Italian (app/streamlit_app.py).

Short labels go through `translator(lang)`: the English text is the key, `DE` and `IT` hold the
translations. Templates keep their {placeholders}; numbers are formatted with `number`, which
writes German and Italian decimals ("21,4"). Longer explanations are per-language dicts with
the same keys. Tests check that every label the app translates has a version in each language
with the same placeholders.
"""

from __future__ import annotations

from collections.abc import Callable

LANGS = {"en": "English", "de": "Deutsch", "it": "Italiano"}


def number(x: float, digits: int = 1, lang: str = "en", sign: bool = False) -> str:
    """12345.678 -> "12,345.7" (en) or "12.345,7" (de, it); a real minus sign; optional "+"."""
    text = f"{x:{'+' if sign else ''},.{digits}f}".replace("-", "−")
    if lang != "en":
        text = text.translate(str.maketrans({",": ".", ".": ","}))
    return text


def percent(x: float, digits: int = 0, lang: str = "en", sign: bool = False) -> str:
    """0.774 -> "77%" (en, it) or "77 %" (de, with a narrow no-break space)."""
    return number(100 * x, digits, lang, sign) + ("\u202f%" if lang == "de" else "%")


MISSING: set[str] = set()   # a translation asked for but not there; the tests keep it empty


def translator(lang: str) -> Callable[[str], str]:
    """The label in the chosen language; English is the key and the fallback."""
    table = TRANSLATIONS.get(lang)
    if table is None:
        return lambda text: text

    def translate(text: str) -> str:
        if text not in table:
            MISSING.add(text)
        return table.get(text, text)

    return translate


# --------------------------------------------------------------------------- #
# Short labels and templates (English key -> German)
# --------------------------------------------------------------------------- #
DE: dict[str, str] = {
    # sidebar
    "Your assumptions": "Ihre Annahmen",
    "Language": "Sprache",
    "Park": "Park",
    "Solar park · Borrentin · 114 MWp": "Solarpark · Borrentin · 114 MWp",
    "Wind park · Everswinkel · 28.5 MW": "Windpark · Everswinkel · 28,5 MW",
    "Which past represents the delivery year?": "Welche Vergangenheit steht für das Lieferjahr?",
    "Last 12 months (base case)": "Letzte 12 Monate (Basisfall)",
    "Whole 2024-2026 window": "Gesamter Zeitraum 2024-2026",
    "Negative prices": "Negative Preise",
    "Paid for every MWh (base case)": "Jede MWh wird bezahlt (Basisfall)",
    "Clause: we stop producing and are not paid": "Klausel: Abregelung, keine Vergütung",
    "Shift of the forward curve (%)": "Verschiebung der Terminkurve (%)",
    "Solar and storage build-out after {start}": "Zubau von Solar und Speichern nach {start}",
    "Capture-rate trend (pp per year)": "Trend der Capture Rate (Prozentpunkte pro Jahr)",
    "Tenor (years)": "Laufzeit (Jahre)",
    "Discount rate (%)": "Diskontsatz (%)",
    "Output degradation (% per year)": "Degradation der Erzeugung (% pro Jahr)",
    "Balancing and route to market (EUR/MWh)": "Ausgleichsenergie und Vermarktung (EUR/MWh)",
    "Credit and liquidity (EUR/MWh)": "Kredit und Liquidität (EUR/MWh)",
    "Defaults = the Step 7 base case (config/project.toml).":
        "Voreinstellungen = Basisfall aus Schritt 7 (config/project.toml).",
    "{name}: solar +{pv} GW, storage +{storage} GWh a year":
        "{name}: Solar +{pv} GW, Speicher +{storage} GWh pro Jahr",
    "Central": "Zentral",
    "Recent pace": "Aktuelles Tempo",
    "EEG solar target pace": "EEG-Ausbaupfad Solar",
    "Storage boom": "Speicherboom",
    "Slowdown": "Verlangsamung",
    "{name} (base case)": "{name} (Basisfall)",
    # page head
    "What fixed price for a renewable PPA, and how much risk is left?":
        "Welcher Festpreis für ein Erneuerbaren-PPA, und wie viel Risiko bleibt?",
    "ppa-lab {version} · German day-ahead prices, 31 ERA5 weather years, {n} joint scenarios "
    "for {start} · illustrative analysis from public data, not an offer":
        "ppa-lab {version} · deutsche Day-Ahead-Preise, 31 ERA5-Wetterjahre, {n} gemeinsame "
        "Szenarien für {start} · illustrative Analyse aus öffentlichen Daten, kein Angebot",
    "Negative-price clause: the park stops producing at negative prices ({share} of its output "
    "in {start}, more at lower forwards) and is not paid for it, so it keeps what a plain PPA "
    "loses ({value} EUR per MWh of output in {start}). Prices are per delivered MWh; per MWh of "
    "output the indicative price is about {per_output}.":
        "Klausel für negative Preise: Der Park regelt bei negativen Preisen ab ({share} seiner "
        "Erzeugung in {start}, mehr bei niedrigeren Terminpreisen) und wird dafür nicht bezahlt. "
        "So behält er, was ein einfaches PPA verschenkt ({value} EUR je MWh Erzeugung in "
        "{start}). Die Preise gelten je gelieferter MWh; je MWh Erzeugung liegt der indikative "
        "Preis bei etwa {per_output}.",
    # headline numbers
    "Indicative price": "Indikativer Preis",
    "Fair price, {tenor} years": "Fairer Preis, {tenor} Jahre",
    "Fair price, {start}": "Fairer Preis, {start}",
    "Risk premium": "Risikoprämie",
    "Cash flow at risk": "Cashflow at Risk",
    "EUR/MWh": "EUR/MWh",
    "EUR per delivered MWh": "EUR je gelieferter MWh",
    "{unit} over {tenor} years; {delta} vs the base case":
        "{unit} über {tenor} Jahre; {delta} ggü. dem Basisfall",
    "{unit}, before the risk premium and costs": "{unit}, vor Risikoprämie und Kosten",
    "{unit}: forward {forward} × capture rate {capture}":
        "{unit}: Terminpreis {forward} × Capture Rate {capture}",
    "EUR/MWh after a baseload hedge ({unhedged} without)":
        "EUR/MWh nach Absicherung mit Baseload ({unhedged} ohne)",
    "EUR m a year with the PPA; {merchant} if merchant ({cut})":
        "Mio. EUR pro Jahr mit PPA; {merchant} am Spotmarkt ({cut})",
    # tabs
    "From forward to offer": "Vom Terminpreis zum Angebot",
    "Risk by structure": "Risiko je Struktur",
    "Hedging": "Absicherung",
    "How it was built": "Wie es gebaut wurde",
    "Method and glossary": "Methode und Glossar",
    # price tab
    "This park is paid under the EEG: spot plus a monthly put on the onshore market value at "
    "its award value ({award} EUR/MWh, assumed; the award is not published). Over {years} years "
    "that pays about {net} EUR/MWh after the marketing fee, against {ppa} for the PPA at the "
    "base case: the PPA here is a what-if (Step 7 report, section 6).":
        "Dieser Park wird nach dem EEG vergütet: Spotmarkt plus ein monatlicher Put auf den "
        "Marktwert Wind an Land zum anzulegenden Wert ({award} EUR/MWh, angenommen; der Wert ist "
        "nicht veröffentlicht). Über {years} Jahre bringt das rund {net} EUR/MWh nach der "
        "Vermarktungsgebühr, gegenüber {ppa} für das PPA im Basisfall: Das PPA ist hier ein "
        "Was-wäre-wenn (Bericht zu Schritt 7, Abschnitt 6).",
    "The price, layer by layer": "Der Preis, Schicht für Schicht",
    "Layer": "Schicht",
    "What it means": "Bedeutung",
    "Forward {start}": "Terminpreis {start}",
    "The market price of a flat block of power in {start}":
        "Der Marktpreis für ein gleichmäßiges Strom-Band in {start}",
    "Shape": "Profil",
    "The park produces more when power is cheap: its capture rate is {capture}":
        "Der Park erzeugt mehr, wenn Strom billig ist: Seine Capture Rate beträgt {capture}",
    "Fair price {start}": "Fairer Preis {start}",
    "Break-even price for {start}: what the output is worth at market prices":
        "Break-even-Preis für {start}: Was die Erzeugung zu Marktpreisen wert ist",
    "Later years": "Spätere Jahre",
    "The forward curve, the capture rate at each year's price level":
        "Die Terminkurve, die Capture Rate beim Preisniveau des jeweiligen Jahres",
    ", the build-out scenario": ", das Zubauszenario",
    ", degradation and discounting": ", Degradation und Diskontierung",
    "One fixed price that is fair over the whole contract":
        "Ein Festpreis, der über die gesamte Laufzeit fair ist",
    "The buyer's charge for profile and volume risk it cannot hedge":
        "Der Aufschlag des Käufers für Profil- und Mengenrisiko, das er nicht absichern kann",
    "Balancing, credit": "Ausgleichsenergie, Kredit",
    "Forecast errors at the imbalance price, marketing fee; credit and capital":
        "Prognosefehler zum Ausgleichsenergiepreis, Vermarktungsgebühr; Kredit und Kapital",
    "What a buyer could accept: the bottom of the negotiation range":
        "Was ein Käufer akzeptieren könnte: die Untergrenze der Verhandlungsspanne",
    "Year by year": "Jahr für Jahr",
    "Why the capture rate is {capture}": "Warum die Capture Rate {capture} beträgt",
    "Daily shape": "Tagesprofil",
    "Seasons": "Jahreszeiten",
    "Weather": "Wetter",
    "Capture rate": "Capture Rate",
    "What moves the price": "Was den Preis bewegt",
    "Solar and storage build-out": "Zubau von Solar und Speichern",
    "Storage decides solar's later years: only a storage boom keeps the capture rate close to "
    "flat.":
        "Speicher entscheiden über die späteren Solarjahre: Nur ein Speicherboom hält die "
        "Capture Rate annähernd stabil.",
    "Volume": "Menge",
    "P50 energy (GWh a year)": "P50-Erzeugung (GWh pro Jahr)",
    "P90, one year (GWh)": "P90, ein Jahr (GWh)",
    "Expected energy P50 {p50} GWh a year; one year in ten below {p90} GWh (P90). Premium and "
    "costs per MWh of the first year apply to every year.":
        "Erwartete Erzeugung P50 {p50} GWh pro Jahr; in einem von zehn Jahren unter {p90} GWh "
        "(P90). Prämie und Kosten je MWh des ersten Jahres gelten für jedes Jahr.",
    # charts
    "Forward\n{start}": "Terminpreis\n{start}",
    "Fair price\n{start}": "Fairer Preis\n{start}",
    "Fair price\n{tenor} years": "Fairer Preis\n{tenor} Jahre",
    "Balancing": "Ausgleich",
    "Credit": "Kredit",
    "Indicative\n{tenor} years": "Indikativ\n{tenor} Jahre",
    "Forward (baseload)": "Terminpreis (Baseload)",
    "Fair price of the park's output": "Fairer Preis der Erzeugung des Parks",
    "Average price by hour of day ({start} scenarios)":
        "Durchschnittspreis je Tagesstunde (Szenarien {start})",
    "Average price {value}": "Durchschnittspreis {value}",
    "What the park earns {value}": "Was der Park erlöst {value}",
    "Average output (MW)": "Durchschnittliche Erzeugung (MW)",
    "Hour of day": "Tagesstunde",
    # tables: columns
    "Year": "Jahr",
    "Forward (EUR/MWh)": "Terminpreis (EUR/MWh)",
    "Fair price (EUR/MWh)": "Fairer Preis (EUR/MWh)",
    "Energy (MWh)": "Erzeugung (MWh)",
    "Discount factor": "Diskontfaktor",
    "Change": "Änderung",
    "Indicative (EUR/MWh)": "Indikativ (EUR/MWh)",
    "vs yours (EUR/MWh)": "ggü. Ihrem Fall (EUR/MWh)",
    "Scenario": "Szenario",
    "Solar added (GW a year)": "Solarzubau (GW pro Jahr)",
    "Storage added (GWh a year)": "Speicherzubau (GWh pro Jahr)",
    "Capture-rate fall (% a year)": "Rückgang der Capture Rate (% pro Jahr)",
    "Strike (EUR/MWh)": "Strike (EUR/MWh)",
    "CFaR 95% (EUR m)": "CFaR 95 % (Mio. EUR)",
    "Expected (EUR m)": "Erwartet (Mio. EUR)",
    "Bad year, P5 (EUR m)": "Schlechtes Jahr, P5 (Mio. EUR)",
    "Output paid (%)": "Bezahlte Erzeugung (%)",
    "MW sold": "Verkaufte MW",
    "Hedge ratio (%)": "Hedge-Quote (%)",
    "CFaR95 (EUR m)": "CFaR95 (Mio. EUR)",
    "CFaR cut (%)": "CFaR-Senkung (%)",
    "Variance removed (%)": "Entfernte Varianz (%)",
    "spot": "Spot",
    # tables: rows
    "Forward curve −10%": "Terminkurve −10 %",
    "Forward curve +10%": "Terminkurve +10 %",
    "Capture-rate trend −1 pp a year": "Trend der Capture Rate −1 Pp. pro Jahr",
    "Capture-rate trend +1 pp a year": "Trend der Capture Rate +1 Pp. pro Jahr",
    "Discount rate +2 pp": "Diskontsatz +2 Pp.",
    "Discount rate −2 pp": "Diskontsatz −2 Pp.",
    "Balancing and credit +1 EUR/MWh": "Ausgleich und Kredit +1 EUR/MWh",
    "Build-out: {name}": "Zubau: {name}",
    "Merchant, curtailing at negative prices": "Spotmarkt, Abregelung bei negativen Preisen",
    "Merchant, producing at negative prices": "Spotmarkt, Erzeugung bei negativen Preisen",
    "Pay-as-produced PPA": "Pay-as-produced-PPA",
    "Pay-as-produced, negative-price clause": "Pay-as-produced mit Klausel für negative Preise",
    "Pay-as-produced, buyer curtails, deemed output paid":
        "Pay-as-produced, Käufer regelt ab, fiktive Erzeugung bezahlt",
    "Merchant + floor at 0 (premium paid)": "Spotmarkt + Floor bei 0 (Prämie bezahlt)",
    "Baseload PPA": "Baseload-PPA",
    "No hedge (merchant)": "Keine Absicherung (Spotmarkt)",
    "Cal base, 50% of average output": "Cal Base, 50 % der mittleren Erzeugung",
    "Cal base, 100% of average output": "Cal Base, 100 % der mittleren Erzeugung",
    "Cal base, minimum-variance": "Cal Base, minimale Varianz",
    "Quarters, minimum-variance": "Quartale, minimale Varianz",
    "Months, minimum-variance": "Monate, minimale Varianz",
    # risk tab
    "What each structure leaves with the producer ({start}, fair strikes)":
        "Was jede Struktur beim Erzeuger lässt ({start}, faire Strikes)",
    "What each structure means": "Was die Strukturen bedeuten",
    "The buyer's risk premium": "Die Risikoprämie des Käufers",
    "Without a hedge (EUR/MWh)": "Ohne Absicherung (EUR/MWh)",
    "After a baseload hedge (EUR/MWh)": "Nach Baseload-Absicherung (EUR/MWh)",
    "of which profile (EUR/MWh)": "davon Profil (EUR/MWh)",
    "of which volume (EUR/MWh)": "davon Menge (EUR/MWh)",
    "The buyer of a pay-as-produced PPA asks for **{joint} EUR/MWh** after selling a baseload "
    "forward; without the hedge it would be {unhedged}, but most of that is the price level, "
    "which the buyer can hedge almost for free. {tech}'s remaining risk is mostly **{kind}**.":
        "Der Käufer eines Pay-as-produced-PPA verlangt **{joint} EUR/MWh**, nachdem er ein "
        "Baseload-Termingeschäft verkauft hat; ohne Absicherung wären es {unhedged}, doch das "
        "meiste davon ist das Preisniveau, das der Käufer fast kostenlos absichern kann. Das "
        "verbleibende Risiko von {tech} ist vor allem **{kind}**.",
    "Solar": "Solar",
    "Wind": "Wind",
    "profile": "Profilrisiko",
    "volume": "Mengenrisiko",
    "Output at negative prices, {start}": "Erzeugung bei negativen Preisen, {start}",
    "Value of stopping (EUR per MWh of output)": "Wert der Abregelung (EUR je MWh Erzeugung)",
    "Clause, 10 years (EUR per delivered MWh)": "Klausel, 10 Jahre (EUR je gelieferter MWh)",
    # hedging tab
    "No hedging results yet: run `ppa-lab hedging` and `ppa-lab memo` (Step 8).":
        "Noch keine Ergebnisse zur Absicherung: `ppa-lab hedging` und `ppa-lab memo` ausführen "
        "(Schritt 8).",
    "If the park sold at spot: merchant risk by futures hedge ({start})":
        "Wenn der Park am Spotmarkt verkauft: Risiko je Futures-Absicherung ({start})",
    "MW sold: futures sold, as a year-average MW. Hedge ratio = MW sold / the park's average "
    "output. CFaR95 = expected revenue minus its 5% quantile.":
        "Verkaufte MW: verkaufte Futures als Jahresmittel in MW. Hedge-Quote = verkaufte MW / "
        "mittlere Erzeugung des Parks. CFaR95 = erwarteter Erlös minus sein 5-%-Quantil.",
    "Selling **{ratio} of the average output** as Cal base futures cuts the merchant cash flow "
    "at risk by **{cut}**. The PPA buyer's premium falls from {full} to {best} EUR/MWh with the "
    "minimum-variance hedge ({buyer_ratio} of the average output).":
        "Der Verkauf von **{ratio} der mittleren Erzeugung** als Cal-Base-Futures senkt den "
        "Cashflow at Risk am Spotmarkt um **{cut}**. Die Prämie des PPA-Käufers sinkt mit der "
        "Absicherung minimaler Varianz ({buyer_ratio} der mittleren Erzeugung) von {full} auf "
        "{best} EUR/MWh.",
    "Why not hedge 100%, and why not months?": "Warum nicht 100 % absichern, und warum nicht "
                                               "monatlich?",
    "Market check: the latest Cal base quote, {quote} EUR/MWh ({date}), differs from the "
    "model's forward ({model}). At the quote the indicative price is {indicative} EUR/MWh.":
        "Marktabgleich: Die letzte Cal-Base-Notierung, {quote} EUR/MWh ({date}), weicht vom "
        "Terminpreis des Modells ({model}) ab. Zur Notierung liegt der indikative Preis bei "
        "{indicative} EUR/MWh.",
    "Published Cal-{yy} base quotes (EUR/MWh): {quotes}.":
        "Veröffentlichte Cal-{yy}-Base-Notierungen (EUR/MWh): {quotes}.",
    # built tab
    "Nine steps from raw data to a price": "Neun Schritte von Rohdaten zum Preis",
    "Step": "Schritt",
    "What": "Was",
    "Result": "Ergebnis",
    "Report": "Bericht",
    "Market data": "Marktdaten",
    "Prices and generation since 2021, checked and reconciled":
        "Preise und Erzeugung seit 2021, geprüft und abgeglichen",
    "Capture prices": "Capture Prices",
    "What solar and wind earn vs the official market values":
        "Was Solar und Wind erlösen, im Vergleich zu den offiziellen Marktwerten",
    "TSO data": "Daten der Übertragungsnetzbetreiber",
    "Official market values reproduced; balancing cost from reBAP":
        "Offizielle Marktwerte nachgebildet; Ausgleichskosten aus dem reBAP",
    "PPA structures": "PPA-Strukturen",
    "Cash flows and fair prices; back-test 2024-2025":
        "Zahlungsströme und faire Preise; Backtest 2024-2025",
    "Weather to power": "Vom Wetter zur Erzeugung",
    "31 ERA5 weather years at two real sites; P50/P90":
        "31 ERA5-Wetterjahre an zwei realen Standorten; P50/P90",
    "Price model": "Preismodell",
    "Hourly prices: seasonality, daily mean reversion, analog days":
        "Stundenpreise: Saisonalität, tägliche Mean Reversion, Analogtage",
    "Joint scenarios": "Gemeinsame Szenarien",
    "Prices simulated for each weather year": "Preise für jedes Wetterjahr simuliert",
    "Pricing and risk": "Bepreisung und Risiko",
    "Structures, premia, price stack, ten-year price":
        "Strukturen, Prämien, Preisaufbau, Zehnjahrespreis",
    "Futures hedges, hedge ratio, buyer's hedge, market check":
        "Futures-Absicherung, Hedge-Quote, Absicherung des Käufers, Marktabgleich",
    "Capture rates per scenario: prices linked to the weather vs not":
        "Capture Rates je Szenario: Preise mit und ohne Wetterbezug",
    "Price stack, both parks": "Preisaufbau, beide Parks",
    "Glossary": "Glossar",
    "Term": "Begriff",
    "ppa-lab · PPA price and risk": "ppa-lab · PPA-Preis und Risiko",
    "Meaning": "Bedeutung",
}

# English key -> Italian
IT: dict[str, str] = {
    # sidebar
    "Your assumptions": "Le tue ipotesi",
    "Language": "Lingua",
    "Park": "Parco",
    "Solar park · Borrentin · 114 MWp": "Parco solare · Borrentin · 114 MWp",
    "Wind park · Everswinkel · 28.5 MW": "Parco eolico · Everswinkel · 28,5 MW",
    "Which past represents the delivery year?": "Quale passato rappresenta l'anno di consegna?",
    "Last 12 months (base case)": "Ultimi 12 mesi (caso base)",
    "Whole 2024-2026 window": "Intero periodo 2024-2026",
    "Negative prices": "Prezzi negativi",
    "Paid for every MWh (base case)": "Pagato per ogni MWh (caso base)",
    "Clause: we stop producing and are not paid": "Clausola: il parco si ferma e non è pagato",
    "Shift of the forward curve (%)": "Spostamento della curva forward (%)",
    "Solar and storage build-out after {start}":
        "Crescita di fotovoltaico e accumuli dopo il {start}",
    "Capture-rate trend (pp per year)": "Trend del capture rate (punti percentuali l'anno)",
    "Tenor (years)": "Durata (anni)",
    "Discount rate (%)": "Tasso di attualizzazione (%)",
    "Output degradation (% per year)": "Degrado della produzione (% l'anno)",
    "Balancing and route to market (EUR/MWh)": "Sbilanciamento e accesso al mercato (EUR/MWh)",
    "Credit and liquidity (EUR/MWh)": "Credito e liquidità (EUR/MWh)",
    "Defaults = the Step 7 base case (config/project.toml).":
        "Valori predefiniti = caso base della fase 7 (config/project.toml).",
    "{name}: solar +{pv} GW, storage +{storage} GWh a year":
        "{name}: fotovoltaico +{pv} GW, accumuli +{storage} GWh l'anno",
    "Central": "Centrale",
    "Recent pace": "Ritmo recente",
    "EEG solar target pace": "Ritmo dell'obiettivo EEG per il solare",
    "Storage boom": "Boom degli accumuli",
    "Slowdown": "Rallentamento",
    "{name} (base case)": "{name} (caso base)",
    # page head
    "What fixed price for a renewable PPA, and how much risk is left?":
        "Quale prezzo fisso per un PPA rinnovabile, e quanto rischio resta?",
    "ppa-lab {version} · German day-ahead prices, 31 ERA5 weather years, {n} joint scenarios "
    "for {start} · illustrative analysis from public data, not an offer":
        "ppa-lab {version} · prezzi day-ahead tedeschi, 31 anni meteo ERA5, {n} scenari "
        "congiunti per il {start} · analisi illustrativa da dati pubblici, non un'offerta",
    "Negative-price clause: the park stops producing at negative prices ({share} of its output "
    "in {start}, more at lower forwards) and is not paid for it, so it keeps what a plain PPA "
    "loses ({value} EUR per MWh of output in {start}). Prices are per delivered MWh; per MWh of "
    "output the indicative price is about {per_output}.":
        "Clausola sui prezzi negativi: il parco si ferma quando i prezzi sono negativi ({share} "
        "della sua produzione nel {start}, di più con forward più bassi) e non viene pagato, "
        "così conserva ciò che un PPA semplice perde ({value} EUR per MWh prodotto nel "
        "{start}). I prezzi sono per MWh consegnato; per MWh prodotto il prezzo indicativo è "
        "di circa {per_output}.",
    # headline numbers
    "Indicative price": "Prezzo indicativo",
    "Fair price, {tenor} years": "Prezzo equo, {tenor} anni",
    "Fair price, {start}": "Prezzo equo, {start}",
    "Risk premium": "Premio per il rischio",
    "Cash flow at risk": "Cash flow at risk",
    "EUR/MWh": "EUR/MWh",
    "EUR per delivered MWh": "EUR per MWh consegnato",
    "{unit} over {tenor} years; {delta} vs the base case":
        "{unit} su {tenor} anni; {delta} rispetto al caso base",
    "{unit}, before the risk premium and costs":
        "{unit}, prima del premio per il rischio e dei costi",
    "{unit}: forward {forward} × capture rate {capture}":
        "{unit}: forward {forward} × capture rate {capture}",
    "EUR/MWh after a baseload hedge ({unhedged} without)":
        "EUR/MWh dopo una copertura baseload ({unhedged} senza)",
    "EUR m a year with the PPA; {merchant} if merchant ({cut})":
        "mln EUR l'anno con il PPA; {merchant} se merchant ({cut})",
    # tabs
    "From forward to offer": "Dal forward all'offerta",
    "Risk by structure": "Rischio per struttura",
    "Hedging": "Copertura",
    "How it was built": "Come è stato costruito",
    "Method and glossary": "Metodo e glossario",
    # price tab
    "This park is paid under the EEG: spot plus a monthly put on the onshore market value at "
    "its award value ({award} EUR/MWh, assumed; the award is not published). Over {years} years "
    "that pays about {net} EUR/MWh after the marketing fee, against {ppa} for the PPA at the "
    "base case: the PPA here is a what-if (Step 7 report, section 6).":
        "Questo parco è remunerato secondo l'EEG: prezzo spot più una put mensile sul valore di "
        "mercato dell'eolico onshore al suo valore di aggiudicazione ({award} EUR/MWh, "
        "ipotizzato; il valore non è pubblicato). Su {years} anni rende circa {net} EUR/MWh al "
        "netto della commissione di commercializzazione, contro {ppa} per il PPA nel caso base: "
        "qui il PPA è solo un'ipotesi (rapporto della fase 7, sezione 6).",
    "The price, layer by layer": "Il prezzo, strato per strato",
    "Layer": "Strato",
    "What it means": "Significato",
    "Forward {start}": "Forward {start}",
    "The market price of a flat block of power in {start}":
        "Il prezzo di mercato di un blocco di energia costante nel {start}",
    "Shape": "Profilo",
    "The park produces more when power is cheap: its capture rate is {capture}":
        "Il parco produce di più quando l'energia costa poco: il suo capture rate è {capture}",
    "Fair price {start}": "Prezzo equo {start}",
    "Break-even price for {start}: what the output is worth at market prices":
        "Prezzo di pareggio per il {start}: quanto vale la produzione ai prezzi di mercato",
    "Later years": "Anni successivi",
    "The forward curve, the capture rate at each year's price level":
        "La curva forward, il capture rate al livello di prezzo di ogni anno",
    ", the build-out scenario": ", lo scenario di crescita",
    ", degradation and discounting": ", degrado e attualizzazione",
    "One fixed price that is fair over the whole contract":
        "Un unico prezzo fisso, equo per tutta la durata del contratto",
    "The buyer's charge for profile and volume risk it cannot hedge":
        "Ciò che l'acquirente chiede per il rischio di profilo e di volume che non può coprire",
    "Balancing, credit": "Sbilanciamento, credito",
    "Forecast errors at the imbalance price, marketing fee; credit and capital":
        "Errori di previsione al prezzo di sbilanciamento, commissione di commercializzazione; "
        "credito e capitale",
    "What a buyer could accept: the bottom of the negotiation range":
        "Ciò che un acquirente potrebbe accettare: il limite inferiore della forchetta negoziale",
    "Year by year": "Anno per anno",
    "Why the capture rate is {capture}": "Perché il capture rate è {capture}",
    "Daily shape": "Profilo giornaliero",
    "Seasons": "Stagioni",
    "Weather": "Meteo",
    "Capture rate": "Capture rate",
    "What moves the price": "Cosa muove il prezzo",
    "Solar and storage build-out": "Crescita di fotovoltaico e accumuli",
    "Storage decides solar's later years: only a storage boom keeps the capture rate close to "
    "flat.":
        "Gli accumuli decidono gli anni successivi del fotovoltaico: solo un boom degli accumuli "
        "mantiene il capture rate quasi stabile.",
    "Volume": "Volume",
    "P50 energy (GWh a year)": "Energia P50 (GWh l'anno)",
    "P90, one year (GWh)": "P90, un anno (GWh)",
    "Expected energy P50 {p50} GWh a year; one year in ten below {p90} GWh (P90). Premium and "
    "costs per MWh of the first year apply to every year.":
        "Energia attesa P50 {p50} GWh l'anno; un anno su dieci sotto {p90} GWh (P90). Premio e "
        "costi per MWh del primo anno valgono per ogni anno.",
    # charts
    "Forward\n{start}": "Forward\n{start}",
    "Fair price\n{start}": "Prezzo equo\n{start}",
    "Fair price\n{tenor} years": "Prezzo equo\n{tenor} anni",
    "Balancing": "Sbilanciamento",
    "Credit": "Credito",
    "Indicative\n{tenor} years": "Indicativo\n{tenor} anni",
    "Forward (baseload)": "Forward (baseload)",
    "Fair price of the park's output": "Prezzo equo della produzione del parco",
    "Average price by hour of day ({start} scenarios)":
        "Prezzo medio per ora del giorno (scenari {start})",
    "Average price {value}": "Prezzo medio {value}",
    "What the park earns {value}": "Ciò che il parco incassa {value}",
    "Average output (MW)": "Produzione media (MW)",
    "Hour of day": "Ora del giorno",
    # tables: columns
    "Year": "Anno",
    "Forward (EUR/MWh)": "Forward (EUR/MWh)",
    "Fair price (EUR/MWh)": "Prezzo equo (EUR/MWh)",
    "Energy (MWh)": "Energia (MWh)",
    "Discount factor": "Fattore di sconto",
    "Change": "Variazione",
    "Indicative (EUR/MWh)": "Indicativo (EUR/MWh)",
    "vs yours (EUR/MWh)": "rispetto al tuo (EUR/MWh)",
    "Scenario": "Scenario",
    "Solar added (GW a year)": "Fotovoltaico aggiunto (GW l'anno)",
    "Storage added (GWh a year)": "Accumuli aggiunti (GWh l'anno)",
    "Capture-rate fall (% a year)": "Calo del capture rate (% l'anno)",
    "Strike (EUR/MWh)": "Strike (EUR/MWh)",
    "CFaR 95% (EUR m)": "CFaR 95% (mln EUR)",
    "Expected (EUR m)": "Atteso (mln EUR)",
    "Bad year, P5 (EUR m)": "Anno negativo, P5 (mln EUR)",
    "Output paid (%)": "Produzione pagata (%)",
    "MW sold": "MW venduti",
    "Hedge ratio (%)": "Rapporto di copertura (%)",
    "CFaR95 (EUR m)": "CFaR95 (mln EUR)",
    "CFaR cut (%)": "Riduzione del CFaR (%)",
    "Variance removed (%)": "Varianza eliminata (%)",
    "spot": "spot",
    # tables: rows
    "Forward curve −10%": "Curva forward −10%",
    "Forward curve +10%": "Curva forward +10%",
    "Capture-rate trend −1 pp a year": "Trend del capture rate −1 p.p. l'anno",
    "Capture-rate trend +1 pp a year": "Trend del capture rate +1 p.p. l'anno",
    "Discount rate +2 pp": "Tasso di attualizzazione +2 p.p.",
    "Discount rate −2 pp": "Tasso di attualizzazione −2 p.p.",
    "Balancing and credit +1 EUR/MWh": "Sbilanciamento e credito +1 EUR/MWh",
    "Build-out: {name}": "Crescita: {name}",
    "Merchant, curtailing at negative prices": "Merchant, fermo a prezzi negativi",
    "Merchant, producing at negative prices": "Merchant, in produzione a prezzi negativi",
    "Pay-as-produced PPA": "PPA pay-as-produced",
    "Pay-as-produced, negative-price clause": "Pay-as-produced, clausola sui prezzi negativi",
    "Pay-as-produced, buyer curtails, deemed output paid":
        "Pay-as-produced, l'acquirente ferma il parco e paga la produzione mancata",
    "Merchant + floor at 0 (premium paid)": "Merchant + floor a 0 (premio pagato)",
    "Baseload PPA": "PPA baseload",
    "No hedge (merchant)": "Nessuna copertura (merchant)",
    "Cal base, 50% of average output": "Cal base, 50% della produzione media",
    "Cal base, 100% of average output": "Cal base, 100% della produzione media",
    "Cal base, minimum-variance": "Cal base, varianza minima",
    "Quarters, minimum-variance": "Trimestri, varianza minima",
    "Months, minimum-variance": "Mesi, varianza minima",
    # risk tab
    "What each structure leaves with the producer ({start}, fair strikes)":
        "Cosa lascia al produttore ogni struttura ({start}, strike equi)",
    "What each structure means": "Cosa significa ogni struttura",
    "The buyer's risk premium": "Il premio per il rischio dell'acquirente",
    "Without a hedge (EUR/MWh)": "Senza copertura (EUR/MWh)",
    "After a baseload hedge (EUR/MWh)": "Dopo una copertura baseload (EUR/MWh)",
    "of which profile (EUR/MWh)": "di cui profilo (EUR/MWh)",
    "of which volume (EUR/MWh)": "di cui volume (EUR/MWh)",
    "The buyer of a pay-as-produced PPA asks for **{joint} EUR/MWh** after selling a baseload "
    "forward; without the hedge it would be {unhedged}, but most of that is the price level, "
    "which the buyer can hedge almost for free. {tech}'s remaining risk is mostly **{kind}**.":
        "L'acquirente di un PPA pay-as-produced chiede **{joint} EUR/MWh** dopo aver venduto "
        "un forward baseload; senza copertura sarebbero {unhedged}, ma gran parte è il livello "
        "dei prezzi, che l'acquirente può coprire quasi gratis. Per {tech} il rischio residuo "
        "è soprattutto **{kind}**.",
    "Solar": "il fotovoltaico",
    "Wind": "l'eolico",
    "profile": "di profilo",
    "volume": "di volume",
    "Output at negative prices, {start}": "Produzione a prezzi negativi, {start}",
    "Value of stopping (EUR per MWh of output)": "Valore dell'arresto (EUR per MWh prodotto)",
    "Clause, 10 years (EUR per delivered MWh)": "Clausola, 10 anni (EUR per MWh consegnato)",
    # hedging tab
    "No hedging results yet: run `ppa-lab hedging` and `ppa-lab memo` (Step 8).":
        "Ancora nessun risultato sulla copertura: eseguire `ppa-lab hedging` e `ppa-lab memo` "
        "(fase 8).",
    "If the park sold at spot: merchant risk by futures hedge ({start})":
        "Se il parco vendesse a spot: rischio merchant per copertura con futures ({start})",
    "MW sold: futures sold, as a year-average MW. Hedge ratio = MW sold / the park's average "
    "output. CFaR95 = expected revenue minus its 5% quantile.":
        "MW venduti: futures venduti, in MW medi sull'anno. Rapporto di copertura = MW venduti "
        "/ produzione media del parco. CFaR95 = ricavo atteso meno il suo quantile al 5%.",
    "Selling **{ratio} of the average output** as Cal base futures cuts the merchant cash flow "
    "at risk by **{cut}**. The PPA buyer's premium falls from {full} to {best} EUR/MWh with the "
    "minimum-variance hedge ({buyer_ratio} of the average output).":
        "Vendere **{ratio} della produzione media** come futures Cal base riduce il cash flow "
        "at risk merchant del **{cut}**. Il premio dell'acquirente del PPA scende da {full} a "
        "{best} EUR/MWh con la copertura a varianza minima ({buyer_ratio} della produzione "
        "media).",
    "Why not hedge 100%, and why not months?":
        "Perché non coprire il 100%, e perché non i singoli mesi?",
    "Market check: the latest Cal base quote, {quote} EUR/MWh ({date}), differs from the "
    "model's forward ({model}). At the quote the indicative price is {indicative} EUR/MWh.":
        "Verifica di mercato: l'ultima quotazione Cal base, {quote} EUR/MWh ({date}), differisce "
        "dal forward del modello ({model}). Alla quotazione il prezzo indicativo è "
        "{indicative} EUR/MWh.",
    "Published Cal-{yy} base quotes (EUR/MWh): {quotes}.":
        "Quotazioni Cal-{yy} base pubblicate (EUR/MWh): {quotes}.",
    # built tab
    "Nine steps from raw data to a price": "Nove fasi dai dati grezzi a un prezzo",
    "Step": "Fase",
    "What": "Cosa",
    "Result": "Risultato",
    "Report": "Rapporto",
    "Market data": "Dati di mercato",
    "Prices and generation since 2021, checked and reconciled":
        "Prezzi e produzione dal 2021, verificati e riconciliati",
    "Capture prices": "Capture price",
    "What solar and wind earn vs the official market values":
        "Quanto incassano solare ed eolico rispetto ai valori di mercato ufficiali",
    "TSO data": "Dati dei gestori di rete (TSO)",
    "Official market values reproduced; balancing cost from reBAP":
        "Valori di mercato ufficiali riprodotti; costo di sbilanciamento dal reBAP",
    "PPA structures": "Strutture di PPA",
    "Cash flows and fair prices; back-test 2024-2025":
        "Flussi di cassa e prezzi equi; back-test 2024-2025",
    "Weather to power": "Dal meteo all'energia",
    "31 ERA5 weather years at two real sites; P50/P90":
        "31 anni meteo ERA5 in due siti reali; P50/P90",
    "Price model": "Modello dei prezzi",
    "Hourly prices: seasonality, daily mean reversion, analog days":
        "Prezzi orari: stagionalità, mean reversion giornaliera, giorni analoghi",
    "Joint scenarios": "Scenari congiunti",
    "Prices simulated for each weather year": "Prezzi simulati per ogni anno meteo",
    "Pricing and risk": "Prezzo e rischio",
    "Structures, premia, price stack, ten-year price":
        "Strutture, premi, composizione del prezzo, prezzo decennale",
    "Futures hedges, hedge ratio, buyer's hedge, market check":
        "Coperture con futures, rapporto di copertura, copertura dell'acquirente, verifica di "
        "mercato",
    "Capture rates per scenario: prices linked to the weather vs not":
        "Capture rate per scenario: prezzi legati al meteo e non",
    "Price stack, both parks": "Composizione del prezzo, entrambi i parchi",
    "Glossary": "Glossario",
    "Term": "Termine",
    "ppa-lab · PPA price and risk": "ppa-lab · prezzo e rischio dei PPA",
    "Meaning": "Significato",
}

TRANSLATIONS: dict[str, dict[str, str]] = {"de": DE, "it": IT}


# --------------------------------------------------------------------------- #
# Explanations behind the help icons
# --------------------------------------------------------------------------- #
HELP: dict[str, dict[str, str]] = {
    "en": {
        "assumptions": "Every number on the page follows these settings. The defaults are the "
                       "base case of the analysis (Step 7 report).",
        "language": "Switch the whole page between English, German and Italian.",
        "park": (
            "**Borrentin**: a 114 MWp ground-mounted solar park in Mecklenburg-Western "
            "Pomerania, about 121 GWh a year. **Everswinkel**: a 28.5 MW onshore wind park in "
            "North Rhine-Westphalia (four Nordex N149 and one N163), about 64 GWh a year, paid "
            "under the EEG. Both are modelled from public data: 31 years of ERA5 weather at the "
            "real site, calibrated to the published yearly output."),
        "pool": (
            "Each simulated day of {start} borrows its hourly price pattern from a real day "
            "with similar weather. Older days have shallower midday dips, because there was "
            "less solar then. Since v1.7 every old day is moved forward by the measured yearly "
            "change of the daily shape, so the choice now changes the price by only a few "
            "cents. The base case uses the last 12 months."),
        "clause": (
            "**Paid for every MWh** (plain pay-as-produced): the park receives the fixed price "
            "even when the market price is negative, so it keeps producing, and the buyer sells "
            "that power at a loss. **Clause**: nothing is paid at negative prices, so the park "
            "switches off. The price is then per delivered MWh (higher), the park keeps the "
            "value of switching off, but takes back volume risk: sunny, cheap years have more "
            "negative hours."),
        "forward": (
            "The forward is today's market price for future delivery (EEX German power, Cal "
            "base). The model's first year averages it, each later year follows the forward "
            "curve. Moving it moves the whole curve, and solar's capture rate moves with it: at "
            "higher price levels midday hours are lifted, as 2023-2026 history confirms."
            "\n\nBase case: {forward_text}."),
        "buildout": (
            "How much solar and battery storage Germany adds each year after the first year. "
            "More solar means more power in the same sunny hours, so each solar MWh is worth "
            "less; storage moves midday power into the evening and slows that fall. The link "
            "is measured on 2023-2026 data: each point of solar share of demand lowered "
            "solar's capture rate by 5.3%."),
        "drift": (
            "An extra change of the capture rate each year, in percentage points, on top of the "
            "build-out scenario. Use it to test a view the scenarios do not cover: −1 means the "
            "capture rate falls one more point every year (0.55 → 0.54 → 0.53 …)."),
        "tenor": (
            "Contract length. The price is one fixed number for all years, so later years with "
            "lower forwards (Cal-28 104.75, Cal-29 87.58 EUR/MWh, then held flat) and lower "
            "capture rates pull it down. A shorter contract stays closer to the first year."),
        "rate": (
            "Discounts later years: a MWh in year t counts with weight (1 + r)^−(t + ½). A "
            "higher rate gives the near, more valuable years more weight, so the ten-year price "
            "moves up towards the first year's."),
        "degradation": (
            "Solar panels lose a little output every year (about 0.5%). Later years then carry "
            "less energy, so they weigh less in the ten-year price."),
        "balancing": (
            "What it costs to sell variable power: forecast errors are settled at the imbalance "
            "price (reBAP), and a direct marketer charges a fee. Measured from the TSOs' data "
            "over the last 12 months (solar 1.68, wind 1.05 EUR/MWh) plus a 0.5 fee."),
        "credit": (
            "A charge for the buyer's default risk and the capital the deal ties up over ten "
            "years. An illustrative assumption; in practice it comes from the buyer's credit "
            "rating."),
        "indicative": (
            "The price a buyer could accept: the **fair price** minus the buyer's **risk "
            "premium** minus **balancing** and **credit** costs. The bottom of the negotiation "
            "range; the fair price is the top. A model view from public data, not an offer."),
        "fair_tenor": (
            "The break-even fixed price over the whole contract, before any risk premium or "
            "cost: the yearly fair prices averaged with weights for energy and discounting. At "
            "this price neither side gains on average."),
        "fair_first": (
            "The break-even price for {start} alone: total revenue at market prices divided by "
            "total energy, over {n} joint weather and price scenarios, E[Σ q·P] / E[Σ q]. It "
            "equals the forward times the **capture rate**, the share of the average price "
            "this park's output earns."),
        "premium": (
            "What the buyer asks for the risk it takes on: the shortfall of its value in a bad "
            "year (5% quantile) per MWh, after it has sold a baseload forward to hedge the "
            "price level. What is left is profile risk (the shape of the output against "
            "prices) and volume risk (how much the weather delivers)."),
        "cfar": (
            "Cash flow at risk: how much less than expected the park earns in a one-in-twenty "
            "year (expected revenue minus its 5% quantile), per year. A PPA fixes the price, so "
            "only volume risk is left."),
        "layers": (
            "Read left to right. Grey: the market's baseload forward. Blue: the fair price, "
            "first for the first year, then for the whole contract. Orange steps take value "
            "away, green steps add it. Navy: the indicative price, what is left after the "
            "buyer's risk premium and costs."),
        "years": (
            "Each contract year has its own forward and capture rate. The ten-year fair price "
            "is their average weighted by energy and discounting; hover over a column title "
            "for its meaning."),
        "capture": (
            "The capture rate is what the park earns per MWh divided by the average price. "
            "Three things pull it away from 1: the **daily shape** (the park produces in the "
            "hours that are cheap or dear on average), the **seasons** (more output in the "
            "cheap or dear part of the year) and the **weather** (within a month and an hour, "
            "sunnier or windier days are cheaper days). Base case, {start} scenarios."),
        "daily_shape": "The capture rate if every day of the year had the average daily price "
                       "and output pattern.",
        "seasons": "What the seasons add: the average pattern of each month instead of the "
                   "year's.",
        "weather": "What the weather adds: within a month and an hour, days with more sun or "
                   "wind have lower prices, because every park of the same kind produces too.",
        "capture_total": "The capture rate of the {start} scenarios: what the park earns per "
                         "MWh divided by the average price.",
        "moves": (
            "Each row changes one assumption from your current settings and shows the new "
            "indicative price. The biggest numbers are the assumptions worth arguing about."),
        "volume": "Annual energy over 31 weather years (1995-2025).",
        "p50": "The median weather year: exceeded in half of all years.",
        "p90": "Exceeded in 9 years out of 10: the volume lenders size debt on.",
        "structures": (
            "Every structure is priced at its own fair strike, so on average they earn about "
            "the same. What differs is the spread: the cash flow at risk. Hover over a column "
            "title for its meaning."),
        "unhedged": "The buyer's risk if it does nothing: mostly the price level.",
        "hedged": "After selling a baseload forward for the expected output: the risk it "
                  "cannot hedge.",
        "profile": "From the shape of the output against prices (how deep the midday dip is).",
        "volume_risk": "From how much the weather delivers, and the fact that windy and sunny "
                       "years are cheap years.",
        "neg_share": "Share of the park's output that falls in hours with negative day-ahead "
                     "prices.",
        "neg_value": "What a park that sells at spot saves by switching off at negative prices; "
                     "a plain PPA gives it away.",
        "neg_clause": "The indicative price with a negative-price clause, per MWh actually "
                      "delivered and paid.",
        "hedge": (
            "Selling futures fixes the price of part of the output in advance. Selling a "
            "product at its forward pays, per MW, the sum over its hours of (forward − spot): "
            "it gains when spot is low, exactly when the park earns little."),
        "steps": (
            "Each step has a report with its numbers and checks, and a learning page in the "
            "repository. Click a report link to open it on GitHub."),
    },
    "de": {
        "assumptions": "Jede Zahl auf der Seite folgt diesen Einstellungen. Die "
                       "Voreinstellungen sind der Basisfall der Analyse (Bericht zu Schritt 7).",
        "language": "Die ganze Seite zwischen Englisch, Deutsch und Italienisch umschalten.",
        "park": (
            "**Borrentin**: ein 114-MWp-Freiflächen-Solarpark in Mecklenburg-Vorpommern, rund "
            "121 GWh pro Jahr. **Everswinkel**: ein 28,5-MW-Windpark an Land in "
            "Nordrhein-Westfalen (vier Nordex N149 und eine N163), rund 64 GWh pro Jahr, nach "
            "dem EEG vergütet. Beide sind aus öffentlichen Daten modelliert: 31 Jahre "
            "ERA5-Wetter am realen Standort, kalibriert auf die veröffentlichte Jahreserzeugung."),
        "pool": (
            "Jeder simulierte Tag in {start} übernimmt sein stündliches Preismuster von einem "
            "realen Tag mit ähnlichem Wetter. Ältere Tage haben flachere Mittagssenken, weil es "
            "damals weniger Solar gab. Seit v1.7 wird jeder alte Tag um die gemessene jährliche "
            "Veränderung des Tagesprofils nach vorn verschoben; die Wahl ändert den Preis daher "
            "nur noch um wenige Cent. Der Basisfall nutzt die letzten 12 Monate."),
        "clause": (
            "**Jede MWh wird bezahlt** (einfaches Pay-as-produced): Der Park erhält den "
            "Festpreis auch bei negativen Marktpreisen, erzeugt also weiter, und der Käufer "
            "verkauft diesen Strom mit Verlust. **Klausel**: Bei negativen Preisen wird nichts "
            "bezahlt, also regelt der Park ab. Der Preis gilt dann je gelieferter MWh (höher), "
            "der Park behält den Wert der Abregelung, trägt aber wieder Mengenrisiko: sonnige, "
            "billige Jahre haben mehr negative Stunden."),
        "forward": (
            "Der Terminpreis ist der heutige Marktpreis für eine künftige Lieferung (EEX, "
            "deutscher Strom, Cal Base). Das erste Modelljahr trifft ihn im Mittel, jedes "
            "spätere Jahr folgt der Terminkurve. Eine Verschiebung bewegt die ganze Kurve, und "
            "die Capture Rate von Solar bewegt sich mit: Bei höherem Preisniveau werden die "
            "Mittagsstunden angehoben, wie die Jahre 2023-2026 bestätigen."
            "\n\nBasisfall: {forward_text}."),
        "buildout": (
            "Wie viel Solar und Batteriespeicher Deutschland nach dem ersten Jahr jährlich "
            "zubaut. Mehr Solar bedeutet mehr Strom in denselben sonnigen Stunden, also ist "
            "jede Solar-MWh weniger wert; Speicher verschieben Mittagsstrom in den Abend und "
            "bremsen diesen Rückgang. Der Zusammenhang ist an Daten von 2023-2026 gemessen: "
            "Jeder Prozentpunkt Solaranteil an der Last senkte die Capture Rate von Solar um "
            "5,3 %."),
        "drift": (
            "Eine zusätzliche jährliche Änderung der Capture Rate in Prozentpunkten, zusätzlich "
            "zum Zubauszenario. Damit lässt sich eine Sicht prüfen, die die Szenarien nicht "
            "abdecken: −1 bedeutet, dass die Capture Rate jedes Jahr um einen weiteren Punkt "
            "fällt (0,55 → 0,54 → 0,53 …)."),
        "tenor": (
            "Vertragslaufzeit. Der Preis ist eine feste Zahl für alle Jahre; spätere Jahre mit "
            "niedrigeren Terminpreisen (Cal-28 104,75, Cal-29 87,58 EUR/MWh, danach konstant) "
            "und niedrigeren Capture Rates ziehen ihn nach unten. Ein kürzerer Vertrag bleibt "
            "näher am ersten Jahr."),
        "rate": (
            "Diskontiert spätere Jahre: Eine MWh im Jahr t zählt mit dem Gewicht "
            "(1 + r)^−(t + ½). Ein höherer Satz gewichtet die nahen, wertvolleren Jahre stärker; "
            "der Zehnjahrespreis rückt so an den des ersten Jahres heran."),
        "degradation": (
            "Solarmodule verlieren jedes Jahr etwas Leistung (rund 0,5 %). Spätere Jahre "
            "tragen dann weniger Energie und zählen im Zehnjahrespreis weniger."),
        "balancing": (
            "Was der Verkauf schwankender Erzeugung kostet: Prognosefehler werden zum "
            "Ausgleichsenergiepreis (reBAP) abgerechnet, und ein Direktvermarkter verlangt "
            "eine Gebühr. Gemessen aus den Daten der Übertragungsnetzbetreiber der letzten 12 "
            "Monate (Solar 1,68, Wind 1,05 EUR/MWh) plus 0,5 Gebühr."),
        "credit": (
            "Ein Aufschlag für das Ausfallrisiko des Käufers und das Kapital, das der Vertrag "
            "über zehn Jahre bindet. Eine illustrative Annahme; in der Praxis ergibt er sich "
            "aus dem Rating des Käufers."),
        "indicative": (
            "Der Preis, den ein Käufer akzeptieren könnte: der **faire Preis** minus die "
            "**Risikoprämie** des Käufers minus Kosten für **Ausgleichsenergie** und "
            "**Kredit**. Die Untergrenze der Verhandlungsspanne; der faire Preis ist die "
            "Obergrenze. Eine Modellsicht aus öffentlichen Daten, kein Angebot."),
        "fair_tenor": (
            "Der Break-even-Festpreis über die gesamte Laufzeit, vor Risikoprämie und Kosten: "
            "die fairen Preise der einzelnen Jahre, gewichtet nach Erzeugung und Diskontierung. "
            "Zu diesem Preis gewinnt im Mittel keine Seite."),
        "fair_first": (
            "Der Break-even-Preis allein für {start}: gesamter Erlös zu Marktpreisen geteilt "
            "durch die gesamte Erzeugung, über {n} gemeinsame Wetter- und Preisszenarien, "
            "E[Σ q·P] / E[Σ q]. Er entspricht dem Terminpreis mal der **Capture Rate**, dem "
            "Anteil am Durchschnittspreis, den die Erzeugung dieses Parks erzielt."),
        "premium": (
            "Was der Käufer für das übernommene Risiko verlangt: der Fehlbetrag seines Werts in "
            "einem schlechten Jahr (5-%-Quantil) je MWh, nachdem er das Preisniveau mit einem "
            "Baseload-Termingeschäft abgesichert hat. Übrig bleiben Profilrisiko (die Form der "
            "Erzeugung gegenüber den Preisen) und Mengenrisiko (wie viel das Wetter liefert)."),
        "cfar": (
            "Cashflow at Risk: wie viel weniger als erwartet der Park in einem von zwanzig "
            "Jahren erlöst (erwarteter Erlös minus sein 5-%-Quantil), pro Jahr. Ein PPA fixiert "
            "den Preis, also bleibt nur das Mengenrisiko."),
        "layers": (
            "Von links nach rechts lesen. Grau: der Baseload-Terminpreis des Markts. Blau: der "
            "faire Preis, erst für das erste Jahr, dann für die ganze Laufzeit. Orange Stufen "
            "nehmen Wert weg, grüne fügen ihn hinzu. Dunkelblau: der indikative Preis, was nach "
            "Risikoprämie und Kosten des Käufers übrig bleibt."),
        "years": (
            "Jedes Vertragsjahr hat seinen eigenen Terminpreis und seine eigene Capture Rate. "
            "Der faire Zehnjahrespreis ist ihr nach Erzeugung und Diskontierung gewichteter "
            "Mittelwert; mit der Maus über einen Spaltentitel fahren für seine Bedeutung."),
        "capture": (
            "Die Capture Rate ist der Erlös des Parks je MWh geteilt durch den "
            "Durchschnittspreis. Drei Dinge entfernen sie von 1: das **Tagesprofil** (der Park "
            "erzeugt in Stunden, die im Mittel billig oder teuer sind), die **Jahreszeiten** "
            "(mehr Erzeugung im billigen oder teuren Teil des Jahres) und das **Wetter** "
            "(innerhalb eines Monats und einer Stunde sind sonnigere oder windigere Tage "
            "billiger). Basisfall, Szenarien {start}."),
        "daily_shape": "Die Capture Rate, wenn jeder Tag des Jahres das durchschnittliche "
                       "Preis- und Erzeugungsmuster hätte.",
        "seasons": "Was die Jahreszeiten hinzufügen: das Durchschnittsmuster jedes Monats "
                   "statt des Jahres.",
        "weather": "Was das Wetter hinzufügt: Innerhalb eines Monats und einer Stunde haben "
                   "Tage mit mehr Sonne oder Wind niedrigere Preise, weil alle Parks gleicher "
                   "Art ebenfalls erzeugen.",
        "capture_total": "Die Capture Rate der Szenarien {start}: Erlös des Parks je MWh "
                         "geteilt durch den Durchschnittspreis.",
        "moves": (
            "Jede Zeile ändert eine Annahme gegenüber Ihren aktuellen Einstellungen und zeigt "
            "den neuen indikativen Preis. Die größten Zahlen sind die Annahmen, über die sich "
            "zu verhandeln lohnt."),
        "volume": "Jahreserzeugung über 31 Wetterjahre (1995-2025).",
        "p50": "Das mittlere Wetterjahr: in der Hälfte aller Jahre überschritten.",
        "p90": "In 9 von 10 Jahren überschritten: die Menge, auf die Banken Kredite auslegen.",
        "structures": (
            "Jede Struktur ist zu ihrem eigenen fairen Strike bepreist; im Mittel erlösen alle "
            "etwa gleich viel. Der Unterschied liegt in der Streuung: dem Cashflow at Risk. Mit "
            "der Maus über einen Spaltentitel fahren für seine Bedeutung."),
        "unhedged": "Das Risiko des Käufers ohne Maßnahmen: vor allem das Preisniveau.",
        "hedged": "Nach dem Verkauf eines Baseload-Termingeschäfts für die erwartete "
                  "Erzeugung: das Risiko, das er nicht absichern kann.",
        "profile": "Aus der Form der Erzeugung gegenüber den Preisen (wie tief die "
                   "Mittagssenke ist).",
        "volume_risk": "Aus der Menge, die das Wetter liefert, und daraus, dass windige und "
                       "sonnige Jahre billige Jahre sind.",
        "neg_share": "Anteil der Erzeugung des Parks in Stunden mit negativen "
                     "Day-Ahead-Preisen.",
        "neg_value": "Was ein Park am Spotmarkt durch Abregelung bei negativen Preisen spart; "
                     "ein einfaches PPA verschenkt es.",
        "neg_clause": "Der indikative Preis mit Klausel für negative Preise, je tatsächlich "
                      "gelieferter und bezahlter MWh.",
        "hedge": (
            "Der Verkauf von Futures fixiert den Preis eines Teils der Erzeugung im Voraus. "
            "Ein zum Terminpreis verkauftes Produkt zahlt je MW die Summe über seine Stunden "
            "von (Terminpreis − Spot): Es gewinnt, wenn der Spotpreis niedrig ist, genau dann, "
            "wenn der Park wenig erlöst."),
        "steps": (
            "Jeder Schritt hat einen Bericht mit seinen Zahlen und Prüfungen und eine "
            "Lernseite im Repository. Ein Klick auf den Bericht öffnet ihn auf GitHub."),
    },
    "it": {
        "assumptions": "Ogni numero della pagina segue queste impostazioni. I valori predefiniti "
                       "sono il caso base dell'analisi (rapporto della fase 7).",
        "language": "Cambia la lingua di tutta la pagina: inglese, tedesco o italiano.",
        "park": (
            "**Borrentin**: un parco solare a terra da 114 MWp nel Meclemburgo-Pomerania "
            "Anteriore, circa 121 GWh l'anno. **Everswinkel**: un parco eolico onshore da 28,5 MW "
            "in Renania Settentrionale-Vestfalia (quattro Nordex N149 e una N163), circa 64 GWh "
            "l'anno, remunerato secondo l'EEG. Entrambi sono modellati da dati pubblici: 31 anni "
            "di meteo ERA5 nel sito reale, calibrati sulla produzione annua pubblicata."),
        "pool": (
            "Ogni giorno simulato del {start} prende il suo profilo orario dei prezzi da un "
            "giorno reale con meteo simile. I giorni più vecchi hanno un calo di mezzogiorno meno "
            "profondo, perché allora c'era meno solare. Dalla v1.7 ogni giorno passato viene "
            "spostato in avanti della variazione annua misurata del profilo giornaliero, quindi "
            "la scelta cambia il prezzo solo di pochi centesimi. Il caso base usa gli ultimi 12 "
            "mesi."),
        "clause": (
            "**Pagato per ogni MWh** (pay-as-produced semplice): il parco riceve il prezzo fisso "
            "anche quando il prezzo di mercato è negativo, quindi continua a produrre, e "
            "l'acquirente rivende quell'energia in perdita. **Clausola**: a prezzi negativi non si "
            "paga nulla, quindi il parco si ferma. Il prezzo è allora per MWh consegnato (più "
            "alto); il parco conserva il valore dell'arresto, ma si riprende rischio di volume: "
            "gli anni soleggiati ed economici hanno più ore negative."),
        "forward": (
            "Il forward è il prezzo di mercato di oggi per una consegna futura (EEX, energia "
            "tedesca, Cal base). Il primo anno del modello lo rispetta in media, ogni anno "
            "successivo segue la curva forward. Spostarlo sposta tutta la curva, e il capture "
            "rate del solare si muove con essa: a livelli di prezzo più alti le ore di mezzogiorno "
            "salgono, come conferma la storia 2023-2026."
            "\n\nCaso base: {forward_text}."),
        "buildout": (
            "Quanto fotovoltaico e quanti accumuli a batteria la Germania aggiunge ogni anno dopo "
            "il primo. Più solare significa più energia nelle stesse ore di sole, quindi ogni MWh "
            "solare vale meno; gli accumuli spostano l'energia di mezzogiorno verso la sera e "
            "frenano questo calo. Il legame è misurato sui dati 2023-2026: ogni punto di quota "
            "solare sulla domanda ha ridotto il capture rate del solare del 5,3%."),
        "drift": (
            "Una variazione aggiuntiva del capture rate ogni anno, in punti percentuali, oltre "
            "allo scenario di crescita. Serve a provare una visione che gli scenari non coprono: "
            "−1 significa che il capture rate scende di un punto in più ogni anno "
            "(0,55 → 0,54 → 0,53 …)."),
        "tenor": (
            "Durata del contratto. Il prezzo è un unico numero fisso per tutti gli anni, quindi "
            "gli anni successivi con forward più bassi (Cal-28 104,75, Cal-29 87,58 EUR/MWh, poi "
            "costante) e capture rate più bassi lo abbassano. Un contratto più breve resta più "
            "vicino al primo anno."),
        "rate": (
            "Attualizza gli anni successivi: un MWh nell'anno t conta con peso (1 + r)^−(t + ½). "
            "Un tasso più alto dà più peso agli anni vicini, che valgono di più, quindi il prezzo "
            "decennale sale verso quello del primo anno."),
        "degradation": (
            "I pannelli solari perdono un po' di resa ogni anno (circa lo 0,5%). Gli anni "
            "successivi portano quindi meno energia e pesano meno nel prezzo decennale."),
        "balancing": (
            "Quanto costa vendere energia variabile: gli errori di previsione si regolano al "
            "prezzo di sbilanciamento (reBAP) e un operatore di mercato (direct marketer) applica "
            "una commissione. Misurato dai dati dei TSO degli ultimi 12 mesi (solare 1,68, eolico "
            "1,05 EUR/MWh) più una commissione di 0,5."),
        "credit": (
            "Un costo per il rischio di insolvenza dell'acquirente e per il capitale che il "
            "contratto immobilizza per dieci anni. Un'ipotesi illustrativa; nella pratica dipende "
            "dal rating dell'acquirente."),
        "indicative": (
            "Il prezzo che un acquirente potrebbe accettare: il **prezzo equo** meno il **premio "
            "per il rischio** dell'acquirente meno i costi di **sbilanciamento** e **credito**. "
            "Il limite inferiore della forchetta negoziale; il prezzo equo è quello superiore. "
            "Una stima di modello da dati pubblici, non un'offerta."),
        "fair_tenor": (
            "Il prezzo fisso di pareggio sull'intero contratto, prima di premio per il rischio e "
            "costi: i prezzi equi dei singoli anni in media ponderata per energia e "
            "attualizzazione. A questo prezzo nessuna delle due parti guadagna in media."),
        "fair_first": (
            "Il prezzo di pareggio del solo {start}: ricavo totale ai prezzi di mercato diviso "
            "per l'energia totale, su {n} scenari congiunti di meteo e prezzi, "
            "E[Σ q·P] / E[Σ q]. È uguale al forward per il **capture rate**, la quota del prezzo "
            "medio che incassa la produzione di questo parco."),
        "premium": (
            "Ciò che l'acquirente chiede per il rischio che si assume: la perdita del suo valore "
            "in un anno negativo (quantile al 5%) per MWh, dopo aver coperto il livello dei prezzi "
            "con la vendita di un forward baseload. Restano il rischio di profilo (la forma della "
            "produzione rispetto ai prezzi) e il rischio di volume (quanto rende il meteo)."),
        "cfar": (
            "Cash flow at risk: quanto meno del previsto incassa il parco in un anno su venti "
            "(ricavo atteso meno il suo quantile al 5%), per anno. Un PPA fissa il prezzo, quindi "
            "resta solo il rischio di volume."),
        "layers": (
            "Si legge da sinistra a destra. Grigio: il forward baseload del mercato. Blu: il "
            "prezzo equo, prima per il primo anno, poi per tutto il contratto. I gradini arancioni "
            "tolgono valore, quelli verdi lo aggiungono. Blu scuro: il prezzo indicativo, ciò che "
            "resta dopo il premio per il rischio e i costi dell'acquirente."),
        "years": (
            "Ogni anno del contratto ha il suo forward e il suo capture rate. Il prezzo equo "
            "decennale è la loro media ponderata per energia e attualizzazione; passa il mouse sul "
            "titolo di una colonna per il suo significato."),
        "capture": (
            "Il capture rate è ciò che il parco incassa per MWh diviso per il prezzo medio. Tre "
            "fattori lo allontanano da 1: il **profilo giornaliero** (il parco produce nelle ore "
            "che in media costano poco o tanto), le **stagioni** (più produzione nella parte "
            "economica o cara dell'anno) e il **meteo** (a parità di mese e ora, i giorni più "
            "soleggiati o ventosi costano meno). Caso base, scenari {start}."),
        "daily_shape": "Il capture rate se ogni giorno dell'anno avesse il profilo giornaliero "
                       "medio di prezzi e produzione.",
        "seasons": "Ciò che aggiungono le stagioni: il profilo medio di ogni mese invece di "
                   "quello dell'anno.",
        "weather": "Ciò che aggiunge il meteo: a parità di mese e ora, i giorni con più sole o "
                   "vento hanno prezzi più bassi, perché producono anche tutti gli impianti dello "
                   "stesso tipo.",
        "capture_total": "Il capture rate degli scenari {start}: ciò che il parco incassa per "
                         "MWh diviso per il prezzo medio.",
        "moves": (
            "Ogni riga cambia un'ipotesi rispetto alle tue impostazioni attuali e mostra il nuovo "
            "prezzo indicativo. I numeri più grandi indicano le ipotesi su cui vale la pena "
            "discutere."),
        "volume": "Energia annua su 31 anni meteo (1995-2025).",
        "p50": "L'anno meteo mediano: superato nella metà degli anni.",
        "p90": "Superato in 9 anni su 10: il volume su cui le banche dimensionano il debito.",
        "structures": (
            "Ogni struttura è prezzata al proprio strike equo, quindi in media incassano tutte "
            "più o meno lo stesso. Cambia la dispersione: il cash flow at risk. Passa il mouse sul "
            "titolo di una colonna per il suo significato."),
        "unhedged": "Il rischio dell'acquirente se non fa nulla: soprattutto il livello dei "
                    "prezzi.",
        "hedged": "Dopo aver venduto un forward baseload per la produzione attesa: il rischio che "
                  "non può coprire.",
        "profile": "Dalla forma della produzione rispetto ai prezzi (quanto è profondo il calo "
                   "di mezzogiorno).",
        "volume_risk": "Da quanto rende il meteo, e dal fatto che gli anni ventosi e soleggiati "
                       "sono anni con prezzi bassi.",
        "neg_share": "Quota della produzione del parco che cade in ore con prezzi day-ahead "
                     "negativi.",
        "neg_value": "Ciò che un parco che vende a spot risparmia fermandosi a prezzi negativi; "
                     "un PPA semplice lo regala.",
        "neg_clause": "Il prezzo indicativo con la clausola sui prezzi negativi, per MWh "
                      "effettivamente consegnato e pagato.",
        "hedge": (
            "Vendere futures fissa in anticipo il prezzo di una parte della produzione. Un "
            "prodotto venduto al suo forward paga, per MW, la somma sulle sue ore di "
            "(forward − spot): guadagna quando lo spot è basso, proprio quando il parco incassa "
            "poco."),
        "steps": (
            "Ogni fase ha un rapporto con i suoi numeri e controlli e una pagina di studio nel "
            "repository. Un clic sul rapporto lo apre su GitHub."),
    },
}

COLUMN_HELP: dict[str, dict[str, str]] = {
    "en": {
        "Forward (EUR/MWh)": "The market's price for that year: the Cal forward, held flat after "
                             "the last quoted year.",
        "Capture rate": "The share of the average price the park's output earns that year.",
        "Fair price (EUR/MWh)": "Forward × capture rate: the break-even price for that year "
                                "alone.",
        "Energy (MWh)": "Expected output (P50), lower each year by degradation.",
        "Discount factor": "Weight of that year's money today: (1 + r)^−(t + ½).",
        "Strike (EUR/MWh)": "Each structure's own fair price: the strike at which it earns the "
                            "same as the market on average. Merchant has none: it sells at "
                            "spot.",
        "Output paid (%)": "Share of the possible output that is produced and paid; below 100% "
                           "where the park stops at negative prices.",
        "Expected (EUR m)": "Average yearly revenue over the scenarios.",
        "Bad year, P5 (EUR m)": "Revenue in a one-in-twenty bad year (5% quantile).",
        "CFaR 95% (EUR m)": "Cash flow at risk: expected revenue minus the bad-year revenue, "
                            "the risk left with the producer. Smaller is safer.",
        "MW sold": "Futures sold, as a year-average MW.",
        "Hedge ratio (%)": "MW sold divided by the park's average output.",
        "CFaR95 (EUR m)": "Cash flow at risk with this hedge.",
        "CFaR cut (%)": "How much smaller the cash flow at risk is than without a hedge.",
        "Variance removed (%)": "Share of the revenue variance the hedge removes (hedge "
                                "effectiveness).",
        "Indicative (EUR/MWh)": "Fair price minus risk premium and costs, with that one change.",
        "vs yours (EUR/MWh)": "Difference to the indicative price with your settings.",
        "Solar added (GW a year)": "New solar capacity in Germany each year after the first "
                                   "year.",
        "Storage added (GWh a year)": "New battery storage each year.",
        "Capture-rate fall (% a year)": "How fast solar's capture rate falls under the "
                                        "scenario.",
    },
    "de": {
        "Forward (EUR/MWh)": "Der Marktpreis für dieses Jahr: der Cal-Terminpreis, nach dem "
                             "letzten notierten Jahr konstant gehalten.",
        "Capture rate": "Der Anteil am Durchschnittspreis, den die Erzeugung des Parks in "
                        "diesem Jahr erzielt.",
        "Fair price (EUR/MWh)": "Terminpreis × Capture Rate: der Break-even-Preis allein für "
                                "dieses Jahr.",
        "Energy (MWh)": "Erwartete Erzeugung (P50), jedes Jahr um die Degradation niedriger.",
        "Discount factor": "Gewicht des Geldes dieses Jahres heute: (1 + r)^−(t + ½).",
        "Strike (EUR/MWh)": "Der eigene faire Preis jeder Struktur: der Strike, zu dem sie im "
                            "Mittel so viel erlöst wie der Markt. Der Spotmarkt hat keinen: er "
                            "verkauft zum Spotpreis.",
        "Output paid (%)": "Anteil der möglichen Erzeugung, der erzeugt und bezahlt wird; unter "
                           "100 %, wo der Park bei negativen Preisen abregelt.",
        "Expected (EUR m)": "Durchschnittlicher Jahreserlös über die Szenarien.",
        "Bad year, P5 (EUR m)": "Erlös in einem schlechten Jahr, das einmal in zwanzig Jahren "
                                "eintritt (5-%-Quantil).",
        "CFaR 95% (EUR m)": "Cashflow at Risk: erwarteter Erlös minus Erlös im schlechten Jahr, "
                            "das Risiko, das beim Erzeuger bleibt. Kleiner ist sicherer.",
        "MW sold": "Verkaufte Futures als Jahresmittel in MW.",
        "Hedge ratio (%)": "Verkaufte MW geteilt durch die mittlere Erzeugung des Parks.",
        "CFaR95 (EUR m)": "Cashflow at Risk mit dieser Absicherung.",
        "CFaR cut (%)": "Um wie viel der Cashflow at Risk kleiner ist als ohne Absicherung.",
        "Variance removed (%)": "Anteil der Erlösvarianz, den die Absicherung entfernt "
                                "(Hedge-Effektivität).",
        "Indicative (EUR/MWh)": "Fairer Preis minus Risikoprämie und Kosten, mit dieser einen "
                                "Änderung.",
        "vs yours (EUR/MWh)": "Unterschied zum indikativen Preis mit Ihren Einstellungen.",
        "Solar added (GW a year)": "Neue Solarleistung in Deutschland pro Jahr nach dem "
                                   "ersten Jahr.",
        "Storage added (GWh a year)": "Neue Batteriespeicher pro Jahr.",
        "Capture-rate fall (% a year)": "Wie schnell die Capture Rate von Solar im Szenario "
                                        "fällt.",
    },
    "it": {
        "Forward (EUR/MWh)": "Il prezzo di mercato per quell'anno: il forward Cal, mantenuto "
                             "costante dopo l'ultimo anno quotato.",
        "Capture rate": "La quota del prezzo medio che la produzione del parco incassa in "
                        "quell'anno.",
        "Fair price (EUR/MWh)": "Forward × capture rate: il prezzo di pareggio di quel solo "
                                "anno.",
        "Energy (MWh)": "Produzione attesa (P50), ogni anno più bassa per il degrado.",
        "Discount factor": "Peso oggi del denaro di quell'anno: (1 + r)^−(t + ½).",
        "Strike (EUR/MWh)": "Il prezzo equo di ogni struttura: lo strike al quale incassa in "
                            "media quanto il mercato. Il merchant non ne ha: vende a spot.",
        "Output paid (%)": "Quota della produzione possibile che viene prodotta e pagata; sotto "
                           "il 100% dove il parco si ferma a prezzi negativi.",
        "Expected (EUR m)": "Ricavo annuo medio sugli scenari.",
        "Bad year, P5 (EUR m)": "Ricavo in un anno negativo, uno su venti (quantile al 5%).",
        "CFaR 95% (EUR m)": "Cash flow at risk: ricavo atteso meno il ricavo dell'anno "
                            "negativo, il rischio che resta al produttore. Più piccolo è più "
                            "sicuro.",
        "MW sold": "Futures venduti, in MW medi sull'anno.",
        "Hedge ratio (%)": "MW venduti divisi per la produzione media del parco.",
        "CFaR95 (EUR m)": "Cash flow at risk con questa copertura.",
        "CFaR cut (%)": "Di quanto il cash flow at risk è più piccolo che senza copertura.",
        "Variance removed (%)": "Quota della varianza dei ricavi che la copertura elimina "
                                "(efficacia della copertura).",
        "Indicative (EUR/MWh)": "Prezzo equo meno premio per il rischio e costi, con quell'unica "
                                "variazione.",
        "vs yours (EUR/MWh)": "Differenza rispetto al prezzo indicativo con le tue impostazioni.",
        "Solar added (GW a year)": "Nuova capacità solare in Germania ogni anno dopo il primo.",
        "Storage added (GWh a year)": "Nuovi accumuli a batteria ogni anno.",
        "Capture-rate fall (% a year)": "Quanto velocemente scende il capture rate del solare "
                                        "nello scenario.",
    },
}

GLOSSARY: dict[str, list[tuple[str, str]]] = {
    "en": [
        ("PPA", "Power purchase agreement: a long-term contract to buy a park's power at a "
                "fixed price"),
        ("Pay-as-produced", "The buyer pays the fixed price for every MWh the park produces"),
        ("Baseload", "A flat block of power, the same MW in every hour of the year"),
        ("Forward, Cal base", "Today's market price for a year of baseload power delivered in "
                              "the future (EEX)"),
        ("Capture price", "What a technology earns per MWh: revenue divided by energy"),
        ("Capture rate", "Capture price divided by the average price; below 1 when output "
                         "falls in cheap hours"),
        ("Fair price", "The fixed price at which neither side gains on average"),
        ("Indicative price", "Fair price minus the buyer's risk premium and costs"),
        ("Risk premium", "What the buyer charges for risk it cannot hedge, per MWh"),
        ("Profile risk", "Risk from the shape of the output against the shape of prices"),
        ("Volume risk", "Risk from how much the weather delivers"),
        ("Cash flow at risk (CFaR95)", "Expected revenue minus the revenue of a one-in-twenty "
                                       "bad year"),
        ("P50 / P90", "Energy exceeded in 50% / 90% of years"),
        ("Negative prices", "Hours when producers pay to deliver: too much power, too little "
                            "demand"),
        ("Build-out scenario", "An assumption on how much solar and storage Germany adds each "
                               "year"),
        ("EEG market premium", "The subsidy: market value topped up to the award value each "
                               "month, a strip of puts"),
        ("reBAP", "The German imbalance price, at which forecast errors are settled"),
    ],
    "de": [
        ("PPA", "Power Purchase Agreement: ein langfristiger Vertrag über den Strom eines Parks "
                "zu einem Festpreis"),
        ("Pay-as-produced", "Der Käufer zahlt den Festpreis für jede erzeugte MWh"),
        ("Baseload", "Ein gleichmäßiges Strom-Band, in jeder Stunde des Jahres dieselben MW"),
        ("Terminpreis, Cal Base", "Der heutige Marktpreis für ein Jahr Baseload-Strom mit "
                                  "künftiger Lieferung (EEX)"),
        ("Capture Price", "Was eine Technologie je MWh erlöst: Erlös geteilt durch Erzeugung"),
        ("Capture Rate", "Capture Price geteilt durch den Durchschnittspreis; unter 1, wenn "
                         "die Erzeugung in billige Stunden fällt (auch Marktwertfaktor)"),
        ("Fairer Preis", "Der Festpreis, zu dem im Mittel keine Seite gewinnt"),
        ("Indikativer Preis", "Fairer Preis minus Risikoprämie und Kosten des Käufers"),
        ("Risikoprämie", "Was der Käufer je MWh für Risiken verlangt, die er nicht absichern "
                         "kann"),
        ("Profilrisiko", "Risiko aus der Form der Erzeugung gegenüber der Form der Preise"),
        ("Mengenrisiko", "Risiko aus der Menge, die das Wetter liefert"),
        ("Cashflow at Risk (CFaR95)", "Erwarteter Erlös minus Erlös eines schlechten Jahres, "
                                      "das einmal in zwanzig Jahren eintritt"),
        ("P50 / P90", "In 50 % / 90 % der Jahre überschrittene Erzeugung"),
        ("Negative Preise", "Stunden, in denen Erzeuger für die Lieferung zahlen: zu viel "
                            "Strom, zu wenig Nachfrage"),
        ("Zubauszenario", "Eine Annahme, wie viel Solar und Speicher Deutschland jährlich "
                          "zubaut"),
        ("EEG-Marktprämie", "Die Förderung: Der Marktwert wird monatlich auf den anzulegenden "
                            "Wert aufgestockt, eine Reihe von Puts"),
        ("reBAP", "Der deutsche Ausgleichsenergiepreis, zu dem Prognosefehler abgerechnet "
                  "werden"),
    ],
    "it": [
        ("PPA", "Power purchase agreement: un contratto di lungo termine per acquistare "
                "l'energia di un parco a prezzo fisso"),
        ("Pay-as-produced", "L'acquirente paga il prezzo fisso per ogni MWh prodotto dal parco"),
        ("Baseload", "Un blocco di energia costante, gli stessi MW in ogni ora dell'anno"),
        ("Forward, Cal base", "Il prezzo di mercato di oggi per un anno di energia baseload "
                              "consegnata in futuro (EEX)"),
        ("Capture price", "Ciò che una tecnologia incassa per MWh: ricavo diviso per energia"),
        ("Capture rate", "Capture price diviso per il prezzo medio; sotto 1 quando la produzione "
                         "cade nelle ore a basso prezzo"),
        ("Prezzo equo", "Il prezzo fisso al quale nessuna delle due parti guadagna in media"),
        ("Prezzo indicativo", "Prezzo equo meno il premio per il rischio e i costi "
                              "dell'acquirente"),
        ("Premio per il rischio", "Ciò che l'acquirente chiede, per MWh, per il rischio che non "
                                  "può coprire"),
        ("Rischio di profilo", "Rischio dalla forma della produzione rispetto alla forma dei "
                               "prezzi"),
        ("Rischio di volume", "Rischio da quanto rende il meteo"),
        ("Cash flow at risk (CFaR95)", "Ricavo atteso meno il ricavo di un anno negativo, uno "
                                       "su venti"),
        ("P50 / P90", "Energia superata nel 50% / 90% degli anni"),
        ("Prezzi negativi", "Ore in cui i produttori pagano per consegnare: troppa energia, "
                            "troppo poca domanda"),
        ("Scenario di crescita", "Un'ipotesi su quanto fotovoltaico e quanti accumuli la "
                                 "Germania aggiunge ogni anno"),
        ("Premio di mercato EEG", "L'incentivo: il valore di mercato integrato ogni mese fino "
                                  "al valore di aggiudicazione, una serie di put"),
        ("reBAP", "Il prezzo di sbilanciamento tedesco, al quale si regolano gli errori di "
                  "previsione"),
    ],
}

STRUCTURES_EXPLAINED = {
    "en": """
- **Merchant**: the park sells every MWh at the day-ahead price. It carries the price level, the
  shape and the volume. Selling at spot it stops at negative prices (that is free).
- **Pay-as-produced PPA**: the buyer pays a fixed price for whatever the park produces. The buyer
  takes the price level and the shape; the volume is shared (the park earns less in a dull year).
- **Negative-price clause**: as pay-as-produced, but nothing is paid at negative prices, so the
  park stops producing. Higher price per delivered MWh, more volume risk for the park.
- **Buyer curtails, deemed output paid**: the buyer may switch the park off at negative prices
  but pays the lost output as if produced. The park keeps its income and the buyer the saving.
- **Baseload PPA**: the park delivers a flat band. The buyer takes the price level; the park must
  buy the shape back when it produces less than the band (at night, in winter).
""",
    "de": """
- **Spotmarkt (Merchant)**: Der Park verkauft jede MWh zum Day-Ahead-Preis. Er trägt
  Preisniveau, Profil und Menge. Am Spotmarkt regelt er bei negativen Preisen ab (das ist
  kostenlos).
- **Pay-as-produced-PPA**: Der Käufer zahlt einen Festpreis für alles, was der Park erzeugt. Er
  übernimmt Preisniveau und Profil; die Menge ist geteilt (in einem trüben Jahr erlöst der Park
  weniger).
- **Klausel für negative Preise**: wie Pay-as-produced, aber bei negativen Preisen wird nichts
  bezahlt, also regelt der Park ab. Höherer Preis je gelieferter MWh, mehr Mengenrisiko für den
  Park.
- **Käufer regelt ab, fiktive Erzeugung bezahlt**: Der Käufer darf den Park bei negativen
  Preisen abschalten, bezahlt die entgangene Erzeugung aber, als wäre sie erzeugt worden. Der
  Park behält seinen Erlös, der Käufer die Ersparnis.
- **Baseload-PPA**: Der Park liefert ein gleichmäßiges Band. Der Käufer übernimmt das
  Preisniveau; der Park muss das Profil zukaufen, wenn er weniger als das Band erzeugt (nachts,
  im Winter).
""",
    "it": """
- **Merchant**: il parco vende ogni MWh al prezzo day-ahead. Porta su di sé il livello dei prezzi,
  il profilo e il volume. Vendendo a spot si ferma a prezzi negativi (senza costi).
- **PPA pay-as-produced**: l'acquirente paga un prezzo fisso per tutto ciò che il parco produce.
  Si assume il livello dei prezzi e il profilo; il volume è condiviso (in un anno poco ventoso o
  nuvoloso il parco incassa meno).
- **Clausola sui prezzi negativi**: come il pay-as-produced, ma a prezzi negativi non si paga
  nulla, quindi il parco si ferma. Prezzo più alto per MWh consegnato, più rischio di volume per
  il parco.
- **L'acquirente ferma il parco e paga la produzione mancata**: l'acquirente può spegnere il parco
  a prezzi negativi, ma paga la produzione persa come se fosse stata prodotta. Il parco mantiene
  il suo ricavo, l'acquirente il risparmio.
- **PPA baseload**: il parco consegna una banda costante. L'acquirente si assume il livello dei
  prezzi; il parco deve ricomprare il profilo quando produce meno della banda (di notte, in
  inverno).
""",
}

HEDGING_EXPLAINED = {
    "en": """
- **Below 100% for solar**: the park produces in cheap hours, so its revenue rises less than a
  flat band when prices rise. A full band over-hedges: in an expensive year the hedge loses more
  than the park gains. The minimum-variance amount balances the two.
- **Months add little**: the monthly amounts are estimated from 496 scenarios and mostly fit
  noise, some even come out negative. One Cal base contract does most of the work.
- **One year's P&L says nothing**: a hedge sold at a fair price wins in some years and loses in
  others. It is judged by the risk it removes, not by last year's result.
""",
    "de": """
- **Unter 100 % für Solar**: Der Park erzeugt in billigen Stunden, sein Erlös steigt also
  weniger als ein gleichmäßiges Band, wenn die Preise steigen. Ein volles Band sichert zu viel
  ab: In einem teuren Jahr verliert die Absicherung mehr, als der Park gewinnt. Die Menge mit
  minimaler Varianz gleicht beides aus.
- **Monate bringen wenig**: Die Monatsmengen werden aus 496 Szenarien geschätzt und passen sich
  vor allem dem Rauschen an, manche fallen sogar negativ aus. Ein Cal-Base-Kontrakt leistet den
  Großteil.
- **Ein Jahresergebnis sagt nichts**: Eine zu einem fairen Preis verkaufte Absicherung gewinnt in
  manchen Jahren und verliert in anderen. Sie wird nach dem Risiko beurteilt, das sie entfernt,
  nicht nach dem Ergebnis des letzten Jahres.
""",
    "it": """
- **Sotto il 100% per il solare**: il parco produce nelle ore a basso prezzo, quindi quando i
  prezzi salgono il suo ricavo cresce meno di una banda costante. Una banda piena copre troppo: in
  un anno caro la copertura perde più di quanto guadagna il parco. La quantità a varianza minima
  bilancia le due cose.
- **I mesi aggiungono poco**: le quantità mensili sono stimate su 496 scenari e seguono
  soprattutto il rumore, alcune risultano perfino negative. Un solo contratto Cal base fa quasi
  tutto il lavoro.
- **Il risultato di un anno non dice nulla**: una copertura venduta a un prezzo equo guadagna in
  alcuni anni e perde in altri. Si giudica dal rischio che elimina, non dal risultato dell'ultimo
  anno.
""",
}

METHOD = {
    "en": """
- **Fair price** = E[Σ q P] / E[Σ q] over {n} joint scenarios: 31 weather years (ERA5, pvlib,
  windpowerlib) × simulated hourly prices that respond to that weather.
- **Risk premium** = 5% shortfall of the buyer's value per expected MWh, after selling a baseload
  forward for the expected average output.
- **Tenor price**: energy- and discount-weighted average of yearly fair prices.
- **Forward**: {forward_text}.
- **Limits**: forwards are published quotes from secondary sources (not EEX files), balancing and
  credit costs are illustrative, the price shape is calibrated on 2024-2026 (one market regime),
  the parks produce their potential output.

Code, tests and methodology: [github.com/ankitpatel1661/ppa-lab](https://github.com/ankitpatel1661/ppa-lab)
· [METHODOLOGY.md]({repo}/METHODOLOGY.md) · [one-page memo]({repo}/reports/step09_memo.md)
""",
    "de": """
- **Fairer Preis** = E[Σ q P] / E[Σ q] über {n} gemeinsame Szenarien: 31 Wetterjahre (ERA5,
  pvlib, windpowerlib) × simulierte Stundenpreise, die auf dieses Wetter reagieren.
- **Risikoprämie** = 5-%-Fehlbetrag des Käuferwerts je erwarteter MWh, nach dem Verkauf eines
  Baseload-Termingeschäfts für die erwartete mittlere Erzeugung.
- **Preis über die Laufzeit**: nach Erzeugung und Diskontierung gewichteter Mittelwert der
  jährlichen fairen Preise.
- **Terminpreis**: {forward_text}.
- **Grenzen**: Die Terminpreise sind veröffentlichte Notierungen aus Sekundärquellen (keine
  EEX-Dateien), Ausgleichs- und Kreditkosten sind illustrativ, das Preisprofil ist auf 2024-2026
  kalibriert (ein Marktregime), die Parks erzeugen ihre potenzielle Erzeugung.

Code, Tests und Methodik (auf Englisch): [github.com/ankitpatel1661/ppa-lab](https://github.com/ankitpatel1661/ppa-lab)
· [METHODOLOGY.md]({repo}/METHODOLOGY.md) · [Memo auf einer Seite]({repo}/reports/step09_memo.md)
""",
    "it": """
- **Prezzo equo** = E[Σ q P] / E[Σ q] su {n} scenari congiunti: 31 anni meteo (ERA5, pvlib,
  windpowerlib) × prezzi orari simulati che reagiscono a quel meteo.
- **Premio per il rischio** = perdita al 5% del valore dell'acquirente per MWh atteso, dopo la
  vendita di un forward baseload per la produzione media attesa.
- **Prezzo sulla durata**: media dei prezzi equi annuali ponderata per energia e attualizzazione.
- **Forward**: {forward_text}.
- **Limiti**: i forward sono quotazioni pubblicate da fonti secondarie (non file EEX), i costi di
  sbilanciamento e di credito sono illustrativi, il profilo dei prezzi è calibrato sul 2024-2026
  (un solo regime di mercato), i parchi producono la loro produzione potenziale.

Codice, test e metodologia (in inglese): [github.com/ankitpatel1661/ppa-lab](https://github.com/ankitpatel1661/ppa-lab)
· [METHODOLOGY.md]({repo}/METHODOLOGY.md) · [memo di una pagina]({repo}/reports/step09_memo.md)
""",
}


FORWARD_TEXT = {   # the forward's quote, its quarters and the later years
    "de": ("EEX Cal-{yy} Base {price} EUR/MWh (Notierung vom {date})",
           "; die Quartale folgen der saisonalen Form des Markts (Q1-Q4 {quarters})",
           "; spätere Jahre folgen der Terminkurve ({later}), nach {last} konstant"),
    "it": ("EEX Cal-{yy} base {price} EUR/MWh (quotazione del {date})",
           "; i trimestri seguono la forma stagionale del mercato (Q1-Q4 {quarters})",
           "; gli anni successivi seguono la curva forward ({later}), costante dopo il {last}"),
}


def forward_text_local(forward: dict, curve: dict, start: int, lang: str) -> str:
    """The forward in German or Italian: the Cal quote, its quarters and the later years."""
    head, quarters_text, later_text = FORWARD_TEXT[lang]
    text = head.format(yy=str(start)[2:], price=number(forward["price_eur_mwh"], 2, lang),
                       date=forward.get("date", "?"))
    quarters = forward.get("quarters")
    if quarters:
        text += quarters_text.format(
            quarters=" / ".join(number(quarters[str(q)], 1, lang) for q in range(1, 5)))
    if curve:
        years = sorted(int(y) for y in curve)
        later = ", ".join(f"{y}: {number(curve[str(y)], 2, lang)}" for y in years)
        text += later_text.format(later=later, last=years[-1])
    return text
