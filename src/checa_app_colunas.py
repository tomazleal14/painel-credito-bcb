"""checa_app_colunas.py -- garante que toda coluna citada no app existe no arquivo enxuto.

Sem esta checagem, uma coluna ausente vira um travessao silencioso na tela em vez de erro --
e o painel exibiria campos vazios sem ninguem perceber.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

import catalogo
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

    # A regra do trabalho e EXATAMENTE 6 indicadores por pergunta. Ela vale sobre a
    # SELECAO ATIVA (indicadores.toml), nao sobre o arquivo: a troca ao vivo exige que
    # as 36 colunas do catalogo estejam publicadas, para que qualquer uma possa entrar
    # sem reprocessar a base. Contar colunas do parquet mediria o pool, nao a regra.
    # Colunas com sufixo de letra apos o numero (ex.: p3_1b) sao VARIANTES DE REGIME
    # CONTABIL do mesmo indicador: p3_1b e a medida AA-H (ate 202412) do indicador P3 nº 1,
    # que nao pode ser encadeada com a medida ECL. Nao entra no score nem na contagem.
    pool = sorted(c for c in df.columns if re.fullmatch(r"p[123]_\d+_\w+", c))
    variantes = sorted(c for c in df.columns if re.fullmatch(r"p[123]_\d+[a-z]_\w+", c))
    ativos, avisos = catalogo.carrega_ativos()

    print(f"\npool disponivel para troca ao vivo (colunas publicadas): {len(pool)}")
    for p, eixo in (("P1", "crescimento"), ("P2", "concentracao"), ("P3", "deterioracao")):
        print(f"  {p}: {len([c for c in pool if c.startswith(p.lower())])} candidatos")

    print("\nselecao ativa (indicadores.toml) -- e aqui que vale a regra dos 6")
    erro_regra = False
    for p, eixo in (("P1", "crescimento"), ("P2", "concentracao"), ("P3", "deterioracao")):
        do_p = list(ativos[eixo])
        fora_do_pool = [c for c in do_p if c not in df.columns]
        marca = "OK" if len(do_p) == 6 and not fora_do_pool else "FORA DA REGRA"
        if marca != "OK":
            erro_regra = True
        print(f"  {p}: {len(do_p)} [{marca}] -> {', '.join(c[3:] for c in do_p)}")
        for c in fora_do_pool:
            print(f"        ativo mas AUSENTE do arquivo publicado: {c}")

    for a in avisos:
        print(f"  aviso do catalogo: {a}")

    if variantes:
        print(f"\nvariantes de regime (NAO contam): {len(variantes)}")
        for v in variantes:
            print(f"  - {v}")

    print("\ntodas as colunas do app existem no arquivo publicado")
    return 1 if erro_regra else 0


if __name__ == "__main__":
    sys.exit(main())
