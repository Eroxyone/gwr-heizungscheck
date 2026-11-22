-- Test 2: Gibt es genug Belege? Heizungs-Baugesuche pro Gemeinde und Monat, inkl. Zuordnungsquote.
-- Gezaehlt werden Vorhaben, nicht Publikationen: Dasselbe Baugesuch erscheint oft mehrfach.
-- Achtung: bfs_nr und municipality_name sind in den Baugesuchen erst ab 2025 gefuellt.
-- Fuer 2024 wird die Gemeinde deshalb hergeleitet.

CREATE OR REPLACE TABLE map_gemeinde AS
SELECT DISTINCT bfs_nr, gemeinde FROM silver_gebaeude;

-- PLZ/Ort -> BFS-Nummer, aus den GWR-Eingaengen, jeweils die haeufigste Gemeinde je PLZ+Ort
CREATE OR REPLACE TABLE map_plz AS
WITH z AS (
    SELECT a.plz, a.ort, g.bfs_nr, count(*) AS n,
           row_number() OVER (PARTITION BY a.plz, a.ort ORDER BY count(*) DESC) AS rang
    FROM silver_adressen a JOIN silver_gebaeude g USING (egid)
    GROUP BY 1, 2, 3
)
SELECT plz, ort, bfs_nr FROM z WHERE rang = 1;

CREATE OR REPLACE VIEW v_baugesuche AS
WITH via_egid AS (   -- BFS-Nummer aus den zugeordneten Gebaeuden, haeufigster Wert
    SELECT bg_id, bfs_nr FROM (
        SELECT bg_id, bfs_nr, row_number() OVER (PARTITION BY bg_id ORDER BY count(*) DESC) AS rang
        FROM match_all GROUP BY 1, 2
    ) WHERE rang = 1
)
SELECT b.*,
       COALESCE(b.bfs_nr_roh, e.bfs_nr, p.bfs_nr)              AS bfs_nr,
       COALESCE(mg1.gemeinde, mg2.gemeinde, mg3.gemeinde,
                b.gemeinde_txt, b.ort)                          AS gemeinde,
       CASE WHEN b.bfs_nr_roh IS NOT NULL THEN 'feld'
            WHEN e.bfs_nr     IS NOT NULL THEN 'via_egid'
            WHEN p.bfs_nr     IS NOT NULL THEN 'via_plz'
            ELSE 'offen' END                                    AS gemeinde_herkunft
FROM silver_baugesuche b
LEFT JOIN via_egid e USING (bg_id)
LEFT JOIN map_plz   p ON p.plz = b.plz AND p.ort = b.ort
LEFT JOIN map_gemeinde mg1 ON mg1.bfs_nr = b.bfs_nr_roh
LEFT JOIN map_gemeinde mg2 ON mg2.bfs_nr = e.bfs_nr
LEFT JOIN map_gemeinde mg3 ON mg3.bfs_nr = p.bfs_nr;

-- Auswertungsfenster: ab Oktober 2024 ist die Sammlung des Statistischen Amts vollstaendig
CREATE OR REPLACE VIEW v_test2_gemeinde AS
WITH fenster AS (
    SELECT date_diff('month', DATE '2024-10-01',
                     (SELECT max(pub_datum) FROM silver_baugesuche)) AS monate
),
z AS (
    SELECT v.bfs_nr, v.gemeinde,
           sum(v.ist_erstpublikation::INT)                                 AS baugesuche_total,
           sum((v.ist_heizungsereignis AND v.ist_erstpublikation)::INT)     AS heizungsgesuche,
           sum((v.ist_heizungsereignis AND v.ist_erstpublikation
                AND s.n_gebaeude IS NOT NULL)::INT)                         AS heizungsgesuche_mit_egid,
           sum((v.ist_heizungsereignis AND v.ist_erstpublikation
                AND s.n_gebaeude = 1)::INT)                                 AS heizungsgesuche_eindeutig
    FROM v_baugesuche v
    LEFT JOIN match_stats s USING (bg_id)
    WHERE v.pub_datum >= DATE '2024-10-01'
    GROUP BY 1, 2
)
SELECT z.*,
       round(z.heizungsgesuche * 12.0 / f.monate, 1)                        AS heizungsgesuche_pro_jahr,
       round(100.0 * z.heizungsgesuche / nullif(z.baugesuche_total, 0), 1)  AS pct_heizung,
       round(100.0 * z.heizungsgesuche_mit_egid / nullif(z.heizungsgesuche, 0), 1) AS pct_zugeordnet
FROM z, fenster f;

CREATE OR REPLACE VIEW v_test2_monat AS
SELECT date_trunc('month', pub_datum) AS monat,
       sum(ist_erstpublikation::INT)                            AS baugesuche_total,
       sum((ist_heizungsereignis AND ist_erstpublikation)::INT)  AS heizungsgesuche
FROM v_baugesuche GROUP BY 1 ORDER BY 1;
