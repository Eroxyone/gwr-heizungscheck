"""Verdachts-Layer (sql/gold_verdacht.sql) gegen die erfundene Welt.

Jede erwartete Zahl laesst sich in tests/verdachtswelt.py nachzaehlen. Gebaeude 15 hat
die EGID 930000015. Wo nichts anderes steht, gilt der juengere Registerstand vom
12.01.2026: Ein Eintrag aus der Volkszaehlung (29.11.2001) ist dann 25 Jahre alt.

Die Punkte eines Falls:
    Baugesuch 50 (mit Textpruefung 55)   Sonde 40   Photovoltaik 18
    Erzeuger-Widerspruch 15   Quelle 860: 12   Eintrag 20 Jahre und aelter: 15
"""
from __future__ import annotations

import datetime as dt

import pipeline
import verdachtswelt as welt
from conftest import STAND_ALT, STAND_NEU, datenverzeichnis
from verdachtswelt import egid

VORSCHLAG_SONDE = "GENH1 7511 Erdwärmesonde, GWAERZH1 7410 Wärmepumpe für ein Gebäude"
VORSCHLAG_LUFT = "GENH1 7501 Luft, GWAERZH1 7410 Wärmepumpe für ein Gebäude"
QUELLE_KANTON = "GWAERSCEH1 864 Gemäss kantonalen Daten / Das Gebäudeprogramm"
QUELLE_BAUBEWILLIGUNG = "GWAERSCEH1 869 Gemäss Baubewilligung"
QUELLE_GEMEINDE = "GWAERSCEH1 865 Gemäss Daten der Gemeinde"

# Was auf der Liste steht: Nummer -> Stufe
LISTE = {
    1: "reihenfolge belegt",        # Sonde 2015, Eintrag 2001
    7: "reihenfolge belegt",        # Sonde 2018, Eintrag 2001
    15: "reihenfolge belegt",       # Baugesuch 2025, Eintrag 2001
    19: "eintrag alt",              # Erzeuger-Widerspruch ohne Datum, Quelle 860
    20: "reihenfolge belegt",       # Baugesuch 2025, Eintrag 2001
    101: "reihenfolge plausibel",   # Laufnummer 12657 ueber der Schwelle 10100
    102: "eintrag alt",             # Laufnummer 1234 darunter, Quelle 860
    103: "eintrag jung",            # Eintrag von 2020, keine Schwelle fuer dieses Jahr
    107: "reihenfolge belegt",      # Zuercher Baugesuch 2024, Eintrag 2001
    112: "eintrag jung",            # Sonde ohne Datum, Gaseintrag vom 08.01.2026
}
# Ein Verdacht, aber nicht auf der Liste
NICHT_AUF_DER_LISTE = {
    11: "beleg vor eintrag",        # Sonde 2012, Eintrag 2020
    17: "nur Solaranlage",
    18: "nur Metadaten",            # Warmwasser an Fernwaerme, sonst nichts
}
# Auf der Liste waere Gebaeude 21, aber dort laeuft laut Gegenbeleg noch ein Kessel.
WIDERLEGT = {21: "reihenfolge belegt"}


def spalte(con, sicht: str, ausdruck: str) -> dict[int, object]:
    """Ein Wert je Gebaeude, Schluessel ist die Nummer des Gebaeudes."""
    return {e - egid(0): wert for e, wert in
            con.execute(f"SELECT egid, {ausdruck} FROM {sicht}").fetchall()}


def zeile(con, sql: str, parameter: list | None = None) -> dict:
    cur = con.execute(sql, parameter or [])
    spalten = [d[0] for d in cur.description]
    werte = cur.fetchall()
    assert len(werte) == 1, f"genau eine Zeile erwartet, {len(werte)} erhalten"
    return dict(zip(spalten, werte[0], strict=True))


# --------------------------------------------------------------------------- Belege

def test_beleg_tabelle_fuehrt_nur_fossile_wohngebaeude_mit_beleg(verdacht):
    r = zeile(verdacht, "SELECT count(*) AS n, count(DISTINCT egid) AS eindeutig FROM gold_belege")
    assert r == {"n": 14, "eindeutig": 14}
    assert set(spalte(verdacht, "gold_belege", "1")) == set(LISTE) | set(NICHT_AUF_DER_LISTE) | set(WIDERLEGT)


def test_fossil_ohne_beleg_ist_kein_verdacht(verdacht):
    # Quelle 860 heisst ungeprueft, nicht falsch. Diese Gebaeude tragen alle Heizoel aus
    # der Volkszaehlung, aber keinen Beleg:
    #   2 bis 6, 8 bis 10, 12 bis 14, 104, 105   ihre Anlage ist nicht eindeutig zugeordnet
    #   25                                       das Baugesuch ist erst drei Monate alt
    #   26, 27                                   die Anlage wurde nicht erstellt oder ist
    #                                            ausser Betrieb
    #   201                                      die Lage der Luzerner Anlagen ist ungenau
    ohne_beleg = [2, 3, 4, 5, 6, 8, 9, 10, 12, 13, 14, 25, 26, 27, 104, 105, 201]
    fossil = spalte(verdacht, "silver_gebaeude_ch", "ist_fossil AND quelle_vz2000")
    assert all(fossil[nr] for nr in ohne_beleg)
    assert not set(ohne_beleg) & set(spalte(verdacht, "gold_belege", "1"))


def test_nicht_fossil_mit_beleg_ist_kein_verdacht(verdacht):
    # 24 hat eine Sonde und eine Photovoltaikanlage, 106 eine Grundwasserfassung. Beide
    # fuehren bereits eine Waermepumpe.
    klasse = spalte(verdacht, "silver_gebaeude_ch", "energie_klasse")
    assert klasse[24] == klasse[106] == "waermepumpe"
    assert not {24, 106} & set(spalte(verdacht, "gold_belege", "1"))


def test_nachgefuehrtes_baugesuch_ist_kein_beleg(verdacht):
    # 16 (Amtsblatt) und 108 (Zuercher OGD-Datensatz): Gesuch fuer eine Waermepumpe,
    # danach ein Gaseintrag mit Quelle 869. Das Gebaeude ist fossil, das Register wurde
    # aber nach dem Gesuch nachgefuehrt.
    assert zeile(verdacht, "SELECT status_gwr FROM v_test3_ch WHERE bg_id::VARCHAR = ?",
                 [welt.bg_id(16)]) == {"status_gwr": "nachgefuehrt"}
    assert zeile(verdacht, "SELECT status FROM v_test3 WHERE egid = ?",
                 [egid(108)]) == {"status": "quelle_869_nach_gesuch"}
    fossil = spalte(verdacht, "silver_gebaeude_ch", "ist_fossil")
    assert fossil[16] and fossil[108]
    assert not {16, 108} & set(spalte(verdacht, "gold_belege", "1"))


def test_belegarten_je_gebaeude(verdacht):
    arten = {nr: tuple(werte) for nr, werte in spalte(
        verdacht, "gold_belege", "[hat_baugesuch, hat_sonde, hat_pv, hat_widerspruch]").items()}
    nur_sonde = (False, True, False, False)
    assert arten == {
        1: nur_sonde, 7: nur_sonde, 11: nur_sonde, 21: nur_sonde,
        101: nur_sonde, 102: nur_sonde, 103: nur_sonde, 112: nur_sonde,
        15: (True, False, False, False), 107: (True, False, False, False),
        17: (False, False, True, False),
        18: (False, False, False, True), 19: (False, False, False, True),
        20: (True, True, True, False),
    }
    assert spalte(verdacht, "gold_belege WHERE hat_widerspruch", "ws_art") == {18: "fernwaerme", 19: "erzeuger"}


def test_baugesuch_traegt_die_referenzen_fuer_das_bauamt(verdacht):
    r = zeile(verdacht, """
        SELECT bg_quelle, bg_referenz, bg_parzelle, bg_weg, bg_datum, bg_neuer_traeger,
               bg_llm_geprueft, n_baugesuche
        FROM gold_belege WHERE egid = ?""", [egid(15)])
    assert r == {"bg_quelle": "Amtsblattportal", "bg_referenz": "Bauamt Sondwil", "bg_parzelle": "GS 15",
                 "bg_weg": "adresse", "bg_datum": dt.date(2025, 3, 10), "bg_neuer_traeger": "waermepumpe",
                 "bg_llm_geprueft": False, "n_baugesuche": 1}

    r = zeile(verdacht, """
        SELECT bg_quelle, bg_referenz, bg_parzelle, bg_weg, bg_datum, bg_llm_geprueft, bg_url
        FROM gold_belege WHERE egid = ?""", [egid(107)])
    assert r == {"bg_quelle": "ZH OGD Baugesuche", "bg_referenz": "BP-ZH-107", "bg_parzelle": "KTN 107",
                 "bg_weg": "adresse", "bg_datum": dt.date(2024, 10, 7), "bg_llm_geprueft": True,
                 "bg_url": "https://www.amtsblattportal.ch/#!/search/publications/detail/" + welt.bg_id(107)}


# --------------------------------------------------------------------------- Stufen und Liste

def test_jede_stufe_hat_ihren_fall(verdacht):
    assert spalte(verdacht, "v_gold_score", "konfidenz") == LISTE | NICHT_AUF_DER_LISTE | WIDERLEGT


def test_liste_fuehrt_nur_belege_zur_heizung(verdacht):
    assert spalte(verdacht, "v_gold_liste", "konfidenz") == LISTE
    # Jede der vier Listenstufen kommt vor
    assert set(LISTE.values()) == {"reihenfolge belegt", "reihenfolge plausibel", "eintrag alt", "eintrag jung"}


def test_gegenbeleg_nimmt_den_fall_aus_verdacht_und_liste(verdacht):
    kessel = spalte(verdacht, "v_gold_score", "[kessel_aktiv, kessel_stillgelegt]")
    assert kessel[21] == [True, False]
    assert kessel[1] == [False, True]           # stillgelegt widerlegt nichts
    assert set(spalte(verdacht, "v_gold_verdacht", "1")) == set(LISTE) | set(NICHT_AUF_DER_LISTE)
    assert 21 not in spalte(verdacht, "v_gold_liste", "1")
    assert 1 in spalte(verdacht, "v_gold_liste", "1")


def test_laufnummer_zaehlt_nur_ueber_der_schwelle_des_eintragsjahrs(verdacht):
    # Ohne 50 Neubauten je Baujahr bleibt von der Kalibrierung nur der Serienwechsel:
    # Schwelle 10100 fuer Eintraege bis 2002, keine fuer spaetere Jahre.
    schwellen = dict(verdacht.execute("""
        SELECT jahr, schwelle FROM gold_laufnummer_kalibrierung WHERE jahr IN (2001, 2020)""").fetchall())
    assert schwellen == {2001: 10100, 2020: None}
    assert spalte(verdacht, "v_gold_score WHERE kanton = 'ZH' AND hat_sonde",
                  "[sonde_laufnummer, lauf_schwelle]") == {
        101: [12657, 10100], 102: [1234, 10100], 103: [12700, None], 112: [13100, None]}


# --------------------------------------------------------------------------- Score

def test_score_ist_die_summe_der_punkte(verdacht):
    punkte = {nr: tuple(werte) for nr, werte in spalte(
        verdacht, "v_gold_score",
        "[p_baugesuch, p_sonde, p_widerspruch, p_pv, p_quelle, p_alter, p_baujahr]").items()}
    alt = (12, 15, 0)       # Quelle 860, Eintrag 25 Jahre alt, Baujahr ohne Punkte
    jung = (0, 0, 0)        # Quelle 869 oder 865, Eintrag von 2020 oder 2026
    assert punkte == {
        1: (0, 40, 0, 0, *alt), 7: (0, 40, 0, 0, *alt), 21: (0, 40, 0, 0, *alt),
        101: (0, 40, 0, 0, *alt), 102: (0, 40, 0, 0, *alt),
        11: (0, 40, 0, 0, *jung), 103: (0, 40, 0, 0, *jung), 112: (0, 40, 0, 0, *jung),
        15: (50, 0, 0, 0, *alt),
        107: (55, 0, 0, 0, *alt),           # mit Textpruefung
        17: (0, 0, 0, 18, *alt),
        18: (0, 0, 0, 0, *alt),             # Warmwasser-Widerspruch gibt keine Punkte
        19: (0, 0, 15, 0, *alt),
        20: (50, 40, 0, 18, *alt),
    }
    assert spalte(verdacht, "v_gold_score", "score") == {
        1: 67, 7: 67, 21: 67, 101: 67, 102: 67, 11: 40, 103: 40, 112: 40,
        15: 77, 107: 82, 17: 45, 18: 27, 19: 42,
        20: 100,                            # 135 Punkte, bei 100 gedeckelt
    }


def test_nachlauf_kennzeichnet_belege_juenger_als_18_monate(verdacht):
    # Gemessen am Registerstand 12.01.2026. Die Zuercher Sonden tragen kein Datum.
    alter = spalte(verdacht, "v_gold_liste", "beleg_alter_monate")
    assert alter == {1: 127, 7: 94, 15: 10, 19: None, 20: 11, 101: None, 102: None, 103: None, 107: 15, 112: None}
    assert {nr for nr, n in spalte(verdacht, "v_gold_liste", "im_nachlauf").items() if n} == {15, 20, 107}
    # Bei Baugesuch und Sonde zaehlt das Datum des Baugesuchs
    assert spalte(verdacht, "v_gold_liste WHERE hat_baugesuch AND hat_sonde",
                  "[beleg_datum, bg_datum, sonde_datum]::VARCHAR[]") == {
        20: ["2025-02-03", "2025-02-03", "2024-09-02"]}


# --------------------------------------------------------------------------- Vorschlag

def test_vorschlag_nennt_energietraeger_erzeuger_und_quelle(verdacht):
    vorschlag = spalte(verdacht, "v_gold_score", "[vorschlag_klasse, vorschlag, vorschlag_quelle]")
    # Sonde am Gebaeude: Erdwaermesonde, Quelle "kantonale Daten"
    for nr in (1, 7, 11, 21, 101, 102, 103, 112):
        assert vorschlag[nr] == ["waermepumpe", VORSCHLAG_SONDE, QUELLE_KANTON]
    # Baugesuch nennt eine Luft/Wasser-Waermepumpe: Quelle "Baubewilligung"
    assert vorschlag[15] == ["waermepumpe", VORSCHLAG_LUFT, QUELLE_BAUBEWILLIGUNG]
    assert vorschlag[107] == ["waermepumpe", VORSCHLAG_LUFT, QUELLE_BAUBEWILLIGUNG]
    # Baugesuch und Sonde: Die Waermequelle kommt von der Anlage, die Quelle vom Baugesuch
    assert vorschlag[20] == ["waermepumpe", VORSCHLAG_SONDE, QUELLE_BAUBEWILLIGUNG]
    # Erzeuger-Widerspruch: Waermepumpe steht fest, die Waermequelle nicht
    assert vorschlag[19] == [
        "waermepumpe",
        "GENH1 offen - Wärmequelle vor Ort klären (7501 Luft, 7511 Erdwärmesonde, 7513 Wasser), "
        "GWAERZH1 7410 Wärmepumpe für ein Gebäude",
        QUELLE_GEMEINDE]
    assert vorschlag[18] == [
        "fernwaerme",
        "GENH1 7580 Fernwärme (generisch), "
        "GWAERZH1 7460 Wärmetauscher (einschliesslich für Fernwärme) für ein Gebäude",
        QUELLE_GEMEINDE]
    # Photovoltaik sagt nichts ueber die neue Heizung
    assert vorschlag[17] == ["pruefen", "offen - bitte vor Ort klären", QUELLE_GEMEINDE]


def test_belegtext_begruendet_den_platz_auf_der_liste(verdacht):
    text = spalte(verdacht, "v_gold_liste", "beleg_text")
    assert text[1] == "Registrierte Erdwärmesonde in 50 m Entfernung, bewilligt 2015."
    assert text[20] == (
        'Baugesuch vom 03.02.2025: "Heizungsersatz: Erdsonden-Wärmepumpe statt Ölheizung". '
        "Registrierte Erdwärmesonde in 15 m Entfernung, bewilligt 2024. "
        "Photovoltaikanlage seit 2023.")
    assert text[101] == ("Registrierte Erdwärmesonde in 15 m Entfernung, Laufnummer 12657 "
                         "(nach Kalibrierung vergeben nach dem Registereintrag).")
    assert text[102] == "Registrierte Erdwärmesonde in 15 m Entfernung."
    assert text[107] == (
        'Baugesuch vom 07.10.2024: "Ersatz Ölheizung durch Luft-Wasser-Wärmepumpe (aussen aufgestellt)". '
        "(Textprüfung: Die Ölheizung wird durch eine Wärmepumpe ersetzt.)")
    assert text[19] == ("Das Register widerspricht sich selbst: als Wärmeerzeuger ist eine "
                        "Wärmepumpe eingetragen, als Energieträger aber Heizöl.")


# --------------------------------------------------------------------------- Aggregat

def test_gemeindeaggregat_zaehlt_verdacht_und_liste(verdacht):
    # Sondwil: Verdacht 1, 7, 11, 15, 17, 18, 19, 20 (21 ist widerlegt); auf der Liste 1,
    # 7, 15, 19, 20. Mittlerer Score (67+67+40+77+45+27+42+100) / 8 = 58,1.
    assert zeile(verdacht, "SELECT * EXCLUDE (kanton, gemeinde) FROM gold_verdacht_gemeinde WHERE bfs_nr = 9301") == {
        "bfs_nr": 9301, "verdachtsfaelle": 8, "konfidenz_hoch": 4, "konfidenz_plausibel": 0,
        "konfidenz_mittel": 1, "auf_der_liste": 5, "im_nachlauf": 2,
        "mit_baugesuch": 2, "mit_sonde": 4, "mit_widerspruch": 2, "mit_pv": 2,
        "score_mittel": 58.1, "score_max": 100}
    # Bohrikon: 101, 102, 103, 107 und 112, alle auf der Liste. (67+67+40+82+40) / 5 = 59,2.
    assert zeile(verdacht, "SELECT * EXCLUDE (kanton, gemeinde) FROM gold_verdacht_gemeinde WHERE bfs_nr = 9302") == {
        "bfs_nr": 9302, "verdachtsfaelle": 5, "konfidenz_hoch": 1, "konfidenz_plausibel": 1,
        "konfidenz_mittel": 3, "auf_der_liste": 5, "im_nachlauf": 1,
        "mit_baugesuch": 1, "mit_sonde": 4, "mit_widerspruch": 0, "mit_pv": 0,
        "score_mittel": 59.2, "score_max": 82}
    # Parzellingen hat kein Gebaeude mit Beleg und deshalb keine Zeile.
    assert verdacht.execute("SELECT count(*) FROM gold_verdacht_gemeinde").fetchone()[0] == 2


# --------------------------------------------------------------------------- Archiv und Korrektur

def test_archiv_haelt_die_liste_je_registerstand_fest(verdacht):
    # Im aelteren Stand standen zusaetzlich 22 (Sonde) und 23 (Baugesuch) auf der Liste.
    # Im juengeren fuehrt das Register sie nicht mehr fossil. 112 kam erst im juengeren
    # dazu: Vorher war dort eine Waermepumpe eingetragen.
    je_stand = {stand: sorted(nummern) for stand, nummern in verdacht.execute("""
        SELECT stand::VARCHAR, list(egid - 930000000) FROM gold_liste_archiv GROUP BY 1""").fetchall()}
    assert je_stand == {
        STAND_ALT: sorted({*LISTE, 22, 23} - {112}),
        STAND_NEU: sorted(LISTE),
    }
    assert zeile(verdacht, """
        SELECT konfidenz, vorschlag, energietraeger_txt, quelle_code, hat_baugesuch, hat_sonde, im_nachlauf
        FROM gold_liste_archiv WHERE egid = ?""", [egid(22)]) == {
        "konfidenz": "reihenfolge belegt", "vorschlag": VORSCHLAG_SONDE, "energietraeger_txt": "Heizöl",
        "quelle_code": "860", "hat_baugesuch": False, "hat_sonde": True, "im_nachlauf": False}


def test_ein_archivierter_stand_wird_nicht_ueberschrieben(verdacht):
    vorher = verdacht.execute("SELECT * FROM gold_liste_archiv ORDER BY ALL").fetchall()
    assert len(vorher) == 21        # 11 im aelteren, 10 im juengeren Stand
    pipeline.fuehre_aus(verdacht, ["gold_verdacht.sql"])
    assert verdacht.execute("SELECT * FROM gold_liste_archiv ORDER BY ALL").fetchall() == vorher


def test_archiv_nimmt_einen_nachgelieferten_kanton_auf(tmp_path, monkeypatch):
    """Der Ingest laedt je Kanton und ueberspringt, was schon vorliegt. Scheitert ein
    Kanton und kommt beim naechsten Lauf nach, traegt er denselben Stand wie die uebrigen.

        Lauf 1   aelterer Stand, alle Kantone
        Lauf 2   juengerer Stand, Zuerich fehlt noch
        Lauf 3   juengerer Stand, Zuerich nachgeliefert
    """
    welt.schreibe_rohdaten(tmp_path)
    datenverzeichnis(monkeypatch, tmp_path)
    con = pipeline.connect()
    try:
        welt.rechne_stand(con, tmp_path, STAND_ALT)
        welt.rechne_stand(con, tmp_path, STAND_NEU, kantone=("ZG", "LU"))
        welt.rechne_stand(con, tmp_path, STAND_NEU, kantone=("ZH",))
        # Die Liste selbst ist vollstaendig ...
        assert spalte(con, "v_gold_liste", "stand::VARCHAR") == dict.fromkeys(LISTE, STAND_NEU)
        # ... das Archiv des juengeren Stands muss es auch sein.
        archiviert = con.execute("""
            SELECT list(egid - 930000000 ORDER BY egid) FROM gold_liste_archiv
            WHERE stand = ?""", [STAND_NEU]).fetchone()[0]
        assert archiviert == sorted(LISTE)
    finally:
        con.close()


def test_korrigierte_faelle_werden_am_vorschlag_gemessen(verdacht):
    korrigiert = {z["egid"] - egid(0): z for z in (
        dict(zip(("egid", "listenstand", "korrigiert_am", "traeger_alt", "genh1_neu", "quelle_neu",
                  "datum_neu", "vorschlag", "vorschlag_trifft"), werte, strict=True))
        for werte in verdacht.execute("""
            SELECT egid, listenstand::VARCHAR, korrigiert_am::VARCHAR, traeger_alt, genh1_neu,
                   quelle_neu, datum_neu::VARCHAR, vorschlag, vorschlag_trifft
            FROM v_gold_liste_korrigiert""").fetchall())}
    # 112 ist kein korrigierter Fall: Nicht fossil war das Gebaeude vor seinem Listenstand,
    # nicht danach.
    assert set(korrigiert) == {22, 23}
    gemeinsam = {"listenstand": STAND_ALT, "korrigiert_am": STAND_NEU, "traeger_alt": "Heizöl",
                 "datum_neu": "2026-01-08"}
    # 22: vorgeschlagen und eingetragen ist die Erdwaermesonde
    assert korrigiert[22] == {**gemeinsam, "egid": egid(22), "genh1_neu": "7511", "quelle_neu": "864",
                              "vorschlag": VORSCHLAG_SONDE, "vorschlag_trifft": True}
    # 23: vorgeschlagen war die Luft-Waermepumpe, eingetragen ist Fernwaerme
    assert korrigiert[23] == {**gemeinsam, "egid": egid(23), "genh1_neu": "7580", "quelle_neu": "870",
                              "vorschlag": VORSCHLAG_LUFT, "vorschlag_trifft": False}


# --------------------------------------------------------------------------- Aufbau

def test_die_gepruefte_reihenfolge_ist_die_der_pipeline(verdacht):
    # Die Welt laesst Schritte des Zuercher Strangs aus, darf aber keinen umstellen.
    in_pipeline = [s for s in pipeline.SCHRITTE_ZH if s in welt.SCHRITTE]
    assert in_pipeline == welt.SCHRITTE
