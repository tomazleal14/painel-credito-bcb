"""
diagnostica_score.py -- o numero de destaque do cartao de eixo diz alguma coisa?

O cartao mostra: mediana, entre as instituicoes do recorte, do score do eixo -- onde o
score de cada instituicao e a media dos seus percentis DENTRO do proprio grupo de pares.

Percentil tem mediana 0,50 por construcao. Entao a pergunta e: quanto o numero exibido
se afasta de 0,50, e esse afastamento carrega informacao ou e so ruido de recorte?
"""
from __future__ import annotations

import pandas as pd

from comum import DATA_PROC
from scoring import EIXOS, PESOS_PADRAO, calcula_scores

CORTES = [0, 1e9, 5e9]


def main() -> None:
    ind = pd.read_parquet(DATA_PROC / "app_indicadores.parquet")
    sc = calcula_scores(ind, grupo_pares="tcb", pesos=PESOS_PADRAO)

    print("1) O NUMERO EXIBIDO AO LONGO DO TEMPO (recorte carteira >= R$ 1 bi)")
    print(f"   {'data-base':>10s} {'IFs':>5s} " +
          " ".join(f"{e[:6]:>8s}" for e in EIXOS))
    linhas = []
    for dt in sorted(sc["data_base"].unique()):
        u = sc[(sc["data_base"] == dt) & (sc["carteira_credito_real"] >= 1e9)]
        vals = [u[f"score_{e}"].median() for e in EIXOS]
        linhas.append(vals)
        print(f"   {dt:>10d} {len(u):>5d} " +
              " ".join(f"{v:>8.3f}" if pd.notna(v) else f"{'-':>8s}" for v in vals))

    d = pd.DataFrame(linhas, columns=EIXOS)
    print("\n   amplitude do numero em 29 trimestres:")
    for e in EIXOS:
        s = d[e].dropna()
        print(f"     {e:14s} min {s.min():.3f} · max {s.max():.3f} · "
              f"amplitude {s.max()-s.min():.3f} · desvio {s.std():.4f}")

    print("\n2) O NUMERO DEPENDE DO CORTE DE PORTE?")
    dt = int(sc['data_base'].max())
    print(f"   {'corte':>12s} {'IFs':>5s} " + " ".join(f"{e[:6]:>8s}" for e in EIXOS))
    for corte in CORTES:
        u = sc[(sc["data_base"] == dt) & (sc["carteira_credito_real"] >= corte)]
        rot = "sem corte" if corte == 0 else f"R$ {corte/1e9:.0f} bi"
        print(f"   {rot:>12s} {len(u):>5d} " +
              " ".join(f"{u[f'score_{e}'].median():>8.3f}" for e in EIXOS))

    print("\n3) O QUE VARIA DE FATO -- instituicoes em risco alto (percentil >= 0,75)")
    print(f"   {'data-base':>10s} " + " ".join(f"{e[:6]:>8s}" for e in EIXOS))
    for dt in sorted(sc["data_base"].unique())[-8:]:
        u = sc[(sc["data_base"] == dt) & (sc["carteira_credito_real"] >= 1e9)]
        print(f"   {dt:>10d} " +
              " ".join(f"{int((u[f'sem_{e}'] == 'alto').sum()):>8d}" for e in EIXOS))

    print("\n4) E A CARTEIRA EXPOSTA A RISCO ALTO (fatia do recorte)")
    print(f"   {'data-base':>10s} " + " ".join(f"{e[:6]:>8s}" for e in EIXOS))
    for dt in sorted(sc["data_base"].unique())[-8:]:
        u = sc[(sc["data_base"] == dt) & (sc["carteira_credito_real"] >= 1e9)]
        tot = u["carteira_credito_real"].sum()
        fatias = [u.loc[u[f"sem_{e}"] == "alto", "carteira_credito_real"].sum() / tot * 100
                  for e in EIXOS]
        print(f"   {dt:>10d} " + " ".join(f"{v:>7.1f}%" for v in fatias))


if __name__ == "__main__":
    main()
