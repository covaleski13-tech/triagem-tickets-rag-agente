"""Agente LangGraph (F4, Q3). A política do case (triar) decide a faixa; o LLM só sugere uma categoria, com tool
calling real; a guarda determinística é a única fonte de faixa_final e nunca promove."""
import json
import os
import re
import time
from functools import lru_cache
from pathlib import Path
from typing import Any, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph

from triagem_rag import politica_caso as pc
from triagem_rag.dados import CATEGORIAS, RAIZ
from pydantic import ValidationError

from triagem_rag.esquema import Classificacao
from triagem_rag.llm import MODELO, checar_tracing, exemplo

# emenda F4: a resposta final vem pela tool `responder`; v1 fica como histórico
PROMPT = RAIZ / "prompts" / "agente_sugerir_v2.txt"
MAX_RODADAS = 3
MAX_TOKENS = 256  # 64 (F2) não cabe uma chamada de tool
TIMEOUT_S = 30
ORDEM = pc.ORDEM


@tool
def recuperar_exemplos() -> str:
    """Returns 5 labeled tickets from the training set that are similar to the current ticket. Takes no arguments."""
    raise RuntimeError("executada só pelo agente")  # o agente executa com o texto mascarado do estado


@tool
def consultar_politica(categoria: str) -> str:
    """Returns read-only configuration values recorded for one category. categoria must be one of the 8 categories."""
    raise RuntimeError("executada só pelo agente")


@tool(args_schema=Classificacao)
def responder(categoria: str, confianca: float) -> str:
    """Gives the final answer: categoria is one of the 8 categories; confianca is a number between 0 and 1."""
    raise RuntimeError("lida só pelo agente")


TOOLS = [recuperar_exemplos, consultar_politica, responder]


def tool_choice(rodada: int):
    # rodadas 1 e 2: alguma tool é obrigatória; rodada 3: só responder
    return "any" if rodada < MAX_RODADAS else "responder"


def validar_responder(args) -> Classificacao | None:
    """Argumentos do LLM são dado não confiável: exatamente categoria e confianca, tipos estritos (sem bool/string)."""
    if not isinstance(args, dict) or set(args) != {"categoria", "confianca"}:
        return None
    try:
        return Classificacao.model_validate(args)
    except ValidationError:
        return None


class ErroTool(Exception):
    pass


class FalhaLLM(Exception):
    pass


class Estado(TypedDict, total=False):
    evento: dict
    texto_mascarado: str
    resultado: dict
    faixa_politica: str
    categoria_classico: str | None
    p_max: float | None
    llm_rodou: bool
    sugestao_llm: dict | None
    falha_llm: str | None
    rodadas: int
    tool_calls: list
    erros: list
    tokens: dict
    faixa_final: str
    motivo_final: str


def cliente_agente(api_key: str | None = None):
    from langchain_anthropic import ChatAnthropic
    # mesmos parâmetros da F2, exceto max_tokens; sem temperature; repetições ficam no nosso código
    return ChatAnthropic(model=MODELO, max_tokens=MAX_TOKENS, max_retries=0, default_request_timeout=TIMEOUT_S,
                         thinking={"type": "disabled"}, output_config={"effort": "low"},
                         api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))


@lru_cache(maxsize=1)
def _textos_treino():
    from triagem_rag.dados import treino
    t = treino()
    return dict(zip(t["id"].astype(int), t["Document"].astype(str)))


def _buscar_padrao(texto, k):
    from triagem_rag.recuperacao import buscar_vetorial  # D-F3-1: vetorial
    return buscar_vetorial(texto, k)


def _politica() -> dict:
    return pc.triagem.carregar_politica()  # só leitura


def _erros_api():
    import anthropic
    return (anthropic.APIError, TimeoutError, ConnectionError)


def executar_tool(tc: dict, texto_mascarado: str, buscar) -> tuple[str, dict, dict]:
    """Executa uma tool call do LLM. Argumentos vindos do LLM são dado não confiável: listas fechadas, sem extras.
    Devolve (conteúdo para o LLM, resumo para o log, argumentos sanitizados para o log)."""
    nome, args = tc.get("name"), tc.get("args") or {}
    if nome == "recuperar_exemplos":
        if args:
            raise ErroTool("recuperar_exemplos não aceita argumentos")
        viz = buscar(texto_mascarado, 5)  # sempre o texto mascarado do estado, nunca texto vindo do LLM
        textos = _textos_treino()
        conteudo = "\n\n".join(exemplo(textos[int(j)], c) for j, c, _ in viz)
        return conteudo, {"ids": [int(j) for j, _, _ in viz], "categorias": [c for _, c, _ in viz]}, {}
    if nome == "consultar_politica":
        if set(args) != {"categoria"}:
            raise ErroTool("consultar_politica exige só o argumento categoria")
        cat = args["categoria"]
        if not isinstance(cat, str) or cat not in CATEGORIAS:
            raise ErroTool("categoria fora da lista")
        pol = _politica()
        res = {"categoria": cat, "teto": pol["por_categoria"].get(cat, "humano decide"),
               "t_decide": pol["t_decide"], "t_sugere": pol["t_sugere"]}
        return json.dumps(res), dict(res), {"categoria": cat}
    raise ErroTool("tool desconhecida")


def _args_log(tc: dict) -> dict:
    # nunca registrar valores livres vindos do LLM: só a categoria, se for da lista fechada, e o nº de argumentos
    args = tc.get("args") or {}
    cat = args.get("categoria") if isinstance(args, dict) else None
    return {"n_args": len(args) if isinstance(args, dict) else -1,
            **({"categoria": cat} if isinstance(cat, str) and cat in CATEGORIAS else {})}


def _nome_log(tc: dict) -> str:
    n = tc.get("name")
    return n if n in ("recuperar_exemplos", "consultar_politica", "responder") else "<desconhecida>"


def _ler_responder(r, rodada: int, chamadas: list) -> Classificacao | None:
    """Resposta final = a 1ª chamada a responder. Outras tool calls da mesma resposta são ignoradas e registradas.
    O texto livre do modelo (r.text) nunca é lido aqui: não é validado, logado nem guardado no estado."""
    principal = next((tc for tc in r.tool_calls if tc.get("name") == "responder"), None)
    for tc in r.tool_calls:
        if tc is not principal:
            chamadas.append({"nome": _nome_log(tc), "argumentos": _args_log(tc), "rodada": rodada, "ignorada": True})
    if principal is None:
        return None
    obj = validar_responder(principal.get("args"))
    chamadas.append({"nome": "responder", "rodada": rodada,
                     **({"argumentos": {"categoria": obj.categoria, "confianca": obj.confianca}} if obj else
                        {"argumentos": _args_log(principal), "erro": "argumentos inválidos"})})
    return obj


def _invocar(modelo, msgs, estado_tok, erros):
    """No máximo 1 nova tentativa por rodada para erro de API ou timeout (CLAUDE.md §3, regra do agente)."""
    for tentativa in (1, 2):
        try:
            r = modelo.invoke(msgs)
            u = getattr(r, "usage_metadata", None) or {}
            estado_tok["entrada"] += u.get("input_tokens", 0)
            estado_tok["saida"] += u.get("output_tokens", 0)
            return r
        except _erros_api() as e:
            timeout = isinstance(e, TimeoutError) or "Timeout" in type(e).__name__
            erros.append(f"{'timeout' if timeout else 'erro de API'} ({type(e).__name__}), tentativa {tentativa}")
            if tentativa == 2:
                raise FalhaLLM("timeout" if timeout else "erro de API")


def no_sugerir(estado: Estado, llm=None, buscar=None) -> dict:
    erros, chamadas, tok = [], [], {"entrada": 0, "saida": 0}
    rodadas, sugestao, falha = 0, None, None
    try:
        base = llm or cliente_agente()
        msgs = [SystemMessage(PROMPT.read_text(encoding="utf-8")),
                HumanMessage(f"<ticket>{estado['texto_mascarado']}</ticket>")]
        while True:
            rodadas += 1
            modelo = base.bind_tools(TOOLS, tool_choice=tool_choice(rodadas))
            r = _invocar(modelo, msgs, tok, erros)
            if not r.tool_calls or any(tc.get("name") == "responder" for tc in r.tool_calls):
                obj = _ler_responder(r, rodadas, chamadas)
                if obj is None:
                    erros.append("responder inválido ou ausente, tentativa 1")
                    r = _invocar(modelo, msgs, tok, erros)  # 1 nova tentativa da rodada
                    obj = _ler_responder(r, rodadas, chamadas)
                    if obj is None:
                        erros.append("responder inválido ou ausente, tentativa 2")
                        raise FalhaLLM("responder inválido")
                sugestao = {"categoria": obj.categoria, "confianca": obj.confianca}
                break
            if rodadas >= MAX_RODADAS:
                raise FalhaLLM("limite de rodadas")  # a 3ª rodada não executa tools
            msgs.append(r)
            for tc in r.tool_calls:
                t0 = time.perf_counter()
                reg = {"nome": _nome_log(tc), "argumentos": _args_log(tc), "rodada": rodadas}
                try:
                    conteudo, resumo, _ = executar_tool(tc, estado["texto_mascarado"], buscar or _buscar_padrao)
                except Exception as e:
                    causa = str(e) if isinstance(e, ErroTool) else type(e).__name__
                    chamadas.append({**reg, "erro": causa, "latencia_ms": round((time.perf_counter() - t0) * 1000, 1)})
                    raise FalhaLLM(f"erro de tool: {causa}")
                chamadas.append({**reg, "resultado": resumo, "latencia_ms": round((time.perf_counter() - t0) * 1000, 1)})
                msgs.append(ToolMessage(conteudo, tool_call_id=tc.get("id")))
    except FalhaLLM as e:
        falha = str(e)
    except Exception as e:
        falha = f"exceção ({type(e).__name__})"
        erros.append(falha)
    return {"llm_rodou": True, "sugestao_llm": sugestao, "falha_llm": falha, "rodadas": rodadas,
            "tool_calls": chamadas, "erros": erros, "tokens": tok}


def no_deterministico(estado: Estado) -> dict:
    ev = estado["evento"]
    res = pc.triar(ev)
    return {"resultado": res,
            "texto_mascarado": pc.mascarar(str(ev.get("texto") or ""), ev.get("nome_cliente")),
            "faixa_politica": res.get("faixa_sem_sombra", res.get("faixa", "humano decide")),
            "categoria_classico": res.get("categoria"), "p_max": res.get("p_max"),
            "llm_rodou": False, "tool_calls": [], "erros": [], "rodadas": 0, "tokens": {"entrada": 0, "saida": 0}}


def rota(estado: Estado) -> str:
    r = estado["resultado"]
    vai = (estado["faixa_politica"] != "IA decide" and not r.get("duplicado")
           and r.get("motivo") not in ("texto insuficiente", "falha do classificador") and r.get("erro") is None)
    return "sugerir" if vai else "guarda"


def no_guarda(estado: Estado) -> dict:
    """Única fonte de faixa_final. A confiança do LLM não entra em nenhuma regra."""
    res, fp = estado["resultado"], estado["faixa_politica"]
    try:
        if not estado.get("llm_rodou"):
            ff, mot = res["faixa"], res["motivo"]
        elif estado.get("falha_llm"):
            ff, mot = "humano decide", f"escalado: {estado['falha_llm']}"  # escalar_humano
        elif estado["sugestao_llm"]["categoria"] != estado["categoria_classico"]:
            ff, mot = "humano decide", "divergência LLM × clássico"
        else:
            ff, mot = res["faixa"], f"{res['motivo']}; LLM concorda"
        assert ORDEM.index(ff) <= ORDEM.index(fp), "promoção acima da política"
        assert not (estado.get("llm_rodou") and ff == "IA decide"), "IA decide com LLM"
    except Exception as e:
        ff, mot = "humano decide", f"escalado: guarda ({type(e).__name__})"
    return {"faixa_final": ff, "motivo_final": mot}


def construir_grafo(llm=None, buscar=None):
    g = StateGraph(Estado)
    g.add_node("deterministico", no_deterministico)
    g.add_node("sugerir", lambda s: no_sugerir(s, llm=llm, buscar=buscar))
    g.add_node("guarda", no_guarda)
    g.add_edge(START, "deterministico")
    g.add_conditional_edges("deterministico", rota, {"sugerir": "sugerir", "guarda": "guarda"})
    g.add_edge("sugerir", "guarda")
    g.add_edge("guarda", END)
    return g.compile()


def _caminho_log() -> Path:
    return Path(os.environ.get("TRIAGEM_AGENTE_LOG", pc.RUNTIME_AGENTE / "agente_log.jsonl"))


def _registrar(saida: dict):
    # motivo do case traz "termos: ..." (palavras do ticket): fora do log, que não pode ter texto de ticket
    linha = {k: saida.get(k) for k in ("chave", "faixa_politica", "faixa_final", "categoria_classico", "p_max",
                                       "categoria_llm", "llm_rodou", "rodadas", "tool_calls", "erros",
                                       "tokens_entrada", "tokens_saida", "latencia_ms")}
    linha["motivo_final"] = re.sub(r"termos: [^;]*", "termos: <omitidos no log>", str(saida.get("motivo_final")))
    arq = _caminho_log()
    arq.parent.mkdir(parents=True, exist_ok=True)
    with open(arq, "a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(linha, ensure_ascii=False) + "\n")


def triar_agente(evento: dict, llm=None, buscar=None) -> dict:
    """Contrato igual ao de triar(): nunca levanta exceção."""
    t0 = time.perf_counter()
    try:
        checar_tracing()
        s = construir_grafo(llm, buscar).invoke({"evento": evento})
        r, sug = s["resultado"], s.get("sugestao_llm")
        saida = {"faixa_final": s["faixa_final"], "motivo_final": s["motivo_final"], "chave": r.get("chave"),
                 "faixa_politica": s["faixa_politica"], "faixa_case": r.get("faixa"),
                 "categoria_classico": s.get("categoria_classico"), "p_max": s.get("p_max"),
                 "categoria_llm": sug["categoria"] if sug else None, "sugestao_llm": sug,
                 "llm_rodou": s.get("llm_rodou", False), "rodadas": s.get("rodadas", 0),
                 "tool_calls": s.get("tool_calls", []), "erros": s.get("erros", []),
                 "tokens_entrada": s.get("tokens", {}).get("entrada", 0),
                 "tokens_saida": s.get("tokens", {}).get("saida", 0)}
    except Exception as e:
        saida = {"faixa_final": "humano decide", "motivo_final": "falha interna do agente", "chave": None,
                 "faixa_politica": None, "categoria_classico": None, "p_max": None, "categoria_llm": None,
                 "sugestao_llm": None, "llm_rodou": False, "rodadas": 0, "tool_calls": [],
                 "erros": [f"falha interna ({type(e).__name__})"], "tokens_entrada": 0, "tokens_saida": 0}
    saida["latencia_ms"] = round((time.perf_counter() - t0) * 1000, 1)
    try:
        _registrar(saida)
    except Exception:
        saida["erros"] = saida["erros"] + ["falha ao gravar o log do agente"]
    return saida
