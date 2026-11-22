-- Silver-Layer: das LLM-Urteil zu den Baugesuchstexten.
--
-- Die Stichwortregel in silver_baugesuche.sql findet Heizungsereignisse zuverlaessig
-- (Recall 98,8 %), erzeugt aber Fehltreffer (Precision 91,1 %): bestehende Anlagen,
-- Waermepumpe ersetzt Waermepumpe, Pool-Waermepumpen. Das LLM prueft diese Treffer nach
-- und hebt die Precision auf 98,7 % (reports/extraktion_evaluation.md).
--
-- Die Regel laeuft ueber alle 22'780 Texte, das LLM sieht nur die Treffer, die als
-- Beleg in Frage kommen.
--
-- Fehlt die Datei, bleibt die Tabelle leer und alles Nachgelagerte faellt auf die
-- reine Regel zurueck.

CREATE OR REPLACE TABLE silver_llm_urteil AS
WITH roh AS (
    SELECT * FROM read_json_auto('data/processed/llm_extraktion.jsonl',
                                 format = 'newline_delimited', ignore_errors = true)
)
SELECT
    text                                                        AS beschrieb,
    TRY_CAST(llm ->> '$.betrifft_heizung'    AS BOOLEAN)        AS llm_betrifft_heizung,
    TRY_CAST(llm ->> '$.ist_traegerwechsel'  AS BOOLEAN)        AS llm_traegerwechsel,
    nullif(llm ->> '$.neuer_traeger',  'unbekannt')             AS llm_neuer_traeger,
    nullif(llm ->> '$.alter_traeger',  'unbekannt')             AS llm_alter_traeger,
    TRY_CAST(llm ->> '$.ist_neubau'          AS BOOLEAN)        AS llm_neubau,
    TRY_CAST(llm ->> '$.heizung_ist_hauptzweck' AS BOOLEAN)     AS llm_hauptzweck,
    llm ->> '$.begruendung'                                     AS llm_begruendung,
    (llm ->> '$.fehler') IS NOT NULL                            AS llm_fehler
FROM roh
WHERE text IS NOT NULL;

-- Kaskade: Regel als Vorfilter, LLM als Pruefer. Wo kein LLM-Urteil vorliegt (Datei
-- fehlt, Modellfehler), gilt die Regel allein.
CREATE OR REPLACE VIEW v_baugesuch_geprueft AS
SELECT b.*,
       u.llm_betrifft_heizung, u.llm_traegerwechsel, u.llm_neuer_traeger,
       u.llm_alter_traeger, u.llm_begruendung,
       (u.beschrieb IS NOT NULL AND NOT u.llm_fehler)           AS llm_geprueft,
       -- Das massgebliche Urteil: beide muessen zustimmen, wenn das LLM gelaufen ist
       CASE
           WHEN u.beschrieb IS NULL OR u.llm_fehler THEN b.ist_heizungsereignis
           ELSE b.ist_heizungsereignis AND COALESCE(u.llm_traegerwechsel, FALSE)
       END                                                      AS ist_traegerwechsel,
       -- Der Traeger kommt bevorzugt vom LLM, weil es den Satzbau versteht
       COALESCE(
           CASE WHEN u.llm_neuer_traeger IN
                     ('waermepumpe','fernwaerme','holz','solarthermie','gas','oel','elektro')
                THEN u.llm_neuer_traeger END,
           nullif(b.neuer_traeger, 'unklar')
       )                                                        AS traeger_final,
       COALESCE(u.llm_alter_traeger, b.alter_traeger_genannt)   AS alter_traeger_final
FROM silver_baugesuche b
LEFT JOIN silver_llm_urteil u ON u.beschrieb = b.beschrieb;
