-- Test 3: Werden Heizungs-Baugesuche im GWR schon nachgefuehrt?
-- Betrachtet werden Heizungs-Baugesuche, deren Publikation mindestens 6 Monate zurueckliegt.
--
-- Grundlage ist v_baugesuch_geprueft, also die Kaskade aus Stichwortregel und
-- LLM-Pruefung (silver_llm.sql). Liegt kein LLM-Urteil vor, gilt die Regel allein.

CREATE OR REPLACE VIEW v_test3_basis AS
SELECT
    b.bg_id, b.vorhaben_id, b.pub_datum, b.beschrieb,
    -- Die Publikationsnummer ist das, was ein Bauamt in seinem eigenen System sucht.
    b.publikationsnr, b.kataster_nr,
    b.traeger_final AS neuer_traeger, b.alter_traeger_final AS alter_traeger_genannt,
    b.llm_geprueft, b.llm_begruendung,
    b.kw_neubau, b.kw_ersatz,
    (b.kw_neubau AND NOT b.kw_ersatz)                     AS ist_reiner_neubau,
    m.egid, m.via_geo, m.via_adresse,
    s.n_gebaeude,
    g.bfs_nr, g.gemeinde, g.energie_klasse, g.energietraeger_txt,
    g.quelle_code, g.quelle_txt, g.quelle_datum, g.baujahr, g.gebaeudekategorie_txt,
    -- traegt das GWR den im Baugesuch genannten neuen Traeger?
    (b.traeger_final IS NOT NULL
       AND b.traeger_final <> 'unklar'
       AND g.energie_klasse = b.traeger_final)            AS traeger_passt,
    -- wurde die Heizungsangabe nach dem Baugesuch ueberhaupt angefasst?
    (g.quelle_datum IS NOT NULL AND g.quelle_datum >= b.pub_datum) AS datum_nach_gesuch,
    (g.quelle_code = '869')                               AS quelle_baubewilligung
FROM v_baugesuch_geprueft b
JOIN match_all  m USING (bg_id)
JOIN match_stats s USING (bg_id)
JOIN silver_gebaeude g ON g.egid = m.egid
WHERE b.ist_traegerwechsel
  AND b.pub_datum <= (SELECT max(pub_datum) FROM silver_baugesuche) - INTERVAL 6 MONTH;

CREATE OR REPLACE VIEW v_test3 AS
SELECT * EXCLUDE (rang) FROM (
SELECT *,
    row_number() OVER (PARTITION BY egid, vorhaben_id ORDER BY pub_datum) AS rang,
    CASE
        WHEN traeger_passt AND datum_nach_gesuch                     THEN 'nachgefuehrt'
        WHEN traeger_passt                                           THEN 'traeger_passt_datum_alt'
        WHEN datum_nach_gesuch AND quelle_baubewilligung             THEN 'quelle_869_nach_gesuch'
        WHEN datum_nach_gesuch                                       THEN 'datum_neu_traeger_anders'
        WHEN neuer_traeger = 'unklar' OR energie_klasse = 'ohne_angabe'
             OR energie_klasse = 'unbestimmt'                        THEN 'unklar'
        ELSE 'nicht_nachgefuehrt'
    END AS status
FROM v_test3_basis) WHERE rang = 1;
