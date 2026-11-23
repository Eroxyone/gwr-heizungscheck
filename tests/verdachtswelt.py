"""Erfundene Welt fuer den Verdachts-Layer und die Zuordnung Anlage -> Gebaeude.

Drei Gemeinden: Sondwil im Kanton Zug (der Kanton liefert zu seinen Anlagen EGID, Adresse
und Datum), Bohrikon im Kanton Zuerich (nur Koordinate und GBS-Nummer) und Parzellingen
im Kanton Luzern (die Koordinate der Anlage meint die Parzelle, nicht das Gebaeude). Die
Kantonskuerzel sind echt, weil die SQL-Schritte nach ihnen unterscheiden. Gemeinden,
EGID, Adressen, Anlagen und Baugesuche sind erfunden.

Jedes Gebaeude traegt eine Nummer, die EGID ist 930000000 plus diese Nummer. Jeder Fall
hat seinen eigenen Platz, 500 m vom naechsten entfernt. Was zum Fall gehoert (ein zweites
Gebaeude, Anlage, Baugesuch, Photovoltaik), traegt dieselbe Nummer oder liegt wenige
Meter daneben. Ein Fall laesst sich so lesen, ohne die anderen zu kennen.

Abgelegt wird alles in dem Format, das die SQL-Schritte lesen: Snapshots als Parquet,
Anlagen als GeoJSON und GeoPackage, Baugesuche als JSONL, Photovoltaik als CSV. Nur die
Bronze-Tabellen des Zuercher Strangs und der Gegenbeleg werden direkt gefuellt
(lade_bronze): build_db.py und die Kataster aus Genf und Zug gehoeren nicht zum Pruefling.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import duckdb

import pipeline
from conftest import (
    GAS_BEWILLIGT,
    KODES,
    OEL_VZ,
    SONDE,
    STAND_NEU,
    _gebaeude,
    schreibe_adressen,
    schreibe_gebaeude,
    schreibe_kodes,
)

# Die Schritte des Zuercher Strangs, die der Verdachts-Layer braucht, in der Reihenfolge
# der Pipeline. Nicht dabei: die Tests 1, 2 und 4 sowie die Kataster aus Genf und Zug
# (Gegenbeleg, Labels) mit den Auswertungen, die auf ihnen rechnen.
SCHRITTE = ["silver.sql", "silver_baugesuche.sql", "silver_llm.sql", "match.sql", "test3.sql",
            "test5.sql", "zuordnung_anlagen.sql", "gold_verdacht.sql"]

SONDWIL = ("ZG", 9301, "Sondwil")
BOHRIKON = ("ZH", 9302, "Bohrikon")
PARZELLINGEN = ("LU", 9303, "Parzellingen")
KANTONE = ("ZG", "ZH", "LU")
PLZ = "9300"

# Texte aus dem Merkmalskatalog 4.2 des BFS, soweit die Vorschlaege sie brauchen
KODES_VERDACHT = KODES + [
    ("GENH1", "7512", "Erdregister"),
    ("GENH1", "7513", "Wasser (Grundwasser, Oberflächenwasser, Abwasser)"),
    ("GENH1", "7540", "Holz (generisch)"), ("GENH1", "7570", "Sonne (thermisch)"),
    ("GWAERZH1", "7410", "Wärmepumpe für ein Gebäude"),
    ("GWAERZH1", "7420", "Thermische Solaranlage für ein Gebäude"),
    ("GWAERZH1", "7430", "Heizkessel (generisch) für ein Gebäude"),
    ("GWAERZH1", "7436", "Ofen"),
    ("GWAERZH1", "7460", "Wärmetauscher (einschliesslich für Fernwärme) für ein Gebäude"),
    ("GWAERSCEH1", "865", "Gemäss Daten der Gemeinde"),
]


def egid(nr: int) -> int:
    return 930000000 + nr


def platz(nr: int, dx: float = 0.0, dy: float = 0.0) -> tuple[float, float]:
    """LV95-Koordinate des Platzes `nr`, um dx/dy Meter verschoben. Plaetze bis 99
    liegen in Sondwil, ab 100 in Bohrikon, ab 200 in Parzellingen."""
    if nr < 100:
        return (2680000.0 + 500 * nr + dx, 1225000.0 + dy)
    if nr < 200:
        return (2690000.0 + 500 * (nr - 100) + dx, 1250000.0 + dy)
    return (2660000.0 + 500 * (nr - 200) + dx, 1210000.0 + dy)


# --------------------------------------------------------------------------- Gebaeude
# Nummer -> (Heizung, Koordinate, weitere Merkmale). Die Heizung ist das Tripel aus
# Energietraeger, Informationsquelle und Datum; OEL_VZ ist Heizoel aus der Volkszaehlung
# 2000 mit Datum 29.11.2001.
GAS_NACH_GESUCH_ZG = ("7520", "869", "2025-06-02")
GAS_NACH_GESUCH_ZH = ("7520", "869", "2025-08-04")

GEBAEUDE: dict[int, tuple] = {
    # ---- Sondwil: Zuordnung der Anlagen (Zug liefert EGID und Adresse)
    1: (OEL_VZ, platz(1), {}),              # amtliche EGID, Anlage 50 m entfernt; zweite Anlage in 15 m
    2: (OEL_VZ, platz(2), {}),              # Versorgungsgruppe: Anlage nennt 2 und 3
    3: (OEL_VZ, platz(2, dx=40), {}),
    4: (OEL_VZ, platz(4), {}),              # Anlage 5 m daneben nennt eine unbekannte EGID
    5: (OEL_VZ, platz(5), {}),              # Anlage nennt EGID 5 und die Adresse von 6
    6: (OEL_VZ, platz(5, dx=40), {}),
    7: (OEL_VZ, platz(7), {}),              # nur ueber die Adresse, Anlage 30 m entfernt
    8: (OEL_VZ, platz(8), {}),              # 8 und 9 tragen dieselbe Adresse
    9: (OEL_VZ, platz(8, dx=40), {}),
    10: (OEL_VZ, platz(10), {}),            # Adresse passt, Anlage liegt 250 m entfernt
    11: (GAS_BEWILLIGT, platz(11), {}),     # einziges Gebaeude im Umkreis, Sonde aelter als der Eintrag
    12: (OEL_VZ, platz(12), {}),            # 12 und 13 liegen beide im Umkreis einer Anlage
    13: (OEL_VZ, platz(12, dx=24), {}),
    14: (OEL_VZ, platz(14), {}),            # Anlage 21,2 m entfernt: knapp ausserhalb
    # ---- Sondwil: Belege aus Baugesuch, Photovoltaik und Register
    15: (OEL_VZ, platz(15), {}),            # Baugesuch, nicht nachgefuehrt
    16: (GAS_NACH_GESUCH_ZG, platz(16), {}),    # Baugesuch, nachgefuehrt: Quelle 869 nach dem Gesuch
    17: (OEL_VZ, platz(17), {}),            # nur Photovoltaik
    18: (OEL_VZ, platz(18), {"warmwasser": ("7580", "870", "2019-01-01")}),    # Warmwasser an Fernwaerme
    19: (OEL_VZ, platz(19), {"erzeuger": "7410"}),      # Erzeuger Waermepumpe, Traeger Heizoel
    20: (OEL_VZ, platz(20), {}),            # Baugesuch, Sonde und Photovoltaik zugleich
    21: (OEL_VZ, platz(21), {}),            # Sonde, aber aktiver Kessel im Gegenbeleg
    22: (OEL_VZ, platz(22), {}),            # Sonde. Im juengeren Stand korrigiert auf Erdwaermesonde
    23: (OEL_VZ, platz(23), {}),            # Baugesuch. Im juengeren Stand korrigiert auf Fernwaerme
    24: (SONDE, platz(24), {}),             # Waermepumpe eingetragen, Sonde und Photovoltaik vorhanden
    25: (OEL_VZ, platz(25), {}),            # Baugesuch juenger als 6 Monate
    26: (OEL_VZ, platz(26), {}),            # Anlage bewilligt, aber nicht erstellt
    27: (OEL_VZ, platz(27), {}),            # Anlage ausser Betrieb
    # ---- Bohrikon: Zuerich liefert nur Koordinate und GBS-Nummer
    101: (OEL_VZ, platz(101), {}),          # Laufnummer 12657, nach dem Serienwechsel vergeben
    102: (OEL_VZ, platz(102), {}),          # Laufnummer 1234, aus der alten Serie
    103: (GAS_BEWILLIGT, platz(103), {}),   # Eintrag von 2020, fuer dieses Jahr gibt es keine Schwelle
    104: (OEL_VZ, platz(104), {}),          # 104 und 105 liegen beide im Umkreis einer Sonde
    105: (OEL_VZ, platz(104, dx=24), {}),
    106: (SONDE, platz(106), {}),           # Waermepumpe eingetragen, Grundwasserfassung daneben
    107: (OEL_VZ, platz(107), {}),          # Zuercher Baugesuch mit Textpruefung, nicht nachgefuehrt
    108: (GAS_NACH_GESUCH_ZH, platz(108), {}),  # Zuercher Baugesuch, Quelle 869 nach dem Gesuch
    112: (SONDE, platz(112), {}),           # Sonde. Erst im juengeren Stand als Gas eingetragen
    # ---- Parzellingen: Die Lage der Luzerner Anlagen ist zu ungenau fuer den Umkreis
    201: (OEL_VZ, platz(201), {}),          # Sonde 15 m daneben
}

# Was der juengere Stand anders fuehrt: Zwei Faelle der Liste sind korrigiert, und ein
# Gebaeude mit Waermepumpe ist neu als Gasheizung eingetragen.
IM_JUENGEREN_STAND = {
    22: ("7511", "864", "2026-01-08"),      # wie vorgeschlagen
    23: ("7580", "870", "2026-01-08"),      # vorgeschlagen war eine Luft-Waermepumpe
    112: ("7520", "865", "2026-01-08"),
}

# Nummer -> (Strasse, Hausnummer), so wie das GWR die Adresse fuehrt
ADRESSEN = {
    6: ("Bohrstrasse", "6"), 7: ("Bohrstrasse", "8"), 8: ("Bohrstrasse", "10"),
    9: ("Bohrstrasse", "10"), 10: ("Bohrstrasse", "12"),
    15: ("Gesuchweg", "1"), 16: ("Gesuchweg", "2"), 20: ("Gesuchweg", "3"),
    23: ("Gesuchweg", "4"), 25: ("Gesuchweg", "5"),
    107: ("Amtsgasse", "7"), 108: ("Amtsgasse", "8"),
}


def _gemeinde(nr: int) -> tuple[str, int, str]:
    return SONDWIL if nr < 100 else BOHRIKON if nr < 200 else PARZELLINGEN


def gebaeude(stand: str) -> dict[str, list[dict]]:
    """Die Gebaeude je Kanton zum Stand."""
    je_kanton: dict[str, list[dict]] = {kanton: [] for kanton in KANTONE}
    for nr, (heizung, koordinate, merkmale) in GEBAEUDE.items():
        if stand == STAND_NEU:
            heizung = IM_JUENGEREN_STAND.get(nr, heizung)
        kanton, bfs, name = _gemeinde(nr)
        je_kanton[kanton].append(
            _gebaeude(egid(nr), kanton, bfs, name, heizung, koordinate=koordinate, **merkmale))
    return je_kanton


def adressen(kanton: str) -> list[dict]:
    return [{"EGID": str(egid(nr)), "STRNAME": strasse, "DEINR": hausnr, "DPLZ4": PLZ,
             "DPLZNAME": _gemeinde(nr)[2],
             "DKODE": str(GEBAEUDE[nr][1][0]), "DKODN": str(GEBAEUDE[nr][1][1])}
            for nr, (strasse, hausnr) in ADRESSEN.items() if _gemeinde(nr)[0] == kanton]


# --------------------------------------------------------------------------- Anlagen
# Zug: Erdwaermesonden mit Anlagennummer "ZG-<Nummer des Falls>". Wo nichts anderes
# steht: in Betrieb, ohne EGID, ohne Adresse.
#   9/12 m versetzt = 15 m Abstand, 3/4 m = 5 m, 18/24 m = 30 m, 12/5 m = 13 m
ANLAGEN_ZG = [
    {"anlage_nr": "ZG-01", "ort": platz(1, 30, 40), "egids": str(egid(1)), "bohrdatum": "2015-06-01"},
    # Eine zweite, naeher gelegene Anlage am selben Gebaeude, nur ueber den Umkreis
    {"anlage_nr": "ZG-01b", "ort": platz(1, 9, 12), "bohrdatum": "2010-05-03"},
    {"anlage_nr": "ZG-02", "ort": platz(2, 3, 4), "egids": f"{egid(2)}, {egid(3)}", "bohrdatum": "2015-06-01"},
    {"anlage_nr": "ZG-04", "ort": platz(4, 3, 4), "egids": "999999999", "bohrdatum": "2015-06-01"},
    {"anlage_nr": "ZG-05", "ort": platz(5, 3, 4), "egids": str(egid(5)),
     "strasse": "Bohrstrasse", "hausnummer": "6", "bohrdatum": "2015-06-01"},
    {"anlage_nr": "ZG-07", "ort": platz(7, 18, 24), "strasse": "Bohrstr.", "hausnummer": "8",
     "bohrdatum": "2018-03-01"},
    {"anlage_nr": "ZG-08", "ort": platz(8, 20, 15), "strasse": "Bohrstrasse", "hausnummer": "10",
     "bohrdatum": "2015-06-01"},
    {"anlage_nr": "ZG-10", "ort": platz(10, 0, 250), "strasse": "Bohrstrasse", "hausnummer": "12",
     "bohrdatum": "2015-06-01"},
    {"anlage_nr": "ZG-11", "ort": platz(11, 9, 12), "bohrdatum": "2012-04-02"},
    {"anlage_nr": "ZG-12", "ort": platz(12, 12, 5), "bohrdatum": "2015-06-01"},
    {"anlage_nr": "ZG-14", "ort": platz(14, 15, 15), "bohrdatum": "2015-06-01"},
    {"anlage_nr": "ZG-20", "ort": platz(20, 9, 12), "bohrdatum": "2024-09-02"},
    {"anlage_nr": "ZG-21", "ort": platz(21, 9, 12), "bohrdatum": "2016-05-02"},
    {"anlage_nr": "ZG-22", "ort": platz(22, 9, 12), "bohrdatum": "2017-05-02"},
    {"anlage_nr": "ZG-24", "ort": platz(24, 9, 12), "bohrdatum": "2019-05-02"},
    {"anlage_nr": "ZG-26", "ort": platz(26, 9, 12), "anlagenstatus": "nicht erstellt"},
    {"anlage_nr": "ZG-27", "ort": platz(27, 9, 12), "bohrdatum": "2015-06-01",
     "anlagenstatus": "ausser Betrieb"},
    # Auf dem unbebauten Platz 28, mit der EGID eines Zuercher Gebaeudes
    {"anlage_nr": "ZG-28", "ort": platz(28), "egids": str(egid(101)), "bohrdatum": "2015-06-01"},
]

# Zuerich: Erdwaermesonden mit GBS-Nummer, dazu je eine Grundwasserfassung, eine
# Quellfassung und ein Erdregister. Die Plaetze 109 bis 111 sind unbebaut.
SONDEN_ZH = [
    ("b 00-12657", platz(101, 9, 12)),
    ("b 00-1234", platz(102, 9, 12)),
    ("b 00-12700", platz(103, 9, 12)),
    ("b 00-12800", platz(104, 12, 5)),
    ("b 00-12900", platz(109)),
    ("b 00-13100", platz(112, 9, 12)),
]
# Luzern: Erdwaermesonde mit realisierter Bohrung. Der Kanton liefert WGS84.
SONDEN_LU = [("LU-201", platz(201, 9, 12))]
GRUNDWASSER_ZH = [("g 02-0006", platz(106, 9, 12))]
QUELLFASSUNG_ZH = [platz(110)]
ERDREGISTER_ZH = [platz(111)]

# --------------------------------------------------------------------------- Baugesuche
WP_LUFT = "Ersatz der Ölheizung durch eine Luft/Wasser-Wärmepumpe"
WP_SONDE = "Heizungsersatz: Erdsonden-Wärmepumpe statt Ölheizung"

# Amtsblattportal (Zug): Nummer -> (Publikationsdatum, Beschrieb)
BAUGESUCHE_CH = {
    15: ("2025-03-10", WP_LUFT),
    16: ("2025-03-10", WP_LUFT),
    20: ("2025-02-03", WP_SONDE),
    23: ("2025-03-10", WP_LUFT),
    25: ("2025-10-06", WP_LUFT),            # am Registerstand erst drei Monate alt
}

# OGD-Datensatz des Kantons Zuerich: Nummer -> (Publikationsdatum, Beschrieb). Das dritte
# Gesuch hat keine Adresse im Register. Es setzt nur das juengste Publikationsdatum, von
# dem test3.sql sechs Monate zurueckrechnet.
WP_AUSSEN = "Ersatz Ölheizung durch Luft-Wasser-Wärmepumpe (aussen aufgestellt)"
BAUGESUCHE_ZH = {
    107: ("2024-10-07", WP_AUSSEN),
    108: ("2025-04-07", "Ersatz Ölheizung durch Wärmepumpe"),
    199: ("2025-12-01", "Neubau Velounterstand"),
}
LLM_BEGRUENDUNG = "Die Ölheizung wird durch eine Wärmepumpe ersetzt."

# --------------------------------------------------------------------------- Photovoltaik
# Nummer -> (Inbetriebnahme, mit EGID im kleineren BFE-Abzug). Die Anlage liegt 5 m
# neben dem Gebaeude.
PHOTOVOLTAIK = {
    17: ("2022-06-01", False),
    20: ("2023-05-01", True),
    24: ("2021-03-01", False),
}

# Der Gegenbeleg: An Gebaeude 21 laeuft noch ein Oelkessel, an Gebaeude 1 ist er
# stillgelegt.
GEGENBELEG = [(egid(21), "Testkataster", True, False), (egid(1), "Testkataster", False, True)]


def bg_id(nr: int) -> str:
    return f"00000000-0000-0000-0000-{nr:012d}"


# --------------------------------------------------------------------------- Ablage
def _geojson(ziel: Path, objekte: list[tuple[dict, tuple[float, float]]]) -> None:
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(json.dumps({
        "type": "FeatureCollection",
        "crs": {"type": "name", "properties": {"name": "urn:ogc:def:crs:EPSG::2056"}},
        "features": [{"type": "Feature", "properties": merkmale,
                      "geometry": {"type": "Point", "coordinates": list(ort)}}
                     for merkmale, ort in objekte],
    }, ensure_ascii=False), encoding="utf-8")


def _geopackage_zg(ziel: Path) -> None:
    """Der Zuger Layer, mit den Spalten, die test5.sql daraus liest."""
    ziel.parent.mkdir(parents=True, exist_ok=True)
    spalten = ["anlage_nr", "egids", "strasse", "hausnummer", "verwendungszweck", "bohrdatum",
               "bewilligungsdatum", "anlagenstatus"]
    vorgabe = {"verwendungszweck": "Gebäudeheizung + Warmwasseraufbereitung",
               "anlagenstatus": "in Betrieb"}
    con = duckdb.connect()
    pipeline.lade_spatial(con)
    con.execute("CREATE TABLE a (" + ", ".join(f"{s} VARCHAR" for s in spalten)
                + ", max_heizleistung DOUBLE, e DOUBLE, n DOUBLE)")
    con.executemany(
        f"INSERT INTO a VALUES ({', '.join('?' * (len(spalten) + 3))})",
        [[{**vorgabe, **a}.get(s) for s in spalten] + [8.0, *a["ort"]] for a in ANLAGEN_ZG])
    con.execute(f"""
        COPY (SELECT * EXCLUDE (e, n), ST_Point(e, n) AS geom FROM a)
        TO '{ziel.as_posix()}'
        WITH (FORMAT GDAL, DRIVER 'GPKG', LAYER_NAME 'zg.ews_erdwaermesondenanlagen',
              SRS 'EPSG:2056')""")
    con.close()


def _geojson_lu(ziel: Path) -> None:
    """Der Luzerner Layer in WGS84, mit den Spalten, die test5.sql daraus liest."""
    con = duckdb.connect()
    pipeline.lade_spatial(con)
    objekte = []
    for nummer, (e, n) in SONDEN_LU:
        laenge, breite = con.execute("""
            SELECT ST_X(p), ST_Y(p)
            FROM (SELECT ST_Transform(ST_Point(?, ?), 'EPSG:2056', 'EPSG:4326', always_xy := true) AS p)
            """, [e, n]).fetchone()
        objekte.append({"type": "Feature",
                        "properties": {"Nutzungsnummer": nummer, "Bohrtiefe__m_": 150, "Anzahl_Sonden": 1,
                                       "Bewilligung_Datum": "01.06.2015", "Realisierung_Bohrung": "2015"},
                        "geometry": {"type": "Point", "coordinates": [laenge, breite]}})
    con.close()
    ziel.write_text(json.dumps({"type": "FeatureCollection", "features": objekte}), encoding="utf-8")


def _baugesuche_ch(ziel: Path) -> None:
    """Der Abzug aus dem Amtsblattportal, wie ingest_baugesuche.py ihn schreibt."""
    with ziel.open("w", encoding="utf-8") as fh:
        for nr, (datum, beschrieb) in BAUGESUCHE_CH.items():
            strasse, hausnr = ADRESSEN[nr]
            fh.write(json.dumps({
                "id": bg_id(nr), "ref": f"https://amtsblatt.example/{nr}", "rubrik": "BP-ZG",
                "kanton": "ZG", "datum": datum, "bfs_behoerde": None, "amt": "Bauamt Sondwil",
                "titel": f"Baugesuch - {strasse} {hausnr}, Sondwil", "beschrieb": beschrieb,
                "strasse": strasse, "hausnummer": hausnr, "plz": PLZ, "ort": "Sondwil",
                "adresse_herkunft": "feld", "bfs_nr": None, "parzelle": f"GS {nr}",
                # Kein Gesuch traegt Versicherungsnummer oder Koordinate: DuckDB liest
                # solche Spalten als JSON statt als Text.
                "versicherungs_nr": None, "koordinate": None, "heizungsbezug": True,
            }, ensure_ascii=False) + "\n")


def _photovoltaik(wurzel: Path) -> None:
    """Die beiden BFE-Abzuege: der vollstaendige mit Koordinaten, der kleinere mit EGID."""
    kopf = ["xtf_id", "Address", "PostCode", "Municipality", "Canton", "BeginningOfOperation",
            "InitialPower", "TotalPower", "MainCategory", "SubCategory", "PlantCategory", "_x", "_y"]
    zeilen = []
    for nr, (inbetriebnahme, _) in PHOTOVOLTAIK.items():
        e, n = platz(nr, 3, 4)
        zeilen.append({"xtf_id": str(9000 + nr), "Address": "", "PostCode": PLZ,
                       "Municipality": "Sondwil", "Canton": "ZG",
                       "BeginningOfOperation": inbetriebnahme, "InitialPower": "9.9",
                       "TotalPower": "9.9", "MainCategory": "maincat_2",
                       "SubCategory": "subcat_2", "PlantCategory": "plantcat_8",
                       "_x": str(e), "_y": str(n)})
    for ordner, spalten, auswahl in (
            ("epa", kopf, zeilen),
            ("epa_egid", kopf[:5] + ["EGID"] + kopf[5:],
             [{**z, "EGID": str(egid(int(z["xtf_id"]) - 9000))} for z in zeilen
              if PHOTOVOLTAIK[int(z["xtf_id"]) - 9000][1]])):
        ziel = wurzel / "raw" / ordner / "ElectricityProductionPlant.csv"
        ziel.parent.mkdir(parents=True, exist_ok=True)
        with ziel.open("w", encoding="utf-8-sig", newline="") as fh:
            schreiber = csv.DictWriter(fh, fieldnames=spalten)
            schreiber.writeheader()
            schreiber.writerows(auswahl)


def schreibe_rohdaten(wurzel: Path) -> None:
    """Alles, was nicht vom Registerstand abhaengt: Codeliste, Anlagen, Baugesuche,
    Photovoltaik und das LLM-Urteil zum Zuercher Baugesuch 107."""
    schreibe_kodes(wurzel, KODES_VERDACHT)
    zh = wurzel / "raw" / "waermenutzung_zh"
    _geojson(zh / "erdwaermesonden.json", [
        ({"Waermeentnahme": 20.4, "Sondentiefe": 250, "Gesamtsondenzahl": 2.0, "GBS-Nummer": gbs}, ort)
        for gbs, ort in SONDEN_ZH])
    _geojson(zh / "grundwasserfassung-waermenutzung.json",
             [({"Grundwasserrecht": recht}, ort) for recht, ort in GRUNDWASSER_ZH])
    _geojson(zh / "quellfassung-waermenutzung.json", [({}, ort) for ort in QUELLFASSUNG_ZH])
    _geojson(zh / "erdregister.json", [({}, ort) for ort in ERDREGISTER_ZH])
    _geopackage_zg(wurzel / "raw" / "waermenutzung_weitere" / "ZG_erdwaermenutzung.gpkg")
    _geojson_lu(wurzel / "raw" / "waermenutzung_weitere" / "LU_erdwaermesonden.json")
    _baugesuche_ch(wurzel / "raw" / "baugesuche_ch.jsonl")
    _photovoltaik(wurzel)
    (wurzel / "processed").mkdir(parents=True, exist_ok=True)
    (wurzel / "processed" / "llm_extraktion.jsonl").write_text(json.dumps({
        "text": WP_AUSSEN,
        "llm": {"betrifft_heizung": True, "ist_traegerwechsel": True,
                "neuer_traeger": "waermepumpe", "alter_traeger": "oel", "ist_neubau": False,
                "heizung_ist_hauptzweck": True, "begruendung": LLM_BEGRUENDUNG},
    }, ensure_ascii=False) + "\n", encoding="utf-8")


def schreibe_stand(wurzel: Path, stand: str, kantone: tuple[str, ...] = KANTONE) -> None:
    """Gebaeude- und Adress-Snapshot eines Registerstands fuer die genannten Kantone."""
    alle = gebaeude(stand)
    for kanton in kantone:
        schreibe_gebaeude(wurzel, stand, kanton, alle[kanton])
        schreibe_adressen(wurzel, stand, kanton, adressen(kanton))


def _tabelle(con: duckdb.DuckDBPyConnection, name: str, zeilen: list[dict]) -> None:
    spalten = list(zeilen[0])
    con.execute(f"CREATE OR REPLACE TABLE {name} (" + ", ".join(f'"{s}" VARCHAR' for s in spalten) + ")")
    con.executemany(f"INSERT INTO {name} VALUES ({', '.join('?' * len(spalten))})",
                    [[z[s] for s in spalten] for z in zeilen])


def lade_bronze(con: duckdb.DuckDBPyConnection, stand: str) -> None:
    """Fuellt, was sonst build_db.py und die Kataster-Schritte liefern: die Bronze-Tabellen
    des Zuercher Strangs (Rohexport des Kantons zum Stand, Baugesuche) und die Sicht
    v_gegenbeleg."""
    zh = gebaeude(stand)["ZH"]
    _tabelle(con, "bronze_gwr_gebaeude", [{**g, "LPARZ": None, "EGRID": None} for g in zh])
    _tabelle(con, "bronze_gwr_eingang", adressen("ZH"))
    _tabelle(con, "bronze_baugesuche", [
        {"id": bg_id(nr), "publicationNumber": f"BP-ZH-{nr}", "publicationDate": datum,
         "bfs_nr": str(BOHRIKON[1]), "municipality_name": BOHRIKON[2],
         "projectDescription": beschrieb,
         "projectLocation_address_street": ADRESSEN.get(nr, ("Feldweg", "99"))[0],
         "projectLocation_address_houseNumber": ADRESSEN.get(nr, ("Feldweg", "99"))[1],
         "projectLocation_address_swissZipCode": PLZ,
         "projectLocation_address_town": BOHRIKON[2],
         "districtCadastre_relation_cadastre": f"KTN {nr}"}
        for nr, (datum, beschrieb) in BAUGESUCHE_ZH.items()])
    # Parzellengeometrien liefert der Kanton erst zu einem Teil der Gesuche. Hier keine:
    # Die Zuordnung der Zuercher Gesuche laeuft ueber die Adresse.
    con.execute("""CREATE OR REPLACE TABLE bronze_baugesuche_geo
                   (id VARCHAR, address VARCHAR, url VARCHAR, geom GEOMETRY)""")
    # Spalten wie in der Auffangsicht am Anfang von gold_verdacht.sql
    con.execute("CREATE OR REPLACE TABLE test_gegenbeleg "
                "(egid BIGINT, gegenbeleg_quelle VARCHAR, fossil_aktiv BOOLEAN, fossil_stillgelegt BOOLEAN)")
    con.executemany("INSERT INTO test_gegenbeleg VALUES (?, ?, ?, ?)", GEGENBELEG)
    con.execute("CREATE OR REPLACE VIEW v_gegenbeleg AS SELECT * FROM test_gegenbeleg")


def rechne_stand(con: duckdb.DuckDBPyConnection, wurzel: Path, stand: str,
                 kantone: tuple[str, ...] = KANTONE) -> None:
    """Ein Lauf wie nach einem Snapshot: Stand der genannten Kantone ablegen, dann die
    Pipeline rechnen. Die Zuercher Bronze-Tabellen folgen dem Zuercher Snapshot."""
    schreibe_stand(wurzel, stand, kantone)
    if "ZH" in kantone:
        lade_bronze(con, stand)
    pipeline.run("ch", con)
    pipeline.fuehre_aus(con, SCHRITTE)
