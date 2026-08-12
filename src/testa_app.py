"""
testa_app.py -- exercita a logica do painel em TODOS os trimestres, sem abrir a interface.

Objetivo: garantir que nenhuma data-base quebra o app e que a degradacao e graciosa
onde o dado nao existe (regime AA-H nao tem inadimplencia 90+; antes de 2023Q3 nao ha
Informacoes de Capital). Cada linha mostra quantas instituicoes alimentam cada grafico.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd

from comum import DATA_PROC
from scoring import agenda, agenda_grandes, calcula_scores

# (rotulo, colunas exigidas pelo grafico)
GRAFICOS = {
    "P1.1 scatter cresc x share":   ["p1_1_cresc_real_aa", "share_carteira"],
    "P1.2 credit gap":              ["p1_2_credit_gap"],
    "P1.3 heatmap modalidade":      ["pf_cartao_real"],
    "P1.4 carteira/capital":        ["p1_4_cresc_carteira_sobre_capital"],
    "P2.2 composicao PF":           ["pf_total_real", "p2_3_pct_alto_risco"],
    "P2.3 regional":                ["p2_4_hhi_regional"],
    "P2.4 loan-to-deposit":         ["p2_6_loan_to_deposit", "p1_1_cresc_real_aa"],
    "P3.1 ASSINATURA":              ["p1_1_cresc_real_aa", "p3_1_inadimplencia"],
    "P3.2 efeito denominador":      ["p3_1_inadimplencia", "p3_4_inadimplencia_ajustada"],
    "P3.3 cobertura x problem.":    ["p3_2_cobertura", "p3_5_ativos_problematicos"],
    "P3.4 folga de capital":        ["p3_6_folga_capital_pp"],
}

CORTE = 1e9


def main() -> int:
    ind = pd.read_parquet(DATA_PROC / "indicadores.parquet")
    scored = calcula_scores(ind, grupo_pares="tcb")

    rotulos = list(GRAFICOS)
    print(f"{'data-base':>10s} {'IFs':>5s} {'atip.':>6s} {'grand.':>7s} " +
          " ".join(f"{r.split()[0]:>6s}" for r in rotulos))

    falhas = 0
    for dt in sorted(ind["data_base"].unique()):
        u = scored[(scored["data_base"] == dt)
                   & (scored["carteira_credito_real"] >= CORTE)]
        try:
            # as duas listas da agenda precisam sobreviver a todo trimestre
            ag = agenda(scored, dt, minimo_carteira=CORTE)
            gr = agenda_grandes(scored, dt)
        except Exception as e:  # noqa: BLE001
            print(f"{dt:>10d}  ERRO na agenda: {type(e).__name__}: {e}")
            falhas += 1
            continue

        contagens = []
        for rot in rotulos:
            cols = [c for c in GRAFICOS[rot] if c in u.columns]
            n = len(u.dropna(subset=cols)) if cols else 0
            contagens.append(n)
        print(f"{dt:>10d} {len(u):>5d} {len(ag):>6d} {len(gr):>7d} " +
              " ".join(f"{n:>6d}" for n in contagens))

    print("\nlegenda das colunas:")
    for r in rotulos:
        print(f"  {r.split()[0]:>6s}  {r}")
    print("\nzeros esperados (degradacao graciosa, nao erro):")
    print("  P3.1/P3.3 antes de 202503 -- inadimplencia 90+ so existe no regime ECL")
    print("  P1.4/P3.4 antes de 202309 -- Informacoes de Capital so existe no tipo 1009")
    print(f"\n{'FALHAS: ' + str(falhas) if falhas else 'nenhuma data-base quebra o painel'}")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
