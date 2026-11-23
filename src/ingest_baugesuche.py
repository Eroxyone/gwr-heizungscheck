"""Baugesuche aus dem Amtsblattportal, schweizweit.

Der Zuercher OGD-Datensatz deckt nur einen Kanton ab. Das Amtsblattportal fuehrt
dieselben Publikationen fuer 13 Kantone, offen und ohne Anmeldung. Welche Mandanten
eine Baugesuch-Subrubrik fuehren, wurde nicht geraten, sondern aus
https://amtsblattportal.ch/api/v1/rubrics gelesen und mit /api/v1/tenants verknuepft.

Der entscheidende Unterschied zwischen den Mandanten ist, **wo der Projektbeschrieb
steht**. Zwei Gruppen:

  modus "titel"  Der Titel traegt den Beschrieb ("Baugesuch - Ersatz Oelheizung durch
                 Luft/Wasser-Waermepumpe, Stans"). Die Listenabfrage reicht als Filter,
                 nur die Treffer brauchen einen Detailabruf. Gilt fuer BL, SO, NW, OW,
                 SH und den Sammelmandanten AM-DA50.
  modus "voll"   Der Titel traegt nur die Adresse ("Kommunale Baugesuchspublikation:
                 Sprungstrasse 13a, Unteraegeri"). Ein Titelfilter faende hier fast
                 nichts - in Zuerich griff er bei 1 von 6743 Publikationen. Fuer diese
                 Mandanten muss jedes Detail geholt werden.

Diese Unterscheidung ist der Grund, warum ein naiver schweizweiter Abzug scheitert:
Er meldet fuer ZH, BE, ZG, AR, BS, TI und SZ null Heizungsbaugesuche, obwohl sie da sind.

    python src/ingest_baugesuche.py                  # alles ab 2024
    python src/ingest_baugesuche.py --ab 2022-01-01
    python src/ingest_baugesuche.py --kantone BE SO  # nur diese Kantone
"""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import html
import json
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

import config

BASIS = "https://amtsblattportal.ch/api/v1/publications"
ZIEL = config.RAW / "baugesuche_ch.jsonl"

# Kanton und Abrufmodus je Subrubrik. AM-DA50 ist der Sammelmandant der Gemeinden ohne
# eigenes Amtsblatt, faktisch fast nur Bern. AA-GR10 (Graubuenden) ist im Rubrikenkatalog
# als aktiv gefuehrt, enthaelt aber keine einzige Publikation - deshalb nicht in der Liste.
# "aktiv": False heisst nur "standardmaessig uebersprungen", nicht "unbrauchbar".
RUBRIKEN: dict[str, dict] = {
    # Zuerich publiziert dieselben Baugesuche als offenen Datensatz des Statistischen
    # Amts - mit Parzellenpolygonen, taeglich aktualisiert und in einer einzigen Tabelle.
    # Der Portalabzug waere die schlechtere Kopie und kostet 6743 Detailabrufe, also fast
    # die Haelfte der gesamten Laufzeit. Mit "--kantone ZH" laesst er sich trotzdem holen,
    # etwa um die beiden Quellen gegeneinander zu pruefen.
    "BP-ZH01": {"kanton": "ZH", "modus": "voll", "aktiv": False},
    "BP-BE10": {"kanton": "BE", "modus": "voll"},
    "BP-BS10": {"kanton": "BS", "modus": "voll"},
    "BP-TI10": {"kanton": "TI", "modus": "voll"},
    "BP-ZG10": {"kanton": "ZG", "modus": "voll"},
    "BP-AR10": {"kanton": "AR", "modus": "voll"},
    "BA-SZ05": {"kanton": "SZ", "modus": "voll"},
    "BP-BL05": {"kanton": "BL", "modus": "titel"},
    "BA-SO05": {"kanton": "SO", "modus": "titel"},
    "BA-NW05": {"kanton": "NW", "modus": "titel"},
    "BA-OW05": {"kanton": "OW", "modus": "titel"},
    "BA-SH05": {"kanton": "SH", "modus": "titel"},
    "BA-VS05": {"kanton": "VS", "modus": "titel"},
    "AM-DA50": {"kanton": "divers", "modus": "titel"},
}

# Bewusst weit gefasst: In dieser Stufe darf lieber zu viel durchrutschen, die
# eigentliche Klassifikation macht silver_baugesuche.sql und die LLM-Pruefung.
HEIZUNG = re.compile(
    r"wärmepump|waermepump|luft[ /-]{0,3}wasser|erdsonde|erdwärme|erdwaerme|erdregister|"
    r"geothermie|heizung|heizkessel|heizzentrale|wärmeerzeug|waermeerzeug|"
    r"fernwärme|fernwaerme|wärmeverbund|waermeverbund|wärmenetz|waermenetz|"
    r"pellet|holzschnitzel|stückholz|ölkessel|oelkessel|öltank|oeltank|heizöl|heizoel|"
    r"gaskessel|gastherme|energiezentrale|solarthermie|thermische solar|"
    r"chauffage|pompe à chaleur|sonde géothermique|chaudière|mazout|chauffe-eau|"
    r"riscaldamento|pompa di calore|sonda geotermica|termopompa|caldaia|teleriscaldamento",
    re.I)

UA = {"User-Agent": config.USER_AGENT}
SEITE = 500
PARALLEL_DETAIL = 12


def _hole(url: str, timeout: int = 120, versuche: int = 5) -> str:
    letzter: Exception | None = None
    for i in range(1, versuche + 1):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as fehler:
            letzter = fehler
            if i < versuche:
                time.sleep(min(2 ** i, 20))
    raise RuntimeError(f"Abruf fehlgeschlagen: {url}") from letzter


def _saeubern(roh: str) -> str | None:
    """Richtext kommt doppelt kodiert an: erst &lt;div&gt;, darin nochmals &amp;auml;.
    Zweimal entschluesseln, dann die HTML-Tags entfernen."""
    s = roh
    for _ in range(2):
        neu = html.unescape(s)
        if neu == s:
            break
        s = neu
    s = re.sub(r"<[^>]+>", " ", s)
    return re.sub(r"\s+", " ", s).strip() or None


def _feld(xml: str, name: str) -> str | None:
    m = re.search(rf"<{name}>([^<]*)</{name}>", xml)
    return _saeubern(m.group(1)) if m else None


def _wert(block: str) -> str | None:
    """Den Wert eines <element>-Blocks lesen, nicht seine Beschriftung.

    Ein Block sieht so aus:
        <element><key>projectDescription</key><term><de>Projektbeschreibung</de></term>
                 <valueRichText><de>...der eigentliche Text...</de></valueRichText></element>
    Wer einfach das erste <de> nimmt, erhaelt "Projektbeschreibung" - genau dieser Fehler
    liess Schwyz wie ein Kanton ohne Projektbeschriebe aussehen. Deshalb zuerst den
    value-Knoten suchen und nur ersatzweise den Block ohne <term> durchsehen.
    """
    m = re.search(r"<value(RichText|Text|TextNeutral)>(.*?)</value\1>", block, re.S)
    raum = m.group(2) if m else re.sub(
        r"<term>.*?</term>|<delimiterTitle>.*?</delimiterTitle>", "", block, flags=re.S)
    for sprache in ("de", "fr", "it", "valueTextNeutral"):
        treffer = _feld(raum, sprache)
        if treffer:
            return treffer
    return _saeubern(re.sub(r"<[^>]+>", " ", raum))


def liste(rubrik: str, ab: str, bis: str) -> tuple[list[dict], int]:
    """Alle Publikationen einer Subrubrik im Zeitraum, jahrweise abgefragt.

    Warum jahrweise: Das Wallis meldet ueber vier Jahre mehr als 10'000 Publikationen.
    Ab etwa Seite 20 laeuft die Abfrage in einen Timeout - tiefe Paginierung kostet den
    Server offenbar zunehmend. Ein Lauf ueber den ganzen Zeitraum brach deshalb bei
    genau 10'000 Zeilen ab, ohne dass das aufgefallen waere, wenn man die Zahl nicht
    kennt. Ein Jahr am Stueck bleibt flach genug.
    """
    treffer: list[dict] = []
    luecken = 0
    for jahr in range(int(ab[:4]), int(bis[:4]) + 1):
        von = max(ab, f"{jahr}-01-01")
        nach = min(bis, f"{jahr}-12-31")
        if von > nach:
            continue
        teil, fehlend = _liste_zeitraum(rubrik, von, nach)
        treffer.extend(teil)
        luecken += fehlend
    return treffer, luecken


def _liste_zeitraum(rubrik: str, ab: str, bis: str) -> tuple[list[dict], int]:
    """Eine Subrubrik in einem Zeitraum durchblaettern. Zweiter Rueckgabewert ist die Zahl
    der Seiten, die trotz Wiederholung nicht geladen werden konnten - eine einzelne kaputte
    Seite darf nicht den ganzen Kanton kosten."""
    treffer, seite, luecken = [], 0, 0
    while True:
        url = (f"{BASIS}/xml?publicationStates=PUBLISHED&subRubrics={rubrik}"
               f"&publicationDate.start={ab}&publicationDate.end={bis}"
               f"&pageRequest.size={SEITE}&pageRequest.page={seite}")
        try:
            xml = _hole(url, timeout=180)
        except RuntimeError:
            luecken += 1
            seite += 1
            if luecken >= 3:
                break
            continue
        bloecke = re.findall(r"<publication .*?</publication>", xml, re.S)
        if not bloecke:
            break
        for b in bloecke:
            titel = None
            m = re.search(r"<title>(.*?)</title>", b, re.S)
            if m:
                titel = _feld(m.group(1), "de") or _feld(m.group(1), "fr") \
                        or _feld(m.group(1), "it")
            ref = re.search(r'ref="([^"]+)"', b)
            treffer.append({
                "id": _feld(b, "id"),
                "ref": ref.group(1) if ref else None,
                "rubrik": rubrik,
                "kanton": _feld(b, "cantons"),
                "datum": _feld(b, "publicationDate"),
                "bfs_behoerde": _feld(b, "municipalityId"),
                "amt": _feld(b, "displayName"),
                "titel": titel,
            })
        if len(bloecke) < SEITE:
            break
        seite += 1
    return treffer, luecken


def _elemente(xml: str) -> dict[str, str]:
    """Das Detail-XML ist generisch aufgebaut: beliebig viele <element>-Bloecke, jeder
    mit einem <key>. Welche Schluessel vorkommen, unterscheidet sich je Mandant -
    SZ, SO, NW und OW fuehren projectDescription als Element, ZH, BE, BS, TI und ZG als
    eigenes Feld auf oberster Ebene. Deshalb wird nach key indexiert statt nach
    Feldnamen gesucht."""
    treffer: dict[str, str] = {}
    for block in re.findall(r"<element>.*?</element>", xml, re.S):
        k = re.search(r"<key>([^<]+)</key>", block)
        if k:
            treffer.setdefault(k.group(1), block)
    return treffer


# Bloecke, die eine Personen- oder Firmenadresse enthalten. Sie muessen vor jeder
# Adresssuche verschwinden - sonst steht in einer Zuger Publikation die Adresse des
# Haustechnikbetriebs aus Wolhusen LU als Standort des Vorhabens. Genau so ein stiller
# Fehler ist bei einer Adresszuordnung teurer als eine fehlende Adresse.
PERSONENBLOCK = re.compile(
    r"<(buildingContractor|projectFramer|landOwner|owner|applicant|representative"
    r"|registrationOffice|invoiceAddress|contact)>.*?</\1>", re.S)

# Reihenfolge zaehlt: zuerst der ausdrueckliche Standortblock, dann das Element
# projectAddress, erst zuletzt ein Freitext. Nie ein Rest-Dokument durchsuchen.
LV95 = re.compile(r"(2[\s'’]?\d{3}[\s'’]?\d{3})\s*[/,;\s]\s*(1[\s'’]?\d{3}[\s'’]?\d{3})")

# Schwyz publiziert den Beschrieb als Fliesstext und nennt darin Planverfasser und
# Grundeigentuemer mit Namen und Wohnadresse. Das sind Personendaten, die dieses Projekt
# laut eigener Regel nicht verarbeitet. Sie werden beim Einlesen entfernt, nicht erst
# spaeter - was nie gespeichert wird, kann auch nicht versehentlich in einen Bericht
# geraten. Der Rest des Satzes, das eigentliche Bauobjekt, bleibt erhalten.
NAMENSFELD = re.compile(
    r"\b(Projektverfasser(?:in)?|Planverfasser(?:in)?|Grundeigent[üu]mer(?:in)?|"
    r"Eigent[üu]mer(?:in)?|Bauherrschaft|Gesuchsteller(?:in)?|Architekt(?:in)?|"
    r"Bauleitung|Ma[îi]tre d.ouvrage|Propri[ée]taire|Auteur des plans|"
    r"Istante|Richiedente|Committente|Proprietario del fondo|Proprietari del fondo|"
    r"Progettista|Autore del progetto|Direzione lavori)\s*:\s*"
    # Ende des Namensfeldes: Satzende vor Grossbuchstabe oder - so macht es das Tessin -
    # die naechste Formularnummer ("2. Proprietario del fondo: ...").
    #
    # Ein Semikolon galt hier zunaechst auch als Ende. Das war falsch und liess
    # Personendaten stehen: Schwyz schreibt "Grundeigentuemer: A GmbH; Herr + Frau
    # Vorname Name, Strasse 5, 8849 Ort." - der Schnitt am Semikolon entfernte die
    # Firma und liess die Privatpersonen mitsamt Wohnadresse im Text.
    r".*?(?=\.\s+[A-ZÄÖÜ]|\s+\d{1,2}\.\s+[A-Za-zÀ-ÿ]|$)", re.I | re.S)

# Schwyz stellt dem eigentlichen Beschrieb einen Vorspann mit Zone, Planverfasser und
# Grundeigentuemern voran und leitet das Vorhaben mit "Bauobjekt:" ein. Wo dieses Wort
# vorkommt, ist alles davor Verwaltungsprosa und Personendaten - also weg damit. Das ist
# die wirksamere Massnahme als jede Stichprobe: Sie entfernt auch Namen, an die niemand
# gedacht hat.
VORSPANN = re.compile(r"^.*?\b(Bauobjekt|Bauvorhaben)\s*:\s*", re.I | re.S)

# Das Tessin publiziert ein nummeriertes Formular statt eines Beschriebs. Punkt 3 nennt
# die Art des Vorhabens, Punkt 4 das Grundstueck - beides brauchen wir, der Rest sind
# Auflagefristen und Oeffnungszeiten der Bauverwaltung.
TI_FELD = {
    "art": re.compile(r"Genere dell.opera\s*:\s*(.*?)(?=\s+\d{1,2}\.\s|$)", re.S),
    "zweck": re.compile(r"Destinazione degli edifici[^:]*:\s*(.*?)(?=\s+\d{1,2}\.\s|$)", re.S),
    "parzelle": re.compile(r"N\.?\s*di mappa\s*:\s*([\d,\s/]+?)(?=\s*[A-Za-z]|$)", re.S),
    "ort": re.compile(r"Localit[àa]\s*:\s*(.*?)(?=\s+[A-ZÀ-Ý][a-zà-ÿ]+\s*:|\s+\d{1,2}\.\s|$)", re.S),
}


def _anonymisieren(text: str | None) -> str | None:
    if not text:
        return None
    text = VORSPANN.sub("", text, count=1)
    return NAMENSFELD.sub(lambda m: f"{m.group(1)}: [entfernt]", text).strip() or None


def _tessin(text: str | None) -> dict:
    """Aus dem Tessiner Formular die drei sachlichen Felder herausloesen."""
    if not text or "Genere dell" not in text:
        return {}
    gefunden = {}
    for name, muster in TI_FELD.items():
        m = muster.search(text)
        if m:
            wert = re.sub(r"\s+", " ", m.group(1)).strip(" .,;")
            if wert and wert.lower() not in ("-/-", "nessuna", "diversa"):
                gefunden[name] = wert
    return gefunden


def _koordinate_aus_text(text: str | None) -> str | None:
    """Schwyz fuehrt keinen Koordinatenblock, schreibt die LV95-Koordinate aber in den
    Beschrieb ("Koordinaten 2 700 535/1 221 177"). Das ist die genaueste Ortsangabe,
    die dieser Mandant liefert."""
    if not text:
        return None
    m = LV95.search(text)
    if not m:
        return None
    ost, nord = (re.sub(r"[\s'’]", "", g) for g in m.groups())
    return f"{ost}/{nord}"


def detail(eintrag: dict) -> dict:
    """Objektadresse, Parzelle, BFS-Nummer und Volltext einer Publikation nachladen."""
    try:
        x = re.sub(r">\s+<", "><", _hole(eintrag["ref"], 90, versuche=3))
    # Breit gefangen: Eine einzelne Publikation, die sich nicht laden laesst (Netz, Format),
    # soll den Abzug von Zehntausenden nicht abbrechen. Der Fehler steht im Datensatz.
    except Exception as fehler:
        return {**eintrag, "detail_fehler": str(fehler)[:80]}

    ohne = PERSONENBLOCK.sub("", x)
    el = _elemente(ohne)

    teile = []
    for key in ("projectDescription", "constructionProjectTitle"):
        if key in el:
            teile.append(_wert(el[key]))
    if not any(teile):
        teile = [_feld(ohne, "projectDescription")]
    # Das Wallis vergibt dem Titel-Element gar keinen <key>, es steht nur als erstes
    # Element unter <primary>. Ohne diesen Zweig saehe VS aus wie ein Kanton ohne
    # Projektbeschriebe, obwohl jede Publikation einen hat.
    if not any(teile):
        p = re.search(r"<primary>(.*?)</primary>", ohne, re.S)
        teile = [_wert(p.group(1))] if p else teile
    # Letzter Rueckfall: Bei BL, SO, NW, OW, SH und AM-DA50 traegt der Titel den
    # Beschrieb ohnehin - dann ist er die beste verfuegbare Quelle.
    beschrieb = " / ".join(t for t in teile if t) or None
    if not beschrieb and eintrag.get("titel"):
        beschrieb = re.sub(r"^(Baugesuch|Baupublikation|Gesuch f[üu]r Baubewilligung|"
                           r"Kommunale Baugesuchspublikation|Bauprojekt|"
                           r"Domanda di costruzione|Demande d.autorisation de construire)"
                           r"\s*[\-–—:]\s*", "", eintrag["titel"], flags=re.I)
    beschrieb = _anonymisieren(beschrieb)

    m = re.search(r"<projectLocation>(.*?)</projectLocation>", ohne, re.S)
    adr, herkunft = (m.group(1), "projectLocation") if m else ("", None)
    if not adr and "projectAddress" in el:
        adr, herkunft = el["projectAddress"], "projectAddress"

    # Parzelle: die Westschweizer und Innerschweizer Mandanten fuehren sie als Element,
    # die uebrigen als districtCadastre mit Grundstueck- und Versicherungsnummer.
    parzelle = _wert(el["parcel"]) if "parcel" in el else None
    kat = re.search(r"<districtCadastre>(.*?)</districtCadastre>", ohne, re.S)
    versicherung = None
    if kat:
        parzelle = parzelle or _feld(kat.group(1), "property") \
                   or _feld(kat.group(1), "plot") or _feld(kat.group(1), "cadastre")
        versicherung = _feld(kat.group(1), "insurance")

    # Die BFS-Nummer steht je nach Mandant direkt im Feld oder im <key> darunter.
    bfs = _feld(ohne, "municipalityId")
    if not bfs:
        k = re.search(r"<municipalityId>.*?<key>([^<]+)</key>", ohne, re.S)
        bfs = k.group(1) if k else None

    koord = _wert(el["coordinates"]) if "coordinates" in el else None
    koord = koord or _feld(ohne, "locationCoordinate")
    # Einheitlich als "Ost/Nord" ablegen, egal ob der Mandant Schraegstrich, Komma,
    # Leerzeichen oder Hochkommas als Tausendertrenner verwendet.
    koord = _koordinate_aus_text(koord) or _koordinate_aus_text(beschrieb)

    ti = _tessin(beschrieb)
    if ti:
        # Der Formularrumpf ist fuer die Heizungserkennung wertlos und enthaelt Namen.
        # Nur die Sachfelder behalten.
        beschrieb = " / ".join(ti[k] for k in ("art", "zweck") if k in ti) or beschrieb
        parzelle = parzelle or ti.get("parzelle")

    strasse = _feld(adr, "street")
    # Basel-Landschaft fuehrt keine Adresse, sondern schreibt Parzelle und Strasse in
    # ein Feld: "1356 - Strengenfeldweg 8". Beides ist brauchbar, getrennt mehr wert.
    if not strasse and parzelle:
        m = re.match(r"\s*(\d+)\s*[-–]\s*(\D.+)$", parzelle)
        if m:
            parzelle, strasse = m.group(1), m.group(2).strip()
            herkunft = "parzellenfeld"

    return {
        **eintrag,
        "beschrieb": beschrieb,
        "strasse": strasse,
        "hausnummer": _feld(adr, "houseNumber") or _feld(adr, "streetNumber"),
        "plz": _feld(adr, "swissZipCode"),
        "ort": _feld(adr, "town") or _feld(adr, "city"),
        "adresse_herkunft": herkunft,
        "bfs_nr": bfs or eintrag.get("bfs_behoerde"),
        "parzelle": parzelle,
        "versicherungs_nr": versicherung,
        "koordinate": koord,
        "freitext_adresse": _feld(ohne, "customAddress"),
        "keys": ",".join(sorted(el)) or None,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ab", default="2024-01-01")
    p.add_argument("--bis", default=date.today().isoformat())
    p.add_argument("--kantone", nargs="*", help="nur diese Kantone, z. B. BE SO")
    p.add_argument("--out", default=str(ZIEL))
    p.add_argument("--neu", action="store_true",
                   help="Zwischenstand verwerfen und alle Details neu holen")
    a = p.parse_args(argv)

    gewaehlt = [x.upper() for x in a.kantone] if a.kantone else None
    auswahl = {r: m for r, m in RUBRIKEN.items()
               if (m["kanton"].upper() in gewaehlt if gewaehlt
                   else m.get("aktiv", True))}
    print(f"Amtsblattportal, {a.ab} bis {a.bis}, {len(auswahl)} Subrubriken\n")
    print(f"  {'Rubrik':9s} {'Kt':7s} {'Modus':6s} {'Publ.':>7s} {'Detail':>7s}")

    alle: list[dict] = []
    zu_holen: list[dict] = []
    for rubrik, meta in auswahl.items():
        try:
            zeilen, luecken = liste(rubrik, a.ab, a.bis)
        # Breit gefangen: Faellt die Liste eines Kantons aus, laufen die uebrigen weiter.
        except Exception as fehler:
            print(f"  {rubrik:9s} FEHLER: {fehler}", file=sys.stderr)
            continue
        if meta["modus"] == "voll":
            kandidaten = [z for z in zeilen if z["ref"]]
        else:
            kandidaten = [z for z in zeilen
                          if z["ref"] and z["titel"] and HEIZUNG.search(z["titel"])]
        warnung = f"  ({luecken} Seiten fehlen)" if luecken else ""
        print(f"  {rubrik:9s} {meta['kanton']:7s} {meta['modus']:6s} "
              f"{len(zeilen):7d} {len(kandidaten):7d}{warnung}", flush=True)
        alle.extend(zeilen)
        zu_holen.extend(kandidaten)

    ziel = Path(a.out) if a.out.startswith(str(config.ROOT)) else config.ROOT / a.out
    zwischen = ziel.with_suffix(".detail.jsonl")

    # Zehntausend Detailabrufe dauern Stunden. Wird erst am Schluss geschrieben, ist bei
    # jedem Abbruch alles verloren. Deshalb landet jede Antwort sofort in einer
    # Zwischendatei, und ein neuer Lauf ueberspringt, was schon drinsteht.
    fertig: dict[str, dict] = {}
    if zwischen.exists() and not a.neu:
        for zeile in zwischen.read_text(encoding="utf-8").splitlines():
            try:
                e = json.loads(zeile)
            except json.JSONDecodeError:
                continue  # abgeschnittene letzte Zeile eines harten Abbruchs
            if e.get("id"):
                fertig[e["id"]] = e
    offen = [z for z in zu_holen if z["id"] not in fertig]
    print(f"\n{len(alle)} Publikationen, {len(zu_holen)} Detailabrufe "
          f"({len(fertig)} bereits vorhanden, {len(offen)} offen)\n")

    with (open(zwischen, "a", encoding="utf-8") as roh,
          futures.ThreadPoolExecutor(max_workers=PARALLEL_DETAIL) as pool):
        for i, e in enumerate(pool.map(detail, offen), 1):
            fertig[e["id"]] = e
            roh.write(json.dumps(e, ensure_ascii=False) + "\n")
            if i % 250 == 0 or i == len(offen):
                roh.flush()
                print(f"  Detail {i}/{len(offen)}", flush=True)

    angereichert = list(fertig.values())
    # Erst mit dem Beschrieb steht fest, ob es ein Heizungsvorhaben ist. Publikationen
    # ohne Detail kommen ohne dieses Kennzeichen mit, damit sich der Anteil nachrechnen
    # laesst - sonst waere unklar, ob ein Kanton wenig Heizungen hat oder wenig Daten.
    for e in angereichert:
        text = " ".join(filter(None, (e.get("titel"), e.get("beschrieb"))))
        e["heizungsbezug"] = bool(HEIZUNG.search(text))
    ergebnis = angereichert + [z for z in alle if z["id"] not in fertig]

    with open(ziel, "w", encoding="utf-8") as fh:
        for e in ergebnis:
            fh.write(json.dumps(e, ensure_ascii=False) + "\n")
    fehler = sum(1 for e in angereichert if e.get("detail_fehler"))
    heiz = sum(1 for e in angereichert if e.get("heizungsbezug"))
    print(f"\ngeschrieben: {ziel}")
    print(f"  {len(ergebnis)} Zeilen, {len(angereichert)} mit Detail, "
          f"{heiz} mit Heizungsbezug, {fehler} Detailfehler")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
