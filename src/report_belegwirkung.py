"""Was ist ein Beleg wert - und gilt das auch dort, wo die Liste benutzt werden soll?

Dieser Bericht ersetzt die Top-K-Kurve aus reports/precision.md als Leitzahl des
Projekts. Der Grund steht ausfuehrlich in sql/belegwirkung.sql: Die Kurve wurde von
einem zufaelligen Tiebreak erzeugt, weil auf den obersten Raengen hunderte Faelle
denselben Score hatten und die Sortierung nach EGID entschied, welche zwanzig oben
landen. In Genf heisst niedrige EGID Innenstadt, Innenstadt heisst Fernwaerme - und
schon steht eine Trefferquote von 70 Prozent im Bericht, die nichts misst.

Je Belegart gemessen gibt es dieses Problem nicht: ein Topf, eine Quote, kein Rang.

Zwei Dinge macht dieser Bericht ausserdem, die vorher fehlten:

  1. Er trennt, WORAN ein Beleg gemessen wurde. Genfs Bohrungsregister fuehrt 3'668
     Bohrungen, davon 145 mit dem Status "in Betrieb". Der Rest ist eine Einstufung
     der Ressource. Wer damit misst, misst nicht dieselbe Sache wie in Zug.
  2. Er rechnet vor, was in Zuerich davon uebrig bleibt. Zug ordnet ueber amtliche
     EGID zu, Zuerich kann das nicht. Also wird dieselbe Zuger Messung noch einmal
     mit dem Zuercher Verfahren gerechnet.

    python src/report_belegwirkung.py
"""
from __future__ import annotations

import argparse
from datetime import date
from math import sqrt

import config
import fmt
import pipeline

ZIEL = config.ROOT / "reports" / "belegwirkung.md"


def wilson(treffer: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Vertrauensbereich fuer einen Anteil.

    Bei n = 11 und null Treffern ist der naive Anteil 0 Prozent - eine Zahl, die
    Sicherheit vortaeuscht, wo keine ist. Wilson sagt stattdessen: irgendwo zwischen
    0 und 26 Prozent. Genau dieser Unterschied hat in diesem Projekt fast zu einem
    falschen Urteil ueber den staerksten Beleg gefuehrt.
    """
    if n == 0:
        return (0.0, 0.0)
    p = treffer / n
    nenner = 1 + z * z / n
    mitte = (p + z * z / (2 * n)) / nenner
    rand = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / nenner
    return (max(0.0, 100 * (mitte - rand)), min(100.0, 100 * (mitte + rand)))


def _mit_ci(df, spalte_n="n", spalte_treffer="falsch"):
    unten, oben = [], []
    for _, r in df.iterrows():
        u, o = wilson(int(r[spalte_treffer]), int(r[spalte_n]))
        unten.append(round(u, 1))
        oben.append(round(o, 1))
    df = df.copy()
    df["von_%"] = unten
    df["bis_%"] = oben
    return df


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    con = pipeline.connect(schreibend=False)

    wirkung = con.execute("""
        SELECT label_kanton AS kanton, belegart, n, falsch, praezision, grundrate, faktor
        FROM v_belegwirkung WHERE n >= 5
        ORDER BY label_kanton, praezision DESC""").df()
    umkreis = con.execute("""
        SELECT eindeutigkeit, distanz, n, falsch, praezision
        FROM v_zg_umkreis_wirkung ORDER BY eindeutigkeit, distanz DESC""").df()
    aufbau = con.execute("""
        SELECT kanton, belegart, faelle, stark, gemeinden FROM v_listenaufbau
        WHERE faelle >= 5 ORDER BY kanton, faelle DESC""").df()
    liefer = con.execute("""
        SELECT kanton, konfidenz, n, falsch, praezision, grundrate, faktor
        FROM v_verdachtsliste_wirkung ORDER BY kanton,
             list_position(['reihenfolge belegt', 'reihenfolge plausibel', 'eintrag alt', 'eintrag jung'], konfidenz)""").df()
    liefer_gesamt = con.execute("""
        SELECT l.label_kanton AS kanton, count(*) AS n,
               sum(l.eintrag_falsch::INT) AS falsch,
               round(100.0 * avg(l.eintrag_falsch::INT), 1) AS praezision
        FROM v_gold_score s JOIN v_label_alle l USING (egid)
        WHERE s.konfidenz IN ('reihenfolge belegt', 'reihenfolge plausibel', 'eintrag alt', 'eintrag jung')
        GROUP BY 1 ORDER BY n DESC""").df()
    ungeklaert = con.execute("""
        SELECT CASE WHEN s.egid IS NULL THEN 'kein Beleg'
                    WHEN s.konfidenz IN ('reihenfolge belegt', 'reihenfolge plausibel', 'eintrag alt', 'eintrag jung')
                         THEN 'auf der Verdachtsliste'
                    WHEN s.hat_pv THEN 'nur Photovoltaik'
                    ELSE 'sonstiger Beleg' END                  AS gruppe,
               count(*)                                         AS n,
               sum((l.label = 'ungeklaert')::INT)               AS ungeklaert,
               round(100.0 * avg((l.label = 'ungeklaert')::INT), 1) AS anteil
        FROM v_zg_label l LEFT JOIN v_gold_score s USING (egid)
        GROUP BY 1 ORDER BY anteil DESC""").df()
    status = con.execute("""
        SELECT kanton, coalesce(status, '(kein Statusfeld)') AS status,
               count(*) AS anlagen,
               sum(belegt_anlage::INT) AS zaehlt_als_beleg
        FROM silver_waermenutzung GROUP BY 1, 2
        HAVING sum(belegt_anlage::INT) <> count(*) OR count(*) > 500
        ORDER BY 1, 3 DESC""").df()

    text = f"""# Was ein Beleg wert ist

Stand {date.today().strftime('%d.%m.%Y')}. Gemessen an zwei kantonalen Gegenquellen:
dem Genfer Waermeerzeuger-Layer (61'895 Anlagen mit EGID, darunter 9'615 Waermepumpen
und 3'181 Fernwaerme-Uebergabestationen) und dem Zuger Tankkataster (nur Oel).

## Warum dieser Bericht die Top-K-Kurve ersetzt

Der frueher berichtete Wert "die obersten 20 Raenge treffen zu 70 Prozent" war ein
Artefakt. Der Score kennt nur wenige mögliche Summen; in Genf hatten hunderte Faelle
exakt 45 Punkte, und welche davon auf den Raengen 13 bis 20 landeten, entschied die
Sortierung nach EGID. Niedrige EGID heisst in Genf Innenstadt, Innenstadt heisst
Fernwaerme. Die Zahl mass den Tiebreak, nicht das Verfahren.

Je Belegart gibt es keine Rangfolge und damit keinen Tiebreak. Die Quoten unten sind
reproduzierbar.

## Trefferquote je Belegart

"Falsch" heisst: Die Gegenquelle zeigt einen anderen Waermeerzeuger als das Register.
"Faktor" ist der Abstand zur Grundrate desselben Kantons - das ist die Zahl, die zaehlt.
Der Vertrauensbereich ist Wilson, 95 Prozent.

{fmt.md(_mit_ci(wirkung))}

## Der Status der Anlage entscheidet, nicht der Kanton

Eine erste Fassung mass in Genf 2 Treffer auf 30 Faelle und in Zug 40 auf 51 - und
haette beinahe zum Schluss gefuehrt, das Verfahren sei nicht uebertragbar. Der
Unterschied lag woanders: Alle 30 Genfer Faelle hingen an Bohrungen mit Status
"Exploitable" oder "Inconnu". Das ist eine Einstufung der Ressource, keine laufende
Anlage.

Die Zuger Gegenprobe ist dagegen gemischt, und das gehoert genannt: 24 der 51 Faelle
tragen "in Betrieb" (22 davon treffen zu), 27 tragen "unbekannt" (18 treffen zu). Eine
frueher hier stehende Behauptung, alle 51 seien betriebsbestaetigt, war falsch. Der Statusunterschied erklaert den Genfer Ausfall
trotzdem: "unbekannt" heisst in Zug, dass der Kanton den Betriebszustand nicht fuehrt,
waehrend "Exploitable" in Genf ausdruecklich sagt, dass hier nur gebohrt werden
KOENNTE.

Seitdem zaehlt eine Anlage nur noch als Beleg, wenn ihr Status eine laufende oder
entstehende Waermepumpe belegt. Genf verliert damit fast seinen ganzen Bestand an
pruefbaren Anlagenfaellen - und damit die Faehigkeit, diesen Beleg zu messen. Das ist
kein Verlust an Substanz, sondern die Korrektur einer Scheinmessung.

{fmt.md(status)}

Zuerich, Schwyz und Zuerichs Nachbarn fuehren gar kein Statusfeld. Dort gelten alle
veroeffentlichten Anlagen als bestehend - eine Annahme, die nicht geprueft werden kann
und offengelegt gehoert.

## Die Verdachtsliste selbst

Die Tabelle oben misst Belegarten. Benutzt wird aber eine Liste, und die ist eine
Auswahl aus mehreren Belegarten in einer bestimmten Reihenfolge. Deshalb dasselbe noch
einmal fuer genau das, was in der Mappe steht:

{fmt.md(_mit_ci(liefer_gesamt))}

Und je Stufe, so wie sie in der Mappe benannt sind:

{fmt.md(_mit_ci(liefer))}

Der eigentliche Befund ist, was NICHT in dieser Tabelle steht. Die Stufe "Beleg aelter
als der Eintrag" fehlt, weil sie seit einer Korrektur gar nicht mehr auf der Liste steht:
Sie traf in Zug in 4 von 30 Faellen zu, also fast auf Grundratenniveau. Uebrig bleibt
eine Liste, deren Stufen sich in der Trefferquote kaum noch unterscheiden - der Filter
hat die Arbeit getan, die vorher die Stufen tun mussten.

Nicht die Belegart trennt am staerksten, sondern die Reihenfolge: Ein Beleg sagt, dass
am Gebaeude etwas an der Heizung geschehen ist. Ob das im Register steht, haengt daran,
ob jemand das Register danach noch angefasst hat.

Genf steht in dieser Tabelle nicht mehr sinnvoll: Nach dem Statusfilter bleiben dort
drei pruefbare Faelle. Das ist keine Messung und wird auch nicht als eine ausgewiesen.

## Was davon in Zuerich uebrig bleibt

Zug ordnet seine Anlagen ueber die amtliche EGID oder die Adresse zu - der Kanton sagt
also selbst, zu welchem Gebaeude die Sonde gehoert. Zuerich liefert das nicht: 38'553
Bohrungen ohne EGID, ohne Adresse, ohne Status. Dort bleibt nur der 20-Meter-Umkreis.

Deshalb dieselbe Zuger Messung noch einmal, aber ausschliesslich ueber den Umkreis -
also mit dem Verfahren, das in Zuerich laufen wuerde:

{fmt.md(_mit_ci(umkreis))}

Das Ergebnis ist der wichtigste Satz dieses Berichts: **Die Eindeutigkeit des Umkreises
entscheidet.** Liegt genau ein Gebaeude im 20-Meter-Umkreis der Anlage, trifft der
Verdacht in rund vier von fuenf Faellen zu - auch ohne amtliche Zuordnung. Liegen drei
oder mehr Gebaeude darin, faellt die Quote auf das Niveau der Grundrate.

Die Zuercher Liste enthaelt ausschliesslich Faelle mit genau einem Gebaeude im Umkreis.

## Woraus die Listen bestehen

Ein Bauamt darf erwarten, dass wir sagen, worauf SEINE Liste beruht.

{fmt.md(aufbau)}

## Die unbequeme Zahl: wer aus der Messung faellt

Gemessen werden kann nur, wozu der Tankkataster etwas sagt. Wo er gar keinen Tank kennt,
gilt der Fall als ungeklaert und faellt heraus. Das ist nicht gleichmaessig verteilt:

{fmt.md(ungeklaert)}

Gebaeude mit einem Beleg fallen haeufiger aus der Messung als Gebaeude ohne - rund ein
Drittel gegenueber einem Viertel. Beide Lesarten sind moeglich, und keine laesst sich
mit diesen Daten entscheiden:

- **Zugunsten der Liste:** Wer von Oel auf eine Waermepumpe wechselt, laesst den Tank
  ausbauen. Gebaeude ohne jeden Tankeintrag waeren dann ueberdurchschnittlich oft
  genau die gesuchten Faelle - und die gemessene Quote waere zu tief.
- **Zuungunsten der Liste:** Der Kataster fuehrt stillgelegte Tanks ausdruecklich
  weiter (388 Stueck). "Kein Tank" heisst dann eher "nie erfasst", und die
  Herausgefallenen sind eine Mischung wie alle anderen auch.

Dazu kommt eine zweite Luecke derselben Art: Ein Fuenftel der Verdachtsliste sind
Gaseintraege, und ein Oeltankkataster sagt ueber Gas nichts. Auch sie sind ungeprueft.

Festhalten laesst sich nur: Ein erheblicher Teil der Faelle auf der Verdachtsliste ist in
Zug nicht pruefbar, und dieser Anteil ist hoeher als bei Gebaeuden ohne Beleg. Wer die
gemessene Quote zitiert, muss diesen Satz mitzitieren.

## Was ungemessen bleibt

Das Baugesuch ist der Beleg, der den neuen Energietraeger im Klartext nennt und datiert
ist - und der einzige, fuer den es keine einzige Messung gibt. In Genf und Zug ist kein
einziger Baugesuchsfall zugeordnet, weil beide Kantone nicht im Amtsblatt-Abzug mit
verwertbarem Objektbeschrieb liegen. Die 228 schweizweiten Faelle mit Baugesuch-Beleg
stehen also auf einer Annahme, nicht auf einer Messung. Das gehoert zu jeder Liste dazu.
"""
    ZIEL.write_text(fmt.de(text), encoding="utf-8")
    print(f"{ZIEL} geschrieben")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
