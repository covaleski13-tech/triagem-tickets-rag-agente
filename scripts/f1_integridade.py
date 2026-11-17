"""F1 passo 4: integridade do DS2 e dos splits + reprodução do classificador clássico do case."""
import hashlib
import json
import sys
import time
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "src/triagem_rag/caso"))  # triagem.py do case importa `comum` sem pacote
from triagem import PARAMS  # noqa: E402
from triagem_rag.dados import DATA_DIR, DS2_ARQUIVO, SEED, ids_amostra_400, ler_ds2, ler_splits  # noqa: E402


def main():
    bruto = DATA_DIR / "raw" / DS2_ARQUIVO
    out = {"sha256_csv_bruto": hashlib.sha256(bruto.read_bytes()).hexdigest()}
    ds2, sp = ler_ds2(), ler_splits()
    out.update(linhas_csv=len(ds2), linhas_splits=len(sp))
    assert len(ds2) == 47837 and len(sp) == 47837
    assert list(sp.columns) == ["id", "group_id", "split_grupo", "split_aleatorio"]
    assert sp["id"].is_unique
    df = ds2.merge(sp, on="id", validate="1:1")
    assert len(df) == 47837

    cont = df["split_grupo"].value_counts().to_dict()
    out["split_grupo"] = cont
    assert cont == {"treino": 38270, "holdout": 9567}, cont
    g_tr = set(df.loc[df.split_grupo == "treino", "group_id"])
    g_ho = set(df.loc[df.split_grupo == "holdout", "group_id"])
    out["grupos_cruzados"] = len(g_tr & g_ho)
    assert not (g_tr & g_ho)

    # receita do case (triagem._treinar): só treino
    tr, ho = df[df.split_grupo == "treino"], df[df.split_grupo == "holdout"]
    t0 = time.perf_counter()
    m = make_pipeline(TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True),
                      LogisticRegression(max_iter=2000, random_state=SEED)).fit(tr["Document"], tr["Topic_group"])
    out["treino_s"] = round(time.perf_counter() - t0, 1)

    pred_ho = m.predict(ho["Document"])
    acertos_ho = int((pred_ho == ho["Topic_group"].values).sum())
    out["acc_holdout"] = {"acertos": acertos_ho, "n": len(ho), "pct": round(100 * acertos_ho / len(ho), 4)}
    assert abs(100 * acertos_ho / len(ho) - 85.07) <= 0.05, out["acc_holdout"]

    ids400 = ids_amostra_400()
    am = df.set_index("id").loc[ids400]
    acertos_400 = int((m.predict(am["Document"]) == am["Topic_group"].values).sum())
    out["acc_400"] = {"acertos": acertos_400, "n": 400, "pct": round(100 * acertos_400 / 400, 2)}
    assert acertos_400 == 278, out["acc_400"]

    # concordância com as predições salvas pelo case no holdout (mesmo modelo => esperado 100%)
    caso = pd.read_csv(DATA_DIR / "caso/f3_probs_holdout_grupo.csv").set_index("id").loc[ho["id"], "pred"].values
    out["concordancia_pred_caso_holdout_pct"] = round(100 * float((caso == pred_ho).mean()), 4)

    # mesmo nome de arquivo do case: hash do f1_splits.csv + parâmetros
    h_splits = hashlib.sha256((DATA_DIR / "f1_splits.csv").read_bytes()).hexdigest()
    versao = hashlib.sha256((h_splits + PARAMS).encode()).hexdigest()[:12]
    arq = DATA_DIR / "modelos" / f"modelo_{versao}.joblib"
    arq.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump({"pipeline": m, "versao": versao, "treino_s": out["treino_s"]}, arq)
    out["modelo"] = arq.relative_to(RAIZ).as_posix()

    (RAIZ / "results/f1").mkdir(parents=True, exist_ok=True)
    (RAIZ / "results/f1/integridade.json").write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
