-- Test 4 schweizweit: Photovoltaik vorhanden, GWR sagt fossil mit Quelle Volkszaehlung.
--
-- Eine Solaranlage sagt wenig ueber die Heizung: Sie zeigt, dass sich jemand mit dem
-- Gebaeude beschaeftigt hat. Neben einem Heizungseintrag aus der Volkszaehlung 2000 ist
-- das ein Indiz, kein Beleg.
--
-- Zwei Zuordnungswege, getrennt gefuehrt:
--   egid        Die BFE-Variante "csv/2056" traegt eine EGID-Spalte, ist aber auf
--               100'000 der 333'313 Anlagen gekuerzt. Wo die EGID vorliegt, hat sie
--               Vorrang.
--   koordinate  Der vollstaendige Datensatz traegt LV95-Koordinaten. Dann derselbe
--               20-m-Umkreis wie bei den Waermenutzungsanlagen, mit der in
--               reports/zuordnung_zg.md gemessenen Schwaeche.
-- Wo beide Wege greifen, muessen sie dasselbe Gebaeude nennen (v_solar_wege).

CREATE OR REPLACE TABLE silver_solar_ch AS
WITH voll AS (
    SELECT CAST(xtf_id AS VARCHAR)                  AS anlage_nr,
           Canton                                   AS kanton,
           Municipality                             AS gemeinde_txt,
           TRY_CAST(BeginningOfOperation AS DATE)   AS inbetriebnahme,
           TRY_CAST(TotalPower AS DOUBLE)           AS leistung_kw,
           SubCategory                              AS unterkategorie,
           TRY_CAST(_x AS DOUBLE)                   AS e_lv95,
           TRY_CAST(_y AS DOUBLE)                   AS n_lv95
    FROM read_csv('data/raw/epa/ElectricityProductionPlant.csv',
                  header = true, all_varchar = true)
    -- subcat_2 ist Photovoltaik. Andere Anlagen sagen nichts ueber die Heizung.
    WHERE SubCategory = 'subcat_2'
),
mit_egid AS (
    SELECT CAST(xtf_id AS VARCHAR) AS anlage_nr, TRY_CAST(EGID AS BIGINT) AS egid_amtlich
    FROM read_csv('data/raw/epa_egid/ElectricityProductionPlant.csv',
                  header = true, all_varchar = true)
    WHERE TRY_CAST(EGID AS BIGINT) IS NOT NULL
)
SELECT v.*, e.egid_amtlich
FROM voll v
LEFT JOIN mit_egid e USING (anlage_nr)
-- Anlagen ohne brauchbare Koordinate bleiben drin, solange sie eine EGID tragen.
WHERE v.e_lv95 BETWEEN 2480000 AND 2840000
   OR e.egid_amtlich IS NOT NULL;

CREATE OR REPLACE TABLE match_solar_ch AS
WITH ueber_egid AS (
    SELECT s.anlage_nr, s.egid_amtlich AS egid, 'egid' AS weg, NULL::DOUBLE AS dist_m
    FROM silver_solar_ch s
    WHERE s.egid_amtlich IS NOT NULL
),
-- Umkreis-Join als Gitter: Beide Seiten bekommen eine Zelle von 20 m Kantenlaenge, jede
-- Anlage wird auf ihre neun Nachbarzellen vervielfacht. Aus dem Bereichsvergleich
-- (BETWEEN) wird so ein Gleichheitsvergleich, den DuckDB als Hash-Join rechnet. Der
-- Range-Join ueber alle Anlagen und 3,2 Mio. Gebaeude dauerte rund 500 Sekunden.
-- Neun Zellen reichen, weil ein Punkt hoechstens 20 m weit reicht. Das Gitter grenzt
-- nur vor, die Distanzpruefung darunter entscheidet.
ueber_koordinate AS (
    WITH gebaeude AS (
        SELECT egid, kanton,
               e_lv95, n_lv95,
               CAST(floor(e_lv95 / 20) AS INTEGER) AS gx,
               CAST(floor(n_lv95 / 20) AS INTEGER) AS gy
        FROM silver_gebaeude_ch
        WHERE e_lv95 IS NOT NULL
    ),
    anlagen AS (
        SELECT anlage_nr, kanton, e_lv95, n_lv95,
               CAST(floor(e_lv95 / 20) AS INTEGER) + dx AS gx,
               CAST(floor(n_lv95 / 20) AS INTEGER) + dy AS gy
        FROM silver_solar_ch,
             (SELECT unnest([-1, 0, 1]) AS dx) d1,
             (SELECT unnest([-1, 0, 1]) AS dy) d2
        WHERE e_lv95 IS NOT NULL
    )
    SELECT a.anlage_nr, g.egid, 'koordinate' AS weg,
           round(sqrt(pow(a.e_lv95 - g.e_lv95, 2) + pow(a.n_lv95 - g.n_lv95, 2)), 1) AS dist_m
    FROM anlagen a
    JOIN gebaeude g ON g.kanton = a.kanton AND g.gx = a.gx AND g.gy = a.gy
    WHERE sqrt(pow(a.e_lv95 - g.e_lv95, 2) + pow(a.n_lv95 - g.n_lv95, 2)) <= 20
)
SELECT z.anlage_nr, z.egid, z.weg, z.dist_m,
       s.kanton, s.inbetriebnahme, s.leistung_kw,
       g.bfs_nr, g.gemeinde, g.energie_klasse, g.ist_fossil, g.ist_wohngebaeude,
       g.quelle_code, g.quelle_txt, g.quelle_datum, g.baujahr
FROM (SELECT * FROM ueber_egid UNION ALL SELECT * FROM ueber_koordinate) z
JOIN silver_solar_ch s USING (anlage_nr)
JOIN silver_gebaeude_ch g USING (egid);

-- Wo beide Wege greifen: Nennen sie dasselbe Gebaeude?
CREATE OR REPLACE VIEW v_solar_wege AS
SELECT count(DISTINCT anlage_nr)                                   AS anlagen_mit_beiden,
       count(DISTINCT CASE WHEN gleich THEN anlage_nr END)         AS beide_gleich,
       round(100.0 * count(DISTINCT CASE WHEN gleich THEN anlage_nr END)
             / nullif(count(DISTINCT anlage_nr), 0), 1)            AS pct_einig
FROM (
    SELECT k.anlage_nr, max((k.egid = e.egid)::INT)::BOOLEAN AS gleich
    FROM match_solar_ch k
    JOIN match_solar_ch e ON e.anlage_nr = k.anlage_nr AND e.weg = 'egid'
    WHERE k.weg = 'koordinate'
    GROUP BY 1
);

-- Genau ein Gebaeude je Anlage: Der EGID-Weg hat Vorrang, sonst gilt das naechstgelegene
-- Gebaeude. Der Umkreis-Join allein wuerde die Nachbarn mitzaehlen und den Befund von
-- 22'425 auf 40'586 Gebaeude aufblaehen (docs/datenquellen.md).
-- Bei Photovoltaik ist das vertretbar, weil die Anlage auf dem Gebaeude liegt: Wo
-- beide Zuordnungswege vorliegen, nennen sie in 99,4 % der Faelle dasselbe Gebaeude.
-- Bei den Sonden in Zug trifft das naechste Gebaeude nur in 65 %
-- (reports/zuordnung_zg.md).
-- Die EGID am Ende der Sortierung macht die Auswahl bei gleicher Distanz
-- reproduzierbar, unabhaengig vom Join-Verfahren.
-- Die Sicht wird vom Test unten und von gold_verdacht.sql benutzt.
CREATE OR REPLACE VIEW v_solar_gebaeude AS
SELECT DISTINCT ON (anlage_nr) *
FROM match_solar_ch
ORDER BY anlage_nr, CASE weg WHEN 'egid' THEN 0 ELSE 1 END, dist_m, egid;

-- Der Test: fossiler Eintrag aus der Volkszaehlung 2000 und eine Photovoltaikanlage.
CREATE OR REPLACE VIEW v_test4_ch AS
WITH bester_weg AS (SELECT * FROM v_solar_gebaeude)
SELECT kanton, bfs_nr, gemeinde, egid, anlage_nr, weg, inbetriebnahme, leistung_kw,
       energie_klasse, quelle_code, quelle_txt, quelle_datum, baujahr
FROM bester_weg
WHERE ist_wohngebaeude
  AND ist_fossil
  AND quelle_code = '860';

CREATE OR REPLACE TABLE gold_solar_gemeinde AS
SELECT kanton, bfs_nr, gemeinde,
       count(DISTINCT egid)                                        AS gebaeude_mit_pv_fossil_vz2000,
       count(DISTINCT anlage_nr)                                   AS anlagen,
       round(avg(leistung_kw), 1)                                  AS leistung_kw_schnitt,
       min(inbetriebnahme)                                         AS erste_anlage,
       max(inbetriebnahme)                                         AS letzte_anlage
FROM v_test4_ch
GROUP BY 1, 2, 3;
