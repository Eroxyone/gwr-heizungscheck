"""Die Website baut aus den Berichten im Repo, und ihre Verweise gehen nicht ins Leere.

Der Bau selbst bricht bei einem toten Verweis ab; die Tests hier halten fest, was darueber
hinaus gelten soll: Das Diagramm zeigt die Zahlen der Tabelle, und Verweise zwischen
Berichten zeigen auf Seiten statt auf Markdown-Dateien.
"""
from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def bau():
    spec = importlib.util.spec_from_file_location("build_site", ROOT / "scripts" / "build_site.py")
    modul = importlib.util.module_from_spec(spec)
    sys.modules["build_site"] = modul
    spec.loader.exec_module(modul)
    return modul


@pytest.fixture(scope="module")
def website(bau, tmp_path_factory):
    ziel = tmp_path_factory.mktemp("site")
    anzahl = bau.baue(ziel)
    return ziel, anzahl


def test_jeder_bericht_wird_eine_seite(bau, website):
    ziel, anzahl = website
    assert anzahl == 1 + len(bau.BERICHTE) + len(bau.HTML_BERICHTE)
    for md in bau.BERICHTE:
        assert (ziel / bau.seitenpfad(md)).is_file(), md
    assert (ziel / "index.html").is_file()
    assert (ziel / ".nojekyll").is_file()


def test_keine_verweise_ins_leere(bau, website):
    ziel, _ = website
    assert bau.pruefe_verweise(ziel) == []


def test_verweise_zwischen_berichten_zeigen_auf_seiten(website):
    """Kein Verweis der Website darf noch auf eine Markdown-Datei im selben Baum zeigen."""
    ziel, _ = website
    for seite in ziel.rglob("*.html"):
        text = re.sub(r"<script\b.*?</script>", "", seite.read_text(encoding="utf-8"), flags=re.S)
        lokal = [h for h in re.findall(r'href="([^"]+)"', text) if not h.startswith(("http", "#", "mailto:"))]
        assert not [h for h in lokal if h.partition("#")[0].endswith(".md")], seite.name


def test_diagramm_zeigt_die_zahlen_der_tabelle(bau):
    """Die Hoechstwerte im Diagramm sind die groessten Wochenwerte aus reports/zeitreihe.md."""
    wochen, promille, anzahl, n_rest = bau.zeitreihe_daten()
    assert len(wochen) >= 2 and n_rest + len(bau.HERVOR) == 26
    svg = bau.zeitreihe_svg(1000, 400, 13.5, 1)
    for kanton in bau.HERVOR:
        hoechst = f"{max(anzahl[kanton]):,}".replace(",", "'")
        assert f">{kanton} {hoechst}<" in svg
        assert len(promille[kanton]) == len(wochen)


def test_toter_verweis_bricht_den_bau_ab(bau):
    with pytest.raises(bau.Baufehler):
        bau.verweis("docs/methode.md", "gibt_es_nicht.md", set(bau.BERICHTE), set(bau.KOPIEN))


def test_verweis_auf_code_fuehrt_ins_repository(bau):
    ziel = bau.verweis("docs/methode.md", "../sql/gold.sql", set(bau.BERICHTE), set(bau.KOPIEN))
    assert ziel == f"{bau.REPO}/blob/main/sql/gold.sql"
    seite = bau.verweis("docs/methode.md", "../reports/zeitreihe.md", set(bau.BERICHTE), set(bau.KOPIEN))
    assert seite == "../reports/zeitreihe.html"


def test_ausgeschriebene_adressen_werden_verweise(bau):
    html = bau.adressen_verlinken('<p>Siehe https://example.org/a.b, dann <code>https://x.y/z</code> '
                                  'und <a href="https://q.r">https://q.r</a>.</p>')
    assert '<a href="https://example.org/a.b">https://example.org/a.b</a>, dann' in html
    assert "<code>https://x.y/z</code>" in html
    assert html.count("<a ") == 2
