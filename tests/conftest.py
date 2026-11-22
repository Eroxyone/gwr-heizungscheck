"""Gemeinsame Testbasis: ein kleines, erfundenes Register mit genau bekannten Eigenschaften.

Die echte Pipeline rechnet ueber 3,17 Mio Gebaeude und braucht rund 910 MB Rohdaten. Die
Tests brauchen davon nichts: Sie bauen in einem temporaeren Verzeichnis zwei Snapshot-
Staende mit zwei Dutzend Gebaeuden auf, lassen die unveraenderten SQL-Schritte darueber
laufen und pruefen die Ergebnisse gegen Zahlen, die sich von Hand nachzaehlen lassen.

Alle Gemeinden, EGID und Adressen hier sind erfunden.
"""
from __future__ import annotations

import csv
from pathlib import Path

import duckdb
import pytest

import config
import pipeline

STAND_ALT = "2026-01-05"
STAND_NEU = "2026-01-12"

OEL_VZ = ("7530", "860", "2001-11-29")       # Heizoel, Quelle Volkszaehlung 2000
GAS_BEWILLIGT = ("7520", "869", "2020-05-01")
SONDE = ("7511", "869", "2023-03-01")
UNBESTIMMT = ("7598", "859", "2012-01-01")
FERNWAERME = ("7580", "870", "2024-06-01")


def _gebaeude(egid, kanton, bfs, gemeinde, heizung, gkat="1020", gstat="1004"):
    traeger, quelle, datum = heizung
    return {
        "EGID": str(egid), "GDEKT": kanton, "GGDENR": str(bfs), "GGDENAME": gemeinde,
        "GKODE": "2700000.0", "GKODN": "1200000.0", "GSTAT": gstat, "GKAT": gkat,
        "GKLAS": "1110", "GBAUJ": "1975", "GAREA": "120", "GASTW": "2", "GANZWHG": "1",
        "GWAERZH1": "7436", "GENH1": traeger, "GWAERSCEH1": quelle, "GWAERDATH1": datum,
        "GWAERZW1": None, "GENW1": None, "GWAERSCEW1": None, "GWAERDATW1": None,
    }


def _stand_neu() -> dict[str, list[dict]]:
    """Der juengere Stand. Kanton AI traegt die Aenderungen, Kanton ZG bleibt unveraendert."""
    ai = lambda egid, heizung, **kw: _gebaeude(egid, "AI", 9001, "Testwil", heizung, **kw)  # noqa: E731
    zg = lambda egid, heizung: _gebaeude(egid, "ZG", 9002, "Musterhausen", heizung)         # noqa: E731
    return {
        "AI": [
            ai(900000001, OEL_VZ),
            ai(900000002, OEL_VZ),
            ai(900000003, ("7511", "864", "2026-01-08")),      # im alten Stand: OEL_VZ
            ai(900000004, ("7511", "864", "2026-01-08")),      # im alten Stand: OEL_VZ
            ai(900000005, ("7520", "869", "2026-01-09")),      # im alten Stand: GAS_BEWILLIGT
            ai(900000006, GAS_BEWILLIGT),
            ai(900000007, SONDE),
            ai(900000008, SONDE),
            ai(900000009, SONDE),
            ai(900000010, UNBESTIMMT),
            ai(900000011, OEL_VZ, gkat="1060"),                # ohne Wohnnutzung
            ai(900000012, OEL_VZ, gstat="1007"),               # abgebrochen
            ai(900000013, ("7501", "869", "2025-12-01")),      # Zugang, fehlt im alten Stand
        ],
        "ZG": [zg(900000101 + i, OEL_VZ) for i in range(3)]
              + [zg(900000104 + i, FERNWAERME) for i in range(3)],
    }


def _stand_alt() -> dict[str, list[dict]]:
    neu = _stand_neu()
    vorher = {"900000003": OEL_VZ, "900000004": OEL_VZ, "900000005": GAS_BEWILLIGT}
    ai = []
    for g in neu["AI"]:
        if g["EGID"] == "900000013":
            continue
        if g["EGID"] in vorher:
            g = {**g, **dict(zip(("GENH1", "GWAERSCEH1", "GWAERDATH1"), vorher[g["EGID"]], strict=True))}
        ai.append(g)
    # Abgang: steht nur im alten Stand
    ai.append(_gebaeude(900000014, "AI", 9001, "Testwil", OEL_VZ))
    return {"AI": ai, "ZG": neu["ZG"]}


ADRESSEN = [
    # EGID, Strasse, Hausnummer, offizielle Adresse
    ("900000001", "Bahnhofstr.", "4a", "1"),
    ("900000002", "Bahnhofstrasse", "4 A", "1"),
    ("900000003", "Dorfgasse", "007", "1"),
    ("900000003", "Dorfgasse", "7b", "0"),
]

KODES = [
    ("GENH1", "7501", "Luft"), ("GENH1", "7511", "Erdwärmesonde"), ("GENH1", "7520", "Gas"),
    ("GENH1", "7530", "Heizöl"), ("GENH1", "7580", "Fernwärme (generisch)"),
    ("GENH1", "7598", "Unbestimmt"),
    ("GWAERSCEH1", "859", "Andere"), ("GWAERSCEH1", "860", "Gemäss Volkszählung 2000"),
    ("GWAERSCEH1", "864", "Gemäss kantonalen Daten / Das Gebäudeprogramm"),
    ("GWAERSCEH1", "869", "Gemäss Baubewilligung"),
    ("GWAERSCEH1", "870", "Gemäss Versorgungswerk (Gas, Fernwärme)"),
    ("GKAT", "1020", "Gebäude mit ausschliesslicher Wohnnutzung"),
    ("GKAT", "1060", "Gebäude ohne Wohnnutzung"),
]


def _schreibe_parquet(ziel: Path, zeilen: list[dict], spalten: list[str]) -> None:
    ziel.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.execute("CREATE TABLE t (" + ", ".join(f'"{s}" VARCHAR' for s in spalten) + ")")
    con.executemany(f"INSERT INTO t VALUES ({', '.join('?' * len(spalten))})",
                    [[z.get(s) for s in spalten] for z in zeilen])
    con.execute(f"COPY t TO '{ziel.as_posix()}' (FORMAT PARQUET)")
    con.close()


def baue_register(wurzel: Path) -> None:
    """Legt Snapshots, Adressen und Codeliste so ab, wie ingest.py sie hinterlaesst."""
    for stand, kantone in ((STAND_ALT, _stand_alt()), (STAND_NEU, _stand_neu())):
        for kanton, gebaeude in kantone.items():
            _schreibe_parquet(
                wurzel / "snapshots" / "gwr" / f"snapshot_date={stand}" / f"kanton={kanton}" / "data.parquet",
                [{**g, "GEXPDAT": stand} for g in gebaeude], config.SNAPSHOT_SPALTEN)
    _schreibe_parquet(
        wurzel / "snapshots" / "gwr_adresse" / f"snapshot_date={STAND_NEU}" / "kanton=AI" / "data.parquet",
        [{"EGID": egid, "STRNAME": strasse, "DEINR": nr, "DPLZ4": "9000", "DPLZNAME": "Testwil",
          "DKODE": "2700000.0", "DKODN": "1200000.0", "DOFFADR": offiziell, "DEXPDAT": STAND_NEU}
         for egid, strasse, nr, offiziell in ADRESSEN],
        config.SNAPSHOT_SPALTEN_EINGANG)

    (wurzel / "raw").mkdir(parents=True, exist_ok=True)
    with (wurzel / "raw" / "kodes_codes_codici.csv").open("w", encoding="utf-8", newline="") as fh:
        schreiber = csv.writer(fh, delimiter="\t")
        schreiber.writerow(["CECODID", "CMERKM", "CODTXTLD"])
        schreiber.writerows((code, merkmal, text) for merkmal, code, text in KODES)


@pytest.fixture(scope="session")
def register(tmp_path_factory) -> duckdb.DuckDBPyConnection:
    """Der schweizweite Strang der Pipeline, gerechnet ueber das erfundene Register."""
    wurzel = tmp_path_factory.mktemp("gwr")
    baue_register(wurzel)
    mp = pytest.MonkeyPatch()
    mp.setattr(config, "DATA", wurzel)
    mp.setattr(config, "RAW", wurzel / "raw")
    mp.setattr(config, "SNAPSHOTS", wurzel / "snapshots")
    mp.setattr(config, "PROCESSED", wurzel / "processed")
    mp.setattr(config, "DB", wurzel / "processed" / "gwr.duckdb")
    con = pipeline.run("ch")
    yield con
    con.close()
    mp.undo()
