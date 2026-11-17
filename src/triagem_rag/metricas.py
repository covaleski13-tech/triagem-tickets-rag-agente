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


FAMILIA_Q1 = [("v3", "v1"), ("v3", "k1"), ("v3", "c"), ("v2", "v3")]  # F0 §2: primária primeiro; não alterar


def familia(acertos: dict) -> list[dict]:
    """McNemar exato + Holm sobre exatamente as 4 comparações pré-registradas, nesta ordem."""
    linhas = []
    for a, b in FAMILIA_Q1:
        m = mcnemar_exato(acertos[a], acertos[b])
        acc_a, acc_b = float(np.mean(acertos[a])), float(np.mean(acertos[b]))
        linhas.append({"comparacao": f"{a}_x_{b}", "a": a, "b_variante": b, "acuracia_a": acc_a, "acuracia_b": acc_b,
                       "diferenca_pp": 100 * (acc_a - acc_b), "b": m["b"], "c": m["c"], "p_bruto": m["p"]})
    for l, p in zip(linhas, holm([l["p_bruto"] for l in linhas])):
        l["p_holm"] = p
    return linhas


def veredictos(fam) -> dict:
    """Critérios da F0 §2 aplicados mecanicamente a partir da tabela da família (DataFrame ou lista de dicts)."""
    linhas = fam.to_dict("records") if hasattr(fam, "to_dict") else fam
    f = {l["comparacao"]: l for l in linhas}
    assert [l["comparacao"] for l in linhas] == [f"{a}_x_{b}" for a, b in FAMILIA_Q1]
    v31, v3k, v3c = f["v3_x_v1"], f["v3_x_k1"], f["v3_x_c"]
    return {
        "rag_ajuda": bool(v31["acuracia_a"] > v31["acuracia_b"] and v31["p_holm"] < 0.05),
        "llm_agrega": bool(v3k["acuracia_a"] > v3k["acuracia_b"] and v3k["p_holm"] < 0.05),
        # F0 não definiu teste para este critério: comparação pontual; o p de Holm fica ao lado, só informativo
        "vale_para_producao": bool(v3c["acuracia_a"] >= v3c["acuracia_b"]),
        "vale_para_producao_p_holm_v3_x_c": float(v3c["p_holm"]),
    }


def precisao_rotulo(rotulo: str, categorias_vizinhos: list[str]) -> float:
    return sum(c == rotulo for c in categorias_vizinhos) / len(categorias_vizinhos)


def bootstrap_ic_media(valores, n_boot=2000, seed=42) -> tuple[float, float]:
    """IC 95% percentil da média, reamostrando as consultas."""
    x = np.asarray(valores, float)
    rng = np.random.default_rng(seed)
    medias = x[rng.integers(0, len(x), (n_boot, len(x)))].mean(axis=1)
    return (float(np.percentile(medias, 2.5)), float(np.percentile(medias, 97.5)))


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
