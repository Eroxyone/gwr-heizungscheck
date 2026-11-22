-- Zuordnung Baugesuch -> EGID.
-- Zwei unabhaengige Wege, damit die Qualitaet gegenseitig pruefbar bleibt:
--   A) raeumlich: GWR-Gebaeudepunkt liegt im Parzellen-Polygon des Baugesuchs (nur Gesuche ab 2025)
--   B) ueber die Adresse: normalisierte Strasse + Hausnummer + PLZ gegen die GWR-Eingaenge

-- A) raeumlich
CREATE OR REPLACE TABLE match_geo AS
WITH pts AS (
    SELECT egid, bfs_nr, gemeinde, ST_Point(e_lv95, n_lv95) AS pt
    FROM silver_gebaeude
    WHERE e_lv95 IS NOT NULL AND n_lv95 IS NOT NULL
)
SELECT g.bg_id, p.egid, p.bfs_nr, p.gemeinde, 'geo' AS methode
FROM silver_baugesuche_geo g
JOIN pts p ON ST_Intersects(g.geom, p.pt);

-- B) ueber die Adresse
CREATE OR REPLACE TABLE match_adr AS
SELECT DISTINCT b.bg_id, a.egid, g.bfs_nr, g.gemeinde, 'adresse' AS methode
FROM silver_baugesuche b
JOIN silver_adressen a
  ON a.strasse_norm = b.strasse_norm
 AND a.hnr_norm     = b.hnr_norm
 AND a.plz          = b.plz
JOIN silver_gebaeude g ON g.egid = a.egid
WHERE b.strasse_norm <> '' AND b.hnr_norm <> '' AND b.plz IS NOT NULL;

-- Vereinigung mit Herkunftskennzeichen
CREATE OR REPLACE TABLE match_all AS
SELECT bg_id, egid, bfs_nr, gemeinde,
       bool_or(methode = 'geo')     AS via_geo,
       bool_or(methode = 'adresse') AS via_adresse
FROM (SELECT * FROM match_geo UNION ALL SELECT * FROM match_adr)
GROUP BY 1, 2, 3, 4;

-- Kennzahlen je Baugesuch: wie viele Gebaeude wurden zugeordnet?
CREATE OR REPLACE TABLE match_stats AS
SELECT bg_id,
       count(*)                    AS n_gebaeude,
       sum(via_geo::INT)           AS n_via_geo,
       sum(via_adresse::INT)       AS n_via_adresse,
       sum((via_geo AND via_adresse)::INT) AS n_beide
FROM match_all GROUP BY 1;
