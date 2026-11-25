"""F7 (Q4): o agente da F4 reimplementado como workflow em grafo no Google ADK 2.0. Só roda no .venv-adk."""
import os

# antes de qualquer import do litellm: sem buscar a tabela de preços na internet (adendo F7, requisito 4)
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")
