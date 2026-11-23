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

**Stichprobe.** Geschichtet gezogen: 90 Texte, die die Regel als Heizungsereignis erkennt,
40 nicht erkannte mit heizungsnahen Wörtern, 20 rein zufällige. Precision lässt sich direkt
ablesen, für den Recall wird auf die Grundgesamtheit zurückgewichtet. Grundgesamtheit sind
die 17'654 Vorhaben mit Projektbeschrieb (Datenstand 11.09.2026), nicht die 22'780
Publikationen: Mehrfachpublikationen desselben Vorhabens zählen einmal.

**Herkunft der Labels.** Am 13.09.2026 einzeln vergeben, jeweils nach dem ganzen Text,
durch ein Sprachmodell (Claude Opus 5, Feld `gelabelt_von`). Eine Zweitprüfung durch eine
Person gibt es nicht. Für die Zahlen in
[reports/extraktion_evaluation.md](../../reports/extraktion_evaluation.md) heisst das:
Gemessen wird gegen das Urteil eines Sprachmodells, nicht gegen ein von Menschen geprüftes
Label.

**Keine unabhängige Teststichprobe.** Der Systemprompt in `src/extract_llm.py` nennt als
Sonderfälle die Fehlermuster, die in genau diesen Texten gefunden sind. Die Kennzahlen der
Sprachmodell-Prüfung sind deshalb auf den Texten gemessen, an denen der Prompt entwickelt
ist, und für neue Texte zu günstig.
