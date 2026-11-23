"""Labels aus Genf und Zug: Wie oft ist der Registereintrag falsch?

groundtruth_ge.sql und groundtruth_zg.sql leiten aus den kantonalen Gegenquellen je
auswertbarem Gebaeude ein Label ab: Passt der GWR-Eintrag zum Waermeerzeuger, den die
Gegenquelle ausweist? "Kein aktiver fossiler Kessel gefunden" reicht dafuer nicht, denn
ein Gebaeude ohne Kesseleintrag kann auch nicht erfasst sein (reports/precision.md misst
nur diese Hilfsgroesse).

Dieser Bericht dokumentiert die Labelsaetze und die Grundrate. Die Messung je Belegart
und Listenstufe steht in reports/belegwirkung.md.

    python src/report_groundtruth.py
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import config
import fmt
import pipeline

# Drei Labelsaetze. Der Unterschied zwischen "breit" und "strikt" ist die
# Hauptunsicherheit dieser Messung:
#
#   breit    Auch "fossiler Kessel stillgelegt, nichts Neues erfasst" gilt als falscher
#            Eintrag. Begruendung: Das Gebaeude muss mit irgendetwas geheizt werden.
#   strikt   Nur wo der Kataster einen anderen aktiven Waermeerzeuger nennt. Das ist ein
#            direkter Vergleich statt eines Schlusses.
#
# Beide werden ausgewiesen.
KANTONE = {
    "GE": {"sicht": "v_ge_label_klar", "roh": "v_ge_label",
           "quelle": "Feuerungskataster mit EGID, Brennstoff und Betriebszustand",
           "staerke": "nennt auch den Wärmeerzeuger, der stattdessen läuft"},
    "GE strikt": {"sicht": "v_ge_label_strikt", "roh": "v_ge_label",
                  "quelle": "derselbe Kataster, aber nur direkte Vergleiche",
                  "staerke": "ohne die Fälle, bei denen nur die Stilllegung bekannt ist",
                  "ohne_verteilung": True},
    "ZG": {"sicht": "v_zg_label_klar", "roh": "v_zg_label",
           "quelle": "Tankkataster, getrennt nach in und ausser Betrieb",
           "staerke": "nur Heizöl, Zuordnung über einen 10-m-Umkreis statt über die EGID"},
}

# Die Sichten fuehren die Labels als technische Bezeichner.
LABEL_TXT = {
    "stimmt": "stimmt", "ungeklaert": "ungeklärt",
    "hybrid": "hybrid (fossil und erneuerbar zugleich)",
    "falscher_traeger": "falscher fossiler Träger",
    "veraltet_waermepumpe": "veraltet, jetzt Wärmepumpe",
    "veraltet_fernwaerme": "veraltet, jetzt Fernwärme",
    "veraltet_holz": "veraltet, jetzt Holz",
    "veraltet_elektro": "veraltet, jetzt Elektroheizung",
    "veraltet_stillgelegt": "veraltet, Feuerung oder Tank stillgelegt",
}

BELEG_SQL = """
    CASE WHEN b.egid IS NULL                            THEN '0 kein Beleg'
         WHEN b.hat_baugesuch                           THEN '1 Baugesuch'
         WHEN b.hat_sonde AND b.sonde_dist_m <= 10      THEN '2 Anlage bis 10 m'
         WHEN b.hat_sonde                               THEN '3 Anlage 10 bis 20 m'
         WHEN b.ws_art IS NOT NULL                      THEN '4 Registerwiderspruch'
         WHEN b.hat_pv                                  THEN '5 nur Photovoltaik'
         ELSE                                                '6 anderes' END
"""


def wilson(k: int, n: int) -> tuple[float, float]:
    """95-Prozent-Intervall nach Wilson. Bei Fallzahlen unter hundert ist die einfache
    Normalnaeherung irrefuehrend - sie liefert Intervalle, die unter null reichen."""
    if not n:
        return (0.0, 0.0)
    p, z = k / n, 1.96
    d = 1 + z * z / n
    m = (p + z * z / (2 * n)) / d
    s = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (round(100 * (m - s), 1), round(100 * (m + s), 1))


def je_beleg(con, kt: str) -> list[dict]:
    sicht = KANTONE[kt]["sicht"]
    zeilen = con.execute(f"""
        WITH k AS (
            SELECT l.eintrag_falsch, {BELEG_SQL} AS beleg
            FROM {sicht} l LEFT JOIN gold_belege b USING (egid))
        SELECT beleg, count(*) AS n, sum(eintrag_falsch::INT) AS falsch
        FROM k GROUP BY 1 ORDER BY 1
    """).fetchall()
    basis = next((f / n for b, n, f in zeilen if b.startswith("0")), None)
    ergebnis = []
    for beleg, n, falsch in zeilen:
        lo, hi = wilson(falsch, n)
        ergebnis.append({
            "beleg": beleg[2:], "n": n, "falsch": falsch,
            "pct": round(100 * falsch / n, 1), "lo": lo, "hi": hi,
            "faktor": (round((falsch / n) / basis, 1)
                       if basis and not beleg.startswith("0") else None),
        })
    return ergebnis


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=str(config.REPORTS / "groundtruth.md"))
    a = p.parse_args(argv)

    con = pipeline.connect(schreibend=False)
    stand = con.execute("SELECT max(stand) FROM silver_gebaeude_ch").fetchone()[0]
    text = [
        "# Labels aus Genf und Zug: Wie oft ist der Registereintrag falsch?",
        "",
        f"Registerstand {stand.strftime('%d.%m.%Y')}. Der Bericht beschreibt die "
        "Labelsätze, an denen die Verdachtsfälle gemessen werden: Für jedes auswertbare "
        "Gebäude in Genf und Zug steht fest, ob der GWR-Eintrag zum Wärmeerzeuger passt, "
        "den eine kantonale Gegenquelle ausweist. Der Bericht ist eine Vorstufe: Die "
        "Messung je Belegart und Listenstufe steht in [belegwirkung.md](belegwirkung.md).",
        "",
        "Ein Label ist strenger als die Hilfsgrösse aus [precision.md](precision.md). "
        "Dort gilt ein Verdacht schon als gestützt, wenn sich kein aktiver fossiler "
        "Kessel findet. Ein Gebäude ohne Kesseleintrag kann aber auch nicht erfasst "
        "sein; hier gilt es deshalb als ungeklärt.",
        "",
        "Der Faktor in den Tabellen bezieht sich auf die Gebäude ohne Beleg (erste "
        "Zeile). In [belegwirkung.md](belegwirkung.md) bezieht er sich auf die "
        "Grundrate aller auswertbaren Gebäude; die Faktoren der beiden Berichte sind "
        "deshalb nicht gleich.",
        "",
    ]

    for kt, meta in KANTONE.items():
        verteilung = (None if meta.get("ohne_verteilung") else con.execute(f"""
            SELECT label, count(*) AS n FROM {meta['roh']} GROUP BY 1 ORDER BY 2 DESC
        """).df())
        n, falsch = con.execute(f"""
            SELECT count(*), sum(eintrag_falsch::INT) FROM {meta['sicht']}
        """).fetchone()
        text += [
            f"## {kt}: {meta['quelle']}",
            "",
            f"*{meta['staerke']}*",
            "",
            *([] if verteilung is None else
              [fmt.md(verteilung.assign(label=verteilung["label"].replace(LABEL_TXT))
                      .rename(columns={"label": "Label", "n": "Gebäude"})), ""]),
            f"Auswertbar sind {fmt.tsd(n)} Gebäude. Davon ist der Eintrag bei "
            f"**{fmt.tsd(falsch)} falsch, also {fmt.de(f'{100 * falsch / n:.1f}')} %.** "
            "Das ist die Grundrate.",
            "",
            "| Beleg | Gebäude | falsch | Anteil | 95 %-Intervall | Faktor |",
            "|---|---:|---:|---:|---|---:|",
        ]
        for z in je_beleg(con, kt):
            faktor = fmt.de(str(z["faktor"])) if z["faktor"] is not None else "Bezugswert"
            text.append(
                f"| {z['beleg']} | {fmt.tsd(z['n'])} | {fmt.tsd(z['falsch'])} "
                f"| {fmt.de(str(z['pct']))} % "
                f"| {fmt.de(str(z['lo']))} bis {fmt.de(str(z['hi']))} % | {faktor} |")
        text.append("")

    # Pruefbare Anlagenfaelle je Kanton, fuer den Abschnitt zu den Grenzen
    anlage = {kt: sum(z["n"] for z in je_beleg(con, kt) if z["beleg"].startswith("Anlage"))
              for kt in ("GE", "ZG")}
    text += [
        "## Messung je Belegart statt entlang einer Rangfolge",
        "",
        "Eine Auswertung entlang der Rangfolge nach Punktzahl (Trefferquote der obersten "
        "20, 100 oder 500 Fälle) enthält dieser Bericht nicht. Der Score kennt nur "
        "wenige mögliche Summen, viele Fälle teilen dieselbe Punktzahl, und innerhalb "
        "gleicher Punktzahl entscheidet die Sortierung nach Gebäudenummer. Ein "
        "Rangschnitt misst dann diese Sortierung. Zudem ordnet die Verdachtsliste nach "
        "Stufe und Belegklasse, nicht nach Punktzahl.",
        "",
        "Die Messung je Belegart und je Listenstufe steht in "
        "[belegwirkung.md](belegwirkung.md). Dieser Bericht dokumentiert die "
        "Labelsätze, also woran gemessen wird.",
        "",
        "## Was diese Messung nicht kann",
        "",
        "1. **Das Baugesuch bleibt ungemessen.** In Genf und Zug gibt es keinen "
        "zugeordneten Baugesuchsfall mit Label. Der Beleg, von dem die Studie ausgeht, "
        "lässt sich hier nicht prüfen.",
        "2. **Ungeklärte Fälle bleiben ungeklärt.** Ein Teil der Gebäude ist in den "
        "Gegenquellen nicht oder nur mit Warmwasseranlagen erfasst (Label "
        "\"ungeklärt\" in den Tabellen oben). Der Anteil ist zwischen den Belegarten "
        "nicht gleich: In Zug liegt er bei Gebäuden mit Beleg höher als bei Gebäuden "
        "ohne ([belegwirkung.md](belegwirkung.md)). Eine Verzerrung ist damit nicht "
        "ausgeschlossen.",
        "3. **Genf misst den Anlagenbeleg nicht.** Das Genfer Bohrungsregister führt "
        "für fast alle Bohrungen den Status \"Inconnu\" oder \"Exploitable\", also "
        "eine Einstufung der Ressource statt einer laufenden Anlage. Solche Einträge "
        f"gelten nicht als Beleg. In Genf bleiben {fmt.tsd(anlage['GE'])} prüfbare "
        "Anlagenfälle.",
        "4. **Ein Kanton ist nicht die Schweiz.** Die Messung des Anlagenbelegs beruht "
        f"damit auf Zug: ein kleiner Kanton, ein Öltankkataster, {fmt.tsd(anlage['ZG'])} "
        "prüfbare Fälle mit Anlagenbeleg. Ob die Quoten in Zürich gelten, ist offen; "
        "klären liesse sich das nur durch eine Prüfung vor Ort.",
        "",
    ]

    ziel = (Path(a.out) if str(a.out).startswith(str(config.ROOT))
            else config.ROOT / a.out)
    ziel.write_text(fmt.de("\n".join(text)), encoding="utf-8")
    print(f"geschrieben: {ziel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
