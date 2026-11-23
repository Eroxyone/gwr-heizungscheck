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

# Berichte, die als Seite erscheinen. Der Titel kommt aus der ersten Überschrift.
BERICHTE = [
    "docs/befunde.md", "docs/methode.md", "docs/datenquellen.md",
    "reports/zeitreihe.md", "reports/belegwirkung.md", "reports/kantonsvergleich.md",
    "reports/report.md", "reports/zuordnung_zg.md", "reports/extraktion_evaluation.md",
    "reports/precision.md", "reports/groundtruth.md", "reports/quellenmatrix.md",
    "reports/quellenvergleich.md", "reports/lizenzen.md",
]
# Bestehende HTML-Berichte: Sie werden übernommen und bekommen eine Leiste zur Startseite.
HTML_BERICHTE = ["reports/dashboard.html", "reports/befund.html"]
# Was unverändert mitkommt: Ziel -> Quelle.
KOPIEN = {
    "reports/zeitreihe.png": "reports/zeitreihe.png",
    "reports/dashboard.png": "reports/dashboard.png",
    "reports/dashboard_daten.js": "reports/dashboard_daten.js",
    "reports/befund_daten.js": "reports/befund_daten.js",
    "site.css": "site/site.css",
    "favicon.svg": "site/favicon.svg",
}
NAVIGATION = [
    ("Ergebnis", "index.html"),
    ("Dashboard", "reports/dashboard.html"),
    ("Berichte", "index.html#berichte"),
    ("Methode", "docs/methode.html"),
    ("Datenquellen", "docs/datenquellen.html"),
]
SCHRIFTEN = ('<link rel="preconnect" href="https://fonts.googleapis.com">\n'
             '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n'
             '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@500;600;700'
             '&family=Source+Sans+3:ital,wght@0,400;0,600;1,400&family=IBM+Plex+Mono:wght@400;500;600'
             '&display=swap">')


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

def stil_version() -> str:
    """Kurzer Fingerabdruck des Stylesheets, damit Browser nach einer Aenderung neu laden."""
    return hashlib.sha256((QUELLE / "site.css").read_bytes()).hexdigest()[:8]


def navigation(seite: str) -> str:
    punkte = []
    for text, ziel in NAVIGATION:
        aktiv = ' aria-current="page"' if ziel == seite else ""
        punkte.append(f'<li><a href="{relativ(seite, ziel)}"{aktiv}>{text}</a></li>')
    punkte.append(f'<li><a href="{REPO}">Code auf GitHub</a></li>')
    return (f'<nav class="nav" aria-label="Hauptnavigation"><div class="huelle">'
            f'<a class="nav-marke" href="{relativ(seite, "index.html")}">{NAME}</a>'
            f'<ul>{"".join(punkte)}</ul></div></nav>')


def fuss(seite: str) -> str:
    return (f'<footer class="fuss"><div class="huelle">'
            f'<p>Code unter der MIT-Lizenz, Berichte und Texte unter CC BY 4.0. Die Quelldaten gehören '
            f'ihren Herausgebern; was davon weiterverwendet werden darf, steht in der '
            f'<a href="{relativ(seite, "reports/lizenzen.html")}">Lizenzlage</a>.</p>'
            f'<p>Quelltext, Anleitung zum Nachrechnen und Zitierangaben im '
            f'<a href="{REPO}">Repository auf GitHub</a>. Fragen und Hinweise gern als '
            f'<a href="{REPO}/issues">Issue</a>.</p>'
            f'</div></footer>')


def rahmen(seite: str, titel: str, beschreibung: str, inhalt: str) -> str:
    voll = NAME if seite == "index.html" else f"{titel} - {NAME}"
    return f"""<!doctype html>
<html lang="de">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(voll)}</title>
<meta name="description" content="{html.escape(beschreibung)}">
<meta property="og:type" content="article">
<meta property="og:title" content="{html.escape(voll)}">
<meta property="og:description" content="{html.escape(beschreibung)}">
<meta property="og:image" content="{ADRESSE}reports/zeitreihe.png">
<link rel="canonical" href="{ADRESSE}{'' if seite == 'index.html' else seite}">
<link rel="icon" href="{relativ(seite, 'favicon.svg')}" type="image/svg+xml">
{SCHRIFTEN}
<link rel="stylesheet" href="{relativ(seite, 'site.css')}?v={stil_version()}">
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
        for k in t.children or []:
            if k.type == "link_open":
                k.attrSet("href", verweis(md, k.attrGet("href"), seiten, dateien))
            elif k.type == "image":
                k.attrSet("src", verweis(md, k.attrGet("src"), seiten, dateien, bild=True))
                k.attrSet("loading", "lazy")
    if not titel:
        raise Baufehler(f"{md}: keine Überschrift erster Ordnung")
    koerper = adressen_verlinken(parser.renderer.render(tokens, parser.options, {}))
    # Breite Tabellen rollen in ihrem eigenen Rahmen, nicht die ganze Seite.
    koerper = koerper.replace("<table>", '<div class="tabelle" tabindex="0" role="region" '
                              'aria-label="Tabelle"><table>').replace("</table>", "</table></div>")
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
             f'<a href="{REPO}/blob/main/{md}"><code>{md}</code></a> im Repository.</p>'
             f'</article></div></main>')
    absatz = re.search(r"<p>(.*?)</p>", koerper, re.S)
    kurz = re.sub(r"<[^>]+>", "", absatz.group(1)) if absatz else BESCHREIBUNG
    kurz = html.unescape(re.sub(r"\s+", " ", kurz)).strip()
    if len(kurz) > 200:
        kurz = kurz[:197].rsplit(" ", 1)[0] + " ..."
    return titel, rahmen(seite, titel, kurz, haupt)


# ---------------------------------------------------------------- bestehende HTML-Berichte

LEISTE_STIL = """<style>
.zur-studie { background: var(--flaeche); border-bottom: 1px solid var(--linie); font-size: .93rem; }
.zur-studie div { max-width: var(--breite); margin: 0 auto; padding: 10px 24px; display: flex;
  flex-wrap: wrap; gap: 4px 24px; align-items: baseline; }
.zur-studie a { color: var(--text-leise); text-decoration: none; }
.zur-studie a:hover { color: var(--text); text-decoration: underline; }
.zur-studie a:first-child { font-family: Archivo, ui-sans-serif, system-ui, sans-serif; font-weight: 700;
  color: var(--text); margin-right: auto; }
.zur-studie a:focus-visible { outline: 2px solid var(--akzent); outline-offset: 3px; }
:where(a) { color: var(--akzent); }
</style>"""


def html_bericht(pfad: str) -> str:
    """Übernimmt einen fertigen HTML-Bericht und setzt die Leiste zur Studie darüber."""
    text = (ROOT / pfad).read_text(encoding="utf-8")
    punkte = "".join(f'<a href="{relativ(pfad, ziel)}">{name}</a>' for name, ziel in
                     [(NAME, "index.html"), ("Ergebnis", "index.html"), ("Berichte", "index.html#berichte"),
                      ("Methode", "docs/methode.html")])
    leiste = f'<nav class="zur-studie" aria-label="Zur Studie"><div>{punkte}<a href="{REPO}">Code auf GitHub</a></div></nav>'
    if "</head>" not in text or not re.search(r"<body[^>]*>", text):
        raise Baufehler(f"{pfad}: kein vollständiges HTML-Dokument")
    text = text.replace("</head>", LEISTE_STIL + "\n</head>", 1)

    def umgeschrieben(m: re.Match) -> str:
        ziel = (ROOT / pfad).parent.joinpath(m.group(1)).resolve().relative_to(ROOT).as_posix()
        if ziel not in BERICHTE:
            raise Baufehler(f"{pfad}: Verweis auf {m.group(1)}, das keine Seite der Website ist")
        return f'href="{relativ(pfad, seitenpfad(ziel))}{m.group(2) or ""}"'

    # Im Repository zeigen die Verweise auf die Markdown-Fassung, hier auf die Seite daraus.
    text = re.sub(r'href="([^":#]+\.md)(#[^"]*)?"', umgeschrieben, text)
    return re.sub(r"(<body[^>]*>)", lambda m: m.group(1) + "\n" + leiste, text, count=1)


# ---------------------------------------------------------------- Zeitreihendiagramm

HERVOR = ["AG", "BL", "ZH"]     # Kantone mit eigener Linie; alle übrigen laufen zusammen


def zeitreihe_daten() -> tuple[list[str], dict[str, list[float]], dict[str, list[int]], int]:
    """Liest die Tabelle aus reports/zeitreihe.md: Wochen, Promille je Reihe, Anzahl je Reihe."""
    zeilen = [z for z in (ROOT / "reports/zeitreihe.md").read_text(encoding="utf-8").splitlines()
              if z.startswith("|")]
    kopf = [z.strip() for z in zeilen[0].strip("|").split("|")]
    wochen = [k.removeprefix("bis ").strip() for k in kopf if k.startswith("bis ")]
    if kopf[0] != "Kanton" or "Gebäude" not in kopf or len(wochen) < 2:
        raise Baufehler("reports/zeitreihe.md: Tabelle der Bewegung nicht erkannt")
    spalte_geb = kopf.index("Gebäude")
    anzahl: dict[str, list[int]] = {}
    gebaeude: dict[str, int] = {}
    for z in zeilen[2:]:
        zellen = [c.strip().replace("'", "") for c in z.strip("|").split("|")]
        if len(zellen) != len(kopf):
            break                                   # die zweite Tabelle des Berichts beginnt
        anzahl[zellen[0]] = [int(c) for c in zellen[1:1 + len(wochen)]]
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


def zeitreihe_svg(breite: int, hoehe: int, schrift: float, jede: int) -> str:
    """Zeichnet das Diagramm als SVG. `jede` dünnt die Beschriftung der Wochen aus."""
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
        text = f"{k} {anzahl[k][i]:,}".replace(",", "'")
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
    spitzen = ", ".join(
        f"{namen[k]} {max(anzahl[k]):,} Einträge in der Woche bis {wochen[anzahl[k].index(max(anzahl[k]))]}"
        .replace(",", "'") for k in HERVOR)
    rest_max = f"{max(promille['rest']):.1f}".replace(".", ",")
    text = (f"Liniendiagramm über {len(wochen)} Wochen. Höchstwerte: {spitzen}. "
            f"Die übrigen {n_rest} Kantone bleiben zusammen unter {rest_max} Einträgen je 1'000 Gebäude.")
    breit = zeitreihe_svg(1000, 400, 13.5, 1)
    schmal = zeitreihe_svg(520, 380, 15.0, 2).replace('aria-labelledby="zr-titel zr-text"', 'aria-hidden="true"')
    return (f'<p class="einheit" id="zr-titel">Geänderte Energieträger je Woche und 1\'000 Gebäude</p>'
            f'<ul class="legende">{legende}</ul>'
            f'<p id="zr-text" hidden>{text}</p>'
            f'<div class="zr-breit">{breit}</div><div class="zr-schmal">{schmal}</div>')


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


def baue(ziel: Path) -> int:
    if ziel.exists():
        for kind in ziel.iterdir():
            if kind.name == ".git":
                continue
            shutil.rmtree(kind) if kind.is_dir() else kind.unlink()
    ziel.mkdir(parents=True, exist_ok=True)

    seiten = set(BERICHTE)
    dateien = set(KOPIEN) | set(HTML_BERICHTE)

    def schreibe(rel: str, text: str) -> None:
        pfad = ziel / rel
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(text, encoding="utf-8", newline="\n")

    start = (QUELLE / "index.html").read_text(encoding="utf-8")
    start = re.sub(r"<!--.*?-->\s*", "", start, count=1, flags=re.S)
    start = start.replace("{{ZEITREIHE}}", zeitreihe_block()).replace("{{REPO}}", REPO)
    if "{{" in start:
        raise Baufehler("site/index.html: unbekannter Platzhalter")
    schreibe("index.html", rahmen("index.html", NAME, BESCHREIBUNG, start))

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
