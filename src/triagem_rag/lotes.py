"""Gravação em lotes e retomada da Q2 (F3b). Um id_consulta só conta como feito se a híbrida dele foi gravada,
porque a híbrida é a última parte escrita de cada consulta."""
from pathlib import Path

import pandas as pd

from triagem_rag.dados import CATEGORIAS

COLUNAS = ["id_consulta", "recuperador", "rank", "id_vizinho", "categoria_vizinho"]


def ler_concluidos(arq: Path) -> pd.DataFrame:
    """Lê o CSV parcial e descarta consultas incompletas (ex.: execução interrompida no meio de uma escrita)."""
    if not Path(arq).exists():
        return pd.DataFrame(columns=COLUNAS)
    viz = pd.read_csv(arq, on_bad_lines="skip")
    viz = viz.dropna(subset=COLUNAS)
    # categoria é a última coluna: uma linha truncada no fim do arquivo fica com categoria ausente ou parcial
    viz = viz[viz.categoria_vizinho.isin(CATEGORIAS) & viz.recuperador.isin(["vetorial", "fulltext", "hibrida"])]
    ok = viz[viz.recuperador == "hibrida"].groupby("id_consulta").size()
    feitos = set(ok[ok == 5].index)
    return viz[viz.id_consulta.isin(feitos)].astype({"id_consulta": int, "rank": int, "id_vizinho": int})


def preparar_retomada(arq: Path, ids: list[int]) -> list[int]:
    """Regrava o arquivo só com as consultas completas e devolve os ids que faltam, na ordem da amostra."""
    viz = ler_concluidos(arq)
    if Path(arq).exists():
        viz.to_csv(arq, index=False, lineterminator="\n")
    feitos = set(viz["id_consulta"])
    return [i for i in ids if i not in feitos]


def anexar(arq: Path, lote: pd.DataFrame):
    novo = not Path(arq).exists()
    with open(arq, "a", encoding="utf-8", newline="\n") as f:
        lote[COLUNAS].to_csv(f, index=False, header=novo, lineterminator="\n")
