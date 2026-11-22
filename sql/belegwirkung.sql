-- Was ist ein Beleg wert? Gemessen wird die Trefferquote je Belegart, nicht entlang
-- einer Rangfolge nach Score. Der Score ist grobkoernig: Viele Faelle teilen dieselbe
-- Punktzahl, und ein Rangschnitt (Top-K) misst dann den Tiebreak der Sortierung. Eine
-- Belegart ist klar abgegrenzt und kommt ohne Rangfolge aus.

-- ------------------------------------------------------------------ Alle Labels
-- Genf und Zug in einer Sicht, mit Herkunft und Sicherheit des Labels.
CREATE OR REPLACE VIEW v_label_alle AS
SELECT egid, 'GE' AS label_kanton, label, eintrag_falsch, label_sicherheit
FROM v_ge_label_klar
UNION ALL
SELECT egid, 'ZG' AS label_kanton, label, eintrag_falsch, label_sicherheit
FROM v_zg_label_klar;

-- ------------------------------------------------------------------ Belegart
-- Genau eine Belegart je Gebaeude, in der Reihenfolge der Aussagekraft. Ein Gebaeude
-- mit Baugesuch und Anlage zaehlt beim Baugesuch, sonst gingen die Summen nicht auf.
CREATE OR REPLACE VIEW v_belegart AS
SELECT s.egid, s.kanton,
       CASE
           WHEN s.hat_baugesuch                          THEN 'Baugesuch'
           WHEN s.hat_sonde AND s.sonde_dist_m <= 10     THEN 'Anlage bis 10 m'
           WHEN s.hat_sonde                              THEN 'Anlage 10 bis 20 m'
           WHEN s.ws_art = 'fernwaerme'                  THEN 'Warmwasser an Fernwärme'
           WHEN s.ws_art = 'erzeuger'                    THEN 'Register widerspricht sich'
           WHEN s.ws_art IS NOT NULL                     THEN 'Warmwasser-Wärmepumpe'
           WHEN s.hat_pv                                 THEN 'nur Photovoltaik'
           ELSE                                               'kein externer Beleg'
       END AS belegart,
       s.konfidenz, s.score
FROM v_gold_score s;

-- ------------------------------------------------------------------ Die Messung
CREATE OR REPLACE VIEW v_belegwirkung AS
WITH grundrate AS (
    SELECT label_kanton, avg(eintrag_falsch::INT) AS basis
    FROM v_label_alle GROUP BY 1
)
SELECT l.label_kanton, b.belegart,
       count(*)                                              AS n,
       sum(l.eintrag_falsch::INT)                            AS falsch,
       round(100.0 * avg(l.eintrag_falsch::INT), 1)          AS praezision,
       round(100.0 * any_value(g.basis), 1)                  AS grundrate,
       round(avg(l.eintrag_falsch::INT) / any_value(g.basis), 1) AS faktor
FROM v_belegart b
JOIN v_label_alle l USING (egid)
JOIN grundrate g ON g.label_kanton = l.label_kanton
GROUP BY 1, 2;

-- ------------------------------------------------------------------ Uebertragbarkeit
-- Zug liefert an 805 Anlagen die amtliche EGID und an vielen weiteren die Adresse. Die
-- gemessene Trefferquote beruht auf dieser amtlichen Zuordnung. Zuerich liefert nichts
-- davon (38'553 Bohrungen ohne EGID, Adresse und Status), dort bleibt der
-- 20-Meter-Umkreis. Deshalb hier dieselben Zuger Anlagen noch einmal, nur ueber den
-- Umkreis zugeordnet. Das Ergebnis ist die Erwartung fuer Zuerich.
CREATE OR REPLACE VIEW v_zg_umkreis AS
WITH geb AS (
    SELECT egid, e_lv95, n_lv95, ist_fossil, ist_wohngebaeude, energie_klasse
    FROM silver_gebaeude_ch WHERE kanton = 'ZG' AND e_lv95 IS NOT NULL
),
paare AS (
    SELECT a.anlage_id, g.egid, g.ist_fossil, g.ist_wohngebaeude, g.energie_klasse,
           a.ist_gebaut, a.belegt_anlage,
           round(sqrt(pow(a.e_lv95 - g.e_lv95, 2)
                      + pow(a.n_lv95 - g.n_lv95, 2)), 1) AS dist_m
    FROM silver_waermenutzung a
    JOIN geb g ON g.e_lv95 BETWEEN a.e_lv95 - 20 AND a.e_lv95 + 20
              AND g.n_lv95 BETWEEN a.n_lv95 - 20 AND a.n_lv95 + 20
    WHERE a.kanton = 'ZG' AND a.e_lv95 IS NOT NULL
      AND sqrt(pow(a.e_lv95 - g.e_lv95, 2) + pow(a.n_lv95 - g.n_lv95, 2)) <= 20
),
je_anlage AS (
    SELECT anlage_id, count(*) AS gebaeude_im_umkreis,
           sum((energie_klasse = 'waermepumpe')::INT) AS mit_waermepumpe
    FROM paare GROUP BY 1
)
SELECT p.egid, p.dist_m, p.anlage_id, a.gebaeude_im_umkreis
FROM paare p JOIN je_anlage a USING (anlage_id)
WHERE p.ist_fossil AND p.ist_wohngebaeude AND p.ist_gebaut AND p.belegt_anlage
  AND a.mit_waermepumpe = 0
QUALIFY row_number() OVER (PARTITION BY p.egid ORDER BY p.dist_m) = 1;

-- Das Ergebnis nach dem Merkmal, das auch in Zuerich bekannt ist: der Zahl der Gebaeude
-- im Umkreis der Anlage.
CREATE OR REPLACE VIEW v_zg_umkreis_wirkung AS
SELECT CASE WHEN u.gebaeude_im_umkreis = 1 THEN '1 Gebäude im Umkreis'
            WHEN u.gebaeude_im_umkreis = 2 THEN '2 Gebäude im Umkreis'
            ELSE                                '3 und mehr' END      AS eindeutigkeit,
       CASE WHEN u.dist_m <= 10 THEN 'bis 10 m' ELSE '10 bis 20 m' END AS distanz,
       count(*)                                                        AS n,
       sum(l.eintrag_falsch::INT)                                      AS falsch,
       round(100.0 * avg(l.eintrag_falsch::INT), 1)                    AS praezision
FROM v_zg_umkreis u
JOIN v_zg_label_klar l USING (egid)
GROUP BY 1, 2;

-- ------------------------------------------------------------- Woraus die Liste besteht
-- Zusammensetzung der Verdachtsliste je Kanton nach Belegart.
CREATE OR REPLACE VIEW v_listenaufbau AS
SELECT v.kanton, b.belegart,
       count(*)                                                  AS faelle,
       count(*) FILTER (WHERE v.konfidenz = 'reihenfolge belegt') AS stark,
       count(DISTINCT v.bfs_nr)                                  AS gemeinden
FROM v_gold_verdacht v
JOIN v_belegart b USING (egid)
WHERE v.konfidenz IN ('reihenfolge belegt', 'reihenfolge plausibel', 'eintrag alt', 'eintrag jung')
GROUP BY 1, 2;

-- ------------------------------------------------------------ Die Liste selbst
-- Misst die Stufen der Verdachtsliste, je Konfidenzstufe und ohne Rangschnitt nach
-- Punktzahl.
CREATE OR REPLACE VIEW v_verdachtsliste_wirkung AS
WITH grundrate AS (
    SELECT label_kanton, avg(eintrag_falsch::INT) AS basis FROM v_label_alle GROUP BY 1
)
SELECT l.label_kanton                                        AS kanton,
       s.konfidenz,
       count(*)                                              AS n,
       sum(l.eintrag_falsch::INT)                            AS falsch,
       round(100.0 * avg(l.eintrag_falsch::INT), 1)          AS praezision,
       round(100.0 * any_value(g.basis), 1)                  AS grundrate,
       round(avg(l.eintrag_falsch::INT) / any_value(g.basis), 1) AS faktor
FROM v_gold_score s
JOIN v_label_alle l USING (egid)
JOIN grundrate g ON g.label_kanton = l.label_kanton
-- v_gold_score statt v_gold_liste: Die Listensicht filtert mit dem Genfer
-- Kesselkataster, aus dem die Genfer Labels stammen, die Messung waere zirkulaer. Die
-- Konfidenzstufen sind in beiden Sichten dieselben.
WHERE s.konfidenz IN ('reihenfolge belegt', 'reihenfolge plausibel', 'eintrag alt', 'eintrag jung')
GROUP BY 1, 2;
