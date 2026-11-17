import numpy as np
import pandas as pd
import pytest

from triagem_rag.dados import RAIZ, ds2_com_splits, ids_amostra_400
from triagem_rag.metricas import (FAMILIA_Q1, bootstrap_ic_media, familia, holm, precisao_rotulo,
                                  veredictos)


def test_familia_ordem():
    rng = np.random.default_rng(0)
    ac = {v: rng.random(400) < p for v, p in {"v1": .3, "v2": .45, "v3": .5, "k1": .55, "c": .7}.items()}
    f = familia(ac)
    assert [l["comparacao"] for l in f] == ["v3_x_v1", "v3_x_k1", "v3_x_c", "v2_x_v3"]
    assert FAMILIA_Q1[0] == ("v3", "v1")
    assert [l["p_holm"] for l in f] == holm([l["p_bruto"] for l in f])


def _fam(acc, p):
    return pd.DataFrame([{"comparacao": f"{a}_x_{b}", "acuracia_a": x, "acuracia_b": y, "p_holm": q}
                         for (a, b), (x, y), q in zip(FAMILIA_Q1, acc, p)])


def test_veredictos():
    v = veredictos(_fam([(.45, .24), (.45, .55), (.45, .70), (.48, .45)], [1e-16, 1e-3, 1e-13, .23]))
    assert v["rag_ajuda"] is True and v["llm_agrega"] is False and v["vale_para_producao"] is False
    # V3 > V1 mas p ajustado >= 0,05: não ajuda; V3 >= C pontual: vale (sem teste, critério da F0)
    v = veredictos(_fam([(.30, .28), (.60, .55), (.70, .70), (.5, .5)], [.06, .01, .9, 1.0]))
    assert v["rag_ajuda"] is False and v["llm_agrega"] is True and v["vale_para_producao"] is True
    with pytest.raises(AssertionError):
        veredictos(_fam([(.5, .5)] * 4, [1] * 4).iloc[[1, 0, 2, 3]])


def test_precisao_rotulo():
    assert precisao_rotulo("Access", ["Access", "Hardware", "Access", "Access", "Storage"]) == pytest.approx(0.6)


def test_bootstrap_seed():
    x = np.random.default_rng(1).random(300)
    assert bootstrap_ic_media(x, seed=42) == bootstrap_ic_media(x, seed=42)
    assert bootstrap_ic_media(x, seed=42) != bootstrap_ic_media(x, seed=43)


@pytest.mark.parametrize("v", ["v2", "v3"])
def test_exemplos_v2_v3(v):
    arq = RAIZ / f"results/f3/exemplos_{v}.csv"
    if not arq.exists():
        pytest.skip(f"{arq.name} ainda não gerado")
    ex = pd.read_csv(arq)
    df = ds2_com_splits().set_index("id")
    assert ex["id"].drop_duplicates().tolist() == ids_amostra_400()
    assert (ex.groupby("id").size() == 5).all()
    assert (df.loc[ex["id_exemplo"], "split_grupo"] == "treino").all()
    assert (df.loc[ex["id_exemplo"], "group_id"].values != df.loc[ex["id"], "group_id"].values).all()
    assert (ex.groupby("id", sort=False)["ordem"].apply(list) == pd.Series([[1, 2, 3, 4, 5]] * 400)
            .set_axis(ex["id"].drop_duplicates())).all()
    fonte = pd.read_csv(RAIZ / ("results/f2/vizinhos_400.csv" if v == "v2" else "results/f2/hibrida_top5_400.csv"))
    if v == "v2":
        fonte = fonte[(fonte.recuperador == "vetorial") & (fonte["rank"] <= 5)]
    m = ex.merge(fonte, left_on=["id", "ordem"], right_on=["id_consulta", "rank"])
    assert len(m) == 2000 and (m["id_exemplo"] == m["id_vizinho"]).all()


def test_retomada_lotes(tmp_path):
    from triagem_rag.lotes import anexar, ler_concluidos, preparar_retomada
    arq = tmp_path / "vizinhos_q2.csv"

    def linhas(i, n_hib):
        r = [(i, "vetorial", k, 100 + k, "Access") for k in (1, 2)] + [(i, "fulltext", 1, 200, "Storage")]
        return r + [(i, "hibrida", k, 300 + k, "Hardware") for k in range(1, n_hib + 1)]

    cols = ["id_consulta", "recuperador", "rank", "id_vizinho", "categoria_vizinho"]
    assert preparar_retomada(arq, [1, 2, 3]) == [1, 2, 3] and not arq.exists()
    anexar(arq, pd.DataFrame(linhas(1, 5) + linhas(2, 5), columns=cols))
    anexar(arq, pd.DataFrame(linhas(3, 3), columns=cols))  # 3: interrompido antes de completar a híbrida
    with open(arq, "a", encoding="utf-8", newline="\n") as f:
        f.write("3,hibrida,4,30")  # linha truncada no fim do arquivo
    assert preparar_retomada(arq, [1, 2, 3, 4]) == [3, 4]
    viz = ler_concluidos(arq)
    assert set(viz.id_consulta) == {1, 2} and len(viz) == 2 * 8
    assert set(pd.read_csv(arq).id_consulta) == {1, 2}  # arquivo regravado sem o id incompleto
    anexar(arq, pd.DataFrame(linhas(3, 5), columns=cols))
    assert preparar_retomada(arq, [1, 2, 3]) == []
