"""F1 passo 10: sanidade dos recuperadores nos 400 (sem LLM). Não calcula precisão de rótulo nem K1 (isso é F3)."""
import json
import sys
import time
from pathlib import Path

import numpy as np
import psycopg

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from triagem_rag.dados import ds2_com_splits, ids_amostra_400  # noqa: E402
from triagem_rag.recuperacao import (buscar_fulltext, buscar_hibrida, buscar_vetorial, pg_dsn_psycopg)  # noqa: E402


def main():
    df = ds2_com_splits().set_index("id")
    textos = df.loc[ids_amostra_400(), "Document"].astype(str).tolist()
    buscar_vetorial(textos[0])  # aquecimento: carrega o modelo e abre a conexão; fora da medida
    lat = {"vetorial": [], "fulltext": [], "hibrida": []}
    zeros = 0
    with psycopg.connect(pg_dsn_psycopg()) as con:
        for t in textos:
            t0 = time.perf_counter(); buscar_vetorial(t); lat["vetorial"].append(time.perf_counter() - t0)
            t0 = time.perf_counter(); r = buscar_fulltext(t, con=con); lat["fulltext"].append(time.perf_counter() - t0)
            zeros += not r
            t0 = time.perf_counter(); buscar_hibrida(t, con=con); lat["hibrida"].append(time.perf_counter() - t0)
    out = {"n": len(textos), "fulltext_zero_resultados": zeros,
           "fulltext_zero_resultados_pct": round(100 * zeros / len(textos), 2),
           "latencia_p50_ms": {k: round(1000 * float(np.median(v)), 1) for k, v in lat.items()},
           "obs": "n=50 candidatos; conexão psycopg reaproveitada no full-text; CPU local; 1 passada sequencial"}
    (RAIZ / "results/f1/sanidade_400.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
