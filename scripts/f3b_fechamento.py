"""F3b: fecha a Q2 na amostra de 2.000. Reorganiza o bloco de tempos de q2_recuperacao.json (sondas como histórico)
e acrescenta, como exploratório, a acurácia do clássico nos mesmos 2.000 ids ao lado do K1 de cada recuperador.
Não muda nenhuma métrica já calculada nem o recorte dos 400."""
import json
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
from triagem_rag.dados import DATA_DIR, ds2_com_splits  # noqa: E402
from triagem_rag.metricas import wilson  # noqa: E402

F3 = RAIZ / "results/f3"


def main():
    arq = F3 / "q2_recuperacao.json"
    res = json.loads(arq.read_text(encoding="utf-8"))
    t = res["tempos"]
    execs = t["execucoes_f3b"]
    assert len(execs) == 1 and execs[0]["threads"] == 4 and execs[0]["consultas"] == 2000
    res["tempos"] = {
        "status": "concluído",
        "execucao": {"threads": 4, "consultas": 2000, "parede_s": execs[0]["parede_s"],
                     "nota": "a F4 rodou ao mesmo tempo no mesmo Postgres (testes db e fumaça do agente); "
                             "a parede inclui essa concorrência"},
        "shared_buffers": t["shared_buffers"],
        "sondas_historico": [
            {**t["rodada_anterior"], "threads": 4, "limite_min": 30.0},
            {k: t[k] for k in ("threads", "limite_min", "vetorial_s", "sonda_fulltext_s", "extrapolacao_total_min",
                               "status")},
        ],
    }

    ids = pd.read_csv(F3 / "amostra_q2_ids.csv")["id"].tolist()
    probs = pd.read_csv(DATA_DIR / "caso/f3_probs_holdout_grupo.csv").set_index("id")
    rot = ds2_com_splits().set_index("id").loc[ids, "Topic_group"]
    assert (probs.loc[ids, "rotulo"].values == rot.values).all()
    ac = int((probs.loc[ids, "pred"].values == rot.values).sum())
    res["exploratorio_classico_vs_k1_amostra"] = {
        "rotulo": "exploratório, fora do pré-registro de Q2; sem teste",
        "n": len(ids),
        "classico": {"acertos": ac, "acuracia": round(ac / len(ids), 4),
                     "wilson95": [round(x, 4) for x in wilson(ac, len(ids))]},
        "k1": {r: {k: v for k, v in m.items() if k.startswith("k1_")}
               for r, m in res["amostra_q2"]["por_recuperador"].items()},
    }
    arq.write_text(json.dumps(res, indent=2, ensure_ascii=False), encoding="utf-8", newline="\n")
    print(json.dumps({k: res[k] for k in ("tempos", "exploratorio_classico_vs_k1_amostra")}, indent=1,
                     ensure_ascii=False))


if __name__ == "__main__":
    main()
