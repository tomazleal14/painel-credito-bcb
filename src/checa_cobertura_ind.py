"""
checa_cobertura_ind.py -- cobertura de CADA indicador ao longo do tempo e o efeito
disso na composicao do score do eixo.

Responde: quais indicadores tem serie mais curta, por que, e quantos indicadores
sustentam o score do eixo em cada trimestre.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

import catalogo
from cartoes import indicadores_por_eixo
from comum import DATA_PROC
from scoring import EIXOS, PESOS_PADRAO, calcula_scores

CORTE = 1e9


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eixo", default="crescimento", choices=list(EIXOS))
    args = ap.parse_args()
    eixo = args.eixo

    ind = pd.read_parquet(DATA_PROC / "app_indicadores.parquet")
    ativos, _ = catalogo.carrega_ativos()
    sc = calcula_scores(ind, grupo_pares="tcb", pesos=PESOS_PADRAO, ativos=ativos)
    u = sc[sc["carteira_credito_real"] >= CORTE]
    cols = indicadores_por_eixo(ativos)[eixo]

    print(f"EIXO {eixo.upper()} — trimestres com dado, por indicador\n")
    print(f"   {'indicador':32s} {'trim.':>6s} {'de':>4s} {'primeiro':>10s} {'ultimo':>9s}")
    dts = sorted(u["data_base"].unique())
    for c in cols:
        pres = [d for d in dts
                if u[(u.data_base == d)][c].replace([np.inf, -np.inf], np.nan).notna().any()]
        print(f"   {catalogo.rotulo(c):32s} {len(pres):>6d} {len(dts):>4d} "
              f"{(str(pres[0])[4:6] + '/' + str(pres[0])[:4]) if pres else '—':>10s} "
              f"{(str(pres[-1])[4:6] + '/' + str(pres[-1])[:4]) if pres else '—':>9s}")

    print(f"\n   quantos indicadores sustentam o score de {eixo} em cada trimestre")
    print(f"   {'data-base':>10s} {'indicadores':>12s}  " +
          "  ".join(f"{catalogo.rotulo(c)[:9]:>9s}" for c in cols))
    for d in dts:
        q = u[u.data_base == d]
        marcas = "  ".join(
            (f"{'sim':>9s}" if q[c].replace([np.inf, -np.inf], np.nan).notna().any()
             else f"{'—':>9s}") for c in cols)
        print(f"   {d:>10d} {q[f'n_ind_{eixo}'].median():>12.0f}  {marcas}")


if __name__ == "__main__":
    main()
