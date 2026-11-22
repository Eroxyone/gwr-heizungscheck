# Wie oft ist der Registereintrag wirklich falsch?

Bisher hat dieses Projekt eine Hilfsgrösse gemessen: ob sich zu einem Verdachtsfall ein aktiver fossiler Kessel finden lässt. Wo keiner gefunden wurde, galt der Verdacht als bestätigt. Das ist zu grosszügig - ein Gebäude ohne Kesseleintrag kann auch einfach nicht erfasst sein.

Jetzt gibt es echte Labels. Für jedes auswertbare Gebäude steht fest, ob der GWR-Eintrag zum tatsächlich laufenden Wärmeerzeuger passt.

## GE: Feuerungskataster mit EGID, Brennstoff und Betriebszustand

*sagt auch, WAS stattdessen laeuft*

| Label                |   Gebäude |
|:---------------------|----------:|
| stimmt               |     28242 |
| ungeklaert           |      1871 |
| falscher_traeger     |       489 |
| veraltet_waermepumpe |       410 |
| veraltet_holz        |       248 |
| veraltet_stillgelegt |       196 |
| veraltet_fernwaerme  |       152 |
| veraltet_elektro     |       119 |
| hybrid               |        84 |

Auswertbar sind 29'856 Gebäude. Davon ist der Eintrag bei **1'614 falsch, also 5,4 %.** Das ist die Grundrate, gegen die jeder Beleg antreten muss.

| Beleg | Gebäude | falsch | Anteil | 95 %-Intervall | Faktor |
|---|---:|---:|---:|---|---:|
| kein Beleg | 26'462 | 1'163 | 4,4 % | 4,2 bis 4,6 % | Grundrate |
| Anlage bis 10 m | 1 | 0 | 0,0 % | 0,0 bis 79,3 % | Grundrate |
| Anlage 10 bis 20 m | 2 | 0 | 0,0 % | 0,0 bis 65,8 % | Grundrate |
| Registerwiderspruch | 140 | 6 | 4,3 % | 2,0 bis 9,0 % | 1,0 |
| nur Photovoltaik | 3'251 | 445 | 13,7 % | 12,5 bis 14,9 % | 3,1 |

## GE strikt: derselbe Kataster, aber nur direkte Vergleiche

*ohne die Faelle, bei denen nur die Stilllegung bekannt ist*

Auswertbar sind 29'660 Gebäude. Davon ist der Eintrag bei **1'418 falsch, also 4,8 %.** Das ist die Grundrate, gegen die jeder Beleg antreten muss.

| Beleg | Gebäude | falsch | Anteil | 95 %-Intervall | Faktor |
|---|---:|---:|---:|---|---:|
| kein Beleg | 26'315 | 1'016 | 3,9 % | 3,6 bis 4,1 % | Grundrate |
| Anlage bis 10 m | 1 | 0 | 0,0 % | 0,0 bis 79,3 % | Grundrate |
| Anlage 10 bis 20 m | 2 | 0 | 0,0 % | 0,0 bis 65,8 % | Grundrate |
| Registerwiderspruch | 140 | 6 | 4,3 % | 2,0 bis 9,0 % | 1,1 |
| nur Photovoltaik | 3'202 | 396 | 12,4 % | 11,3 bis 13,6 % | 3,2 |

## ZG: Tankkataster, getrennt nach in und ausser Betrieb

*nur Heizöl, Zuordnung über einen 10-m-Umkreis statt über die EGID*

| Label                |   Gebäude |
|:---------------------|----------:|
| stimmt               |      4042 |
| ungeklaert           |      1518 |
| veraltet_stillgelegt |       388 |

Auswertbar sind 4'430 Gebäude. Davon ist der Eintrag bei **388 falsch, also 8,8 %.** Das ist die Grundrate, gegen die jeder Beleg antreten muss.

| Beleg | Gebäude | falsch | Anteil | 95 %-Intervall | Faktor |
|---|---:|---:|---:|---|---:|
| kein Beleg | 4'026 | 271 | 6,7 % | 6,0 bis 7,5 % | Grundrate |
| Anlage bis 10 m | 44 | 28 | 63,6 % | 48,9 bis 76,2 % | 9,5 |
| Anlage 10 bis 20 m | 65 | 40 | 61,5 % | 49,4 bis 72,4 % | 9,1 |
| Registerwiderspruch | 16 | 1 | 6,2 % | 1,1 bis 28,3 % | 0,9 |
| nur Photovoltaik | 279 | 48 | 17,2 % | 13,2 bis 22,1 % | 2,6 |

## Was eine Gemeinde erlebt

Hier stand bis zur Ueberarbeitung eine Top-K-Kurve mit Prosa dazu. Beides ist entfallen, und der Grund gehoert in den Bericht:

Die Kurve sortierte nach Punktzahl und schnitt bei Rang 20, 100 und 500 ab. Der Score kennt aber nur wenige moegliche Summen - in Genf hatten hunderte Faelle exakt 45 Punkte. Welche zwanzig davon oben landeten, entschied die Sortierung nach Gebaeudenummer. Niedrige Nummer heisst in Genf Innenstadt, Innenstadt heisst Fernwaerme. Die Kurve mass den Tiebreak.

Dazu kam: Gemessen wurde nach Punktzahl, die Liste ordnet nach Belegklasse. Das sind zwei verschiedene Listen, und die Messung galt der falschen.

Beides ist ersetzt durch eine Messung je Belegart und je Listenstufe, ohne Rangfolge und damit ohne Tiebreak. Sie steht in `reports/belegwirkung.md` und ist die Leitzahl des Projekts. Dieser Bericht behaelt die Labelsaetze selbst, also die Frage, WORAN gemessen wird.

## Was diese Messung nicht kann

1. **Das Baugesuch bleibt ungemessen.** In Genf und Zug gibt es keinen einzigen zugeordneten Baugesuchsfall. Ausgerechnet der Beleg, auf dem die ganze Idee steht, laesst sich hier nicht pruefen.
2. **Ungeklaerte Faelle bleiben ungeklaert.** In Genf ist ein Drittel der Gebaeude gar nicht oder nur mit Warmwasseranlagen erfasst. Der Anteil ist zwischen den Belegarten nicht gleich - bei den Anlagenfaellen liegt er hoeher als bei den uebrigen. Eine Verzerrung ist damit nicht ausgeschlossen.
3. **Genf misst den staerksten Beleg nicht mehr.** Sein Bohrungsregister fuehrt fuer fast alle Bohrungen den Status "Inconnu" oder "Exploitable", also eine Einstufung der Ressource statt einer laufenden Anlage. Seit solche Eintraege nicht mehr als Beleg gelten, bleiben in Genf drei pruefbare Faelle.
4. **Ein Kanton ist nicht die Schweiz.** Damit steht die ganze Messung der Liste auf Zug: ein kleiner Kanton, ein Oeltankkataster, 109 pruefbare Faelle. Ob die Quoten in Zuerich gelten, ist offen - dazu braucht es eine Prüfung durch eine Zürcher Gemeinde.
