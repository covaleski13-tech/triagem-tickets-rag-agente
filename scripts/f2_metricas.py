"""F2 passo 8: consolida V0, V1, K1, C (e V0 do case) nos 400. Comparações McNemar exploratórias, sem Holm."""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from triagem_rag.dados import DATA_DIR, ds2_com_splits, ids_amostra_400  # noqa: E402
from triagem_rag.metricas import FALHA, macro_f1, matriz_confusao, mcnemar_exato, wilson  # noqa: E402

OUT = RAIZ / "results/f2"
PRECO_IN, PRECO_OUT = 0.10, 0.50  # US$/MTok, docs/custos.md


def ler_pred(arq, col):
    return pd.read_csv(arq, keep_default_na=False).set_index("id")[col].replace("", FALHA)


def main():
    ids = ids_amostra_400()
    rot = ds2_com_splits().set_index("id").loc[ids, "Topic_group"]
    k1c = pd.read_csv(OUT / "pred_k1_c.csv").set_index("id")
    pred = pd.DataFrame({
        "id": ids, "rotulo": rot.values,
        "v0": ler_pred(OUT / "pred_v0.csv", "pred").loc[ids].values,
        "v1": ler_pred(OUT / "pred_v1.csv", "pred").loc[ids].values,
        "k1": k1c.loc[ids, "k1"].values, "c": k1c.loc[ids, "c"].values,
        "v0_caso": ler_pred(DATA_DIR / "caso/f3_v0_pred.csv", "pred_caso").loc[ids].values,
    })
    pred.to_csv(OUT / "predicoes_400.csv", index=False, lineterminator="\n")

    res = {"n": len(ids), "variantes": {}, "comparacoes_exploratorias": {}}
    for v in ("v0", "v1", "k1", "c", "v0_caso"):
        acertos = int((pred[v] == pred["rotulo"]).sum())
        r = {"n": len(ids), "acertos": acertos, "acuracia": round(acertos / len(ids), 4),
             "wilson95": [round(x, 4) for x in wilson(acertos, len(ids))],
             "macro_f1": round(macro_f1(pred["rotulo"], pred[v]), 4),
             "matriz_confusao": matriz_confusao(pred["rotulo"], pred[v]),
             "falhas": int((pred[v] == FALHA).sum()),
             "mais_prevista": Counter(pred[v]).most_common(1)[0]}
        if v in ("v0", "v1"):
            log = pd.read_json(OUT / f"llm_log_{v}.jsonl", lines=True)
            meta = json.loads((OUT / f"llm_meta_{v}.json").read_text(encoding="utf-8"))
            prim = log[log["tentativa"] == 1]
            lat = log["latencia_ms"].dropna()
            custo = (log["tokens_entrada"].sum() * PRECO_IN + log["tokens_saida"].sum() * PRECO_OUT) / 1e6
            r.update(invalidas_primeira_tentativa=int((prim["valida"] == "n").sum()),
                     erros_api=int(log["erros_api"].sum()), chamadas=len(log),
                     chamadas_por_ticket=round(len(log) / len(ids), 4),
                     tokens_entrada_medio=round(float(log["tokens_entrada"].mean()), 1),
                     tokens_saida_medio=round(float(log["tokens_saida"].mean()), 1),
                     custo_usd=round(custo, 6), custo_por_1000_tickets_usd=round(custo / len(ids) * 1000, 4),
                     latencia_p50_ms=round(float(np.percentile(lat, 50)), 1),
                     latencia_p95_ms=round(float(np.percentile(lat, 95)), 1),
                     duracao_rodada_s=meta.get("duracao_s"))
            if "sha256_system" in meta:
                r["sha256_system"] = meta["sha256_system"]
        res["variantes"][v] = r

    ac = {v: (pred[v] == pred["rotulo"]).values for v in ("v0", "v1", "k1", "c", "v0_caso")}
    rotulo = "exploratório, fora da família pré-registrada; sem Holm"
    for a, b in (("v0", "v0_caso"), ("v1", "v0"), ("k1", "c"), ("v1", "c")):
        m = mcnemar_exato(ac[a], ac[b])
        res["comparacoes_exploratorias"][f"{a}_x_{b}"] = {**m, "rotulo": rotulo,
                                                          "acertos_a": int(ac[a].sum()), "acertos_b": int(ac[b].sum())}
    res["v0_mesma_predicao_que_caso_pct"] = round(100 * float((pred["v0"] == pred["v0_caso"]).mean()), 2)
    res["custo_total_f2_usd"] = round(sum(res["variantes"][v]["custo_usd"] for v in ("v0", "v1")), 6)
    (OUT / "metricas_f2.json").write_text(json.dumps(res, indent=2, ensure_ascii=False, default=str),
                                          encoding="utf-8", newline="\n")
    resumo = {v: {k: r[k] for k in ("acertos", "acuracia", "wilson95", "macro_f1", "falhas", "mais_prevista")}
              for v, r in res["variantes"].items()}
    print(json.dumps({"resumo": resumo, "comparacoes": res["comparacoes_exploratorias"],
                      "v0_mesma_predicao_que_caso_pct": res["v0_mesma_predicao_que_caso_pct"],
                      "custo_total_f2_usd": res["custo_total_f2_usd"]}, indent=1, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()
