# Apresentação e arguição

## Demonstração sugerida

1. Mostrar o problema: verificar se um serviço web está respondendo sem abrir cada URL manualmente.
2. Abrir o painel; carregar a demonstração. Explicar os estados HTTP 200 e 503, o histórico e a disponibilidade por amostras.
3. Mostrar `docker compose ps` com quatro serviços; abrir `compose.yaml` e explicar imagens, build, redes e volume.
4. Abrir `backend/probe.py` e `worker.py`: explicar o GET, medição de latência, registro do resultado e intervalo de espera.
5. Mostrar `backend/api.py` e `db.py`: explicar a API REST, consultas parametrizadas e persistência. Mostrar `web/nginx.conf` e o encaminhamento de `/api/`.
6. Demonstrar `docker compose down` e `docker compose up -d` preservando os dados. Não use `-v`.

## Perguntas possíveis do professor

**Por que quatro serviços?** Separação de responsabilidades. Nginx serve HTTP, API atende o navegador, worker executa monitoramento independente da interface e PostgreSQL mantém os dados. Dois serviços são próprios.

**Imagem vs. container?** Imagem é o modelo com dependências e código. Container é a instância em execução. API e worker usam a mesma definição de imagem, mas comandos e processos diferentes.

**Dockerfile vs. Compose?** Dockerfile constrói a imagem. Compose descreve como os serviços devem executar juntos, incluindo portas, redes, volumes e dependências.

**Como os serviços se encontram?** Docker fornece DNS na rede; a API usa `db:5432`, Nginx encaminha para `api:8000`, o worker usa `web:80` para a demo.

**Por que duas redes?** `frontend` conecta Nginx, API e worker; `data` isola o banco. Nginx não pertence à rede de dados. O worker precisa de saída HTTP para a internet.

**Por que só uma porta publicada?** O navegador entra pelo Nginx. API e banco usam portas internas dos containers e não precisam estar publicados no host.

**Como funciona o volume?** O PostgreSQL grava seus dados no volume `monitor_data`, mantido independentemente dos containers. `down` não elimina o volume; `down -v` elimina.

**O que faz o healthcheck?** O banco é verificado via `pg_isready`. A API verifica uma consulta simples ao banco. Compose aguarda esses estados antes de iniciar os dependentes. Healthcheck não é o mesmo que a sondagem de URLs da aplicação.

**Como funciona a sondagem?** Worker lê os sites, resolve DNS, bloqueia endereços não públicos (exceto duas rotas demo), faz GET, mede latência até os cabeçalhos ou falha, classifica o resultado e grava no banco. 2xx/3xx são sucesso; 4xx/5xx ou erro de conexão são falha. Não segue redirecionamentos.

**Se o worker parar, a página cai?** Não necessariamente. API, Nginx e banco continuam funcionando, mas o histórico não recebe novas verificações.

**Se o banco parar?** A API não consegue consultar dados e o worker não consegue gravar. O healthcheck da API falha. O worker tenta um novo ciclo após o intervalo.

**Como a interface recebe os resultados?** JavaScript consulta a API REST a cada 5 segundos (polling). O Nginx encaminha a requisição e a API lê o banco; não há WebSocket.

**Como calculamos disponibilidade?** Número de sondagens online dividido pelo total, multiplicado por 100. É uma estimativa por amostras, não medição contínua do tempo em operação.

**E se dois monitores tiverem a mesma URL?** O banco tem uma restrição UNIQUE; a API responde HTTP 409 ao tentar repetir o cadastro.

**O projeto roda na nuvem?** Foi planejado para rodar de forma containerizada localmente, como o enunciado permite. Poderia ser adaptado para uma VM na nuvem, mas isso exigiria configuração de segurança e acesso externo. Não alegar que está hospedado na nuvem se não foi publicado.

**Quais são as limitações?** Uso acadêmico local sem autenticação, sem alertas e sem alta disponibilidade. Não segue redirecionamentos; o histórico cresce continuamente. A integração real deve ser validada antes da apresentação.

## Entrega

Enviar os arquivos de implementação pelo Canvas sem dados preenchidos (somente código e schema). Completar os nomes dos integrantes no artigo, executar o roteiro de aceitação, atualizar a seção de resultados conforme a observação real, exportar PDF e imprimir exatamente a mesma versão em A4. Entregar o impresso e agendar presencialmente até 26/11/2026.
