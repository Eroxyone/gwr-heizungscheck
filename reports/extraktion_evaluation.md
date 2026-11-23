# Texterkennung in Baugesuchen: Evaluation an 150 gelabelten Texten

Stand: Baugesuche des Kantons Zürich bis 11.09.2026, Labels vom 13.09.2026. Gemessen wird,
wie zuverlässig die Stichwortregel (`sql/silver_baugesuche.sql`) Heizungsereignisse in
Baugesuchstexten erkennt und was eine nachgeschaltete Prüfung durch ein Sprachmodell
(`src/extract_llm.py`) daran ändert.

## Vorgehen

150 Baugesuchstexte sind einzeln gelabelt (Volltext, nicht nur der Anfang). Die Labels
stammen von einem Sprachmodell (Feld `gelabelt_von` in `data/labels/gold_labels.json`:
"Sprachmodell (Claude Opus 5), jeder Text einzeln im Volltext beurteilt; keine Zweitprüfung durch eine Person").
Die Stichprobe ist geschichtet gezogen, damit sowohl Fehltreffer als auch übersehene
Fälle sichtbar werden:

| Schicht                            |   gezogen |   Vorhaben in der Grundgesamtheit |   Gewicht |
|:-----------------------------------|----------:|----------------------------------:|----------:|
| von der Regel erkannt              |        90 |                              1427 |      15,9 |
| nicht erkannt, heizungsnahe Wörter |        40 |                              2670 |      66,8 |
| nicht erkannt, Zufallsauswahl      |        20 |                             13557 |     677,9 |

Die Schichten zählen Vorhaben mit Projektbeschrieb und summieren deshalb auf 17'654, nicht
auf die 22'780 Publikationen des Datensatzes: Mehrfachpublikationen desselben Vorhabens
sind zusammengefasst (17'680 Vorhaben), und 26 Vorhaben ohne Projektbeschrieb
fallen in keine Schicht.

Weil die Schichten unterschiedlich stark gezogen sind, wird der Recall auf die
Grundgesamtheit hochgerechnet. Die Precision lässt sich direkt ablesen.

Gelabelt sind fünf Felder: ob es um einen Wärmeerzeuger geht, ob daraus ein
Trägerwechsel folgt (also etwas, das im GWR nachgeführt werden müsste), der neue und der
bisherige Energieträger, und ob es ein Neubau ist.

## Ergebnis der Stichwortregel

| Aufgabe                                                       |   TP |   FP |   FN |   Precision |   Recall |    F1 |
|:--------------------------------------------------------------|-----:|-----:|-----:|------------:|---------:|------:|
| Heizungsereignis erkennen (ungewichtet)                       |   86 |    4 |    2 |        95,6 |     97,7 |  96,6 |
| Heizungsereignis erkennen (auf Grundgesamtheit hochgerechnet) | 1364 |   63 |  134 |        95,6 |     91,1 |  93,3 |
| Trägerwechsel erkennen (ungewichtet)                          |   82 |    8 |    1 |        91,1 |     98,8 |  94,8 |
| neuen Energieträger benennen (76 Fälle mit Träger im Text)    |   76 |    0 |    0 |       100,0 |     –    |  –    |
| bisherigen Energieträger benennen (16 Fälle im Gold-Set)      |   13 |    0 |    3 |        –    |     81,2 |  –    |

## Die 10 Fehler der Stichwortregel im Einzelnen

|   Nr. | Fehlertyp                              | Projektbeschrieb                                                                                                    |
|------:|:---------------------------------------|:--------------------------------------------------------------------------------------------------------------------|
|    18 | kein Trägerwechsel, trotzdem gezählt   | Einbau Wohnung im Obergeschoss/Dachgeschoss der Scheune, zusätzliche Fassadenfenster und zwei Dachflächenfenster, D |
|    25 | falsch positiv (kein Heizungsereignis) | Standort: Zürich  Das Projekt besteht aus der Verlegung von Betonschutzplatten über der Erdgasleitung der Strecke 1 |
|    38 | kein Trägerwechsel, trotzdem gezählt   | Installation einer Luft-Wasser Wärmepumpe als Ersatz der beiden bestehenden Wärmepumpen                             |
|    46 | falsch positiv (kein Heizungsereignis) | Neubau einer Poolanlage mit Wärmepumpe und eines Plattenbelags, Bepflanzung und Terrainanpassung                    |
|    49 | falsch positiv (kein Heizungsereignis) | Erstellung einer unterirdischen Energiezentrale neben der Abwasserreinigungsanlage (ohne Aussteckung)               |
|    58 | falsch positiv (kein Heizungsereignis) | Pool mit Wärmepumpe und Sichtschutzwände                                                                            |
|    60 | kein Trägerwechsel, trotzdem gezählt   | Umbau Energiezentrale, 5 Rückkühler auf Dach (im Inventar Denkmalpflege)                                            |
|    62 | kein Trägerwechsel, trotzdem gezählt   | BG Nr. 2025-0325: Instandsetzung der Dächer auf allen 5 Parkschulcampus KUS und Ersatz der Luft-Wasser-Wärmepumpen  |
|   104 | übersehen                              | Erstellung eines Blockheizkraftwerks mit Trocknungsbunker und überdachtem Umschlagsplatz                            |
|   126 | übersehen                              | Neubau Wärmespeicher                                                                                                |

## Was daraus folgt

Die Stichwortsuche findet Heizungsereignisse zuverlässig. Sie unterscheidet aber nicht,
ob eine Heizung **neu gebaut** oder nur **erwähnt** wird. Drei Fehlermuster kann eine
Stichwortregel nicht lösen:

1. **Bestehende Anlagen.** "Bestehende Pelletsheizung im Hauptgebäude" beschreibt den
   Ist-Zustand, kein Vorhaben.
2. **Wärmepumpe ersetzt Wärmepumpe.** "Ersatz der beiden bestehenden Wärmepumpen" ist ein
   Heizungsereignis, aber der GWR-Eintrag bleibt derselbe.
3. **Wärmepumpen ohne Gebäudebezug.** Pool-Wärmepumpen, Klimageräte, Rückkühler und
   Erdgasleitungen im Boden lösen dieselben Stichwörter aus.

## Prüfung durch ein Sprachmodell

Dieselben 150 Texte, durch `src/extract_llm.py` mit einem lokalen `qwen2.5:7b`. Gemessen
ist die Aufgabe "Trägerwechsel erkennen":

| Verfahren                           |   TP |   FP |   FN |   Precision |   Recall |   F1 |
|:------------------------------------|-----:|-----:|-----:|------------:|---------:|-----:|
| nur Stichwortregel                  |   82 |    8 |    1 |        91,1 |     98,8 | 94,8 |
| nur LLM (`qwen2.5:7b`, lokal)       |   78 |    2 |    5 |        97,5 |     94,0 | 95,7 |
| Regel als Vorfilter, LLM als Prüfer |   78 |    1 |    5 |        98,7 |     94,0 | 96,3 |
| Regel oder LLM                      |   82 |    9 |    1 |        90,1 |     98,8 | 94,3 |

**Das Sprachmodell sortiert 7 der 8 Fehltreffer der Regel aus**, und zwar
Fälle aus den drei Mustern oben. Dafür übersieht es 5 Trägerwechsel, die Regel 1.

Zwei dieser Auslassungen sind Modellfehler, bei denen sich die Ausgabe selbst
widerspricht. Bei "Erstellung von 18 Erdwärmesonden" schreibt das Modell als Begründung
"Erdwärmesonden bedeuten eine Wärmepumpe" und setzt das Merkmal trotzdem auf falsch. Ob ein
grösseres Modell das vermeidet, ist nicht gemessen.

**In dieser Messung hat die Kaskade die höchste Precision.** Regel als Vorfilter,
Sprachmodell als Prüfer: Die Precision steigt von 91,1 % auf 98,7 %
(78 von 79 positiven Urteilen richtig, 1 falsch;
Wilson-Intervall zu 95 %: 93,2 bis 99,8 %), bei gleichem Recall wie das
Sprachmodell allein. Der Wert gilt nur mit den Vorbehalten im Abschnitt "Grenzen dieser
Messung". Die Anordnung spart Rechenaufwand: Die Regel läuft über alle 22'780
Publikationen, das Sprachmodell prüft nur die 1'753 Treffer der Regel.

**Für eine Verdachtsliste zählt Precision mehr als Recall.** Ein Fehltreffer erzeugt
Prüfaufwand ohne Ergebnis, ein übersehener Fall fehlt nur.

## Grenzen dieser Messung

1. **Keine unabhängige Teststichprobe.** Der Systemprompt des Sprachmodells
   (`src/extract_llm.py`) nennt als Sonderfälle genau die Fehlermuster, die in diesem
   Gold-Set gefunden sind: bestehende Pelletsheizung, Wärmepumpe ersetzt Wärmepumpe,
   Pool, Rückkühler, Gasleitung im Boden. Die Precision der Kaskade ist damit auf
   denselben Texten gemessen, an denen der Prompt entwickelt ist. Auf neuen Texten ist
   ein tieferer Wert zu erwarten; wie viel tiefer, ist nicht gemessen.
2. **Kleine Fallzahl.** Die Precision der Kaskade beruht auf n = 79 positiven Urteilen (78 richtig, 1 falsch). Ein einzelner weiterer Fehltreffer senkt sie um 1,3 Prozentpunkte.
3. **Labels von einem Sprachmodell.** Die Labels stammen aus einer einzelnen Durchsicht
   durch ein Sprachmodell, ohne Zweitprüfung durch eine Person. Grenzfälle
   (Blockheizkraftwerk, Wärmespeicher, Energiezentrale einer Kläranlage) sind
   konservativ als "kein Gebäude-Wärmeerzeuger" gewertet.
4. **Der hochgerechnete Recall ist unsicher.** Übersehene Heizungsereignisse: 2 in der Schicht "nicht erkannt, heizungsnahe Wörter" (Gewicht 66,8).
   In der Zufallsschicht (20 Texte, Gewicht 677,9) liegt kein Heizungsereignis;
   ein einziger übersehener Fall dort würde den hochgerechneten Recall deutlich senken.

Eine belastbare Messung braucht eine frische Stichprobe, die erst nach dem Festlegen von
Regel und Prompt gezogen wird, Labels von einer Person (besser von zwei unabhängig, damit
sich die Übereinstimmung messen lässt) und ein Vertrauensintervall zur Precision.
