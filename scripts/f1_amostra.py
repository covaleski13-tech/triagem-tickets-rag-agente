"""F1 passo 3: deriva a amostra dos 400 e as predições V0 do case a partir do f3_llm_log.jsonl (sem copiar o log)."""
import json
import os
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
CASE = Path(os.environ.get("CASE_DIR", r"C:\Users\gusta\challenge-g4-ai-master"))
LOG = CASE / "planning" / "F3" / "f3_llm_log.jsonl"
sys.path.insert(0, str(RAIZ / "src"))
from triagem_rag.dados import CATEGORIAS, ler_ds2  # noqa: E402


def validar(texto):
    # mesma regra do f3_llm.py do case: o texto inteiro é o objeto JSON, com categoria da lista
    try:
        obj = json.loads(str(texto).strip())
    except (json.JSONDecodeError, TypeError):
        return None
    return obj["categoria"] if isinstance(obj, dict) and obj.get("categoria") in CATEGORIAS else None


def main():
    linhas = [json.loads(l) for l in LOG.read_text(encoding="utf-8").splitlines() if l.strip()]
    ids = pd.Series([int(l["id"]) for l in linhas])
    print("linhas no log:", len(linhas), "| ids únicos:", ids.nunique())
    assert len(linhas) == 401 and ids.nunique() == 400

    repetidos = ids[ids.duplicated()].unique().tolist()
    for r in repetidos:
        print("id repetido:", r, [(l["valida"], l["tokens_saida"]) for l in linhas if int(l["id"]) == r])

    ordem = list(dict.fromkeys(ids))
    pd.DataFrame({"id": ordem}).to_csv(RAIZ / "data/amostra_400_ids.csv", index=False, lineterminator="\n")

    ultima = {int(l["id"]): l for l in linhas}  # dict mantém a última linha de cada id
    pred = pd.DataFrame([{"id": i, "pred_caso": validar(ultima[i]["resposta_bruta"]) or "",
                          "valida": ultima[i]["valida"]} for i in ordem])
    assert ((pred["pred_caso"] != "") == (pred["valida"] == "s")).all(), "validação diverge do campo valida do log"
    pred.to_csv(RAIZ / "data/caso/f3_v0_pred.csv", index=False, lineterminator="\n")

    splits = pd.read_csv(RAIZ / "data/f1_splits.csv").set_index("id")
    assert (splits.loc[ordem, "split_grupo"] == "holdout").all()
    probs = pd.read_csv(RAIZ / "data/caso/f3_probs_holdout_grupo.csv").set_index("id")
    assert (probs.loc[ordem, "p_max"] < 0.74).all()

    rot = ler_ds2().set_index("id").loc[ordem, "Topic_group"].values
    acertos = int((pred["pred_caso"].values == rot).sum())
    print(f"acurácia pred_caso: {acertos}/400 = {acertos / 400:.2%} | inválidas finais: {(pred['valida'] != 's').sum()}")
    assert acertos == 106, "não reproduz os 26,5% do case"


if __name__ == "__main__":
    main()
