"""
checa_trimestre_cartao.py -- o cartao da Visao geral obedece ao trimestre selecionado?

Existe por causa de um bug real: o numero de destaque saia de
`carteira_exposta(df_hist).dropna().iloc[-1]` -- o ultimo trimestre COM DADO da serie
inteira -- enquanto a barra de composicao usava o trimestre escolhido na barra lateral.
Trocar a data-base para 12/2025 nao mudava o numero grande, e o cartao exibia 2026Q1 no
topo com 12/2025 embaixo.

Duas travas:
  1. o numero do cartao tem que bater com a fatia "risco alto" da composicao, no MESMO
     trimestre, para todo trimestre do painel;
  2. trimestre em que nenhuma instituicao tem score tem que dar VAZIO, nao zero: zero
     diria "nada em risco alto" onde o correto e "nao da para avaliar".
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import catalogo
import cartoes
from comum import DATA_PROC
from scoring import EIXOS, PESOS_PADRAO, calcula_scores

CORTE = 1e9
# tolerancia RELATIVA: a carteira e float32 no parquet, e somar 258 valores em ordens
# diferentes da diferenca na 8a casa. O que se checa aqui e identidade de conceito,
# nao igualdade bit a bit.
TOL_REL = 1e-6


def main() -> int:
    ind = pd.read_parquet(DATA_PROC / "app_indicadores.parquet")
    ativos, _ = catalogo.carrega_ativos()
    sc = calcula_scores(ind, grupo_pares="tcb", pesos=PESOS_PADRAO, ativos=ativos)
    hist = sc[sc["carteira_credito_real"] >= CORTE]
    dts = sorted(hist["data_base"].unique())

    falhas: list[str] = []
    print(f"{'data-base':>10s}  " + "  ".join(f"{e[:12]:>12s}" for e in EIXOS))
    for d in dts:
        u = hist[hist["data_base"] == d]
        celulas = []
        for eixo in EIXOS:
            v = cartoes.exposta_no_trimestre(u, eixo)
            n_score = int(u[f"score_{eixo}"].notna().sum())

            # (1) o numero e a fatia "risco alto" da composicao do MESMO trimestre.
            # Sem nenhuma instituicao avaliavel, o esperado tambem e VAZIO: a barra
            # ainda desenha a fatia cinza de "nao avaliavel", entao risco alto = 0 --
            # mas 0 ali nao e uma medida, e ausencia dela.
            fatias = cartoes.composicao_carteira(u, eixo)
            total = sum(f[1] for f in fatias)
            alto = sum(f[1] for f in fatias if f[0] == "Risco alto")
            esperado = (alto / total * 100) if (total > 0 and n_score > 0) else np.nan

            if pd.isna(v) != pd.isna(esperado):
                falhas.append(f"{d} {eixo}: cartao {v} != composicao {esperado}")
            elif pd.notna(v) and abs(v - esperado) > TOL_REL * max(1.0, abs(esperado)):
                falhas.append(f"{d} {eixo}: cartao {v} != composicao {esperado}")

            # (2) sem nenhuma instituicao com score, o numero e VAZIO -- nunca zero
            if n_score == 0 and pd.notna(v):
                falhas.append(f"{d} {eixo}: 0 instituicoes com score, mas cartao mostra {v}")
            if n_score > 0 and pd.isna(v):
                falhas.append(f"{d} {eixo}: {n_score} com score, mas cartao vazio")

            celulas.append("vazio" if pd.isna(v) else f"{v:.1f}%")
        print(f"{d:>10d}  " + "  ".join(f"{c:>12s}" for c in celulas))

    # (3) o numero PRECISA variar entre trimestres -- se nao variar, voltou a ler a serie
    for eixo in EIXOS:
        vals = [cartoes.exposta_no_trimestre(hist[hist["data_base"] == d], eixo)
                for d in dts]
        distintos = {round(v, 4) for v in vals if pd.notna(v)}
        if len(distintos) <= 1:
            falhas.append(f"{eixo}: o numero nao varia entre trimestres "
                          f"({len(distintos)} valor distinto) -- suspeita de leitura fixa")

    print()
    if falhas:
        print(f"FALHAS ({len(falhas)}):")
        for f in falhas:
            print(f"  - {f}")
        return 1
    print("o numero do cartao segue o trimestre selecionado, bate com a composicao "
          "e fica vazio onde nao ha score")
    return 0


if __name__ == "__main__":
    sys.exit(main())
