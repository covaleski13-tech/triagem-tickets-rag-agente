import os
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
DATA_DIR = (RAIZ / os.environ.get("DATA_DIR", "data")).resolve()
DS2_ARQUIVO = "all_tickets_processed_improved_v3.csv"
SEED = 42
CATEGORIAS = ["Access", "Administrative rights", "HR Support", "Hardware", "Internal Project",
              "Miscellaneous", "Purchase", "Storage"]


def ler_ds2() -> pd.DataFrame:
    # mesma convenção do case (comum.ler_ds2): id = índice da linha no CSV bruto, base 0
    df = pd.read_csv(DATA_DIR / "raw" / DS2_ARQUIVO)
    df.insert(0, "id", range(len(df)))
    return df


def ler_splits() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "f1_splits.csv")


def ds2_com_splits() -> pd.DataFrame:
    return ler_ds2().merge(ler_splits(), on="id", validate="1:1")


def treino() -> pd.DataFrame:
    df = ds2_com_splits()
    return df[df["split_grupo"] == "treino"].reset_index(drop=True)


def ids_amostra_400() -> list[int]:
    return pd.read_csv(DATA_DIR / "amostra_400_ids.csv")["id"].tolist()
