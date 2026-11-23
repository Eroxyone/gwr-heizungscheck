"""Belegwirkung: Wie oft ist der Registereintrag falsch, wenn ein Beleg vorliegt?

Gemessen wird je Belegart und je Stufe der Verdachtsliste, nicht entlang einer Rangfolge
nach Punktzahl. Der Score kennt nur wenige Summen, viele Faelle teilen dieselbe Punktzahl,
und innerhalb gleicher Punktzahl entscheidet die Sortierung nach EGID. Ein Rangschnitt
(Top-K) misst dann diese Sortierung. Die Herleitung steht in sql/belegwirkung.sql.

Der Bericht trennt ausserdem zwei Dinge:

  1. Woran ein Beleg gemessen wird. Genfs Bohrungsregister fuehrt 3'668 Bohrungen, davon
     145 mit einem Status, der einen Betrieb belegt. Der Rest ist eine Einstufung der
     Ressource und zaehlt nicht als Beleg.
  2. Was davon auf Zuerich uebertragbar ist. Zug ordnet ueber amtliche EGID zu, Zuerich
     kann das nicht. Deshalb wird dieselbe Zuger Messung noch einmal nur ueber den
     Umkreis gerechnet.

    python src/report_belegwirkung.py
"""
from __future__ import annotations

import argparse
from math import sqrt

import config
import fmt
import pipeline

ZIEL = config.ROOT / "reports" / "belegwirkung.md"

# Stufen, mit denen ein Fall auf der Verdachtsliste steht (v_gold_liste).
STUFEN = "('reihenfolge belegt', 'reihenfolge plausibel', 'eintrag alt', 'eintrag jung')"

# Spaltentitel der Tabellen. Die Sichten liefern technische Namen.
KOPF = {
    "kanton": "Kanton", "belegart": "Belegart", "n": "Fälle", "falsch": "davon falsch",
    "praezision": "Trefferquote %", "grundrate": "Grundrate %", "faktor": "Faktor",
    "von_%": "von %", "bis_%": "bis %", "status": "Status", "anlagen": "Anlagen",
    "zaehlt_als_beleg": "zählt als Beleg", "konfidenz": "Stufe",
    "eindeutigkeit": "Eindeutigkeit", "distanz": "Distanz", "faelle": "Fälle",
    "stark": "davon Reihenfolge belegt", "gemeinden": "Gemeinden", "gruppe": "Gruppe",
    "ungeklaert": "ungeklärt", "anteil": "Anteil %",
}
STUFE_TXT = {
    "reihenfolge belegt": "Reihenfolge belegt",
    "reihenfolge plausibel": "Reihenfolge plausibel",
    "eintrag alt": "Eintrag alt", "eintrag jung": "Eintrag jung",
}
# Zwei Kantone tragen diesen Status ohne Umlaut (gesetzt in sql/test5.sql).
STATUS_TXT = {"Bohrung ausgefuehrt": "Bohrung ausgeführt"}


def wilson(treffer: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Vertrauensbereich fuer einen Anteil nach Wilson.

    Bei kleinen Fallzahlen ist der blosse Anteil irrefuehrend: null Treffer auf elf Faelle
    sind nicht 0 Prozent, sondern irgendwo zwischen 0 und 26 Prozent.
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


def _tab(df, **eigene) -> str:
    """Markdown-Tabelle mit lesbaren Spaltentiteln und Zellwerten."""
    df = df.copy()
    if "konfidenz" in df.columns:
        df["konfidenz"] = df["konfidenz"].replace(STUFE_TXT)
    if "status" in df.columns:
        df["status"] = df["status"].replace(STATUS_TXT)
    return fmt.md(df.rename(columns={**KOPF, **eigene}))


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    con = pipeline.connect(schreibend=False)

    # Registerstand der ausgewerteten Faelle, nicht das Datum des Laufs
    stand = con.execute("SELECT max(stand) FROM gold_belege").fetchone()[0]
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
    liefer_gesamt = con.execute(f"""
        SELECT l.label_kanton AS kanton, count(*) AS n,
               sum(l.eintrag_falsch::INT) AS falsch,
               round(100.0 * avg(l.eintrag_falsch::INT), 1) AS praezision
        FROM v_gold_score s JOIN v_label_alle l USING (egid)
        WHERE s.konfidenz IN {STUFEN}
        GROUP BY 1 ORDER BY n DESC""").df()
    ungeklaert = con.execute(f"""
        SELECT CASE WHEN s.egid IS NULL THEN 'kein Beleg'
                    WHEN s.konfidenz IN {STUFEN} THEN 'mit Listenstufe'
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

    # Zuger Fallzahlen fuer die Ueberleitung: Faelle mit Listenstufe vor dem
    # Gegenbeleg-Filter (v_gold_score), davon Gas, Oel und mit Tank in Betrieb.
    zg_stufe, zg_gas, zg_oel, zg_tank_aktiv = con.execute(f"""
        SELECT count(*), count(*) FILTER (WHERE energie_klasse = 'gas'),
               count(*) FILTER (WHERE energie_klasse = 'oel'),
               count(*) FILTER (WHERE kessel_aktiv)
        FROM v_gold_score WHERE kanton = 'ZG' AND konfidenz IN {STUFEN}""").fetchone()
    vor_n, vor_falsch = con.execute("""
        SELECT count(*), coalesce(sum(l.eintrag_falsch::INT), 0)
        FROM v_gold_score s JOIN v_label_alle l USING (egid)
        WHERE l.label_kanton = 'ZG' AND s.konfidenz = 'beleg vor eintrag'""").fetchone()
    liste_n, liste_gas, liste_baugesuch = con.execute("""
        SELECT count(*), count(*) FILTER (WHERE energie_klasse = 'gas'),
               count(*) FILTER (WHERE hat_baugesuch)
        FROM v_gold_liste""").fetchone()
    zg_stillgelegt = con.execute("""
        SELECT count(*) FROM v_zg_label WHERE label = 'veraltet_stillgelegt'""").fetchone()[0]
    ge_stufe = con.execute(f"""
        SELECT count(*) FROM v_gold_score s JOIN v_label_alle l USING (egid)
        WHERE l.label_kanton = 'GE' AND s.konfidenz IN {STUFEN}""").fetchone()[0]

    zg = liefer_gesamt[liefer_gesamt["kanton"] == "ZG"]
    zg_pruefbar = int(zg["n"].iloc[0]) if len(zg) else 0
    zg_falsch = int(zg["falsch"].iloc[0]) if len(zg) else 0
    stufe_oel = ungeklaert[ungeklaert["gruppe"] == "mit Listenstufe"]
    zg_ungeklaert = int(stufe_oel["ungeklaert"].iloc[0]) if len(stufe_oel) else 0
    t = fmt.tsd
    ueberleitung = "\n".join([
        "| Zuger Fälle | Anzahl |",
        "|---|---:|",
        f"| mit Listenstufe, Öl- und Gaseinträge (`v_gold_score`) | {t(zg_stufe)} |",
        f"| davon Gaseinträge, am Tankkataster nicht prüfbar | {t(zg_gas)} |",
        f"| davon Öleinträge | {t(zg_oel)} |",
        f"| Öleinträge ohne Tank im Kataster (ungeklärt) | {t(zg_ungeklaert)} |",
        f"| Öleinträge mit Tank im Kataster (prüfbar) | {t(zg_pruefbar)} |",
        f"| davon Eintrag falsch (Tank ausser Betrieb) | {t(zg_falsch)} |",
        f"| davon Eintrag stimmt (Tank in Betrieb) | {t(zg_pruefbar - zg_falsch)} |",
        f"| auf der Verdachtsliste (`v_gold_liste`: mit Listenstufe, ohne Tank in Betrieb) "
        f"| {t(zg_stufe - zg_tank_aktiv)} |",
    ])

    text = f"""# Belegwirkung: Trefferquote der Verdachtsfälle je Belegart

Registerstand {stand.strftime('%d.%m.%Y')}. Gemessen wird, wie oft der Registereintrag falsch
ist, wenn zu einem Gebäude ein Beleg vorliegt: je Belegart und für die Verdachtsliste.
Gegenquellen sind der Genfer Wärmeerzeuger-Layer (61'895 Anlagen mit EGID, darunter 9'615
Wärmepumpen und 3'181 Fernwärme-Übergabestationen) und der Zuger Tankkataster (nur Heizöl).

## Warum je Belegart und nicht nach Rang gemessen wird

Der Verdachtsscore kennt nur wenige mögliche Summen, und viele Fälle teilen dieselbe
Punktzahl, in Genf mehrere hundert. Bei einem Rangschnitt (die obersten 20, 100 oder 500
Fälle) entscheidet innerhalb gleicher Punktzahl die Sortierung nach EGID, welche Fälle oben
stehen. Eine Trefferquote entlang der Rangfolge misst dann diese Sortierung und nicht das
Verfahren.

Eine Belegart ist klar abgegrenzt und kommt ohne Rangfolge aus. Die Quoten unten sind
deshalb reproduzierbar.

## Trefferquote je Belegart

"Davon falsch" heisst: Die Gegenquelle zeigt einen anderen Wärmeerzeuger als das Register.
Die Grundrate ist der Anteil falscher Einträge unter allen auswertbaren Gebäuden des Kantons,
der Faktor das Verhältnis der Trefferquote zu dieser Grundrate. Der Vertrauensbereich
(von, bis) ist das Wilson-Intervall zu 95 Prozent. Gezeigt sind Belegarten ab fünf Fällen.

{_tab(_mit_ci(wirkung))}

## Der Status der Anlage entscheidet

Als Beleg zählt eine Anlage nur, wenn ihr Status eine laufende oder entstehende Wärmepumpe
belegt (Merkmal `belegt_anlage` in `sql/test5.sql`). Der Grund ist Genf: Das dortige
Bohrungsregister führt für fast alle Bohrungen den Status "Inconnu" oder "Exploitable".
"Exploitable" stuft die Ressource ein und sagt, dass dort gebohrt werden könnte; eine
laufende Anlage belegt dieser Status nicht. Ohne die Einschränkung treffen in Genf 2 von
30 Anlagenfällen zu, und der Unterschied zu Zug sähe aus wie ein Unterschied zwischen den
Kantonen.

Die Zuger Anlagen sind gemischt. Von den 51 Fällen mit genau einem Gebäude im Umkreis
(Abschnitt "Übertragbarkeit auf Zürich") tragen 24 den Status "in Betrieb" (22 davon
treffen zu) und 27 den Status "unbekannt" (18 treffen zu). "Unbekannt" heisst in Zug, dass
der Kanton den Betriebszustand nicht führt; diese Anlagen zählen deshalb als Beleg.

Mit dem Statusfilter verliert Genf fast alle prüfbaren Anlagenfälle. Der Anlagenbeleg
lässt sich dort nicht messen.

Anlagen je Status (Zeilen mit mehr als 500 Anlagen oder mit Anlagen, die nicht als Beleg
zählen):

{_tab(status)}

Zürich und Schwyz führen kein Statusfeld, in St. Gallen fehlt es bei einem Teil der Anlagen.
Dort gelten alle veröffentlichten Anlagen als bestehend. Diese Annahme lässt sich nicht
prüfen. In Schaffhausen und Solothurn nennt das Feld die Anlagenart ("Erdsonde",
"WP mit Erdwärmesonde") und keinen Betriebszustand; auch diese Anlagen zählen als Beleg.

## Die Verdachtsliste

Die Tabelle oben misst Belegarten. Die Verdachtsliste ist eine Auswahl aus mehreren
Belegarten, gegliedert nach Stufen. Deshalb dieselbe Messung für die Fälle mit Listenstufe:

{_tab(_mit_ci(liefer_gesamt))}

Je Stufe:

{_tab(_mit_ci(liefer))}

Gemessen wird auf `v_gold_score`, also vor dem Gegenbeleg-Filter der Liste: Der Filter
benutzt dieselben Kataster, aus denen die Labels stammen, die Messung wäre sonst zirkulär.

Die Stufe "Beleg vor Eintrag" steht nicht auf der Liste und fehlt deshalb in der Tabelle.
Liegt der Beleg vor dem Registereintrag, trifft der Verdacht in Zug in {vor_falsch} von
{vor_n} prüfbaren Fällen zu, also nahe der Grundrate. Zusammen mit diesen Fällen sind in Zug
{t(zg_pruefbar + vor_n)} Fälle mit Anlagenbeleg prüfbar.

Am stärksten trennt damit die Reihenfolge von Beleg und Registereintrag, stärker als die
Belegart. Ein Beleg sagt, dass am Gebäude etwas an der Heizung geschehen ist. Ob das im
Register steht, hängt daran, ob der Eintrag danach noch bearbeitet wurde.

Für Genf ist die Tabelle keine Messung: Nach dem Statusfilter bleibt dort kaum ein
prüfbarer Fall mit Listenstufe (Anzahl: {ge_stufe}).

### Überleitung der Zuger Fallzahlen

Die Berichte nennen für Zug mehrere Fallzahlen. Sie zählen verschiedene Mengen:

{ueberleitung}

## Übertragbarkeit auf Zürich

Zug ordnet seine Anlagen über die amtliche EGID oder die Adresse zu; der Kanton nennt also
selbst das Gebäude zur Sonde. Zürich liefert das nicht: 38'553 Bohrungen ohne EGID, ohne
Adresse, ohne Status. Dort bleibt nur der 20-Meter-Umkreis.

Deshalb dieselbe Zuger Messung noch einmal, ausschliesslich über den Umkreis zugeordnet,
also mit dem Verfahren, das für Zürich gilt:

{_tab(_mit_ci(umkreis))}

**Die Eindeutigkeit des Umkreises entscheidet.** Liegt genau ein Gebäude im
20-Meter-Umkreis der Anlage, trifft der Verdacht in rund vier von fünf Fällen zu, auch ohne
amtliche Zuordnung. Liegen drei oder mehr Gebäude darin, fällt die Quote in die Nähe der
Grundrate.

Die Zuordnung übernimmt eine Zürcher Anlage deshalb nur, wenn genau ein Gebäude in ihrem
Umkreis liegt (`sql/zuordnung_anlagen.sql`).

## Woraus die Listen bestehen

Zusammensetzung der Verdachtsliste je Kanton nach Belegart (Zeilen ab fünf Fällen):

{_tab(aufbau)}

## Wer aus der Messung fällt

Gemessen werden kann nur, wozu der Tankkataster etwas sagt. Kennt er zu einem Gebäude
keinen Tank, gilt der Fall als ungeklärt und fällt heraus. Das ist nicht gleichmässig
verteilt (Zuger Wohngebäude mit Öleintrag):

{_tab(ungeklaert, n="Gebäude")}

Gebäude mit einem Beleg fallen häufiger aus der Messung als Gebäude ohne, rund ein Drittel
gegenüber einem Viertel. Zwei Lesarten sind möglich, und mit diesen Daten lässt sich keine
ausschliessen:

- **Zugunsten der Liste:** Wer von Öl auf eine Wärmepumpe wechselt, lässt den Tank
  ausbauen. Gebäude ohne Tankeintrag wären dann überdurchschnittlich oft die gesuchten
  Fälle, und die gemessene Quote wäre zu tief.
- **Zuungunsten der Liste:** Der Kataster führt stillgelegte Tanks weiter
  ({t(zg_stillgelegt)} Gebäude mit stillgelegtem Tank). "Kein Tank" heisst dann eher
  "nie erfasst", und die herausgefallenen Fälle sind eine Mischung wie alle anderen.

Dazu kommt eine zweite Lücke derselben Art: {t(liste_gas)} der {t(liste_n)} Fälle der
Verdachtsliste sind Gaseinträge, in Zug {t(zg_gas)} von {t(zg_stufe)} Fällen mit Listenstufe.
Ein Öltankkataster sagt über Gas nichts; auch diese Fälle sind ungeprüft.

Ein erheblicher Teil der Fälle mit Listenstufe ist in Zug also nicht prüfbar, und dieser
Anteil ist höher als bei Gebäuden ohne Beleg. Die gemessene Quote gilt nur zusammen mit
dieser Einschränkung.

## Was ungemessen bleibt

Das Baugesuch nennt den neuen Energieträger im Klartext und ist datiert. Für diesen Beleg
gibt es keine Messung: In den beiden Labelkantonen Genf und Zug kommt kein prüfbarer Fall
mit Baugesuch-Beleg vor. Die {t(liste_baugesuch)} Fälle der Verdachtsliste mit
Baugesuch-Beleg beruhen damit auf einer Annahme.
"""
    ZIEL.write_text(fmt.de(text), encoding="utf-8")
    print(f"{ZIEL} geschrieben")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
