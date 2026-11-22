"""Datenqualitaets- und Regressionspruefungen fuer die Pipeline.

Jede Pruefung ist eine Behauptung ueber die Daten, die stimmen muss, bevor Zahlen
in einen Report wandern. Faellt eine, wird das Ergebnis nicht veroeffentlicht.

    python src/checks.py            # alle Pruefungen
    python src/checks.py -v         # zusaetzlich die gemessenen Werte

Exit-Code 0 wenn alles besteht, sonst 1. Damit laesst sich das in CI haengen.
"""
from __future__ import annotations

import sys
from dataclasses import dataclass, field

import config
import pipeline

# Aus der ZH-Detailauswertung (Abzug vom 13.09.2026). Aendern sich diese Zahlen, hat
# sich die Fachlogik verschoben und nicht nur die Datenbasis.
REGRESSION_ZH = {
    "gebaeude_bestehend": 367385,
    "wohngebaeude": 228968,
}


@dataclass
class Ergebnis:
    name: str
    bestanden: bool
    gemessen: str = ""
    erwartet: str = ""


@dataclass
class Pruefer:
    con: object
    ergebnisse: list[Ergebnis] = field(default_factory=list)

    def _wert(self, sql: str):
        return self.con.execute(pipeline.datenpfade(sql)).fetchone()[0]

    def hat(self, tabelle: str) -> bool:
        """Gibt es diese Tabelle? Teile der Pipeline haengen an Daten, die Stunden
        brauchen - fehlen sie, sollen die uebrigen Pruefungen trotzdem laufen."""
        return bool(self.con.execute(
            "SELECT count(*) FROM information_schema.tables WHERE table_name = ?",
            [tabelle]).fetchone()[0])

    def gleich(self, name: str, sql: str, soll) -> None:
        ist = self._wert(sql)
        self.ergebnisse.append(Ergebnis(name, ist == soll, str(ist), str(soll)))

    def null(self, name: str, sql: str) -> None:
        """Die Abfrage muss 0 Zeilen liefern - fuer Verletzungen aller Art."""
        ist = self._wert(f"SELECT count(*) FROM ({sql})")
        self.ergebnisse.append(Ergebnis(name, ist == 0, f"{ist} Verstoesse", "0"))

    def hoechstens(self, name: str, sql: str, grenze: int, grund: str = "") -> None:
        """Bekannte Datenfehler der Quelle, die wir nicht beheben koennen. Die Grenze
        haelt fest, wie viele es beim letzten Pruefen waren - waechst die Zahl
        deutlich, faellt der Check auf und wir schauen erneut hin."""
        ist = self._wert(f"SELECT count(*) FROM ({sql})")
        self.ergebnisse.append(
            Ergebnis(f"{name}{' - ' + grund if grund else ''}",
                     ist <= grenze, f"{ist} Faelle", f"hoechstens {grenze}"))

    def zwischen(self, name: str, sql: str, unten: float, oben: float) -> None:
        ist = self._wert(sql)
        ok = ist is not None and unten <= ist <= oben
        self.ergebnisse.append(Ergebnis(name, ok, str(ist), f"{unten} bis {oben}"))


def pruefe(p: Pruefer) -> None:
    # ---------------------------------------------------------------- Vollstaendigkeit
    p.gleich("alle 26 Kantone geladen",
             "SELECT count(DISTINCT kanton) FROM silver_gebaeude_ch", 26)
    p.zwischen("Gemeindezahl plausibel (BFS: rund 2100)",
               "SELECT count(*) FROM gold_gemeinde", 2000, 2200)
    p.zwischen("Gebaeudezahl CH plausibel",
               "SELECT count(*) FROM silver_gebaeude_ch", 2_800_000, 3_600_000)

    # ---------------------------------------------------------------- Schluessel
    p.null("EGID ist eindeutig",
           "SELECT egid FROM silver_gebaeude_ch GROUP BY 1 HAVING count(*) > 1")
    p.null("kein Gebaeude ohne EGID",
           "SELECT 1 FROM silver_gebaeude_ch WHERE egid IS NULL")
    p.null("kein Gebaeude ohne Gemeindenummer",
           "SELECT 1 FROM silver_gebaeude_ch WHERE bfs_nr IS NULL")

    # ---------------------------------------------------------------- Wertebereiche
    p.null("Koordinaten liegen in der Schweiz (LV95)",
           """SELECT 1 FROM silver_gebaeude_ch
              WHERE e_lv95 IS NOT NULL
                AND (e_lv95 NOT BETWEEN 2480000 AND 2840000
                  OR n_lv95 NOT BETWEEN 1070000 AND 1300000)""")
    p.null("Baujahr ist plausibel",
           """SELECT 1 FROM silver_gebaeude_ch
              WHERE baujahr IS NOT NULL AND (baujahr < 800 OR baujahr > year(stand) + 1)""")
    # Bekannter Erfassungsfehler im GWR: einzelne Eintraege tragen ein Datum in der
    # Zukunft, im Extremfall neun Monate. Nicht korrigierbar, aber ueberwachbar.
    p.hoechstens("Aktualisierungsdatum in der Zukunft",
                 "SELECT 1 FROM silver_gebaeude_ch WHERE quelle_datum > stand",
                 25, "Erfassungsfehler der Quelle")
    p.null("Prozentwerte bleiben im Bereich 0 bis 100",
           """SELECT 1 FROM gold_gemeinde
              WHERE pct_vollstaendig NOT BETWEEN 0 AND 100
                 OR pct_vz2000 NOT BETWEEN 0 AND 100
                 OR pflege_index NOT BETWEEN 0 AND 100""")

    p.null("Gebaeude mit Wohnnutzung hat eine Gebaeudekategorie",
           "SELECT 1 FROM silver_gebaeude_ch WHERE ist_wohngebaeude AND gkat IS NULL")
    p.zwischen("Anteil Wohngebaeude an allen Gebaeuden plausibel",
               """SELECT round(100.0 * sum(ist_wohngebaeude::INT) / count(*), 1)
                  FROM silver_gebaeude_ch""", 45, 70)
    p.zwischen("Anteil fossil beheizter Wohngebaeude plausibel",
               """SELECT round(100.0 * sum(ist_fossil::INT) / count(*), 1)
                  FROM silver_gebaeude_ch WHERE ist_wohngebaeude""", 35, 65)

    # ---------------------------------------------------------------- Codelisten
    p.null("jeder Energietraeger-Code ist im Katalog",
           """SELECT 1 FROM silver_gebaeude_ch g
              WHERE g.energietraeger_code IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM bronze_gwr_kodes k
                WHERE k.CMERKM = 'GENH1' AND k.CECODID = g.energietraeger_code)""")
    p.null("jeder Quellen-Code ist im Katalog",
           """SELECT 1 FROM silver_gebaeude_ch g
              WHERE g.quelle_code IS NOT NULL AND NOT EXISTS (
                SELECT 1 FROM bronze_gwr_kodes k
                WHERE k.CMERKM = 'GWAERSCEH1' AND k.CECODID = g.quelle_code)""")
    p.null("kein Energietraeger faellt in die Klasse ohne_angabe, obwohl ein Code da ist",
           """SELECT 1 FROM silver_gebaeude_ch
              WHERE energietraeger_code IS NOT NULL AND energie_klasse = 'ohne_angabe'""")

    # ---------------------------------------------------------------- Aggregate stimmen
    p.null("Gemeindesummen ergeben die Kantonssumme",
           """SELECT k.kanton FROM gold_kanton k
              JOIN (SELECT kanton, sum(wohngebaeude) AS s FROM gold_gemeinde GROUP BY 1) g
                USING (kanton)
              WHERE k.wohngebaeude <> g.s""")
    p.null("Teilmengen ueberschreiten die Gesamtmenge nicht",
           """SELECT 1 FROM gold_gemeinde
              WHERE fossil + waermepumpe + fernwaerme + holz > wohngebaeude
                 OR aus_vz2000 > wohngebaeude OR mit_angabe > wohngebaeude""")
    p.null("Kandidaten sind eine Teilmenge der fossil beheizten Gebaeude",
           "SELECT 1 FROM gold_gemeinde WHERE kandidaten > fossil")

    # ---------------------------------------------------------------- Snapshots
    p.null("je Kanton und Stand genau eine Snapshot-Datei",
           """SELECT kanton, snapshot_date FROM (
                SELECT kanton, snapshot_date, count(DISTINCT filename) AS n
                FROM read_parquet('data/snapshots/gwr/**/*.parquet',
                                  hive_partitioning = true, filename = true)
                GROUP BY 1, 2) WHERE n > 1""")
    p.null("Snapshot-Datum passt zum Exportdatum im Datensatz",
           """SELECT kanton FROM bronze_gwr_aktuell
              GROUP BY kanton, snapshot_date HAVING max(GEXPDAT) <> any_value(snapshot_date)""")

    # ---------------------------------------------------------------- Regression ZH
    tabellen = {t for (t,) in p.con.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
    ).fetchall()}
    if "silver_gebaeude" in tabellen:
        # Der ZH-Strang rechnet auf dem Abzug vom 13.09.2026 (gwr_zh.zip), der
        # schweizweite Strang auf dem juengsten Wochen-Snapshot. Die Regressionszahlen
        # gelten deshalb fuer den ZH-Layer und nicht fuer den CH-Layer.
        p.gleich("ZH: bestehende Gebaeude wie in der Detailauswertung",
                 "SELECT count(*) FROM silver_gebaeude",
                 REGRESSION_ZH["gebaeude_bestehend"])
        p.gleich("ZH: Wohngebaeude wie in der Detailauswertung",
                 "SELECT count(*) FROM silver_gebaeude WHERE gkat IN ('1020', '1030', '1040')",
                 REGRESSION_ZH["wohngebaeude"])
        # Gleicher Stand, gleiche Regel (GSTAT 1004), gleiche Zahl: Der ZH-Layer muss
        # dem Snapshot seines eigenen Exportdatums entsprechen, nicht dem juengsten.
        p.gleich("ZH: alter Silver-Layer zaehlt wie der Snapshot seines Stands",
                 """SELECT (SELECT count(*) FROM silver_gebaeude)
                         - (SELECT count(*) FROM bronze_gwr_snapshots
                            WHERE kanton = 'ZH' AND GSTAT = '1004'
                              AND snapshot_date = (SELECT max(GEXPDAT)::DATE
                                                   FROM bronze_gwr_gebaeude))""", 0)
        # Der Gold-Layer wird aus dem CH-Layer gerechnet. Bleibt er nach einem Snapshot
        # stehen, fuehrt die Liste Faelle, die das Register schon korrigiert hat.
        p.gleich("Gold-Layer steht auf demselben Stand wie der Silver-Layer",
                 """SELECT (SELECT max(stand) FROM gold_belege)
                         = (SELECT max(stand) FROM silver_gebaeude_ch)""", True)
        p.null("Verdachtsliste enthaelt keinen im aktuellen Stand schon korrigierten Fall",
               """SELECT 1 FROM v_gold_liste v JOIN silver_gebaeude_ch g USING (egid)
                  WHERE NOT g.ist_fossil OR NOT g.ist_wohngebaeude""")
        p.null("Archiv der Verdachtsliste: je Stand hoechstens ein Eintrag je Gebaeude",
               """SELECT egid, stand FROM gold_liste_archiv
                  GROUP BY 1, 2 HAVING count(*) > 1""")
        p.null("ZH: Baugesuch-Zuordnung trifft nur existierende Gebaeude",
               """SELECT 1 FROM match_all m
                  WHERE NOT EXISTS (SELECT 1 FROM silver_gebaeude g WHERE g.egid = m.egid)""")
        p.null("ZH: je Vorhaben genau eine Erstpublikation",
               """SELECT vorhaben_id FROM silver_baugesuche
                  GROUP BY 1 HAVING sum(ist_erstpublikation::INT) <> 1""")
        p.null("ZH: Test 3 zaehlt kein Gebaeude doppelt zum selben Vorhaben",
               """SELECT egid FROM v_test3 GROUP BY egid, vorhaben_id HAVING count(*) > 1""")
        p.zwischen("ZH: Anteil Mehrfachpublikationen plausibel",
                   """SELECT round(100.0 * sum((NOT ist_erstpublikation)::INT) / count(*), 1)
                      FROM silver_baugesuche""", 15, 30)
        p.null("Waermenutzungsanlagen liegen in der Schweiz",
               """SELECT 1 FROM silver_waermenutzung
                  WHERE e_lv95 NOT BETWEEN 2480000 AND 2840000
                     OR n_lv95 NOT BETWEEN 1070000 AND 1300000""")
        p.null("Waermenutzung: Anlage und zugeordnetes Gebaeude im selben Kanton",
               """SELECT 1 FROM match_waermenutzung m
                  JOIN silver_waermenutzung a USING (anlage_id)
                  WHERE m.kanton <> a.kanton""")
        p.null("Waermenutzung: Zuordnung haelt den Radius ein",
               "SELECT 1 FROM match_waermenutzung WHERE dist_m > 20")
        p.null("BE: jede ausgefuehrte Anlage in Test 6 hat ein Bewilligungsdatum",
               "SELECT 1 FROM v_test6 WHERE datum_bewilligung IS NULL")
        # ------------------------------------------------------------ LLM-Kaskade
        p.null("Kaskade verliert keinen Fall, wenn kein LLM-Urteil vorliegt",
               """SELECT 1 FROM v_baugesuch_geprueft
                  WHERE ist_heizungsereignis AND NOT llm_geprueft
                    AND NOT ist_traegerwechsel""")
        p.null("Kaskade erfindet keinen Fall ohne Regeltreffer",
               """SELECT 1 FROM v_baugesuch_geprueft
                  WHERE ist_traegerwechsel AND NOT ist_heizungsereignis""")
        p.null("LLM-Urteil ist je Beschrieb eindeutig",
               """SELECT beschrieb FROM silver_llm_urteil
                  GROUP BY 1 HAVING count(*) > 1""")
        p.null("gemeldeter Energietraeger ist ein bekannter Wert",
               """SELECT 1 FROM v_baugesuch_geprueft
                  WHERE traeger_final IS NOT NULL AND traeger_final NOT IN
                    ('waermepumpe','fernwaerme','holz','solarthermie','gas','oel','elektro')""")

        # ------------------------------------------------------------ Verdachts-Layer
        # Greift der Gegenbeleg, darf der Fall nicht auf der Liste stehen: Der Kanton
        # fuehrt die fossile Heizung des Gebaeudes selbst als in Betrieb.
        p.null("kein Verdachtsfall mit laufender fossiler Feuerung",
               "SELECT 1 FROM v_gold_verdacht WHERE kessel_aktiv")
        p.zwischen("Gegenbeleg greift bei einem plausiblen Teil der Kandidaten",
                   """SELECT round(100.0 * sum(kessel_aktiv::INT)
                        / nullif(count(*), 0), 1)
                      FROM gold_belege WHERE kanton IN ('GE', 'ZG')""", 5, 60)
        p.null("Verdachtsfall hat immer mindestens einen echten Beleg",
               """SELECT 1 FROM v_gold_verdacht
                  WHERE NOT hat_baugesuch AND NOT hat_sonde
                    AND NOT hat_pv AND NOT hat_widerspruch""")
        p.null("Verdachtsfaelle sind fossil eingetragene Wohngebaeude",
               """SELECT 1 FROM v_gold_verdacht v
                  JOIN silver_gebaeude_ch g USING (egid)
                  WHERE NOT g.ist_fossil OR NOT g.ist_wohngebaeude""")
        p.null("Score bleibt zwischen 0 und 100",
               "SELECT 1 FROM v_gold_verdacht WHERE score NOT BETWEEN 0 AND 100")
        p.null("Verdachtsliste fuehrt nur die vier dokumentierten Stufen",
               """SELECT 1 FROM v_gold_liste
                  WHERE konfidenz NOT IN ('reihenfolge belegt', 'reihenfolge plausibel',
                                          'eintrag alt', 'eintrag jung')
                     OR konfidenz IS NULL""")
        p.null("Registerwiderspruch nur bei fossil eingetragenen Gebaeuden",
               """SELECT 1 FROM v_gold_verdacht WHERE hat_widerspruch
                  AND energie_klasse NOT IN ('oel', 'gas')""")
        p.null("Widerspruchsart ist immer gesetzt, wenn der Beleg greift",
               "SELECT 1 FROM v_gold_verdacht WHERE hat_widerspruch AND ws_art IS NULL")
        p.null("Erzeuger-Widerspruch ist wirklich Waermepumpe mit Heizoel",
               """SELECT 1 FROM v_gold_verdacht v JOIN silver_gebaeude_ch g USING (egid)
                  WHERE v.ws_art = 'erzeuger'
                    AND NOT (g.waermeerzeuger_code IN ('7410','7411')
                             AND g.energietraeger_code = '7530')""")
        p.zwischen("Verdachtsfaelle decken fast alle Kantone ab",
                   "SELECT count(DISTINCT kanton) FROM v_gold_verdacht", 20, 26)
        p.null("jeder Verdachtsfall traegt einen Belegtext",
               "SELECT 1 FROM v_gold_verdacht WHERE beleg_text IS NULL OR length(beleg_text) < 10")
        p.null("Gemeindesummen des Verdachts-Layers stimmen",
               """SELECT bfs_nr FROM (
                    SELECT bfs_nr, count(*) AS n FROM v_gold_verdacht GROUP BY 1) a
                  JOIN gold_verdacht_gemeinde g USING (bfs_nr)
                  WHERE a.n <> g.verdachtsfaelle""")
        # Mehrere Kantone messen unabhaengig voneinander dasselbe. UR faellt ab, weil
        # dort nur Konzessionen gemeldet werden, GE weil dort fast die Haelfte der
        # Gebaeude im Sondenumkreis "unbestimmt" als Energietraeger traegt. Zuerich
        # stand am 14.09.2026 bei 47,8 %. Seit der kantonalen Sammelnachfuehrung ab
        # 21.09.2026 steigt der Wert (16.11.2026: 67,4 %) und misst nicht mehr
        # denselben Zustand. Der Vergleich laeuft deshalb ueber BE, TG und SH. Fuer
        # Zuerich gilt nur, dass der Wert nicht unter den Ausgangsstand faellt.
        p.zwischen("BE, TG und SH messen aehnliche Werte",
                   """SELECT round(max(pct) - min(pct), 1) FROM (
                        SELECT kanton, 100.0*sum((mit_waermepumpe>0)::INT)/count(*) AS pct
                        FROM v_test5_anlage WHERE ist_gebaut
                          AND kanton IN ('BE','TG','SH') GROUP BY 1)""", 0, 15)
        p.zwischen("ZH: Waermepumpen-Anteil neben Anlagen faellt nicht unter den Ausgangsstand",
                   """SELECT round(100.0*sum((mit_waermepumpe>0)::INT)/count(*), 1)
                      FROM v_test5_anlage WHERE ist_gebaut AND kanton = 'ZH'""", 45, 100)
        p.zwischen("Genfer Sonderfall bleibt erklaerbar: viel \"unbestimmt\" im Umkreis",
                   """SELECT round(100.0*count(*) FILTER (WHERE energie_klasse='unbestimmt')
                      / count(*), 1) FROM match_waermenutzung
                      WHERE kanton='GE' AND ist_wohngebaeude""", 30, 70)
        p.null("jede Anlage liegt im Kanton, dem sie zugeordnet ist",
               """SELECT 1 FROM silver_waermenutzung
                  WHERE kanton = 'GE' AND (e_lv95 NOT BETWEEN 2484000 AND 2515000
                                        OR n_lv95 NOT BETWEEN 1110000 AND 1136000)""")
        # Die Datumsfelder der Kantone kommen in vier Formaten (TT.MM.JJJJ, JJJJMMTT,
        # blosses Jahr, ISO). Ein Formatfehler zeigt sich als unmoegliches Datum: Zug
        # lieferte 2105.
        p.null("kein Anlagendatum ausserhalb des Moeglichen",
               """SELECT 1 FROM silver_waermenutzung
                  WHERE datum_bewilligung IS NOT NULL
                    AND (datum_bewilligung < DATE '1900-01-01'
                         OR datum_bewilligung > current_date + INTERVAL 1 YEAR)""")
        # Davon zu unterscheiden: ein Datum wenige Tage in der Zukunft. Luzern fuehrt
        # zwei Bewilligungen mit Datum in der kommenden Woche, eine Eigenheit der
        # Quelle. Nur die Zahl wird ueberwacht.
        p.hoechstens("Anlagendatum leicht in der Zukunft",
                     """SELECT 1 FROM silver_waermenutzung
                        WHERE datum_bewilligung > current_date""",
                     10, "Erfassungsfehler der Quelle")
        p.null("Luft-Wasser-Waermepumpen zaehlen nicht als Ausfuehrungsnachweis",
               """SELECT 1 FROM v_test6 t JOIN silver_waermenutzung a USING (anlage_id)
                  WHERE a.anlagentyp = 'luft_wasser_wp'""")
        # Eine Anlagenkoordinate ist nur brauchbar, wenn sie das geheizte Gebaeude meint.
        # Tut sie es nicht, tragen die Gebaeude im Umkreis nicht haeufiger eine
        # Waermepumpe als ein beliebiges Wohngebaeude desselben Kantons. So ist es in
        # Luzern (v_lage_ungenau). Diese Pruefung sucht weitere Kantone mit dem Muster.
        p.null("Anlagenkoordinaten tragen Information ueber das Gebaeude",
               """WITH hintergrund AS (
                      SELECT kanton,
                             100.0 * sum((energie_klasse='waermepumpe')::INT) / count(*) AS basis
                      FROM silver_gebaeude_ch WHERE ist_wohngebaeude GROUP BY 1),
                    naechstes AS (
                      SELECT DISTINCT ON (anlage_id) anlage_id, kanton, energie_klasse
                      FROM match_waermenutzung WHERE ist_gebaut ORDER BY anlage_id, dist_m),
                    gemessen AS (
                      SELECT kanton, count(*) AS n,
                             100.0 * sum((energie_klasse='waermepumpe')::INT) / count(*) AS naehe
                      FROM naechstes GROUP BY 1)
                  SELECT g.kanton FROM gemessen g JOIN hintergrund h USING (kanton)
                  WHERE g.n >= 500
                    -- Faktor 1,3 statt 1,0: Knapp ueber der Hintergrundrate waere Zufall.
                    AND g.naehe < h.basis * 1.3
                    AND g.kanton NOT IN (SELECT kanton FROM v_lage_ungenau)
                    -- Genf faellt aus einem anderen Grund durch und darf deshalb nicht
                    -- als Koordinatenproblem gelten: Dort steht bei fast der Haelfte der
                    -- Gebaeude im Sondenumkreis "unbestimmt" als Energietraeger. Nicht
                    -- die Lage ist unbrauchbar, sondern der Registereintrag daneben.
                    -- Der eigene Check "Genfer Sonderfall" ueberwacht diese Erklaerung.
                    AND g.kanton <> 'GE'""")
        # Zug liefert die amtliche EGID mit. Trifft die raeumliche Zuordnung sie nur
        # noch selten, stimmt etwas mit dem Umkreis-Join nicht.
        p.zwischen("Zuordnung trifft Zugs amtliche EGID wie gemessen",
                   """SELECT round(100.0 * count(DISTINCT CASE WHEN k.egid IS NOT NULL
                                                          THEN a.anlage_id END)
                                   / nullif(count(DISTINCT a.anlage_id), 0), 1)
                      FROM (SELECT anlage_id, TRIM(x) AS egid_amt
                            FROM silver_waermenutzung,
                                 UNNEST(str_split(egid_amtlich, ',')) AS t(x)
                            WHERE egid_amtlich IS NOT NULL AND TRIM(x) <> '') a
                      LEFT JOIN match_waermenutzung k
                        ON k.anlage_id = a.anlage_id
                       AND CAST(k.egid AS VARCHAR) = a.egid_amt""", 65, 85)

    if p.hat("v_ge_label_klar"):
        # Der Genfer Labelsatz ist die Referenz der Messungen und muss in sich stimmen.
        p.null("Label ist nie gleichzeitig richtig und falsch",
               """SELECT egid FROM v_ge_label_klar
                  GROUP BY egid HAVING count(DISTINCT eintrag_falsch) > 1""")
        p.zwischen("Genfer Fehlerquote bleibt im gemessenen Bereich",
                   """SELECT round(100.0 * sum(eintrag_falsch::INT) / count(*), 1)
                      FROM v_ge_label_klar""", 4, 12)
        # v_gold_verdacht filtert mit demselben Genfer Kataster, aus dem die Labels
        # stammen. Eine Messung der Rangfolge daran waere zirkulaer. Die ungefilterte
        # Sicht muss deshalb mehr Faelle enthalten als die gefilterte.
        p.null("Score-Sicht ist nicht mit der Listensicht identisch",
               """SELECT 1 WHERE (SELECT count(*) FROM v_gold_score)
                              <= (SELECT count(*) FROM v_gold_verdacht)""")

    if p.hat("v_gold_liste"):
        # Prueft den Text, der in der Liste steht, nicht eine Zwischenstufe. Zwei
        # Bedingungen: Die erste sucht die Form "Grossbuchstabe-Wort
        # Grossbuchstabe-Wort;" am Textanfang, so steht die Bauherrschaft in den
        # Walliser und Schaffhauser Publikationen. Die zweite schliesst deutsche
        # Substantivgruppen aus, die genauso aussehen ("Anpassungen
        # Umgebungsgestaltung; Erstellen Aussenpool ..."): Ein Nachname endet selten
        # auf -ung, -heit, -keit, -schaft oder -tion.
        p.null("kein Personenname im Belegtext der Liste",
               r"""WITH anfang AS (
                       SELECT regexp_extract(COALESCE(bg_beschrieb, ''),
                                  '^([A-ZÄÖÜ][A-Za-zÄÖÜäöüß''-]+'
                                  || '( [A-ZÄÖÜ][A-Za-zÄÖÜäöüß''-]+){1,2});', 1) AS kopf
                       FROM v_gold_liste)
                   SELECT 1 FROM anfang
                   WHERE kopf <> ''
                     AND NOT regexp_matches(kopf,
                           '(ung|ungen|heit|keit|schaft|tion|ierung|arbeiten|anlage)$')
                     AND NOT regexp_matches(kopf,
                           '(ung|ungen|heit|keit|schaft|tion|ierung) ')""")

        # Die Liste darf keine Faelle enthalten, die nur auf Photovoltaik beruhen
        # (Trefferquote 13,7 % in Genf, 17,2 % in Zug). Der Ausschluss in der Sicht
        # haengt an einem COALESCE, weil FALSE OR NULL in SQL NULL ergibt. Geprueft
        # wird deshalb das Ergebnis und nicht die Formulierung.
        p.null("auf der Verdachtsliste steht kein Fall ohne Heizungsbeleg",
               """SELECT 1 FROM v_gold_liste
                  WHERE NOT hat_baugesuch AND NOT hat_sonde
                    AND COALESCE(ws_art, '') <> 'erzeuger'""")
        # Jeder Code im Vorschlag muss im Merkmalskatalog des BFS stehen, und der
        # Klartext daneben muss der des Katalogs sein. Die Codes sind leicht zu
        # verwechseln: 7430 ist "Heizkessel (generisch)", die Waermepumpe ist 7410.
        p.null("jeder Code im Korrekturvorschlag stimmt mit dem Merkmalskatalog überein",
               r"""WITH zerlegt AS (
                       SELECT DISTINCT
                              regexp_extract(vorschlag,
                                  'GENH1 ([0-9]{4}) (.*?), GWAERZH1',
                                  ['code', 'text'])            AS traeger,
                              regexp_extract(vorschlag,
                                  'GWAERZH1 ([0-9]{4}) (.*)$',
                                  ['code', 'text'])            AS erzeuger,
                              regexp_extract(vorschlag_quelle,
                                  'GWAERSCEH1 ([0-9]{3}) (.*)$',
                                  ['code', 'text'])            AS quelle
                       FROM v_gold_liste),
                   einzeln AS (
                       SELECT 'GENH1'      AS merkmal, traeger.code,  traeger.text  FROM zerlegt
                       UNION ALL
                       SELECT 'GWAERZH1',            erzeuger.code, erzeuger.text FROM zerlegt
                       UNION ALL
                       SELECT 'GWAERSCEH1',          quelle.code,   quelle.text   FROM zerlegt)
                   SELECT 1 FROM einzeln
                   WHERE code <> ''
                     AND NOT EXISTS (
                         SELECT 1 FROM bronze_gwr_kodes k
                         WHERE k.CMERKM = einzeln.merkmal
                           AND k.CECODID = einzeln.code
                           AND trim(k.CODTXTLD) = trim(einzeln.text))""")
        # Die vorgeschlagene Informationsquelle muss zur Herkunft des Belegs passen:
        # 869 fuer ein Baugesuch, 864 fuer das kantonale Waermenutzungsregister, sonst
        # 865.
        p.null("die vorgeschlagene Informationsquelle passt zur Herkunft des Belegs",
               """SELECT 1 FROM v_gold_liste
                  WHERE vorschlag_quelle NOT LIKE
                        'GWAERSCEH1 ' || CASE WHEN hat_baugesuch THEN '869'
                                              WHEN hat_sonde     THEN '864'
                                              ELSE                    '865' END || ' %'""")
        # Geprueft wird die Eigenschaft und nicht der CASE-Ausdruck der Sicht: Auf der
        # Liste steht kein Fall, dessen datierter Beleg aelter ist als der
        # Registereintrag. Solche Faelle treffen in Zug zu 13,3 % zu, nahe der Grundrate.
        p.null("kein Fall, dessen Beleg aelter ist als der Registereintrag",
               """SELECT 1 FROM v_gold_liste
                  WHERE beleg_datum IS NOT NULL AND quelle_datum IS NOT NULL
                    AND beleg_datum <= quelle_datum""")
        p.null("Stufe 'reihenfolge belegt' heisst wirklich datiert und juenger",
               """SELECT 1 FROM v_gold_liste
                  WHERE konfidenz = 'reihenfolge belegt'
                    AND NOT (beleg_datum IS NOT NULL AND quelle_datum IS NOT NULL
                             AND beleg_datum > quelle_datum)""")
        # Die Laufnummer-Stufe: undatiert, aber die Nummer liegt ueber der kalibrierten
        # Schwelle des Eintragsjahrs. Sie darf nie mit einem echten Datum zusammenfallen
        # und nur dort auftreten, wo ein Kanton solche Nummern vergibt (Zuerich).
        p.null("Stufe 'reihenfolge plausibel' heisst undatiert und Laufnummer ueber der Schwelle",
               """SELECT 1 FROM v_gold_liste
                  WHERE konfidenz = 'reihenfolge plausibel'
                    AND NOT (beleg_datum IS NULL AND sonde_laufnummer IS NOT NULL
                             AND lauf_schwelle IS NOT NULL
                             AND sonde_laufnummer > lauf_schwelle)""")
        p.null("Laufnummer-Stufe nur dort, wo der Kanton Laufnummern vergibt",
               """SELECT 1 FROM v_gold_liste
                  WHERE konfidenz = 'reihenfolge plausibel' AND kanton <> 'ZH'""")
        p.null("Laufnummer-Schwellen steigen mit dem Jahr",
               """SELECT 1 FROM (SELECT schwelle,
                                        lag(schwelle) OVER (ORDER BY jahr) AS vorher
                                 FROM gold_laufnummer_kalibrierung
                                 WHERE schwelle IS NOT NULL)
                  WHERE schwelle < vorher""")
        p.zwischen("Laufnummer-Kalibrierung beruht auf genug Neubauten je Jahr",
                   """SELECT min(neubauten) FROM gold_laufnummer_kalibrierung
                      WHERE neubauten IS NOT NULL""", 50, 100000)
        p.zwischen("Laufnummer-Kalibrierung deckt die juengsten Eintragsjahre ab",
                   """SELECT max(jahr) FROM gold_laufnummer_kalibrierung
                      WHERE neubauten IS NOT NULL""", 2025, 2100)
        # Der Nachlauf: ein Beleg unter 18 Monaten am Tag des Registerabzugs. Die
        # Kennzeichnung muss aus demselben Datum folgen wie die Reihenfolge.
        p.null("'im Nachlauf' heisst Beleg juenger als 18 Monate am Tag des Abzugs",
               """SELECT 1 FROM v_gold_liste
                  WHERE im_nachlauf <> (beleg_datum IS NOT NULL
                                        AND date_diff('month', beleg_datum, stand) < 18)""")
        # Genfs Bohrungsregister fuehrt 3'520 Bohrungen mit Status "Inconnu" oder
        # "Exploitable": eine Einstufung der Ressource, keine laufende Anlage. Sie darf
        # nie als Beleg fuer eine laufende Waermepumpe gelten. Geprueft wird
        # silver_waermenutzung, die Stufe vor v_test5. v_test5 selbst haelt seinen
        # Filter per Konstruktion ein.
        p.null("Ressourceneinstufung gilt nicht als Anlagenbeleg",
               """SELECT 1 FROM silver_waermenutzung
                  WHERE belegt_anlage
                    AND status IN ('Inconnu', 'Exploitable', 'Défectueux',
                                   'Konzession erteilt', 'bewilligt oder geplant',
                                   'ausser Betrieb', 'geplant',
                                   'geplant, nicht umgesetzt',
                                   'aufgehoben, zugeschüttet, versiegt')""")

    if p.hat("v_verdachtsliste_wirkung"):
        # Die Methodikzahlen des Exports kommen aus dieser Sicht. Ist sie leer, hat der
        # Export nichts Belegbares.
        p.zwischen("die Verdachtsliste ist gegen echte Labels gemessen",
                   "SELECT sum(n) FROM v_verdachtsliste_wirkung", 50, 100000)

    if p.hat("silver_baugesuche"):
        # Der Zuercher OGD-Datensatz gilt als personendatenfrei. Eine Gemeinde haengt
        # die Bauherrschaft aber als "K Nachname Vorname" an den Objektbeschrieb.
        p.null("keine Personenangaben im Zuercher Beschrieb",
               r"""SELECT 1 FROM silver_baugesuche
                   WHERE regexp_matches(beschrieb,
                         '\sK [A-ZÄÖÜ][a-zäöüß]+ [A-ZÄÖÜ]')""")

    if p.hat("silver_baugesuche_ch"):
        p.null("Baugesuch-Zuordnung trifft nur existierende Gebaeude",
               """SELECT 1 FROM match_baugesuche_ch m
                  LEFT JOIN silver_gebaeude_ch g USING (egid)
                  WHERE g.egid IS NULL""")
        p.null("Baugesuch und zugeordnetes Gebaeude im selben Kanton",
               """SELECT 1 FROM match_baugesuche_ch m
                  JOIN silver_gebaeude_ch g USING (egid)
                  WHERE g.kanton <> m.kanton""")
        p.null("je Vorhaben genau eine Erstpublikation",
               """SELECT vorhaben_id FROM silver_baugesuche_ch
                  GROUP BY 1 HAVING sum(ist_erstpublikation::INT) <> 1""")
        # Geprueft wird der anonymisierte Titel, weil er bei fehlendem Beschrieb in die
        # Liste gelangt. Zugesichert ist: Wo ein Schnitt moeglich war, wurde er
        # gemacht. Nicht "bis zum Stillstand", das wuerde Titel aus lauter kurzen
        # Abschnitten zerstoeren. Die Bauherrschaft steht im ersten Abschnitt.
        p.null("wo die Bauherrschaft stehen koennte, wurde geschnitten",
               """SELECT 1 FROM silver_baugesuche_ch
                  WHERE titel IS NOT NULL
                    AND bauherrschaft_schnitt(titel_vorspann_weg(titel))
                        <> titel_vorspann_weg(titel)
                    AND titel_anonym = titel_vorspann_weg(titel)""")
        # Der Formtest findet auch Objektbeschriebe, die zufaellig wie ein Name
        # aussehen. Die zwei verbleibenden Faelle sind von Hand geprueft und enthalten
        # keine Person. Waechst die Zahl, lohnt ein neuer Blick.
        p.hoechstens("kein namensfoermiger Titelabschnitt in der Arbeitsmappe",
                     r"""SELECT 1 FROM silver_baugesuche_ch
                         WHERE titel_anonym IS NOT NULL
                           AND regexp_matches(titel_anonym,
                               '^[A-ZÄÖÜ][A-Za-zÄÖÜäöüß''-]+'
                               || '( [A-ZÄÖÜ][A-Za-zÄÖÜäöüß''-]+){1,2};')""",
                     2, "zwei Obwaldner Objektbeschriebe, von Hand geprueft")
        # Sucht die Muster, mit denen Schwyz und Tessin Personen im Fliesstext fuehren.
        p.null("keine Personenangaben im Beschrieb",
               """SELECT 1 FROM silver_baugesuche_ch
                  WHERE beschrieb IS NOT NULL
                    AND regexp_matches(lower(beschrieb),
                        -- DuckDB nutzt RE2, und RE2 kennt keinen Lookahead. Statt
                        -- "Doppelpunkt, gefolgt von etwas anderem als [entfernt]" also:
                        -- Doppelpunkt, Leerraum, dann ein Zeichen, das weder Leerraum
                        -- noch oeffnende Klammer ist. Das Leerzeichen gehoert zwingend
                        -- in die verbotene Menge - sonst greift die Regel auf dem
                        -- Leerzeichen vor "[entfernt]" und meldet jeden sauberen Text.
                        '(projektverfasser|grundeigentumer|grundeigentümer|bauherrschaft|'
                        || 'istante|proprietario del fondo|progettista)'
                        || '[a-z]{0,3}\\s*:\\s*[^\\[[:space:]]')""")
        p.zwischen("Adresszuordnung greift bei einem brauchbaren Teil der Baugesuche",
                   """SELECT round(100.0 * count(DISTINCT bg_id)
                        / nullif((SELECT count(DISTINCT bg_id) FROM silver_baugesuche_ch
                                  WHERE ist_heizungsereignis AND ist_erstpublikation), 0), 1)
                      FROM match_baugesuche_ch""", 20, 100)


def main(argv: list[str]) -> int:
    ausfuehrlich = "-v" in argv
    if not config.DB.exists():
        print("Keine Datenbank gefunden. Zuerst:  python src/ingest.py && python src/pipeline.py ch")
        return 2
    # Lesend: Die Pruefungen schreiben nichts und laufen so auch, waehrend ein anderer
    # Prozess die Datenbank offen hat.
    con = pipeline.connect(schreibend=False)
    p = Pruefer(con)
    try:
        pruefe(p)
    finally:
        con.close()

    breite = max(len(e.name) for e in p.ergebnisse) + 2
    for e in p.ergebnisse:
        zeichen = "ok  " if e.bestanden else "FEHL"
        zeile = f"  [{zeichen}] {e.name:<{breite}}"
        if ausfuehrlich or not e.bestanden:
            zeile += f" gemessen {e.gemessen}, erwartet {e.erwartet}"
        print(zeile)

    gefallen = [e for e in p.ergebnisse if not e.bestanden]
    print(f"\n{len(p.ergebnisse) - len(gefallen)} von {len(p.ergebnisse)} Pruefungen bestanden")
    return 1 if gefallen else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
