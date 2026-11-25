"""Workflow ADK 2.0 do agente (F7, Q4): START -> deterministico -> (sugerir -> guarda | guarda).
Mesmas tools, guarda, prompt v2, modelo e parâmetros do agente LangGraph (agente.py, congelado)."""
import asyncio
import time
import uuid

import triagem_rag.adk  # noqa: F401  LITELLM_LOCAL_MODEL_COST_MAP antes do litellm
from google.adk import Agent, Event, Runner, Workflow
from google.adk.sessions import InMemorySessionService
from google.adk.workflow import START
from google.genai import types

from triagem_rag import agente as ag
from triagem_rag.adk import nos
from triagem_rag.adk.tools_adk import LiteLlmPorRodada, ToolBruta

MODELO_LITELLM = f"anthropic/{ag.MODELO}"


def modelo_litellm(timeout_s: float = ag.TIMEOUT_S) -> LiteLlmPorRodada:
    # mesmos parâmetros do cliente_agente(); num_retries=0: a nova tentativa é a nossa, contada por requisição
    return LiteLlmPorRodada(model=MODELO_LITELLM, max_tokens=ag.MAX_TOKENS, thinking={"type": "disabled"},
                            output_config={"effort": "low"}, num_retries=0, timeout=timeout_s)


def chamar_litellm(modelo: LiteLlmPorRodada):
    async def chamar(req):
        ultima = None
        async for r in modelo.generate_content_async(req, stream=False):
            ultima = r
        return ultima
    return chamar


def _instrucao(_ctx) -> str:
    # InstructionProvider: o texto vai como está, sem a substituição de {variáveis} do ADK
    return ag.PROMPT.read_text(encoding="utf-8")


def construir_workflow(reg: dict, chamar) -> Workflow:
    def deterministico(node_input):
        reg.update(ag.no_deterministico({"evento": reg["evento"]}))
        rota = ag.rota(reg)
        return Event(output=f"<ticket>{reg['texto_mascarado']}</ticket>" if rota == "sugerir" else None, route=rota)

    def guarda(node_input):
        reg.update(ag.no_guarda(nos.estado_guarda(reg)))
        return Event(output=None)

    def iniciar_sugerir(node_input):
        reg.update({"llm_rodou": True, "sugestao_llm": None, "falha_llm": None})
        return Event(output=node_input)

    executar = nos.executor_tool(reg)
    sugerir = Agent(name="sugerir", model=nos.ModeloSugerir(model=ag.MODELO, reg=reg, chamar=chamar),
                    instruction=_instrucao, include_contents="none",
                    tools=[ToolBruta(t, executar(t.name)) for t in ag.TOOLS],
                    before_model_callback=nos.antes_do_modelo(reg))
    return Workflow(name="triagem_adk", edges=[
        (START, deterministico, {"sugerir": iniciar_sugerir, "guarda": guarda}),
        (iniciar_sugerir, sugerir, guarda),
    ])


async def _rodar(reg: dict, chamar):
    wf = construir_workflow(reg, chamar)
    ss = InMemorySessionService()
    s = await ss.create_session(app_name="triagem_adk", user_id="f7")
    runner = Runner(app_name="triagem_adk", node=wf, session_service=ss)
    # a mensagem de entrada não leva o ticket: o texto entra só mascarado, pelo nó determinístico
    async for _ in runner.run_async(user_id="f7", session_id=s.id, invocation_id=uuid.uuid4().hex,
                                    new_message=types.Content(role="user", parts=[types.Part(text="triar")])):
        pass


def triar_agente_adk(evento: dict, chamar=None, buscar=None) -> dict:
    """Mesmo contrato e mesma saída de agente.triar_agente: nunca levanta exceção. Não grava log (quem chama grava,
    na thread principal)."""
    t0 = time.perf_counter()
    reg = nos.novo_registro(evento, buscar)
    reg.update({"llm_rodou": False, "tool_calls": [], "erros": [], "rodadas": 0,
                "tokens": {"entrada": 0, "saida": 0}})
    try:
        ag.checar_tracing()
        asyncio.run(_rodar(reg, chamar or chamar_litellm(modelo_litellm())))
        r, sug = reg["resultado"], reg.get("sugestao_llm")
        saida = {"faixa_final": reg["faixa_final"], "motivo_final": reg["motivo_final"], "chave": r.get("chave"),
                 "faixa_politica": reg["faixa_politica"], "faixa_case": r.get("faixa"),
                 "categoria_classico": reg.get("categoria_classico"), "p_max": reg.get("p_max"),
                 "categoria_llm": sug["categoria"] if sug else None, "sugestao_llm": sug,
                 "llm_rodou": reg.get("llm_rodou", False), "rodadas": reg.get("rodadas", 0),
                 "tool_calls": reg.get("tool_calls", []), "erros": reg.get("erros", []),
                 "tokens_entrada": reg["tokens"]["entrada"], "tokens_saida": reg["tokens"]["saida"]}
    except Exception as e:  # nunca BaseException: a doc do ADK 2.0 pede para não travar pausas HITL
        saida = {"faixa_final": "humano decide", "motivo_final": "falha interna do agente", "chave": None,
                 "faixa_politica": None, "categoria_classico": None, "p_max": None, "categoria_llm": None,
                 "sugestao_llm": None, "llm_rodou": False, "rodadas": 0, "tool_calls": [],
                 "erros": [f"falha interna ({type(e).__name__})"], "tokens_entrada": 0, "tokens_saida": 0}
    saida["latencia_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    return saida
