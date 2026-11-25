"""Adaptações específicas do ADK (contornos registrados em results/f7/esforco.json)."""
from typing import Any

from google.adk.models.lite_llm import LiteLlm
from google.adk.tools import BaseTool, ToolContext
from google.genai import types
from langchain_core.utils.function_calling import convert_to_openai_tool


class LiteLlmPorRodada(LiteLlm):
    """Contorno 1. O adaptador do ADK (lite_llm.py, modo ANY -> "required") descarta allowed_function_names e não
    tem como pedir disable_parallel_tool_use: a marca da rodada posta pelo callback vira tool_choice e
    parallel_tool_calls no formato OpenAI, que o LiteLLM converte para os dicts da Anthropic."""

    async def generate_content_async(self, llm_request, stream=False):
        nomes = llm_request.config.tool_config.function_calling_config.allowed_function_names or []
        kw = ({"tool_choice": {"type": "function", "function": {"name": nomes[0]}}} if len(nomes) == 1
              else {"tool_choice": "required", "parallel_tool_calls": False})
        req = llm_request.model_copy(deep=True)
        req.config.tool_config = None  # senão o ADK sobrescreve tool_choice com "required"
        # delegado novo por chamada: nada mutável compartilhado entre execuções concorrentes
        delegado = LiteLlm(model=self.model, **self._additional_args, **kw)
        async for r in delegado.generate_content_async(req, stream):
            yield r


class ToolBruta(BaseTool):
    """Contorno 3. O FunctionTool do ADK descarta argumentos extras e devolve erro de validação ou de argumento
    faltante ao LLM (function_tool.py, run_async). Aqui a declaração é a mesma da tool LangChain do agente.py
    (nome, descrição e JSON schema, por import) e a execução recebe os argumentos brutos, que passam pela
    validação do agente da F4 (executar_tool)."""

    def __init__(self, tool_lc, executar):
        f = convert_to_openai_tool(tool_lc)["function"]
        super().__init__(name=f["name"], description=f["description"])
        self._schema = f["parameters"]
        self._executar = executar

    def _get_declaration(self) -> types.FunctionDeclaration:
        return types.FunctionDeclaration(name=self.name, description=self.description,
                                         parameters_json_schema=self._schema)

    async def run_async(self, *, args: dict[str, Any], tool_context: ToolContext) -> Any:
        return self._executar(dict(args or {}), tool_context)
