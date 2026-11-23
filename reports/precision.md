# Vorstufe: Gegenprobe der Verdachtsfälle an Feuerungs- und Tankkataster

> **Dieser Bericht ist eine Vorstufe, Registerstand 14.09.2026.** Er misst, ob sich zu einem Verdachtsfall noch ein aktiver fossiler Kessel oder Tank finden lässt, also eine Hilfsgrösse. Wie oft der Registereintrag tatsächlich falsch ist, beantwortet [belegwirkung.md](belegwirkung.md). Wo die beiden Berichte verschiedene Zahlen nennen, gilt belegwirkung.md.

Alle Belege dieser Studie zeigen in dieselbe Richtung: Hier ist eine Wärmepumpe gebaut, hier eine Sonde gebohrt, hier ein Baugesuch publiziert. Keiner davon sagt, ob die alte Ölheizung daneben **noch läuft**. Ein Verdachtsfall ist aber nur dann ein Fehler im Register, wenn der fossile Eintrag nicht mehr stimmt.

Zwei Kantone erlauben die Gegenprobe, mit verschiedenen Datensätzen:

- **GE, Feuerungskataster**: 55'372 Kessel mit EGID, Brennstoff, Betriebszustand und Baujahr
- **ZG, Tankkataster**: 8'319 Heizöltanks in vier Layern, getrennt nach Betriebszustand (nur gegen Einträge mit Energieträger Heizöl ausgewertet)

Beide Messungen zeigen dieselbe Rangfolge der Belegarten.

## GE: Feuerungskataster

Von den fossil eingetragenen Wohngebäuden in GE stehen 24'566 auch in dieser Quelle. Bei **81,7 %** von ihnen läuft dort noch eine fossile Heizung. Das ist die Grundrate.

| Beleg               |   Fälle |   geprüft |   fossil läuft noch % |
|:--------------------|--------:|----------:|----------------------:|
| Wärmenutzungsanlage |       3 |         3 |                  66,7 |
| nur Photovoltaik    |    3475 |      3011 |                  74,7 |
| Registerwiderspruch |     146 |       119 |                  86,6 |

Stärkster Beleg: **Wärmenutzungsanlage** mit 66,7 %, also 15,0 Prozentpunkte unter der Grundrate.

Über der Grundrate liegt **Registerwiderspruch** mit 86,6 %, gemessen an 119 geprüften Fällen. Diese Belegart findet hier eher Gebäude, bei denen der fossile Eintrag stimmt.

Der Gegenbeleg nimmt 2'365 Fälle aus der Sicht `v_gold_verdacht`, 1'259 bleiben.

## ZG: Tankkataster

Von den fossil eingetragenen Wohngebäuden in ZG stehen 4'430 auch in dieser Quelle. Bei **91,2 %** von ihnen läuft dort noch eine fossile Heizung. Das ist die Grundrate.

| Beleg               |   Fälle |   geprüft |   fossil läuft noch % |
|:--------------------|--------:|----------:|----------------------:|
| Wärmenutzungsanlage |     173 |       109 |                  37,6 |
| nur Photovoltaik    |     408 |       279 |                  82,8 |
| Registerwiderspruch |      32 |        16 |                  93,8 |

Stärkster Beleg: **Wärmenutzungsanlage** mit 37,6 %, also 53,6 Prozentpunkte unter der Grundrate.

Über der Grundrate liegt **Registerwiderspruch** mit 93,8 %, gemessen an 16 geprüften Fällen. Diese Belegart findet hier eher Gebäude, bei denen der fossile Eintrag stimmt. Die Fallzahl ist für eine belastbare Aussage zu klein.

Der Gegenbeleg nimmt 287 Fälle aus der Sicht `v_gold_verdacht`, 666 bleiben.

## Was beide Messungen gemeinsam sagen

1. **Die Auswahl wirkt, trennt aber nicht sauber.** Der beste Beleg drückt den Anteil noch laufender fossiler Heizungen um 15,0 bis 53,6 Prozentpunkte unter die Grundrate. Über alle Belegarten zusammen trägt die Mehrheit der ausgewählten Gebäude weiterhin einen aktiven fossilen Gegenbeleg.
2. **Die Wärmenutzungsanlage ist der stärkste verfügbare Beleg**, in beiden Kantonen. Photovoltaik liegt dahinter, wirkt aber messbar, und ist der einzige Beleg, den es in allen 26 Kantonen gibt.
3. **Der Registerwiderspruch liegt in beiden Kantonen über der Grundrate**, beruht dort aber auf wenigen geprüften Fällen. Der Untertyp, der im Score Punkte gibt (Wärmeerzeuger "Wärmepumpe" bei Energieträger "Heizöl"), kommt in Genf und Zug nicht vor. Gemessen sind nur die Warmwasser-Untertypen Fernwärme, Erdwärme und Luft. Über den Erzeuger-Widerspruch sagt diese Messung nichts.

**Zur Formulierung.** Gemessen ist: Ausgewählte Gebäude tragen seltener einen **aktiven fossilen Gegenbeleg** als der Vergleichsbestand. Das ist nicht dasselbe wie "der GWR-Eintrag ist falsch": Ein Gebäude ohne Kessel- oder Tankeintrag kann auch nicht erfasst sein. Eine Aussage wie "der Anteil veralteter Einträge ist doppelt so hoch" geht deshalb über diese Messung hinaus.

## Grenzen dieser Messung

1. **Zwei Kantone sind nicht die Schweiz.** Genf hat den höchsten Anteil "unbestimmt" im GWR und eine sehr tiefe Wärmepumpendichte, Zug ist klein und dicht bebaut. Die Zahlen sind eine Grössenordnung.
2. **Eine Gegenquelle gilt nur für den Brennstoff, den sie kennt.** Ein stillgelegter Öltank widerlegt keine Gasheizung. Zug wird deshalb nur gegen Öl-Einträge gerechnet. Gegen alle fossilen Einträge gerechnet, mischen sich 4'430 Öl-Einträge (91,2 % mit aktivem Tank) mit 554 Gas-Einträgen (26,4 %) zu einer irreführenden Grundrate von 84,0 %.
3. **Die Gegenquellen sind selbst nicht fehlerfrei.** Ein Kessel gilt als aktiv und ein Tank als in Betrieb, bis jemand die Stilllegung meldet. Wo zwei amtliche Register sich widersprechen, lässt sich aus den Daten allein nicht sagen, welches recht hat.
4. **Eine Zentralheizung kann mehrere Gebäude versorgen.** Genf führt dazu eine eigene Beziehungstabelle mit 2'587 Einträgen; dieser Bericht nutzt sie nicht. Der Zuger Tankkataster wird über einen 10-m-Umkreis zugeordnet, nicht über eine Gebäudenummer.
5. **Hybridanlagen sind keine Widersprüche.** Ein Genfer Kessel "en réserve" neben einer Wärmepumpe ist der Normalfall und zählt weder als Beleg noch als Gegenbeleg.

## Einordnung

Diese Messung ersetzt die Prüfung vor Ort nicht. Die Messung an Labels steht in [belegwirkung.md](belegwirkung.md), die Messung an den späteren Korrekturen im Register in [zeitreihe.md](zeitreihe.md).
