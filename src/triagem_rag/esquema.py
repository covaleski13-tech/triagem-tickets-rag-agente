import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, StrictFloat, StrictInt, ValidationError, field_validator

from triagem_rag.dados import CATEGORIAS

Categoria = Literal[tuple(CATEGORIAS)]  # type: ignore[valid-type]


class Classificacao(BaseModel):
    # extra ignorado e tipos estritos: mesma regra do validar() do f3_llm.py do case (bool e string rejeitados)
    model_config = ConfigDict(extra="ignore")
    categoria: Categoria
    confianca: StrictInt | StrictFloat

    @field_validator("confianca")
    @classmethod
    def _faixa(cls, v):
        if not 0 <= v <= 1:
            raise ValueError("confianca fora de [0, 1]")
        return v


def validar(texto) -> Classificacao | None:
    """JSON estrito: o texto inteiro, sem espaços nas pontas, é o objeto. Sem cercas nem texto ao redor."""
    try:
        obj = json.loads(texto.strip())
    except (json.JSONDecodeError, AttributeError):
        return None
    if not isinstance(obj, dict):
        return None
    try:
        return Classificacao.model_validate(obj)
    except ValidationError:
        return None
