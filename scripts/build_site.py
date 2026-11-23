"""Website der Studie bauen.

Erzeugt aus der Startseite in site/, den Berichten in reports/ und docs/ und den beiden
bestehenden HTML-Berichten eine statische Website mit gemeinsamer Navigation:

    python scripts/build_site.py              # schreibt nach _site/
    python scripts/build_site.py --ziel PFAD  # anderswohin

Die Markdown-Berichte bleiben die Quelle; hier werden sie nur umgewandelt. Verweise auf
andere Berichte zeigen danach auf deren HTML-Seite, Verweise auf Code und Daten ins
Repository. Ein Verweis, der ins Leere geht, bricht den Bau ab.

Das Zeitreihendiagramm der Startseite entsteht aus der Tabelle in reports/zeitreihe.md,
damit Seite und Bericht dieselben Zahlen zeigen.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import os
import re
import shutil
import sys
from pathlib import Path

from markdown_it import MarkdownIt

ROOT = Path(__file__).resolve().parents[1]
QUELLE = ROOT / "site"
REPO = "https://github.com/Eroxyone/gwr-heizungscheck"
ADRESSE = "https://eroxyone.github.io/gwr-heizungscheck/"
NAME = "GWR-Heizungscheck"
BESCHREIBUNG = ("Validierungsstudie: Lassen sich veraltete Heizungsangaben im eidgenössischen "
                "Gebäude- und Wohnungsregister aus offenen Daten erkennen?")

# Berichte, die als Seite erscheinen, mit ihrem Kurznamen. Der Seitentitel kommt aus der
# ersten Überschrift; der Kurzname ersetzt Verweistexte wie "methode.md", die im Repository
# den Dateinamen nennen.
BERICHTE = {
    "docs/befunde.md": "Befunde im Detail",
    "docs/methode.md": "Methode",
    "docs/datenquellen.md": "Datenquellen",
    "reports/zeitreihe.md": "Zeitreihe",
    "reports/belegwirkung.md": "Belegwirkung",
    "reports/kantonsvergleich.md": "Kantonsvergleich",
    "reports/report.md": "Detailauswertung Zürich",
    "reports/zuordnung_zg.md": "Genauigkeit der Zuordnung",
    "reports/extraktion_evaluation.md": "Auswertung der Baugesuchstexte",
    "reports/precision.md": "Vorstufe der Messung",
    "reports/groundtruth.md": "Vergleichsdaten Genf und Zug",
    "reports/quellenmatrix.md": "Quellenmatrix",
    "reports/quellenvergleich.md": "Quellenvergleich",
    "reports/lizenzen.md": "Lizenzlage",
}
# Bestehende HTML-Berichte: Sie werden übernommen und bekommen Navigation, Titel und
# Metadaten der Website.
HTML_BERICHTE = {
    "reports/dashboard.html": ("Dashboard", "Pflege-Index der Heizungsangaben im GWR für 26 Kantone "
                               "und 2'110 Gemeinden, Stand 14.09.2026."),
    "reports/befund.html": ("Zwischenbericht", "Der Stand der Studie vom 14.09.2026 auf einer Seite, "
                            "vor der Messung der Belegwirkung und vor der Zeitreihe."),
}
# Was unverändert mitkommt: Ziel -> Quelle.
KOPIEN = {
    "reports/zeitreihe.png": "reports/zeitreihe.png",
    "reports/dashboard.png": "reports/dashboard.png",
    "reports/dashboard_daten.js": "reports/dashboard_daten.js",
    "reports/befund_daten.js": "reports/befund_daten.js",
    "site.css": "site/site.css",
    "schriften.css": "site/schriften.css",
    "navigation.css": "site/navigation.css",
    "favicon.svg": "site/favicon.svg",
    # Schriften liegen bei der Website selbst, mit ihren Lizenzen
    **{f"fonts/{p.name}": f"site/fonts/{p.name}" for p in sorted((QUELLE / "fonts").iterdir())},
}
NAVIGATION = [
    ("Ergebnis", "index.html"),
    ("Dashboard", "reports/dashboard.html"),
    ("Berichte", "index.html#berichte"),
    ("Methode", "docs/methode.html"),
    ("Datenquellen", "docs/datenquellen.html"),
]


class Baufehler(Exception):
    pass


def seitenpfad(md: str) -> str:
    """reports/zeitreihe.md -> reports/zeitreihe.html"""
    return md[:-3] + ".html"


def relativ(von_seite: str, ziel: str) -> str:
    """Pfad von einer Seite zu einem Ziel, beide relativ zur Wurzel der Website."""
    anker = ""
    if "#" in ziel:
        ziel, anker = ziel.split("#", 1)
        anker = "#" + anker
    start = os.path.dirname(von_seite) or "."
    return Path(os.path.relpath(ziel, start)).as_posix() + anker


# ---------------------------------------------------------------- Rahmen jeder Seite

def stil(seite: str, datei: str) -> str:
    """Verweis auf ein Stylesheet mit kurzem Fingerabdruck, damit Browser nach einer
    Änderung neu laden statt eine zwischengespeicherte Fassung zu zeigen."""
    version = hashlib.sha256((QUELLE / datei).read_bytes()).hexdigest()[:8]
    return f'<link rel="stylesheet" href="{relativ(seite, datei)}?v={version}">'


def navigation(seite: str) -> str:
    punkte = []
    for text, ziel in NAVIGATION:
        aktiv = ' aria-current="page"' if ziel == seite else ""
        punkte.append(f'<li><a href="{relativ(seite, ziel)}"{aktiv}>{text}</a></li>')
    punkte.append(f'<li><a href="{REPO}">Code auf GitHub</a></li>')
    return (f'<nav class="nav" aria-label="Hauptnavigation"><div class="huelle">'
            f'<a class="nav-marke" href="{relativ(seite, "index.html")}">{NAME}</a>'
            f'<ul>{"".join(punkte)}</ul></div></nav>')


def fuss_absaetze(seite: str) -> str:
    return (f'<p>Code unter der MIT-Lizenz, Berichte und Texte unter CC BY 4.0. Die Quelldaten gehören '
            f'ihren Herausgebern; was davon weiterverwendet werden darf, steht in der '
            f'<a href="{relativ(seite, "reports/lizenzen.html")}">Lizenzlage</a>.</p>'
            f'<p>Quelltext, Anleitung zum Nachrechnen und Zitierangaben im '
            f'<a href="{REPO}">Repository auf GitHub</a>. Fragen und Hinweise gern als '
            f'<a href="{REPO}/issues">Issue</a>.</p>')


def fuss(seite: str) -> str:
    return f'<footer class="fuss fuss-website"><div class="huelle">{fuss_absaetze(seite)}</div></footer>'


def metadaten(seite: str, titel: str, beschreibung: str) -> str:
    """Titel, Beschreibung, Vorschau beim Teilen, kanonische Adresse und Symbol einer Seite."""
    voll = NAME if seite == "index.html" else f"{titel} - {NAME}"
    adresse = ADRESSE + ("" if seite == "index.html" else seite)
    return f"""<title>{html.escape(voll)}</title>
<meta name="description" content="{html.escape(beschreibung)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{html.escape(voll)}">
<meta property="og:description" content="{html.escape(beschreibung)}">
<meta property="og:url" content="{adresse}">
<meta property="og:image" content="{ADRESSE}reports/zeitreihe.png">
<meta property="og:image:width" content="1500">
<meta property="og:image:height" content="780">
<meta property="og:image:alt" content="Änderungen der Heizungsangabe je Woche: Zürich, Aargau und Basel-Landschaft gegen die übrigen Kantone">
<meta name="twitter:card" content="summary_large_image">
<meta name="color-scheme" content="light dark">
<link rel="canonical" href="{adresse}">
<link rel="icon" href="{relativ(seite, 'favicon.svg')}" type="image/svg+xml">
{stil(seite, 'schriften.css')}
{stil(seite, 'navigation.css')}"""


def rahmen(seite: str, titel: str, beschreibung: str, inhalt: str) -> str:
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
{metadaten(seite, titel, beschreibung)}
{stil(seite, 'site.css')}
</head>
<body>
<a class="sprung" href="#inhalt">Zum Inhalt</a>
{navigation(seite)}
{inhalt}
{fuss(seite)}
</body>
</html>
"""


# ---------------------------------------------------------------- Markdown-Berichte

_UMLAUT = str.maketrans({"ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss"})


def anker(text: str, vergeben: set[str]) -> str:
    kern = re.sub(r"[^a-z0-9]+", "-", text.lower().translate(_UMLAUT)).strip("-") or "abschnitt"
    name, n = kern, 2
    while name in vergeben:
        name, n = f"{kern}-{n}", n + 1
    vergeben.add(name)
    return name


def verweis(md: str, ziel: str, seiten: set[str], dateien: set[str], bild: bool = False) -> str:
    """Schreibt einen Verweis aus einem Markdown-Bericht für die Website um."""
    if re.match(r"^(https?:|mailto:|#)", ziel):
        return ziel
    pfad, _, sprung = ziel.partition("#")
    sprung = "#" + sprung if sprung else ""
    absolut = (ROOT / md).parent.joinpath(pfad).resolve()
    try:
        rel = absolut.relative_to(ROOT).as_posix()
    except ValueError as e:
        raise Baufehler(f"{md}: Verweis verlässt das Repository: {ziel}") from e
    seite = seitenpfad(md)
    if rel == "README.md":                  # im Repository die Übersicht, hier die Startseite
        return relativ(seite, "index.html") + sprung
    if rel in seiten:
        return relativ(seite, seitenpfad(rel)) + sprung
    if rel in dateien:
        return relativ(seite, rel) + sprung
    if bild:
        raise Baufehler(f"{md}: Bild {ziel} fehlt in KOPIEN")
    if not absolut.exists():
        raise Baufehler(f"{md}: Verweis ins Leere: {ziel}")
    art = "tree" if absolut.is_dir() else "blob"
    return f"{REPO}/{art}/main/{rel}{sprung}"


_ADRESSE = re.compile(r"https?://[^\s<>\"]+[^\s<>\".,;:)]")


def adressen_verlinken(koerper: str) -> str:
    """Macht ausgeschriebene Adressen im Fliesstext anklickbar, wie GitHub es beim Anzeigen tut.

    Text innerhalb von Verweisen und Code bleibt unberührt.
    """
    teile, tiefe = [], 0
    for stueck in re.split(r"(<[^>]+>)", koerper):
        if stueck.startswith("<"):
            name = re.match(r"</?(\w+)", stueck)
            if name and name.group(1) in ("a", "code", "pre"):
                tiefe += -1 if stueck.startswith("</") else 1
        elif tiefe == 0:
            stueck = _ADRESSE.sub(lambda m: f'<a href="{m.group(0)}">{m.group(0)}</a>', stueck)
        teile.append(stueck)
    return "".join(teile)


_DATEINAME = re.compile(r"^(\.\./)?([\w-]+/)*[\w-]+\.(md|html)(#[\w-]+)?$")


def verweistexte_benennen(md: str, kinder: list) -> None:
    """Ein Verweis, dessen Text nur der Dateiname eines Berichts ist ("methode.md"), bekommt
    auf der Website den Kurznamen der Seite als Text."""
    for i, k in enumerate(kinder[:-2]):
        if k.type != "link_open" or kinder[i + 2].type != "link_close":
            continue
        text = kinder[i + 1]
        if text.type not in ("text", "code_inline") or not _DATEINAME.match(text.content):
            continue
        ziel = (ROOT / md).parent.joinpath((k.attrGet("href") or "").partition("#")[0]).resolve()
        rel = ziel.relative_to(ROOT).as_posix() if ziel.is_relative_to(ROOT) else ""
        name = BERICHTE.get(rel) or HTML_BERICHTE.get(rel, (None,))[0]
        if name:
            text.type, text.tag, text.markup, text.content = "text", "", "", name


_ERZEUGT = re.compile(r"\s*<p>Erzeugt von .*?</p>\n?", re.S)


def typografie(koerper: str) -> str:
    """Schweizer Satzregeln im Fliesstext: geschütztes Leerzeichen vor Prozent und Promille,
    Datum als TT.MM.JJJJ, Tausendertrenner in Tabellenzellen, kein Umbruch in "SHA-256".

    Code, vorformatierter Text und Skripte bleiben unberührt.
    """
    teile, tiefe, letztes_tag = [], 0, ""
    for stueck in re.split(r"(<[^>]+>)", koerper):
        if stueck.startswith("<"):
            name = re.match(r"</?(\w+)", stueck)
            if name and name.group(1) in ("code", "pre", "script", "style"):
                tiefe += -1 if stueck.startswith("</") else 1
            letztes_tag = stueck
        elif tiefe == 0 and stueck:
            stueck = re.sub(r"(\d) ([%‰])", "\\1&nbsp;\\2", stueck)
            stueck = re.sub(r"\b(20\d\d)-([01]\d)-([0-3]\d)\b", r"\3.\2.\1", stueck)
            stueck = stueck.replace("SHA-256", "SHA‑256").replace(" – ", " - ")
            # Gerade Anführungszeichen um ein Zitat oder einen Begriff werden zu Guillemets.
            stueck = re.sub(r'(?:&quot;|")([^"<>&\n]{1,90}?)(?:&quot;|")', "«\\1»", stueck)
            if letztes_tag.startswith("<td") and re.fullmatch(r"\d{5,}", stueck.strip()):
                stueck = f"{int(stueck):,}".replace(",", "'")
        teile.append(stueck)
    return "".join(teile)


def tabellen_ordnen(koerper: str) -> str:
    """Tabellenköpfe gelten für ihre Spalte; eine ausgeschriebene Adresse in einer Zelle wird
    als Verweis mit dem Namen des Servers gezeigt, damit die Spalte nicht zerbricht."""
    koerper = re.sub(r"<th(?![^>]*\bscope=)", '<th scope="col"', koerper)

    def kurz(m: re.Match) -> str:
        adresse, text = m.group(1), m.group(2)
        if text != adresse:
            return m.group(0)
        server = re.sub(r"^https?://", "", adresse).split("/", 1)[0]
        return f'<a href="{adresse}" title="{adresse}">{server}</a>'

    def zelle(t: str) -> str:
        t = re.sub(r'<a href="([^"]+)">([^<]+)</a>', kurz, t)
        # Zellen mit viel Text bekommen auf schmalen Bildschirmen mehr Breite (site.css).
        if len(html.unescape(re.sub(r"<[^>]+>", "", t))) > 60:
            t = re.sub(r"^<td\b", '<td class="lang"', t)
        return t

    teile = re.split(r"(<td\b.*?</td>)", koerper, flags=re.S)
    return "".join(zelle(t) if t.startswith("<td") else t for t in teile)


def bericht(md: str, seiten: set[str], dateien: set[str]) -> tuple[str, str]:
    """Wandelt einen Markdown-Bericht um. Gibt Titel und fertige Seite zurück."""
    parser = MarkdownIt("commonmark").enable("table")
    tokens = parser.parse((ROOT / md).read_text(encoding="utf-8"))
    titel, kapitel, vergeben = "", [], set()
    for i, t in enumerate(tokens):
        if t.type == "heading_open":
            text = "".join(k.content for k in tokens[i + 1].children or []
                           if k.type in ("text", "code_inline"))
            if t.tag == "h1" and not titel:
                titel = text
                continue
            name = anker(text, vergeben)
            t.attrSet("id", name)
            if t.tag == "h2":
                kapitel.append((name, text))
        verweistexte_benennen(md, t.children or [])
        for k in t.children or []:
            if k.type == "link_open":
                k.attrSet("href", verweis(md, k.attrGet("href"), seiten, dateien))
            elif k.type == "image":
                k.attrSet("src", verweis(md, k.attrGet("src"), seiten, dateien, bild=True))
                k.attrSet("loading", "lazy")
    if not titel:
        raise Baufehler(f"{md}: keine Überschrift erster Ordnung")
    koerper = adressen_verlinken(parser.renderer.render(tokens, parser.options, {}))
    # Der Hinweis, welches Skript den Bericht erzeugt, gehört ans Ende, nicht unter den Titel.
    erzeugt = _ERZEUGT.search(koerper)
    herkunft = ""
    if erzeugt:
        koerper = koerper.replace(erzeugt.group(0), "\n", 1)
        herkunft = " " + erzeugt.group(0).strip()[3:-4]
    koerper = tabellen_ordnen(typografie(koerper))
    # Breite Tabellen rollen in ihrem eigenen Rahmen, nicht die ganze Seite. Der Rahmen trägt
    # den Namen des Abschnitts, damit Screenreader die Tabellen unterscheiden können.
    teile, abschnitt, nummer = [], titel, {}
    for stueck in re.split(r"(<h[1-4][^>]*>.*?</h[1-4]>|<table>)", koerper, flags=re.S):
        if re.match(r"<h[1-4]", stueck):
            abschnitt = html.unescape(re.sub(r"<[^>]+>", "", stueck)).strip()
        elif stueck == "<table>":
            nummer[abschnitt] = nummer.get(abschnitt, 0) + 1
            name = abschnitt + (f", Tabelle {nummer[abschnitt]}" if nummer[abschnitt] > 1 else "")
            stueck = (f'<div class="tabelle" tabindex="0" role="region" '
                      f'aria-label="{html.escape(name)}"><table>')
        teile.append(stueck)
    koerper = "".join(teile).replace("</table>", "</table></div>")
    # Der Zeitreihenbericht zeigt dasselbe Diagramm wie die Startseite statt des Bildes fürs README.
    if md == "reports/zeitreihe.md":
        koerper, n = re.subn(r'<p><img src="zeitreihe\.png"[^>]*></p>',
                             lambda _: f'<figure class="diagramm bild">{zeitreihe_block()}</figure>', koerper)
        if n != 1:
            raise Baufehler(f"{md}: Diagramm nicht gefunden")
    koerper = re.sub(r"<p>(<img [^>]*>)</p>", r'<div class="bild">\1</div>', koerper)

    seite = seitenpfad(md)
    inhalt = ""
    if len(kapitel) >= 3:
        punkte = "".join(f'<li><a href="#{n}">{html.escape(t)}</a></li>' for n, t in kapitel)
        inhalt = (f'<nav class="inhalt" aria-labelledby="inhalt-titel">'
                  f'<p id="inhalt-titel">Auf dieser Seite</p><ul>{punkte}</ul></nav>')
    haupt = (f'<main id="inhalt" class="seite"><div class="huelle bericht">'
             f'<aside class="rand">'
             f'<p class="zurueck"><a href="{relativ(seite, "index.html#berichte")}">Alle Berichte</a></p>'
             f'{inhalt}</aside>'
             f'<article class="prosa">{koerper}'
             f'<p class="quelltext">Diese Seite entsteht aus '
             f'<a href="{REPO}/blob/main/{md}"><code>{md}</code></a> im Repository.{herkunft}</p>'
             f'</article></div></main>')
    absatz = re.search(r"<p>(.*?)</p>", koerper, re.S)
    kurz = re.sub(r"<[^>]+>", "", absatz.group(1)) if absatz else BESCHREIBUNG
    kurz = html.unescape(re.sub(r"\s+", " ", kurz)).strip()
    if len(kurz) > 200:
        kurz = kurz[:197].rsplit(" ", 1)[0] + " ..."
    return titel, rahmen(seite, titel, kurz, haupt)


# ---------------------------------------------------------------- bestehende HTML-Berichte

def html_bericht(pfad: str) -> str:
    """Übernimmt einen fertigen HTML-Bericht und gibt ihm Navigation, Titel und Metadaten
    der Website."""
    text = (ROOT / pfad).read_text(encoding="utf-8")
    if "</head>" not in text or not re.search(r"<body[^>]*>", text) or not re.search(r"<main\b", text):
        raise Baufehler(f"{pfad}: kein vollständiges HTML-Dokument")
    titel, beschreibung = HTML_BERICHTE[pfad]
    # Die Schriften bindet metadaten() ein; der Verweis für den Aufruf aus dem Repository entfällt.
    schriften = '<link rel="stylesheet" href="../site/schriften.css">'
    if schriften not in text:
        raise Baufehler(f"{pfad}: bindet site/schriften.css nicht ein")
    text = text.replace(schriften + "\n", "").replace(schriften, "")
    text = re.sub(r"<title>.*?</title>", lambda _: metadaten(pfad, titel, beschreibung), text, count=1, flags=re.S)
    text = re.sub(r"<main\b(?![^>]*\bid=)", '<main id="inhalt"', text, count=1)
    # Der eigene Fuss des Berichts bekommt die Angaben zu Lizenz und Repository dazu.
    text, n = re.subn(r'<footer class="fuss huelle">(.*?)</footer>',
                      lambda m: (f'<footer class="fuss fuss-website"><div class="huelle">{m.group(1).strip()}'
                                 f'{fuss_absaetze(pfad)}</div></footer>'), text, count=1, flags=re.S)
    if n != 1:
        raise Baufehler(f"{pfad}: Fuss nicht gefunden")
    kopf = f'<a class="sprung" href="#inhalt">Zum Inhalt</a>\n{navigation(pfad)}'

    def umgeschrieben(m: re.Match) -> str:
        ziel = (ROOT / pfad).parent.joinpath(m.group(1)).resolve().relative_to(ROOT).as_posix()
        if ziel == "README.md":             # im Repository die Übersicht, hier die Startseite
            return f'<a href="{relativ(pfad, "index.html")}{m.group(2) or ""}">{m.group(3)}</a>'
        if ziel not in BERICHTE:
            raise Baufehler(f"{pfad}: Verweis auf {m.group(1)}, das keine Seite der Website ist")
        linktext = m.group(3)
        if _DATEINAME.match(linktext):          # Dateiname als Text wird zum Namen der Seite
            linktext = BERICHTE[ziel]
        return f'<a href="{relativ(pfad, seitenpfad(ziel))}{m.group(2) or ""}">{linktext}</a>'

    # Im Repository zeigen die Verweise auf die Markdown-Fassung, hier auf die Seite daraus.
    text = re.sub(r'<a href="([^":#]+\.md)(#[^"]*)?">([^<]*)</a>', umgeschrieben, text)
    if re.search(r'href="[^":#]+\.md[#"]', text):
        raise Baufehler(f"{pfad}: Verweis auf eine Markdown-Datei mit unerwartetem Aufbau")
    return re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + "\n" + kopf, text, count=1)


# ---------------------------------------------------------------- Zeitreihendiagramm

HERVOR = ["AG", "BL", "ZH"]     # Kantone mit eigener Linie; alle übrigen laufen zusammen


def zeitreihe_daten() -> tuple[list[str], dict[str, list[float]], dict[str, list[int]], int]:
    """Liest die Tabelle aus reports/zeitreihe.md: Wochen, Promille je Reihe, Anzahl je Reihe."""
    zeilen = [z for z in (ROOT / "reports/zeitreihe.md").read_text(encoding="utf-8").splitlines()
              if z.startswith("|")]
    kopf = [z.strip() for z in zeilen[0].strip("|").split("|")]
    spalten_woche = [i for i, k in enumerate(kopf) if k.startswith("bis ")]
    wochen = [kopf[i].removeprefix("bis ").strip() for i in spalten_woche]
    if kopf[0] != "Kanton" or "Gebäude" not in kopf or len(wochen) < 2:
        raise Baufehler("reports/zeitreihe.md: Tabelle der Bewegung nicht erkannt")
    spalte_geb = kopf.index("Gebäude")
    anzahl: dict[str, list[int]] = {}
    gebaeude: dict[str, int] = {}
    for z in zeilen[2:]:
        zellen = [c.strip().replace("'", "") for c in z.strip("|").split("|")]
        if len(zellen) != len(kopf):
            break                                   # die zweite Tabelle des Berichts beginnt
        anzahl[zellen[0]] = [int(zellen[i]) for i in spalten_woche]
        gebaeude[zellen[0]] = int(zellen[spalte_geb])
    if not set(HERVOR) <= set(anzahl):
        raise Baufehler("reports/zeitreihe.md: hervorgehobene Kantone fehlen")
    rest = [k for k in anzahl if k not in HERVOR]
    anzahl["rest"] = [sum(anzahl[k][i] for k in rest) for i in range(len(wochen))]
    gebaeude["rest"] = sum(gebaeude[k] for k in rest)
    promille = {k: [1000.0 * n / gebaeude[k] for n in anzahl[k]] for k in [*HERVOR, "rest"]}
    return wochen, promille, anzahl, len(rest)


def _schneidet(kasten: tuple[float, float, float, float], linien: list[list[tuple[float, float]]]) -> bool:
    """Trifft eine der Linien den Kasten? Geprüft an dicht gesetzten Punkten je Strecke."""
    x0, y0, x1, y1 = kasten
    for linie in linien:
        for (ax, ay), (bx, by) in zip(linie, linie[1:], strict=False):
            for s in range(41):
                px, py = ax + (bx - ax) * s / 40, ay + (by - ay) * s / 40
                if x0 <= px <= x1 and y0 <= py <= y1:
                    return True
    return False


def zeitreihe_svg(breite: int, hoehe: int, schrift: float, jede: int, absolut: bool = True) -> str:
    """Zeichnet das Diagramm als SVG. `jede` dünnt die Beschriftung der Wochen aus; ohne
    `absolut` nennen die Marken nur den Wert der Achse, für die schmale Fassung."""
    wochen, promille, anzahl, _ = zeitreihe_daten()
    # Rechts so viel Rand, dass die letzte Wochenbeschriftung nicht abgeschnitten wird.
    links, rechts, oben, unten = 34.0, schrift * 2.1, schrift * 2.2, schrift * 2.4
    hoechst = max(max(r) for r in promille.values())
    decke = 5 * (int(hoechst // 5) + 1)

    def x(i: int) -> float:
        return links + (breite - links - rechts) * i / (len(wochen) - 1)

    def y(wert: float) -> float:
        return oben + (hoehe - oben - unten) * (1 - wert / decke)

    teile = [f'<svg viewBox="0 0 {breite} {hoehe}" role="img" aria-labelledby="zr-titel zr-text">']
    for wert in range(0, decke + 1, 5):
        teile.append(f'<line class="zr-raster" x1="{links}" x2="{breite - rechts}" y1="{y(wert):.1f}" y2="{y(wert):.1f}"/>')
        teile.append(f'<text class="zr-achse" x="{links - 8}" y="{y(wert) + schrift * 0.34:.1f}" '
                     f'text-anchor="end" font-size="{schrift}">{wert}</text>')
    for i, woche in enumerate(wochen):
        if (len(wochen) - 1 - i) % jede == 0:
            teile.append(f'<text class="zr-achse" x="{x(i):.1f}" y="{hoehe - schrift * 0.5:.1f}" '
                         f'text-anchor="middle" font-size="{schrift}">{woche}</text>')

    punkte = {k: [(x(i), y(w)) for i, w in enumerate(r)] for k, r in promille.items()}
    for k in ["rest", *HERVOR]:
        pfad = " ".join(f"{px:.1f},{py:.1f}" for px, py in punkte[k])
        teile.append(f'<polyline class="zr-linie zr-{k.lower()}" points="{pfad}"/>')

    # Beschriftung am Höchstwert jeder hervorgehobenen Reihe. Vier Lagen werden versucht;
    # genommen wird die erste, die keine Linie und keine frühere Beschriftung trifft.
    belegt: list[tuple[float, float, float, float]] = []
    for k in HERVOR:
        i = max(range(len(wochen)), key=lambda j: promille[k][j])
        px, py = punkte[k][i]
        # Die Marke nennt den Wert in der Einheit der Achse, dazu die absolute Zahl.
        text = f"{k} {promille[k][i]:.1f}".replace(".", ",")
        if absolut:
            text += f" ({anzahl[k][i]:,})".replace(",", "'")
        b, h = len(text) * schrift * 0.58, schrift * 1.15
        lagen = [("middle", px, py - 12, px - b / 2), ("start", px + 12, py + h * 0.3, px + 12),
                 ("end", px - 12, py + h * 0.3, px - 12 - b), ("start", px + 12, py - 10, px + 12),
                 ("end", px - 12, py - 10, px - 12 - b)]
        gewaehlt = lagen[0]
        for lage in lagen:
            _, _, ty, kx = lage
            kasten = (kx, ty - h, kx + b, ty + 2)
            if kx < 0 or kx + b > breite or ty - h < 0:
                continue
            frei = not _schneidet(kasten, list(punkte.values()))
            frei = frei and not any(kasten[0] < o[2] and o[0] < kasten[2] and kasten[1] < o[3] and o[1] < kasten[3]
                                    for o in belegt)
            if frei:
                gewaehlt = lage
                belegt.append(kasten)
                break
        anker_, tx, ty, _ = gewaehlt
        teile.append(f'<circle class="zr-punkt zr-f-{k.lower()}" cx="{px:.1f}" cy="{py:.1f}" r="{schrift * 0.42:.1f}"/>')
        teile.append(f'<text class="zr-marke" x="{tx:.1f}" y="{ty:.1f}" text-anchor="{anker_}" '
                     f'font-size="{schrift * 1.12:.1f}">{text}</text>')
    teile.append("</svg>")
    return "\n".join(teile)


def zeitreihe_block() -> str:
    wochen, promille, anzahl, n_rest = zeitreihe_daten()
    namen = {"AG": "Aargau", "BL": "Basel-Landschaft", "ZH": "Zürich"}
    legende = "".join(f'<li class="l-{k.lower()}"><i></i>{namen[k]}</li>' for k in HERVOR)
    legende += f'<li class="l-rest"><i></i>übrige {n_rest} Kantone zusammen</li>'
    spitzen = "; ".join(
        f"{namen[k]} {max(anzahl[k]):,} Einträge (Woche bis {wochen[anzahl[k].index(max(anzahl[k]))]})"
        .replace(",", "'") for k in HERVOR)
    rest_max = f"{max(promille['rest']):.2f}".replace(".", ",")
    text = (f"Liniendiagramm über {len(wochen)} Wochen. Höchstwerte: {spitzen}. "
            f"Die übrigen {n_rest} Kantone kommen zusammen auf höchstens {rest_max} geänderte "
            f"Einträge je 1'000 Gebäude und Woche.")
    # Beide Fassungen sind für Screenreader verborgen; die Beschreibung hängt am Rahmen, der
    # immer sichtbar ist, gleich welche Fassung die Bildschirmbreite zeigt.
    breit = zeitreihe_svg(1000, 400, 13.5, 1).replace(
        'role="img" aria-labelledby="zr-titel zr-text"', 'aria-hidden="true" focusable="false"')
    # Auf dem Handy wird das Diagramm auf rund 340 px verkleinert; die Schrift ist so gewählt,
    # dass sie dort mindestens 12 px gross bleibt.
    schmal = zeitreihe_svg(440, 380, 16.0, 2, absolut=False).replace(
        'role="img" aria-labelledby="zr-titel zr-text"', 'aria-hidden="true" focusable="false"')
    return (f'<p class="einheit" id="zr-titel">Geänderte Energieträger je Woche und 1\'000 Gebäude</p>'
            f'<ul class="legende">{legende}</ul>'
            f'<p id="zr-text" hidden>{text}</p>'
            f'<div role="img" aria-labelledby="zr-titel zr-text">'
            f'<div class="zr-breit">{breit}</div><div class="zr-schmal">{schmal}</div></div>')


# ---------------------------------------------------------------- Bau und Prüfung

def pruefe_verweise(ziel: Path) -> list[str]:
    """Jeder interne Verweis der fertigen Website muss auf eine vorhandene Datei zeigen."""
    fehler = []
    for seite in sorted(ziel.rglob("*.html")):
        text = seite.read_text(encoding="utf-8")
        text = re.sub(r"<script\b.*?</script>", "", text, flags=re.S)   # Verweise, die erst im Browser entstehen
        ids = set(re.findall(r'\bid="([^"]+)"', text))
        for attr in re.findall(r'(?:href|src)="([^"]+)"', text):
            if re.match(r"^(https?:|mailto:|data:)", attr):
                continue
            pfad, _, sprung = attr.partition("#")
            pfad = pfad.partition("?")[0]
            datei = seite if not pfad else (seite.parent / pfad).resolve()
            if not datei.is_file():
                fehler.append(f"{seite.relative_to(ziel).as_posix()}: {attr}")
            elif sprung and datei.suffix == ".html":
                vorhanden = ids if datei == seite else set(
                    re.findall(r'\bid="([^"]+)"', datei.read_text(encoding="utf-8")))
                if sprung not in vorhanden:
                    fehler.append(f"{seite.relative_to(ziel).as_posix()}: Sprungziel fehlt: {attr}")
    return fehler


def leere_ziel(ziel: Path) -> None:
    """Leert das Zielverzeichnis, aber nur, wenn es leer ist oder eine frühere Website enthält.

    Erkennungszeichen ist die Datei .nojekyll, die jeder Bau anlegt. Ein Tippfehler bei
    --ziel löscht so keinen fremden Ordner.
    """
    if not ziel.exists():
        return
    inhalt = [k for k in ziel.iterdir() if k.name != ".git"]
    if inhalt and not (ziel / ".nojekyll").is_file():
        raise Baufehler(f"{ziel} ist nicht leer und enthält keine frühere Website; nichts gelöscht")
    for kind in inhalt:
        shutil.rmtree(kind) if kind.is_dir() else kind.unlink()


def baue(ziel: Path) -> int:
    leere_ziel(ziel)
    ziel.mkdir(parents=True, exist_ok=True)

    seiten = set(BERICHTE)
    dateien = set(KOPIEN) | set(HTML_BERICHTE)

    def schreibe(rel: str, text: str) -> None:
        pfad = ziel / rel
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(text, encoding="utf-8", newline="\n")

    start = (QUELLE / "index.html").read_text(encoding="utf-8")
    start = re.sub(r"<!--.*?-->\s*", "", start, count=1, flags=re.S)
    start = typografie(start).replace("{{ZEITREIHE}}", zeitreihe_block()).replace("{{REPO}}", REPO)
    if "{{" in start:
        raise Baufehler("site/index.html: unbekannter Platzhalter")
    schreibe("index.html", rahmen("index.html", NAME, BESCHREIBUNG, start))
    # GitHub Pages zeigt 404.html für jede unbekannte Adresse, auch in Unterordnern. Die
    # Basisadresse sorgt dafür, dass Stylesheets und Verweise dort trotzdem stimmen.
    fehlt = rahmen("404.html", "Seite nicht gefunden", BESCHREIBUNG,
                   '<main id="inhalt" class="seite"><div class="huelle"><article class="prosa">'
                   '<h1>Diese Seite gibt es nicht</h1>'
                   '<p>Die Adresse ist falsch geschrieben oder die Seite wurde umbenannt. Alle Berichte '
                   'stehen auf der <a href="index.html#berichte">Startseite</a>.</p>'
                   '</article></div></main>')
    schreibe("404.html", fehlt.replace("<head>", f'<head>\n<base href="{ADRESSE}">', 1))

    for md in BERICHTE:
        _, seite = bericht(md, seiten, dateien)
        schreibe(seitenpfad(md), seite)
    for pfad in HTML_BERICHTE:
        schreibe(pfad, html_bericht(pfad))
    for nach, von in KOPIEN.items():
        (ziel / nach).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / von, ziel / nach)
    # GitHub Pages soll die Dateien unverändert ausliefern, ohne Jekyll.
    (ziel / ".nojekyll").write_text("", encoding="utf-8")

    fehler = pruefe_verweise(ziel)
    if fehler:
        raise Baufehler("Verweise ins Leere:\n  " + "\n  ".join(fehler))
    return 1 + len(BERICHTE) + len(HTML_BERICHTE)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ziel", default=str(ROOT / "_site"))
    args = ap.parse_args()
    try:
        n = baue(Path(args.ziel))
    except Baufehler as e:
        print(f"Bau abgebrochen: {e}", file=sys.stderr)
        return 1
    print(f"{n} Seiten nach {args.ziel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
