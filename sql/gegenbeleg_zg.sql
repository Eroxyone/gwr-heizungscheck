-- Der Zuger Tankkataster: der zweite Gegenbeleg.
--
-- Zug fuehrt seine Tanks in vier getrennten Layern: im oder am Gebaeude bzw. erdverlegt,
-- je einmal "in Betrieb" und "ausser Betrieb". Die Unterscheidung steckt also in der
-- Layerwahl, nicht in einem Statusfeld.
--   Heizoeltank in Betrieb        -> die Oelheizung laeuft, der GWR-Eintrag stimmt wohl
--   Heizoeltank ausser Betrieb    -> stuetzt den Verdacht
--
-- Der Kataster traegt keine EGID, nur Koordinaten. Ein Tank steht im Gebaeude, nicht im
-- Garten, deshalb ist das weniger heikel als bei den Erdwaermesonden. Der Umkreis ist
-- trotzdem 10 m statt 20: Ein Fehltreffer beim Gegenbeleg nimmt einen richtigen Fall
-- von der Liste.
--
-- Nur Heizoel zaehlt. Diesel, Benzin und Chemikalien sagen nichts ueber die Heizung.

CREATE OR REPLACE TABLE silver_tank_zg AS
SELECT * FROM (
    SELECT 'gebaeude' AS lage, TRUE  AS in_betrieb, objectnumber AS tank_nr,
           tankstatus AS status, substance AS stoff, TRY_CAST(volume AS DOUBLE) AS liter,
           geometry AS geom
    FROM st_read('data/raw/waermenutzung_weitere/ZG_tank_gebaeude_in_betrieb.gml')
    UNION ALL BY NAME
    SELECT 'gebaeude' AS lage, FALSE AS in_betrieb, objectnumber AS tank_nr,
           tankstatus AS status, substance AS stoff, TRY_CAST(volume AS DOUBLE) AS liter,
           geometry AS geom
    FROM st_read('data/raw/waermenutzung_weitere/ZG_tank_gebaeude_ausser_betrieb.gml')
    UNION ALL BY NAME
    SELECT 'erdverlegt' AS lage, TRUE AS in_betrieb, objectnumber AS tank_nr,
           tankstatus AS status, substance AS stoff, TRY_CAST(volume AS DOUBLE) AS liter,
           geometry AS geom
    FROM st_read('data/raw/waermenutzung_weitere/ZG_tank_erdverlegt_in_betrieb.gml')
    UNION ALL BY NAME
    SELECT 'erdverlegt' AS lage, FALSE AS in_betrieb, objectnumber AS tank_nr,
           tankstatus AS status, substance AS stoff, TRY_CAST(volume AS DOUBLE) AS liter,
           geometry AS geom
    FROM st_read('data/raw/waermenutzung_weitere/ZG_tank_erdverlegt_ausser_betrieb.gml')
)
WHERE stoff = 'Heizöl' AND geom IS NOT NULL;

-- Zuordnung ueber einen 10-m-Umkreis, als Gitter-Join.
CREATE OR REPLACE TABLE match_tank_zg AS
WITH tank AS (
    SELECT tank_nr, lage, in_betrieb, liter,
           ST_X(ST_Centroid(geom)) AS e_lv95,
           ST_Y(ST_Centroid(geom)) AS n_lv95
    FROM silver_tank_zg
),
gestreut AS (
    SELECT t.*, CAST(floor(e_lv95 / 10) AS INTEGER) + dx AS gx,
                CAST(floor(n_lv95 / 10) AS INTEGER) + dy AS gy
    FROM tank t, (SELECT unnest([-1, 0, 1]) AS dx) d1, (SELECT unnest([-1, 0, 1]) AS dy) d2
),
geb AS (
    SELECT egid, e_lv95, n_lv95,
           CAST(floor(e_lv95 / 10) AS INTEGER) AS gx,
           CAST(floor(n_lv95 / 10) AS INTEGER) AS gy
    FROM silver_gebaeude_ch WHERE kanton = 'ZG' AND e_lv95 IS NOT NULL
)
SELECT g.egid, t.tank_nr, t.lage, t.in_betrieb, t.liter,
       round(sqrt(pow(t.e_lv95 - g.e_lv95, 2) + pow(t.n_lv95 - g.n_lv95, 2)), 1) AS dist_m
FROM gestreut t
JOIN geb g ON g.gx = t.gx AND g.gy = t.gy
WHERE sqrt(pow(t.e_lv95 - g.e_lv95, 2) + pow(t.n_lv95 - g.n_lv95, 2)) <= 10;

CREATE OR REPLACE VIEW v_tank_zg AS
SELECT egid,
       count(*)                                  AS tanks,
       bool_or(in_betrieb)                       AS oeltank_in_betrieb,
       bool_or(NOT in_betrieb)                   AS oeltank_ausser_betrieb,
       min(dist_m)                               AS naechster_tank_m
FROM match_tank_zg
GROUP BY egid;

-- --------------------------------------------------------- Gegenbelege zusammengefasst
-- Genf und Zug in einer Sicht: Laeuft die fossile Heizung noch? Der Verdachts-Layer
-- muss die Herkunft der Antwort nicht kennen.
CREATE OR REPLACE VIEW v_gegenbeleg_fossil AS
SELECT egid, 'GE Feuerungskataster' AS quelle,
       fossil_aktiv                 AS fossil_aktiv,
       fossil_stillgelegt           AS fossil_stillgelegt
FROM v_ge_istzustand
UNION ALL
SELECT egid, 'ZG Tankkataster' AS quelle,
       oeltank_in_betrieb     AS fossil_aktiv,
       oeltank_ausser_betrieb AS fossil_stillgelegt
FROM v_tank_zg t
JOIN silver_gebaeude_ch g USING (egid)
WHERE g.kanton = 'ZG' AND g.energie_klasse = 'oel';

CREATE OR REPLACE VIEW v_gegenbeleg AS
SELECT egid,
       string_agg(DISTINCT quelle, ', ')  AS gegenbeleg_quelle,
       bool_or(fossil_aktiv)              AS fossil_aktiv,
       bool_or(fossil_stillgelegt)        AS fossil_stillgelegt
FROM v_gegenbeleg_fossil
GROUP BY egid;
