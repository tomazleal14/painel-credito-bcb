"""
diagnostica_salto.py -- a carteira exposta salta na virada 202412 -> 202503. É real?

A minissérie dos cartões da Visão geral mostra um degrau na virada de regime. Aqui se
investiga se ele vem do dado ou da troca de universo (tipo 1005 -> 1009, Res. 4.966).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import catalogo
from cartoes import carteira_exposta, indicadores_por_eixo
from comum import DATA_PROC
from scoring import EIXOS, PESOS_PADRAO, calcula_scores

CORTE = 1e9
VIRADA = 202503


def main() -> None:
    ind = pd.read_parquet(DATA_PROC / "app_indicadores.parquet")
    ativos, _ = catalogo.carrega_ativos()
    sc = calcula_scores(ind, grupo_pares="tcb", pesos=PESOS_PADRAO, ativos=ativos)
    u = sc[sc["carteira_credito_real"] >= CORTE]
    comp = indicadores_por_eixo(ativos)

    print("1) CARTEIRA EXPOSTA POR TRIMESTRE (o que a minissérie desenha)")
    print(f"   {'data-base':>10s} " + " ".join(f"{e[:7]:>9s}" for e in EIXOS) + "   IFs")
    series = {e: carteira_exposta(u, e) for e in EIXOS}
    for dt in sorted(u["data_base"].unique()):
        vals = " ".join(f"{series[e].get(dt, float('nan')):>8.1f}%" for e in EIXOS)
        marca = "  <-- virada de regime" if dt == VIRADA else ""
        print(f"   {dt:>10d} {vals}   {int((u['data_base']==dt).sum()):>4d}{marca}")

    print("\n2) O QUE MUDA NA VIRADA — cobertura de cada indicador")
    print(f"   {'indicador':32s} {'202412':>8s} {'202503':>8s}")
    antes = u[u["data_base"] == 202412]
    depois = u[u["data_base"] == VIRADA]
    for eixo in EIXOS:
        print(f"   -- {eixo}")
        for c in comp[eixo]:
            a = antes[c].replace([np.inf, -np.inf], np.nan).notna().mean() * 100
            d = depois[c].replace([np.inf, -np.inf], np.nan).notna().mean() * 100
            alerta = "  <-- passa a existir" if a < 5 and d > 50 else (
                     "  <-- deixa de existir" if a > 50 and d < 5 else "")
            print(f"      {catalogo.rotulo(c):29s} {a:>7.0f}% {d:>7.0f}%{alerta}")

    print("\n3) QUANTOS INDICADORES ENTRAM NA MÉDIA DE CADA EIXO")
    print(f"   {'eixo':14s} {'202412':>8s} {'202503':>8s}")
    for eixo in EIXOS:
        a = antes[f"n_ind_{eixo}"].median()
        d = depois[f"n_ind_{eixo}"].median()
        print(f"   {eixo:14s} {a:>8.0f} {d:>8.0f}")

    print("\n4) QUEM ESTÁ SINALIZADO EM CRESCIMENTO, ANTES E DEPOIS")
    for dt, rot in [(202412, "antes"), (VIRADA, "depois")]:
        d = u[(u["data_base"] == dt) & (u["sem_crescimento"] == "alto")]
        tot = u[u["data_base"] == dt]["carteira_credito_real"].sum()
        print(f"\n   {rot} ({dt}): {len(d)} sinalizadas · "
              f"{d['carteira_credito_real'].sum()/tot*100:.1f}% da carteira")
        for r in d.nlargest(5, "carteira_credito_real").itertuples():
            print(f"      {str(r.instituicao)[:38]:38s} R$ {r.carteira_credito_real/1e9:7.1f} bi"
                  f" · score {r.score_crescimento:.3f}")


if __name__ == "__main__":
    main()
