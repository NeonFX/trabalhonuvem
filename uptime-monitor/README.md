# Uptime Monitor

Projeto final de Computação em Nuvem (PUC-Campinas). Aplicação web de monitoramento HTTP, com quatro serviços Docker Compose: Nginx, API FastAPI, worker Python e PostgreSQL. Os dois serviços Python são de implementação própria. A execução prevista é local e não exige conta de nuvem, API paga ou serviço externo para a demonstração.

## Executar no Windows ou macOS

1. Instale e abra o Docker Desktop (modo de containers Linux).
2. Extraia o ZIP e abra um terminal na pasta `uptime-monitor` (onde está `compose.yaml`).
3. Execute:

```sh
docker compose up -d --build
docker compose ps
```

4. Abra http://localhost:8080 no navegador.
5. Clique em **Carregar demonstração**. O worker verificará duas rotas HTTP do Nginx: `/demo/online` (200) e `/demo/offline` (503). Aguarde o próximo ciclo e a atualização do painel. Não depende da internet depois do download das imagens. Também é possível cadastrar sites públicos.

A primeira construção precisa de internet para baixar imagens e dependências. Se a porta 8080 estiver ocupada, altere `127.0.0.1:8080:80` em `compose.yaml` para `127.0.0.1:8081:80` e use a nova porta no navegador.

## Comandos para a apresentação

```sh
docker compose ps
docker compose logs --tail=20 worker
docker compose logs --tail=20 api
docker compose exec db psql -U monitor -d monitor -c "SELECT id, name, url FROM sites;"
docker compose exec db psql -U monitor -d monitor -c "SELECT site_id, online, status_code, latency_ms FROM checks ORDER BY id DESC LIMIT 10;"
docker compose down
docker compose up -d
```

O último par de comandos demonstra persistência: `down` remove os containers e as redes, mas mantém o volume nomeado. Após subir novamente, os monitores e o histórico continuam disponíveis. Não execute `docker compose down -v` a menos que queira apagar todos os dados.

## Arquitetura

```text
Browser -> localhost:8080 -> web (Nginx, porta 80)
                              | /api/*
                              v
                        api (FastAPI, porta 8000)
                              | SQL
                              v
                        db (PostgreSQL, porta 5432) -> volume monitor_data
                              ^
                              | SQL
                        worker (Python) -> HTTP(S) público / rotas demo do web
```

- `frontend`: rede bridge dos serviços web, api e worker; permite saída HTTP do worker.
- `data`: rede interna (api, worker, db); PostgreSQL não publica porta para o host.
- Apenas Nginx publica uma porta, restrita a localhost. O Nginx serve arquivos estáticos e atua como proxy reverso da API.
- O `Dockerfile` cria a imagem Python dos serviços api e worker. A API cria as tabelas no início; `depends_on` com healthcheck aguarda o banco e a API antes de iniciar os dependentes.
- A cada ciclo, o worker consulta os sites, faz até oito sondagens em paralelo e grava o resultado. Espera 15 segundos após o fim de cada ciclo. A interface consulta a API a cada 5 segundos.
- Resultado 2xx/3xx significa online (redirecionamentos não são seguidos). 4xx/5xx e falhas de DNS, TLS, conexão ou timeout significam offline. A latência é medida do início da sondagem até os cabeçalhos HTTP, ou até a falha. Disponibilidade acumulada = verificações online / verificações totais × 100; não é SLA real baseado em duração.

## Estrutura

```text
compose.yaml          serviços, redes, volume e healthchecks
backend/Dockerfile    imagem própria Python
backend/api.py        endpoints REST e validação de cadastro
backend/db.py         consultas SQL parametrizadas
backend/schema.sql    tabelas, chave estrangeira e índice
backend/probe.py      sondagem HTTP e validação de endereços
backend/worker.py     ciclo periódico de verificações
web/nginx.conf        servidor HTTP, proxy e rotas de demonstração
web/index.html        estrutura do painel
web/styles.css        aparência responsiva
web/app.js            interação, atualização e gráfico SVG

tests/test_app.py     testes HTTP e contratos da API

docs/APRESENTACAO.md  roteiro e perguntas de estudo
```

## API REST

| Método | Endpoint | Função |
|---|---|---|
| GET | /api/health | verifica conectividade com o banco |
| GET | /api/sites | lista monitores e último resultado |
| POST | /api/sites | cria monitor: `{"name":"Exemplo","url":"https://example.com"}` |
| GET | /api/sites/{id}/history | últimas 50 verificações |
| DELETE | /api/sites/{id} | exclui monitor e histórico |
| POST | /api/demo | cadastra dois monitores locais de demonstração |

## Validação e limitações

Os 13 testes automatizados passaram. A interface também foi verificada no Chromium com API simulada (cadastro, demonstração, gráfico, histórico e exclusão). Testes direcionados da API usam acesso ao banco simulado; a sondagem HTTP usa servidor local real de testes, sem depender da internet. O ambiente em que os arquivos foram produzidos não possui Docker nem servidor PostgreSQL; por isso a execução integral do Compose e a persistência ainda precisam ser verificadas no Docker Desktop do grupo antes da entrega.

Roteiro de aceitação: subir os quatro serviços, cadastrar a demonstração, aguardar os estados online/offline, abrir histórico, cadastrar e excluir um site, executar `down` seguido de `up -d` e conferir a persistência. Verificar os logs se houver falha.

Aplicação acadêmica local, sem login, alertas, retenção automática ou hospedagem pública. Não expor à internet sem controles adicionais. O worker restringe URLs a HTTP(S), portas 80/443, valida endereços públicos a cada resolução e não segue redirecionamentos, exceto que admite as duas rotas internas de demonstração. A senha padrão do banco é exclusiva para desenvolvimento local; para implantação real, configurar credenciais seguras. Nenhuma base de dados preenchida é distribuída; `schema.sql` define somente a estrutura das tabelas.

## Testes opcionais fora dos containers

Com Python 3.12 disponível, em ambiente virtual, instale `backend/requirements.txt` e `httpx`, depois execute `python -m unittest discover -s tests -v`. Esses testes não exigem banco PostgreSQL ativo.
