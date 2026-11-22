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

try {
    python src/ingest.py 2>&1 | Tee-Object -FilePath $log -Append
    if ($LASTEXITCODE -ne 0) { throw "ingest.py endete mit Code $LASTEXITCODE" }

    # "alle" statt "ch": Der Gold-Layer (Belege, Verdachtsliste, Archiv) wird aus dem
    # CH-Layer gerechnet und muss mit jedem Snapshot nachziehen. Mit "ch" blieb er auf
    # dem alten Stand stehen und die Liste fuehrte Faelle, die das Register schon
    # korrigiert hatte (02.10.2026: 240 von 3'423).
    python src/pipeline.py alle 2>&1 | Tee-Object -FilePath $log -Append
    python src/checks.py 2>&1 | Tee-Object -FilePath $log -Append
    if ($LASTEXITCODE -ne 0) {
        "WARNUNG: Datenqualitaetspruefungen nicht bestanden" | Tee-Object -FilePath $log -Append
    }
    "fertig" | Tee-Object -FilePath $log -Append
}
catch {
    "FEHLER: $_" | Tee-Object -FilePath $log -Append
    exit 1
}

# Protokolle aelter als 90 Tage aufraeumen
Get-ChildItem $logs -Filter "snapshot_*.log" |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-90) } |
    Remove-Item -Force
