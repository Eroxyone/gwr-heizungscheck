"""Vorstufe: Gegenprobe der Verdachtsfaelle an zwei kantonalen Gegenquellen.

Gemessen wird eine Hilfsgroesse: Laeuft bei einem fossil eingetragenen Wohngebaeude laut
Gegenquelle noch eine fossile Heizung - und wie oft bei einem Gebaeude mit Beleg?

  Genf  Feuerungskataster, 55'372 Kessel mit EGID, Brennstoff und Betriebszustand
  Zug   Tankkataster, 8'319 Heizoeltanks, getrennt nach "in Betrieb" und "ausser Betrieb"

Aussagekraeftig ist der Abstand zur Grundrate, nicht der Anteil selbst. Wie oft der
Registereintrag tatsaechlich falsch ist, misst reports/belegwirkung.md an Labels.

    python src/report_precision.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import config
import fmt
import pipeline

# Je Kanton: die Sicht mit dem Gegenbeleg, die Spalte "laeuft noch" und eine Beschreibung.
QUELLEN = {
    "GE": {
        "sicht": "v_feuerung_ge",
        "spalte": "fossil_aktiv",
        "name": "Feuerungskataster",
        "beschreibung": "55'372 Kessel mit EGID, Brennstoff, Betriebszustand und Baujahr",
    },
    "ZG": {
        "sicht": "v_tank_zg",
        "spalte": "oeltank_in_betrieb",
        "name": "Tankkataster",
        "beschreibung": "8'319 Heizöltanks in vier Layern, getrennt nach Betriebszustand",
        # Ein Heizoeltank sagt nichts ueber eine Gasheizung. Gegen alle fossilen Eintraege
        # gerechnet, mischen sich 4'430 Oel-Eintraege (91,2 % mit aktivem Tank) mit
        # 554 Gas-Eintraegen (26,4 %) zu einer irrefuehrenden Grundrate von 84,0 %.
        # Zug prueft deshalb nur Oel.
        "nur_klasse": "oel",
    },
}


def messung(con, kt: str) -> dict:
    q = QUELLEN[kt]
    # Die Gegenquelle darf nur dort als Gegenbeleg gelten, wo sie den richtigen
    # Brennstoff kennt. Sonst widerlegt ein stillgelegter Oeltank eine Gasheizung.
    klasse = q.get("nur_klasse")
    filter_klasse = (f"AND g.energie_klasse = '{klasse}'" if klasse
                     else "AND g.ist_fossil")
    grund = con.execute(f"""
        SELECT count(*) AS gebaeude,
               round(100.0 * sum(f.{q['spalte']}::INT) / count(*), 1) AS pct_aktiv
        FROM silver_gebaeude_ch g JOIN {q['sicht']} f USING (egid)
        WHERE g.kanton = '{kt}' AND g.ist_wohngebaeude {filter_klasse}
    """).df().iloc[0]
    # Alle Kandidaten, auch die vom Gegenbeleg entfernten - sonst misst man sich selbst.
    filter_kandidat = (f"AND b.energie_klasse = '{klasse}'" if klasse else "")
    je_beleg = con.execute(f"""
        WITH kandidaten AS (
            SELECT b.egid,
                   CASE WHEN b.hat_baugesuch   THEN 'Baugesuch'
                        WHEN b.hat_sonde       THEN 'Wärmenutzungsanlage'
                        WHEN b.hat_widerspruch THEN 'Registerwiderspruch'
                        WHEN b.hat_pv          THEN 'nur Photovoltaik'
                        ELSE 'anderes' END AS beleg,
                   f.egid IS NOT NULL AS im_kataster,
                   COALESCE(f.{q['spalte']}, FALSE) AS aktiv
            FROM gold_belege b
            LEFT JOIN {q['sicht']} f USING (egid)
            WHERE b.kanton = '{kt}' {filter_kandidat}
        )
        SELECT beleg AS "Beleg", count(*) AS "Fälle",
               sum(im_kataster::INT) AS "geprüft",
               round(100.0 * sum(aktiv::INT) / nullif(sum(im_kataster::INT), 0), 1)
                   AS "fossil läuft noch %"
        FROM kandidaten GROUP BY 1 HAVING sum(im_kataster::INT) > 0 ORDER BY 4
    """).df()
    entfernt = con.execute(f"""SELECT count(*) FROM gold_belege
                               WHERE kanton = '{kt}' AND kessel_aktiv""").fetchone()[0]
    bleibt = con.execute(f"""SELECT count(*) FROM v_gold_verdacht
                             WHERE kanton = '{kt}'""").fetchone()[0]
    return {"kanton": kt, "grund": grund, "je_beleg": je_beleg,
            "entfernt": entfernt, "bleibt": bleibt, **q}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=str(config.REPORTS / "precision.md"))
    a = p.parse_args(argv)

    con = pipeline.connect(schreibend=False)
    stand = con.execute("SELECT max(stand) FROM silver_gebaeude_ch").fetchone()[0]
    messungen = [messung(con, kt) for kt in QUELLEN]

    text = [
        "# Vorstufe: Gegenprobe der Verdachtsfälle an Feuerungs- und Tankkataster",
        "",
        f"> **Dieser Bericht ist eine Vorstufe, Registerstand {stand.strftime('%d.%m.%Y')}.** "
        "Er misst, ob sich zu einem Verdachtsfall noch ein aktiver fossiler Kessel oder "
        "Tank finden lässt, also eine Hilfsgrösse. Wie oft der Registereintrag "
        "tatsächlich falsch ist, beantwortet [belegwirkung.md](belegwirkung.md). Wo die "
        "beiden Berichte verschiedene Zahlen nennen, gilt belegwirkung.md.",
        "",
        "Alle Belege dieser Studie zeigen in dieselbe Richtung: Hier ist eine "
        "Wärmepumpe gebaut, hier eine Sonde gebohrt, hier ein Baugesuch publiziert. "
        "Keiner davon sagt, ob die alte Ölheizung daneben **noch läuft**. Ein "
        "Verdachtsfall ist aber nur dann ein Fehler im Register, wenn der fossile "
        "Eintrag nicht mehr stimmt.",
        "",
        "Zwei Kantone erlauben die Gegenprobe, mit verschiedenen Datensätzen:",
        "",
    ]
    for m in messungen:
        klasse_txt = {"oel": "Heizöl", "gas": "Gas"}.get(m.get("nur_klasse"), m.get("nur_klasse"))
        einschr = (f" (nur gegen Einträge mit Energieträger "
                   f"{klasse_txt} ausgewertet)") if m.get("nur_klasse") else ""
        text.append(f"- **{m['kanton']}, {m['name']}**: {m['beschreibung']}{einschr}")
    text += [
        "",
        "Beide Messungen zeigen dieselbe Rangfolge der Belegarten.",
        "",
    ]

    for m in messungen:
        grund = m["grund"]
        beste = m["je_beleg"].iloc[0] if len(m["je_beleg"]) else None
        text += [
            f"## {m['kanton']}: {m['name']}",
            "",
            f"Von den fossil eingetragenen Wohngebäuden in {m['kanton']} stehen "
            f"{fmt.tsd(int(grund.gebaeude))} auch in dieser Quelle. Bei "
            f"**{fmt.de(str(grund.pct_aktiv))} %** von ihnen läuft dort noch eine fossile "
            "Heizung. Das ist die Grundrate.",
            "",
            fmt.md(m["je_beleg"]),
            "",
        ]
        if beste is not None:
            diff = round(float(grund.pct_aktiv) - float(beste["fossil läuft noch %"]), 1)
            text += [
                f"Stärkster Beleg: **{beste['Beleg']}** mit "
                f"{fmt.de(str(beste['fossil läuft noch %']))} %, also "
                f"{fmt.de(str(diff))} Prozentpunkte unter der Grundrate.",
                "",
            ]
        schlechter = m["je_beleg"][
            m["je_beleg"]["fossil läuft noch %"] > float(grund.pct_aktiv)]
        for _, z in schlechter.iterrows():
            klein = int(z["geprüft"]) < 50
            text += [
                f"Über der Grundrate liegt **{z['Beleg']}** mit "
                f"{fmt.de(str(z['fossil läuft noch %']))} %, gemessen an "
                f"{fmt.tsd(int(z['geprüft']))} geprüften Fällen. Diese Belegart findet "
                "hier eher Gebäude, bei denen der fossile Eintrag stimmt."
                + (" Die Fallzahl ist für eine belastbare Aussage zu klein."
                   if klein else ""),
                "",
            ]
        text += [
            f"Der Gegenbeleg nimmt {fmt.tsd(m['entfernt'])} Fälle aus der Sicht "
            f"`v_gold_verdacht`, {fmt.tsd(m['bleibt'])} bleiben.",
            "",
        ]

    abstaende = [round(float(m["grund"].pct_aktiv)
                       - float(m["je_beleg"].iloc[0]["fossil läuft noch %"]), 1)
                 for m in messungen if len(m["je_beleg"])]
    text += [
        "## Was beide Messungen gemeinsam sagen",
        "",
        f"1. **Die Auswahl wirkt, trennt aber nicht sauber.** Der beste Beleg "
        f"drückt den Anteil noch laufender fossiler Heizungen um "
        f"{fmt.de(str(min(abstaende)))} bis {fmt.de(str(max(abstaende)))} Prozentpunkte "
        "unter die Grundrate. Über alle Belegarten zusammen trägt die Mehrheit der "
        "ausgewählten Gebäude weiterhin einen aktiven fossilen Gegenbeleg.",
        "2. **Die Wärmenutzungsanlage ist der stärkste verfügbare Beleg**, in beiden "
        "Kantonen. Photovoltaik liegt dahinter, wirkt aber messbar, und ist der einzige "
        "Beleg, den es in allen 26 Kantonen gibt.",
        "3. **Der Registerwiderspruch liegt in beiden Kantonen über der Grundrate**, "
        "beruht dort aber auf wenigen geprüften Fällen. Der Untertyp, der im Score "
        "Punkte gibt (Wärmeerzeuger \"Wärmepumpe\" bei Energieträger \"Heizöl\"), kommt "
        "in Genf und Zug nicht vor. Gemessen sind nur die Warmwasser-Untertypen "
        "Fernwärme, Erdwärme und Luft. Über den Erzeuger-Widerspruch sagt diese "
        "Messung nichts.",
        "",
        "**Zur Formulierung.** Gemessen ist: Ausgewählte Gebäude tragen seltener einen "
        "**aktiven fossilen Gegenbeleg** als der Vergleichsbestand. Das ist nicht "
        "dasselbe wie \"der GWR-Eintrag ist falsch\": Ein Gebäude ohne Kessel- oder "
        "Tankeintrag kann auch nicht erfasst sein. Eine Aussage wie \"der Anteil "
        "veralteter Einträge ist doppelt so hoch\" geht deshalb über diese Messung "
        "hinaus.",
        "",
        "## Grenzen dieser Messung",
        "",
        "1. **Zwei Kantone sind nicht die Schweiz.** Genf hat den höchsten Anteil "
        "\"unbestimmt\" im GWR und eine sehr tiefe Wärmepumpendichte, Zug ist klein und "
        "dicht bebaut. Die Zahlen sind eine Grössenordnung.",
        "2. **Eine Gegenquelle gilt nur für den Brennstoff, den sie kennt.** Ein "
        "stillgelegter Öltank widerlegt keine Gasheizung. Zug wird deshalb nur gegen "
        "Öl-Einträge gerechnet. Gegen alle fossilen Einträge gerechnet, mischen sich "
        "4'430 Öl-Einträge (91,2 % mit aktivem Tank) mit 554 Gas-Einträgen (26,4 %) zu "
        "einer irreführenden Grundrate von 84,0 %.",
        "3. **Die Gegenquellen sind selbst nicht fehlerfrei.** Ein Kessel gilt als aktiv "
        "und ein Tank als in Betrieb, bis jemand die Stilllegung meldet. Wo zwei amtliche "
        "Register sich widersprechen, lässt sich aus den Daten allein nicht sagen, "
        "welches recht hat.",
        "4. **Eine Zentralheizung kann mehrere Gebäude versorgen.** Genf führt dazu eine "
        "eigene Beziehungstabelle mit 2'587 Einträgen; dieser Bericht nutzt sie nicht. "
        "Der Zuger Tankkataster wird über einen 10-m-Umkreis zugeordnet, nicht über "
        "eine Gebäudenummer.",
        "5. **Hybridanlagen sind keine Widersprüche.** Ein Genfer Kessel \"en réserve\" "
        "neben einer Wärmepumpe ist der Normalfall und zählt weder als Beleg noch als "
        "Gegenbeleg.",
        "",
        "## Einordnung",
        "",
        "Diese Messung ersetzt die Prüfung vor Ort nicht. Die Messung an Labels steht in "
        "[belegwirkung.md](belegwirkung.md), die Messung an den späteren Korrekturen im "
        "Register in [zeitreihe.md](zeitreihe.md).",
        "",
    ]

    ziel = config.ROOT / a.out if not str(a.out).startswith(str(config.ROOT)) else a.out
    Path(ziel).write_text(fmt.de("\n".join(text)), encoding="utf-8")
    for m in messungen:
        print(f"{m['kanton']}: Grundrate {m['grund'].pct_aktiv} %, "
              f"{m['entfernt']} Faelle entfernt, {m['bleibt']} bleiben")
    print(f"geschrieben: {ziel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
