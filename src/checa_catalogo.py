"""
checa_catalogo.py -- todo indicador do catálogo existe na base e tem cobertura?

Sem isto, um indicador poderia ser oferecido para troca ao vivo e chegar vazio na
tela durante a apresentação.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from catalogo import CATALOGO, EIXOS, do_eixo, formata
from comum import DATA_PROC


def main() -> int:
    caminho = DATA_PROC / "app_indicadores.parquet"
    if not caminho.exists():
        caminho = DATA_PROC / "indicadores.parquet"
    d = pd.read_parquet(caminho)
    dt = int(d["data_base"].max())
    u = d[(d["data_base"] == dt) & (d["carteira_credito_real"] >= 1e9)]

    print(f"base: {caminho.name} · data-base {dt} · recorte {len(u)} IFs\n")
    faltando, vazios = [], []

    for eixo in EIXOS:
        print(f"--- {eixo.upper()}")
        print(f"    {'indicador':32s} {'padrão':>7s} {'preench.':>9s} {'mediana':>14s}")
        for ind in do_eixo(eixo):
            if ind.chave not in d.columns:
                faltando.append(ind.chave)
                print(f"    {ind.rotulo:32s} {'sim' if ind.padrao else '-':>7s} "
                      f"{'AUSENTE':>9s}")
                continue
            s = u[ind.chave].replace([np.inf, -np.inf], np.nan).dropna()
            pct = len(s) / len(u) * 100 if len(u) else 0
            if len(s) == 0:
                vazios.append(ind.chave)
            print(f"    {ind.rotulo:32s} {'sim' if ind.padrao else '-':>7s} "
                  f"{pct:>8.0f}% {formata(ind.chave, s.median()) if len(s) else '—':>14s}")
        print()

    print(f"catálogo: {len(CATALOGO)} indicadores · "
          f"{sum(1 for i in CATALOGO if i.padrao)} no padrão")
    if faltando:
        print(f"\nFALHA: ausentes da base -> {', '.join(faltando)}")
        print("Rode src/indicadores.py e src/prepara_deploy.py.")
        return 1
    if vazios:
        print(f"\naviso: sem nenhum valor no recorte atual -> {', '.join(vazios)}")
    for eixo in EIXOS:
        n = sum(1 for i in do_eixo(eixo) if i.padrao)
        if n != 6:
            print(f"\nFALHA: eixo {eixo} tem {n} indicadores padrão, deveria ter 6")
            return 1
    print("\ntodo indicador do catálogo existe na base e a seleção padrão tem 6 por eixo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
