"""
diagnostica_agenda.py -- mostra COMO as duas agendas sao formadas, e por que sao duas.

O score mede ATIPICIDADE dentro do grupo de pares -- nao relevancia sistemica. Com uma
lista unica por score, os cinco maiores bancos do pais ficavam entre a 548a e a 1046a
posicao e nao entravam na agenda de supervisao. Este script expoe esse efeito e a
correcao adotada.
"""
from __future__ import annotations

import pandas as pd

from comum import DATA_PROC
from scoring import (COBERTURA_GRANDES, LIMIAR_AGENDA, PESOS_PADRAO, agenda,
                     agenda_grandes, calcula_scores)

CORTE = 1e9


def main() -> None:
    ind = pd.read_parquet(DATA_PROC / "app_indicadores.parquet")
    sc = calcula_scores(ind, grupo_pares="tcb", pesos=PESOS_PADRAO)
    dt = int(sc["data_base"].max())
    univ = sc[(sc["data_base"] == dt) & (sc["carteira_credito_real"] >= CORTE)]
    todos = sc[sc["data_base"] == dt]
    carteira_recorte = univ["carteira_credito_real"].sum()

    ag = agenda(sc, dt, minimo_carteira=CORTE, limiar=LIMIAR_AGENDA)
    gr = agenda_grandes(sc, dt, cobertura=COBERTURA_GRANDES)

    print(f"data-base {dt}\n")
    print("LISTA 1 -- ATIPICAS NO GRUPO DE PARES")
    print(f"  criterio ......... score >= {LIMIAR_AGENDA:.2f} e carteira >= R$ 1 bi")
    print(f"  universo ......... {len(todos)} no trimestre, {len(univ)} apos o corte de porte")
    print(f"  selecionadas ..... {len(ag)}")
    if len(ag):
        print(f"  score ............ {ag['score_final'].min():.3f} a {ag['score_final'].max():.3f}")
        print(f"  carteira somada .. R$ {ag['carteira_credito_real'].sum()/1e9:.1f} bi "
              f"({ag['carteira_credito_real'].sum()/carteira_recorte*100:.1f}% do recorte)")
        print(f"  composicao ....... " +
              " · ".join(f"{k}:{v}" for k, v in ag["tcb"].value_counts().items()))

    print(f"\nLISTA 2 -- GRANDES COM SINAL")
    print(f"  criterio ......... maiores que somam {COBERTURA_GRANDES:.0%} da carteira do recorte")
    print(f"  selecionadas ..... {len(gr)}")
    if len(gr):
        print(f"  carteira somada .. R$ {gr['carteira_credito_real'].sum()/1e9:.1f} bi "
              f"({gr['carteira_credito_real'].sum()/carteira_recorte*100:.1f}% do recorte)")
        print(f"  score ............ {gr['score_final'].min():.3f} a {gr['score_final'].max():.3f}")
        print("\n  ordem de atencao (score decide a ORDEM, nao quem entra):")
        for r in gr.head(8).itertuples():
            print(f"    {int(r.posicao):>2}. {str(r.instituicao)[:36]:36s} "
                  f"R$ {r.carteira_credito_real/1e9:7.1f} bi | score {r.score_final:.3f}")

    print("\nCOBERTURA CONJUNTA DAS DUAS LISTAS")
    juntas = pd.concat([ag, gr]).drop_duplicates("cod_inst")
    print(f"  instituicoes distintas .. {len(juntas)}")
    print(f"  carteira coberta ........ "
          f"{juntas['carteira_credito_real'].sum()/carteira_recorte*100:.1f}% do recorte")
    print(f"  em ambas as listas ...... {len(set(ag['cod_inst']) & set(gr['cod_inst']))}")


if __name__ == "__main__":
    main()
