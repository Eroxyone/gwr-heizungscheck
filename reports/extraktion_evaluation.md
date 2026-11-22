# Wie gut ist die Stichwortsuche? Evaluation an einem Gold-Set

Die Erkennung von Heizungsereignissen in Baugesuchstexten läuft bisher über Stichwörter
und Regeln (`sql/silver_baugesuche.sql`). Diese Auswertung misst, wie gut das ist, und
schätzt damit ab, was eine LLM-Extraktion zusätzlich bringen würde.

## Vorgehen

150 Baugesuchstexte wurden einzeln gelabelt (Volltext gelesen, nicht nur der Anfang). Die Labels
stammen aus einer Durchsicht durch ein Sprachmodell (Claude Opus 5, siehe `gelabelt_von` in
`data/labels/gold_labels.json`); eine Zweitprüfung durch eine weitere Person ist nicht
dokumentiert.
Die Stichprobe ist geschichtet gezogen, damit sowohl Fehltreffer als auch übersehene
Fälle sichtbar werden:

| Schicht     |   gezogen |   in Grundgesamtheit |   Gewicht |
|:------------|----------:|---------------------:|----------:|
| erkannt     |        90 |                 1427 |      15,9 |
| verdaechtig |        40 |                 2670 |      66,8 |
| zufall      |        20 |                13557 |     677,9 |

Weil die Schichten unterschiedlich stark gezogen wurden, muss der Recall auf die
Grundgesamtheit hochgerechnet werden. Die Precision lässt sich direkt ablesen.

Gelabelt wurden fünf Felder: ob es überhaupt um einen Wärmeerzeuger geht, ob daraus ein
Trägerwechsel folgt (also etwas, das im GWR nachgeführt werden müsste), der neue und der
bisherige Energieträger, und ob es ein Neubau ist.

## Ergebnis

| Aufgabe                                                       |   TP |   FP |   FN |   Precision |   Recall |    F1 |
|:--------------------------------------------------------------|-----:|-----:|-----:|------------:|---------:|------:|
| Heizungsereignis erkennen (ungewichtet)                       |   86 |    4 |    2 |        95,6 |     97,7 |  96,6 |
| Heizungsereignis erkennen (auf Grundgesamtheit hochgerechnet) | 1364 |   63 |  134 |        95,6 |     91,1 |  93,3 |
| Traegerwechsel erkennen (ungewichtet)                         |   82 |    8 |    1 |        91,1 |     98,8 |  94,8 |
| neuen Energieträger benennen (76 Fälle mit Träger im Text)    |   76 |    0 |    0 |       100,0 |     –    |  –    |
| bisherigen Energieträger benennen (16 Fälle im Gold-Set)      |   13 |    0 |    3 |        –    |     81,2 |  –    |

## Die 10 Fehler im Einzelnen

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

Die Stichwortsuche findet Heizungsereignisse zuverlässig. Ihre Schwäche liegt woanders:
Sie kann nicht unterscheiden, ob eine Heizung **neu gebaut** oder nur **erwähnt** wird.

Drei Fehlermuster, die eine Regel prinzipiell nicht löst:

1. **Bestehende Anlagen.** "Bestehende Pelletsheizung im Hauptgebäude" beschreibt den
   Ist-Zustand, kein Vorhaben.
2. **Wärmepumpe ersetzt Wärmepumpe.** "Ersatz der beiden bestehenden Wärmepumpen" ist ein
   Heizungsereignis, aber der GWR-Eintrag bleibt derselbe.
3. **Wärmepumpen ohne Gebäudebezug.** Pool-Wärmepumpen, Klimageräte, Rückkühler und
   Erdgasleitungen im Boden lösen dieselben Stichwörter aus.

## Gemessen: was die LLM-Extraktion wirklich bringt

Dieselben 150 Texte, durch `src/extract_llm.py` mit einem lokalen qwen2.5:7b:

| Verfahren                           |   TP |   FP |   FN |   Precision |   Recall |   F1 |
|:------------------------------------|-----:|-----:|-----:|------------:|---------:|-----:|
| nur Stichwortregel                  |   82 |    8 |    1 |        91,1 |     98,8 | 94,8 |
| nur LLM (`qwen2.5:7b`, lokal)       |   78 |    2 |    5 |        97,5 |     94,0 | 95,7 |
| Regel als Vorfilter, LLM als Prüfer |   78 |    1 |    5 |        98,7 |     94,0 | 96,3 |
| Regel oder LLM                      |   82 |    9 |    1 |        90,1 |     98,8 | 94,3 |

**Das LLM sortierte sieben der acht Fehltreffer der Regel korrekt aus** - genau die drei Muster
oben. Dafür übersieht es mehr: fünf Trägerwechsel, die die Regel gefunden hätte.

Zwei dieser Auslassungen sind echte Modellfehler, bei denen sich die Ausgabe selbst
widerspricht. Bei "Erstellung von 18 Erdwärmesonden" schreibt das Modell als Begründung
"Erdwärmesonden bedeuten eine Wärmepumpe" und setzt das Flag trotzdem auf falsch. Das ist
typisch für ein 7B-Modell; ein grösseres würde das vermutlich vermeiden.

**Die Kaskade schlägt beide Einzelverfahren.** Die Regel als Vorfilter, das LLM als Prüfer:
Precision steigt von 91,1 % auf 98,7 %, bei gleichem Recall wie das LLM allein. Das ist auch
betrieblich die richtige Anordnung - die Regel läuft ohne Aufwand über alle 22'780 Texte, das LLM
muss dann nur noch die rund 1'750 Treffer prüfen. Das ist ein dreizehnmal kleinerer
Rechenaufwand als eine LLM-Extraktion über den ganzen Bestand.

**Für die Anwendung zählt Precision mehr als Recall.** Ein Fehltreffer in einer
Verdachtsliste kostet Vertrauen bei der Gemeinde, die ihn prüft. Ein übersehener Fall
kostet nur einen entgangenen Treffer.

## Grenzen dieser Evaluation

- Die Labels stammen aus einer einzelnen Durchsicht, nicht aus einem Mehrfachurteil.
  Grenzfälle (Blockheizkraftwerk, Wärmespeicher, Energiezentrale einer Kläranlage) wurden
  konservativ als "kein Gebäude-Wärmeerzeuger" gewertet.
- 150 Texte reichen für Precision, aber der hochgerechnete Recall hat eine grosse
  Unsicherheit: In der Zufallsschicht liegt ein einziger Grenzfall, und dieser eine Fall
  wird mit einem Gewicht von mehreren Hundert multipliziert.
- Bei einer Weiterführung sollte das Gold-Set auf rund 500 Texte wachsen und von zwei Personen
  unabhängig gelabelt werden, damit sich die Übereinstimmung messen lässt.
