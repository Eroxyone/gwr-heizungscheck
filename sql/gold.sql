-- Gold-Layer: Kennzahlen zur Pflege der Heizungsangaben, je Gemeinde und je Kanton.
--
-- Zur Interpretation: Die Kennzahlen messen, wie gut ein Register gepflegt aussieht,
-- nicht wie richtig es ist. Die Stadt Zuerich erreicht hohe Werte und hat trotzdem bei
-- rund zwei Dritteln der Heizungs-Baugesuche keine Nachfuehrung (Test 3). Neben dem
-- Index steht deshalb das Pflegemuster: Ein Sammelimport sieht im Index aus wie gute
-- Pflege.

-- --------------------------------------------------------------------------- Basis
CREATE OR REPLACE VIEW v_gold_basis AS
SELECT * FROM silver_gebaeude_ch WHERE ist_wohngebaeude;

-- --------------------------------------------------------------------------- Kennzahlen
-- Dieselben Kennzahlen auf zwei Ebenen. Jede Kennzahl ist genau einmal definiert:
-- GROUPING SETS rechnet sie je Gemeinde und je Kanton, die Spalte ebene sagt, welche
-- Zeile zu welcher Ebene gehoert. gold_gemeinde und gold_kanton sind Ausschnitte
-- dieser Sicht und koennen deshalb nicht auseinanderlaufen.
CREATE OR REPLACE VIEW v_gold_kennzahlen AS
WITH z AS (
    SELECT
        CASE WHEN GROUPING(bfs_nr) = 1 THEN 'kanton' ELSE 'gemeinde' END AS ebene,
        kanton, bfs_nr, gemeinde, max(stand) AS stand,
        count(DISTINCT bfs_nr)                                         AS gemeinden,
        count(*)                                                       AS wohngebaeude,
        sum(hat_angabe::INT)                                           AS mit_angabe,
        sum((quelle_datum >= stand - INTERVAL 5 YEAR)::INT)            AS aktuell_5j,
        sum((quelle_datum >= stand - INTERVAL 15 YEAR)::INT)           AS aktuell_15j,
        sum(quelle_vz2000::INT)                                        AS aus_vz2000,
        sum(ist_fossil::INT)                                           AS fossil,
        sum((energie_klasse = 'waermepumpe')::INT)                     AS waermepumpe,
        sum((energie_klasse = 'fernwaerme')::INT)                      AS fernwaerme,
        sum((energie_klasse = 'holz')::INT)                            AS holz,
        sum((ist_fossil AND (quelle_vz2000 OR quelle_datum IS NULL
             OR quelle_datum < stand - INTERVAL 15 YEAR))::INT)        AS kandidaten,
        median(alter_jahre)                                            AS median_alter_jahre,
        count(DISTINCT quelle_code)                                    AS anzahl_quellen,
        sum((quelle_datum >= stand - INTERVAL 1 YEAR)::INT)            AS aktualisiert_12m
    FROM v_gold_basis
    GROUP BY GROUPING SETS ((kanton, bfs_nr, gemeinde), (kanton))
)
SELECT z.*,
    round(100.0 * mit_angabe   / nullif(wohngebaeude, 0), 1)                      AS pct_vollstaendig,
    round(100.0 * aktuell_5j   / nullif(wohngebaeude, 0), 1)                      AS pct_aktuell_5j,
    round(100.0 * aktuell_15j  / nullif(wohngebaeude, 0), 1)                      AS pct_aktuell_15j,
    round(100.0 * aus_vz2000   / nullif(wohngebaeude, 0), 1)                      AS pct_vz2000,
    round(100.0 * (wohngebaeude - aus_vz2000) / nullif(wohngebaeude, 0), 1)       AS pct_ohne_vz2000,
    round(100.0 * fossil       / nullif(wohngebaeude, 0), 1)                      AS pct_fossil,
    round(100.0 * waermepumpe  / nullif(wohngebaeude, 0), 1)                      AS pct_waermepumpe,
    round(100.0 * kandidaten   / nullif(wohngebaeude, 0), 1)                      AS pct_kandidaten,
    round(100.0 * aktualisiert_12m / nullif(wohngebaeude, 0), 1)                  AS pct_bewegung_12m,
    -- Pflege-Index: Mittel aus Vollstaendigkeit, Aktualitaet und Herkunft, 0 bis 100
    round((100.0 * mit_angabe  / nullif(wohngebaeude, 0)
         + 100.0 * aktuell_15j / nullif(wohngebaeude, 0)
         + 100.0 * (wohngebaeude - aus_vz2000) / nullif(wohngebaeude, 0)) / 3.0, 1) AS pflege_index
FROM z;

-- Je Gemeinde. Die Zahl der Gemeinden waere hier immer eins.
CREATE OR REPLACE TABLE gold_gemeinde AS
SELECT * EXCLUDE (ebene, gemeinden)
FROM v_gold_kennzahlen WHERE ebene = 'gemeinde';

-- Je Kanton, ohne die Spalten, die nur auf Gemeindeebene gefuehrt werden.
CREATE OR REPLACE TABLE gold_kanton AS
SELECT * EXCLUDE (ebene, bfs_nr, gemeinde, fernwaerme, holz, anzahl_quellen)
FROM v_gold_kennzahlen WHERE ebene = 'kanton';

-- --------------------------------------------------------------------------- Pflegemuster
-- Der Index oben belohnt Sammelimporte: Basel-Stadt traegt bei 99 % aller Wohngebaeude
-- dasselbe Aktualisierungsdatum und erreicht damit 100 Punkte. Diese Kennzahlen trennen
-- einen einmaligen Schub von laufender Pflege.
--
-- Die Volkszaehlung 2000 ist hier ausgeschlossen. Sonst misst die Kennzahl bei schlecht
-- gepflegten Kantonen den unbearbeiteten Altbestand (alle tragen den 29.11.2001) statt
-- eines Imports, und Zuerich saehe nach Sammelimport aus.
CREATE OR REPLACE TABLE gold_pflegemuster AS
WITH grenze AS (SELECT max(stand) - INTERVAL 24 MONTH AS ab FROM v_gold_basis),
verteilung AS (
    SELECT kanton, bfs_nr, quelle_datum, count(*) AS n
    FROM v_gold_basis WHERE quelle_datum IS NOT NULL AND NOT quelle_vz2000
    GROUP BY 1, 2, 3
),
anteile AS (
    SELECT *, n::DOUBLE / sum(n) OVER (PARTITION BY kanton, bfs_nr) AS anteil
    FROM verteilung
)
SELECT kanton, bfs_nr,
       sum(n)                                                          AS mit_datum,
       count(*)                                                        AS verschiedene_daten,
       count(*) FILTER (WHERE quelle_datum >= (SELECT ab FROM grenze))
                                                                       AS aktive_tage_24m,
       round(100.0 * max(anteil), 1)                                   AS pct_groesstes_datum,
       round(sum(anteil * anteil), 4)                                  AS datums_konzentration
FROM anteile GROUP BY 1, 2;

CREATE OR REPLACE TABLE gold_pflegemuster_kanton AS
WITH grenze AS (SELECT max(stand) - INTERVAL 24 MONTH AS ab FROM v_gold_basis),
verteilung AS (
    SELECT kanton, quelle_datum, count(*) AS n
    FROM v_gold_basis WHERE quelle_datum IS NOT NULL AND NOT quelle_vz2000 GROUP BY 1, 2
),
anteile AS (
    SELECT *, n::DOUBLE / sum(n) OVER (PARTITION BY kanton) AS anteil FROM verteilung
)
SELECT kanton,
       sum(n)                                                          AS mit_datum,
       count(*)                                                        AS verschiedene_daten,
       count(*) FILTER (WHERE quelle_datum >= (SELECT ab FROM grenze))
                                                                       AS aktive_tage_24m,
       round(100.0 * max(anteil), 1)                                   AS pct_groesstes_datum,
       round(sum(anteil * anteil), 4)                                  AS datums_konzentration
FROM anteile GROUP BY 1;

-- --------------------------------------------------------------------------- Gesamtsichten
CREATE OR REPLACE VIEW v_gold_kanton AS
SELECT k.*,
    m.pct_groesstes_datum, m.verschiedene_daten, m.aktive_tage_24m, m.datums_konzentration,
    CASE WHEN k.pct_aktuell_15j < 50      THEN 'Rueckstand'
         WHEN m.pct_groesstes_datum >= 40 THEN 'Sammelimport'
         WHEN m.aktive_tage_24m >= 250    THEN 'laufend'
         ELSE                                  'sporadisch' END AS pflegemuster,
    CASE WHEN k.pflege_index >= 90 THEN 'A'  WHEN k.pflege_index >= 75 THEN 'B'
         WHEN k.pflege_index >= 60 THEN 'C'  WHEN k.pflege_index >= 45 THEN 'D'
         ELSE 'E' END AS note
FROM gold_kanton k LEFT JOIN gold_pflegemuster_kanton m USING (kanton);

CREATE OR REPLACE VIEW v_gold_gemeinde AS
SELECT g.*,
    m.pct_groesstes_datum, m.aktive_tage_24m, m.datums_konzentration,
    CASE WHEN g.pct_aktuell_15j < 50      THEN 'Rueckstand'
         WHEN m.pct_groesstes_datum >= 40 THEN 'Sammelimport'
         WHEN m.aktive_tage_24m >= 24     THEN 'laufend'
         ELSE                                  'sporadisch' END AS pflegemuster,
    CASE WHEN g.pflege_index >= 90 THEN 'A'  WHEN g.pflege_index >= 75 THEN 'B'
         WHEN g.pflege_index >= 60 THEN 'C'  WHEN g.pflege_index >= 45 THEN 'D'
         ELSE 'E' END AS note
FROM gold_gemeinde g LEFT JOIN gold_pflegemuster m USING (kanton, bfs_nr);

-- --------------------------------------------------------------------------- Quellenmix
CREATE OR REPLACE TABLE gold_quellenmix AS
SELECT kanton,
       COALESCE(quelle_code, '(leer)')                                     AS quelle_code,
       COALESCE(quelle_txt, 'ohne Angabe')                                 AS quelle_txt,
       count(*)                                                            AS gebaeude,
       round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY kanton), 1) AS pct
FROM v_gold_basis GROUP BY 1, 2, 3;

-- --------------------------------------------------------------------------- Altersprofil
CREATE OR REPLACE TABLE gold_altersprofil AS
SELECT kanton,
       CASE WHEN quelle_datum IS NULL THEN '9 ohne Datum'
            WHEN alter_jahre <  2     THEN '0 unter 2 Jahre'
            WHEN alter_jahre <  5     THEN '1 2 bis 4 Jahre'
            WHEN alter_jahre < 10     THEN '2 5 bis 9 Jahre'
            WHEN alter_jahre < 15     THEN '3 10 bis 14 Jahre'
            WHEN alter_jahre < 20     THEN '4 15 bis 19 Jahre'
            ELSE                           '5 20 Jahre und aelter' END     AS altersklasse,
       count(*)                                                            AS gebaeude,
       round(100.0 * count(*) / sum(count(*)) OVER (PARTITION BY kanton), 1) AS pct
FROM v_gold_basis GROUP BY 1, 2;

-- --------------------------------------------------------------------------- Zeitreihe
-- Greift erst, sobald mindestens zwei Snapshot-Staende vorliegen. Misst, wie viele
-- Heizungsangaben sich zwischen zwei Staenden tatsaechlich geaendert haben - die
-- Kennzahl, die ein einzelner Snapshot nicht hergibt.
--
-- Der Vergleich laeuft ueber einen FULL JOIN, damit Zugaenge (neue EGID) und Abgaenge
-- (verschwundene EGID) sichtbar bleiben statt stillschweigend herauszufallen.
CREATE OR REPLACE VIEW v_gold_veraenderung AS
WITH staende AS (
    SELECT DISTINCT kanton, snapshot_date FROM bronze_gwr_snapshots
),
paare AS (
    SELECT kanton, snapshot_date AS stand_neu,
           lag(snapshot_date) OVER (PARTITION BY kanton ORDER BY snapshot_date) AS stand_alt
    FROM staende
),
-- Beide Seiten getrennt aufbauen und erst dann verbinden. Ein FULL JOIN direkt gegen
-- die paare-Tabelle wuerde fuer neue EGID auch kanton und Stand auf NULL setzen, weil
-- diese Spalten nur von der linken Seite kommen - Zugaenge landeten dann in einer
-- NULL-Gruppe statt beim Kanton.
vorher AS (
    SELECT p.kanton, p.stand_alt, p.stand_neu,
           s.EGID, s.GENH1, s.GWAERSCEH1, s.GWAERDATH1, s.GKAT
    FROM paare p
    JOIN bronze_gwr_snapshots s ON s.kanton = p.kanton AND s.snapshot_date = p.stand_alt
    WHERE p.stand_alt IS NOT NULL
),
nachher AS (
    SELECT p.kanton, p.stand_alt, p.stand_neu,
           s.EGID, s.GENH1, s.GWAERSCEH1, s.GWAERDATH1, s.GKAT
    FROM paare p
    JOIN bronze_gwr_snapshots s ON s.kanton = p.kanton AND s.snapshot_date = p.stand_neu
    WHERE p.stand_alt IS NOT NULL
),
vergleich AS (
    SELECT COALESCE(a.kanton, n.kanton)        AS kanton,
           COALESCE(a.stand_alt, n.stand_alt)  AS stand_alt,
           COALESCE(a.stand_neu, n.stand_neu)  AS stand_neu,
           a.EGID AS egid_alt, n.EGID AS egid_neu,
           a.GENH1 AS traeger_alt, n.GENH1 AS traeger_neu,
           a.GWAERSCEH1 AS quelle_alt, n.GWAERSCEH1 AS quelle_neu,
           a.GWAERDATH1 AS datum_alt, n.GWAERDATH1 AS datum_neu,
           COALESCE(n.GKAT, a.GKAT) AS gkat
    FROM vorher a
    FULL JOIN nachher n
      ON n.kanton = a.kanton AND n.stand_neu = a.stand_neu AND n.EGID = a.EGID
)
SELECT kanton, stand_alt, stand_neu,
       count(*) FILTER (WHERE egid_alt IS NOT NULL AND egid_neu IS NOT NULL) AS gebaeude_verglichen,
       count(*) FILTER (WHERE egid_alt IS NULL)                              AS zugaenge,
       count(*) FILTER (WHERE egid_neu IS NULL)                              AS abgaenge,
       count(*) FILTER (WHERE egid_alt IS NOT NULL AND egid_neu IS NOT NULL
                          AND traeger_alt IS DISTINCT FROM traeger_neu)      AS traeger_geaendert,
       count(*) FILTER (WHERE egid_alt IS NOT NULL AND egid_neu IS NOT NULL
                          AND quelle_alt IS DISTINCT FROM quelle_neu)        AS quelle_geaendert,
       count(*) FILTER (WHERE egid_alt IS NOT NULL AND egid_neu IS NOT NULL
                          AND datum_alt IS DISTINCT FROM datum_neu)          AS datum_geaendert,
       count(*) FILTER (WHERE egid_alt IS NOT NULL AND egid_neu IS NOT NULL
                          AND datum_alt IS DISTINCT FROM datum_neu
                          AND gkat IN ('1020','1030','1040'))                AS datum_geaendert_wohnen,
       round(100.0 * count(*) FILTER (WHERE egid_alt IS NOT NULL AND egid_neu IS NOT NULL
                                        AND datum_alt IS DISTINCT FROM datum_neu)
             / nullif(count(*) FILTER (WHERE egid_alt IS NOT NULL AND egid_neu IS NOT NULL), 0),
             3)                                                              AS pct_bewegt
FROM vergleich GROUP BY 1, 2, 3;
