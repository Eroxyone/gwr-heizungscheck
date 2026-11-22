"""Wie oft ist der Registereintrag wirklich falsch? Gemessen an echten Labels.

Das Projekt hat lange die falsche Frage gemessen. Die Gegenkataster von Genf und Zug
wurden nur benutzt, um einen Verdacht zu entkraeften - "kein aktiver fossiler Kessel
gefunden" galt als Treffer. Das ist nicht dasselbe wie "der Eintrag ist falsch": Ein
Gebaeude ohne Kesseleintrag kann auch einfach nicht erfasst sein.

Seit groundtruth_ge.sql und groundtruth_zg.sql gibt es echte Labels. Fuer jedes
auswertbare Gebaeude steht fest, ob der GWR-Eintrag zum tatsaechlichen Waermeerzeuger
passt. Damit laesst sich zum ersten Mal sagen, was ein Beleg wert ist.

Zwei Kantone, zwei voellig verschiedene Quellen, dieselbe Rangfolge - das ist der
eigentliche Befund. Ein einzelner Kanton waere nicht genug gewesen.

    python src/report_groundtruth.py
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

import config
import fmt
import pipeline

# Drei Labelsaetze statt zwei. Der Unterschied zwischen "breit" und "strikt" ist keine
# Feinheit, sondern die Hauptunsicherheit dieser Messung:
#
#   breit    Auch "fossiler Kessel stillgelegt, nichts Neues erfasst" gilt als falscher
#            Eintrag. Begruendung: Das Gebaeude muss mit irgendetwas geheizt werden.
#   strikt   Nur wo der Kataster einen ANDEREN aktiven Waermeerzeuger nennt. Das ist ein
#            direkter Vergleich statt eines Schlusses. Kostet 861 der 1'437 positiven
#            Faelle, also drei Fuenftel des Signals.
#
# Beide werden ausgewiesen. Wer nur die guenstigere Zahl nennt, behauptet eine Sicherheit,
# die er nicht hat.
KANTONE = {
    "GE": {"sicht": "v_ge_label_klar", "roh": "v_ge_label",
           "quelle": "Feuerungskataster mit EGID, Brennstoff und Betriebszustand",
           "staerke": "sagt auch, WAS stattdessen laeuft"},
    "GE strikt": {"sicht": "v_ge_label_strikt", "roh": "v_ge_label",
                  "quelle": "derselbe Kataster, aber nur direkte Vergleiche",
                  "staerke": "ohne die Faelle, bei denen nur die Stilllegung bekannt ist",
                  "ohne_verteilung": True},
    "ZG": {"sicht": "v_zg_label_klar", "roh": "v_zg_label",
           "quelle": "Tankkataster, getrennt nach in und ausser Betrieb",
           "staerke": "nur Heizöl, Zuordnung über einen 10-m-Umkreis statt über die EGID"},
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

    con = pipeline.connect()
    text = [
        "# Wie oft ist der Registereintrag wirklich falsch?",
        "",
        "Bisher hat dieses Projekt eine Hilfsgrösse gemessen: ob sich zu einem "
        "Verdachtsfall ein aktiver fossiler Kessel finden lässt. Wo keiner gefunden "
        "wurde, galt der Verdacht als bestätigt. Das ist zu grosszügig - ein Gebäude "
        "ohne Kesseleintrag kann auch einfach nicht erfasst sein.",
        "",
        "Jetzt gibt es echte Labels. Für jedes auswertbare Gebäude steht fest, ob der "
        "GWR-Eintrag zum tatsächlich laufenden Wärmeerzeuger passt.",
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
              [fmt.md(verteilung.rename(columns={"label": "Label", "n": "Gebäude"})), ""]),
            f"Auswertbar sind {fmt.tsd(n)} Gebäude. Davon ist der Eintrag bei "
            f"**{fmt.tsd(falsch)} falsch, also {fmt.de(f'{100 * falsch / n:.1f}')} %.** "
            "Das ist die Grundrate, gegen die jeder Beleg antreten muss.",
            "",
            "| Beleg | Gebäude | falsch | Anteil | 95 %-Intervall | Faktor |",
            "|---|---:|---:|---:|---|---:|",
        ]
        for z in je_beleg(con, kt):
            faktor = fmt.de(str(z["faktor"])) if z["faktor"] is not None else "Grundrate"
            text.append(
                f"| {z['beleg']} | {fmt.tsd(z['n'])} | {fmt.tsd(z['falsch'])} "
                f"| {fmt.de(str(z['pct']))} % "
                f"| {fmt.de(str(z['lo']))} bis {fmt.de(str(z['hi']))} % | {faktor} |")
        text.append("")

    # Das ist die Zahl, die ein Bauamt wissen will: Was erlebt eine Gemeinde, die die
    # obersten N Faelle prueft? Gemessen auf v_gold_score, NICHT auf v_gold_verdacht -
    # letztere filtert mit demselben Genfer Kataster, aus dem die Labels stammen.
    text += [
        "## Was eine Gemeinde erlebt",
        "",
        "Hier stand bis zur Ueberarbeitung eine Top-K-Kurve mit Prosa dazu. Beides ist "
        "entfallen, und der Grund gehoert in den Bericht:",
        "",
        "Die Kurve sortierte nach Punktzahl und schnitt bei Rang 20, 100 und 500 ab. "
        "Der Score kennt aber nur wenige moegliche Summen - in Genf hatten hunderte "
        "Faelle exakt 45 Punkte. Welche zwanzig davon oben landeten, entschied die "
        "Sortierung nach Gebaeudenummer. Niedrige Nummer heisst in Genf Innenstadt, "
        "Innenstadt heisst Fernwaerme. Die Kurve mass den Tiebreak.",
        "",
        "Dazu kam: Gemessen wurde nach Punktzahl, die Liste ordnet nach Belegklasse. "
        "Das sind zwei verschiedene Listen, und die Messung galt der falschen.",
        "",
        "Beides ist ersetzt durch eine Messung je Belegart und je Listenstufe, ohne "
        "Rangfolge und damit ohne Tiebreak. Sie steht in `reports/belegwirkung.md` und "
        "ist die Leitzahl des Projekts. Dieser Bericht behaelt die Labelsaetze selbst, "
        "also die Frage, WORAN gemessen wird.",
        "",
        "## Was diese Messung nicht kann",
        "",
        "1. **Das Baugesuch bleibt ungemessen.** In Genf und Zug gibt es keinen "
        "einzigen zugeordneten Baugesuchsfall. Ausgerechnet der Beleg, auf dem die "
        "ganze Idee steht, laesst sich hier nicht pruefen.",
        "2. **Ungeklaerte Faelle bleiben ungeklaert.** In Genf ist ein Drittel der "
        "Gebaeude gar nicht oder nur mit Warmwasseranlagen erfasst. Der Anteil ist "
        "zwischen den Belegarten nicht gleich - bei den Anlagenfaellen liegt er hoeher "
        "als bei den uebrigen. Eine Verzerrung ist damit nicht ausgeschlossen.",
        "3. **Genf misst den staerksten Beleg nicht mehr.** Sein Bohrungsregister fuehrt "
        "fuer fast alle Bohrungen den Status \"Inconnu\" oder \"Exploitable\", also "
        "eine Einstufung der Ressource statt einer laufenden Anlage. Seit solche "
        "Eintraege nicht mehr als Beleg gelten, bleiben in Genf drei pruefbare Faelle.",
        "4. **Ein Kanton ist nicht die Schweiz.** Damit steht die ganze Messung des "
        "Liste auf Zug: ein kleiner Kanton, ein Oeltankkataster, 109 pruefbare "
        "Faelle. Ob die Quoten in Zuerich gelten, ist offen - dazu braucht es eine "
        "Pruefung durch eine Zuercher Gemeinde.",
        "",
    ]

    ziel = (Path(a.out) if str(a.out).startswith(str(config.ROOT))
            else config.ROOT / a.out)
    ziel.write_text(fmt.de("\n".join(text)), encoding="utf-8")
    print(f"geschrieben: {ziel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
