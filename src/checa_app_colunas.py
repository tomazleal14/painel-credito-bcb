"""checa_app_colunas.py -- garante que toda coluna citada no app existe no arquivo enxuto.

Sem esta checagem, uma coluna ausente vira um travessao silencioso na tela em vez de erro --
e o painel exibiria campos vazios sem ninguem perceber.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

from comum import DATA_PROC

RAIZ = Path(__file__).resolve().parent.parent


def main() -> int:
    df = pd.read_parquet(DATA_PROC / "app_indicadores.parquet")
    texto = (RAIZ / "app.py").read_text(encoding="utf-8")

    # colunas citadas como string literal no app
    citadas = set(re.findall(r'"((?:p[123]_|ctx_|pj_|reg_|pf_)\w+)"', texto))
    citadas |= set(re.findall(r'"(carteira_credito_real|share_carteira|indice_basileia|'
                              r'captacoes_real|qtd_clientes|instituicao|tcb|segmento_sr|'
                              r'cod_inst|data_base|regime_contabil)"', texto))

    # as chaves do dicionario de textos (LRC) tem a forma curta "p1_1".."p3_4" e NAO sao
    # colunas de dado -- excluir para nao gerar falso positivo
    citadas = {c for c in citadas if not re.fullmatch(r"p[123]_\d+", c)}

    faltando = sorted(c for c in citadas if c not in df.columns)
    ok = sorted(c for c in citadas if c in df.columns)

    print(f"colunas citadas no app: {len(citadas)}")
    print(f"  presentes no arquivo enxuto: {len(ok)}")
    if faltando:
        print(f"  AUSENTES ({len(faltando)}):")
        for c in faltando:
            print(f"    - {c}")
        return 1

    # A regra do trabalho e EXATAMENTE 6 indicadores por pergunta. Colunas com sufixo de
    # letra apos o numero (ex.: p3_1b) sao VARIANTES DE REGIME CONTABIL do mesmo indicador,
    # nao indicadores adicionais: p3_1b e a medida AA-H (ate 202412) do indicador P3 nº 1,
    # que nao pode ser encadeada com a medida ECL. Nao entra no score nem na contagem.
    inds = sorted(c for c in df.columns if re.fullmatch(r"p[123]_\d+_\w+", c))
    variantes = sorted(c for c in df.columns if re.fullmatch(r"p[123]_\d+[a-z]_\w+", c))

    print(f"\nindicadores (contam para a regra dos 6 por pergunta): {len(inds)}")
    erro_regra = False
    for p in ("p1", "p2", "p3"):
        do_p = [c for c in inds if c.startswith(p)]
        marca = "OK" if len(do_p) == 6 else "FORA DA REGRA"
        if len(do_p) != 6:
            erro_regra = True
        print(f"  {p.upper()}: {len(do_p)} [{marca}] -> {', '.join(c[3:] for c in do_p)}")

    if variantes:
        print(f"\nvariantes de regime (NAO contam): {len(variantes)}")
        for v in variantes:
            print(f"  - {v}")

    print("\ntodas as colunas do app existem no arquivo publicado")
    return 1 if erro_regra else 0


if __name__ == "__main__":
    sys.exit(main())
