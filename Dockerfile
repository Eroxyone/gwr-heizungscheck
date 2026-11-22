# Laufumgebung fuer Pipeline, Pruefungen und Tests.
#
#   docker build -t gwr-heizungscheck .
#   docker run --rm gwr-heizungscheck -m pytest                              # Tests, ohne Daten
#   docker run --rm -v gwr-daten:/data gwr-heizungscheck src/ingest.py       # Rohdaten laden
#   docker run --rm -v gwr-daten:/data gwr-heizungscheck src/pipeline.py ch  # rechnen
#
# Rohdaten, Snapshots und die Datenbank liegen auf dem Volume /data, nicht im Image.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    MPLBACKEND=Agg \
    GWR_DATA_DIR=/data

RUN useradd --create-home gwr && mkdir /data /app && chown gwr:gwr /data /app
WORKDIR /app

COPY requirements.txt requirements-dev.txt ./
RUN pip install -r requirements-dev.txt

USER gwr
# Die Spatial-Extension schon beim Bauen holen. DuckDB laedt sie sonst beim ersten Lauf
# aus dem Netz nach, und der Container soll danach auch ohne Netz rechnen koennen.
RUN python -c "import duckdb; duckdb.connect().execute('INSTALL spatial')"

COPY --chown=gwr:gwr . .

VOLUME /data
ENTRYPOINT ["python"]
CMD ["-m", "pytest"]
