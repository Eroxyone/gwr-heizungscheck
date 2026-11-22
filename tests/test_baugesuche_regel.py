"""Die Stichwortregel fuer Heizungs-Baugesuche gegen das gelabelte Gold-Set.

sql/silver_baugesuche.sql laeuft hier unveraendert ueber die 150 gelabelten Texte aus
data/labels/. Aendert jemand ein Stichwort, zeigt der Test sofort, was das an Precision
und Recall kostet - ohne den Abzug der Baugesuche laden zu muessen.
"""
from __future__ import annotations

import json

import duckdb
import pytest

import config
import pipeline

BRONZE_SPALTEN = [
    "id", "publicationNumber", "publicationDate", "bfs_nr", "municipality_name",
    "projectDescription", "projectLocation_address_street", "projectLocation_address_houseNumber",
    "projectLocation_address_swissZipCode", "projectLocation_address_town",
    "districtCadastre_relation_cadastre",
]


def klassifiziere(texte: dict[str, str]) -> duckdb.DuckDBPyConnection:
    """Legt die Texte als Bronze-Tabelle an und laesst den Silver-Schritt darueber laufen."""
    con = duckdb.connect()
    con.execute("CREATE TABLE bronze_baugesuche ("
                + ", ".join(f'"{s}" VARCHAR' for s in BRONZE_SPALTEN) + ")")
    con.executemany(
        "INSERT INTO bronze_baugesuche (id, publicationDate, projectDescription) VALUES (?, '2025-06-01', ?)",
        list(texte.items()))
    con.execute("CREATE TABLE bronze_baugesuche_geo (id VARCHAR, address VARCHAR, url VARCHAR, geom VARCHAR)")
    con.execute(pipeline._sql("silver_baugesuche.sql"))
    return con


@pytest.fixture(scope="module")
def gold_set():
    proben = json.loads((config.LABELS / "label_stichprobe.json").read_text(encoding="utf-8"))
    labels = json.loads((config.LABELS / "gold_labels.json").read_text(encoding="utf-8"))["labels"]
    con = klassifiziere({str(p["nr"]): p["text"] for p in proben})
    regel = {nr: (heizung, traeger) for nr, heizung, traeger in con.execute(
        "SELECT bg_id, ist_heizungsereignis, neuer_traeger FROM silver_baugesuche").fetchall()}
    con.close()
    return [{"nr": str(p["nr"]), "eingefroren": bool(p["regel_heizung"]),
             "regel": regel[str(p["nr"])][0], "traeger": regel[str(p["nr"])][1],
             **labels[str(p["nr"])]} for p in proben]


def test_gold_set_ist_vollstaendig(gold_set):
    assert len(gold_set) == 150
    assert all(isinstance(g["heizung"], bool) for g in gold_set)


def test_regel_stimmt_mit_dem_eingefrorenen_urteil_ueberein(gold_set):
    # Die Stichprobe haelt fest, was die Regel beim Ziehen sagte. Weicht das heutige Urteil
    # davon ab, wurde die Regel geaendert, und die Zahlen im Bericht gelten nicht mehr.
    abweichend = [g["nr"] for g in gold_set if g["regel"] != g["eingefroren"]]
    assert abweichend == []


def test_heizungsereignis_erkennen(gold_set):
    tp = sum(g["regel"] and g["heizung"] for g in gold_set)
    fp = sum(g["regel"] and not g["heizung"] for g in gold_set)
    fn = sum(not g["regel"] and g["heizung"] for g in gold_set)
    # Gemessen und in reports/extraktion_evaluation.md ausgewiesen: 95,6 % und 97,7 %
    assert round(100 * tp / (tp + fp), 1) == 95.6
    assert round(100 * tp / (tp + fn), 1) == 97.7


def test_neuer_energietraeger_wird_nie_falsch_benannt(gold_set):
    benannt = [g for g in gold_set if g["regel"] and g["wechsel"] and g["neu"] is not None]
    assert len(benannt) > 30
    assert [g["nr"] for g in benannt if g["traeger"] != g["neu"]] == []


@pytest.mark.parametrize("text, ereignis, traeger", [
    ("Ersatz Ölheizung durch Luft/Wasser-Wärmepumpe", True, "waermepumpe"),
    ("Erdsondenbohrung für Sole-Wasser-Wärmepumpe", True, "waermepumpe"),
    ("Anschluss an den Wärmeverbund, Rückbau Öltank", True, "fernwaerme"),
    ("Neue Pelletheizung im Untergeschoss", True, "holz"),
    ("Heizungsersatz", True, "unklar"),
    # Netzinfrastruktur ohne Gebaeudebezug ist kein Heizungsereignis am Gebaeude
    ("Neubau Fernwärmeleitung in der Hauptstrasse", False, None),
    # Ein umgenutzter Heizungsraum sagt nichts ueber den Energietraeger
    ("Umnutzung Heizungsraum zu Veloraum", False, None),
    ("Anbau Wintergarten und neue Dachfenster", False, None),
])
def test_einzelfaelle(text, ereignis, traeger):
    con = klassifiziere({"x": text})
    assert con.execute(
        "SELECT ist_heizungsereignis, neuer_traeger FROM silver_baugesuche").fetchone() == (ereignis, traeger)


def test_bauherrschaft_wird_vor_der_klassifikation_entfernt():
    # Der Name ist erfunden. Das Muster "K Nachname Vorname" am Ende des Beschriebs kam in
    # einzelnen Gemeinden im offenen Datensatz vor.
    con = klassifiziere({"x": "2025-053 Wärmepumpe (aussen aufgestellt), GS 83, Musterweg 2f, K Muster Hans"})
    beschrieb, ereignis = con.execute(
        "SELECT beschrieb, ist_heizungsereignis FROM silver_baugesuche").fetchone()
    assert "Muster Hans" not in beschrieb
    assert beschrieb.endswith("[Bauherrschaft entfernt]")
    assert ereignis is True
