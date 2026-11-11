param(
    [string]$TaskName = "Sofadata JSONL Import",
    [int]$IntervalMinutes = 15
)

$ErrorActionPreference = "Stop"

if ($IntervalMinutes -lt 5) {
    throw "IntervalMinutes deve ser pelo menos 5 para limitar execuções frequentes."
}

$backend = (Resolve-Path (Join-Path $PSScriptRoot "..\backend")).Path
$python = Join-Path $backend ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Ambiente Python não encontrado: $python. Crie-o antes de registrar a tarefa."
}

$action = New-ScheduledTaskAction -Execute $python -Argument "-m collection_worker" -WorkingDirectory $backend
$trigger = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes($IntervalMinutes) `
    -RepetitionInterval (New-TimeSpan -Minutes $IntervalMinutes) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings `
    -Description "Importa periodicamente os arquivos JSONL locais do Sofadata. Sem coleta de rede." `
    -User "$env:USERDOMAIN\$env:USERNAME" -RunLevel Limited -Force | Out-Null
Disable-ScheduledTask -TaskName $TaskName | Out-Null

Write-Output "Tarefa '$TaskName' registrada e DESATIVADA. Intervalo configurado: $IntervalMinutes minutos."
Write-Output "Antes de habilitar, configure COLLECTION_ENABLED=true e os caminhos dos JSONL em app\backend\.env."
