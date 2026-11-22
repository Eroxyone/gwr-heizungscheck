"""Formatierung fuer die Reports: deutsches Dezimalkomma und Markdown-Tabellen.

Die Zahlen kommen als Punktzahlen aus der Pipeline, die Reports sollen sie mit Komma
zeigen. Was dabei NICHT angefasst werden darf: URLs, Abschnittsnummern und alles in
Backticks - dort stehen Modellnamen wie qwen2.5:7b, Versionen und Pfade.
"""
from __future__ import annotations

import re

import pandas as pd

# Code-Spans und Datumsangaben bleiben unangetastet. Das Datum musste nachtraeglich
# dazu: "Stand 14.09.2026" wurde zu "Stand 14,09,2026", weil ein Schweizer Datum
# nun einmal aussieht wie zwei Dezimalzahlen hintereinander.
_CODE = re.compile(r"`[^`]*`|\d{1,2}\.\d{1,2}\.\d{4}")
# Zahl mit Dezimalpunkt, aber nicht nach "Abschnitt"/"Test"/"Kapitel" - dort sind es
# Gliederungsnummern, keine Zahlen.
_ZAHL = re.compile(r"(?<!Abschnitt \d)(?<!Kapitel \d)(?<!Test \d)(?<=\d)\.(?=\d)")


def de(text) -> str:
    """Dezimalpunkt zu Komma, aber nur dort, wo es wirklich eine Zahl ist."""
    zeilen = []
    for zeile in str(text).split("\n"):
        if "http" in zeile or zeile.lstrip().startswith("#"):
            zeilen.append(zeile)
            continue
        # Code-Spans und Daten ausklammern, damit qwen2.5:7b, Pfade und
        # "14.09.2026" unveraendert bleiben
        teile, pos = [], 0
        for treffer in _CODE.finditer(zeile):
            teile.append(_ZAHL.sub(",", zeile[pos:treffer.start()]))
            teile.append(treffer.group(0))
            pos = treffer.end()
        teile.append(_ZAHL.sub(",", zeile[pos:]))
        zeilen.append("".join(teile))
    return "\n".join(zeilen)


def md(df: pd.DataFrame, prozent_als_float: bool = True) -> str:
    """Markdown-Tabelle mit deutschem Dezimalkomma.

    Spalten ohne echte Nachkommastellen werden als Ganzzahl gesetzt - ausser
    Prozent- und Indexspalten, dort bleibt die Nachkommastelle der Vergleichbarkeit
    wegen stehen. Int64 (nullable) statt int64 ist noetig, weil tabulate sonst das
    floatfmt der Prozentspalten auch auf die Ganzzahlen anwendet.
    """
    df = df.copy()
    for spalte in df.columns:
        werte = df[spalte]
        name = str(spalte)
        ist_prozent = prozent_als_float and ("%" in name or "Index" in name
                                             or name in ("Precision", "Recall", "F1"))
        if (pd.api.types.is_numeric_dtype(werte)
                and not pd.api.types.is_bool_dtype(werte)
                and not ist_prozent
                and werte.dropna().eq(werte.dropna().round()).all()):
            df[spalte] = werte.astype("Int64")
    return de(df.to_markdown(index=False, floatfmt=".1f"))


def skalar(wert) -> str:
    """Einzelwert fuer den Fliesstext, mit deutschem Dezimalkomma."""
    return de(f"{wert}")


def tsd(n) -> str:
    """Tausendertrennung mit Apostroph, wie in der Schweiz ueblich."""
    return f"{int(n):,}".replace(",", "'")
