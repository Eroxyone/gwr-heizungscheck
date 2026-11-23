# Labels aus Genf und Zug: Wie oft ist der Registereintrag falsch?

Registerstand 14.09.2026. Der Bericht beschreibt die Labelsätze, an denen die Verdachtsfälle gemessen werden: Für jedes auswertbare Gebäude in Genf und Zug steht fest, ob der GWR-Eintrag zum Wärmeerzeuger passt, den eine kantonale Gegenquelle ausweist. Der Bericht ist eine Vorstufe: Die Messung je Belegart und Listenstufe steht in [belegwirkung.md](belegwirkung.md).

Ein Label ist strenger als die Hilfsgrösse aus [precision.md](precision.md). Dort gilt ein Verdacht schon als gestützt, wenn sich kein aktiver fossiler Kessel findet. Ein Gebäude ohne Kesseleintrag kann aber auch nicht erfasst sein; hier gilt es deshalb als ungeklärt.

Der Faktor in den Tabellen bezieht sich auf die Gebäude ohne Beleg (erste Zeile). In [belegwirkung.md](belegwirkung.md) bezieht er sich auf die Grundrate aller auswertbaren Gebäude; die Faktoren der beiden Berichte sind deshalb nicht gleich.

## GE: Feuerungskataster mit EGID, Brennstoff und Betriebszustand

*nennt auch den Wärmeerzeuger, der stattdessen läuft*

| Label                                    |   Gebäude |
|:-----------------------------------------|----------:|
| stimmt                                   |     28242 |
| ungeklärt                                |      1871 |
| falscher fossiler Träger                 |       489 |
| veraltet, jetzt Wärmepumpe               |       410 |
| veraltet, jetzt Holz                     |       248 |
| veraltet, Feuerung oder Tank stillgelegt |       196 |
| veraltet, jetzt Fernwärme                |       152 |
| veraltet, jetzt Elektroheizung           |       119 |
| hybrid (fossil und erneuerbar zugleich)  |        84 |

Auswertbar sind 29'856 Gebäude. Davon ist der Eintrag bei **1'614 falsch, also 5,4 %.** Das ist die Grundrate.

| Beleg | Gebäude | falsch | Anteil | 95 %-Intervall | Faktor |
|---|---:|---:|---:|---|---:|
| kein Beleg | 26'462 | 1'163 | 4,4 % | 4,2 bis 4,6 % | Bezugswert |
| Anlage bis 10 m | 1 | 0 | 0,0 % | 0,0 bis 79,3 % | 0,0 |
| Anlage 10 bis 20 m | 2 | 0 | 0,0 % | 0,0 bis 65,8 % | 0,0 |
| Registerwiderspruch | 140 | 6 | 4,3 % | 2,0 bis 9,0 % | 1,0 |
| nur Photovoltaik | 3'251 | 445 | 13,7 % | 12,5 bis 14,9 % | 3,1 |

## GE strikt: derselbe Kataster, aber nur direkte Vergleiche

*ohne die Fälle, bei denen nur die Stilllegung bekannt ist*

Auswertbar sind 29'660 Gebäude. Davon ist der Eintrag bei **1'418 falsch, also 4,8 %.** Das ist die Grundrate.

| Beleg | Gebäude | falsch | Anteil | 95 %-Intervall | Faktor |
|---|---:|---:|---:|---|---:|
| kein Beleg | 26'315 | 1'016 | 3,9 % | 3,6 bis 4,1 % | Bezugswert |
| Anlage bis 10 m | 1 | 0 | 0,0 % | 0,0 bis 79,3 % | 0,0 |
| Anlage 10 bis 20 m | 2 | 0 | 0,0 % | 0,0 bis 65,8 % | 0,0 |
| Registerwiderspruch | 140 | 6 | 4,3 % | 2,0 bis 9,0 % | 1,1 |
| nur Photovoltaik | 3'202 | 396 | 12,4 % | 11,3 bis 13,6 % | 3,2 |

## ZG: Tankkataster, getrennt nach in und ausser Betrieb

*nur Heizöl, Zuordnung über einen 10-m-Umkreis statt über die EGID*

| Label                                    |   Gebäude |
|:-----------------------------------------|----------:|
| stimmt                                   |      4042 |
| ungeklärt                                |      1518 |
| veraltet, Feuerung oder Tank stillgelegt |       388 |

Auswertbar sind 4'430 Gebäude. Davon ist der Eintrag bei **388 falsch, also 8,8 %.** Das ist die Grundrate.

| Beleg | Gebäude | falsch | Anteil | 95 %-Intervall | Faktor |
|---|---:|---:|---:|---|---:|
| kein Beleg | 4'026 | 271 | 6,7 % | 6,0 bis 7,5 % | Bezugswert |
| Anlage bis 10 m | 44 | 28 | 63,6 % | 48,9 bis 76,2 % | 9,5 |
| Anlage 10 bis 20 m | 65 | 40 | 61,5 % | 49,4 bis 72,4 % | 9,1 |
| Registerwiderspruch | 16 | 1 | 6,2 % | 1,1 bis 28,3 % | 0,9 |
| nur Photovoltaik | 279 | 48 | 17,2 % | 13,2 bis 22,1 % | 2,6 |

## Messung je Belegart statt entlang einer Rangfolge

Eine Auswertung entlang der Rangfolge nach Punktzahl (Trefferquote der obersten 20, 100 oder 500 Fälle) enthält dieser Bericht nicht. Der Score kennt nur wenige mögliche Summen, viele Fälle teilen dieselbe Punktzahl, und innerhalb gleicher Punktzahl entscheidet die Sortierung nach Gebäudenummer. Ein Rangschnitt misst dann diese Sortierung. Zudem ordnet die Verdachtsliste nach Stufe und Belegklasse, nicht nach Punktzahl.

Die Messung je Belegart und je Listenstufe steht in [belegwirkung.md](belegwirkung.md). Dieser Bericht dokumentiert die Labelsätze, also woran gemessen wird.

## Was diese Messung nicht kann

1. **Das Baugesuch bleibt ungemessen.** In Genf und Zug gibt es keinen zugeordneten Baugesuchsfall mit Label. Der Beleg, von dem die Studie ausgeht, lässt sich hier nicht prüfen.
2. **Ungeklärte Fälle bleiben ungeklärt.** Ein Teil der Gebäude ist in den Gegenquellen nicht oder nur mit Warmwasseranlagen erfasst (Label "ungeklärt" in den Tabellen oben). Der Anteil ist zwischen den Belegarten nicht gleich: In Zug liegt er bei Gebäuden mit Beleg höher als bei Gebäuden ohne ([belegwirkung.md](belegwirkung.md)). Eine Verzerrung ist damit nicht ausgeschlossen.
3. **Genf misst den Anlagenbeleg nicht.** Das Genfer Bohrungsregister führt für fast alle Bohrungen den Status "Inconnu" oder "Exploitable", also eine Einstufung der Ressource statt einer laufenden Anlage. Solche Einträge gelten nicht als Beleg. In Genf bleiben 3 prüfbare Anlagenfälle.
4. **Ein Kanton ist nicht die Schweiz.** Die Messung des Anlagenbelegs beruht damit auf Zug: ein kleiner Kanton, ein Öltankkataster, 109 prüfbare Fälle mit Anlagenbeleg. Ob die Quoten in Zürich gelten, ist offen; klären liesse sich das nur durch eine Prüfung vor Ort.
