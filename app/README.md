# Sofadata - execucao local no Windows

Este guia descreve o MVP local. Nao e uma implantacao publica: o backend e o PostgreSQL ficam vinculados a 127.0.0.1.

## Banco de desenvolvimento

O PostgreSQL do Sofadata roda em Docker na porta 5433, com volume nomeado persistente. O servico PostgreSQL instalado no Windows na porta 5432 nao e usado pelo Sofadata.

No PowerShell, a partir da pasta sofadata:

```powershell
docker compose -f app\docker-compose.yml up -d postgres
docker compose -f app\docker-compose.yml ps
```

Parar o container sem apagar os dados:

```powershell
docker compose -f app\docker-compose.yml stop postgres
```

Iniciar novamente:

```powershell
docker compose -f app\docker-compose.yml start postgres
```

O banco de desenvolvimento chama-se `sofadata`. O banco `sofadata_test` e separado e contem somente a amostra usada nos testes de integracao. Nao remova volumes para limpar os dados.

## Iniciar backend e frontend

Abra dois terminais PowerShell.

Terminal 1 - backend:

```powershell
cd "C:\Users\Alex Barbosa\Documents\PROJETOS\sofadata\app\backend"
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8011
```

Terminal 2 - frontend:

```powershell
cd "C:\Users\Alex Barbosa\Documents\PROJETOS\sofadata\app\frontend"
npm run dev
```

Abra o endereco local mostrado pelo Vite (normalmente `http://localhost:5173`). O proxy de desenvolvimento envia `/api` ao backend em `127.0.0.1:8011`.

Para parar cada processo, pressione Ctrl+C no terminal correspondente. A porta 8011 pode ja estar ocupada por outro uvicorn; nao encerre um processo desconhecido. Identifique o processo ou escolha outra porta e atualize o proxy de desenvolvimento.

## Exportar e importar partidas manualmente

O scraper nao e iniciado pelo frontend e nao faz coleta automaticamente. Exporte uma partida ja armazenada usando o CLI do scraper, por exemplo:

```powershell
cd "C:\Users\Alex Barbosa\Documents\PROJETOS\sofadata\sofascore_scraper-main"
.\.venv\Scripts\python.exe -m sofascore_scraper.cli.main export --dataset events --format jsonl --event 16363874 --out "..\data\events.jsonl" --force
.\.venv\Scripts\python.exe -m sofascore_scraper.cli.main export --dataset slices --schema raw --format jsonl --event 16363874 --out "..\data\slices.jsonl" --force
```

Depois importe os dois arquivos para o banco configurado em `app\backend\.env`:

```powershell
cd "C:\Users\Alex Barbosa\Documents\PROJETOS\sofadata\app\backend"
.\.venv\Scripts\python.exe -m import_jsonl --events "..\..\data\events.jsonl" --slices "..\..\data\slices.jsonl"
```

A importacao e idempotente pelos IDs da fonte. Arquivos em `data/` e credenciais `.env` sao locais e ignorados pelo Git.

## Testes

```powershell
cd "C:\Users\Alex Barbosa\Documents\PROJETOS\sofadata\app\backend"
.\.venv\Scripts\python.exe -m pytest -q tests
```

```powershell
cd "C:\Users\Alex Barbosa\Documents\PROJETOS\sofadata\app\frontend"
npm run build
```

## Agendador

O worker so reimporta os JSONL locais configurados; ele nao consulta o SofaScore. Esta desativado por padrao (`COLLECTION_ENABLED=false`). Nenhuma tarefa do Windows foi registrada ou habilitada.

Antes de preparar uma tarefa, revise os caminhos `COLLECTION_EVENTS_FILE` e `COLLECTION_SLICES_FILE` em `app\backend\.env`. Nao habilite coleta frequente sem definir previamente intervalo e horario.

## Implantacao publica

Nao configurada. Antes de expor o servico fora do computador, sera necessario definir autenticacao, segredos, TLS, firewall, estrategia de backup e politica de atualizacao.
