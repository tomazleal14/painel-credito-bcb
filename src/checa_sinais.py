"""checa_sinais.py -- confere o SINAL das contas redutoras (provisao / perda esperada).

No COSIF, provisao e conta retificadora do ativo: o saldo publicado e NEGATIVO.
Usar o valor cru faz a cobertura e a razao provisao/carteira sairem negativas.
Este script mostra a evidencia antes de aplicar o valor absoluto.
"""
from __future__ import annotations

import pandas as pd

from comum import DATA_PROC

COLS = ["provisao_antiga", "perda_esperada", "inadimplencia_valor",
        "ativos_problematicos_valor", "carteira_credito"]


def main() -> None:
    p = pd.read_parquet(DATA_PROC / "painel_ifdata_longo.parquet")
    print("SINAL DOS CAMPOS (contagem por sinal, todas as linhas nao nulas)\n")
    print(f"{'campo':32s} {'negativos':>11s} {'zeros':>9s} {'positivos':>11s}")
    for c in COLS:
        if c not in p.columns:
            continue
        s = p[c].dropna()
        print(f"{c:32s} {(s < 0).sum():>11,} {(s == 0).sum():>9,} {(s > 0).sum():>11,}")

    print("\nEXEMPLO -- ITAU, ultimo trimestre de cada regime")
    for dt in [202412, 202603]:
        linha = p[(p["data_base"] == dt) & p["instituicao"].str.contains("ITAU", na=False)]
        if linha.empty:
            continue
        r = linha.iloc[0]
        print(f"\n  {dt} :: {r['instituicao']} ({r['regime_contabil']})")
        for c in COLS:
            if c in linha.columns and pd.notna(r[c]):
                print(f"    {c:30s} {r[c]:>22,.2f}")


if __name__ == "__main__":
    main()
