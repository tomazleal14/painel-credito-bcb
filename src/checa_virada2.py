"""checa_virada2.py -- qual percentil de P1 dispara para os grandes na virada?"""
from __future__ import annotations

import numpy as np
import pandas as pd

import catalogo
from cartoes import indicadores_por_eixo
from comum import DATA_PROC
from scoring import PESOS_PADRAO, calcula_scores

ALVOS = ["ITAU", "BRADESCO", "BTG PACTUAL"]


def main() -> None:
    ind = pd.read_parquet(DATA_PROC / "app_indicadores.parquet")
    ativos, _ = catalogo.carrega_ativos()
    sc = calcula_scores(ind, grupo_pares="tcb", pesos=PESOS_PADRAO, ativos=ativos)
    cols = indicadores_por_eixo(ativos)["crescimento"]

    for nome in ALVOS:
        print(f"\n{'='*76}\n{nome}")
        for dt in [202409, 202412, 202503, 202506]:
            d = sc[(sc["data_base"] == dt) & sc["instituicao"].str.contains(nome, na=False)]
            if d.empty:
                print(f"  {dt}: ausente do painel")
                continue
            r = d.iloc[0]
            print(f"  {dt} · score {r['score_crescimento']:.3f} · "
                  f"tcb {r['tcb']} · n_ind {int(r['n_ind_crescimento'])}")
            for c in cols:
                v, p = r.get(c), r.get(f"pct_{c}")
                print(f"      {catalogo.rotulo(c):30s} "
                      f"{catalogo.formata(c, v):>12s}  pct "
                      f"{(f'{p:.3f}' if pd.notna(p) else '—'):>6s}")

    print(f"\n{'='*76}\nTAMANHO DO GRUPO DE PARES b1 E DISPERSAO DO INDICADOR")
    for dt in [202412, 202503]:
        g = sc[(sc["data_base"] == dt) & (sc["tcb"] == "b1")]
        print(f"\n  {dt}: {len(g)} instituicoes b1 no trimestre")
        for c in cols:
            s = g[c].replace([np.inf, -np.inf], np.nan).dropna()
            if len(s):
                print(f"      {catalogo.rotulo(c):30s} n={len(s):>3} "
                      f"mediana {catalogo.formata(c, s.median()):>12s} "
                      f"p90 {catalogo.formata(c, s.quantile(.9)):>12s}")
            else:
                print(f"      {catalogo.rotulo(c):30s} n=  0  (sem dado no grupo)")


if __name__ == "__main__":
    main()
