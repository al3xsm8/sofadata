# context.md — Aplicação Web de Estatísticas de Partidas de Futebol

## 1. Contexto e objetivo do projeto

Quero construir uma aplicação web com banco de dados que obtenha estatísticas de partidas de futebol usando como base o projeto:

- Repositório: https://github.com/tunjayoff/sofascore_scraper

O projeto será desenvolvido **para fins de estudo pessoal**, sem intenção de comercialização.

A aplicação deverá coletar estatísticas de partidas, armazená-las em um banco de dados próprio e exibi-las em uma interface web organizada, permitindo consultar partidas anteriores e filtrar os dados.

A planilha `modelo.xlsx`, fornecida no início do projeto, é a referência dos campos e do formato de dados que quero acompanhar. Não se deve inventar estatísticas adicionais como requisito obrigatório sem conversar comigo primeiro.

## 2. Como a IA deve me orientar

A IA deverá atuar como **tutora técnica e parceira de desenvolvimento**, guiando-me do início ao fim.

### Regras obrigatórias de colaboração

1. Não desenvolver o projeto inteiro de uma só vez.
2. Dividir o trabalho em etapas pequenas, sequenciais e verificáveis.
3. Antes de começar uma etapa, explicar:
   - o que será construído;
   - por que isso é necessário;
   - quais ferramentas/arquivos serão usados;
   - como saberei que a etapa funcionou.
4. Gerar o código necessário para a etapa atual.
5. Explicar exatamente:
   - qual arquivo devo criar ou abrir;
   - em qual pasta ele deve ficar;
   - se devo substituir todo o conteúdo ou adicionar um trecho;
   - como executar os comandos, incluindo o diretório em que devo estar.
6. Após fornecer o código, aguardar que eu execute os passos e compartilhe o resultado antes de avançar.
7. Se ocorrer um erro, ajudar a diagnosticar a causa com base nas mensagens, sem avançar para outra etapa.
8. Não presumir que eu já conheço conceitos, comandos ou ferramentas. Explicar de forma clara, mas sem excesso de teoria.
9. Não alterar decisões de arquitetura, bibliotecas ou escopo sem explicar a razão e pedir minha aprovação quando a mudança for significativa.
10. Não apresentar funcionalidades como concluídas antes de eu confirmar que foram implementadas e testadas.
11. Preferir soluções simples, legíveis e adequadas para aprendizado, em vez de abstrações complexas ou arquitetura desnecessariamente sofisticada.
12. Não despejar todos os arquivos do projeto em uma única resposta. Trabalhar arquivo por arquivo e etapa por etapa.

### Formato preferido de cada etapa

- **Objetivo**
- **Explicação breve**
- **Ação que devo realizar**
- **Código**, quando necessário
- **Como executar/testar**
- **Resultado esperado**
- **Pausa para minha confirmação**

A IA deve manter o contexto das decisões e do progresso já realizados na conversa.

## 3. Escopo funcional

### Funcionalidades principais

- Obter partidas e estatísticas através do projeto `sofascore_scraper`.
- Permitir a coleta de estatísticas de partidas do dia e, quando suportado pela fonte, de partidas anteriores.
- Persistir os dados em banco de dados próprio.
- Evitar duplicar partidas ao coletar dados mais de uma vez.
- Exibir partidas em uma aplicação web.
- Permitir pesquisar e filtrar os dados por data, campeonato, time, adversário, local e rodada.
- Exibir os dados de cada partida em formato organizado, inspirado na planilha.
- Permitir atualizar estatísticas de partidas que ainda estejam em andamento ou cujos dados tenham sido alterados.
- Registrar erros de coleta para que possam ser investigados.

### Fora do escopo inicial

Não implementar sem minha aprovação:

- apostas, recomendações de apostas ou previsões;
- sistema de usuários, login ou permissões;
- pagamentos ou monetização;
- aplicativo mobile nativo;
- notificações;
- scraping de páginas por métodos diferentes da biblioteca escolhida;
- análises avançadas, gráficos complexos ou modelos de IA;
- coleta indiscriminada de todas as ligas e temporadas.

A primeira versão deverá ser um MVP (produto mínimo viável) funcional.

## 4. Fonte dos dados

O repositório-base é:

https://github.com/tunjayoff/sofascore_scraper

A IA deverá primeiro me ajudar a compreender o repositório e verificar:

- linguagem e dependências;
- como instalar e executar;
- quais funções/endpoints ou métodos estão disponíveis;
- como localizar partidas por data;
- como obter detalhes de uma partida;
- como obter estatísticas de cada time ou partida;
- quais estatísticas são realmente retornadas;
- como identificar uma partida de forma única;
- limitações, falhas e possíveis mudanças na fonte.

**Não inventar nomes de métodos, endpoints, campos ou formatos de resposta.** Antes de escrever a integração, verificar o código e a documentação disponível do projeto e, se necessário, executar testes pequenos para inspecionar a resposta real.

A aplicação deverá ter uma camada própria de integração com o scraper. A lógica do banco de dados e da interface não deve depender diretamente do formato bruto retornado pela biblioteca.

### Cuidados com a fonte

- Usar a biblioteca para fins de estudo e respeitar os termos, limitações e recomendações do repositório.
- Não presumir que a API seja oficial, estável ou que tenha garantia de disponibilidade.
- Não coletar dados em frequência excessiva.
- Tratar erros, timeouts, respostas vazias e mudanças no formato dos dados.
- Se a fonte não fornecer determinado campo, armazenar como nulo/indisponível, sem inventar um valor.
- Antes de implementar coleta automática, validar uma partida manualmente e confirmar os campos retornados.

## 5. Dados de referência da planilha

A planilha de exemplo possui uma linha de cabeçalho com os seguintes campos:

| Campo na planilha | Significado pretendido |
|---|---|
| Data | Data da partida |
| Capeonato | Campeonato/competição (corrigir o rótulo para “Campeonato” na interface) |
| Time | Time que será o foco do registro |
| Resultado | Placar final |
| Adversario | Adversário (corrigir para “Adversário” na interface) |
| Local | Casa ou fora |
| Gol 1º Tempo | Gols do time no primeiro tempo |
| Resultado 1ª Tempo | Placar do primeiro tempo |
| Escateios 1º Tempo | Escanteios do time no primeiro tempo (corrigir para “Escanteios”) |
| Cartão 1º Tempo | Cartões do time no primeiro tempo |
| Chutes 1º Tempo | Chutes do time no primeiro tempo |
| Chutes Gol 1º Tempo | Chutes no gol do time no primeiro tempo |
| Gols | Gols do time na partida |
| Escateios | Escanteios do time na partida (corrigir para “Escanteios”) |
| Cartão | Cartões do time na partida |
| Chutes | Chutes do time na partida |
| Chutes Gol | Chutes no gol do time na partida |
| Rodada | Rodada da competição |

Exemplo da planilha:

- Data: 01/10/2026
- Campeonato: Champions
- Time: PSG
- Resultado: 6 x 1
- Adversário: Slovan Bratislava
- Local: Casa
- Gols no 1º tempo: 3
- Resultado do 1º tempo: 3 x 0
- Escanteios no 1º tempo: 4
- Cartões no 1º tempo: 0
- Chutes no 1º tempo: 21
- Chutes no gol no 1º tempo: 7
- Gols: 6
- Escanteios: 7
- Cartões: 0
- Chutes: 35
- Chutes no gol: 14
- Rodada: 1

### Observações importantes sobre o modelo

- O exemplo da planilha apresenta estatísticas para um time por linha.
- Uma partida tem dois times. O banco pode guardar a partida uma única vez e as estatísticas de cada equipe separadamente.
- A interface poderá exibir uma linha por time, como na planilha, para facilitar a comparação e a exportação.
- O campo “Local” deverá representar se o time está jogando em casa ou fora.
- Os campos “Cartão” e “Cartão 1º Tempo” ainda precisam ser definidos com precisão: pode ser contagem de cartões amarelos, vermelhos ou total de cartões. Antes de implementar, conferir o que a fonte fornece e combinar comigo qual interpretação usar.
- O campo “Resultado 1ª Tempo” deve ser armazenado preferencialmente como gols de cada time, permitindo formatar o placar na interface.
- A data deverá ser armazenada em formato apropriado no banco, com atenção ao fuso horário e à data local da partida.
- Os nomes dos campos na interface devem ser corrigidos e padronizados em português.

## 6. Modelo de dados sugerido

A IA deverá explicar e validar o modelo comigo antes de criar as tabelas.

Modelo inicial recomendado:

### Tabela `competitions`

Armazena campeonatos/competições.

Campos possíveis:
- `id` — chave primária;
- `source_id` — identificador da competição na fonte, se disponível;
- `name` — nome;
- `country` — país, se disponível;
- `season` — temporada, se disponível.

### Tabela `teams`

Armazena times.

Campos possíveis:
- `id` — chave primária;
- `source_id` — identificador do time na fonte, se disponível;
- `name` — nome;
- `short_name` — nome curto, se disponível;
- `country` — país, se disponível.

### Tabela `matches`

Armazena uma partida uma única vez.

Campos possíveis:
- `id` — chave primária local;
- `source_id` — identificador da partida na fonte;
- `competition_id` — referência ao campeonato;
- `home_team_id` — time da casa;
- `away_team_id` — time visitante;
- `match_date` — data e horário;
- `status` — agendada, ao vivo, finalizada ou outro status disponível;
- `round` — rodada, se disponível;
- `home_goals` — gols do time da casa;
- `away_goals` — gols do visitante;
- `home_half_time_goals` — gols do time da casa no primeiro tempo;
- `away_half_time_goals` — gols do visitante no primeiro tempo;
- `last_updated_at` — última atualização dos dados.

### Tabela `team_match_statistics`

Armazena as estatísticas de cada time em uma partida.

Campos possíveis:
- `id` — chave primária;
- `match_id` — referência à partida;
- `team_id` — referência ao time;
- `is_home` — indica se é o time da casa;
- `goals` — gols do time;
- `half_time_goals` — gols no primeiro tempo;
- `corners` — escanteios;
- `half_time_corners` — escanteios no primeiro tempo;
- `cards` — cartões conforme definição acordada;
- `half_time_cards` — cartões no primeiro tempo;
- `shots` — chutes;
- `half_time_shots` — chutes no primeiro tempo;
- `shots_on_target` — chutes no gol;
- `half_time_shots_on_target` — chutes no gol no primeiro tempo;
- `updated_at` — data/hora da atualização.

A estrutura final deverá refletir os campos que realmente existem na fonte. Se alguma estatística não for disponibilizada, não inventar ou estimar.

### Integridade e duplicidade

- Usar identificadores da fonte quando disponíveis.
- Criar restrição única para impedir duplicação da mesma partida.
- Criar restrição única para impedir duplicação das estatísticas do mesmo time na mesma partida.
- Usar operações de inserção/atualização (upsert) na coleta.
- Criar chaves estrangeiras entre partidas, times, competições e estatísticas.

## 7. Banco de dados

A IA deverá recomendar e explicar um banco apropriado ao projeto.

Preferência inicial: **PostgreSQL**, por ser robusto e útil para aprendizado de aplicações web com dados relacionais.

Para desenvolvimento local, pode ser executado por Docker. A IA deverá explicar como configurar:
- serviço do banco;
- variáveis de ambiente;
- usuário e senha;
- banco de dados;
- persistência dos dados;
- migrações ou criação de tabelas;
- conexão entre backend e banco.

Credenciais não devem ser colocadas diretamente no código nem enviadas ao Git. Usar arquivo `.env` e incluir `.env` no `.gitignore`.

## 8. Arquitetura sugerida

A arquitetura deve ser simples e separada por responsabilidade:

1. **Fonte de dados** — projeto `sofascore_scraper`.
2. **Backend/API própria** — responsável pela coleta, normalização, persistência e disponibilização dos dados.
3. **Banco de dados** — responsável por armazenar partidas e estatísticas.
4. **Frontend web** — responsável pela visualização, pesquisa e filtros.
5. **Agendador de coleta** — executa coleta em intervalos definidos.

A IA deverá propor a stack e explicar os motivos antes de instalar dependências. Uma stack possível para avaliação:

- Backend: Python com FastAPI, caso seja adequado ao scraper Python.
- Banco: PostgreSQL.
- Frontend: React com Vite.
- Comunicação: API HTTP/JSON entre frontend e backend.
- Ambiente: Docker Compose, se for útil para simplificar o desenvolvimento.

A stack pode ser ajustada após verificar o repositório e conversar comigo. Não adotar várias tecnologias redundantes.

## 9. Coleta e atualização de dados

A coleta deverá ser desenvolvida em etapas:

1. Consultar as partidas de uma data escolhida.
2. Inspecionar os dados brutos retornados.
3. Identificar quais partidas possuem estatísticas disponíveis.
4. Obter detalhes/estatísticas de uma partida.
5. Converter a resposta para um modelo interno consistente.
6. Salvar ou atualizar competição, times, partida e estatísticas.
7. Confirmar que a partida não foi duplicada.
8. Registrar o resultado da coleta e eventuais erros.

### Agendamento

- A primeira versão deve permitir coleta manual por comando ou botão.
- Depois de validar a coleta, adicionar agendamento automático.
- Definir comigo o intervalo e o horário antes de ativar coleta frequente.
- Partidas ao vivo podem exigir atualizações mais frequentes do que partidas finalizadas, mas isso deve ser limitado e configurável.
- Partidas finalizadas podem ser atualizadas com menor frequência.
- O agendador deve continuar funcionando sem depender de o usuário manter a página web aberta.

## 10. Interface web

A interface deverá ser organizada, clara e em português.

### Página inicial / painel

Exibir:
- quantidade de partidas armazenadas;
- partidas da data selecionada;
- estado da última coleta;
- horário da última atualização;
- erros recentes, quando houver.

### Página de partidas

Exibir tabela com campos equivalentes aos da planilha:
- Data;
- Campeonato;
- Time;
- Resultado;
- Adversário;
- Local;
- Gols 1º Tempo;
- Resultado 1º Tempo;
- Escanteios 1º Tempo;
- Cartões 1º Tempo;
- Chutes 1º Tempo;
- Chutes no Gol 1º Tempo;
- Gols;
- Escanteios;
- Cartões;
- Chutes;
- Chutes no Gol;
- Rodada.

### Filtros

- data ou intervalo de datas;
- campeonato;
- time;
- adversário;
- casa/fora;
- rodada;
- status da partida, se disponível.

### Detalhes da partida

Ao abrir uma partida, mostrar:
- nomes dos times;
- placar final;
- placar do primeiro tempo;
- competição, rodada e data;
- estatísticas de cada time lado a lado;
- data/hora da última atualização.

A interface deverá tratar valores ausentes de forma clara, por exemplo `—`, sem mostrar `0` quando a estatística não foi fornecida.

## 11. API do backend

A IA deverá definir os endpoints após o modelo de dados estar validado. Exemplos de rotas que podem ser consideradas:

- `GET /api/health` — verificar se a API está funcionando;
- `GET /api/matches` — listar partidas com filtros;
- `GET /api/matches/{id}` — obter detalhes de uma partida;
- `POST /api/collection/run` — iniciar coleta manual;
- `GET /api/collection/status` — consultar estado da coleta.

Essas rotas são propostas, não uma exigência de nomes exatos. Definir o formato dos parâmetros e respostas antes de implementá-las.

A coleta não deve ser disparada automaticamente por cada visita do frontend à página. Deve ser controlada pelo backend/agendador.

## 12. Qualidade, segurança e manutenção

- Validar entradas e parâmetros de filtro.
- Usar consultas parametrizadas no banco.
- Não expor tokens, senhas ou dados de conexão.
- Tratar falhas de rede e respostas inesperadas.
- Registrar erros com mensagens úteis, sem vazar segredos.
- Manter separação entre configuração, integração, banco, API e frontend.
- Adicionar testes básicos para normalização dos dados e prevenção de duplicatas.
- Manter dependências documentadas.
- Não ignorar erros silenciosamente.
- Usar Git para registrar etapas importantes, explicando os comandos quando necessário.

## 13. Etapas de desenvolvimento

A IA deverá seguir a sequência abaixo, uma etapa por vez, confirmando comigo antes de avançar.

### Etapa 1 — Análise da fonte
- Abrir e analisar o repositório `sofascore_scraper`.
- Entender instalação, uso e dados retornados.
- Fazer um teste pequeno de consulta.
- Identificar estatísticas disponíveis e limitações.

### Etapa 2 — Definição do projeto
- Confirmar stack.
- Definir funcionalidades do MVP.
- Validar o modelo de dados com base na planilha e na fonte.

### Etapa 3 — Preparação do ambiente
- Criar estrutura de pastas.
- Configurar ambiente Python/Node conforme stack escolhida.
- Configurar Git e `.env`.
- Configurar banco local.

### Etapa 4 — Banco de dados
- Criar tabelas e relacionamentos.
- Validar inserção e consulta de dados de exemplo.
- Implementar proteção contra duplicidade.

### Etapa 5 — Integração com scraper
- Consultar partidas de uma data.
- Obter estatísticas de uma partida.
- Normalizar os dados.
- Persistir no banco.
- Testar atualizações.

### Etapa 6 — Backend/API
- Criar endpoints.
- Implementar filtros.
- Testar endpoints individualmente.

### Etapa 7 — Frontend
- Criar estrutura da interface.
- Implementar tabela de partidas.
- Implementar filtros.
- Implementar detalhes da partida.
- Integrar com a API.

### Etapa 8 — Agendamento
- Adicionar coleta automática.
- Configurar intervalo.
- Exibir estado e última coleta.
- Testar comportamento após reinicialização.

### Etapa 9 — Testes e ajustes
- Verificar dados contra a fonte.
- Corrigir divergências.
- Testar filtros, atualizações e partidas sem estatísticas.
- Revisar logs e erros.

### Etapa 10 — Execução contínua / implantação
- Avaliar se será executado apenas localmente ou em servidor.
- Se for usar servidor, configurar ambiente e variáveis de forma segura.
- Confirmar funcionamento após reinício.
- Documentar comandos para iniciar, parar e atualizar a aplicação.

## 14. Critérios de conclusão do MVP

O MVP será considerado funcional quando:

- A aplicação consegue consultar partidas usando o scraper.
- As estatísticas disponíveis são normalizadas e armazenadas no banco.
- Coletas repetidas não criam partidas ou estatísticas duplicadas.
- A aplicação web lista os dados armazenados.
- Os filtros básicos funcionam.
- A visualização dos campos corresponde ao modelo da planilha.
- Dados ausentes são tratados corretamente.
- A coleta pode ser iniciada manualmente.
- Os erros de coleta podem ser identificados.
- Eu consigo executar o projeto seguindo as instruções documentadas.

## 15. Primeira tarefa da IA ao receber este contexto

Comece **somente pela Etapa 1 — Análise da fonte**.

Não crie a aplicação, banco, frontend ou todos os arquivos ainda.

Primeiro:
1. Explique brevemente o que vamos verificar no repositório.
2. Oriente-me a abrir/baixar o projeto e executar o primeiro teste.
3. Ajude-me a identificar os dados retornados.
4. Compare os dados disponíveis com as colunas da planilha.
5. Apresente o que está disponível, o que falta e quais decisões precisamos tomar.

Depois, aguarde minha confirmação para iniciar a Etapa 2.
