# Gold-Set für die Textextraktion

150 Baugesuchstexte mit Labels, an denen die Stichwortregel und die LLM-Extraktion gemessen
werden (`src/eval_extraktion.py`, `src/extract_llm.py --gold`, `tests/test_baugesuche_regel.py`).

| Datei | Inhalt |
|---|---|
| `label_stichprobe.json` | Die Stichprobe: Projektbeschrieb, Schicht (`gruppe`) und das Urteil der Stichwortregel zum Zeitpunkt der Ziehung (`regel_*`). |
| `gold_labels.json` | Je Text die Labels `heizung`, `wechsel`, `neu`, `alt`, `neubau`; das Schema steht in der Datei. |

**Herkunft der Texte.** Datensatz "Baugesuche im Kanton Zürich" des Statistischen Amts des
Kantons Zürich, offene Behördendaten. Der Herausgeber hat die
Personendaten entfernt. Die Texte nennen zum Teil die Lage des Vorhabens (Strasse,
Kataster- oder Versicherungsnummer), so wie sie amtlich publiziert wurde.

**Stichprobe.** Geschichtet gezogen: 90 Texte, die die Regel als Heizungsereignis erkannte,
40 nicht erkannte mit heizungsnahen Wörtern, 20 rein zufällige. Precision lässt sich direkt
ablesen, für den Recall wird auf die Grundgesamtheit zurückgewichtet.

**Herkunft der Labels.** Am 13.09.2026 einzeln vergeben, nach Durchsicht des ganzen Texts,
durch ein Sprachmodell (Claude Opus 5, Feld `gelabelt_von`). Eine Zweitprüfung durch eine
weitere Person ist nicht dokumentiert. Wer die Zahlen in
[reports/extraktion_evaluation.md](../../reports/extraktion_evaluation.md) weiterverwendet,
sollte das wissen: Gemessen wird gegen ein sorgfältiges, aber nicht doppelt geprüftes Urteil.
