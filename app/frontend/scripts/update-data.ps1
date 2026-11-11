$ErrorActionPreference = 'Stop'

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..\..')
$output = Join-Path $PSScriptRoot '..\public\data\matches.json'
$temporaryOutput = Join-Path $env:TEMP 'sofadata-matches.json.tmp'
$apiUrl = if ($env:SOFADATA_API_URL) { $env:SOFADATA_API_URL.TrimEnd('/') } else { 'http://127.0.0.1:8015' }
$uri = "$apiUrl/api/data/matches.json"

New-Item -ItemType Directory -Force -Path (Split-Path $output) | Out-Null
try {
    Invoke-WebRequest -Uri $uri -OutFile $temporaryOutput -UseBasicParsing -TimeoutSec 120
    $snapshot = Get-Content $temporaryOutput -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($snapshot.schema_version -ne 1 -or $snapshot.items.Count -ne $snapshot.total) {
        throw 'O snapshot retornado pela API é inválido ou incompleto.'
    }
    Move-Item -LiteralPath $temporaryOutput -Destination $output -Force
    Remove-Item -LiteralPath $temporaryOutput -ErrorAction SilentlyContinue
    Write-Host "Snapshot atualizado: $($snapshot.total) partidas em $output"
}
catch {
    Remove-Item -LiteralPath $temporaryOutput -ErrorAction SilentlyContinue
    throw "Falha ao atualizar JSON de $uri. Verifique se o backend e o banco estão ativos. $($_.Exception.Message)"
}
