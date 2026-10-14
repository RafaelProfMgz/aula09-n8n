# AGENTS.md — Aula 09 (n8n)

## Contexto
- n8n 2.42.5 em contêiner (`docker compose`), editor em http://localhost:5680.
- Workflows versionados em `workflows/` como JSON; registro na Data table `cadastro_fornecedores`.
- Operação pela API com `python cliente_n8n.py <operação>` (ambiente `.venv`).

## Proibido
- Ler, exibir ou copiar o `.env` ou qualquer chave de API.
- Qualquer operação de apagar: workflows, execuções, tabelas, linhas, volumes (`docker compose down -v`).
- Publicar ou retirar de produção sem pedido explícito.
- Acrescentar ao workflow consultas que ampliem dados pessoais (ex.: CNPJ com quadro de sócios) sem pedido explícito.

## Como verificar uma mudança
1. Editar o JSON em `workflows/` e importar com `python cliente_n8n.py importar <arquivo>`.
2. Executar e conferir com `python cliente_n8n.py execucoes <id>` e `python cliente_n8n.py linhas cadastro_fornecedores`.
3. Os nomes dos nós são usados nas expressões (`$('Dados do pedido')`, `$('Pedidos do dia')`): não renomear.
