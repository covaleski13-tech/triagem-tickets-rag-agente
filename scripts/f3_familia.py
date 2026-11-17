"""F3 passo 3: família pré-registrada de Q1 (McNemar exato + Holm sobre 4 comparações) e veredictos da F0 §2."""
import json
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from triagem_rag.dados import ids_amostra_400  # noqa: E402
from triagem_rag.metricas import (FALHA, familia, macro_f1, matriz_confusao, mcnemar_exato, veredictos,  # noqa: E402
                                  wilson)

F2, F3 = RAIZ / "results/f2", RAIZ / "results/f3"
PRECO_IN, PRECO_OUT = 0.10, 0.50  # US$/MTok, docs/custos.md
LOGS = {"v0": F2, "v1": F2, "v2": F3, "v3": F3}


def main():
    ids = ids_amostra_400()
    p = pd.read_csv(F2 / "predicoes_400.csv", keep_default_na=False).set_index("id").loc[ids]
    for v in ("v2", "v3"):
        p[v] = pd.read_csv(F3 / f"pred_{v}.csv", keep_default_na=False).set_index("id").loc[ids, "pred"].replace("", FALHA)
    p = p.reset_index()[["id", "rotulo", "v0", "v1", "v2", "v3", "k1", "c", "v0_caso"]]
    p.to_csv(F3 / "predicoes_400.csv", index=False, lineterminator="\n")

    res = {"n": len(ids), "variantes": {}}
    for v in ("v0", "v1", "v2", "v3", "k1", "c"):
        ac = int((p[v] == p["rotulo"]).sum())
        r = {"acertos": ac, "acuracia": round(ac / len(ids), 4), "wilson95": [round(x, 4) for x in wilson(ac, len(ids))],
             "macro_f1": round(macro_f1(p["rotulo"], p[v]), 4), "matriz_confusao": matriz_confusao(p["rotulo"], p[v]),
             "falhas": int((p[v] == FALHA).sum()), "mais_prevista": list(Counter(p[v]).most_common(1)[0])}
        if v in LOGS:
            log = pd.read_json(LOGS[v] / f"llm_log_{v}.jsonl", lines=True)
            lat = log["latencia_ms"].dropna()
            custo = (log["tokens_entrada"].sum() * PRECO_IN + log["tokens_saida"].sum() * PRECO_OUT) / 1e6
            r.update(chamadas=len(log), invalidas_primeira_tentativa=int((log[log.tentativa == 1].valida == "n").sum()),
                     erros_api=int(log["erros_api"].sum()), tokens_entrada_medio=round(float(log.tokens_entrada.mean()), 1),
                     tokens_saida_medio=round(float(log.tokens_saida.mean()), 1), custo_usd=round(custo, 6),
                     custo_por_1000_tickets_usd=round(custo / len(ids) * 1000, 4),
                     latencia_p50_ms=round(float(np.percentile(lat, 50)), 1),
                     latencia_p95_ms=round(float(np.percentile(lat, 95)), 1))
        res["variantes"][v] = r

    acertos = {v: (p[v] == p["rotulo"]).values for v in ("v0", "v1", "v2", "v3", "k1", "c")}
    fam = pd.DataFrame(familia(acertos))
    fam.to_csv(F3 / "familia_q1.csv", index=False, lineterminator="\n")
    ver = veredictos(pd.read_csv(F3 / "familia_q1.csv"))
    (F3 / "veredictos.json").write_text(json.dumps(ver, indent=2), encoding="utf-8", newline="\n")

    rot = "exploratório, fora da família pré-registrada; sem Holm"
    res["exploratorias"] = {f"{a}_x_{b}": {**mcnemar_exato(acertos[a], acertos[b]), "rotulo": rot}
                            for a, b in (("v2", "v1"), ("v2", "k1"), ("v2", "c"), ("v3", "v0"))}
    res["custo_f3_usd"] = round(res["variantes"]["v2"]["custo_usd"] + res["variantes"]["v3"]["custo_usd"], 6)
    (F3 / "metricas_f3.json").write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")

    print(fam.to_string())
    print(json.dumps(ver))
    print(json.dumps({v: {k: r.get(k) for k in ("acertos", "acuracia", "wilson95", "macro_f1", "falhas", "mais_prevista",
                                                 "custo_por_1000_tickets_usd", "latencia_p50_ms", "latencia_p95_ms")}
                      for v, r in res["variantes"].items()}, ensure_ascii=False))
    print(json.dumps(res["exploratorias"]), res["custo_f3_usd"])


if __name__ == "__main__":
    main()
