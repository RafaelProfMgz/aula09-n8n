"""Cliente da API pública do n8n usado na Aula 09.

Uso (com o .venv ativo e o .env preenchido):

    python cliente_n8n.py listar
    python cliente_n8n.py importar workflows/workflow01-consulta-cep.json
    python cliente_n8n.py exportar <id> workflows/meu-workflow.json
    python cliente_n8n.py publicar <id>
    python cliente_n8n.py despublicar <id>
    python cliente_n8n.py execucoes <id> [quantidade]
    python cliente_n8n.py criar-tabela cadastro_fornecedores
    python cliente_n8n.py linhas cadastro_fornecedores

A chave é lida do .env (N8N_API_KEY) e nunca aparece no código.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

URL = os.environ.get("N8N_URL", "http://127.0.0.1:5678") + "/api/v1"
cliente = httpx.Client(base_url=URL, headers={"X-N8N-API-KEY": os.environ["N8N_API_KEY"]}, timeout=60)

# Campos que o POST /workflows aceita; os demais (id, shared, versionId...) são da instalação.
CAMPOS_GRAVAVEIS = ("name", "nodes", "connections", "settings")

COLUNAS_CADASTRO = [
    "protocolo", "razao_social", "cnpj", "email", "cep", "municipio",
    "uf", "logradouro", "situacao", "mensagem", "consultado_em",
]


def listar() -> None:
    """Lista os workflows: id, situação e nome."""
    r = cliente.get("/workflows", params={"limit": 250})
    r.raise_for_status()
    for wf in r.json()["data"]:
        situacao = "publicado" if wf.get("active") else "rascunho"
        print(f"{wf['id']}  {situacao:<10}  {wf['name']}")


def importar(arquivo: str) -> None:
    """Cria um workflow a partir de um arquivo JSON exportado."""
    dados = json.loads(Path(arquivo).read_text(encoding="utf-8"))
    if isinstance(dados, list):        # o export:workflow da linha de comando grava uma lista
        dados = dados[0]
    corpo = {k: dados[k] for k in CAMPOS_GRAVAVEIS if k in dados}
    r = cliente.post("/workflows", json=corpo)
    r.raise_for_status()
    print(f"importado: {r.json()['name']} ({r.json()['id']})")


def exportar(workflow_id: str, arquivo: str) -> None:
    """Grava o workflow sem o projeto dono e sem os identificadores de credencial."""
    r = cliente.get(f"/workflows/{workflow_id}")
    r.raise_for_status()
    wf = r.json()
    for no in wf["nodes"]:
        for cred in no.get("credentials", {}).values():
            cred.pop("id", None)
    saida = {k: wf[k] for k in ("name", "nodes", "connections", "settings") if k in wf}
    saida["pinData"] = {}
    saida["id"] = wf["id"]
    Path(arquivo).write_text(json.dumps(saida, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"exportado: {wf['name']} -> {arquivo}")


def publicar(workflow_id: str) -> None:
    r = cliente.post(f"/workflows/{workflow_id}/publish", json={})
    r.raise_for_status()
    print(f"publicado: {r.json()['name']}")


def despublicar(workflow_id: str) -> None:
    r = cliente.post(f"/workflows/{workflow_id}/unpublish")
    r.raise_for_status()
    print(f"retirado de produção: {r.json()['name']}")


def execucoes(workflow_id: str, quantidade: str = "5") -> None:
    """Lista as execuções de um workflow com a duração e os itens por nó."""
    r = cliente.get("/executions", params={"workflowId": workflow_id, "limit": int(quantidade), "includeData": "true"})
    r.raise_for_status()
    for ex in r.json()["data"]:
        inicio = datetime.fromisoformat(ex["startedAt"].replace("Z", "+00:00"))
        fim = datetime.fromisoformat(ex["stoppedAt"].replace("Z", "+00:00")) if ex.get("stoppedAt") else inicio
        print(f"execução {ex['id']}  modo={ex['mode']}  situação={ex['status']}  {ex['startedAt']}  "
              f"{(fim - inicio).total_seconds():.2f} s")
        run_data = ((ex.get("data") or {}).get("resultData") or {}).get("runData") or {}
        for no, rodadas in run_data.items():
            for rodada in rodadas:
                saidas = (rodada.get("data") or {}).get("main") or []
                contagem = "/".join(str(len(s or [])) for s in saidas)
                print(f"     {no:<28} {rodada.get('executionTime', 0):>5} ms   itens por saída: {contagem}")


def _id_tabela(nome: str) -> str:
    r = cliente.get("/data-tables", params={"filter": json.dumps({"name": nome})})
    r.raise_for_status()
    tabelas = [t for t in r.json()["data"] if t["name"] == nome]
    if not tabelas:
        sys.exit(f"tabela {nome} não encontrada; crie com: python cliente_n8n.py criar-tabela {nome}")
    return tabelas[0]["id"]


def criar_tabela(nome: str = "cadastro_fornecedores") -> None:
    """Cria a Data table com as onze colunas de texto da seção 6.1."""
    corpo = {"name": nome, "columns": [{"name": c, "type": "string"} for c in COLUNAS_CADASTRO]}
    r = cliente.post("/data-tables", json=corpo)
    r.raise_for_status()
    print(f"tabela criada: {nome} ({r.json()['id']})")


def linhas(nome: str = "cadastro_fornecedores") -> None:
    """Mostra as linhas gravadas na Data table."""
    r = cliente.get(f"/data-tables/{_id_tabela(nome)}/rows", params={"limit": 250, "sortBy": "id:asc"})
    r.raise_for_status()
    for linha in r.json()["data"]:
        print(f"{linha['id']:>3}  {linha.get('protocolo') or '':<16} {linha.get('situacao') or '':<20} "
              f"{linha.get('municipio') or '-'}/{linha.get('uf') or '-'}  {linha.get('consultado_em') or ''}")


OPERACOES = {
    "listar": listar,
    "importar": importar,
    "exportar": exportar,
    "publicar": publicar,
    "despublicar": despublicar,
    "execucoes": execucoes,
    "criar-tabela": criar_tabela,
    "linhas": linhas,
}

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in OPERACOES:
        sys.exit(__doc__)
    OPERACOES[sys.argv[1]](*sys.argv[2:])
