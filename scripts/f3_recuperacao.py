"""F3/F3b (Q2): qualidade de recuperação na amostra G9-a (2.000 do holdout, seed 42) e no recorte dos 400.
Sem API. A amostra é gravada antes de qualquer consulta.
- `--so-400`: só o recorte dos 400, com as listas da F2 (sem consulta nova).
- sem argumento (F3b, execução longa): 4 threads no full-text, grava vizinhos_q2.csv em lotes de 100, retomável
  (pula os id_consulta já completos), imprime o progresso e só calcula as métricas com os 2.000 presentes."""
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd
import psycopg

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from triagem_rag.dados import SEED, ds2_com_splits, ids_amostra_400  # noqa: E402
from triagem_rag.lotes import anexar, ler_concluidos, preparar_retomada  # noqa: E402
from triagem_rag.metricas import bootstrap_ic_media, precisao_rotulo  # noqa: E402
from triagem_rag.recuperacao import (buscar_fulltext, embeddings, pg_dsn_psycopg, rrf, vector_store,  # noqa: E402
                                     voto_k1)

F2, F3 = RAIZ / "results/f2", RAIZ / "results/f3"
N_AMOSTRA, N_THREADS, N_LOTE = 2000, 4, 100
ARQ_VIZ = F3 / "vizinhos_q2.csv"
RECS = ("vetorial", "fulltext", "hibrida")
PARES = (("hibrida", "vetorial"), ("hibrida", "fulltext"), ("fulltext", "vetorial"))


def amostra(df):
    arq = F3 / "amostra_q2_ids.csv"
    if not arq.exists():
        ho = df[df["split_grupo"] == "holdout"].sort_values("id")
        pd.DataFrame({"id": ho.sample(N_AMOSTRA, random_state=SEED)["id"].values}).to_csv(arq, index=False,
                                                                                          lineterminator="\n")
    return pd.read_csv(arq)["id"].tolist()


def fulltext_paralelo(ids, texto):
    lotes = [ids[k::N_THREADS] for k in range(N_THREADS)]

    def trab(lote):
        with psycopg.connect(pg_dsn_psycopg()) as con:
            return {i: buscar_fulltext(texto[i], 50, con=con) for i in lote}

    out = {}
    with ThreadPoolExecutor(N_THREADS) as ex:
        for parte in ex.map(trab, lotes):
            out.update(parte)
    return out


def com_hibrida(viz):
    """Acrescenta a híbrida top 5 via rrf() sobre as listas já gravadas, sem nova consulta."""
    hib = []
    for i, g in viz.groupby("id_consulta", sort=False):
        listas = [g[g.recuperador == r].sort_values("rank")["id_vizinho"].tolist() for r in ("vetorial", "fulltext")]
        cat = dict(zip(g["id_vizinho"], g["categoria_vizinho"]))
        hib += [(i, "hibrida", r, j, cat[j]) for r, (j, _) in enumerate(rrf(listas, top=5), 1)]
    return pd.concat([viz, pd.DataFrame(hib, columns=viz.columns)], ignore_index=True)


def metricas(viz, rotulo, ids):
    por = {}
    for rec in RECS:
        top = viz[(viz.recuperador == rec) & (viz["rank"] <= 5)].sort_values(["id_consulta", "rank"])
        cats = top.groupby("id_consulta")["categoria_vizinho"].apply(list).reindex(ids)
        # consulta sem resultado: precisão 0 e K1 sem voto (erro); só pode ocorrer no full-text
        prec = np.array([precisao_rotulo(rotulo[i], c) if isinstance(c, list) and c else 0.0 for i, c in cats.items()])
        k1 = np.array([float(isinstance(c, list) and bool(c) and voto_k1(c) == rotulo[i]) for i, c in cats.items()])
        por[rec] = {"precisao5": prec, "k1": k1, "sem_resultado": int(sum(not isinstance(c, list) for c in cats))}
    res = {"n": len(ids), "por_recuperador": {}, "diferencas": []}
    for rec in RECS:
        r = por[rec]
        res["por_recuperador"][rec] = {
            "precisao5_media": round(float(r["precisao5"].mean()), 4),
            "precisao5_ic95": [round(x, 4) for x in bootstrap_ic_media(r["precisao5"], seed=SEED)],
            "k1_acertos": int(r["k1"].sum()), "k1_acuracia": round(float(r["k1"].mean()), 4),
            "sem_resultado": r["sem_resultado"], "sem_resultado_pct": round(100 * r["sem_resultado"] / len(ids), 2)}
    for a, b in PARES:
        for met in ("precisao5", "k1"):
            d = por[a][met] - por[b][met]
            lo, hi = bootstrap_ic_media(d, seed=SEED)
            res["diferencas"].append({"par": f"{a}-{b}", "metrica": met, "diferenca_media": round(float(d.mean()), 4),
                                      "ic95_inf": round(lo, 4), "ic95_sup": round(hi, 4)})
    return res


def recorte_400(cat):
    ids400 = ids_amostra_400()
    v400 = pd.read_csv(F2 / "vizinhos_400.csv")
    v400 = pd.concat([v400, pd.read_csv(F2 / "hibrida_top5_400.csv").assign(recuperador="hibrida")[v400.columns]],
                     ignore_index=True)
    return metricas(v400, cat, ids400)


def so_400():
    """Recorte dos 400 com as listas já gravadas na F2: nenhuma consulta nova."""
    cat = ds2_com_splits().set_index("id")["Topic_group"]
    res = {"amostra_q2": "pendente: F3b (q2_tempos.json)", "recorte_400": recorte_400(cat)}
    (F3 / "q2_recuperacao.json").write_text(json.dumps(res, indent=2), encoding="utf-8", newline="\n")
    pd.DataFrame([{"universo": "recorte_400", **d} for d in res["recorte_400"]["diferencas"]]).to_csv(
        F3 / "q2_diferencas.csv", index=False, lineterminator="\n")
    print(json.dumps(res, indent=1))


def main():
    F3.mkdir(parents=True, exist_ok=True)
    df = ds2_com_splits().set_index("id")
    ids = amostra(df.reset_index())
    assert len(ids) == N_AMOSTRA and len(set(ids)) == N_AMOSTRA and (df.loc[ids, "split_grupo"] == "holdout").all()
    texto, cat = df["Document"], df["Topic_group"]
    arq_t = F3 / "q2_tempos.json"
    tempos = json.loads(arq_t.read_text(encoding="utf-8")) if arq_t.exists() else {}
    pendentes = preparar_retomada(ARQ_VIZ, ids)
    n_ini = N_AMOSTRA - len(pendentes)
    print(f"retomada: {n_ini} de {N_AMOSTRA} já feitos; faltam {len(pendentes)}", flush=True)

    vs = vector_store()
    t0 = time.perf_counter()
    for k in range(0, len(pendentes), N_LOTE):
        lote = pendentes[k:k + N_LOTE]
        vetores = embeddings().embed_documents(texto.loc[lote].astype(str).tolist())
        vet = {i: [(int(d.metadata["id"]), d.metadata["categoria"], r)
                   for r, d in enumerate(vs.similarity_search_by_vector(v, k=50), 1)] for i, v in zip(lote, vetores)}
        fts = fulltext_paralelo(lote, texto)
        linhas = [(i, "vetorial", r, j, c) for i in lote for j, c, r in vet[i]]
        linhas += [(i, "fulltext", r, j, c) for i in lote for j, c, r in fts[i]]
        viz = com_hibrida(pd.DataFrame(linhas, columns=["id_consulta", "recuperador", "rank", "id_vizinho",
                                                        "categoria_vizinho"]))
        assert (df.loc[viz["id_vizinho"], "split_grupo"] == "treino").all()
        assert (df.loc[viz["id_vizinho"], "group_id"].values != df.loc[viz["id_consulta"], "group_id"].values).all()
        anexar(ARQ_VIZ, viz)  # o lote só é gravado inteiro, depois dos asserts
        feitos, dec = n_ini + k + len(lote), time.perf_counter() - t0
        resta = dec / (k + len(lote)) * (len(pendentes) - k - len(lote))
        print(f"{feitos}/{N_AMOSTRA} feitos | decorrido {dec / 60:.1f} min | restante extrapolado {resta / 60:.1f} min",
              flush=True)
    if pendentes:
        tempos.setdefault("execucoes_f3b", []).append({"threads": N_THREADS, "consultas": len(pendentes),
                                                       "parede_s": round(time.perf_counter() - t0, 1)})
        arq_t.write_text(json.dumps(tempos, indent=2), encoding="utf-8", newline="\n")

    viz = ler_concluidos(ARQ_VIZ)
    if set(viz["id_consulta"]) != set(ids):
        raise SystemExit(f"incompleto: {viz['id_consulta'].nunique()} de {N_AMOSTRA}; rode de novo para retomar")
    res = {"amostra_q2": metricas(viz, cat, ids), "recorte_400": recorte_400(cat), "tempos": tempos}
    (F3 / "q2_recuperacao.json").write_text(json.dumps(res, indent=2), encoding="utf-8", newline="\n")
    pd.DataFrame([{"universo": u, **d} for u in ("amostra_q2", "recorte_400") for d in res[u]["diferencas"]]).to_csv(
        F3 / "q2_diferencas.csv", index=False, lineterminator="\n")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    so_400() if "--so-400" in sys.argv else main()
