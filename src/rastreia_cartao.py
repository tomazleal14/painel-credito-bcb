"""
rastreia_cartao.py -- segue o calculo do cartao de eixo do inicio ao fim, numa
instituicao real, para que cada numero da tela possa ser conferido a mao.

Cadeia: indicador -> percentil no grupo de pares -> score do eixo -> sinalizacao
        -> carteira exposta (o numero de destaque)
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from cartoes import FORMATO, INDICADORES_POR_EIXO, carteira_exposta
from comum import DATA_PROC
from scoring import CORTE_ALTO, EIXOS, PESOS_PADRAO, calcula_scores

CORTE = 1e9
EIXO = "crescimento"


def main() -> None:
    ind = pd.read_parquet(DATA_PROC / "app_indicadores.parquet")
    sc = calcula_scores(ind, grupo_pares="tcb", pesos=PESOS_PADRAO)
    dt = int(sc["data_base"].max())
    univ = sc[(sc["data_base"] == dt) & (sc["carteira_credito_real"] >= CORTE)].copy()

    print(f"data-base {dt} · recorte: {len(univ)} instituicoes com carteira >= R$ 1 bi")
    print("=" * 78)

    # ---------------------------------------------------------------- passo 1 a 3
    alvo = (univ[univ[f"sem_{EIXO}"] == "alto"]
            .nlargest(1, "carteira_credito_real").iloc[0])
    pares = sc[(sc["data_base"] == dt) & (sc["tcb"] == alvo["tcb"])]

    print(f"\nEXEMPLO: {alvo['instituicao']}")
    print(f"  TCB {alvo['tcb']} · carteira R$ {alvo['carteira_credito_real']/1e9:.1f} bi")
    print(f"  grupo de pares = as {len(pares)} instituicoes TCB '{alvo['tcb']}' "
          f"neste trimestre (todas, sem corte de porte)")

    print(f"\nPASSO 1-2: cada indicador do eixo '{EIXO}' vira um PERCENTIL no grupo")
    print(f"  {'indicador':34s} {'valor':>12s} {'percentil':>10s}")
    pcts = []
    for c in INDICADORES_POR_EIXO[EIXO]:
        rot, uni, fat, casas, _ = FORMATO[c]
        v = alvo.get(c)
        p = alvo.get(f"pct_{c}")
        if pd.notna(p):
            pcts.append(p)
        vtxt = f"{v*fat:,.{casas}f}{uni}" if pd.notna(v) else "sem dado"
        ptxt = f"{p:.3f}" if pd.notna(p) else "—"
        print(f"  {rot:34s} {vtxt:>12s} {ptxt:>10s}")

    print(f"\nPASSO 3: score do eixo = media dos {len(pcts)} percentis disponiveis")
    print(f"  ({' + '.join(f'{p:.3f}' for p in pcts)}) / {len(pcts)} = "
          f"{np.mean(pcts):.3f}")
    print(f"  score na base: {alvo[f'score_{EIXO}']:.3f}  "
          f"-> {'RISCO ALTO' if alvo[f'score_{EIXO}'] >= CORTE_ALTO else 'nao sinalizada'} "
          f"(corte {CORTE_ALTO})")

    # ---------------------------------------------------------------- passo 4
    print("\n" + "=" * 78)
    print("PASSO 4: o NUMERO DE DESTAQUE de cada cartao")
    print(f"  {'eixo':14s} {'IFs alto':>9s} {'carteira das sinalizadas':>26s} {'destaque':>10s}")
    total = univ["carteira_credito_real"].sum()
    for e in EIXOS:
        marc = univ[univ[f"sem_{e}"] == "alto"]
        soma = marc["carteira_credito_real"].sum()
        print(f"  {e:14s} {len(marc):>9d} {soma/1e9:>21,.1f} bi "
              f"{soma/total*100:>9.1f}%")
    print(f"  {'':14s} {'':>9s} {'carteira do recorte:':>21s} {total/1e9:,.1f} bi")

    # ---------------------------------------------------------------- componentes
    print("\n" + "=" * 78)
    print("OS COMPONENTES EXIBIDOS NO PE DO CARTAO")
    print("  Sao a MEDIANA de cada indicador -- e a mediana e calculada sobre")
    print("  TODAS as instituicoes do recorte, nao apenas sobre as sinalizadas.")
    print(f"\n  {'indicador':34s} {'todas (' + str(len(univ)) + ')':>14s} "
          f"{'so sinalizadas':>16s}")
    marc = univ[univ[f"sem_{EIXO}"] == "alto"]
    for c in INDICADORES_POR_EIXO[EIXO]:
        rot, uni, fat, casas, _ = FORMATO[c]
        a = univ[c].replace([np.inf, -np.inf], np.nan).dropna()
        b = marc[c].replace([np.inf, -np.inf], np.nan).dropna()
        ta = f"{a.median()*fat:,.{casas}f}{uni}" if len(a) else "—"
        tb = f"{b.median()*fat:,.{casas}f}{uni}" if len(b) else "—"
        print(f"  {rot:34s} {ta:>14s} {tb:>16s}")

    print("\n  => o cartao mostra hoje a coluna da ESQUERDA (todas).")

    # ---------------------------------------------------------------- 6 vs 4
    print("\n" + "=" * 78)
    print("POR QUE 6 PERCENTIS NUM EIXO E 4 NO OUTRO")
    for e in EIXOS:
        cols = INDICADORES_POR_EIXO[e]
        print(f"  {e:14s} {len(cols)} percentis: " +
              ", ".join(FORMATO[c][0] for c in cols))
    print("\n  Concentracao tem 6 indicadores no trabalho, mas 2 deles -- HHI do sistema")
    print("  e CR5 -- descrevem o MERCADO INTEIRO e sao identicos para todas as")
    print("  instituicoes no trimestre. Um valor igual para todos nao gera percentil")
    print("  (todos empatariam), entao nao entra na media.")
    hhi = univ["p2_1_hhi_sistema"].dropna().unique()
    cr5 = univ["p2_2_cr5_sistema_pct"].dropna().unique()
    print(f"\n  prova: HHI assume {len(hhi)} valor distinto no recorte ({hhi[0]:,.0f}) "
          f"e CR5 tambem {len(cr5)} ({cr5[0]:.1f}%)")


if __name__ == "__main__":
    main()
