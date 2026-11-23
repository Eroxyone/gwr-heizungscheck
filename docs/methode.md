# Methode

Wie aus den Quellen ein Verdacht wird, was gemessen ist und was nicht. Zahlen mit
Registerstand 14.09.2026, wo nichts anderes steht. Die Kurzfassung steht in der
[Übersicht](../README.md), die Herkunft der Daten in [datenquellen.md](datenquellen.md).

## Warum Snapshots

Ein einzelner GWR-Stand zeigt nur, wie das Register heute aussieht. Die interessantere Grösse
ist die Bewegung: Wie viele Heizungseinträge ändert ein Kanton tatsächlich pro Monat? Das
lässt sich nicht nachträglich beschaffen.

Deshalb legt `ingest.py` bei jedem Lauf ein Parquet je Kanton ab, hive-partitioniert:

```
data/snapshots/gwr/snapshot_date=2026-09-13/kanton=ZH/data.parquet
```

Rund 60 MB für die ganze Schweiz pro Stand, dank ZSTD-Kompression. DuckDB liest den ganzen
Baum mit `read_parquet('data/snapshots/gwr/**/*.parquet', hive_partitioning = true)`.
Sobald zwei Stände vorliegen, liefert die View `v_gold_veraenderung` die Änderungsrate je
Kanton und Zeitraum.

Den wöchentlichen Abzug zieht `scripts/snapshot.ps1`, im Projekt jeden Montag um 06:30 über
den Windows-Taskplaner gestartet.

## Was die Zeitreihe nach neun Wochen gezeigt hat

Der Gold-Layer wird aus dem jüngsten Snapshot gerechnet; ein Fall verlässt die Liste, sobald
das Register ihn nicht mehr fossil führt. Damit die Spur nicht verloren geht, hält
`gold_liste_archiv` je Registerstand fest, was auf der Liste stand, und
`v_gold_liste_korrigiert` zeigt je archiviertem Fall den ersten späteren Snapshot, in dem der
Eintrag nicht mehr fossil ist, mit neuem Träger und neuer Quelle. Gemessen wird damit an
Korrekturen, die Gemeinden und Kantone von sich aus vornehmen.

Zwischen dem 14.09. und dem 16.11.2026 hat der Kanton Zürich 2'720 Wohngebäude von fossil auf
nicht fossil umgestellt, 1'901 davon mit Quelle 864 (kantonale Daten) und 2'201 auf
Erdwärmesonde, gemeindeweise in Blöcken. Das ist das in ZUP 109 beschriebene Verfahren im
Vollzug: rund 3'000 Trägeränderungen pro Woche bis Mitte Oktober, dann Ruhe, dann ein weiterer
Block von 4'284 in der Woche bis 09.11. Von den 2'720 standen 650 auf der Liste vom 14.09.
(24 %), und bei 645 traf der Korrekturvorschlag den neuen Eintrag. Die übrigen drei Viertel
erreicht die Liste nicht, weil der Kanton die Sonden mit Datum und Gebäudebezug kennt und die
offenen Daten nur Koordinate und Laufnummer hergeben.

Zürich ist nicht allein. Der Aargau bewegt im November 4'398 und 5'148 Einträge pro Woche,
Basel-Landschaft 2'329 in der Woche bis 26.10. Dort geht es nur zum kleineren Teil um fossile
Einträge: Im Aargau werden vor allem unbestimmte Energieträger konkretisiert, mit dem
Versorgungswerk und kantonalen Daten als Quelle. Die übrigen 23 Kantone zusammen bleiben in
jeder Woche unter einem geänderten Eintrag je 1'000 Gebäude
([reports/zeitreihe.md](../reports/zeitreihe.md)).

Praktische Folge: Nach jedem Snapshot `python src/pipeline.py alle` laufen lassen, nicht nur
`ch`. Am 02.10.2026 stand der Gold-Layer noch auf dem 14.09., und 240 der 3'423 Listenfälle
waren im Register bereits erledigt.

## Belege, Stufen und der Verdachtsscore

`gold_verdacht.sql` führt die Tests zusammen. In `gold_belege` steht ein fossil
eingetragenes Wohngebäude nur, wenn es **mindestens einen Beleg** gibt: ein nicht
nachgeführtes Heizungs-Baugesuch, eine Wärmenutzungsanlage, eine Photovoltaikanlage oder
einen Widerspruch im Register selbst. Daraus entstehen zwei Grössen, die Verschiedenes
leisten.

**Die Stufe** (Spalte `konfidenz`) entscheidet, ob ein Fall auf die Liste kommt, und sie
ordnet die Liste. Sie hängt an der Art des Belegs und an der Reihenfolge von Beleg und
Registereintrag, nicht an Punkten:

| Stufe | Bedingung | auf der Liste |
|---|---|---|
| Reihenfolge belegt | Beleg datiert und jünger als der Registereintrag | ja |
| Reihenfolge plausibel | Zürcher Sonde ohne Datum, Laufnummer über der Schwelle des Eintragsjahrs | ja |
| Eintrag alt | Reihenfolge nicht bestimmbar (Beleg oder Eintrag ohne Datum), Eintrag mit Quelle 860 oder älter als 15 Jahre | ja |
| Eintrag jung | Reihenfolge nicht bestimmbar, Eintrag jünger | ja |
| Beleg vor Eintrag | Beleg datiert und älter als der Registereintrag | nein |
| nur Solaranlage, nur Metadaten | kein Beleg zur Heizung (weder Baugesuch noch Anlage noch Erzeuger-Widerspruch) | nein |

**Der Score** ist die Summe der Gewichte unten, begrenzt auf 100. Seine Rolle ist heute
klein:

- Er entscheidet nicht, ob ein Fall auf die Liste kommt. `v_gold_liste` wählt allein nach
  der Stufe aus, nach dem Gegenbeleg-Filter von `v_gold_verdacht`.
- Er bestimmt die Reihenfolge der Liste nicht. `src/pruefliste.py` sortiert nach Stufe,
  dann nach Belegklasse (ausgeführte Anlage in der Nähe, ausgeführte Anlage, Anlage ohne
  Status, Baugesuch). Der Score ist erst das dritte Sortiermerkmal, vor der EGID.
- Sonst erscheint er nur als beschreibende Kennzahl: mittlerer und höchster Score je
  Gemeinde (`gold_verdacht_gemeinde`), mittlerer Score je Beleglage im HTML-Befund
  (`src/export_bericht.py`) und eine Bereichsprüfung in `checks.py`.
- Er schätzt keine Wahrscheinlichkeit, und entlang seiner Rangfolge ist nichts gemessen:
  Er kennt nur wenige Summen, viele Fälle teilen dieselbe Punktzahl
  ([reports/belegwirkung.md](../reports/belegwirkung.md)).

Gewichte im Score (`v_gold_score`):

| Merkmal | Punkte | gemessene Wirkung |
|---|---|---|
| Heizungs-Baugesuch, nicht nachgeführt | 50, mit Textprüfung durch das Sprachmodell 55 | **ungemessen** - in keinem Labelkanton kommt ein Fall vor |
| Wärmenutzungsanlage, eindeutig zugeordnet | 40 | 62 bis 64 % falsche Einträge, Faktor 7 (Zug) |
| Photovoltaikanlage | 18 | 13,7 % (Genf) und 17,2 % (Zug), Faktor 2 bis 2,5 - allein zu wenig |
| Wärmeerzeuger ist Wärmepumpe, Träger ist Heizöl | 15 | ungemessen, aber technisch unmöglich |
| Quelle 860 | 12 | kein Beleg, nur zusammen mit einem Beleg |
| Registereintrag 20 Jahre und älter / 15 bis 19 Jahre / ohne Datum | 15 / 8 / 6 | kein Beleg, nur zusammen mit einem Beleg |
| Warmwasser über Fernwärme oder Wärmepumpe | 0 | Faktor 0,7 bis 0,8, also keine Wirkung |
| Entfernung der Anlage zum Gebäude | keine Abstufung | kein Gradient zwischen den Distanzklassen |
| Baujahr | 0 (konstant) | Faktor 0,94, also keine Wirkung |

Das Baujahr steht als konstante Null im Score (`p_baujahr`) und ändert ihn nie. Beim
Warmwasser-Widerspruch liegt der Grund im Genfer Wärmeerzeuger-Layer: Die
Fernwärme-Übergabestationen dieser Fälle tragen im Feld `USAGE` den Wert `['ECS']`,
versorgen also nur das Warmwasser. Der Beleg "das Warmwasser läuft über Fernwärme" und die
Gegenquelle sagen dann dasselbe, und die Übereinstimmung zweier Register ist kein
Heizungswechsel. Ohne Auswertung von `USAGE` erscheint dieser Beleg fälschlich stark
(Faktor 5,1).

Merkmale ausserhalb des Scores:

| Merkmal | Wirkung | Messung |
|---|---|---|
| Beleg älter als der Registereintrag | Stufe "Beleg vor Eintrag", nicht auf der Liste | 13,3 % statt 80,8 %, gemessen in Zug |
| Laufnummer der Zürcher Sonde über der Jahresschwelle | Stufe "Reihenfolge plausibel" | **ungemessen** - kalibriert an Neubauten, `gold_laufnummer_kalibrierung` |
| Beleg jünger als 18 Monate am Tag des Abzugs | Kennzeichen "im Nachlauf" | Bern: Meldepflicht Heizungsersatz seit 2023, Nachführung bei der Abnahme |

Die GWR-Codes im Korrekturvorschlag kommen aus dem Merkmalskatalog (`bronze_gwr_kodes`)
und sind nicht von Hand eingetragen.

**Quelle 860 und ein altes Datum sind ausdrücklich keine Belege.** Ohne diese Regel kämen
alle Kandidaten auf die Liste, am 14.09.2026 sind das 333'680 Gebäude
([reports/kantonsvergleich.md](../reports/kantonsvergleich.md)), die grosse Mehrheit ohne
jeden Beleg.

Zusammen mit einem Beleg trennt die Reihenfolge von Beleg und Registereintrag am
stärksten. Gemessen an den 109 prüfbaren Zuger Fällen mit Anlagenbeleg (79 mit Listenstufe
und 30 der Stufe "Beleg vor Eintrag"):

| Stufe | gemessen | n | Faktor |
|---|---:|---:|---:|
| Beleg jünger als der Registereintrag | 80,8 % | 78 | 9,2 |
| Beleg älter als der Registereintrag | 13,3 % | 30 | 1,5 |
| *Grundrate im Kanton* | *8,8 %* | *4'430* | *1,0* |

Der 109. Fall trägt die Stufe "Eintrag jung" (undatierter Beleg) und trifft zu.

Die Erklärung: Ein Beleg sagt, dass am Gebäude etwas an der Heizung geschehen ist. Ob das
im Register steht, hängt daran, wann der Eintrag zuletzt bearbeitet wurde. Das Alter des
Eintrags ist ein Stellvertreter für die Reihenfolge und dient nur dort, wo der Beleg kein
Datum trägt (Stufen "Eintrag alt" und "Eintrag jung").

### Die Zuger Fallzahlen

Für Zug stehen in den Dokumenten mehrere Fallzahlen. Sie zählen verschiedene Mengen, alle
zum Registerstand 14.09.2026:

| Zahl | Was sie zählt | Herkunft |
|---:|---|---|
| 144 | Zuger Fälle mit Listenstufe vor dem Gegenbeleg-Filter, Öl- und Gaseinträge | `v_gold_score`; 122 Öl + 22 Gas |
| 129 | Zuger Fälle auf der Liste: die 144 ohne die 15 mit Öltank in Betrieb (Gegenbeleg) | `v_gold_liste`, archiviert in `gold_liste_archiv`; 107 Öl + 22 Gas |
| 122 | die Öleinträge unter den 144; nur über sie sagt der Tankkataster etwas | Tabelle "Wer aus der Messung fällt" in [reports/belegwirkung.md](../reports/belegwirkung.md) |
| 79 | die prüfbaren unter den 122: Der Kataster kennt einen Tank (64 ausser Betrieb, 15 in Betrieb); bei 43 kennt er keinen | Messung der Liste, 64 von 79 = 81,0 % |
| 109 | alle prüfbaren Zuger Fälle mit Anlagenbeleg: die 79 mit Listenstufe und 30 der Stufe "Beleg vor Eintrag", die nicht auf der Liste steht | Messung je Belegart (44 + 65) und je Stufe (78 + 30 + 1) |

"Von 144 Zuger Fällen liessen sich 79 prüfen" und "64 von 79 treffen zu" beziehen sich
also auf dieselbe Menge. Die 129 der Liste und die 79 der Messung überschneiden sich nur
zum Teil: Die 15 Fälle mit Tank in Betrieb sind gemessen (als Fehltreffer), stehen aber
nicht auf der Liste, und die 65 nicht prüfbaren Fälle (43 Öl ohne Tankeintrag, 22 Gas)
stehen auf der Liste, sind aber nicht gemessen. Die Zahl 144 ist aus 122 und 22
hergeleitet und mit dem Archiv abgeglichen (129 + 15); einzeln nachrechnen lässt sie sich
in der Datenbank nicht mehr, weil `v_gold_score` nur den jüngsten Stand führt.

## Was auf die Liste kommt

`v_gold_verdacht` enthält rund 88'000 Fälle, aber über 95 % davon beruhen allein auf
einer Photovoltaikanlage oder auf Metadaten. Bei 13,7 bis 17,2 % Trefferquote ist das für
eine Prüfliste zu wenig. **`v_gold_liste` ist deshalb die engere Sicht: 3'423 Fälle in
526 Gemeinden am 14.09.2026, 2'738 am 16.11.2026.** Zwei Filter machen den Unterschied:
Es braucht einen Beleg, der etwas über die Heizung sagt, und dieser Beleg darf nicht
älter sein als der Registereintrag.

Stand 14.09.2026:

| Kanton | auf der Liste | Reihenfolge belegt (datiert) | Reihenfolge plausibel (Laufnummer) | davon im Nachlauf | Gemeinden |
|---|---:|---:|---:|---:|---:|
| ZH | 2'143 | 138 | 1'355 | 64 | 141 |
| BE | 655 | 651 | - | 91 | 175 |
| SO | 216 | 213 | - | 17 | 70 |
| ZG | 129 | 128 | - | 2 | 9 |
| TG | 79 | 79 | - | 0 | 39 |
| SZ | 53 | 43 | - | 4 | 16 |
| SH | 43 | 8 | - | 4 | 14 |
| SG | 42 | 42 | - | 22 | 27 |
| BL | 36 | 36 | - | 0 | 17 |
| Schweiz | **3'423** | **1'364** | **1'355** | **219** | **526** |

**Die Laufnummer als Datumsersatz (nur Zürich).** Das AWEL publiziert kein Datum,
aber die GBS-Nummer der Sonde ("b 00-12657") trägt eine Laufnummer, die mit der Zeit
steigt. Kalibriert an Zürcher Neubauten mit Wärmepumpe und genau einer Sonde im
20-m-Umkreis: Nummern unter 10'000 gehören zu Baujahren bis 2001, die neue Serie ab
10'000 beginnt 2002; ab 2009 liefert das 90. Perzentil je Baujahr eine monoton
steigende Schwelle (2009: 10'934, 2018: 11'955, 2024: 12'959). Liegt die Laufnummer
über der Schwelle des Eintragsjahrs, heisst der Fall "reihenfolge plausibel" - eine
eigene Stufe, weil sie im Unterschied zur datierten Stufe nicht gemessen ist. Damit
rücken 1'057 der 1'214 Zürcher Volkszählungsfälle und 170 der 342 Fälle der Stadt
Zürich in eine geordnete Stufe. Herleitung in `sql/test5.sql`, sechs Prüfungen in
`checks.py`.

**Der Nachlauf.** Ein Beleg, der am Tag des Registerabzugs jünger als 18 Monate war,
ist kein liegengebliebener Altbestand: Bern kennt seit 2023 eine Meldepflicht für den
Heizungsersatz über eBau, Zürich das Meldeverfahren für Wärmepumpen, und nachgetragen
wird bei der Abnahme. Solche Fälle bleiben auf der Liste, sind aber in der Spalte
"Hinweis" gekennzeichnet.

Gemessen an Zug treffen die Fälle mit Listenstufe in 81,0 % der prüfbaren Fälle zu (64
von 79, Vertrauensbereich 71 bis 88 %), die Stufe mit belegter Reihenfolge in 80,8 % (63
von 78). Die Grundrate liegt bei 8,8 %. Prüfbar sind 79 der 144 Zuger Fälle mit
Listenstufe; wie sich das zu den 129 Zuger Fällen der Tabelle verhält, steht im Abschnitt
"Die Zuger Fallzahlen".

Die Spalte "Reihenfolge belegt" zählt die Fälle, bei denen der Beleg datiert und
nachweislich jünger ist als der Registereintrag. Wo ein Kanton zu seinen Anlagen kein
Datum veröffentlicht, vor allem in Zürich, bleiben die Laufnummer oder das Alter des
Eintrags als Stellvertreter.

Neben jedem Fall stehen die **Stufe** und ein **Belegtext** in einem Satz:

```
EGID 1234567 · Baujahr 1951 · Stufe: Reihenfolge belegt
  Im GWR: Heizöl, Quelle "Gemäss Volkszählung 2000", Stand 29.11.2001
  Beleg: Erdwärmesonde, Bohrung 2019, 6 m vom Gebäude, einziges Gebäude im Umkreis.
  Vorschlag: GENH1 7511 Erdwärmesonde, Quelle "Gemäss kantonalen Daten"
```

Das Beispiel ist erfunden; es zeigt nur den Aufbau. `src/pruefliste.py` schreibt die Fälle
je Kanton oder Gemeinde als Arbeitsmappe nach `data/processed/prueflisten/` und damit
ausserhalb des Git.

## Textextraktion und ihre Evaluation

Heizungsereignisse werden zuerst über Stichwörter erkannt (`silver_baugesuche.sql`).
Wie gut das ist, ist an 150 einzeln gelabelten Baugesuchstexten gemessen
(`data/labels/`, geschichtete Stichprobe; Herkunft der Labels in
[data/labels/README.md](../data/labels/README.md)):

| Aufgabe | Precision | Recall |
|---|---|---|
| Heizungsereignis erkennen | 95,6 % | 97,7 % |
| Trägerwechsel erkennen | 91,1 % | 98,8 % |
| neuen Energieträger benennen | 100 % | – |
| bisherigen Energieträger benennen | – | 81,2 % |

Die Regel findet zuverlässig, unterscheidet aber schlecht: Sie erkennt nicht, ob eine
Anlage neu gebaut oder nur erwähnt wird ("bestehende Pelletsheizung"), ob eine Wärmepumpe
eine Wärmepumpe ersetzt, oder ob die Wärmepumpe zu einem Pool gehört.

`src/extract_llm.py` löst das über eine LLM-Extraktion mit Structured Outputs. Zwei
Backends: die Claude API oder ein lokales Modell über Ollama. **Gemessen** an denselben
150 Texten, mit einem lokalen `qwen2.5:7b`:

| Verfahren | Precision | Recall | F1 |
|---|---|---|---|
| nur Stichwortregel | 91,1 % | 98,8 % | 94,8 |
| nur LLM | 97,5 % | 94,0 % | 95,7 |
| **Regel als Vorfilter, LLM als Prüfer** | **98,7 %** | 94,0 % | **96,3** |

Das Sprachmodell sortiert sieben der acht Fehltreffer der Regel aus. Die Regel läuft über
alle 22'780 Publikationen (17'654 Vorhaben mit Projektbeschrieb, die Grundgesamtheit der
Stichprobe), das Sprachmodell prüft nur die Treffer der Regel.

**Vorbehalt zu den 98,7 %:** Der Wert ist auf denselben 150 Texten gemessen, an denen der
Prompt des Sprachmodells entwickelt ist (keine unabhängige Teststichprobe), er beruht auf
n = 79 positiven Urteilen, und die Labels stammen von einem Sprachmodell. Eine belastbare
Messung braucht eine frische, von einer Person gelabelte Stichprobe
([reports/extraktion_evaluation.md](../reports/extraktion_evaluation.md), Abschnitt
"Grenzen dieser Messung").

**Die Pipeline verwendet die Kaskade** (`sql/silver_llm.sql`). Test 3 und die Belege aus
Baugesuchen bauen auf `v_baugesuch_geprueft` auf: Regel als Vorfilter, Sprachmodell als
Prüfer, beide müssen zustimmen. Liegt kein Urteil des Sprachmodells vor, weil die
Extraktion nicht gelaufen ist oder das Modell einen Fehler liefert, gilt die Regel allein.
So gehen keine Fälle stillschweigend verloren; zwei Prüfungen in `checks.py` überwachen das.

```bash
python src/extract_llm.py --test3 --backend ollama --model qwen2.5:7b --cpu     --out data/processed/llm_extraktion.jsonl
python src/pipeline.py zh     # Test 3 und Verdachtsscore nutzen das Urteil
```

```bash
python src/extract_llm.py --gold                          # gegen das Gold-Set messen
python src/extract_llm.py --backend ollama --model qwen2.5:32b --gold
python src/extract_llm.py --alle --out data/processed/extraktion.jsonl
```

Für den lokalen Lauf muss zuerst ein Modell vorliegen: `ollama pull qwen2.5:32b`
(rund 20 GB; `qwen2.5:7b` mit 4,7 GB reicht für einen ersten Vergleich).

## Kennzahlen und ihre Grenzen

**Pflege-Index** (0 bis 100): Mittel aus Vollständigkeit (Anteil mit konkretem Energieträger),
Aktualität (Datum jünger als 15 Jahre) und Herkunft (nicht aus der Volkszählung 2000).

**Pflegemuster**: Der Index allein belohnt Sammelimporte. Basel-Stadt erreicht 100 Punkte,
weil 99,1 % aller Wohngebäude dasselbe Aktualisierungsdatum tragen. Deshalb wird zusätzlich
die Streuung der Aktualisierungsdaten gemessen und in vier Muster eingeteilt: *laufend*,
*Sammelimport*, *sporadisch*, *Rückstand*. Die Volkszählung 2000 ist aus dieser Messung
ausgeschlossen, sonst zählt der unbearbeitete Altbestand fälschlich als Import.

**Was der Index nicht kann:** Er misst, ob ein Eintrag angefasst wurde, nicht ob er stimmt.
Der Nachweis steckt in der Zürcher Gegenprobe (siehe [reports/report.md](../reports/report.md)).
