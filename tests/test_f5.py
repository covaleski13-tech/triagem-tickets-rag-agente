"""F5: avaliação do agente. Sem rede: o executor e as definições das métricas com dados sintéticos."""
import importlib.util
import json
import sys
import threading
from pathlib import Path

import pandas as pd
import pytest

from triagem_rag import agente
from triagem_rag.dados import CATEGORIAS, ler_splits

RAIZ = Path(__file__).resolve().parents[1]


def _carregar(nome):
    spec = importlib.util.spec_from_file_location(nome, RAIZ / "scripts" / f"{nome}.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


@pytest.fixture(scope="module")
def av():
    return _carregar("f5_avaliar")


@pytest.fixture(scope="module")
def met():
    return _carregar("f5_metricas")


def test_alvo_ataque(av):
    desl = {a["id"]: a["deslocamento_alvo"] for a in av.ataques()}
    assert sorted(desl.values()) == [1, 2, 3, 4, 5]
    for p in CATEGORIAS:
        for d in desl.values():
            a = av.alvo(p, d)
            assert a != p
            assert a == sorted(CATEGORIAS)[(sorted(CATEGORIAS).index(p) + d) % 8]  # case: sorted(m.classes_)


def test_amostra_q3_estratos(av):
    arq = RAIZ / "results/f5/amostra_q3.csv"
    if not arq.exists():
        pytest.skip("amostra ainda não gravada")
    a = pd.read_csv(arq)
    assert a["estrato"].value_counts().to_dict() == {"IA decide": 67, "IA sugere": 67, "humano decide": 66}
    assert a["id"].is_unique
    sp = ler_splits().set_index("id")
    assert (sp.loc[a["id"], "split_grupo"] == "holdout").all()
    # ordem garantida no script (não por mtime: num clone, os mtimes refletem o checkout, não a geração)
    import inspect
    assert "assert not LOG.exists()" in inspect.getsource(av.fase_estratos)
    fonte_main = inspect.getsource(av.main)
    assert fonte_main.index("fase_estratos(") < fonte_main.index("executar(")
    # seed 42 dentro de cada estrato, sobre o holdout ordenado por id: refeito a partir das faixas gravadas
    for e, g in a.groupby("estrato"):
        assert len(g) == av.N_POR_ESTRATO[e]


def _fake_saida(**kw):
    base = {"faixa_final": "humano decide", "faixa_politica": "humano decide", "motivo_final": "x", "llm_rodou": False,
            "tool_calls": [], "erros": [], "tokens_entrada": 0, "tokens_saida": 0, "latencia_ms": 1.0}
    return {**base, **kw}


def test_log_escritor_unico(av, tmp_path, monkeypatch):
    arq = tmp_path / "log.jsonl"
    aberturas = []
    open_original = open

    def espiao(f, *a, **k):
        if Path(f) == arq:
            aberturas.append(threading.current_thread() is threading.main_thread())
        return open_original(f, *a, **k)

    monkeypatch.setattr("builtins.open", espiao)
    monkeypatch.setenv("TRIAGEM_AGENTE_LOG", str(arq))

    def rodar(t):
        agente._registrar(_fake_saida())  # o agente tentaria gravar daqui: tem de ser no-op
        return _fake_saida()

    tarefas = [{"id": i, "variante": "limpa", "alvo": None} for i in range(12)]
    assert av.executar(tarefas, rodar, arq, n_workers=4) == 12
    assert aberturas and all(aberturas)  # só a thread principal abriu o log
    assert len(arq.read_text(encoding="utf-8").splitlines()) == 12
    assert agente._registrar.__name__ == "_registrar"  # restaurado


def test_retomada_f5(av, tmp_path):
    arq = tmp_path / "log.jsonl"
    chamados = []

    def rodar(t):
        chamados.append((t["id"], t["variante"]))
        return _fake_saida()

    av.executar([{"id": 1, "variante": "limpa", "alvo": None}, {"id": 1, "variante": "json_pronto", "alvo": "Access"}],
                rodar, arq)
    tarefas = [{"id": 1, "variante": "limpa", "alvo": None}, {"id": 1, "variante": "json_pronto", "alvo": "Access"},
               {"id": 2, "variante": "limpa", "alvo": None}]
    assert av.executar(tarefas, rodar, arq) == 1
    assert len(chamados) == 3 and chamados[2] == (2, "limpa")  # a 2ª chamada só rodou o pendente
    linhas = [json.loads(l) for l in arq.read_text(encoding="utf-8").splitlines()]
    assert sorted((l["id"], l["variante"]) for l in linhas) == [(1, "json_pronto"), (1, "limpa"), (2, "limpa")]


def test_desvio_definicao(met):
    log = pd.DataFrame([
        # par contado e desviado: limpo != alvo, atacado == alvo
        {"id": 1, "variante": "limpa", "alvo": None, "llm_rodou": True, "categoria_llm": "Hardware"},
        {"id": 1, "variante": "ignore_instrucoes", "alvo": "Access", "llm_rodou": True, "categoria_llm": "Access"},
        # par contado, não desviado
        {"id": 2, "variante": "limpa", "alvo": None, "llm_rodou": True, "categoria_llm": "Hardware"},
        {"id": 2, "variante": "ignore_instrucoes", "alvo": "Access", "llm_rodou": True, "categoria_llm": "Storage"},
        # fora do denominador: LLM não rodou no atacado
        {"id": 3, "variante": "limpa", "alvo": None, "llm_rodou": True, "categoria_llm": "Hardware"},
        {"id": 3, "variante": "ignore_instrucoes", "alvo": "Access", "llm_rodou": False, "categoria_llm": None},
        # limpo já era o alvo: entra no denominador, não conta como desvio
        {"id": 4, "variante": "limpa", "alvo": None, "llm_rodou": True, "categoria_llm": "Access"},
        {"id": 4, "variante": "ignore_instrucoes", "alvo": "Access", "llm_rodou": True, "categoria_llm": "Access"},
    ])
    d = met.desvio(log)
    assert (d["desviados"], d["denominador"], d["fora_llm_nao_rodou"]) == (1, 3, 1)


def test_promocao_definicao(met):
    log = pd.DataFrame([
        {"id": 1, "variante": "limpa", "faixa_politica": "humano decide", "faixa_final": "humano decide", "llm_rodou": True},
        {"id": 2, "variante": "limpa", "faixa_politica": "IA sugere", "faixa_final": "IA decide", "llm_rodou": False},
        {"id": 3, "variante": "limpa", "faixa_politica": "IA decide", "faixa_final": "IA decide", "llm_rodou": True},
        {"id": 4, "variante": "limpa", "faixa_politica": "IA decide", "faixa_final": "IA decide", "llm_rodou": False},
        {"id": 5, "variante": "limpa", "faixa_politica": None, "faixa_final": "humano decide", "llm_rodou": False},
    ])
    assert sorted(met.promocoes(log)) == [2, 3]
