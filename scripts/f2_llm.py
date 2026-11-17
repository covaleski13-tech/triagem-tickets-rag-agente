"""F2 passos 1, 6 e 7: V0 (prompt do case) e V1 (5 exemplos aleatórios do treino) nos 400.
Uso: python scripts/f2_llm.py --variante v0|v1 [--estimar]"""
import argparse
import hashlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from triagem_rag.dados import ds2_com_splits, ids_amostra_400  # noqa: E402
from triagem_rag.llm import (MODELO, checar_tracing, classificar, cliente, mensagens, sortear_v1,  # noqa: E402
                             system_rag, system_v0)

OUT = RAIZ / "results/f2"
PRECO_IN, PRECO_OUT = 0.10, 0.50  # US$/MTok, página oficial consultada em 2026-11-17 (docs/custos.md)


def preparar(variante: str):
    df = ds2_com_splits()
    treino = df[df["split_grupo"] == "treino"]
    texto = df.set_index("id")["Document"]
    ids = ids_amostra_400()
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {"variante": variante, "modelo": MODELO}
    if variante == "v0":
        system, ex = system_v0(treino)
        cat = df.set_index("id")["Topic_group"]
        assert all(df.set_index("id").loc[i, "split_grupo"] == "treino" and cat[i] == c for c, i in ex)
        pd.DataFrame(ex, columns=["categoria", "id_exemplo"]).to_csv(OUT / "exemplos_v0.csv", index=False,
                                                                      lineterminator="\n")
        meta["sha256_system"] = hashlib.sha256(system.encode("utf-8")).hexdigest()
        systems = {i: system for i in ids}
    else:
        ids_treino = np.sort(treino["id"].to_numpy())
        cat = treino.set_index("id")["Topic_group"]
        linhas, systems = [], {}
        for i in ids:
            sel = sortear_v1(i, ids_treino)
            assert len(set(sel)) == 5 and i not in sel
            linhas += [(i, o, j, cat[j]) for o, j in enumerate(sel, 1)]
            systems[i] = system_rag([(texto[j], cat[j]) for j in sel])
        ex = pd.DataFrame(linhas, columns=["id", "ordem", "id_exemplo", "categoria_exemplo"])
        sp = df.set_index("id")["split_grupo"]
        assert (sp.loc[ex["id_exemplo"]] == "treino").all() and (ex.groupby("id").size() == 5).all()
        ex.to_csv(OUT / "exemplos_v1.csv", index=False, lineterminator="\n")
    return ids, texto, systems, meta


def estimar(variante: str):
    ids, texto, systems, _ = preparar(variante)
    llm = cliente()
    amostra = ids[:5]
    toks = [llm.get_num_tokens_from_messages(mensagens(systems[i], texto[i])) for i in amostra]
    media = float(np.mean(toks))
    custo = 400 * 1.05 * (media * PRECO_IN + 64 * PRECO_OUT) / 1e6
    out = {"variante": variante, "ids": amostra, "tokens_entrada": toks, "media_entrada": media,
           "premissa_saida_tokens": 64, "chamadas": 420, "estimativa_usd": round(custo, 4)}
    print(json.dumps(out))
    return out


def rodar(variante: str):
    checar_tracing()
    ids, texto, systems, meta = preparar(variante)
    llm = cliente()
    t0 = time.perf_counter()
    with ThreadPoolExecutor(8) as ex:
        res = list(ex.map(lambda i: classificar(llm, systems[i], i, texto[i]), ids))
    meta["duracao_s"] = round(time.perf_counter() - t0, 1)
    with open(OUT / f"llm_log_{variante}.jsonl", "w", encoding="utf-8", newline="\n") as f:
        for tentativas, _ in res:
            for t in tentativas:  # só a saída do LLM; o texto do ticket não entra no log
                f.write(json.dumps({"id": t["id"], "variante": variante, "tentativa": t["tentativa"],
                                    "latencia_ms": t["lat_ms"], "tokens_entrada": t["in"], "tokens_saida": t["out"],
                                    "resposta_bruta": t["bruto"], "valida": t["valida"],
                                    "erros_api": t["erros_api"]}, ensure_ascii=False) + "\n")
    pd.DataFrame({"id": ids, "pred": [p for _, p in res]}).to_csv(OUT / f"pred_{variante}.csv", index=False,
                                                                   lineterminator="\n")
    chamadas = [t for ts, _ in res for t in ts]
    meta.update(chamadas=len(chamadas), tokens_entrada=sum(t["in"] for t in chamadas),
                tokens_saida=sum(t["out"] for t in chamadas))
    meta["custo_usd"] = round((meta["tokens_entrada"] * PRECO_IN + meta["tokens_saida"] * PRECO_OUT) / 1e6, 6)
    rot = ds2_com_splits().set_index("id").loc[ids, "Topic_group"].values
    meta["acertos"] = int(sum(p == r for (_, p), r in zip(res, rot)))
    meta["acuracia"] = meta["acertos"] / 400
    (OUT / f"llm_meta_{variante}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8", newline="\n")
    print(json.dumps(meta))
    if variante == "v0" and not 0.2225 <= meta["acuracia"] <= 0.31:
        raise SystemExit(f"PORTÃO: V0 = {meta['acuracia']:.2%} fora de [22,25%; 31,0%]. Pare antes de V1.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--variante", choices=["v0", "v1"], required=True)
    ap.add_argument("--estimar", action="store_true")
    a = ap.parse_args()
    estimar(a.variante) if a.estimar else rodar(a.variante)
