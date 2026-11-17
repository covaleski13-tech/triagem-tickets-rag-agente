import numpy as np
from scipy.stats import binomtest
from sklearn.metrics import f1_score

from triagem_rag.dados import CATEGORIAS

FALHA = "falha"


def wilson(k, n, z=1.959964):
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    centro = (p + z * z / (2 * n)) / (1 + z * z / n)
    meia = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / (1 + z * z / n)
    return (max(0.0, centro - meia), min(1.0, centro + meia))


def macro_f1(y, p) -> float:
    # `falha` não está em labels: conta como erro (FN da classe verdadeira) sem virar classe própria
    return float(f1_score(list(y), list(p), labels=CATEGORIAS, average="macro", zero_division=0))


def matriz_confusao(y, p) -> list[list[int]]:
    """8 linhas (rótulo) × 9 colunas (8 categorias + falha)."""
    cols = CATEGORIAS + [FALHA]
    m = np.zeros((len(CATEGORIAS), len(cols)), dtype=int)
    for a, b in zip(y, p):
        m[CATEGORIAS.index(a), cols.index(b)] += 1
    return m.tolist()


def mcnemar_exato(acertos_a, acertos_b) -> dict:
    a, b_ = np.asarray(acertos_a, bool), np.asarray(acertos_b, bool)
    b = int((a & ~b_).sum())
    c = int((~a & b_).sum())
    p = 1.0 if b + c == 0 else float(binomtest(min(b, c), b + c, 0.5).pvalue)
    return {"b": b, "c": c, "p": p}


def holm(pvalores) -> list[float]:
    p = np.asarray(pvalores, float)
    m = len(p)
    ordem = np.argsort(p, kind="stable")
    ajust = np.empty(m)
    acum = 0.0
    for i, j in enumerate(ordem):
        acum = max(acum, (m - i) * p[j])
        ajust[j] = min(1.0, acum)
    return ajust.tolist()
