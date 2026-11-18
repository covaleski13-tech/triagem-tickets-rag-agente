"""Adaptador: liga a política do case (src/triagem_rag/caso/triagem.py) aos caminhos deste repositório,
sem alterar a lógica do case. Importar este módulo configura o case; use `triagem` daqui."""
import os
import sys
from pathlib import Path

from triagem_rag.dados import DATA_DIR, RAIZ

CASO_DIR = RAIZ / "src" / "triagem_rag" / "caso"
RUNTIME_AGENTE = RAIZ / "runtime_agente"

# o case importa `from comum import ...` como módulo de topo
if str(CASO_DIR) not in sys.path:
    sys.path.insert(0, str(CASO_DIR))
import triagem  # noqa: E402

triagem.OUT_DIR = DATA_DIR / "caso"  # f8_politica_por_categoria.csv e f8_faixas.json


def versao_modelo_f1() -> str:
    """Versão do joblib gravado na F1 (data/modelos/modelo_<versao>.joblib), lida do nome do arquivo.
    Não recalcular pela fórmula do case: na F1 o hash foi feito sobre a cópia CRLF do f1_splits.csv
    (antes da correção para LF) e não bate com o arquivo atual; ver docs/decisoes.md (F4)."""
    arqs = sorted((DATA_DIR / "modelos").glob("modelo_*.joblib"))
    assert len(arqs) == 1, f"esperado 1 modelo da F1 em data/modelos, achei {len(arqs)}"
    return arqs[0].stem.removeprefix("modelo_")


VERSAO_MODELO = versao_modelo_f1()
os.environ.setdefault("TRIAGEM_CACHE_DIR", str(DATA_DIR / "modelos"))
os.environ.setdefault("TRIAGEM_MODELO_VERSAO", VERSAO_MODELO)
os.environ.setdefault("TRIAGEM_RUNTIME_DIR", str(RUNTIME_AGENTE))

triar = triagem.triar
mascarar = triagem.mascarar
ORDEM = triagem.ORDEM
