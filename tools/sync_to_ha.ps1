<#
.SYNOPSIS
  Copie lol_stats sur Home Assistant (SSH) puis ha core restart.

.DESCRIPTION
  Charge tools\ha_local.env (optionnel), puis lance sync_to_ha.py.
  Copiez ha-sync.example.env vers tools\ha_local.env et renseignez le mot de passe.

.EXAMPLE
  .\tools\sync_to_ha.ps1
#>
$ErrorActionPreference = "Stop"

$RepoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$EnvFile = Join-Path $PSScriptRoot "ha_local.env"

if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith("#")) { return }
        $eq = $line.IndexOf("=")
        if ($eq -lt 1) { return }
        $k = $line.Substring(0, $eq).Trim()
        $v = $line.Substring($eq + 1).Trim()
        if ($v.Length -ge 2 -and $v.StartsWith('"') -and $v.EndsWith('"')) {
            $v = $v.Substring(1, $v.Length - 2)
        }
        Set-Item -Path "Env:$k" -Value $v
    }
}

$Py = Join-Path $PSScriptRoot "sync_to_ha.py"
if (-not (Test-Path $Py)) {
    Write-Error "Fichier introuvable : $Py"
    exit 1
}

python $Py $RepoRoot.Path
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
