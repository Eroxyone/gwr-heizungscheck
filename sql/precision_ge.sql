-- Achtung: Diese Auswertung ist zirkulaer und taugt nicht als Kennzahl. Sie misst auf
-- v_gold_verdacht, und diese Sicht hat Faelle mit aktivem fossilem Kessel bereits
-- entfernt, mit demselben Genfer Kataster, gegen den hier gemessen wird. Die Datei
-- dokumentiert nur den Gegenbeleg-Mechanismus. Die massgebliche Messung steht in
-- reports/belegwirkung.md und laeuft auf v_gold_score.
--
-- Ausgaenge:
--   widerlegt   aktiver fossiler Heizkessel vorhanden, der GWR-Eintrag stimmt wohl
--   bestaetigt  fossiler Kessel stillgelegt oder aktive erneuerbare Anlage
--   hybrid      fossiler Kessel nur noch als Reserve, keine Aussage
--   unbekannt   das Gebaeude steht nicht im Kataster
--   ungeklaert  im Kataster, aber weder Stilllegung noch aktive erneuerbare Anlage
--               (oft nur Warmwasseranlagen), belegt nichts
CREATE OR REPLACE VIEW v_precision_ge AS
SELECT v.egid, v.bfs_nr, v.gemeinde, v.konfidenz, v.score,
       v.hat_baugesuch, v.hat_sonde, v.hat_pv, v.hat_widerspruch,
       f.fossil_aktiv, f.fossil_reserve, f.fossil_stillgelegt, f.juengster_fossiler_kessel,
       CASE
           WHEN f.egid IS NULL                                THEN 'unbekannt'
           WHEN f.fossil_aktiv                                THEN 'widerlegt'
           WHEN f.fossil_reserve AND NOT f.fossil_stillgelegt THEN 'hybrid'
           WHEN f.fossil_stillgelegt                          THEN 'bestaetigt'
           WHEN f.erneuerbar_aktiv                            THEN 'bestaetigt'
           ELSE                                                    'ungeklaert'
       END AS befund
FROM v_gold_verdacht v
LEFT JOIN v_feuerung_ge f USING (egid)
WHERE v.kanton = 'GE';
