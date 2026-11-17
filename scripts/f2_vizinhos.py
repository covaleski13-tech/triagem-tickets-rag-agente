"""F2 passo 5: vizinhos dos 400 (vetorial e full-text, 50 cada), híbrida top 5 via rrf() sobre o CSV, K1 e C.
Sem API. Saídas sem texto de ticket."""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pandas as pd
import psycopg

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from triagem_rag.dados import DATA_DIR, ds2_com_splits, ids_amostra_400  # noqa: E402
from triagem_rag.recuperacao import (buscar_fulltext, buscar_vetorial, pg_dsn_psycopg, rrf,  # noqa: E402
                                     voto_k1)

OUT = RAIZ / "results/f2"
N_CONEXOES = 4


def main():
    t0 = time.perf_counter()
    df = ds2_com_splits().set_index("id")
    ids = ids_amostra_400()
    texto = df["Document"]

    buscar_vetorial(texto[ids[0]], 1)  # carrega o modelo antes das threads
    lotes = [ids[k::N_CONEXOES] for k in range(N_CONEXOES)]

    def trabalhar(lote):
        linhas = []
        with psycopg.connect(pg_dsn_psycopg()) as con:
            for i in lote:
                for rec, res in (("vetorial", buscar_vetorial(texto[i], 50)),
                                 ("fulltext", buscar_fulltext(texto[i], 50, con=con))):
                    linhas += [(i, rec, r, j, c) for j, c, r in res]
        return linhas

    with ThreadPoolExecutor(N_CONEXOES) as ex:
        linhas = [l for parte in ex.map(trabalhar, lotes) for l in parte]
    viz = pd.DataFrame(linhas, columns=["id_consulta", "recuperador", "rank", "id_vizinho", "categoria_vizinho"])
    ordem = {i: k for k, i in enumerate(ids)}
    viz = viz.sort_values(["id_consulta", "recuperador", "rank"], key=lambda s: s.map(ordem) if s.name == "id_consulta"
                          else s, kind="stable").reset_index(drop=True)
    t_busca = time.perf_counter() - t0

    # anti-vazamento
    assert (df.loc[viz["id_vizinho"], "split_grupo"] == "treino").all()
    assert (viz["id_vizinho"] != viz["id_consulta"]).all()
    assert (df.loc[viz["id_vizinho"], "group_id"].values != df.loc[viz["id_consulta"], "group_id"].values).all()
    cont = viz.groupby(["id_consulta", "recuperador"]).size().unstack(fill_value=0)
    assert set(cont.index) == set(ids)
    viz.to_csv(OUT / "vizinhos_400.csv", index=False, lineterminator="\n")

    hib, k1 = [], {}
    for i, g in viz.groupby("id_consulta", sort=False):
        listas = [g[g.recuperador == r].sort_values("rank")["id_vizinho"].tolist() for r in ("vetorial", "fulltext")]
        cat = dict(zip(g["id_vizinho"], g["categoria_vizinho"]))
        top = rrf(listas, top=5)
        hib += [(i, r, j, cat[j]) for r, (j, _) in enumerate(top, 1)]
        k1[i] = voto_k1([cat[j] for j, _ in top])
    hib = pd.DataFrame(hib, columns=["id_consulta", "rank", "id_vizinho", "categoria_vizinho"])
    assert (hib.groupby("id_consulta").size() == 5).all()
    hib.to_csv(OUT / "hibrida_top5_400.csv", index=False, lineterminator="\n")

    probs = pd.read_csv(DATA_DIR / "caso/f3_probs_holdout_grupo.csv").set_index("id")
    rot = df.loc[ids, "Topic_group"]
    c = probs.loc[ids, "pred"]
    assert int((c.values == rot.values).sum()) == 278
    pd.DataFrame({"id": ids, "k1": [k1[i] for i in ids], "c": c.values}).to_csv(
        OUT / "pred_k1_c.csv", index=False, lineterminator="\n")

    out = {"n_consultas": len(ids), "linhas_vizinhos": len(viz),
           "vizinhos_por_recuperador_min": cont.min().to_dict(), "vizinhos_por_recuperador_max": cont.max().to_dict(),
           "buscas_s": round(t_busca, 1), "total_s": round(time.perf_counter() - t0, 1), "conexoes": N_CONEXOES,
           "acertos_k1": int(sum(k1[i] == rot[i] for i in ids)), "acertos_c": 278}
    (OUT / "vizinhos_meta.json").write_text(json.dumps(out, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(out))


if __name__ == "__main__":
    main()
