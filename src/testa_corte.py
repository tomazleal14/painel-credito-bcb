"""
testa_corte.py -- efeito de mover o corte de risco alto por eixo.

O corte de 0,75 e o quartil superior do grupo de pares: convencao de triagem, nao
exigencia normativa. Por isso e ajustavel na barra lateral -- e por isso precisa de um
teste que mostre o que ele move, para a pergunta "e se fosse 0,70?" ter resposta
medida em vez de opiniao.

Trava tambem a monotonicidade: baixar o corte nunca pode reduzir o numero de
sinalizadas nem a carteira exposta. Se reduzir, o semaforo esta invertido em algum
ponto.
"""
from __future__ import annotations

import sys

import pandas as pd

import cartoes
import catalogo
from comum import DATA_PROC
from scoring import CORTE_ALTO, EIXOS, PESOS_PADRAO, calcula_scores

CORTE_CARTEIRA = 1e9
CORTES = (0.65, 0.70, CORTE_ALTO, 0.80, 0.85)


def main() -> int:
    ind = pd.read_parquet(DATA_PROC / "app_indicadores.parquet")
    ativos, _ = catalogo.carrega_ativos()
    dt = int(max(ind["data_base"]))

    print(f"EFEITO DO CORTE DE RISCO ALTO -- data-base {str(dt)[4:6]}/{str(dt)[:4]}\n")
    cab = "  ".join(f"{e[:12]:>22s}" for e in EIXOS)
    print(f"   {'corte':>6s}  {cab}")
    print(f"   {'':>6s}  " + "  ".join(f"{'IFs / carteira':>22s}" for _ in EIXOS))

    linhas = {}
    for corte in CORTES:
        sc = calcula_scores(ind, grupo_pares="tcb", pesos=PESOS_PADRAO,
                            ativos=ativos, corte_alto=corte)
        u = sc[(sc["data_base"] == dt) & (sc["carteira_credito_real"] >= CORTE_CARTEIRA)]
        reg = {}
        for eixo in EIXOS:
            n = int((u[f"sem_{eixo}"] == "alto").sum())
            v = cartoes.exposta_no_trimestre(u, eixo)
            reg[eixo] = (n, 0.0 if pd.isna(v) else float(v))
        linhas[corte] = reg
        marca = "  <- padrao" if abs(corte - CORTE_ALTO) < 1e-9 else ""
        celulas = "  ".join(f"{reg[e][0]:>13d} / {reg[e][1]:>5.1f}%" for e in EIXOS)
        print(f"   {corte:>6.2f}  {celulas}{marca}")

    falhas = []
    ordenados = sorted(CORTES)
    for eixo in EIXOS:
        for menor, maior in zip(ordenados, ordenados[1:]):
            n_menor, c_menor = linhas[menor][eixo]
            n_maior, c_maior = linhas[maior][eixo]
            if n_menor < n_maior:
                falhas.append(f"{eixo}: corte {menor:.2f} sinaliza {n_menor} e "
                              f"{maior:.2f} sinaliza {n_maior} -- baixar o corte reduziu")
            if c_menor + 1e-9 < c_maior:
                falhas.append(f"{eixo}: corte {menor:.2f} expoe {c_menor:.2f}% e "
                              f"{maior:.2f} expoe {c_maior:.2f}% -- baixar o corte reduziu")

    print()
    if falhas:
        print(f"FALHAS ({len(falhas)}):")
        for f in falhas:
            print(f"  - {f}")
        return 1
    print("o corte e monotonico nos tres eixos: baixa-lo so pode aumentar a selecao")
    return 0


if __name__ == "__main__":
    sys.exit(main())
