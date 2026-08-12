"""
checa_dependencias.py -- garante que o painel so importa o que esta no requirements.txt.

Motivo: o app quebrou no Streamlit Cloud com ImportError porque `filtros.py` importava
`comum`, que importava `requests` no topo -- e `requests` havia saido do requirements de
execucao. Localmente nao aparecia, porque o venv de desenvolvimento tem tudo instalado.

Este teste percorre a cadeia de imports a partir de app.py, resolve os modulos locais e
compara os pacotes de terceiros com o requirements.txt. Roda sem instalar nada.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "src"

# nome do import -> nome no requirements (quando diferem)
APELIDOS = {"dateutil": "python-dateutil", "PIL": "pillow", "yaml": "pyyaml"}

# usados indiretamente por pandas/streamlit; nao precisam constar como import direto
IMPLICITOS = {"pyarrow"}


def modulos_locais() -> set[str]:
    return {p.stem for p in SRC.glob("*.py")}


def imports_de(caminho: Path) -> set[str]:
    """Imports que EXECUTAM ao importar o modulo.

    Imports dentro de funcoes sao ignorados de proposito: eles so falham se a funcao
    for chamada, e o painel nunca chama as funcoes de coleta. E exatamente por isso
    que `requests` foi movido para dentro de comum.baixa().
    """
    arvore = ast.parse(caminho.read_text(encoding="utf-8"), str(caminho))
    achados: set[str] = set()

    def percorre(corpo) -> None:
        for no in corpo:
            if isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue  # corpo de funcao/classe: import preguicoso, nao executa agora
            if isinstance(no, ast.Import):
                for a in no.names:
                    achados.add(a.name.split(".")[0])
            elif isinstance(no, ast.ImportFrom):
                if no.level == 0 and no.module:
                    achados.add(no.module.split(".")[0])
            # if/try/with no topo do modulo executam na importacao
            for campo in ("body", "orelse", "finalbody", "handlers"):
                filho = getattr(no, campo, None)
                if isinstance(filho, list):
                    percorre([x for x in filho if isinstance(x, ast.stmt)])

    percorre(arvore.body)
    return achados


def cadeia_do_app() -> tuple[set[str], list[str]]:
    """Percorre app.py e todos os modulos locais que ele alcanca."""
    locais = modulos_locais()
    a_visitar = [RAIZ / "app.py"]
    vistos: set[str] = set()
    terceiros: set[str] = set()
    percorridos: list[str] = []

    while a_visitar:
        caminho = a_visitar.pop()
        if str(caminho) in vistos or not caminho.exists():
            continue
        vistos.add(str(caminho))
        percorridos.append(caminho.name)
        for nome in imports_de(caminho):
            if nome in locais:
                a_visitar.append(SRC / f"{nome}.py")
            elif nome not in sys.stdlib_module_names:
                terceiros.add(APELIDOS.get(nome, nome))
    return terceiros, sorted(percorridos)


def pacotes_do_requirements() -> set[str]:
    txt = (RAIZ / "requirements.txt").read_text(encoding="utf-8")
    pacotes = set()
    for linha in txt.splitlines():
        linha = linha.split("#")[0].strip()
        if not linha or linha.startswith("-"):
            continue
        pacotes.add(linha.split(">=")[0].split("==")[0].split("[")[0].strip().lower())
    return pacotes


def main() -> int:
    terceiros, percorridos = cadeia_do_app()
    declarados = pacotes_do_requirements()

    print(f"módulos percorridos a partir de app.py: {', '.join(percorridos)}")
    print(f"\npacotes de terceiros usados em execução: {', '.join(sorted(terceiros))}")
    print(f"declarados em requirements.txt: {', '.join(sorted(declarados))}")

    faltando = {p for p in terceiros if p.lower() not in declarados}
    sobrando = declarados - {p.lower() for p in terceiros} - IMPLICITOS

    if faltando:
        print(f"\nFALHA: usados mas NÃO declarados -> {', '.join(sorted(faltando))}")
        print("O app quebraria no Streamlit Cloud com ImportError.")
        return 1

    if sobrando:
        print(f"\naviso: declarados mas não importados diretamente -> "
              f"{', '.join(sorted(sobrando))}")

    print("\ntoda dependência de execução está declarada")
    return 0


if __name__ == "__main__":
    sys.exit(main())
