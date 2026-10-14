# Aula 09 — Automação de Workflows com n8n

INTEGRANTES: Angel Rafael Souza da Silva, Nicolas Veiga , Janaína Lima Viana

Cadastro de fornecedores automatizado no n8n 2.42.5: consulta o CEP da sede na
BrasilAPI, decide se a sede fica em Mato Grosso, redige a mensagem ao
representante e grava o pedido na Data table `cadastro_fornecedores`.

## Conteúdo

| Arquivo                                           | O que é                                                                                                                    |
| ------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `docker-compose.yml`                              | Serviço n8n 2.42.5, fuso `America/Cuiaba`, porta só local, retenção das execuções                                          |
| `workflows/workflow01-consulta-cep.json`          | Seção 6 — um pedido, gatilho manual, 7 nós                                                                                 |
| `workflows/workflow02-rotina-diaria.json`         | Seção 7 — Schedule Trigger todo dia às 8h, lista no nó Code, saída de erro no Consultar CEP                                |
| `workflows/workflow03-formulario-fornecedor.json` | Seção 7.5 — mesmo processo a partir de um n8n Form Trigger                                                                 |
| `workflows/meu-workflow0*.json`                   | Os três workflows exportados da instalação depois de testados (sem dono e sem credenciais)                                 |
| `cliente_n8n.py`                                  | Cliente da API pública: `listar`, `importar`, `exportar`, `publicar`, `despublicar`, `execucoes`, `criar-tabela`, `linhas` |
| `pedidos-fornecedores.json`                       | Pedidos fictícios: `pedido_unico`, `pedidos_do_dia`, `pedido_formulario`                                                   |
| `AGENTS.md`                                       | Regras para um agente que opere a instalação                                                                               |

## Como subir

Nesta máquina a porta 5678 já é usada por outro serviço (MySQL), por isso o
editor fica em **http://localhost:5680**, solução indicada na seção 10 da
apostila. O contêiner se chama `n8n-aula09`, mas os comandos usam o nome do
serviço, `n8n`, e ficam iguais aos da apostila.

```bash
docker compose up -d
curl -s http://127.0.0.1:5680/healthz          # {"status":"ok"}
python3 -m venv .venv && source .venv/bin/activate
pip install httpx python-dotenv
cp .env.exemplo .env                           # cole a chave em N8N_API_KEY
python cliente_n8n.py criar-tabela cadastro_fornecedores
python cliente_n8n.py importar workflows/workflow01-consulta-cep.json
python cliente_n8n.py importar workflows/workflow02-rotina-diaria.json
python cliente_n8n.py importar workflows/workflow03-formulario-fornecedor.json
python cliente_n8n.py publicar <id da rotina>
```

O formulário fica em `http://localhost:5680/form/cadastro-fornecedor` depois de publicado.

## Resultados verificados (14/10/2026)

**Workflow 01 — consulta de CEP** (execução manual)

| CEP       | Saída do If | Linha gravada                                          |
| --------- | ----------- | ------------------------------------------------------ |
| 78048-000 | true        | PED-2026-0412, Cuiabá/MT, Avenida Miguel Sutil, `APTO` |
| 69900-100 | false       | PED-2026-0412, Rio Branco/AC, `CONFERENCIA MANUAL`     |

**Workflow 02 — rotina diária** (execução de produção, modo `trigger`, 0,41 s;
publicada com intervalo de 1 minuto só para o teste e republicada às 8h)

```
execução 5  modo=trigger  situação=success  2026-10-14T12:34:42.016Z  0.41 s
     Todo dia às 8h                   0 ms   itens por saída: 1
     Pedidos do dia                  41 ms   itens por saída: 5
     Consultar CEP                  196 ms   itens por saída: 4/1
     Endereço em MT?                  3 ms   itens por saída: 3/1
     Apto para cadastro              57 ms   itens por saída: 3
     Registrar pedido                23 ms   itens por saída: 3
     Registrar pedido                16 ms   itens por saída: 1
     Registrar pedido                20 ms   itens por saída: 1
     Conferência manual              24 ms   itens por saída: 1
     CEP não localizado              16 ms   itens por saída: 1
```

| Protocolo     | Município                      | Situação           |
| ------------- | ------------------------------ | ------------------ |
| PED-2026-0413 | Rondonópolis/MT                | APTO               |
| PED-2026-0414 | Sinop/MT                       | APTO               |
| PED-2026-0417 | Várzea Grande/MT               | APTO               |
| PED-2026-0415 | Rio Branco/AC                  | CONFERENCIA MANUAL |
| PED-2026-0416 | (CEP 78890-000 não localizado) | CEP NAO LOCALIZADO |

**Workflow 03 — formulário** (modo `webhook`, 0,24 s): envio com os dados de
`pedido_formulario` gravou `PED-2026-0007`, Cuiabá/MT, `APTO`.

O Form Trigger usa a versão 2.5 do nó: nas versões anteriores a 2.4 o Field Name
só vale para campos ocultos, e os campos chegam com o rótulo (`CEP da sede`) em
vez de `cep`, o que faz todo envio cair em `CEP NAO LOCALIZADO`.

## Onde ficam os dados pessoais (seção 9)

Os pedidos trazem nome e e-mail do representante, dados pessoais pela LGPD
(Lei nº 13.709/2018) mesmo quando a pessoa age em nome da empresa.

| Lugar                              | O que guarda                                                              | Decisão tomada                                                                                                                                                                                                                            |
| ---------------------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Data table `cadastro_fornecedores` | Protocolo, razão social, CNPJ, e-mail, CEP, endereço, situação e mensagem | Mesma retenção da planilha que substitui; baixar em CSV e limpar ao fim de cada ciclo de cadastro                                                                                                                                         |
| Execuções                          | Entrada e saída de cada nó, inclusive nome e e-mail                       | Apagadas após 336 h (14 dias) ou acima de 10 mil execuções — `EXECUTIONS_DATA_MAX_AGE` e `EXECUTIONS_DATA_PRUNE_MAX_COUNT` no `docker-compose.yml`. Em produção, desligar _Save successful production executions_ e manter só as com erro |
| Credenciais                        | Nenhuma nesta aula (a BrasilAPI não exige chave)                          | O arquivo `config` do volume guarda a chave de cifra e entra na cópia de segurança                                                                                                                                                        |

- Tudo fica no volume `n8n_data` (`/home/node/.n8n`): quem acessa o volume acessa todos os pedidos. `docker compose down -v` apaga tudo.
- A chave da API fica só no `.env`, que o `.gitignore` exclui; ela tem validade de 90 dias.
- O `export:workflow` da CLI inclui nome e e-mail do dono no campo `shared`; por isso `workflows/rotina-cli.json` e `workflows/todos.json` estão no `.gitignore`, e os arquivos versionados foram exportados pelo `cliente_n8n.py exportar`.
- A mensagem gravada é um rascunho: a decisão do cadastro continua com quem analisa os documentos, e a consulta de CEP é dado auxiliar, não prova.
