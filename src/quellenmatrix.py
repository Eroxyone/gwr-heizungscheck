"""Welche Datenquelle gibt es in welchem Kanton - und was folgt daraus?

Das GWR gibt es ueberall. Alles, womit sich das GWR pruefen laesst, gibt es nur
stellenweise. Diese Ungleichheit bestimmt, welche Aussage ueber einen Kanton moeglich ist:

  Stufe 0  nur GWR              -> man sieht, wie gepflegt das Register aussieht,
                                   nicht, ob es stimmt
  Stufe 1  + Anlagen ohne Datum -> Widersprueche sichtbar, aber nicht datierbar
  Stufe 2  + Anlagen mit Datum  -> "seit wann nicht nachgefuehrt" wird beantwortbar
  Stufe 3  + Baugesuche         -> auch Anlagen ohne Bohrung (Luft/Wasser, Fernwaerme)

Ein Kantonsvergleich ohne diese Stufen vergleicht die Datenlage und nicht die
Registerqualitaet.

    python src/quellenmatrix.py
"""
from __future__ import annotations

import argparse
from pathlib import Path

import config
import fmt
import pipeline

# Was die Recherche je Kanton ergeben hat. Die Zahlen holt der Lauf aus der Datenbank,
# hier steht nur, was sich nicht ausrechnen laesst: warum eine Quelle fehlt.
BEFUND = {
    "ZH": "Vier Layer des AWEL, dazu der OGD-Baugesuchsdatensatz des Statistischen Amts",
    "BE": "AGI-Anlagenregister mit Ausführungsstatus; Baugesuche im Amtsblattportal",
    "LU": "Sonden mit Bohrdatum und als einziger Kanton Luft-Wasser-Wärmepumpen. Die "
          "Koordinaten sind nicht gebäudegenau (Median 24 m zum nächsten Gebäude statt "
          "8 bis 9 m); Luzern ist deshalb aus den auswertenden Sichten ausgeschlossen",
    "SG": "Anlagenregister statt Sondenkataster, führt die Wärmepumpe selbst. 84 % der "
          "Gebäude neben einer Anlage tragen sie schon im GWR; der Kanton führt "
          "offenbar bereits nach",
    "SO": "AFU-Sonden ab 1986, Abgabe auf 5'000 Objekte je Anfrage begrenzt",
    "TG": "Sonden mit Bohrdatum und Status",
    "GE": "SITG-CSV mit Realisierungsdatum",
    "ZG": "Einziger Kanton mit EGID an der Anlage",
    "BL": "Bohrregister mit Bohrjahr (Ausführung, nicht Bewilligung)",
    "AI": "Bohrkataster mit Erstelljahr. Wie in St. Gallen stehen 86 % schon im GWR",
    "SZ": "Nur über map.geo.sz.ch/mapserv_proxy erreichbar, nicht über wfs.geo.sz.ch",
    "SH": "Sonden ohne Datum, in WGS84",
    "UR": "Nur Konzessionen (bewilligt, nicht nachweislich gebaut)",
    "AG": "Keine Anlagendaten als Vektor, nur Eignungskarten als WMS. Der Kanton "
          "überträgt Energiemerkmale seit 2026 direkt aus dem Bewilligungssystem ins GWR",
    "VD": "Geothermie-Kataster vorhanden, aber kostenpflichtig (10 CHF/km2)",
    "JU": "Nur Bohrbeschränkungszonen",
    "AR": "Nur Zulässigkeitsbereiche. Das kantonale EnergyGIS führt eine "
          "Heizungskategorie je Gebäude, leitet sie aber aus dem GWR ab und ist als "
          "Beleg zirkulär",
    "BS": "Nur Energierichtplan-Flächen",
    "NW": "Erdsondenkataster vorhanden, aber nur als WMS-Bild",
    "OW": "Erdsondenkataster vorhanden, aber nur als WMS-Bild",
    "GR": "Nichts gefunden; die Baugesuch-Subrubrik AA-GR10 ist angemeldet, aber leer",
    "GL": "Nichts gefunden",
    "FR": "Nichts gefunden",
    "NE": "Nichts gefunden",
    "TI": "Keine Anlagendaten; Baugesuche im Amtsblattportal",
    "VS": "Keine Anlagendaten; Baugesuche im Amtsblattportal",
}

# Baugesuch-Quelle je Kanton. "ogd" ist der Zuercher Datensatz, "portal" das
# Amtsblattportal, "-" heisst: publiziert kommunal und nicht zentral abrufbar.
BAUGESUCHE = {
    "ZH": "ogd", "BE": "portal", "BS": "portal", "TI": "portal", "ZG": "portal",
    "AR": "portal", "SZ": "portal", "BL": "portal", "SO": "portal", "NW": "portal",
    "OW": "portal", "SH": "portal", "VS": "portal",
}
# Wie die Baugesuch-Quelle in der Tabelle heisst.
BAUGESUCHE_TXT = {"ogd": "OGD Kanton Zürich", "portal": "Amtsblattportal", "-": "–"}


def _tabelle_da(con, name: str) -> bool:
    return bool(con.execute(
        "SELECT count(*) FROM information_schema.tables WHERE table_name = ?",
        [name]).fetchone()[0])


def sammeln(con) -> list[dict]:
    gebaeude = dict(con.execute(
        "SELECT kanton, count(*) FROM silver_gebaeude_ch GROUP BY 1").fetchall())

    anlagen: dict[str, tuple] = {}
    if _tabelle_da(con, "silver_waermenutzung"):
        anlagen = {k: (n, d) for k, n, d in con.execute("""
            SELECT kanton, count(*), count(datum_bewilligung)
            FROM silver_waermenutzung GROUP BY 1""").fetchall()}

    bg: dict[str, int] = {}
    if _tabelle_da(con, "silver_baugesuche_ch"):
        bg = dict(con.execute("""
            SELECT kanton, count(*) FROM silver_baugesuche_ch
            WHERE ist_heizungsereignis AND ist_erstpublikation GROUP BY 1""").fetchall())
    if _tabelle_da(con, "silver_baugesuche"):
        zh = con.execute("""SELECT count(*) FROM silver_baugesuche
                            WHERE ist_heizungsereignis AND ist_erstpublikation""").fetchone()[0]
        bg["ZH"] = max(bg.get("ZH", 0), zh)

    zeilen = []
    for kt in config.KANTONE:
        n_anl, n_dat = anlagen.get(kt, (0, 0))
        n_bg = bg.get(kt, 0)
        if n_bg and n_dat:
            stufe = 3
        elif n_dat:
            stufe = 2
        elif n_anl:
            stufe = 1
        elif n_bg:
            # Baugesuche ohne Anlagen sind auch ein datierter Beleg - dieselbe Stufe wie
            # datierte Anlagen, nur auf anderer Grundlage.
            stufe = 2
        else:
            stufe = 0
        zeilen.append({
            "kanton": kt,
            "gebaeude": gebaeude.get(kt, 0),
            "anlagen": n_anl,
            "anlagen_datiert": n_dat,
            "baugesuche_heizung": n_bg,
            "baugesuch_quelle": BAUGESUCHE.get(kt, "-"),
            "stufe": stufe,
            "befund": BEFUND.get(kt, ""),
        })
    return sorted(zeilen, key=lambda z: (-z["stufe"], -z["anlagen"], z["kanton"]))


STUFEN_TEXT = {
    3: "Anlagen mit Datum **und** Baugesuche",
    2: "datierte Belege",
    1: "Anlagen ohne Datum",
    0: "nur GWR",
}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--out", default=str(config.ROOT / "reports" / "quellenmatrix.md"))
    a = p.parse_args(argv)

    con = pipeline.connect(schreibend=False)
    stand = con.execute("SELECT max(stand) FROM silver_gebaeude_ch").fetchone()[0]
    zeilen = sammeln(con)

    text = [
        "# Quellenmatrix: Welche Daten gibt es in welchem Kanton?",
        "",
        f"Stand {stand.strftime('%d.%m.%Y')}. Die Tabelle zeigt je Kanton, welche offenen "
        "Daten neben dem GWR vorliegen (Wärmenutzungsanlagen, Heizungs-Baugesuche) und "
        "welche Prüfung des Registers damit möglich ist.",
        "",
        "Das GWR deckt die ganze Schweiz ab. Alles, womit sich das GWR **prüfen** lässt, "
        "gibt es nur stellenweise. Die Tabelle sagt deshalb weniger über die Kantone "
        "aus als über die Grenzen dieser Auswertung.",
        "",
        "| Kanton | Gebäude | Anlagen | davon datiert | Heizungs-Baugesuche "
        "| Quelle der Baugesuche | Stufe |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for z in zeilen:
        text.append(
            f"| {z['kanton']} | {fmt.tsd(z['gebaeude'])} | "
            f"{fmt.tsd(z['anlagen']) if z['anlagen'] else '–'} | "
            f"{fmt.tsd(z['anlagen_datiert']) if z['anlagen_datiert'] else '–'} | "
            f"{fmt.tsd(z['baugesuche_heizung']) if z['baugesuche_heizung'] else '–'} | "
            f"{BAUGESUCHE_TXT[z['baugesuch_quelle']]} | {z['stufe']} |")

    verteilung = {s: sum(1 for z in zeilen if z["stufe"] == s) for s in (3, 2, 1, 0)}
    text += [
        "",
        "## Die vier Stufen",
        "",
        "| Stufe | Was möglich ist | Kantone |",
        "|---|---|---:|",
        f"| 3 | {STUFEN_TEXT[3]}: auch Anlagen ohne Bohrung werden sichtbar | {verteilung[3]} |",
        f"| 2 | {STUFEN_TEXT[2]}: \"seit wann nicht nachgeführt\" ist beantwortbar | {verteilung[2]} |",
        f"| 1 | {STUFEN_TEXT[1]}: Widersprüche sichtbar, aber nicht datierbar | {verteilung[1]} |",
        f"| 0 | {STUFEN_TEXT[0]}: sichtbar ist, wie gepflegt das Register aussieht, nicht ob es stimmt | {verteilung[0]} |",
        "",
        "**Diese Ungleichheit begrenzt jeden Kantonsvergleich der Studie.** Ein Kanton auf "
        f"Stufe 0 (davon gibt es {verteilung[0]}) kann in keiner Rangliste schlecht "
        "abschneiden, weil eine Gegenquelle fehlt. Umgekehrt sieht ein Kanton mit guter "
        "Datenlage zwangsläufig schlechter aus, weil nur bei ihm etwas gefunden werden "
        "kann. Jede Kantonsrangliste der Studie ist deshalb zuerst eine Rangliste der "
        "Datenoffenheit.",
        "",
        "## Befund je Kanton",
        "",
        "| Kanton | Stufe | Befund |",
        "|---|---|---|",
    ]
    for z in sorted(zeilen, key=lambda x: x["kanton"]):
        text.append(f"| {z['kanton']} | {z['stufe']} | {z['befund']} |")
    text += [
        "",
        "Die Suche umfasst den nationalen Metadatenkatalog geocat.ch (deutsch, "
        "französisch, italienisch), opendata.swiss, den Themenkatalog von geodienste.ch "
        "und einen Endpunkt-Scan aller 26 Kantone. Ein leerer Befund heisst \"auf diesen "
        "Wegen nicht gefunden\", nicht \"existiert nicht\".",
        "",
    ]

    ziel = config.ROOT / a.out if not str(a.out).startswith(str(config.ROOT)) else a.out
    Path(ziel).write_text(fmt.de("\n".join(text)), encoding="utf-8")
    print(f"{len(zeilen)} Kantone, Stufenverteilung "
          f"3:{verteilung[3]} 2:{verteilung[2]} 1:{verteilung[1]} 0:{verteilung[0]}")
    print(f"geschrieben: {ziel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
