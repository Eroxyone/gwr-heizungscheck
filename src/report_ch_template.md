# Heizungsangaben im GWR: Wie gut pflegen die Kantone ihr Register?

**Alle 26 Kantone, {gemeinden} Gemeinden, {wohngeb} Wohngebäude. Datenstand {stand}.**
Erzeugt von `src/report_ch.py` aus den Parquet-Snapshots. Keine Zahl ist von Hand eingetragen.

Interaktive Fassung: [dashboard.html](dashboard.html).
Die Detailauswertung für den Kanton Zürich mit Baugesuchen steht in [report.md](report.md).

---

## Kurzfassung

Im Gebäude- und Wohnungsregister trägt jedes Gebäude einen Eintrag zu Energieträger und
Wärmeerzeuger, dazu eine Informationsquelle und ein Aktualisierungsdatum. Wie gut dieser
Eintrag gepflegt wird, unterscheidet sich zwischen den Kantonen drastisch.

- **{pct_vz2000} % aller Schweizer Wohngebäude** ({vz2000} Stück) tragen bei der Heizung
  immer noch die Volkszählung 2000 als Quelle. Der Eintrag wurde seit einem Vierteljahrhundert
  nicht bestätigt.
- Das **Median-Alter** der Heizungsangabe liegt schweizweit bei **{median_alter} Jahren**.
- **{pct_fossil} %** der Wohngebäude sind fossil beheizt ({fossil} mit Öl oder Gas),
  **{pct_wp} %** haben eine Wärmepumpe.
- **{kandidaten} Gebäude** ({pct_kandidaten} %) sind Verdachtsfälle: fossil beheizt und der
  Eintrag entweder ungeprüft oder älter als 15 Jahre.
- Die Spannweite zwischen den Kantonen reicht von **{best_kt} mit {best_idx} Punkten** bis
  **{schlecht_kt} mit {schlecht_idx}**. In **{n_rueckstand} Kantonen** überwiegt der
  unbearbeitete Altbestand.

Ein Befund vorweg, der die ganze Auswertung relativiert: **Der Index misst Pflege, nicht
Richtigkeit.** Wie weit beides auseinanderliegt, zeigt Abschnitt 5.

---

## 1 Der Pflege-Index

Drei Anteile über alle Wohngebäude, gemittelt:

| Bestandteil | Was gemessen wird |
|---|---|
| Vollständigkeit | Anteil mit konkretem Energieträger (nicht leer, nicht "unbestimmt", nicht "andere") |
| Aktualität | Anteil mit Aktualisierungsdatum jünger als 15 Jahre |
| Herkunft | Anteil, der **nicht** aus der Volkszählung 2000 stammt |

Quelle 860 (Volkszählung 2000) heisst nicht falsch, sondern ungeprüft. Ob der Eintrag
stimmt, weiss niemand, weil ihn seit 2000 niemand bestätigt hat.

Notenklassen: A ab 90, B ab 75, C ab 60, D ab 45, E darunter.

---

## 2 Kantone

{rang}

### Pflegemuster

Der Index allein genügt nicht. Ein Kanton, der einmal alles auf einen Schlag importiert,
sieht darin aus wie einer, der laufend arbeitet. Deshalb wird zusätzlich gemessen, wie sich
die Aktualisierungsdaten verteilen:

- **laufend** - die Daten streuen über viele Tage, es wird kontinuierlich gearbeitet
- **Sammelimport** - mindestens 40 % aller Einträge tragen denselben Tag
- **Rückstand** - weniger als die Hälfte der Gebäude hat überhaupt eine Angabe aus den letzten 15 Jahren
- **sporadisch** - weder das eine noch das andere

{muster}

Die Kantone mit Sammelimport im Detail:

{bulk}

Basel-Stadt ist der Extremfall: 99,1 % aller Wohngebäude tragen dasselbe Aktualisierungsdatum,
Quelle ist zu 99,7 % die Feuerungskontrolle. Der Index von 100 Punkten steht für einen
einzigen Schreibvorgang, nicht für einen laufenden Prozess.

### Informationsquellen schweizweit

{quellen_ch}

---

## 3 Gemeinden

{gem_noten}

**{n_gem_de} Gemeinden ({pct_gem_de} %) stehen bei Note D oder E**, {n_gem_rueckstand}
Gemeinden sind im Rückstand.

{gem_muster}

### Grösster Rückstand (ab 500 Wohngebäuden)

{schlecht}

### Vorbildlich laufende Pflege (ab 500 Wohngebäuden)

{gut}

### Meiste Verdachtsfälle in absoluten Zahlen

Diese Liste ist für die Praxis interessanter als die Prozentwerte: Hier liegt die grösste
Menge an Gebäuden, bei denen der Heizungseintrag fossil und ungeprüft ist.

{absolut}

---

## 4 Datenqualität der Quelle

Vor jedem Report läuft `python src/checks.py`, eine Reihe von Datenqualitäts- und
Regressionsprüfungen. Was dabei aufgefallen ist:

- **{zukunft} Einträge tragen ein Aktualisierungsdatum in der Zukunft**, im Extremfall neun
  Monate. Erfassungsfehler in der Quelle, nicht korrigierbar, aber überwacht.
- **{ohne_datum} Gebäude haben überhaupt kein Aktualisierungsdatum.** Das sind überwiegend
  Gebäude ohne Wohnnutzung und ohne Wärmeerzeuger.
- Ein Regressionstest hält die Zürcher Zahlen aus der Detailauswertung fest. Ändert sich die
  Fachlogik, fällt er auf, bevor Zahlen im Report landen.

---

## 5 Die Grenze dieser Auswertung

**Der Index misst dokumentierte Pflege, nicht Richtigkeit.** Das lässt sich in diesem Projekt
belegen, weil für den Kanton Zürich eine unabhängige Gegenprobe existiert: {t3_n} Baugesuche für
einen Heizungsersatz wurden mit dem Registerstand verglichen.

Ergebnis: **Bei {t3_luecke} % der Fälle zeigt das GWR weiterhin den alten Energieträger**, obwohl das
Baugesuch mindestens ein halbes Jahr zurückliegt. Bei Gesuchen ab 18 Monaten sind es noch {t3_luecke18} %.

Der entscheidende Punkt: **Die Stadt Zürich hat null Einträge aus der Volkszählung 2000.** Nach
dieser Auswertung ist sie sauber. In der Gegenprobe verfehlt sie bei rund zwei Dritteln der
Heizungs-Baugesuche die Nachführung. Metadaten zählen ersetzt nicht, Ereignisse zu prüfen.

Daraus folgt für die Lesart dieses Reports:

1. Ein hoher Index heisst: Das Register wurde angefasst. Nicht: Die Einträge stimmen.
2. Ein niedriger Index ist dagegen aussagekräftig. Wo die Volkszählung 2000 noch die
   Hauptquelle ist, wurde tatsächlich nichts geprüft.
3. Das Pflegemuster trägt mehr Information als der Index. Laufende Pflege über viele Tage
   ist ein besseres Zeichen als ein hoher Punktwert aus einem Import.

Die Auswertung erfasst ausserdem nur Gebäude mit Wohnnutzung (Gebäudekategorien 1020, 1030,
1040) und nur den Status "bestehend". Wärmeerzeuger 2 und Warmwasser bleiben unberücksichtigt.

### 5.1 Wo überhaupt gegengeprüft werden kann

Der Index oben lässt sich für alle 26 Kantone rechnen, weil er nur das GWR braucht.
Die Gegenprobe braucht eine zweite Quelle - und die gibt es nur stellenweise:

{belege}

Ein leeres Feld heisst **nicht**, dass der Kanton sauber ist. Es heisst, dass niemand
nachsehen kann. Umgekehrt sieht ein Kanton mit offenen Anlagendaten zwangsläufig
schlechter aus, weil bei ihm überhaupt etwas gefunden werden kann. **Jede Rangliste in
diesem Report ist zuerst eine Rangliste der Datenoffenheit.** Die vollständige
Quellenlage je Kanton steht in `reports/quellenmatrix.md`.

### 5.2 Wie zuverlässig die Zuordnung ist

Ein Beleg nützt nur, wenn er beim richtigen Gebäude landet. Zwei unabhängige Messungen
dazu, mit sehr unterschiedlichem Ergebnis:

| Beleg | Referenz | Treffer |
|---|---|---|
| Photovoltaikanlage | BFE-Datensatz mit EGID-Spalte, {solar_beide} Anlagen mit beiden Zuordnungswegen | **{solar_pct} %** Übereinstimmung |
| Erdwärmesonde | amtliche EGID des Kantons Zug, 805 Anlagen | **73,8 %** Recall bei 20 m |

Der Unterschied hat einen einfachen Grund: **Eine Solaranlage liegt auf dem Gebäude, eine
Erdsonde daneben.** Bei der Photovoltaik ist die Koordinate praktisch das Gebäude, bei der
Sonde ist sie ein Punkt im Garten - und der kann näher beim Nachbarn liegen. Auch bei 50 m
Radius steigt der Sonden-Recall nur auf 80 %; ein grösserer Umkreis kauft vor allem
Nachbarn dazu (`reports/zuordnung_zg.md`).

Für die Fallzahlen heisst das: Bei den Sonden sind sie eher Unter- als Obergrenzen, weil
rund ein Viertel der echten Fälle gar nicht gefunden wird.

---

## 6 Was als Nächstes gemessen werden sollte

Ein einzelner Snapshot zeigt einen Zustand. Die interessantere Grösse ist die Bewegung:
Wie viele Heizungseinträge ändert ein Kanton pro Monat tatsächlich?

Die Pipeline legt deshalb bei jedem Lauf einen Parquet-Snapshot pro Kanton ab
(`data/snapshots/gwr/snapshot_date=.../kanton=.../data.parquet`, rund 60 MB für die ganze
Schweiz). Sobald zwei Stände vorliegen, liefert `v_gold_veraenderung` die Änderungsrate je
Kanton und Zeitraum. Diese Kennzahl lässt sich nicht nachträglich beschaffen, sie entsteht
nur durch Sammeln ab jetzt.

---

## Reproduzierbarkeit

```bash
pip install -r requirements.txt
python src/ingest.py       # alle 26 Kantone laden, Snapshot schreiben
python src/pipeline.py ch  # Silver- und Gold-Layer rechnen
python src/checks.py       # Datenqualitäts- und Regressionsprüfungen
python src/report_ch.py    # diesen Report erzeugen
```
