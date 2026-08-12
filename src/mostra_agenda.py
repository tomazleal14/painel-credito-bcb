"""mostra_agenda.py -- imprime a agenda de supervisao do trimestre (mesma logica do app)."""
from __future__ import annotations

import argparse

import pandas as pd

from comum import DATA_PROC
from scoring import agenda, calcula_scores


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-base", type=int, default=202603)
    ap.add_argument("--corte", type=float, default=1e9, help="carteira minima em R$")
    ap.add_argument("--n", type=int, default=12)
    args = ap.parse_args()

    caminho = DATA_PROC / "app_indicadores.parquet"
    ind = pd.read_parquet(caminho if caminho.exists() else DATA_PROC / "indicadores.parquet")
    sc = calcula_scores(ind, grupo_pares="tcb")
    ag = agenda(sc, args.data_base, minimo_carteira=args.corte, n=args.n)

    print(f"AGENDA DE SUPERVISAO -- data-base {args.data_base} | "
          f"corte de carteira R$ {args.corte/1e9:.1f} bi\n")
    print(f"{'#':>2} {'instituicao':32s} {'cart(bi)':>9s} {'cresc':>7s} "
          f"{'inad':>6s} {'cobert':>7s} {'basil':>6s}  {'C':>1s}{'N':>1s}{'D':>1s} {'score':>6s}")
    marca = {"alto": "A", "medio": "m", "baixo": ".", "sem": "-"}
    for i, r in enumerate(ag.itertuples(), 1):
        f = lambda v, m=100, s="%": f"{v*m:.1f}{s}" if pd.notna(v) else "  -"
        print(f"{i:>2} {str(r.instituicao)[:32]:32s} "
              f"{r.carteira_credito_real/1e9:>9,.1f} "
              f"{f(r.p1_1_cresc_real_aa):>7s} "
              f"{f(r.p3_1_inadimplencia):>6s} "
              f"{f(r.p3_2_cobertura):>7s} "
              f"{f(r.indice_basileia):>6s}  "
              f"{marca[r.sem_crescimento]}{marca[r.sem_concentracao]}{marca[r.sem_deterioracao]} "
              f"{r.score_final:>6.3f}")
    print("\nC/N/D = semaforo de Crescimento / coNcentracao / Deterioracao "
          "(A=alto, m=medio, .=baixo, -=sem dado)")


if __name__ == "__main__":
    main()
