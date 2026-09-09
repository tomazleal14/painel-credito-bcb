"""checa_serie_cartao.py -- o que a minissérie de cada eixo desenha, hoje, e por quê."""
from __future__ import annotations

import numpy as np
import pandas as pd

import catalogo
from cartoes import carteira_exposta
from comum import DATA_PROC
from scoring import EIXOS, PESOS_PADRAO, calcula_scores

CORTE = 1e9


def main() -> None:
    ind = pd.read_parquet(DATA_PROC / "app_indicadores.parquet")
    ativos, _ = catalogo.carrega_ativos()
    sc = calcula_scores(ind, grupo_pares="tcb", pesos=PESOS_PADRAO, ativos=ativos)
    u = sc[sc["carteira_credito_real"] >= CORTE]
    series = {e: carteira_exposta(u, e) for e in EIXOS}

    print("SERIE DESENHADA NA MINISSERIE (carteira exposta, % do recorte)\n")
    print(f"   {'data-base':>10s} " + " ".join(f"{e[:11]:>11s}" for e in EIXOS) +
          "   n sinalizadas")
    dts = sorted(u["data_base"].unique())
    for dt in dts:
        vals = " ".join(f"{series[e].get(dt, float('nan')):>10.1f}%" for e in EIXOS)
        ns = " ".join(f"{int((u[(u.data_base==dt)][f'sem_{e}']=='alto').sum()):>3d}"
                      for e in EIXOS)
        nota = ""
        if dt == 202503:
            nota = "  <- muda universo 1005->1009 e P1 fica sem indicadores"
        elif dt == 202603:
            nota = "  <- P1 volta a ter dado"
        print(f"   {dt:>10d} {vals}   {ns}{nota}")

    print("\nDELTA DE 12 MESES QUE O CARTAO MOSTRA (ultimo x 4 trimestres antes)")
    for e in EIXOS:
        s = series[e]
        if len(s) >= 5:
            print(f"   {e:14s} {s.iloc[-1]:.1f}% - {s.iloc[-5]:.1f}% = "
                  f"{s.iloc[-1]-s.iloc[-5]:+.1f} p.p.  "
                  f"(compara 202603 com {s.index[-5]})")

    print("\nQUANTOS INDICADORES ALIMENTAM O SCORE DE P1 EM CADA TRIMESTRE")
    for dt in dts[-8:]:
        q = u[u["data_base"] == dt]
        print(f"   {dt}: mediana de {q['n_ind_crescimento'].median():.0f} indicadores "
              f"(de 6) · {int((q['sem_crescimento']=='alto').sum())} sinalizadas")

    print("\nO DEGRAU DE CONCENTRACAO EM 202209 -- quem entrou")
    for dt in [202206, 202209]:
        d = u[(u["data_base"] == dt) & (u["sem_concentracao"] == "alto")]
        tot = u[u["data_base"] == dt]["carteira_credito_real"].sum()
        print(f"\n   {dt}: {len(d)} sinalizadas · "
              f"{d['carteira_credito_real'].sum()/tot*100:.1f}% da carteira")
        for r in d.nlargest(4, "carteira_credito_real").itertuples():
            print(f"      {str(r.instituicao)[:40]:40s} R$ {r.carteira_credito_real/1e9:7.1f} bi")


if __name__ == "__main__":
    main()
