# Woechentlicher GWR-Snapshot.
#
# Laedt alle 26 Kantone, legt je Kanton ein Parquet unter data/snapshots/gwr/ ab und
# schreibt ein Protokoll nach logs/. Ueberspringt Kantone, deren Stand schon vorliegt,
# der Lauf ist also gefahrlos wiederholbar.
#
# Einrichten (einmalig, in einer normalen PowerShell):
#   $t = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday -At 06:30
#   $a = New-ScheduledTaskAction -Execute "powershell.exe" `
#          -Argument "-NoProfile -ExecutionPolicy Bypass -File <Pfad zum Repo>\scripts\snapshot.ps1"
#   Register-ScheduledTask -TaskName "GWR-Snapshot" -Trigger $t -Action $a `
#          -Description "Woechentlicher GWR-Snapshot fuer gwr-heizungscheck"
#
# Wieder entfernen:
#   Unregister-ScheduledTask -TaskName "GWR-Snapshot" -Confirm:$false

$ErrorActionPreference = "Stop"
$projekt = Split-Path -Parent $PSScriptRoot
$logs = Join-Path $projekt "logs"
if (-not (Test-Path $logs)) { New-Item -ItemType Directory -Path $logs | Out-Null }

$stempel = Get-Date -Format "yyyy-MM-dd_HHmm"
$log = Join-Path $logs "snapshot_$stempel.log"

Set-Location $projekt
"=== GWR-Snapshot $stempel ===" | Tee-Object -FilePath $log

# Fuehrt einen Python-Schritt aus, schreibt seine Ausgabe ins Protokoll und gibt den
# Exit-Code zurueck. Ueber Erfolg entscheidet allein dieser Code.
function Invoke-PythonSchritt {
    param([Parameter(Mandatory = $true)][string[]]$Argumente)

    # Windows PowerShell 5.1 macht aus jeder stderr-Zeile eines Programms einen
    # Fehlerdatensatz. Unter "Stop" braeche schon die erste Zeile den Lauf ab, und der
    # Rest der Meldung (etwa ein Python-Traceback) fehlte im Protokoll. Die Einstellung
    # gilt nur innerhalb dieser Funktion.
    $ErrorActionPreference = "Continue"
    & python @Argumente 2>&1 |
        ForEach-Object { "$_" } |
        Tee-Object -FilePath $log -Append |
        Out-Host
    return $LASTEXITCODE
}

$pruefungenBestanden = $true
try {
    $code = Invoke-PythonSchritt -Argumente "src/ingest.py"
    if ($code -ne 0) {
        throw "ingest.py endete mit Exit-Code $code. Der Snapshot ist unvollstaendig, die Pipeline wurde nicht gestartet."
    }

    # "alle" statt "ch": Der Gold-Layer (Belege, Verdachtsliste, Archiv) wird aus dem
    # CH-Layer gerechnet und muss mit jedem Snapshot nachziehen. Mit "ch" blieb er auf
    # dem alten Stand stehen und die Liste fuehrte Faelle, die das Register schon
    # korrigiert hatte (02.10.2026: 240 von 3'423).
    $code = Invoke-PythonSchritt -Argumente "src/pipeline.py", "alle"
    if ($code -ne 0) {
        throw "pipeline.py endete mit Exit-Code $code. Der Snapshot liegt vor, Silver- und Gold-Layer sind nicht nachgezogen."
    }

    $code = Invoke-PythonSchritt -Argumente "src/checks.py"
    if ($code -ne 0) {
        $pruefungenBestanden = $false
        "WARNUNG: Datenqualitaetspruefungen nicht bestanden (checks.py endete mit Exit-Code $code)" |
            Tee-Object -FilePath $log -Append
    }
    else {
        "fertig" | Tee-Object -FilePath $log -Append
    }
}
catch {
    "FEHLER: $_" | Tee-Object -FilePath $log -Append
    exit 1
}

# Protokolle aelter als 90 Tage aufraeumen
Get-ChildItem $logs -Filter "snapshot_*.log" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-90) } |
    Remove-Item -Force

# Exit-Codes: 0 alles in Ordnung, 1 Ingest oder Pipeline gescheitert, 2 Snapshot und
# Pipeline in Ordnung, aber mindestens eine Datenqualitaetspruefung nicht bestanden.
if (-not $pruefungenBestanden) { exit 2 }
