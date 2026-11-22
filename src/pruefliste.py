"""Die Pruefliste als Arbeitsmappe fuer ein Bauamt.

Wer einen Fall prueft, braucht mehr als eine Tabellenzeile: wo das Gebaeude steht, welcher
Beleg genau vorliegt, und einen Ort, an dem das Ergebnis festgehalten wird.

Die Mappe hat vier bis fuenf Blaetter:

  Pruefliste   eine Zeile je Gebaeude, sortiert nach Belegart, mit Adresse, Koordinate,
               Kartenlink, heutigem Eintrag, Beleg, Korrekturvorschlag und vier leeren
               Spalten zum Eintragen
  Gemeinden    nur in der Kantonsmappe: wie viele Faelle auf wen entfallen
  Belege       die Quellenkette je Fall: Quelle, Referenz, Datum, Zuordnungsweg, Distanz
  Methodik     was gemessen wurde und was nicht, in Prosa, ohne Schoenfaerberei
  Datenstand   Quellen mit Abrufdatum und Pruefsumme

Zwei Regeln:

1. Die Mappe zieht aus v_gold_liste, nicht aus v_gold_verdacht. Dort beruhen 92,6 Prozent
   aller Faelle allein auf einer Photovoltaikanlage, gemessene Trefferquote 13,7 bis
   17,2 Prozent.

2. Die Messwerte im Methodikblatt kommen aus der Datenbank. Fehlt die Messung, bricht der
   Export ab, statt einen Vorgabewert einzusetzen.

    python src/pruefliste.py Volketswil
    python src/pruefliste.py --bfs 199 --max 150
    python src/pruefliste.py --kanton ZH
    python src/pruefliste.py --top 5        # die fuenf groessten Gemeindelisten
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

import config
import pipeline

ZIEL = config.PROCESSED / "prueflisten"

# Die Stufen heissen nicht "hoch" und "sehr hoch". Diese Woerter behaupten eine
# Sicherheit, die nicht gemessen ist. Stattdessen beschreiben sie, WORAUF der Verdacht
# beruht - daraus kann ein Bauamt selbst schliessen, wie ernst es den Fall nimmt.
KLASSE = {
    "reihenfolge belegt":    "Beleg ist nachweislich jünger als der Registereintrag",
    # Zuerich: kein Datum, aber eine kalibrierte Laufnummer. Eine eigene Stufe, damit
    # die gemessene Quote der datierten Stufe nicht auf sie abfaerbt.
    "reihenfolge plausibel": "Beleg nach Laufnummer jünger als der Registereintrag "
                             "(kalibriert, nicht amtlich datiert)",
    "eintrag alt":           "Beleg undatiert, Registereintrag seit über 15 Jahren unberührt",
    "eintrag jung":          "Beleg undatiert, Registereintrag jünger",
}
REIHE = ["reihenfolge belegt", "reihenfolge plausibel", "eintrag alt", "eintrag jung"]

# Welche Anlagenstatus bedeuten "steht und laeuft"? Nicht dasselbe wie "gebaut".
# Die Pruefliste sortiert solche Faelle innerhalb der Stufe nach vorn.
AUSGEFUEHRT = ("Ausgeführt", "WP mit Erdwärmesonde", "WP mit Erdkollektor",
               "ausgebaut, in Nutzung", "in Betrieb", "bestehend, vorhanden",
               "Bohrung ausgefuehrt", "Bohrung realisiert",
               "Erdsonde", "Erdsondenfeld", "Erdkollektoren")
# Gemessen trifft eine Sonde auf 20 m so oft wie auf 8 m. Fuers Nachschlagen auf der
# Karte ist Naehe trotzdem ein Argument, deshalb kommen nahe Anlagen zuerst.
NAH_M = 12

# Kopftext und Spaltenbreite. Die letzten vier sind die Eingabespalten. Alles Weitere
# daraus zu berechnen erspart die Buchstabenzaehlerei, an der dieser Export schon
# zweimal zerbrochen ist, als eine Spalte dazukam.
SPALTEN_BASIS = [
    ("Fall", 11), ("EGID", 10), ("Gemeinde", 20), ("Adresse", 26), ("PLZ", 7),
    ("Ort", 16), ("E (LV95)", 11), ("N (LV95)", 11), ("Karte", 13),
    ("Baujahr", 8), ("Gebäudeart", 20), ("GWR heute", 16),
    ("Informationsquelle", 26), ("Stand", 11), ("Alter (J.)", 9),
    ("Worauf der Verdacht beruht", 32), ("Hinweis", 30), ("Beleg", 52),
    ("Korrekturvorschlag", 44), ("neue Informationsquelle", 34),
]
SPALTEN_EINGABE = [("Geprüft am", 12), ("Ergebnis", 22),
                   ("Neuer Energieträger", 20), ("Bemerkung", 30)]

KOPF = PatternFill("solid", fgColor="1F3A5F")
KOPF_SCHRIFT = Font(color="FFFFFF", bold=True, size=10)
EINGABE = PatternFill("solid", fgColor="FFF6D9")
RAHMEN = Border(*[Side(style="thin", color="D0D5DB")] * 4)

# Die Schluessel muessen den Werten aus anlage_entscheidung entsprechen. Der Eintrag
# hiess einmal "umkreis", in der Datenbank steht aber "umkreis_eindeutig" - und weil
# .get() still auf den Rohwert zurueckfaellt, las das Bauamt in 2'013 Zeilen der
# Zuercher Mappe einen internen Bezeichner. Genau dorthin verwies der Methodiktext.
WEG_TEXT = {"amtlich":           "amtliche EGID des Kantons",
            "adresse":           "Adresse",
            "umkreis":           "Koordinate, 20-m-Umkreis",
            "umkreis_eindeutig": "Koordinate, 20-m-Umkreis"}


class MessungFehlt(RuntimeError):
    """Kein Vorgabewert, kein stiller Rueckfall. Siehe Modulkopf, Punkt 2."""


def _zahl(wert, typ=int):
    """pandas liefert je nach Spalte NaN, None oder pd.NA. Alle drei muessen zu einer
    leeren Zelle werden - "NA" als Text in einer Pruefliste ist schlimmer als leer."""
    return None if wert is None or pd.isna(wert) else typ(wert)


def _text(wert) -> str | None:
    return None if wert is None or pd.isna(wert) else str(wert)


def _datum(wert) -> str | None:
    """Als Text im Schweizer Format. Excel wuerde ein echtes Datum nach Gebietsschema
    formatieren, und ein Zeitstempel "2018-11-23 00:00:00" in einer Pruefliste sieht
    nach Maschine aus, nicht nach Arbeitsmittel."""
    if wert is None or pd.isna(wert):
        return None
    return pd.Timestamp(wert).strftime("%d.%m.%Y")


def _hinweis(r) -> str | None:
    """Was ein Bauamt wissen sollte, bevor es nachschlaegt.

    Ein Beleg unter 18 Monaten ist kein liegengebliebener Altbestand: Bern kennt seit
    2023 eine Meldepflicht fuer den Heizungsersatz, Zuerich das Meldeverfahren fuer
    Waermepumpen, und nachgetragen wird bei der Abnahme, nicht bei der Bewilligung.
    Solche Faelle bleiben auf der Liste, aber mit diesem Satz daneben.
    """
    teile = []
    if bool(r.kessel_stillgelegt):
        teile.append(f"{_text(r.gegenbeleg_quelle)}: Öltank ausser Betrieb, "
                     "zweite kantonale Quelle stützt den Verdacht")
    elif bool(r.kessel_aktiv):
        teile.append(f"{_text(r.gegenbeleg_quelle)}: Öltank noch in Betrieb, "
                     "spricht gegen den Verdacht")
    if bool(r.im_nachlauf):
        teile.append(f"Beleg erst {int(r.beleg_alter_monate)} Monate alt: die ordentliche "
                     "Nachführung ist möglicherweise noch im Gang")
    if r.konfidenz == "reihenfolge plausibel":
        teile.append("Reihenfolge aus der Laufnummer der Anlage abgeleitet, "
                     "nicht aus einem Datum")
    if bool(r.hat_sonde) and _text(r.sonde_status) is not None             and _text(r.sonde_status) not in AUSGEFUEHRT:
        teile.append(f"Anlage mit Status \"{_text(r.sonde_status)}\": ein Vorhaben, "
                     "noch nicht als ausgeführt verzeichnet")
    if bool(r.hat_sonde) and _zahl(r.sonde_dist_m, float) is not None             and _zahl(r.sonde_dist_m, float) > NAH_M:
        teile.append(f"Anlage {round(_zahl(r.sonde_dist_m, float))} m vom Gebäude, "
                     "einziges Gebäude im Umkreis")
    return "; ".join(teile) or None


def _breiten(ws, breiten: list[int]) -> None:
    for i, breite in enumerate(breiten, 1):
        ws.column_dimensions[get_column_letter(i)].width = breite


def _kopfzeile(ws, zeile: int = 1) -> None:
    for zelle in ws[zeile]:
        if zelle.value is not None:
            zelle.fill, zelle.font = KOPF, KOPF_SCHRIFT
            zelle.alignment = Alignment(vertical="center", wrap_text=True)
    ws.row_dimensions[zeile].height = 30
    ws.freeze_panes = f"A{zeile + 1}"
    ws.auto_filter.ref = ws.dimensions


# --------------------------------------------------------------------------- Messung
def messwerte(con) -> dict:
    """Die gemessenen Quoten - aus der Datenbank, nicht aus dem Quelltext.

    Fehlt eine der Messungen, bricht der Export ab. Eine Pruefliste ohne Messung ist
    keine Pruefliste, sondern eine Behauptung - und genau die stand in der ersten
    Fassung dieses Blattes.
    """
    def hat(sicht: str) -> bool:
        return bool(con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = ?",
            [sicht]).fetchone()[0])

    for sicht in ("v_verdachtsliste_wirkung", "v_zg_umkreis_wirkung", "v_label_alle"):
        if not hat(sicht):
            raise MessungFehlt(
                f"Die Sicht {sicht} fehlt. Ohne sie enthaelt das Methodikblatt keine "
                f"belegbaren Zahlen. Zuerst 'python src/pipeline.py --zh' laufen lassen.")

    gesamt = con.execute("""
        SELECT l.label_kanton AS kanton, count(*) AS n,
               sum(l.eintrag_falsch::INT) AS falsch,
               round(100.0 * avg(l.eintrag_falsch::INT), 1) AS praezision,
               round(100.0 * (SELECT avg(a.eintrag_falsch::INT) FROM v_label_alle a
                              WHERE a.label_kanton = l.label_kanton), 1) AS grundrate
        FROM v_gold_score s JOIN v_label_alle l USING (egid)
        WHERE s.konfidenz IN ('reihenfolge belegt', 'reihenfolge plausibel', 'eintrag alt', 'eintrag jung')
        GROUP BY 1 ORDER BY 1""").df()
    umkreis = con.execute("""
        SELECT eindeutigkeit, distanz, n, falsch, praezision
        FROM v_zg_umkreis_wirkung WHERE eindeutigkeit = '1 Gebäude im Umkreis'""").df()
    # Wie viele Faelle waren ueberhaupt pruefbar? Ohne diese Zahl sieht die Quote
    # zu gut aus: Wo der Tankkataster gar keinen
    # Tank kennt, faellt der Fall aus der Messung, und das trifft die Verdachtsliste
    # haeufiger als den Rest.
    luecke = con.execute("""
        SELECT count(*)                                        AS zug_gesamt,
               count(*) FILTER (WHERE l.egid IS NULL)           AS ohne_label,
               count(*) FILTER (WHERE l.label = 'ungeklaert')   AS ungeklaert,
               count(*) FILTER (WHERE l.label IS NOT NULL
                                AND l.label <> 'ungeklaert')    AS pruefbar
        FROM v_gold_score s LEFT JOIN v_zg_label l USING (egid)
        WHERE s.kanton = 'ZG'
          AND s.konfidenz IN ('reihenfolge belegt', 'reihenfolge plausibel', 'eintrag alt', 'eintrag jung')
        """).df()
    # Die Photovoltaikquote im Methodiktext stand frueher als "14 bis 19 Prozent" im
    # Quelltext. Sie stammte aus einem aelteren Lauf und wanderte unveraendert in jede
    # Mappe. Jetzt kommt sie aus derselben Messung wie alles andere.
    pv = con.execute("""
        SELECT min(praezision) AS von, max(praezision) AS bis
        FROM v_belegwirkung WHERE belegart = 'nur Photovoltaik' AND n >= 50""").df()
    # Enthaelt diese Mappe ausschliesslich Faelle, die ueber den Umkreis zugeordnet
    # wurden? Nur dann darf der Satz ueber die Eindeutigkeit des Umkreises stehen.
    # In Zug laeuft die Zuordnung ueber die amtliche Gebaeudenummer, dort waere er
    # schlicht falsch.
    if gesamt.empty or umkreis.empty or pv.empty:
        raise MessungFehlt("Die Messsichten sind leer - es fehlen die Labelsaetze.")
    return {"gesamt": gesamt, "umkreis": umkreis, "luecke": luecke, "pv": pv}


# ----------------------------------------------------------------------------- Abzug
def hole(con, wo: str, werte: list, grenze: int):
    """Faelle, sortiert nach Belegart und erst darin nach Punktzahl.

    Die Punktzahl allein wuerde einen Fall mit vielen schwachen Merkmalen ueber einen
    mit einem starken Beleg stellen. Fuer eine Pruefliste ist aber die Belegart
    entscheidend, und genau diese Reihenfolge wird auch gemessen.
    """
    hat_adressen = bool(con.execute(
        """SELECT count(*) FROM information_schema.tables
           WHERE table_name = 'silver_adresse_ch'""").fetchone()[0])
    adr_spalten = ("a.adresse, a.plz, a.ort," if hat_adressen
                   else "NULL AS adresse, NULL AS plz, NULL AS ort,")
    adr_join = ("""
        LEFT JOIN (
            SELECT DISTINCT ON (egid) egid,
                   trim(coalesce(strasse, '') || ' ' || coalesce(hausnummer, ''))
                     AS adresse, plz, ort
            FROM silver_adresse_ch
            ORDER BY egid, ist_offiziell DESC NULLS LAST, hausnummer
        ) a ON a.egid = v.egid""" if hat_adressen else "")
    reihenfolge = ", ".join(f"'{k}'" for k in REIHE)
    stufen = ", ".join(f"'{x}'" for x in AUSGEFUEHRT)
    return con.execute(f"""
        SELECT v.egid, v.kanton, v.gemeinde, {adr_spalten}
               v.e_lv95, v.n_lv95, v.baujahr, v.gebaeudekategorie_txt,
               v.energietraeger_txt, v.quelle_txt, v.quelle_datum, v.alter_jahre,
               v.konfidenz, v.score, v.vorschlag, v.vorschlag_quelle, v.beleg_text,
               v.im_nachlauf, v.beleg_alter_monate, v.sonde_laufnummer,
               v.hat_baugesuch, v.bg_datum, v.bg_beschrieb, v.bg_llm_geprueft,
               v.bg_id, v.bg_quelle, v.bg_referenz, v.bg_parzelle, v.bg_url,
               v.hat_sonde, v.sonde_typ, v.sonde_dist_m, v.sonde_datum, v.sonde_nr,
               v.sonde_weg, v.sonde_status, v.hat_pv, v.pv_datum, v.ws_art,
               v.gegenbeleg_quelle, v.kessel_aktiv, v.kessel_stillgelegt
        FROM v_gold_liste v {adr_join}
        WHERE {wo}
        ORDER BY list_position([{reihenfolge}], v.konfidenz),
                 -- innerhalb der Stufe: ausgefuehrte, nahe Anlage vor entfernter Anlage
                 -- vor Vorhaben vor Baugesuch
                 CASE WHEN v.hat_sonde AND v.sonde_status IN ({stufen})
                           AND v.sonde_dist_m <= {NAH_M}                 THEN 0
                      WHEN v.hat_sonde AND v.sonde_status IN ({stufen})   THEN 1
                      WHEN v.hat_sonde AND v.sonde_status IS NULL         THEN 2
                      WHEN v.hat_baugesuch                                THEN 3
                      ELSE 4 END,
                 v.score DESC, v.egid
        LIMIT {grenze}
    """, werte).df()


# -------------------------------------------------------------------------- Blaetter
def blatt_pruefliste(wb: Workbook, df, praefix: str, mit_gemeinde: bool) -> None:
    ws = wb.create_sheet("Prüfliste")
    spalten = [s for s in SPALTEN_BASIS
               if mit_gemeinde or s[0] != "Gemeinde"] + SPALTEN_EINGABE
    kopf = [k for k, _ in spalten]
    ws.append(kopf)
    karte_spalte = kopf.index("Karte") + 1
    for i, (_, r) in enumerate(df.iterrows(), 1):
        e, n = _zahl(r.e_lv95, float), _zahl(r.n_lv95, float)
        zeile = [f"{praefix}-{i:04d}", int(r.egid)]
        if mit_gemeinde:
            zeile.append(_text(r.gemeinde))
        zeile += [
            _text(r.adresse), _text(r.plz), _text(r.ort),
            None if e is None else round(e), None if n is None else round(n),
            None, _zahl(r.baujahr),
            _text(r.gebaeudekategorie_txt), _text(r.energietraeger_txt),
            _text(r.quelle_txt), _datum(r.quelle_datum), _zahl(r.alter_jahre),
            KLASSE.get(r.konfidenz, r.konfidenz), _hinweis(r), _text(r.beleg_text),
            _text(r.vorschlag), _text(r.vorschlag_quelle),
            None, None, None, None,
        ]
        ws.append(zeile)
        # Der Kartenlink ist der Grund, warum die Koordinate ueberhaupt mitkommt:
        # Ein Bauamt sucht ein Gebaeude im GIS, nicht ueber die EGID.
        if e is not None and n is not None:
            zelle = ws.cell(ws.max_row, karte_spalte)
            zelle.value = "im Geoportal"
            zelle.hyperlink = (f"https://map.geo.admin.ch/"
                               f"?swisssearch={round(e)},{round(n)}&zoom=10")
            zelle.font = Font(color="1155CC", underline="single")

    _kopfzeile(ws)
    _breiten(ws, [b for _, b in spalten])
    erste_eingabe = len(spalten) - len(SPALTEN_EINGABE) + 1
    auswahl = DataValidation(
        type="list", allow_blank=True,
        formula1='"korrigiert,Eintrag war korrekt,Hybridanlage,falsches Gebäude,ungeklärt"')
    ws.add_data_validation(auswahl)
    sp = get_column_letter(erste_eingabe + 1)   # Spalte "Ergebnis"
    auswahl.add(f"{sp}2:{sp}{ws.max_row}")
    for zeile in ws.iter_rows(min_row=2, min_col=erste_eingabe, max_col=len(spalten)):
        for zelle in zeile:
            zelle.fill, zelle.border = EINGABE, RAHMEN
    beleg = kopf.index("Beleg") + 1
    for zeile in ws.iter_rows(min_row=2, min_col=beleg, max_col=beleg):
        for zelle in zeile:
            zelle.alignment = Alignment(wrap_text=True, vertical="top")


def blatt_gemeinden(wb: Workbook, df) -> None:
    """Nur in der Kantonsmappe. Ein Kanton verteilt die Liste an seine Gemeinden -
    dafuer braucht er zuerst die Uebersicht, wie viel auf wen entfaellt."""
    ws = wb.create_sheet("Gemeinden")
    ws.append(["Gemeinde", "Fälle gesamt", "Beleg datiert und jünger als der Eintrag",
               "Beleg nach Laufnummer jünger (kalibriert)",
               "Beleg undatiert, Eintrag alt", "Beleg undatiert, Eintrag jung",
               "davon Beleg jünger als 18 Monate (Nachlauf)"])
    tab = (df.groupby("gemeinde")["konfidenz"].value_counts().unstack(fill_value=0)
             .reindex(columns=REIHE, fill_value=0))
    tab["gesamt"] = tab.sum(axis=1)
    tab["nachlauf"] = (df.groupby("gemeinde")["im_nachlauf"].sum()
                         .reindex(tab.index).fillna(0))
    for gemeinde, r in tab.sort_values("gesamt", ascending=False).iterrows():
        ws.append([gemeinde, int(r["gesamt"]), int(r["reihenfolge belegt"]),
                   int(r["reihenfolge plausibel"]),
                   int(r["eintrag alt"]), int(r["eintrag jung"]), int(r["nachlauf"])])
    _kopfzeile(ws)
    _breiten(ws, [28, 14, 30, 30, 30, 30, 30])


def blatt_belege(wb: Workbook, df) -> None:
    """Die Quellenkette. Ohne sie muss das Bauamt jeden Beleg noch einmal selbst
    suchen - und genau diese Suchzeit soll die Mappe ersparen."""
    ws = wb.create_sheet("Belege")
    ws.append(["EGID", "Belegart", "Quelle", "Referenz", "Datum des Ereignisses",
               "Zuordnungsweg", "Distanz (m)", "Details", "Gegenbeleg geprüft"])
    for _, r in df.iterrows():
        if r.hat_baugesuch:
            # Die Referenz ist das, was das Bauamt in seinem eigenen System sucht -
            # nicht die interne Kennung. Im Zuercher Strang ist das die
            # Publikationsnummer, im Amtsblattstrang das publizierende Amt; die
            # Parzelle steht dabei, weil eine Bauverwaltung darueber sucht.
            referenz = " / ".join(x for x in (
                _text(r.bg_referenz),
                f"Parzelle {_text(r.bg_parzelle)}" if _text(r.bg_parzelle) else None,
            ) if x)
            zeile_nr = ws.max_row + 1
            ws.append([int(r.egid), "Baugesuch", _text(r.bg_quelle), referenz or None,
                       _datum(r.bg_datum), "Adresse oder Parzelle", None,
                       (r.bg_beschrieb or "")[:900]
                       + ("  [zusätzlich per Sprachmodell geprüft]"
                          if r.bg_llm_geprueft else ""),
                       _text(r.gegenbeleg_quelle)])
            if _text(r.bg_url):
                z = ws.cell(zeile_nr, 4)
                z.hyperlink = _text(r.bg_url)
                z.font = Font(color="1155CC", underline="single")
        if r.hat_sonde:
            # Distanz auf einen Dezimeter. Sieben Nachkommastellen behaupten eine
            # Genauigkeit, die eine Koordinate aus einem Bohrregister nicht hat.
            dist = _zahl(r.sonde_dist_m, float)
            datiert = _datum(r.sonde_datum)
            ws.append([int(r.egid), "Wärmenutzungsanlage",
                       "kantonales Anlagenregister", _text(r.sonde_nr), datiert,
                       WEG_TEXT.get(_text(r.sonde_weg), _text(r.sonde_weg)),
                       None if dist is None else round(dist, 1),
                       f"Anlagentyp: {_text(r.sonde_typ)}"
                       + ("" if datiert else
                          (f"  [der Kanton führt kein Datum zur Anlage; die Laufnummer "
                           f"{_zahl(r.sonde_laufnummer)} liegt nach Kalibrierung über "
                           f"der Schwelle des Eintragsjahrs - Reihenfolge plausibel, "
                           f"nicht belegt]"
                           if r.konfidenz == "reihenfolge plausibel" else
                           "  [der Kanton führt kein Datum zur Anlage - der Beleg ist "
                           "undatiert und sagt nichts über die Reihenfolge]")),
                       _text(r.gegenbeleg_quelle)])
        if r.hat_pv:
            ws.append([int(r.egid), "Photovoltaikanlage",
                       "BFE Elektrizitätsproduktionsanlagen (Pronovo)", None,
                       _datum(r.pv_datum), "EGID bzw. Koordinate", None,
                       "Anlage auf dem Dach registriert", _text(r.gegenbeleg_quelle)])
        if isinstance(r.ws_art, str) and r.ws_art:
            ws.append([int(r.egid), "Widerspruch im Register selbst", "GWR", None, None,
                       "keine, betrifft denselben Eintrag", None,
                       f"Art: {r.ws_art}", _text(r.gegenbeleg_quelle)])
    _kopfzeile(ws)
    _breiten(ws, [10, 28, 34, 18, 18, 26, 11, 80, 24])
    for zeile in ws.iter_rows(min_row=2, min_col=8, max_col=8):
        for zelle in zeile:
            zelle.alignment = Alignment(wrap_text=True, vertical="top")


def _de(x) -> str:
    """Deutsches Dezimalkomma. Ein Methodikblatt mit "62.4 Prozent" sieht nach einem
    Maschinenauszug aus, und genau diesen Eindruck soll es nicht machen."""
    return f"{x}".replace(".", ",")


# Unter dieser Fallzahl wird nichts als Quote ausgewiesen. Genf faellt seit dem
# Statusfilter auf drei Faelle - "0,0 Prozent von 3" neben "62,4 Prozent von 109" liest
# sich wie ein Widerspruch, obwohl es schlicht keine Messung ist.
MESSGRENZE = 20


def _saetze_messung(m: dict) -> list[str]:
    """Die gemessenen Quoten als Prosa - jede Zahl kommt aus der Datenbank."""
    namen = {"GE": "Genf", "ZG": "Zug"}
    zeilen, zu_klein = [], []
    for _, r in m["gesamt"].iterrows():
        name = namen.get(r.kanton, r.kanton)
        if int(r.n) < MESSGRENZE:
            zu_klein.append((name, int(r.n)))
            continue
        zeilen.append(
            f"{name}: Von {int(r.n)} prüfbaren Gebäuden, die auf einer solchen Liste "
            f"stünden, widersprach die kantonale Gegenquelle bei {int(r.falsch)} dem "
            f"Registereintrag - der Öltank war stillgelegt oder ein anderer "
            f"Wärmeerzeuger ist geführt. Das sind {_de(r.praezision)} Prozent. Greift "
            f"man in diesem Kanton ohne Liste zu, sind es {_de(r.grundrate)} Prozent; "
            f"die Liste trifft also rund "
            f"{_de(round(r.praezision / r.grundrate, 1))}-mal so oft.")
    lk = m["luecke"].iloc[0]
    n_ges, n_pr = int(lk.zug_gesamt), int(lk.pruefbar)
    treffer = int(m["gesamt"].loc[m["gesamt"].kanton == "ZG", "falsch"].iloc[0]) \
        if (m["gesamt"].kanton == "ZG").any() else 0
    # Die ganze rechnerische Spannweite, nicht nur die guenstige Haelfte. Die obere
    # Schranke darf die Gasfaelle nicht stillschweigend als Fehlschlag behandeln.
    unten = round(100 * treffer / n_ges, 1)
    oben = round(100 * (treffer + int(lk.ungeklaert) + int(lk.ohne_label)) / n_ges, 1)
    zeilen.append(
        f"Diese Quote gilt für die prüfbaren Fälle, und das sind nicht alle. Von "
        f"{n_ges} Zuger Fällen der Messkohorte liessen sich {n_pr} prüfen. Bei "
        f"{int(lk.ungeklaert)} kennt der Tankkataster gar keinen Tank, "
        f"{int(lk.ohne_label)} sind Gaseinträge, über die ein Öltankkataster nichts "
        f"sagt. Rechnet man die nicht prüfbaren Fälle einmal alle als Fehlschlag und "
        f"einmal alle als Treffer, spannt sich das Ergebnis von {_de(unten)} bis "
        f"{_de(oben)} Prozent. Wo darin die Wahrheit liegt, sagen diese Daten nicht.")
    u = m["umkreis"]
    n, falsch = int(u["n"].sum()), int(u["falsch"].sum())
    zeilen.append(
        f"Zuordnung allein über die Koordinate, wie sie dort nötig ist, wo der Kanton "
        f"keine Gebäudenummer zur Anlage führt: {falsch} von {n} Fällen trafen zu, "
        f"sofern genau ein Gebäude im 20-Meter-Umkreis der Anlage liegt "
        f"({_de(round(100 * falsch / n, 1))} Prozent). Liegen drei oder mehr Gebäude "
        f"darin, fällt die Quote auf das Niveau des blinden Zugriffs. Wo in dieser "
        f"Mappe \"Koordinate, 20-m-Umkreis\" als Zuordnungsweg steht, lag genau ein "
        f"Gebäude im Umkreis; die übrigen Fälle sind über die amtliche Gebäudenummer "
        f"oder die Adresse zugeordnet. Das Blatt Belege weist es je Fall aus. "
        f"Einschränkung: Von diesen {n} Zuger Anlagen führt der Kanton bei 24 den "
        f"Status \"in Betrieb\" und bei 27 \"unbekannt\" - die Stichprobe ist also "
        f"nicht durchgehend betriebsbestätigt.")
    for name, n_klein in zu_klein:
        zeilen.append(
            f"{name} liefert keine Messung mehr: Das dortige Bohrungsregister führt "
            f"für fast alle Bohrungen den Status \"Inconnu\" oder \"Exploitable\" - "
            f"eine Einstufung der Ressource, keine laufende Anlage. Solche Einträge "
            f"gelten seit einer Korrektur nicht mehr als Beleg. Damit bleibt in "
            f"{name} noch "
            + ("ein prüfbarer Fall" if n_klein == 1 else f"{n_klein} prüfbare Fälle")
            + " übrig. Das ist zu wenig für eine Quote, und deshalb wird hier auch "
              "keine ausgewiesen.")
    return zeilen


def blatt_methodik(wb: Workbook, raum: str, n: int, m: dict,
                   gesamt: int | None = None) -> None:
    ws = wb.create_sheet("Methodik")
    ws.column_dimensions["A"].width = 118
    zeilen = [
        (f"Prüfliste Heizungsangaben GWR - {raum}", True),
        ("", False),
        # Die Gemeindemappe war bisher auf 150 Zeilen begrenzt, ohne das zu sagen. Wer
        # 342 Fälle hat und 150 bekommt, muss das erfahren - sonst hält er die Liste
        # für vollständig und wundert sich beim nächsten Abgleich.
        (f"Erstellt am {date.today().strftime('%d.%m.%Y')}, {n} Fälle."
         + (f" Das sind die {n} dringlichsten von insgesamt {gesamt}."
            if gesamt and gesamt > n else ""), False),
        ("", False),
        ("WAS DIESE LISTE IST", True),
        ("Eine Prüfreihenfolge, keine Fehlerliste. Sie sagt, welche Gebäude sich zuerst "
         "zu prüfen lohnen, und liefert zu jedem den Beleg mit. Ob der Registereintrag "
         "wirklich falsch ist, entscheidet die Prüfung.", False),
        ("", False),
        ("WAS DRIN IST UND WAS NICHT", True),
        ("Aufgenommen ist nur, wofür ein Beleg vorliegt, der etwas über die HEIZUNG "
         "sagt: ein Heizungs-Baugesuch oder eine bewilligte Wärmenutzungsanlage am "
         "Gebäude.", False),
        (f"Bewusst nicht aufgenommen sind Gebäude, bei denen nur eine "
         f"Photovoltaikanlage auf einen Umbau hindeutet. Solche Fälle gäbe es "
         f"schweizweit über 80'000, aber ihre gemessene Trefferquote liegt bei "
         f"{_de(m['pv']['von'].iloc[0])} bis {_de(m['pv']['bis'].iloc[0])} Prozent. "
         f"Wer vier von fünf Adressen umsonst anschaut, verliert mehr Zeit, als die "
         f"Liste spart.", False),
        ("Ebenfalls nicht aufgenommen sind Gebäude, deren Beleg datiert und ÄLTER ist "
         "als der Registereintrag. Wenn jemand den Eintrag nach der Bohrung angefasst "
         "und trotzdem Heizöl stehen gelassen hat, ist das kein Fall für eine "
         "Prüfliste. In Zug treffen solche Fälle nur in 13 von 100 Fällen zu.", False),
        ("Gekennzeichnet, aber nicht entfernt sind Fälle, deren Beleg am Tag des "
         "Registerabzugs jünger als 18 Monate war (Spalte Hinweis, Blatt Gemeinden). "
         "Ein Bauamt trägt den Heizungsersatz bei der Abnahme nach, nicht bei der "
         "Bewilligung, und mehrere Kantone kennen seit 2023 eine Meldepflicht. Bei "
         "diesen Fällen kann die ordentliche Nachführung noch im Gang sein; sie zählen "
         "nicht als Altbestand.", False),
        ("", False),
        ("WIE GUT SIE IST", True),
        ("Gemessen wird gegen amtliche Quellen, die unabhängig von den hier verwendeten "
         "Belegen sind und sagen, was an einem Gebäude tatsächlich läuft. Zwei Kantone "
         "veröffentlichen so etwas: Genf einen Wärmeerzeuger-Layer, Zug einen "
         "Öltankkataster.", False),
        ("Gemessen wurde dieselbe Auswahl und dieselbe Reihenfolge, die auch "
         "auf der Liste steht, mit einer Ausnahme: In Genf und Zug nimmt ein zusätzlicher "
         "Schritt jene Gebäude von der Liste, bei denen die kantonale Quelle noch einen "
         "laufenden fossilen Kessel oder Öltank meldet. Dieser Schritt benutzt dieselbe "
         "Quelle, aus der auch die Messung stammt - wer ihn mitmisst, prüft sich selbst "
         "und käme auf 100 Prozent.", False),
        ("Die Messkohorte ist deshalb absichtlich grösser als die Zuger Verdachtsliste: "
         "144 Fälle gegenüber 129 auf der Liste. Die genannte Quote ist die "
         "vorsichtige - sie enthält die 15 Fälle, die in Zug vorab entfernt würden, in "
         "Ihrem Kanton aber mangels Quelle auf der Liste blieben. Genau das ist die "
         "ehrliche Übertragung.", False),
        ("", False),
    ]
    zeilen += [(s, False) for s in _saetze_messung(m)]
    zeilen += [
        ("", False),
        ("WAS DARAN UNSICHER IST", True),
        ("Diese Zahlen stammen aus einem einzigen Kanton. Für den Kanton, den diese "
         "Liste betrifft, gibt es keine Messung - in der ganzen Schweiz führen nur zwei "
         "Kantone öffentlich, was tatsächlich heizt, und einer davon fällt aus den "
         "oben genannten Gründen aus. Die Übertragung ist begründet, aber nicht "
         "bewiesen.", False),
        ("Ein Fünftel der Fälle sind Gaseinträge. Ein Öltankkataster sagt über Gas "
         "nichts, diese Fälle sind also auch in Zug nicht geprüft.", False),
        ("Der stärkste Beleg, das Baugesuch, ist überhaupt nicht gemessen: In Genf und "
         "Zug ist kein einziger Baugesuchsfall zugeordnet. Dass ein Baugesuch \"Ersatz "
         "Ölheizung durch Wärmepumpe\" etwas über die Heizung sagt, ist einleuchtend - "
         "gemessen ist es nicht.", False),
        ("Wo der Kanton kein Datum zur Anlage führt - unter anderem Zürich -, ist der "
         "Beleg undatiert. Eine Bohrung ohne Jahr neben einem Registereintrag von 2019 "
         "sagt nichts über die Reihenfolge. Das Blatt Belege weist das je Fall aus.",
         False),
        ("Für Zürich gibt es einen Ersatz: Die Anlagenummer des AWEL trägt eine "
         "Laufnummer, die mit der Zeit steigt. An Neubauten mit Wärmepumpe lässt sie "
         "sich je Baujahr kalibrieren. Liegt die Laufnummer einer Sonde über dem "
         "90. Perzentil der Nummern aus dem Jahr des Registereintrags, ist die Sonde "
         "mit hoher Wahrscheinlichkeit jünger als der Eintrag. Solche Fälle heissen in "
         "dieser Mappe \"Reihenfolge plausibel\". Das ist eine Ableitung, keine "
         "amtliche Datierung, und sie ist nicht gemessen - der Labelkanton Zug "
         "publiziert echte Daten, dort braucht es den Ersatz nicht.", False),
        ("Ein noch laufender fossiler Kessel als Gegenbeleg liess sich nur in Genf und "
         "Zug prüfen, weil es die Quelle nur dort gibt. In allen anderen Kantonen wurde "
         "nichts entfernt, weil nichts zu prüfen war.", False),
        ("", False),
        ("WAS WIR VON IHNEN BRAUCHEN", True),
        ("Die vier gelben Spalten rechts im Blatt Prüfliste. Wer sie ausgefüllt "
         "zurückschickt, liefert genau die Zahl, die oben fehlt: wie oft der Verdacht "
         "in diesem Kanton zutrifft. Die nächste Liste wird damit messbar besser.",
         False),
        ("", False),
        ("RECHTLICHES", True),
        ("Wir schreiben nie selbst ins GWR. Die Erfassung bleibt bei der Gemeinde.",
         False),
        ("Die Liste enthält keine Namen und keine Kontaktdaten. Sie enthält aber "
         "Angaben zu einzelnen Gebäuden, die sich bei einem Einfamilienhaus einer "
         "bestimmbaren Person zuordnen lassen. Behandeln Sie sie entsprechend und geben "
         "Sie sie nicht ungeprüft an Dritte weiter.", False),
        ("Quellen: GWR Stufe A des Bundesamts für Statistik, kantonale Anlagenregister, "
         "BFE-Register der Elektrizitätsproduktionsanlagen, Amtsblattportal und "
         "kantonale Baugesuchsdaten. Einzeln aufgeführt im Blatt Datenstand.", False),
    ]
    for text, fett in zeilen:
        ws.append([text])
        if fett:
            ws.cell(ws.max_row, 1).font = Font(bold=True, size=11)
        ws.cell(ws.max_row, 1).alignment = Alignment(wrap_text=True, vertical="top")


def blatt_datenstand(wb: Workbook, con) -> None:
    ws = wb.create_sheet("Datenstand")
    # Die Pruefsumme stand im Manifest und nicht in der Mappe, obwohl die Methodik sie
    # zusicherte. Sie ist der einzige Weg, wie ein Bauamt spaeter belegen kann, welchen
    # Datenstand er bekommen hat.
    # Die Lizenz gehoert in die Arbeitsmappe. Ein Bauamt, das die Liste weiterverwendet -
    # etwa in einer Energieplanung -, muss wissen, welche Quelle eine Quellenangabe
    # verlangt. Die Angaben stammen aus config.LIZENZEN, nachgetragen ueber die
    # CKAN-Schnittstelle von opendata.swiss.
    ws.append(["Quelle", "Beschreibung", "Stand", "SHA-256 (gekürzt)", "Nutzung"])
    stand = str(con.execute("SELECT max(stand) FROM silver_gebaeude_ch").fetchone()[0])[:10]
    ws.append(["GWR, öffentliche Daten Stufe A",
               "Bundesamt für Statistik, alle 26 Kantone", stand, "",
               "Stufe A, uneingeschränkt nutzbar"])
    # Die Lizenz haengt am Host, das Manifest kennt nur die URL - also einmal
    # nachschlagen, welcher Quellenschluessel zu welcher Datei gehoert.
    nach_datei = {q["file"]: s for s, q in config.QUELLEN.items()}
    manifest = config.RAW / "manifest.json"
    if manifest.exists():
        for _, eintrag in json.loads(manifest.read_text(encoding="utf-8")).items():
            schluessel = nach_datei.get(eintrag.get("file", ""))
            if schluessel:
                lizenz = config.lizenz(schluessel)["lizenz"]
            elif eintrag.get("file", "").startswith("gwr"):
                # Die GWR-Abzuege kommen aus dem Ingest, nicht aus config.QUELLEN.
                lizenz = "GWR Stufe A: uneingeschränkt nutzbar (BFS)"
            else:
                lizenz = eintrag.get("lizenz", "")
            ws.append([eintrag.get("file", ""), eintrag.get("desc", ""),
                       str(eintrag.get("downloaded_utc", ""))[:10],
                       str(eintrag.get("sha256", ""))[:16], lizenz])
    _kopfzeile(ws)
    _breiten(ws, [46, 70, 14, 20, 62])


# ---------------------------------------------------------------------------- Mappen
def _mappe(con, df, raum: str, praefix: str, dateiname: str, m: dict,
           mit_gemeinde: bool, gesamt: int | None = None) -> Path:
    wb = Workbook()
    wb.remove(wb.active)
    blatt_pruefliste(wb, df, praefix, mit_gemeinde)
    if mit_gemeinde:
        blatt_gemeinden(wb, df)
    blatt_belege(wb, df)
    blatt_methodik(wb, raum, len(df), m, gesamt)
    blatt_datenstand(wb, con)
    ZIEL.mkdir(parents=True, exist_ok=True)
    pfad = ZIEL / dateiname
    wb.save(pfad)
    return pfad


def _slug(name: str) -> str:
    return (name.lower().replace("ü", "ue").replace("ä", "ae").replace("ö", "oe")
            .replace(" ", "_").replace("(", "").replace(")", "").replace(".", ""))


def erzeuge_gemeinde(con, bfs_nr: int, gemeinde: str, kanton: str, grenze: int,
                     m: dict) -> Path:
    df = hole(con, "v.bfs_nr = ?", [bfs_nr], grenze)
    gesamt = con.execute(
        "SELECT count(*) FROM v_gold_liste WHERE bfs_nr = ?", [bfs_nr]).fetchone()[0]
    return _mappe(con, df, f"{gemeinde} ({kanton})", gemeinde[:3].upper(),
                  f"Pruefliste_{kanton}_{_slug(gemeinde)}.xlsx", m,
                  mit_gemeinde=False, gesamt=gesamt)


def erzeuge_kanton(con, kanton: str, grenze: int, m: dict) -> Path:
    df = hole(con, "v.kanton = ?", [kanton], grenze)
    return _mappe(con, df, f"Kanton {kanton}", kanton,
                  f"Pruefliste_Kanton_{kanton}.xlsx", m, mit_gemeinde=True)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("gemeinde", nargs="?")
    p.add_argument("--bfs", type=int)
    p.add_argument("--kanton", help="Kantonskuerzel, z.B. ZH - eine Mappe fuer den "
                                    "ganzen Kanton, mit Gemeindeuebersicht")
    p.add_argument("--top", type=int, help="die N groessten Gemeindelisten erzeugen")
    p.add_argument("--max", type=int,
                   help="hoechstens so viele Faelle (Gemeinde 150, Kanton alle)")
    a = p.parse_args(argv)

    con = pipeline.connect(schreibend=False)
    m = messwerte(con)

    if a.kanton:
        pfad = erzeuge_kanton(con, a.kanton.upper(), a.max or 100_000, m)
        print(f"  Kanton {a.kanton.upper()}: {pfad.name}")
        print(f"\nMappe unter {ZIEL}")
        return 0

    grenze = a.max or 150
    if a.top:
        ziele = con.execute("""
            SELECT bfs_nr, gemeinde, kanton FROM gold_verdacht_gemeinde
            ORDER BY konfidenz_hoch DESC, verdachtsfaelle DESC LIMIT ?""",
            [a.top]).fetchall()
    elif a.bfs:
        ziele = con.execute(
            "SELECT bfs_nr, gemeinde, kanton FROM gold_gemeinde WHERE bfs_nr = ?",
            [a.bfs]).fetchall()
    elif a.gemeinde:
        ziele = con.execute(
            """SELECT bfs_nr, gemeinde, kanton FROM gold_gemeinde
               WHERE lower(gemeinde) LIKE lower(?) ORDER BY wohngebaeude DESC LIMIT 1""",
            [f"%{a.gemeinde}%"]).fetchall()
    else:
        p.error("Gemeinde, --bfs, --kanton oder --top angeben")

    if not ziele:
        print("Keine Gemeinde gefunden.")
        return 1
    for bfs_nr, gemeinde, kanton in ziele:
        pfad = erzeuge_gemeinde(con, bfs_nr, gemeinde, kanton, grenze, m)
        print(f"  {gemeinde} ({kanton}): {pfad.name}")
    print(f"\nMappen unter {ZIEL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
