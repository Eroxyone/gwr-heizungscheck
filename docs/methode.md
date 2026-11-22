# Methode

Wie aus den Quellen ein Verdacht wird, was gemessen ist und was nicht. Die Kurzfassung steht im
[README](../README.md), die Herkunft der Daten in [datenquellen.md](datenquellen.md).

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

Ein Windows-Task `GWR-Snapshot` läuft dafür wöchentlich montags um 06:30
(`scripts/snapshot.ps1`). Entfernen mit
`Unregister-ScheduledTask -TaskName "GWR-Snapshot" -Confirm:$false`.

## Was die Zeitreihe nach neun Wochen gezeigt hat

Der Gold-Layer wird aus dem jüngsten Snapshot gerechnet; ein Fall verlässt die Liste, sobald
das Register ihn nicht mehr fossil führt. Damit die Spur nicht verloren geht, hält
`gold_liste_archiv` je Registerstand fest, was auf der Liste stand, und
`v_gold_liste_korrigiert` zeigt je archiviertem Fall den ersten späteren Snapshot, in dem der
Eintrag nicht mehr fossil ist, mit neuem Träger und neuer Quelle. Das ist die natürliche
Messung des Projekts: Korrekturen, die Gemeinden und Kantone ohne unser Zutun vornehmen,
gegen die Liste gehalten.

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

## Vom Befund zum Verdachtsscore

`gold_verdacht.sql` führt die Tests zusammen. Ein Gebäude kommt nur auf die Liste, wenn
es **mindestens einen echten Beleg** gibt:

| Beleg | Gewicht | gemessene Wirkung |
|---|---|---|
| Heizungs-Baugesuch, nicht nachgeführt | 50 bis 55 | **ungemessen** - in keinem Labelkanton kommt ein einziger Fall vor |
| Wärmenutzungsanlage, eindeutig zugeordnet | 40 | 62 bis 64 % falsche Einträge, Faktor 7 (Zug) |
| Wärmeerzeuger ist Wärmepumpe, Träger ist Heizöl | 15 | ungemessen, aber technisch unmöglich |
| Photovoltaikanlage | 18 | 13,7 % (Genf) und 17,2 % (Zug), Faktor 2 bis 2,5 - allein zu wenig |
| Quelle 860 | 12 | nur zusammen mit einem Beleg, siehe unten |
| Registereintrag älter als 15 Jahre | 8 bis 15 | dito, und nur wo der Beleg undatiert ist |
| Beleg älter als der Registereintrag | Ausschluss | 13,3 % statt 80,8 %, gemessen in Zug |
| Laufnummer der Zürcher Sonde über der Jahresschwelle | Stufe "reihenfolge plausibel" | **ungemessen** - kalibriert an Neubauten, `gold_laufnummer_kalibrierung` |
| Beleg jünger als 18 Monate am Tag des Abzugs | Kennzeichen "im Nachlauf" | Bern: Meldepflicht Heizungsersatz seit 2023, Nachführung bei der Abnahme |
| GWR-Codes im Korrekturvorschlag | aus `bronze_gwr_kodes` | nicht mehr getippt - 3'419 Vorschläge trugen einmal 7430 statt 7410 |
| Warmwasser über Fernwärme oder Wärmepumpe | 0 | **widerlegt**, Faktor 0,7 bis 0,8 |
| Entfernung der Anlage zum Gebäude | 0 | **widerlegt**, kein Gradient zwischen 5 und 20 m |
| Baujahr | 0 | **widerlegt**, Faktor 0,94 |

Drei Gewichte stehen hier auf null, weil die Messung sie widerlegt hat. Der teuerste
Irrtum war der Fernwärme-Widerspruch: Er sah mit Faktor 5,1 nach einem starken Beleg
aus, bis im Genfer Wärmeerzeuger-Layer das Feld `USAGE` ausgewertet wurde. Die
vermeintlichen Treffer waren Übergabestationen, an denen `['ECS']` steht - sie machen
nur das Warmwasser. Der Beleg lautete "das Warmwasser läuft über Fernwärme", und die
Gegenquelle sagte dasselbe. Gemessen wurde die Übereinstimmung zweier Register, nicht
ein Heizungswechsel. Details in `reports/belegwirkung.md`.

**Quelle 860 und ein altes Datum sind ausdrücklich keine Belege.** Das ist der Kernbefund
des Projekts: Ohne diesen Filter stünden 343'265 Gebäude auf der Liste, 95 % davon ohne
jeden Beleg.

Zusammen mit einem Beleg sind sie allerdings das trennschärfste Merkmal überhaupt -
und das war die Überraschung der Kalibrierung. Gemessen an den 109 Zuger Fällen, die
auf der Verdachtsliste stünden:

| Stufe | gemessen | n | Faktor |
|---|---:|---:|---:|
| Beleg jünger als der Registereintrag | 80,8 % | 78 | 9,2 |
| Beleg älter als der Registereintrag | 13,3 % | 30 | 1,5 |
| *Grundrate im Kanton* | *8,8 %* | *4'430* | *1,0* |

Das ist in sich stimmig: Ein Beleg sagt, dass am Gebäude etwas an der Heizung geschehen
ist. Ob das im Register schon steht, hängt daran, wann das Register zuletzt angefasst
wurde. Die früheren Stufen ("alter Eintrag", "Solaranlage zusätzlich") waren ein
Stellvertreter für genau dieses Merkmal - wo die Reihenfolge direkt bekannt ist, braucht
es ihn nicht mehr.

## Was auf die Liste kommt

`v_gold_verdacht` enthält rund 88'000 Fälle, aber über 95 % davon beruhen allein auf
einer Photovoltaikanlage oder auf Metadaten. Bei 13,7 bis 17,2 % Trefferquote ist das keine
Liste, die jemand abarbeiten kann. **`v_gold_liste` ist deshalb die engere Sicht: 3'423
Fälle in 526 Gemeinden am 14.09.2026, 2'738 am 16.11.2026.** Zwei Filter machen den Unterschied: Es braucht einen Beleg, der
etwas über die Heizung sagt, und dieser Beleg darf nicht älter sein als der
Registereintrag.

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

Gemessen an Zug trifft die ganze Liste in 81,0 % der prüfbaren Fälle zu (64 von 79,
Vertrauensbereich 71 bis 88 %), die Stufe mit belegter Reihenfolge in 80,8 % (63 von
78). Die Grundrate liegt bei 8,8 %.

Die Spalte "Reihenfolge belegt" ist die entscheidende: Sie zählt die Fälle,
bei denen der Beleg datiert und nachweislich jünger ist als der Registereintrag. Wo ein
Kanton zu seinen Anlagen kein Datum veröffentlicht - Zürich ist der grosse Fall -,
bleibt nur das Alter des Eintrags als Stellvertreter.

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

Heizungsereignisse werden heute über Stichwörter erkannt (`silver_baugesuche.sql`).
Wie gut das ist, wurde an 150 einzeln gelabelten Baugesuchstexten gemessen
(`data/labels/`, geschichtete Stichprobe; Herkunft der Labels in
[data/labels/README.md](../data/labels/README.md)):

| Aufgabe | Precision | Recall |
|---|---|---|
| Heizungsereignis erkennen | 95,6 % | 97,7 % |
| Trägerwechsel erkennen | 91,1 % | 98,8 % |
| neuen Energieträger benennen | 100 % | – |
| bisherigen Energieträger benennen | – | 81,2 % |

Die Schwäche der Regel ist nicht das Finden, sondern das Unterscheiden: Sie erkennt
nicht, ob eine Anlage neu gebaut oder nur erwähnt wird ("bestehende Pelletsheizung"),
ob eine Wärmepumpe eine Wärmepumpe ersetzt, oder ob die Wärmepumpe zu einem Pool gehört.

`src/extract_llm.py` löst das über eine LLM-Extraktion mit Structured Outputs. Zwei
Backends: die Claude API oder ein lokales Modell über Ollama. **Gemessen** an denselben
150 Texten, mit einem lokalen `qwen2.5:7b`:

| Verfahren | Precision | Recall | F1 |
|---|---|---|---|
| nur Stichwortregel | 91,1 % | 98,8 % | 94,8 |
| nur LLM | 97,5 % | 94,0 % | 95,7 |
| **Regel als Vorfilter, LLM als Prüfer** | **98,7 %** | 94,0 % | **96,3** |

Das LLM sortierte sieben der acht Fehltreffer der Regel korrekt aus. Die Kaskade ist auch
betrieblich richtig: Die Regel läuft ohne Aufwand über alle 22'780 Texte, das LLM prüft nur
noch die wenigen hundert, die als Beleg in Frage kommen.

**Die Kaskade läuft produktiv** (`sql/silver_llm.sql`). Test 3 und der Verdachtsscore
bauen auf `v_baugesuch_geprueft` auf: Regel als Vorfilter, LLM als Prüfer, beide müssen
zustimmen. Liegt kein LLM-Urteil vor - weil die Extraktion noch nicht lief oder das
Modell einen Fehler lieferte - gilt die Regel allein. Das Verfahren degradiert also
sauber, statt Fälle stillschweigend zu verlieren; zwei Checks wachen darüber.

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
