-- Adressen und ihre Normalisierung.
--
-- Eigene Datei, weil zwei Schritte die Tabelle brauchen: die Zuordnung der Baugesuche
-- und die Zuordnung der Waermenutzungsanlagen. Die zweite soll nicht ausfallen, wenn
-- der Amtsblatt-Abzug fehlt.

-- "Bahnhofstr. 4a" und "Bahnhofstrasse 4 a" sind dieselbe Adresse. Im schweizweiten
-- Strang und bei den Anlagen laufen deshalb beide Seiten des Vergleichs durch diese
-- Makros. Der Zuercher Strang (silver.sql, silver_baugesuche.sql) normalisiert mit
-- eigenen Ausdruecken, ohne die Angleichung von "str" an "strasse".
CREATE OR REPLACE MACRO strasse_norm(s) AS
    regexp_replace(
        regexp_replace(lower(strip_accents(COALESCE(s, ''))), '[^a-z0-9]', '', 'g'),
        '(str)$', 'strasse');

CREATE OR REPLACE MACRO hausnr_norm(s) AS
    regexp_replace(lower(regexp_replace(COALESCE(s, ''), '[^0-9a-zA-Z]', '', 'g')),
                   '^0+', '');

CREATE OR REPLACE TABLE silver_adresse_ch AS
SELECT TRY_CAST(EGID AS BIGINT)          AS egid,
       kanton,
       STRNAME                           AS strasse,
       DEINR                             AS hausnummer,
       DPLZ4                             AS plz,
       DPLZNAME                          AS ort,
       TRY_CAST(DKODE AS DOUBLE)         AS e_lv95,
       TRY_CAST(DKODN AS DOUBLE)         AS n_lv95,
       strasse_norm(STRNAME)             AS strasse_k,
       hausnr_norm(DEINR)                AS hausnr_k,
       -- DOFFADR = 1 markiert die offizielle Adresse. Ein Gebaeude kann mehrere
       -- Eingaenge haben.
       (DOFFADR = '1')                   AS ist_offiziell,
       snapshot_date                     AS stand
FROM read_parquet('data/snapshots/gwr_adresse/**/*.parquet', hive_partitioning = true)
-- Nur der juengste Stand. Das Maximum laeuft ueber die verschiedenen Staende statt
-- direkt ueber den Scan: "SELECT max(snapshot_date) FROM read_parquet(...)" scheitert in
-- DuckDB 1.5 mit einem internen Fehler, sobald genau eine Snapshot-Datei vorliegt
-- (abgedeckt in tests/test_pipeline_ch.py).
WHERE snapshot_date = (
          SELECT max(stand)
          FROM (SELECT DISTINCT snapshot_date AS stand
                FROM read_parquet('data/snapshots/gwr_adresse/**/*.parquet',
                                  hive_partitioning = true)))
  AND TRY_CAST(EGID AS BIGINT) IS NOT NULL;
