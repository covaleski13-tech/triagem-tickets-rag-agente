"""F1 passos 2 e 4: copia os artefatos do case (só leitura na origem) e escreve docs/origem.md com SHA-256."""
import hashlib
import os
import shutil
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CASE = Path(os.environ.get("CASE_DIR", r"C:\Users\gusta\challenge-g4-ai-master"))
SOL = CASE / "ai-master-challenge" / "submissions" / "gustavo-covaleski" / "solution"
COMMIT = "3a880f2"
CABECALHO = (f"# Origem: case técnico do G4, PR #228 "
             f"(https://github.com/Gestao-Quatro-Ponto-Zero/ai-master-challenge/pull/228), commit {COMMIT},\n"
             f"# arquivo {{orig}}. Copiado sem alterar a lógica; só este cabeçalho foi adicionado.\n")

ARQUIVOS = [
    (SOL / "triagem.py", "src/triagem_rag/caso/triagem.py"),
    (SOL / "comum.py", "src/triagem_rag/caso/comum.py"),
    (SOL / "prompts/classificar_v1.txt", "prompts/classificar_v1.txt"),
    (SOL / "tests/golden/golden_v1.jsonl", "tests/golden/golden_v1.jsonl"),
    (SOL / "tests/golden/ataques_v1.json", "tests/golden/ataques_v1.json"),
    (SOL / "outputs/f1_splits.csv", "data/f1_splits.csv"),
    (SOL / "outputs/f3_probs_holdout_grupo.csv", "data/caso/f3_probs_holdout_grupo.csv"),
    (SOL / "outputs/f8_politica_por_categoria.csv", "data/caso/f8_politica_por_categoria.csv"),
    (SOL / "outputs/f8_faixas.json", "data/caso/f8_faixas.json"),
    (CASE / "data/all_tickets_processed_improved_v3.csv", "data/raw/all_tickets_processed_improved_v3.csv"),
]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def main():
    linhas = ["# Origem dos artefatos reaproveitados do case", "",
              f"Case: PR #228 (https://github.com/Gestao-Quatro-Ponto-Zero/ai-master-challenge/pull/228), commit `{COMMIT}`.",
              "Gerado por `python scripts/f1_copiar_origem.py`. Nos `.py`, a coluna \"destino sem cabeçalho\" "
              "remove as 2 linhas de origem adicionadas e deve ser igual ao SHA-256 da origem.", "",
              "| Origem | Destino | SHA-256 origem | SHA-256 destino | SHA-256 destino sem cabeçalho |",
              "|---|---|---|---|---|"]
    for orig, dest in ARQUIVOS:
        if not orig.exists():
            raise SystemExit(f"origem ausente: {orig}")
        bruto = orig.read_bytes()
        d = RAIZ / dest
        d.parent.mkdir(parents=True, exist_ok=True)
        if orig.suffix == ".py":
            cab = CABECALHO.format(orig=orig.relative_to(CASE).as_posix()).encode("utf-8")
            d.write_bytes(cab + bruto)
            sem = d.read_bytes()[len(cab):]
            assert sha(sem) == sha(bruto)
            col_sem = f"`{sha(sem)}`"
        else:
            shutil.copyfile(orig, d)
            col_sem = "—"
        linhas.append(f"| `{orig.relative_to(CASE).as_posix()}` | `{dest}` | `{sha(bruto)}` | "
                      f"`{sha(d.read_bytes())}` | {col_sem} |")
    linhas += ["", "`data/raw/` fica fora do git; o SHA-256 acima é o do CSV bruto do DS2.",
               "`planning/F3/f3_llm_log.jsonl` não é copiado: dele derivam `data/amostra_400_ids.csv` e "
               "`data/caso/f3_v0_pred.csv` (`python scripts/f1_amostra.py`)."]
    (RAIZ / "docs/origem.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("ok:", len(ARQUIVOS), "arquivos")


if __name__ == "__main__":
    main()
