"""Zeitreihe als Bild: Wie viele Heizungseintraege bewegt ein Kanton pro Woche?

Liest v_gold_veraenderung (gold.sql) und zeichnet je Kanton die Aenderungsrate des
Energietraegers je Snapshot-Woche, in Promille der verglichenen Gebaeude. Dazu, falls
gold_liste_archiv Staende enthaelt, die Korrekturen der Listenfaelle je Kanton.

    python src/plot_zeitreihe.py            # schreibt reports/zeitreihe.png und reports/zeitreihe.md

Das Bild gehoert ins README. Die Tabelle daneben haelt die Zahlen fest, die im Bild nur
geschaetzt ablesbar sind.
"""
from __future__ import annotations

import duckdb
import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.ticker  # noqa: E402

import config  # noqa: E402
import pipeline  # noqa: E402

AUS = config.REPORTS / "zeitreihe.png"
TAB = config.REPORTS / "zeitreihe.md"


def lade(con) -> tuple[pd.DataFrame, pd.DataFrame]:
    bewegung = con.execute("""
        SELECT kanton, stand_alt, stand_neu, gebaeude_verglichen, traeger_geaendert,
               round(1000.0 * traeger_geaendert / gebaeude_verglichen, 2) AS promille
        FROM v_gold_veraenderung
        WHERE stand_alt IS NOT NULL AND stand_neu - stand_alt >= 5   -- echte Wochen, kein Doppelabzug
        ORDER BY kanton, stand_neu""").df()
    # Das Archiv der Liste entsteht erst im vollen Lauf. Wer nur den schweizweiten Strang
    # rechnet, bekommt Diagramm und Tabelle der Bewegung, ohne den Abschnitt zur Liste.
    if not pipeline.hat(con, "gold_liste_archiv", "v_gold_liste_korrigiert"):
        return bewegung, pd.DataFrame()
    korrigiert = con.execute("""
        SELECT a.kanton, a.stand AS listenstand, count(*) AS auf_der_liste,
               count(k.egid) AS korrigiert,
               count(k.egid) FILTER (WHERE k.vorschlag_trifft) AS vorschlag_trifft
        FROM gold_liste_archiv a
        LEFT JOIN v_gold_liste_korrigiert k ON k.egid = a.egid AND k.listenstand = a.stand
        WHERE a.stand = (SELECT min(stand) FROM gold_liste_archiv)
        GROUP BY 1, 2 HAVING count(k.egid) > 0 OR count(*) >= 100
        ORDER BY korrigiert DESC, auf_der_liste DESC""").df()
    return bewegung, korrigiert


# Kantone, die im Beobachtungszeitraum eine Sammelnachfuehrung zeigen, bekommen eine
# eigene Linie; alle uebrigen laufen zusammen als eine graue Vergleichslinie. Wer
# hervorgehoben wird, entscheidet die Schwelle, nicht eine feste Liste - ein Kanton,
# der spaeter nachzieht, erscheint von selbst.
SCHWELLE_PROMILLE = 5.0
FARBEN = ["#2a78d6", "#eb6834", "#1baf7a"]      # feste Reihenfolge, validiert (dataviz)
GRAU, TEXT, TEXT2, RASTER, FLAECHE = "#8a897f", "#0b0b0b", "#52514e", "#e6e5e0", "#fcfcfb"


def zeichne(bewegung: pd.DataFrame) -> None:
    spitze = bewegung.groupby("kanton")["promille"].max().sort_values(ascending=False)
    # Alphabetisch, nicht nach Rang: Die Farbe gehoert zum Kanton und darf nicht wechseln,
    # wenn naechste Woche ein anderer Kanton den hoechsten Ausschlag hat.
    vorn = sorted(spitze[spitze >= SCHWELLE_PROMILLE].index[:len(FARBEN)])
    rest = bewegung[~bewegung["kanton"].isin(vorn)]
    rest_reihe = (rest.groupby("stand_neu")
                  .apply(lambda g: 1000.0 * g["traeger_geaendert"].sum()
                         / g["gebaeude_verglichen"].sum(), include_groups=False))

    fig, ax = plt.subplots(figsize=(10, 5.2), dpi=150, facecolor=FLAECHE)
    ax.set_facecolor(FLAECHE)
    ax.plot(rest_reihe.index, rest_reihe.values, color=GRAU, lw=2, solid_capstyle="round",
            label=f"übrige {bewegung['kanton'].nunique() - len(vorn)} Kantone zusammen")
    for kanton, farbe in zip(vorn, FARBEN, strict=False):
        reihe = bewegung[bewegung["kanton"] == kanton].set_index("stand_neu")["promille"]
        ax.plot(reihe.index, reihe.values, color=farbe, lw=2, solid_capstyle="round",
                solid_joinstyle="round", label=f"Kanton {kanton}")
        # Direktes Etikett am Hoechstwert: Am rechten Rand laufen die Linien zusammen,
        # dort wuerden sich Endetiketten ueberdecken.
        wann, wert = reihe.idxmax(), reihe.max()
        absolut = int(bewegung[(bewegung["kanton"] == kanton)
                               & (bewegung["stand_neu"] == wann)]["traeger_geaendert"].iloc[0])
        ax.plot([wann], [wert], "o", ms=8, color=farbe, mec=FLAECHE, mew=2, zorder=5)
        links = wann == reihe.index.min()
        rechts = wann == reihe.index.max()
        ax.annotate(f"{kanton}: {absolut:,}".replace(",", "'") + " Einträge",
                    (wann, wert), xytext=(8 if links else (-8 if rechts else 0), 9),
                    textcoords="offset points", color=TEXT, fontsize=9,
                    ha="left" if links else ("right" if rechts else "center"))
    ax.set_xticks(sorted(bewegung["stand_neu"].unique()))
    ax.set_xticklabels([f"{pd.Timestamp(w):%d.%m.}" for w in sorted(bewegung["stand_neu"].unique())],
                       color=TEXT2, fontsize=9)
    ax.tick_params(axis="y", colors=TEXT2, labelsize=9, length=0)
    ax.tick_params(axis="x", length=0)
    ax.set_ylim(0, None)
    ax.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(5))
    ax.margins(x=0.04, y=0.14)
    ax.set_ylabel("geänderte Energieträger je 1'000 Gebäude", color=TEXT2, fontsize=9)
    ax.set_xlabel("Woche bis", color=TEXT2, fontsize=9)
    ax.set_title("Das GWR wird in Wellen nachgeführt: Änderungen der Heizungsangabe je Woche",
                 color=TEXT, fontsize=12, loc="left", pad=14)
    ax.legend(frameon=False, fontsize=9, labelcolor=TEXT2, loc="upper center",
              ncol=len(vorn) + 1, bbox_to_anchor=(0.5, -0.14), handlelength=1.6)
    for seite in ("top", "right", "left"):
        ax.spines[seite].set_visible(False)
    ax.spines["bottom"].set_color(RASTER)
    ax.grid(axis="y", color=RASTER, lw=1)
    ax.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(AUS, facecolor=FLAECHE)


def schreibe_tabelle(bewegung: pd.DataFrame, korrigiert: pd.DataFrame) -> None:
    piv = (bewegung.pivot(index="kanton", columns="stand_neu", values="traeger_geaendert")
           .fillna(0).astype(int))
    piv.columns = [f"bis {pd.Timestamp(c):%d.%m.}" for c in piv.columns]
    piv["Gebäude"] = bewegung.groupby("kanton")["gebaeude_verglichen"].last()
    piv["je 1'000 und Woche"] = bewegung.groupby("kanton")["promille"].mean().round(2)
    piv = piv.sort_values("je 1'000 und Woche", ascending=False)
    zeilen = ["# Zeitreihe: Bewegung im Register je Woche", "",
              f"Stand {pd.Timestamp(bewegung['stand_neu'].max()):%d.%m.%Y}. Quelle: "
              "`v_gold_veraenderung`, Energieträger (GENH1) zwischen zwei Wochen-Snapshots "
              "verglichen, alle Einträge des Registers unabhängig vom Gebäudestatus.", "",
              "![Zeitreihe](zeitreihe.png)", "",
              "| Kanton | " + " | ".join(piv.columns) + " |",
              "|---|" + "---:|" * len(piv.columns)]
    for k, r in piv.iterrows():
        zellen = [f"{r[c]:.2f}" if c == "je 1'000 und Woche"
                  else f"{int(r[c]):,}".replace(",", "'") for c in piv.columns]
        zeilen.append(f"| {k} | " + " | ".join(zellen) + " |")
    if len(korrigiert):
        zeilen += ["", "## Was mit der Liste geschah", "",
                   f"Liste vom {pd.Timestamp(korrigiert['listenstand'].iloc[0]):%d.%m.%Y}, "
                   "Fälle, die in einem späteren Snapshot nicht mehr fossil eingetragen sind "
                   "(`v_gold_liste_korrigiert`).", "",
                   "| Kanton | auf der Liste | seither korrigiert | Vorschlag traf |",
                   "|---|---:|---:|---:|"]
        for _, r in korrigiert.iterrows():
            zeilen.append(f"| {r.kanton} | {int(r.auf_der_liste):,} | {int(r.korrigiert)} | "
                          f"{int(r.vorschlag_trifft)} |".replace(",", "'"))
    TAB.write_text("\n".join(zeilen) + "\n", encoding="utf-8")


def main() -> None:
    con = duckdb.connect(str(config.DB), read_only=True)
    bewegung, korrigiert = lade(con)
    if bewegung.empty:
        raise SystemExit("v_gold_veraenderung ist leer: mindestens zwei Snapshot-Staende noetig")
    zeichne(bewegung)
    schreibe_tabelle(bewegung, korrigiert)
    print(f"geschrieben: {AUS}\n             {TAB}")


if __name__ == "__main__":
    main()
