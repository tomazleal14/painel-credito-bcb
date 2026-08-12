"""checa_p2_5.py -- cobertura do novo P2 nº 5 (% da carteira PJ em grande porte)
comparada a proxy que ele substituiu, dentro do universo que de fato entra na agenda.
"""
from __future__ import annotations

import pandas as pd

from comum import DATA_PROC

CORTES = [0, 1e9, 5e9]


def main() -> None:
    ind = pd.read_parquet(DATA_PROC / "indicadores.parquet")
    dt = ind["data_base"].max()
    u0 = ind[ind["data_base"] == dt]

    print(f"data-base {dt}\n")
    print(f"{'corte de carteira':>18s} {'IFs':>6s} {'novo P2.5':>11s} "
          f"{'proxy antiga':>13s} {'com PJ>0':>9s}")
    for corte in CORTES:
        u = u0[u0["carteira_credito_real"] >= corte]
        novo = u["p2_5_pct_grande_porte"].notna().sum()
        antigo = u["ctx_ticket_medio_real"].notna().sum()
        com_pj = (u["pj_total_porte_real"].fillna(0) > 0).sum()
        rot = "sem corte" if corte == 0 else f"R$ {corte/1e9:.0f} bi"
        print(f"{rot:>18s} {len(u):>6,} {novo:>7,} ({novo/len(u)*100:4.0f}%) "
              f"{antigo:>7,} ({antigo/len(u)*100:3.0f}%) {com_pj:>9,}")

    u = u0[u0["carteira_credito_real"] >= 1e9]
    print("\nDistribuicao do novo indicador (universo com carteira >= R$ 1 bi):")
    s = u["p2_5_pct_grande_porte"].dropna()
    for q in [0.10, 0.25, 0.50, 0.75, 0.90]:
        print(f"  p{int(q*100):>2d}: {s.quantile(q)*100:6.1f}% da carteira PJ em grande porte")

    print("\nMaiores exposicoes a tomadores de grande porte (carteira >= R$ 5 bi):")
    top = (u0[(u0["carteira_credito_real"] >= 5e9)]
           .dropna(subset=["p2_5_pct_grande_porte"])
           .nlargest(10, "p2_5_pct_grande_porte"))
    for r in top.itertuples():
        print(f"  {str(r.instituicao)[:34]:34s} "
              f"{r.p2_5_pct_grande_porte*100:5.1f}%  "
              f"(PJ R$ {r.pj_total_porte_real/1e9:6.1f} bi de "
              f"carteira R$ {r.carteira_credito_real/1e9:6.1f} bi)")

    sem_pj = u[(u["pj_total_porte_real"].fillna(0) <= 0)]
    print(f"\nIFs sem carteira PJ no recorte (indicador fica VAZIO, nao zero): {len(sem_pj)}")
    print("  exemplos:", ", ".join(str(x)[:26] for x in sem_pj["instituicao"].head(4)))


if __name__ == "__main__":
    main()
