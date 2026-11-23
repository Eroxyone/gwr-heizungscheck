"""Zuordnung Anlage -> Gebaeude (sql/zuordnung_anlagen.sql) gegen die erfundene Welt.

Jede erwartete Zahl laesst sich in tests/verdachtswelt.py nachzaehlen: 18 Zuger Anlagen
(ANLAGEN_ZG), 9 Zuercher (sechs Sonden, je eine Grundwasserfassung, Quellfassung und ein
Erdregister) und eine Luzerner Sonde. Die Anlage "ZG-07" gehoert zum Gebaeude 7 mit der
EGID 930000007.
"""
from __future__ import annotations

from verdachtswelt import egid


def entscheidung(con, anlage_nr: str) -> tuple:
    """Entscheidung und zugeordnete EGID einer Anlage."""
    zeilen = con.execute("""
        SELECT e.entscheidung, e.egid
        FROM anlage_entscheidung e JOIN silver_waermenutzung a USING (anlage_id)
        WHERE a.anlage_nr = ?""", [anlage_nr]).fetchall()
    assert len(zeilen) == 1, f"genau eine Entscheidung fuer {anlage_nr} erwartet"
    return zeilen[0]


def kandidaten(con, anlage_nr: str) -> list[tuple]:
    """Kandidaten einer Anlage: Weg, EGID, gueltig, Distanz in Metern."""
    return con.execute("""
        SELECT k.weg, k.egid, k.gueltig, round(k.dist_m, 1)
        FROM anlage_kandidaten k JOIN silver_waermenutzung a USING (anlage_id)
        WHERE a.anlage_nr = ? ORDER BY 1, 2""", [anlage_nr]).fetchall()


# --------------------------------------------------------------------------- Ueberblick

def test_jede_anlage_bekommt_genau_eine_entscheidung(verdacht):
    assert verdacht.execute("SELECT count(*) FROM silver_waermenutzung").fetchone()[0] == 28
    assert verdacht.execute(
        "SELECT count(*), count(DISTINCT anlage_id) FROM anlage_entscheidung").fetchone() == (28, 28)

    verteilung = dict(verdacht.execute(
        "SELECT entscheidung, count(*) FROM anlage_entscheidung GROUP BY 1").fetchall())
    assert verteilung == {
        "amtlich": 1,                       # ZG-01
        "adresse": 1,                       # ZG-07
        # ZG-01b, -11, -20, -21, -22, -24, -26, -27, vier Zuercher Sonden, die
        # Grundwasserfassung und die Luzerner Sonde
        "umkreis_eindeutig": 14,
        "offen_versorgungsgruppe": 1,       # ZG-02
        "offen_amtlich_ungueltig": 2,       # ZG-04, ZG-28
        "offen_quellenkonflikt": 1,         # ZG-05
        "offen_adresse_mehrdeutig": 1,      # ZG-08
        "offen_adresse_lage": 1,            # ZG-10
        "offen_umkreis_mehrdeutig": 2,      # ZG-12 und die Sonde b 00-12800
        # ZG-14, die Sonde b 00-12900, die Quellfassung und das Erdregister
        "offen_kein_kandidat": 4,
    }
    # Zugeordnet ist genau, was amtlich, ueber die Adresse oder eindeutig im Umkreis liegt
    assert verdacht.execute(
        "SELECT count(*) FROM anlage_entscheidung WHERE egid IS NOT NULL").fetchone()[0] == 16


def test_kandidaten_je_weg(verdacht):
    # amtlich: ZG-01, ZG-02 (zwei EGID), ZG-04, ZG-05, ZG-28
    # adresse: ZG-05, ZG-07, ZG-08 (zwei Gebaeude), ZG-10
    # umkreis: ZG-01b, -02, -04, -05, -11, -20, -21, -22, -24, -26, -27 je eines, ZG-12 zwei,
    #          in Zuerich vier Sonden und die Grundwasserfassung je eines, b 00-12800 zwei,
    #          die Luzerner Sonde eines
    je_weg = dict(verdacht.execute(
        "SELECT weg, count(*) FROM anlage_kandidaten GROUP BY 1").fetchall())
    assert je_weg == {"amtlich": 6, "adresse": 5, "umkreis": 21}


# --------------------------------------------------------------------------- Stufe 1: amtliche EGID

def test_amtliche_egid_gilt_auch_ausserhalb_des_umkreises(verdacht):
    # Die Anlage liegt 50 m vom Gebaeude entfernt (30/40 m versetzt), der Kanton nennt
    # die EGID selbst.
    assert kandidaten(verdacht, "ZG-01") == [("amtlich", egid(1), True, 50.0)]
    assert entscheidung(verdacht, "ZG-01") == ("amtlich", egid(1))


def test_mehrere_amtliche_egid_bleiben_als_versorgungsgruppe_offen(verdacht):
    # Gebaeude 2 liegt 5 m neben der Anlage und waere im Umkreis das einzige. Die
    # amtliche Angabe nennt aber zwei Gebaeude, also wird keines zugeordnet.
    assert kandidaten(verdacht, "ZG-02") == [
        ("amtlich", egid(2), True, 5.0),
        ("amtlich", egid(3), True, 37.2),       # 37 m und 4 m versetzt
        ("umkreis", egid(2), True, 5.0),
    ]
    assert entscheidung(verdacht, "ZG-02") == ("offen_versorgungsgruppe", None)


def test_unbekannte_amtliche_egid_faellt_nicht_auf_den_umkreis_zurueck(verdacht):
    assert kandidaten(verdacht, "ZG-04") == [
        ("amtlich", 999999999, False, None),
        ("umkreis", egid(4), True, 5.0),
    ]
    assert entscheidung(verdacht, "ZG-04") == ("offen_amtlich_ungueltig", None)


def test_amtliche_egid_aus_einem_anderen_kanton_gilt_nicht(verdacht):
    # Die Zuger Anlage nennt die EGID des Zuercher Gebaeudes 101. Das Gebaeude besteht,
    # liegt aber nicht im Kanton der Anlage.
    assert [k[:3] for k in kandidaten(verdacht, "ZG-28")] == [("amtlich", egid(101), False)]
    assert entscheidung(verdacht, "ZG-28") == ("offen_amtlich_ungueltig", None)


def test_widerspruch_zwischen_egid_und_adresse_bleibt_offen(verdacht):
    # Die Anlage nennt die EGID von Gebaeude 5 und die Adresse von Gebaeude 6.
    assert kandidaten(verdacht, "ZG-05") == [
        ("adresse", egid(6), True, 37.2),
        ("amtlich", egid(5), True, 5.0),
        ("umkreis", egid(5), True, 5.0),
    ]
    assert entscheidung(verdacht, "ZG-05") == ("offen_quellenkonflikt", None)


# --------------------------------------------------------------------------- Stufe 2: Adresse

def test_adresse_ordnet_zu_wenn_sie_genau_ein_gebaeude_trifft(verdacht):
    # "Bohrstr. 8" bei der Anlage, "Bohrstrasse 8" im Register. Die Anlage liegt 30 m
    # entfernt (18/24 m versetzt), der Umkreis haette sie nicht gefunden.
    assert kandidaten(verdacht, "ZG-07") == [("adresse", egid(7), True, 30.0)]
    assert entscheidung(verdacht, "ZG-07") == ("adresse", egid(7))


def test_adresse_mit_zwei_gebaeuden_bleibt_offen(verdacht):
    assert [k[:2] for k in kandidaten(verdacht, "ZG-08")] == [("adresse", egid(8)), ("adresse", egid(9))]
    assert entscheidung(verdacht, "ZG-08") == ("offen_adresse_mehrdeutig", None)


def test_adresse_weit_weg_von_der_anlage_bleibt_offen(verdacht):
    # 250 m zwischen Anlage und Gebaeude, die Grenze liegt bei 200 m.
    assert kandidaten(verdacht, "ZG-10") == [("adresse", egid(10), True, 250.0)]
    assert entscheidung(verdacht, "ZG-10") == ("offen_adresse_lage", None)


# --------------------------------------------------------------------------- Stufe 3: Umkreis

def test_genau_ein_gebaeude_im_umkreis_wird_zugeordnet(verdacht):
    # 9/12 m versetzt, also 15 m entfernt
    assert kandidaten(verdacht, "ZG-11") == [("umkreis", egid(11), True, 15.0)]
    assert entscheidung(verdacht, "ZG-11") == ("umkreis_eindeutig", egid(11))
    # Zuerich liefert weder EGID noch Adresse, dort gibt es nur diesen Weg
    assert entscheidung(verdacht, "b 00-12657") == ("umkreis_eindeutig", egid(101))
    assert entscheidung(verdacht, "g 02-0006") == ("umkreis_eindeutig", egid(106))


def test_zwei_gebaeude_im_umkreis_werden_nicht_zugeordnet(verdacht):
    # Die Anlage liegt zwischen zwei Gebaeuden, je 13 m entfernt (12/5 m versetzt).
    assert kandidaten(verdacht, "ZG-12") == [
        ("umkreis", egid(12), True, 13.0),
        ("umkreis", egid(13), True, 13.0),
    ]
    assert entscheidung(verdacht, "ZG-12") == ("offen_umkreis_mehrdeutig", None)
    assert entscheidung(verdacht, "b 00-12800") == ("offen_umkreis_mehrdeutig", None)


def test_gebaeude_knapp_ausserhalb_des_umkreises_zaehlt_nicht(verdacht):
    # 15 m nach Osten und 15 m nach Norden: innerhalb des Suchquadrats von 20 m, aber
    # 21,2 m entfernt.
    assert kandidaten(verdacht, "ZG-14") == []
    assert entscheidung(verdacht, "ZG-14") == ("offen_kein_kandidat", None)
    assert entscheidung(verdacht, "b 00-12900") == ("offen_kein_kandidat", None)


def test_anlagen_ohne_nummer_auf_unbebautem_platz_bleiben_offen(verdacht):
    offen = verdacht.execute("""
        SELECT a.anlagentyp, e.entscheidung
        FROM anlage_entscheidung e JOIN silver_waermenutzung a USING (anlage_id)
        WHERE a.anlagentyp IN ('quellfassung', 'erdregister') ORDER BY 1""").fetchall()
    assert offen == [("erdregister", "offen_kein_kandidat"), ("quellfassung", "offen_kein_kandidat")]


# --------------------------------------------------------------------------- Diagnostik

def test_match_waermenutzung_fuehrt_alle_nachbarn_im_umkreis(verdacht):
    # Die Diagnosetabelle waehlt nicht aus: Sie fuehrt jeden Umkreis-Kandidaten, auch die
    # beiden Gebaeude einer mehrdeutigen Anlage.
    assert verdacht.execute(
        "SELECT count(*), count(DISTINCT weg) FROM match_waermenutzung").fetchone() == (21, 1)
    nachbarn = verdacht.execute("""
        SELECT m.egid FROM match_waermenutzung m JOIN silver_waermenutzung a USING (anlage_id)
        WHERE a.anlage_nr = 'ZG-12' ORDER BY 1""").fetchall()
    assert nachbarn == [(egid(12),), (egid(13),)]


# --------------------------------------------------------------------------- Listensignal

def test_v_test5_fuehrt_nur_fossile_gebaeude_mit_gebauter_anlage(verdacht):
    signal = verdacht.execute("""
        SELECT egid, zuordnungsweg, anlage_nr, round(dist_m, 1), gebaeude_im_umkreis, sonde_laufnummer
        FROM v_test5 ORDER BY egid""").fetchall()
    assert signal == [
        (egid(1), "amtlich", "ZG-01", 50.0, None, None),
        (egid(7), "adresse", "ZG-07", 30.0, None, None),
        (egid(11), "umkreis_eindeutig", "ZG-11", 15.0, 1, None),
        (egid(20), "umkreis_eindeutig", "ZG-20", 15.0, 1, None),
        (egid(21), "umkreis_eindeutig", "ZG-21", 15.0, 1, None),
        (egid(101), "umkreis_eindeutig", "b 00-12657", 15.0, 1, 12657),
        (egid(102), "umkreis_eindeutig", "b 00-1234", 15.0, 1, 1234),
        (egid(103), "umkreis_eindeutig", "b 00-12700", 15.0, 1, 12700),
        (egid(112), "umkreis_eindeutig", "b 00-13100", 15.0, 1, 13100),
    ]
    # Zugeordnet, aber kein Signal:
    #   22       im juengeren Stand nicht mehr fossil
    #   24, 106  Waermepumpe eingetragen
    #   26       Anlage "nicht erstellt": nicht gebaut
    #   27       Anlage "ausser Betrieb": gebaut, belegt aber keine laufende Waermepumpe
    for nr, anlage in ((22, "ZG-22"), (24, "ZG-24"), (26, "ZG-26"), (27, "ZG-27"), (106, "g 02-0006")):
        assert entscheidung(verdacht, anlage) == ("umkreis_eindeutig", egid(nr))


def test_ungenaue_lage_traegt_ueber_den_umkreis_kein_signal(verdacht):
    # In Luzern meint die Koordinate der Anlage die Parzelle (v_lage_ungenau). Die Sonde
    # liegt 15 m neben dem einzigen Gebaeude und wird ihm zugeordnet, das Gebaeude ist
    # fossil eingetragen - ein Signal ist das trotzdem nicht.
    assert verdacht.execute("SELECT kanton FROM v_lage_ungenau").fetchall() == [("LU",)]
    assert entscheidung(verdacht, "LU-201") == ("umkreis_eindeutig", egid(201))
    assert kandidaten(verdacht, "LU-201") == [("umkreis", egid(201), True, 15.0)]
    assert verdacht.execute("SELECT count(*) FROM v_test5 WHERE kanton = 'LU'").fetchone()[0] == 0


def test_amtliche_zuordnung_hat_vorrang_vor_der_naeheren_anlage(verdacht):
    # Gebaeude 1 hat zwei Anlagen: ZG-01 amtlich in 50 m, ZG-01b im Umkreis in 15 m.
    # Das Signal traegt die amtlich zugeordnete und deren Bohrdatum.
    assert entscheidung(verdacht, "ZG-01b") == ("umkreis_eindeutig", egid(1))
    assert verdacht.execute("""
        SELECT anlage_nr, zuordnungsweg, datum_bewilligung::VARCHAR FROM v_test5
        WHERE egid = ?""", [egid(1)]).fetchall() == [("ZG-01", "amtlich", "2015-06-01")]
