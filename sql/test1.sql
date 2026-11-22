-- Test 1: Groesse des Problems - fossile Heizungen mit ungeprueftem/altem Eintrag.
-- Stichtag fuer "alt": Aktualisierungsdatum aelter als 15 Jahre.

CREATE OR REPLACE VIEW v_test1_gebaeude AS
SELECT *,
    (quelle_datum IS NULL OR quelle_datum < DATE '2026-09-13' - INTERVAL 15 YEAR) AS datum_alt,
    (ist_fossil AND (quelle_code = '860'
        OR quelle_datum IS NULL
        OR quelle_datum < DATE '2026-09-13' - INTERVAL 15 YEAR))                  AS ist_kandidat
FROM silver_gebaeude
WHERE gkat IN ('1020', '1030', '1040');   -- Gebaeude mit Wohnnutzung

CREATE OR REPLACE VIEW v_test1_gemeinde AS
SELECT bfs_nr, gemeinde,
    count(*)                                                  AS wohngebaeude,
    sum(ist_fossil::INT)                                      AS fossil,
    round(100.0 * sum(ist_fossil::INT) / count(*), 1)         AS pct_fossil,
    sum(ist_kandidat::INT)                                    AS kandidaten,
    round(100.0 * sum(ist_kandidat::INT) / count(*), 1)       AS pct_kandidaten,
    round(100.0 * sum((quelle_code = '860')::INT) / count(*), 1) AS pct_quelle_vz2000,
    round(100.0 * sum((quelle_code = '869')::INT) / count(*), 1) AS pct_quelle_baubew
FROM v_test1_gebaeude
GROUP BY 1, 2;
