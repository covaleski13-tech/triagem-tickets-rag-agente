import pandas as pd
import pytest

from triagem_rag.dados import DATA_DIR, ids_amostra_400, ler_splits
from triagem_rag.recuperacao import rrf


def test_rrf_manual():
    res = rrf([[1, 2, 3], [3, 1, 4]], k_rrf=60, top=10)
    esperado = {1: 1 / 61 + 1 / 62, 3: 1 / 63 + 1 / 61, 2: 1 / 62, 4: 1 / 63}
    assert [i for i, _ in res] == [1, 3, 2, 4]
    for i, s in res:
        assert s == pytest.approx(esperado[i], abs=1e-15)


def test_rrf_empate():
    # 1 e 2 têm o mesmo score (1/61 + 1/62) e o mesmo melhor rank (1): desempata pelo menor id
    assert [i for i, _ in rrf([[2, 1], [1, 2]], top=5)] == [1, 2]
    # 5 e 8 empatam em 1/61 (rank 1), 9 e 7 em 1/62 (rank 2): dentro de cada par, menor id primeiro
    assert [i for i, _ in rrf([[5, 9], [8, 7]], top=5)] == [5, 8, 7, 9]


def test_rrf_top():
    assert len(rrf([[1, 2, 3], [4, 5, 6]], top=5)) == 5


def test_amostra_400():
    ids = ids_amostra_400()
    assert len(ids) == 400 and len(set(ids)) == 400
    sp = ler_splits().set_index("id")
    assert (sp.loc[ids, "split_grupo"] == "holdout").all()


def test_splits_sem_grupo_cruzado():
    sp = ler_splits()
    g = sp.groupby("group_id")["split_grupo"].nunique()
    assert (g == 1).all()


def test_v0_pred_sem_texto():
    pred = pd.read_csv(DATA_DIR / "caso/f3_v0_pred.csv")
    assert list(pred.columns) == ["id", "pred_caso", "valida"]
