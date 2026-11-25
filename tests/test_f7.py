"""F7: agente ADK. Roda só no .venv-adk (no .venv principal o módulo é pulado). Sem rede para a API: LLM falso
programado (mesmos roteiros da F4) ou servidor HTTP falso local para o caminho LiteLLM de ponta a ponta."""
import json
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

pytest.importorskip("google.adk")

from google.adk.models.llm_response import LlmResponse  # noqa: E402
from google.genai import types  # noqa: E402
from langchain_core.messages import AIMessage  # noqa: E402

from triagem_rag import agente  # noqa: E402
from triagem_rag import politica_caso as pc  # noqa: E402
from triagem_rag.adk import nos, workflow  # noqa: E402

import test_f4 as f4  # noqa: E402  mesmos tickets, roteiros e LLM falso da F4
from test_f4 import TREINO5, buscar_falso, chamada, resp  # noqa: E402

tickets_treino = f4.tickets_treino
isolado = f4.isolado
RAIZ = Path(__file__).resolve().parents[1]


def chamar_falso(*itens):
    """Mesmo roteiro do FakeTools da F4, no formato do ADK: AIMessage -> LlmResponse; Exception é levantada."""
    it = iter(itens)

    async def chamar(req):
        chamar.n += 1
        chamar.escolhas.append(req.config.tool_config.function_calling_config.allowed_function_names)
        item = next(it)
        if isinstance(item, BaseException):
            raise item
        partes = [types.Part(function_call=types.FunctionCall(name=tc["name"], args=tc["args"], id=tc.get("id")))
                  for tc in item.tool_calls]
        if item.content:
            partes.append(types.Part(text=item.content))
        return LlmResponse(content=types.Content(role="model", parts=partes))
    chamar.n, chamar.escolhas = 0, []
    return chamar


def _ambos(evento, roteiro, buscar_lg=None, buscar_adk=None, chave=""):
    lg = agente.triar_agente({**evento, "event_id": f"lg-{chave}"}, llm=f4.fake(*roteiro()), buscar=buscar_lg)
    ch = chamar_falso(*roteiro())
    adk = workflow.triar_agente_adk({**evento, "event_id": f"adk-{chave}"}, chamar=ch, buscar=buscar_adk)
    return lg, adk, ch


def test_adk_nunca_promove(tickets_treino):
    for n, (i, txt, cat, f) in enumerate(tickets_treino):
        outra = "Purchase" if cat != "Purchase" else "Storage"
        ch = chamar_falso(chamada("consultar_politica", {"categoria": "Access"}), resp(cat if n % 2 else outra, 1.0))
        s = workflow.triar_agente_adk({"texto": txt, "event_id": f"np-{i}"}, chamar=ch, buscar=buscar_falso(TREINO5))
        assert pc.ORDEM.index(s["faixa_final"]) <= pc.ORDEM.index(s["faixa_politica"])
        if s["llm_rodou"]:
            assert s["faixa_final"] != "IA decide"
        else:
            assert s["faixa_politica"] == "IA decide" and ch.n == 0
    assert {x[3] for x in tickets_treino} == set(pc.ORDEM)


CASOS_FALHA = {**f4.CASOS_FALHA,
               "duas_tools_2x": (lambda: [f4._duas("Access"), f4._duas("Access"), resp("Access")],
                                 "erro de tool: chamada múltipla", 2, None)}


@pytest.mark.parametrize("caso", list(CASOS_FALHA))
def test_adk_falhas(caso, tickets_treino, monkeypatch):
    roteiro, causa, chamadas_esperadas, especial = CASOS_FALHA[caso]
    i, txt, cat, f = f4.ticket_nao_ia_decide(tickets_treino)
    buscar = buscar_falso(TREINO5)
    if especial == "quebra":
        def buscar(texto, k):
            raise RuntimeError("banco fora")
    if especial == "politica":
        monkeypatch.setattr(agente, "_politica", lambda: (_ for _ in ()).throw(RuntimeError("x")))
    ch = chamar_falso(*roteiro())
    s = workflow.triar_agente_adk({"texto": txt}, chamar=ch, buscar=buscar)
    assert s["faixa_final"] == "humano decide" and s["motivo_final"] == f"escalado: {causa}"
    assert ch.n == chamadas_esperadas  # no máximo 1 nova tentativa; erro de tool não volta ao modelo
    if causa.startswith("erro de tool") and caso != "duas_tools_2x":
        assert s["tool_calls"][-1]["erro"] == causa.removeprefix("erro de tool: ")
    if caso in ("erro_api_2x", "timeout_2x", "sem_responder_2x", "duas_tools_2x"):
        assert len(s["erros"]) == 2


def _roteiros_paridade(cat):
    outra = "Purchase" if cat != "Purchase" else "Storage"
    base = {"concorda": lambda: [resp(cat, 0.4)], "diverge": lambda: [resp(outra, 1.0)],
            "tres_rodadas": lambda: [chamada("consultar_politica", {"categoria": cat}, "a"),
                                     chamada("recuperar_exemplos", {}, "b"), resp(cat)],
            "invalido_depois_valido": lambda: [f4.resp_args({"categoria": "Printer", "confianca": 0.9}), resp(cat)],
            "duas_depois_uma": lambda: [f4._duas(cat), resp(cat)],
            "texto_livre": lambda: [resp(cat, 0.7, texto="FRASE-LIVRE-DO-LLM")]}
    return {**base, **{k: v[0] for k, v in f4.CASOS_FALHA.items() if v[3] is None}}


def test_paridade(tickets_treino):
    """Mesmas respostas programadas -> mesma faixa_final e motivo_final (e mesmo registro de tools e erros)."""
    total = 0
    for i, txt, cat, f in tickets_treino:
        for nome, roteiro in _roteiros_paridade(cat).items():
            lg, adk, _ = _ambos({"texto": txt}, roteiro, buscar_falso(TREINO5), buscar_falso(TREINO5), f"{i}-{nome}")
            assert (adk["faixa_final"], adk["motivo_final"]) == (lg["faixa_final"], lg["motivo_final"]), (i, nome)
            sem_lat = lambda tcs: [{k: v for k, v in c.items() if k != "latencia_ms"} for c in tcs]  # noqa: E731
            assert sem_lat(adk["tool_calls"]) == sem_lat(lg["tool_calls"]), (i, nome)
            for k in ("erros", "rodadas", "llm_rodou", "categoria_llm", "faixa_politica", "chave"):
                assert adk[k] == (lg[k].replace("lg-", "adk-") if k == "chave" and lg[k] else lg[k]), (i, nome, k)
            total += 1
    assert total == 30 * len(_roteiros_paridade("Access"))


def test_guarda_importada(tickets_treino, monkeypatch):
    """O ADK usa o mesmo objeto no_guarda do agente.py (sem cópia) e o adaptador de estado é transparente."""
    fonte = "".join(p.read_text(encoding="utf-8") for p in (RAIZ / "src/triagem_rag/adk").glob("*.py"))
    assert "def no_guarda" not in fonte and "def no_deterministico" not in fonte and "def rota" not in fonte
    vistos = []
    original = agente.no_guarda
    monkeypatch.setattr(agente, "no_guarda", lambda e: vistos.append(e) or original(e))
    assert nos.ag is agente and workflow.ag is agente
    i, txt, cat, f = f4.ticket_nao_ia_decide(tickets_treino)
    workflow.triar_agente_adk({"texto": txt}, chamar=chamar_falso(resp(cat)))
    assert len(vistos) == 1 and "buscar" not in vistos[0]
    reg = {"a": 1, "buscar": print}
    assert nos.estado_guarda(reg) == {"a": 1}


def test_texto_livre_descartado_adk(tickets_treino):
    i, txt, cat, f = f4.ticket_nao_ia_decide(tickets_treino)
    s = workflow.triar_agente_adk({"texto": txt}, chamar=chamar_falso(resp(cat, 0.7, texto="FRASE-LIVRE-DO-LLM x")))
    assert s["categoria_llm"] == cat and "FRASE-LIVRE" not in json.dumps(s, ensure_ascii=False)


def test_contrato_sem_excecao_adk(monkeypatch):
    monkeypatch.setattr(agente, "no_deterministico", lambda e: (_ for _ in ()).throw(RuntimeError("x")))
    s = workflow.triar_agente_adk({"texto": "qualquer"}, chamar=chamar_falso())
    assert s["faixa_final"] == "humano decide" and s["motivo_final"] == "falha interna do agente"


# ---------- caminho LiteLLM real, contra servidor HTTP falso local ----------

def _tool_use(nome, args, i):
    return {"type": "tool_use", "id": i, "name": nome, "input": args}


class Servidor:
    """Anthropic falsa: cada POST consome um item do roteiro: lista de blocos tool_use, ("status", n) ou
    ("dorme", s). Guarda os corpos JSON recebidos."""

    def __init__(self, roteiro):
        self.roteiro, self.corpos = list(roteiro), []
        srv = self

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                srv.corpos.append(json.loads(self.rfile.read(int(self.headers["content-length"]))))
                item = srv.roteiro.pop(0) if srv.roteiro else [{"type": "text", "text": "fim"}]
                if isinstance(item, tuple) and item[0] == "dorme":
                    time.sleep(item[1])
                    item = [{"type": "text", "text": "tarde"}]
                if isinstance(item, tuple) and item[0] == "status":
                    corpo, codigo = {"type": "error", "error": {"type": "api_error", "message": "x"}}, item[1]
                else:
                    corpo, codigo = {"id": "m", "type": "message", "role": "assistant", "model": agente.MODELO,
                                     "stop_reason": "tool_use", "content": item,
                                     "usage": {"input_tokens": 100, "output_tokens": 10}}, 200
                b = json.dumps(corpo).encode()
                try:
                    self.send_response(codigo)
                    self.send_header("content-type", "application/json")
                    self.send_header("content-length", str(len(b)))
                    self.end_headers()
                    self.wfile.write(b)
                except OSError:
                    pass  # cliente já desistiu (timeout)

            def log_message(self, *a):
                pass
        self.http = ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.http.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.http.server_port}"

    def chamar(self, timeout_s=agente.TIMEOUT_S):
        m = workflow.modelo_litellm(timeout_s)
        m._additional_args.update(api_base=self.url, api_key="sk-falsa")
        return workflow.chamar_litellm(m)


@pytest.fixture
def ticket(tickets_treino):
    return f4.ticket_nao_ia_decide(tickets_treino)


def test_payload_adk(ticket):
    """Passo 0.3 como teste permanente, de ponta a ponta pelo Workflow com a subclasse LiteLlmPorRodada."""
    i, txt, cat, f = ticket
    srv = Servidor([[_tool_use("recuperar_exemplos", {}, "a")], [_tool_use("consultar_politica", {"categoria": cat}, "b")],
                    [_tool_use("responder", {"categoria": cat, "confianca": 0.5}, "c")]])
    s = workflow.triar_agente_adk({"texto": txt}, chamar=srv.chamar(), buscar=buscar_falso(TREINO5))
    assert s["rodadas"] == 3 and s["categoria_llm"] == cat and len(srv.corpos) == 3
    assert s["tokens_entrada"] == 300 and s["tokens_saida"] == 30
    lg = f4._payload(1)
    for n, c in enumerate(srv.corpos, 1):
        assert c["model"] == "claude-haiku-5-5" and c["max_tokens"] == 256
        assert c["thinking"] == {"type": "disabled"} and c["output_config"] == {"effort": "low"}
        for k in ("temperature", "top_p", "top_k"):
            assert k not in c
        assert [{k: v for k, v in t.items() if k != "type"} for t in c["tools"]] == lg["tools"]  # mesmas tools
        assert c["tool_choice"] == ({"type": "any", "disable_parallel_tool_use": True} if n < 3
                                    else {"type": "tool", "name": "responder"})
        assert "".join(b["text"] for b in c["system"]) == agente.PROMPT.read_text(encoding="utf-8")
        assert c["messages"][0] == {"role": "user", "content": [
            {"type": "text", "text": f"<ticket>{pc.mascarar(txt)}</ticket>"}]}
    # com include_contents="none", a rodada 2 ainda leva o tool_use e o resultado da rodada 1 (e a 3, os das duas)
    m2 = srv.corpos[1]["messages"]
    assert len(m2) == 3 and m2[1]["role"] == "assistant" and m2[2]["role"] == "user"
    uso = [b for b in m2[1]["content"] if b["type"] == "tool_use"]
    res = [b for b in m2[2]["content"] if b["type"] == "tool_result"]
    assert [(u["id"], u["name"], u["input"]) for u in uso] == [("a", "recuperar_exemplos", {})]
    assert [r["tool_use_id"] for r in res] == ["a"]
    conteudo = json.dumps(res[0]["content"], ensure_ascii=False)
    assert '\\"result\\"' in conteudo and "<ticket>" in conteudo  # os exemplos, embrulhados em {"result": ...}
    assert len(srv.corpos[2]["messages"]) == 5


@pytest.mark.parametrize("roteiro,causa", [([("status", 500), ("status", 500)], "erro de API"),
                                           ([("dorme", 3), ("dorme", 3)], "timeout")])
def test_repeticao_por_requisicao_real(ticket, roteiro, causa):
    """Adendo 1: num_retries=0 e sem RetryConfig: erro de API ou timeout = exatamente 2 requisições."""
    i, txt, cat, f = ticket
    srv = Servidor(roteiro)
    s = workflow.triar_agente_adk({"texto": txt}, chamar=srv.chamar(timeout_s=1), buscar=buscar_falso(TREINO5))
    time.sleep(0.2 if causa == "erro de API" else 4)  # o servidor termina de registrar o corpo atrasado
    assert len(srv.corpos) == 2 and s["faixa_final"] == "humano decide" and s["motivo_final"] == f"escalado: {causa}"
    assert len(s["erros"]) == 2, s["erros"]


def test_erro_de_tool_nao_volta_ao_modelo(ticket):
    """Adendo 2: exceção em recuperar_exemplos -> nenhuma requisição depois dela -> humano decide."""
    i, txt, cat, f = ticket

    def quebra(texto, k):
        raise RuntimeError("banco fora")
    srv = Servidor([[_tool_use("recuperar_exemplos", {}, "a")], [_tool_use("responder", {"categoria": cat,
                                                                                         "confianca": 1}, "b")]])
    s = workflow.triar_agente_adk({"texto": txt}, chamar=srv.chamar(), buscar=quebra)
    assert len(srv.corpos) == 1
    assert s["faixa_final"] == "humano decide" and s["motivo_final"] == "escalado: erro de tool: RuntimeError"


def test_nova_tentativa_nao_vira_rodada(ticket):
    """Adendo 3: nova tentativa na rodada 2 não transforma a rodada 3 em chamada sem responder forçado."""
    i, txt, cat, f = ticket
    duas = [_tool_use("recuperar_exemplos", {}, "x"), _tool_use("consultar_politica", {"categoria": cat}, "y")]
    srv = Servidor([[_tool_use("recuperar_exemplos", {}, "a")], duas,
                    [_tool_use("consultar_politica", {"categoria": cat}, "b")],
                    [_tool_use("responder", {"categoria": cat, "confianca": 0.5}, "c")]])
    s = workflow.triar_agente_adk({"texto": txt}, chamar=srv.chamar(), buscar=buscar_falso(TREINO5))
    escolhas = [c["tool_choice"] for c in srv.corpos]
    assert len(srv.corpos) == 4 and s["rodadas"] == 3 and s["categoria_llm"] == cat
    assert escolhas[:3] == [{"type": "any", "disable_parallel_tool_use": True}] * 3
    assert escolhas[3] == {"type": "tool", "name": "responder"}


def test_sem_rede_extra():
    """Adendo 4: num processo novo, com toda conexão que não seja 127.0.0.1 proibida, importar o ADK/LiteLLM e
    rodar o Workflow pelo caminho LiteLLM não tenta sair; sem callbacks de terceiros no LiteLLM."""
    codigo = r'''
import socket, sys
destinos = []
orig = socket.socket.connect
def connect(self, addr):
    destinos.append(addr[0] if isinstance(addr, tuple) else str(addr))
    if isinstance(addr, tuple) and addr[0] not in ("127.0.0.1", "::1", "localhost"):
        raise OSError("rede proibida no teste")
    return orig(self, addr)
socket.socket.connect = connect
import os
sys.path[:0] = ["src", "tests"]
from triagem_rag.adk import workflow
import litellm
assert os.environ["LITELLM_LOCAL_MODEL_COST_MAP"] == "True"
assert not litellm.callbacks and not litellm.success_callback and not litellm.failure_callback
assert not litellm._async_success_callback and not litellm._async_failure_callback
import test_f7
srv = test_f7.Servidor([[test_f7._tool_use("responder", {"categoria": "Access", "confianca": 1}, "a")]])
s = workflow.triar_agente_adk({"texto": "cannot access shared folder after password reset please help"},
                              chamar=srv.chamar(), buscar=lambda t, k: [])
assert s["llm_rodou"] and s["categoria_llm"] == "Access", s
fora = sorted({d for d in destinos if d not in ("127.0.0.1", "::1", "localhost")})
print("destinos:", sorted(set(destinos)), "fora:", fora)
assert not fora
'''
    env = {**__import__("os").environ, "TRIAGEM_RUNTIME_DIR": str(RAIZ / "runtime_f7" / "teste_rede")}
    r = subprocess.run([sys.executable, "-c", codigo], cwd=RAIZ, capture_output=True, text=True, env=env, timeout=300)
    assert r.returncode == 0, r.stderr[-2000:]
    assert "fora: []" in r.stdout
