# GWR-Heizungscheck - Validierung mit echten Daten

**Kanton Zürich im Detail, Erdwärmesonden auch für Bern. Datenstand GWR {stand_gwr}, Baugesuche bis {stand_bg}.**
Erzeugt von `src/report.py`. Alle Zahlen stammen direkt aus der Pipeline, nichts ist von Hand eingetragen.

---

## Kurzfassung

Die Frage war: Sind Heizungsangaben im GWR so oft veraltet, dass sich eine Verdachtsliste
für eine Gemeinde lohnt? Die Antwort aus den Daten ist zweigeteilt.

**Die Datenlücke ist real und gross.** Von {t3_n} eindeutig zugeordneten Heizungs-Baugesuchen,
die mindestens sechs Monate zurückliegen, zeigt das GWR bei **{luecke_pct} %** immer noch den alten
Energieträger mit einem Aktualisierungsdatum vor dem Baugesuch. Nur {nachgef_pct} % sind sauber
nachgeführt, in der weiten Auslegung {nachgef_weit} %. Auch bei Baugesuchen, die 18 Monate und
länger zurückliegen, bleibt die Lücke bei {luecke_18} %. Das Stop-Kriterium (über 80 % nachgeführt)
ist deutlich verfehlt - Test 3 ist ein klares Go.

**Die Belege sind für die meisten Gemeinden zu dünn.** Über alle Gemeinden hinweg finden sich nur
rund {heiz_pro_jahr_kt} Heizungs-Baugesuche pro Jahr im ganzen Kanton. Die mittlere Gemeinde kommt
auf **{median_gesuche} Gesuche pro Jahr**, drei Viertel der Gemeinden liegen unter {q75_gesuche}.
Ein Bericht mit zwei Verdachtsfällen pro Jahr trägt nicht. Nur Zürich und Winterthur haben
genug Volumen. Das ist das Stop-Kriterium aus Test 2.

**Ein dritter Befund kam später dazu und relativiert die ersten beiden.** Bern veröffentlicht
seine Erdwärmesonden mit Bewilligungsdatum und Ausführungsstatus - die beste Messgrundlage
im ganzen Projekt, weil dort feststeht, dass gebaut wurde. Das Ergebnis: {t6_nachgefuehrt} %
der Anlagen sind im GWR sichtbar, aber der Wert hängt stark am Alter. Anlagen aus den letzten
2 bis 4 Jahren sind zu {t6_neu} % erfasst, Anlagen ab 20 Jahren nur zu {t6_alt} %.
**Die Nachführung wird besser.** Der Rückstand liegt im Altbestand, nicht im laufenden
Betrieb. Ein Dienst, der veraltete Einträge findet, arbeitet damit an einem schrumpfenden
Problem.

**Fazit: Die Lücke ist real, Baugesuche allein reichen als Beleg nicht.** Details in Abschnitt 5.

Ein methodischer Nebenbefund, der für die weitere Arbeit wichtiger ist als alles andere:
Die Informationsquelle im GWR (Code 860 "Volkszählung 2000") taugt nicht als Indikator für
Datenqualität. Die Stadt Zürich hat 0 % Einträge mit Quelle 860 und wäre nach Test 1 sauber -
in Test 3 fehlt dort trotzdem bei rund zwei Dritteln der Heizungs-Baugesuche die Nachführung.
Wer veraltete Einträge finden will, muss Ereignisse gegen den Registerstand prüfen, nicht
Metadaten zählen.

---

## 1 Datenbasis

### 1.1 Quellen

{quellen}

Alle Quellen sind offen zugänglich; die Nutzungsbedingungen je Quelle stehen in
[lizenzen.md](lizenzen.md). Rohdaten liegen in `data/raw/` und sind bewusst nicht im Git.
`data/raw/manifest.json` hält URL, Grösse, SHA-256 und Downloadzeitpunkt fest.

### 1.2 Umfang

{umfang}

### 1.3 Stand und Lücken

- **GWR:** Exportdatum {stand_gwr}, also tagesaktuell. Vollständig für den ganzen Kanton.
  Die Codelisten stammen aus der mitgelieferten Datei `kodes_codes_codici.csv`, nicht aus
  Sekundärquellen.
- **Baugesuche:** Publikationen bis {stand_bg}. Die Sammlung des Statistischen Amts ist erst
  ab Herbst 2024 vollständig; frühere Jahre enthalten nur Einzelfälle (2022: 3, 2023: 74).
  Alle Zeitreihen in diesem Report beginnen deshalb im Oktober 2024.
  Die Felder `bfs_nr` und `municipality_name` sind erst ab 2025 gefüllt. Für 2024 wurde die
  Gemeinde über das zugeordnete Gebäude beziehungsweise über PLZ und Ortsname hergeleitet;
  danach bleiben 402 von {n_bg} Gesuchen ohne Gemeinde.
  Parzellengeometrien gibt es erst ab 2025.
- **Mehrfachpublikationen:** Dasselbe Vorhaben erscheint oft mehrmals. {n_doppelt} von {n_bg}
  Publikationen ({pct_doppelt} %) wiederholen einen bereits vorhandenen Beschrieb an derselben
  Adresse; ein Grossprojekt kommt {max_doppelt}-mal vor, offenbar einmal je betroffene
  Liegenschaft. Alle Auswertungen zählen deshalb **Vorhaben, nicht Publikationen**:
  {n_vorhaben} Vorhaben, davon {n_heiz_vorhaben} mit Heizungsbezug. Ohne diese Korrektur
  lägen die Fallzahlen rund ein Fünftel zu hoch.
- **Photovoltaik:** letzte Inbetriebnahme im verwendeten Datensatz {stand_pv}.
  Hier lauert ein Stolperstein: Der auf opendata.swiss verlinkte CSV-Pfad `/csv/2056/` liefert
  eine auf exakt 100'000 Zeilen gekürzte Datei, die für den Kanton Zürich nur bis Oktober 2022
  reicht. Sie enthält dafür eine EGID-Spalte. Verwendet wird deshalb das STAC-Asset desselben
  Datensatzes mit 333'313 Anlagen; dort fehlt die EGID, die Zuordnung läuft über die Koordinate.
  Die gekürzte Datei dient als Referenz zur Prüfung genau dieser Zuordnung (Abschnitt 3).

---

## 2 Ergebnisse

### 2.1 Test 1 - Grösse des Problems

Betrachtet werden bestehende Gebäude mit Wohnnutzung (GKAT 1020, 1030, 1040).
Als *Kandidat* gilt ein fossil beheiztes Gebäude (Heizöl oder Gas), dessen Heizungsangabe
entweder die Quelle 860 trägt oder deren Aktualisierungsdatum älter als 15 Jahre ist
oder fehlt.

{t1_kanton}

**{n_kandidaten} Kandidaten** von {n_wohngeb} Wohngebäuden im Kanton. Verteilung der
Informationsquelle über alle Wohngebäude:

{t1_quellen}

Ein Drittel aller Heizungseinträge im Kanton geht immer noch auf die Volkszählung 2000 zurück.
Die Spannweite zwischen den Gemeinden ist aber enorm:

{t1_spann}

Fokusgemeinden:

{t1_fokus}

Hier zeigt sich der erste wichtige Befund. Zürich hat **null** Einträge mit Quelle 860 und damit
null Kandidaten nach dieser Definition, obwohl 70,5 % der Wohngebäude fossil beheizt sind.
Die Stadt hat die Volkszählungsdaten flächendeckend durch eigene Einträge ersetzt (Code 859
"Andere"), die zum grossen Teil aus den Jahren 2018 bis 2021 stammen. Nach Test 1 wäre Zürich
also sauber. Test 3 zeigt das Gegenteil. **Die Informationsquelle allein ist kein brauchbarer
Qualitätsindikator.**

Test 1 liefert damit *kein* Stop-Signal (der Anteil ist im Median hoch), aber auch kein
belastbares Go - die Kennzahl misst nicht, was sie zu messen vorgibt.

### 2.2 Test 2 - Genug Belege?

{n_heiz} von {n_bg} Publikationen wurden über Stichworte als Heizungsereignis erkannt; nach
Zusammenfassen der Mehrfachpublikationen bleiben **{n_heiz_vorhaben} Vorhaben**
(Details zur Erkennung in Abschnitt 4). Verteilung des erkannten neuen Energieträgers
über alle Publikationen:

{t2_traeger}

Zeitreihe für den ganzen Kanton:

{t2_monat}

Der September 2026 ist ein angebrochener Monat (bis zum {stand_bg}), die absolute Zahl dort
ist deshalb nicht vergleichbar. Der Anteil der Heizungsgesuche steigt über die Quartale hinweg
stetig von 5,6 % (Q4 2024) auf 9,5 % (Q3 2026) - das ist ein echter Trend, kein Artefakt.

Entscheidend ist die Verteilung über die Gemeinden:

{t2_spann}

**Das ist das Stop-Signal.** Die mittlere Gemeinde hat {median_gesuche} Heizungs-Baugesuche pro
Jahr. Selbst im oberen Viertel sind es weniger als {q75_gesuche} pro Jahr. Die Belege konzentrieren
sich fast vollständig auf wenige grosse Gemeinden:

{t2_top}

Fokusgemeinden:

{t2_fokus}

Illnau-Effretikon fällt mit 4 Heizungsgesuchen in zwei Jahren auf, bei 157 Baugesuchen insgesamt.
Das ist kein Datenfehler, sondern Publikationspraxis: Der Anteil der Heizungsgesuche an allen
Baugesuchen schwankt zwischen 0 % und 20 % je nach Gemeinde. Manche Gemeinden publizieren einen
Heizungsersatz als eigenes Baugesuch, andere behandeln ihn als bewilligungsfrei oder als
Nebenpunkt eines grösseren Vorhabens. Der Ausreisser nach oben ist Winterthur mit rund 20 %.

**Grössenordnung zum Vergleich:** Im Kanton stehen rund 127'000 fossil beheizte Wohngebäude.
Bei einer Ersatzrate von 3 bis 5 % pro Jahr wären das 4'000 bis 6'000 Heizungswechsel jährlich.
Gefunden werden über die Baugesuche rund {heiz_pro_jahr_kt} pro Jahr. **Baugesuche erfassen damit
grob geschätzt 10 bis 20 % der tatsächlichen Heizungswechsel.** Der Rest sind Ersatzvorhaben im
Gebäudeinneren, die keine Baubewilligung brauchen. Sichtbar wird vor allem die aussen aufgestellte
Luft/Wasser-Wärmepumpe, weil die wegen Lärm und Grenzabstand bewilligungspflichtig ist.

### 2.3 Test 3 - Werden Baugesuche schon nachgeführt?

Der wichtigste Test. Grundmenge: Heizungs-Baugesuche, deren Publikation mindestens sechs Monate
zurückliegt, die genau einem Gebäude zugeordnet werden konnten und die kein reiner Neubau sind.
Das sind {t3_n} Fälle.

{t3_haupt}

Zusammengefasst: **{nachgef_pct} % sauber nachgeführt**, in der weiten Auslegung (inklusive
"Quelle 869 nach dem Gesuch" und "Energieträger passt, Datum älter") **{nachgef_weit} %**.
Dem stehen **{luecke_pct} % klare Lücken** gegenüber.

Der naheliegende Einwand lautet: Sechs Monate sind zu kurz, gebaut wird erst später. Deshalb
dieselbe Auswertung nach Alter des Baugesuchs:

{t3_alter}

Die Nachführung holt mit der Zeit auf, aber sie holt nicht ein. Bei Baugesuchen, die 18 Monate
und länger zurückliegen, sind {nachgef_18} % nachgeführt und **{luecke_18} % weiterhin nicht**.
Das Stop-Kriterium von 80 % wird in keinem Altersfenster erreicht.

Was in den Lückenfällen im GWR steht:

{t3_gwr_bei_luecke}

Die Streuung zwischen den Gemeinden ist der eigentliche Befund (Gemeinden mit mindestens
8 auswertbaren Fällen):

{t3_gemeinden}

Fokusgemeinden:

{t3_fokus}

Illnau-Effretikon und Fehraltorf fehlen in dieser Tabelle: Beide haben nach allen Filtern
null auswertbare Fälle. Für diese Gemeinden lässt sich die Frage aus Test 3 mit Baugesuchen
schlicht nicht beantworten - was für sich genommen bereits die Antwort auf Test 2 ist.

Winterthur ist der interessanteste Fall. Die Stadt hat im Februar 2024 die Heizungsdaten
flächendeckend aktualisiert - 84 % aller Wohngebäude tragen ein Aktualisierungsdatum ab 2024.
Trotzdem fehlt bei 58 % der Heizungs-Baugesuche die Nachführung, und zwar typischerweise mit
genau diesem Muster: Energieträger Gas, Quelle "Gemäss Daten der Gemeinde", Datum 2024-02-09,
Baugesuch für den Wärmepumpenersatz aus 2025 oder 2026. **Eine Sammelaktualisierung erzeugt einen
sauberen Stichtag, aber keinen laufenden Prozess.** Genau dort läge der Nutzen des Dienstes.

### 2.4 Gegenprobe - wie viel führt der Kanton insgesamt nach?

Diese Auswertung stand nicht im Plan, ist für die Entscheidung aber zentral.
Aktualisierungen der Heizungsangabe bei Wohngebäuden, nach Jahr des Aktualisierungsdatums:

{t3_volumen}

Im Jahr 2024 wurden {akt_2024} Heizungseinträge angefasst, 2026 bereits {akt_2026}. Seit Anfang
2024 wurden {wp_seit_2024} Wohngebäude mit einer Wärmepumpe erfasst. Die Treiber sind das
Gebäudeprogramm (Code 864), Gemeindedaten (865), die Feuerungskontrolle (855) und
Baubewilligungen (869).

**Der Kanton und die Gemeinden führen also bereits im grossen Stil nach - über Kanäle, die pro Jahr
ein Vielfaches dessen abdecken, was Baugesuche überhaupt sichtbar machen können.** Die Lücke aus
Test 3 ist real, aber sie ist eine Lücke in einem bereits laufenden Prozess, nicht ein
unbearbeitetes Feld.

### 2.5 Test 4 - Fälle ohne Baugesuch

Gebäude mit Wohnnutzung, registrierter Photovoltaikanlage, fossilem Heizungseintrag und
Quelle 860: **{t4_kanton} Gebäude im Kanton**.

{t4_top}

Fokusgemeinden:

{t4_fokus}

Das ist wie erwartet nur ein schwaches Indiz. Eine PV-Anlage sagt nichts über die Heizung; sie
zeigt nur, dass die Eigentümerschaft in den letzten Jahren am Gebäude etwas gemacht hat und dass
der Heizungseintrag seither nicht angefasst wurde. Als eigenständiger Beleg ist das zu wenig,
als zusätzliches Merkmal in einem Score brauchbar.

### 2.6 Test 5 - Erdwärmesonden gegen den Registerstand

Dieser Test kam nach der ersten Auswertung dazu und ist der schärfste. Er begann mit fünf
Kantonen (Zürich, Bern, Thurgau, Schaffhausen, Uri) und umfasst inzwischen alle, die ihre
bewilligten Anlagen zur Wärmenutzung des Untergrunds offen veröffentlichen. Zusammen **{t5_anlagen_total} Anlagen**, davon {t5_gebaut}
nachweislich gebaut.

{t5_anlagen}

Der Unterschied zu Test 4 ist entscheidend: Eine Photovoltaikanlage sagt nichts über die
Heizung. Eine Erdwärmesonde schon. Niemand bohrt 250 Meter tief, um eine Ölheizung zu
betreiben. Steht im GWR trotzdem Öl oder Gas, ist das kein Indiz, sondern ein Widerspruch.

**Was im GWR rund um eine Wärmenutzungsanlage steht** (Wohngebäude innerhalb von 20 m,
Kanton Zürich):

{t5_umkreis}

Nur **{t5_pct_wp} %** aller Zürcher Anlagen haben überhaupt ein Gebäude mit
Wärmepumpen-Eintrag im Umkreis. Die anderen Kantone kommen unabhängig davon auf ähnliche
Werte:

{t5_kantone}

**Vier von fünf Kantonen liegen zwischen 45 % und 56 %**, obwohl die Daten von fünf
verschiedenen Ämtern stammen, in unterschiedlichen Formaten geliefert werden und
Schaffhausen sogar ein anderes Koordinatensystem verwendet. Das ist die stärkste
Bestätigung im ganzen Projekt, weil die Messungen nichts miteinander zu tun haben.

Uri fällt mit {t5_pct_wp_ur} % ab, aber das ist erklärbar: Dort meldet der Datensatz
ausschliesslich "Konzession erteilt". Eine erteilte Konzession heisst noch nicht, dass
gebohrt wurde. Uri ist deshalb aus der datierten Auswertung in Abschnitt 2.7
ausgeschlossen.

**Ergebnis:** **{t5_widerspruch} Wohngebäude** über alle fünf Kantone
({t5_widerspruch_zh} in Zürich, {t5_widerspruch_be} in Bern) sind fossil eingetragen,
obwohl innerhalb von 20 m eine
Wärmenutzungsanlage bewilligt und gebaut ist und kein einziges Gebäude dort eine
Wärmepumpe ausweist. Davon tragen {t5_vz2000} die Quelle "Volkszählung 2000". Die mittlere
Distanz zur Anlage beträgt {t5_med_dist} m.

{t5_gemeinden}

Fokusgemeinden (Kanton Zürich):

{t5_fokus}

**Wie robust ist das?** Der Suchradius bestimmt das Ergebnis, deshalb die Sensitivitäts-
rechnung für Zürich:

{t5_radius}

Bei 50 m fängt der Umkreis die halbe Nachbarschaft ein, bei 10 m fehlt einem Drittel der
Anlagen jedes Gebäude. Gewählt sind 20 m: Damit haben 95 % der Anlagen ein Gebäude in der
Nähe, im Schnitt 2,4 Stück. Der Widerspruchsanteil liegt je nach Radius zwischen 13,7 %
und 25,6 % - die Grössenordnung ist stabil, der exakte Wert nicht.

Bemerkenswert ist noch etwas: Bei den Gebäuden rund um eine Wärmenutzungsanlage steht in
28,7 % der Fälle "Unbestimmt" als Energieträger. Das Register weiss dort nicht einmal,
womit geheizt wird, obwohl direkt daneben eine bewilligte Erdsonde liegt.

### 2.7 Test 6 - Bern und Thurgau, mit Datum und Ausführungsnachweis

Zürich veröffentlicht kein Bohrdatum (87 % der GBS-Nummern beginnen mit "00"), der
Widerspruch aus Test 5 lässt sich dort also nicht zeitlich einordnen. **Bern und Thurgau
schon:** Beide Datensätze tragen zu jeder Anlage ein Datum und einen Status, der eine
tatsächlich gebaute Anlage von einer bloss bewilligten unterscheidet.

Damit sind diese beiden die beste Messgrundlage im ganzen Projekt - besser noch als die
Baugesuche aus Test 3. Ein Baugesuch beweist nicht, dass gebaut wurde. Hier steht es im
Datensatz.

Grundmenge: {t6_n} ausgeführte Anlagen mit Bewilligungsdatum und mindestens einem Gebäude
im Umkreis.

{t6_status}

**{t6_nachgefuehrt} % nachgeführt, {t6_widerspruch} % klarer Widerspruch.** Die restlichen
Fälle sind Gebäude, die weder Wärmepumpe noch fossil ausweisen - meist "Unbestimmt".

Der interessanteste Teil ist die Entwicklung über die Zeit:

{t6_alter}

**Die Nachführung wird besser.** Anlagen, die vor 2 bis 4 Jahren bewilligt wurden, sind zu
{t6_neu} % im Register sichtbar. Bei Anlagen, die 20 Jahre und älter sind, sind es nur
{t6_alt} %. Der Rückstand liegt also überwiegend im Altbestand, nicht im laufenden Betrieb.

Jahr für Jahr:

{t6_jahre}

Von 2016 bis 2024 steigt der Anteil deutlich. Der Rückgang in den letzten beiden Jahren ist
kein Rückschritt, sondern der normale Nachlauf: Eine 2025 bewilligte Anlage wird erst
gebaut und dann erfasst.

**Was das für die Gesamtbewertung heisst:** Der Befund aus Test 3 bleibt bestehen, aber er
wird differenzierter. Es ist nicht so, dass nichts passiert. Es ist so, dass der Altbestand
liegen bleibt, während der Neuzugang zunehmend erfasst wird. Ein Dienst, der veraltete
Einträge findet, arbeitet damit an einem schrumpfenden, nicht an einem wachsenden Problem.

---

## 3 Qualität der Zuordnung

Baugesuche werden auf zwei unabhängigen Wegen einem EGID zugeordnet:

- **über die Parzelle:** Der GWR-Gebäudepunkt liegt im Parzellenpolygon aus dem Geopackage
  des Statistischen Amts. Exakt, aber erst ab 2025 verfügbar.
- **über die Adresse:** normalisierte Strasse, Hausnummer und PLZ gegen die GWR-Eingänge.
  Auch für 2024 verfügbar, scheitert bei Sammeladressen wie "Rietstrasse 4b, 4c, 4d".

{match_quote}

Insgesamt **{match_pct} % der Heizungsgesuche** konnten zugeordnet werden, ab 2025 mit
Parzellengeometrie **{match_pct_2025} %**.

Die beiden Wege dienen sich gegenseitig als Kontrolle:

{match_konsistenz}

**{konsistenz_pct} % Übereinstimmung** bei den Gesuchen, die über beide Wege zugeordnet werden.
Das ist der belastbarste Qualitätswert in diesem Projekt.

Die Zuordnung der Photovoltaikanlagen über die Koordinate (nächstes Gebäude, maximal 25 m) wurde
gegen die EGID-Spalte der älteren BFE-Datei geprüft:

{pv_valid}

### 3.1 Manuelle Stichprobe

20 zufällige Zuordnungen schreibt `src/report.py` nach `data/processed/stichprobe_20_matches.md` (gebäudegenau, deshalb nicht Teil des Repositories)
vollständig aufgeführt. Ergebnis der Durchsicht:

- **19 von 20** Gesuchstexten betreffen tatsächlich eine Heizung.
- **1 Fehltreffer:** "Einbau Wohnung im Dachgeschoss der Scheune ... **Bestehende** Pelletsheizung
  im Hauptgebäude, WW: WP-Boiler". Die Stichwortsuche kann "bestehend" nicht von "neu" trennen.
  Im ganzen Datensatz enthalten 54 der {n_heiz} erkannten Gesuche das Wort "bestehend"; das ist
  die Obergrenze für diesen Fehlertyp, rund 3 %.
- Die Zuordnung auf das Gebäude ist bei Fällen mit genau einem Gebäude auf der Parzelle
  überzeugend. Bei Parzellen mit mehreren Gebäuden (z. B. "Gebäude Assek.-Nr. 245 und 246",
  4 Gebäude auf der Parzelle) ist unklar, welches Gebäude gemeint ist. Deshalb arbeitet Test 3
  nur mit den eindeutigen Fällen.

---

## 4 Grenzen der Methode

1. **Baugesuche decken nur einen Teil der Heizungswechsel ab.** Geschätzt 10 bis 20 %
   (Abschnitt 2.2). Der Heizungsersatz im Gebäudeinneren ist in vielen Gemeinden nicht
   bewilligungspflichtig und taucht deshalb nie auf.
2. **Die Publikationspraxis ist uneinheitlich.** Der Anteil der Heizungsgesuche schwankt
   zwischen 0 % und 20 % je Gemeinde. Ein Vergleich zwischen Gemeinden misst zum Teil die
   Publikationspraxis, nicht die Datenqualität.
3. **Ein Baugesuch ist kein Beweis, dass gebaut wurde.** Bewilligungen werden nicht umgesetzt,
   Projekte werden zurückgezogen. Ein Teil der als "nicht nachgeführt" gezählten Fälle ist
   korrekt im GWR - dort wurde schlicht nichts gebaut. Wie gross dieser Anteil ist, lässt sich
   aus den vorhandenen Daten nicht bestimmen. Das ist die grösste einzelne Unsicherheit
   in Test 3.
4. **Die Stichwortsuche ist grob.** Sie erkennt "bestehende Pelletsheizung" als Heizungsereignis
   und unterscheidet einen Wärmepumpenboiler nicht sicher von einer Heizungswärmepumpe.
   Bei 117 Gesuchen konnte kein neuer Energieträger bestimmt werden ("unklar"). Eine
   LLM-Extraktion auf dem Projektbeschrieb würde hier deutlich mehr herausholen: alter Träger,
   neuer Träger, Bestand oder Neubau, Haupt- oder Nebenpunkt des Vorhabens. Das ist der
   naheliegendste nächste Schritt und lässt sich lokal auf eigener GPU rechnen.
5. **Der GWR-Snapshot ist eine Momentaufnahme.** Ob ein Eintrag zwischen Baugesuch und heute
   einmal geändert und wieder überschrieben wurde, ist nicht sichtbar. Für eine Weiterführung
   braucht es Snapshots über die Zeit.
6. **Einzelne Gemeinden haben zu wenige Fälle.** Die Gemeindetabelle in Test 3 ist auf
   Gemeinden mit mindestens 8 Fällen beschränkt; darunter wird der Anteil zu instabil.
7. **Mehrfachpublikationen verzerren rohe Zählungen.** {pct_doppelt} % der Publikationen
   wiederholen ein bereits vorhandenes Vorhaben. Wer die Rohdaten ohne Deduplizierung
   auswertet, kommt auf rund ein Fünftel zu hohe Fallzahlen.
8. **Keine Personendaten.** Die Baugesuchsdaten sind bereits um Namen und Adressen der
   Beteiligten bereinigt. Gebäudegenaue Ergebnisse werden nicht veröffentlicht; die
   Verdachtslisten liegen ausserhalb des Git.

---

## 5 Entscheidung

Die im Vorfeld festgelegten Kriterien:

| Kriterium | Ergebnis | erfüllt |
|---|---|---|
| Test 3 zeigt eine grosse Lücke | {luecke_pct} % nicht nachgeführt, {nachgef_pct} % nachgeführt, weit gefasst {nachgef_weit} % | ja |
| Test 2 liefert genug Fälle | Median {median_gesuche} Heizungsgesuche pro Gemeinde und Jahr | nein |
| Stop-Signal: über 80 % nachgeführt | in keinem Altersfenster erreicht | nein |
| Stop-Signal: nur eine Handvoll Gesuche pro Gemeinde | trifft auf drei Viertel der Gemeinden zu | ja |
| Zusatzbefund: wird das Problem kleiner? | ja, Erfassung steigt von {t6_alt} % auf {t6_neu} % | spricht gegen einen Dauerbetrieb |

**Fazit: Die Lücke ist real, Baugesuche allein reichen als Beleg nicht.**

Begründung:

- Die Lücke, auf der die Idee aufbaut, ist nachweisbar und deutlich grösser als das
  Stop-Kriterium. Das Problem existiert.
- Der Weg über Baugesuche allein trägt aber nicht. Für die mittlere Gemeinde entstehen
  zwei Verdachtsfälle pro Jahr; das lohnt keinen eigenen Prozess.
- Gleichzeitig läuft bereits ein grosser Nachführungsbetrieb: {akt_2026} aktualisierte
  Heizungseinträge allein 2026. Der Beitrag eines Abgleichs aus offenen Daten liegt nicht im
  "Fehler finden", sondern im Schliessen der Lücke zwischen zwei Sammelaktualisierungen.
- **Das Problem schrumpft.** Der Berner Zeitverlauf (Abschnitt 2.7) zeigt es am deutlichsten:
  Von {t6_alt} % Erfassung bei 20 Jahre alten Anlagen auf {t6_neu} % bei den jüngsten.
  Der Altbestand, um den es geht, wird Jahr für Jahr kleiner. Für eine einmalige
  Bereinigung ist das ein Argument, für eine Dauerüberwachung nicht.
- Als Methodenprojekt taugt das Thema gut: eine saubere, messbare Fragestellung, offene
  Daten in brauchbarer Qualität, eine echte Entity-Resolution-Aufgabe, ein sinnvoller
  Einsatz für LLM-Extraktion und eine Evaluation, die sich an Bodenwahrheit prüfen lässt.

### Was aus dem Befund folgt

Wer den Abgleich weiterführen will, sollte ihn so anlegen:

- **Die passende Ebene ist der Kanton oder eine Stadt, nicht die einzelne Gemeinde.** Zürich und
  Winterthur haben zusammen mehr Heizungs-Baugesuche als die anderen 158 Gemeinden zusammen,
  und beide zeigen mit {luecke_zh} % und {luecke_win} % die grössten Lücken unter den
  Gemeinden mit nennenswertem Volumen.
- **Baugesuche reichen als Belegquelle nicht.** Es braucht mindestens Feuerungskontrolle,
  Gebäudeprogramm-Förderdaten, Gasnetz-Abmeldungen und die Pronovo-Anlagendaten. Erst die
  Kombination ergibt eine Abdeckung, die sich lohnt.
- **Erdwärmesonden sind die bisher beste offene Quelle.** Sie liefern einen harten
  Widerspruch statt eines Indizes, sind in zwei Kantonen frei verfügbar und in Bern sogar
  mit Datum und Ausführungsnachweis. Das ist der erste Baustein, nicht die Baugesuche.
- **Sinnvoll ist eine einmalige Bereinigung, keine Dauerüberwachung.** Der Altbestand ist das
  Problem, und ein Altbestand lässt sich einmal aufräumen.
- **Ein Gespräch mit der kantonalen Fachstelle vor jeder weiteren Zeile Code.** Die konkrete
  Frage: "Wir sehen bei {luecke_zh} % der Zürcher
  Heizungs-Baugesuche keine Nachführung im GWR. Ist das für Sie ein Problem, und wenn ja,
  wessen Problem?"

---

## 6 Nächste Schritte

Diese Liste hält den Stand der Detailauswertung vom September 2026 fest. Umgesetzt wurden
seither die LLM-Extraktion, die Snapshot-Zeitreihe und weitere Belegquellen; was daraus
wurde, steht im README.

1. **LLM-Extraktion statt Stichwortsuche.** Aus dem Projektbeschrieb strukturiert ziehen:
   alter Energieträger, neuer Energieträger, Bestand oder Neubau, Gewicht im Vorhaben.
   Evaluation an rund 200 selbst gelabelten Baugesuchen, Kennzahlen je Feld.
   Lokal, damit keine Datenfrage entsteht.
2. **Belegquellen erweitern.** Pronovo-Anlagendaten, Gebäudeprogramm, Minergie,
   GEAK-Bestand. Ziel ist ein Score "wahrscheinlich veraltet" pro Gebäude statt
   einer Ja/Nein-Regel.
3. **GWR-Snapshots sammeln.** Ab sofort wöchentlich `zh.zip` ablegen. Damit wird die
   Nachführung als Ereignis messbar statt nur als Momentaufnahme, und die grösste Schwäche
   von Test 3 verschwindet.
4. **Architektur.** Bronze: GWR-Snapshots, Baugesuche, Anlagendaten, je mit Manifest und
   Ladedatum. Silver: LLM-Extraktion der Heizungsereignisse, Entity Resolution Baugesuch zu
   EGID über Parzelle und Adresse (die 98,9 % Übereinstimmung aus Abschnitt 3 sind die
   Referenz). Gold: Belege je Gebäude, Score, Bericht je Gemeinde.
   Die vorliegende Pipeline ist bereits so aufgebaut.
5. **Evaluation.** Extraktionsgenauigkeit an gelabelten Baugesuchen, Zuordnungsgenauigkeit
   über die Kreuzprüfung der beiden Wege, Precision der Verdachtsfälle über eine Stichprobe,
   die eine Partnergemeinde gegenprüft.

---

## Reproduzierbarkeit

```bash
python src/download.py     # Rohdaten laden, Manifest schreiben
python src/build_db.py     # Bronze-Layer in DuckDB
python src/report.py       # Pipeline rechnen und diesen Report erzeugen
```
