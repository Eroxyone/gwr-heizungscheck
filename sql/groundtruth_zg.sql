-- Zug als zweiter Label-Datensatz, zum Pruefen der Uebertragbarkeit.
--
-- Genf allein traegt keine Verallgemeinerung: tiefe Waermepumpendichte, und die meisten
-- Registereintraege stammen aus kantonalen Daten. Zug liefert einen zweiten Satz aus
-- einer anderen Quelle, dem Tankkataster ("in Betrieb" / "ausser Betrieb"). Er ist
-- schwaecher als der Genfer:
--
-- 1. Nur Oel. Ein Heizoeltank sagt nichts ueber eine Gasheizung. Gas-Eintraege sind
--    deshalb ausgeschlossen und nicht als "ungeklaert" gefuehrt.
-- 2. Keine EGID. Die Zuordnung laeuft ueber einen 10-m-Umkreis und bleibt eine
--    Naeherung.
-- 3. Kein Ersatznachweis. Der Kataster sagt nur, ob der Tank laeuft. "Tank stillgelegt"
--    heisst "wahrscheinlich veraltet", nicht "Waermepumpe eingebaut".

CREATE OR REPLACE VIEW v_zg_label AS
SELECT g.egid, g.bfs_nr, g.gemeinde, g.baujahr, g.gkat, g.energie_klasse,
       g.quelle_code, g.quelle_txt, g.quelle_datum, g.alter_jahre,
       t.tanks, t.oeltank_in_betrieb, t.oeltank_ausser_betrieb, t.naechster_tank_m,
       CASE
           WHEN t.egid IS NULL              THEN 'ungeklaert'
           WHEN t.oeltank_in_betrieb        THEN 'stimmt'
           WHEN t.oeltank_ausser_betrieb    THEN 'veraltet_stillgelegt'
           ELSE                                  'ungeklaert'
       END AS label
FROM silver_gebaeude_ch g
LEFT JOIN v_tank_zg t USING (egid)
-- Nur Oel, siehe Punkt 1 oben.
WHERE g.kanton = 'ZG' AND g.ist_wohngebaeude AND g.energie_klasse = 'oel';

CREATE OR REPLACE VIEW v_zg_label_klar AS
SELECT *, label <> 'stimmt' AS eintrag_falsch,
       'raeumlicher_tankproxy' AS label_sicherheit
FROM v_zg_label
WHERE label <> 'ungeklaert';
