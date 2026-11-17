import json

import numpy as np
import pandas as pd
import pytest

from triagem_rag.dados import CATEGORIAS, DATA_DIR, RAIZ, ler_splits
from triagem_rag.esquema import validar
from triagem_rag.llm import PROMPT_RAG, PROMPT_V0, cliente, mensagens, sortear_v1
from triagem_rag.metricas import holm, macro_f1, matriz_confusao, mcnemar_exato, wilson
from triagem_rag.recuperacao import voto_k1


def validar_caso(texto: str):
    # cópia literal de validar() do f3_llm.py do case (PR #228, commit 3a880f2), para o teste de paridade
    try:
        obj = json.loads(texto.strip())
    except (json.JSONDecodeError, AttributeError):
        return None
    if not isinstance(obj, dict) or obj.get("categoria") not in CATEGORIAS:
        return None
    c = obj.get("confianca")
    if not isinstance(c, (int, float)) or isinstance(c, bool) or not 0 <= c <= 1:
        return None
    return obj


def test_payload_llm():
    p = cliente(api_key="sem-rede")._get_request_payload(mensagens("SYSTEM", "printer jam"))
    assert p["model"] == "claude-haiku-5-5"
    assert p["max_tokens"] == 64
    assert p["thinking"] == {"type": "disabled"}
    assert p["output_config"] == {"effort": "low"}
    for k in ("temperature", "top_p", "top_k"):
        assert k not in p
    assert p["system"] == "SYSTEM"
    assert p["messages"] == [{"role": "user", "content": "<ticket>printer jam</ticket>"}]


CASOS_VALIDAR = [
    '{"categoria": "Access", "confianca": 0.9}',
    '{"categoria": "Access", "confianca": 1}',
    '{"categoria": "Access", "confianca": true}',
    '{"categoria": "Access", "confianca": 1.5}',
    '{"categoria": "Access", "confianca": -0.1}',
    '{"categoria": "Access", "confianca": "0.9"}',
    '{"categoria": "Printer", "confianca": 0.9}',
    '{"categoria": "access", "confianca": 0.9}',
    'Answer: {"categoria": "Access", "confianca": 0.9}',
    '```json\n{"categoria": "Access", "confianca": 0.9}\n```',
    '{"categoria": "Access", "confianca": 0.9, "extra": 1}',
    '',
    '{"categoria": "Administrative rights", "confianca": 0.0}\n\nWait, let me',
    '{"categoria": "Hardware", "confianca": 0.6',
    '  {"categoria": "Storage", "confianca": 0}  ',
    '["Access", 0.9]',
    '{"confianca": 0.9}',
]


@pytest.mark.parametrize("texto", CASOS_VALIDAR)
def test_validar_paridade(texto):
    novo, caso = validar(texto), validar_caso(texto)
    assert (novo is None) == (caso is None)
    if novo is not None:
        assert novo.categoria == caso["categoria"] and novo.confianca == caso["confianca"]


def test_wilson():
    assert [round(v, 4) for v in wilson(106, 400)] == [0.2241, 0.3103]
    assert [round(v, 4) for v in wilson(278, 400)] == [0.6482, 0.7381]
    assert [round(v, 4) for v in wilson(0, 10)] == [0.0, 0.2775]


def test_mcnemar():
    a = [True] * 2 + [False] * 10 + [True] * 5
    b = [False] * 2 + [True] * 10 + [True] * 5
    r = mcnemar_exato(a, b)
    assert (r["b"], r["c"]) == (2, 10) and round(r["p"], 6) == 0.038574
    assert mcnemar_exato([True, False], [True, False])["p"] == 1.0


def test_holm():
    assert [round(v, 10) for v in holm([0.01, 0.04, 0.03, 0.2])] == [0.04, 0.09, 0.09, 0.2]


def test_matriz_e_macro_f1_com_falha():
    y = ["Access", "Access", "Hardware"]
    p = ["Access", "falha", "Hardware"]
    m = matriz_confusao(y, p)
    assert len(m) == 8 and len(m[0]) == 9
    assert m[0][0] == 1 and m[0][8] == 1 and m[3][3] == 1
    # Access: P=1, R=0,5 -> F1=2/3; Hardware: F1=1; demais 6 categorias sem suporte nem predição -> 0
    assert macro_f1(y, p) == pytest.approx((2 / 3 + 1) / 8)


def test_k1_empate():
    # 2 x Access, 2 x Hardware, 1 x Storage: empate entre Access e Hardware; Hardware tem o rank 1
    assert voto_k1(["Hardware", "Access", "Storage", "Access", "Hardware"]) == "Hardware"
    assert voto_k1(["Storage", "Access", "Access", "Hardware", "Hardware"]) == "Access"
    assert voto_k1(["Purchase", "Access", "Access", "Access", "Storage"]) == "Access"


def test_template_rag():
    a = PROMPT_V0.read_text(encoding="utf-8").splitlines()
    b = PROMPT_RAG.read_text(encoding="utf-8").splitlines()
    assert len(a) == len(b)
    dif = [(x, y) for x, y in zip(a, b) if x != y]
    assert dif == [("Labeled examples (one per category):", "Labeled examples from the training set:")]


def test_exemplos_v1():
    arq = RAIZ / "results/f2/exemplos_v1.csv"
    if not arq.exists():
        pytest.skip("results/f2/exemplos_v1.csv ainda não gerado")
    ex = pd.read_csv(arq)
    sp = ler_splits().set_index("id")
    assert (ex.groupby("id").size() == 5).all() and ex["id"].nunique() == 400
    assert (ex.groupby("id")["id_exemplo"].nunique() == 5).all()
    assert (sp.loc[ex["id_exemplo"], "split_grupo"] == "treino").all()
    assert (ex["id"] != ex["id_exemplo"]).all()
    ids_treino = np.sort(sp.index[sp["split_grupo"] == "treino"].to_numpy())
    for i, g in list(ex.groupby("id", sort=False))[:20]:
        assert sortear_v1(i, ids_treino) == g.sort_values("ordem")["id_exemplo"].tolist()


@pytest.mark.api
def test_fumaca_api():
    # chamada real (custo ~US$ 0,0002); fora da execução padrão
    from triagem_rag.llm import checar_tracing, classificar, cliente
    checar_tracing()
    tentativas, pred = classificar(cliente(), "Reply with {\"categoria\": \"Hardware\", \"confianca\": 1}.", 0,
                                   "printer broken")
    assert tentativas[0]["bruto"] is not None and pred in CATEGORIAS + ["falha"]
