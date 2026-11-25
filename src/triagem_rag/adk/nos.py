"""Nós e regras de rodada do agente ADK. Toda a lógica de decisão vem do agente.py da F4, por import:
no_deterministico, rota, no_guarda, executar_tool, validar_responder (via _ler_responder) e as mensagens de erro."""
import time
from types import SimpleNamespace
from typing import Any, AsyncGenerator

from google.adk.models.base_llm import BaseLlm
from google.adk.models.llm_response import LlmResponse
from google.genai import types

from triagem_rag import agente as ag


def novo_registro(evento: dict, buscar) -> dict:
    """Estado de uma execução, no mesmo formato do Estado do LangGraph (agente.Estado)."""
    return {"evento": evento, "buscar": buscar or ag._buscar_padrao}


def estado_guarda(reg: dict) -> dict:
    """Adaptador fino: o dict que no_guarda recebe no LangGraph, sem os campos só do ADK."""
    return {k: v for k, v in reg.items() if k != "buscar"}


def _erros_llm():
    import openai  # exceções do LiteLLM herdam de openai.APIError (inclui litellm.Timeout)
    return ag._erros_api() + (openai.APIError,)


def _como_ai(resp: LlmResponse) -> SimpleNamespace:
    """LlmResponse -> objeto com .tool_calls no formato do LangChain, para reusar _ler_responder e
    _registrar_multipla do agente.py. O texto livre do modelo não é copiado."""
    partes = (resp.content.parts if resp.content else None) or []
    return SimpleNamespace(tool_calls=[{"name": p.function_call.name, "args": p.function_call.args,
                                        "id": p.function_call.id} for p in partes if p.function_call])


def _fim() -> LlmResponse:
    # resposta sem tool: o Agent encerra e o fluxo segue para a guarda; texto fixo, nunca do LLM
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text="fim")]))


def antes_do_modelo(reg: dict):
    """before_model_callback: conta a rodada e marca no tool_config o tool_choice dela (traduzido pela
    LiteLlmPorRodada). Rodadas 1 e 2: alguma tool; rodada 3: só responder (agente.tool_choice)."""
    def cb(callback_context, llm_request):
        reg["rodadas"] += 1
        escolha = ag.tool_choice(reg["rodadas"])
        llm_request.config.tool_config = types.ToolConfig(function_calling_config=types.FunctionCallingConfig(
            mode=types.FunctionCallingConfigMode.ANY,
            allowed_function_names=None if escolha == "any" else [escolha]))
        return None
    return cb


class ModeloSugerir(BaseLlm):
    """Contorno 2. As regras por resposta do no_sugerir da F4 (1 nova tentativa para API/timeout, chamada
    múltipla, responder inválido, limite de rodadas, tool desconhecida) ficam aqui, em volta da requisição real
    (`chamar`), porque o ADK não tem ponto para repetir uma chamada ao modelo sem passar pelo fluxo de tools.
    Uma falha não levanta exceção para o ADK: vai para o registro e a resposta encerra o Agent."""
    reg: Any  # Any, não dict: o pydantic copiaria o dict e o registro compartilhado se perderia
    chamar: Any  # async (LlmRequest) -> LlmResponse; LiteLlmPorRodada em produção, roteiro falso nos testes

    async def _invocar(self, req):
        reg = self.reg
        for tentativa in (1, 2):
            try:
                r = await self.chamar(req)
                u = r.usage_metadata
                reg["tokens"]["entrada"] += (u.prompt_token_count or 0) if u else 0
                reg["tokens"]["saida"] += (u.candidates_token_count or 0) if u else 0
                return r
            except _erros_llm() as e:
                timeout = isinstance(e, TimeoutError) or "Timeout" in type(e).__name__
                # marca TLS: o antivírus da máquina intercepta parte das conexões (F7-report §5)
                tls = ": TLS" if "CERTIFICATE_VERIFY_FAILED" in str(e) else ""
                reg["erros"].append(f"{'timeout' if timeout else 'erro de API'} ({type(e).__name__}{tls}), "
                                    f"tentativa {tentativa}")
                if tentativa == 2:
                    raise ag.FalhaLLM("timeout" if timeout else "erro de API")

    async def _rodada(self, req) -> LlmResponse:
        reg, rodada, chamadas, erros = self.reg, self.reg["rodadas"], self.reg["tool_calls"], self.reg["erros"]
        resp = await self._invocar(req)
        r = _como_ai(resp)
        if len(r.tool_calls) > 1:
            ag._registrar_multipla(r, rodada, chamadas, erros, 1)
            resp = await self._invocar(req)
            r = _como_ai(resp)
            if len(r.tool_calls) > 1:
                ag._registrar_multipla(r, rodada, chamadas, erros, 2)
                raise ag.FalhaLLM("erro de tool: chamada múltipla")
        if not r.tool_calls or r.tool_calls[0].get("name") == "responder":
            obj = ag._ler_responder(r, rodada, chamadas)
            if obj is None:
                erros.append("responder inválido ou ausente, tentativa 1")
                resp = await self._invocar(req)
                obj = ag._ler_responder(_como_ai(resp), rodada, chamadas)
                if obj is None:
                    erros.append("responder inválido ou ausente, tentativa 2")
                    raise ag.FalhaLLM("responder inválido")
            reg["sugestao_llm"] = {"categoria": obj.categoria, "confianca": obj.confianca}
            return resp
        if rodada >= ag.MAX_RODADAS:
            raise ag.FalhaLLM("limite de rodadas")
        tc = r.tool_calls[0]
        if tc["name"] not in ("recuperar_exemplos", "consultar_politica"):
            # o ADK levantaria "tool not found"; mesma causa e registro do executar_tool da F4
            chamadas.append({"nome": ag._nome_log(tc), "argumentos": ag._args_log(tc), "rodada": rodada,
                             "erro": "tool desconhecida", "latencia_ms": 0.0})
            raise ag.FalhaLLM("erro de tool: tool desconhecida")
        return resp

    async def generate_content_async(self, llm_request, stream: bool = False) -> AsyncGenerator[LlmResponse, None]:
        reg = self.reg
        try:
            resp = await self._rodada(llm_request)
        except ag.FalhaLLM as e:
            reg["falha_llm"], resp = str(e), _fim()
        except Exception as e:
            reg["falha_llm"] = f"exceção ({type(e).__name__})"
            reg["erros"].append(reg["falha_llm"])
            resp = _fim()
        yield resp


def executor_tool(reg: dict):
    """Execução das tools com argumentos brutos (ToolBruta). Erro de tool não volta ao modelo: vai para o
    registro e skip_summarization encerra o Agent sem nova requisição (adendo F7, requisito 2)."""
    def executar(nome: str):
        def f(args: dict, tool_context) -> Any:
            if nome == "responder":
                tool_context.actions.skip_summarization = True  # contorno 4: sem 4ª chamada ao modelo
                return "ok"
            t0 = time.perf_counter()
            tc = {"name": nome, "args": args}
            linha = {"nome": nome, "argumentos": ag._args_log(tc), "rodada": reg["rodadas"]}
            try:
                conteudo, resumo, _ = ag.executar_tool(tc, reg["texto_mascarado"], reg["buscar"])
            except Exception as e:
                causa = str(e) if isinstance(e, ag.ErroTool) else type(e).__name__
                reg["tool_calls"].append({**linha, "erro": causa,
                                          "latencia_ms": round((time.perf_counter() - t0) * 1000, 1)})
                reg["falha_llm"] = f"erro de tool: {causa}"
                tool_context.actions.skip_summarization = True
                return "interrompido"
            reg["tool_calls"].append({**linha, "resultado": resumo,
                                      "latencia_ms": round((time.perf_counter() - t0) * 1000, 1)})
            return conteudo
        return f
    return executar
