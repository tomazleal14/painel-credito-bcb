"""qa_base.py -- controle de qualidade do painel processado (cobertura e sanidade)."""
from __future__ import annotations

import pandas as pd

from comum import DATA_PROC

CHAVE = ["carteira_credito", "pr", "indice_basileia", "provisao_antiga", "perda_esperada",
         "inadimplencia_valor", "ativos_problematicos_valor", "risco_h",
         "pf_cartao", "pf_sem_consignacao", "reg_sudeste", "qtd_clientes", "captacoes"]


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--universo", default="longo", choices=["longo", "prudencial"])
    args = ap.parse_args()

    p = pd.read_parquet(DATA_PROC / f"painel_ifdata_{args.universo}.parquet")
    pd.set_option("display.width", 220)
    print(f"universo: {args.universo}")

    print(f"painel: {len(p):,} linhas | {p['data_base'].nunique()} trimestres "
          f"| {p['cod_inst'].nunique():,} instituicoes\n")

    print("COBERTURA DOS CAMPOS-CHAVE (% de linhas preenchidas por regime)")
    presentes = [c for c in CHAVE if c in p.columns]
    ausentes = [c for c in CHAVE if c not in p.columns]
    if ausentes:
        print(f"  (campos inexistentes neste universo: {', '.join(ausentes)})")
    cob = (p.assign(regime=p["regime_contabil"])
             .groupby("regime")[presentes]
             .apply(lambda g: (g.notna().mean() * 100).round(1)))
    print(cob.to_string(), "\n")

    ult = p[p["data_base"] == p["data_base"].max()]
    print(f"TOP 8 POR CARTEIRA -- {ult['data_base'].iloc[0]} "
          f"(R$ bi reais de {int(p['base_deflator'].iloc[0])})")
    top = (ult.nlargest(8, "carteira_credito_real")
              [["instituicao", "carteira_credito_real", "indice_basileia",
                "inadimplencia_valor_real", "ativos_problematicos_valor_real"]]
              .assign(carteira_bi=lambda d: (d["carteira_credito_real"] / 1e9).round(1),
                      basileia_pct=lambda d: (d["indice_basileia"] * 100).round(2),
                      inad_pct=lambda d: (d["inadimplencia_valor_real"]
                                          / d["carteira_credito_real"] * 100).round(2),
                      probl_pct=lambda d: (d["ativos_problematicos_valor_real"]
                                           / d["carteira_credito_real"] * 100).round(2)))
    print(top[["instituicao", "carteira_bi", "basileia_pct", "inad_pct", "probl_pct"]]
          .to_string(index=False), "\n")

    soma = p.groupby("data_base")["carteira_credito_real"].sum() / 1e12
    print("CARTEIRA AGREGADA DO UNIVERSO (R$ tri reais) -- checagem de continuidade")
    print(soma.round(3).to_string())


if __name__ == "__main__":
    main()
