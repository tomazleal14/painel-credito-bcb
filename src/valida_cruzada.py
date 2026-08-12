"""
valida_cruzada.py -- confronta o painel (IF.data, por instituicao) com fontes
INDEPENDENTES do BCB, para detectar erro de decodificacao ou de recorte.

Checagem 1: inadimplencia agregada do universo  x  SGS 21082 (inadimplencia do SFN)
Checagem 2: carteira agregada do universo       x  SGS 20539 (saldo da carteira do SFN)
Checagem 3: ativos problematicos do universo    x  SCR.data (ativo_problematico do sistema)

Nao se espera igualdade exata -- os recortes sao diferentes (o IF.data consolida por
conglomerado e inclui operacoes que o SGS classifica em outro bloco). Espera-se MESMA
ORDEM DE GRANDEZA e mesma direcao. Divergencia grande = sinal de erro.
"""
from __future__ import annotations

import pandas as pd

from comum import DATA_PROC


def main() -> None:
    ind = pd.read_parquet(DATA_PROC / "indicadores.parquet")
    sgs = pd.read_parquet(DATA_PROC / "sgs_series.parquet")
    scr = pd.read_parquet(DATA_PROC / "scr_agregado.parquet")

    sgs["mes"] = sgs["data"].dt.strftime("%Y%m").astype(int)

    # agregados do painel (soma de valores, nao media de razoes)
    agg = (ind.groupby("data_base")
              .apply(lambda g: pd.Series({
                  "carteira_bi": g["carteira_credito"].sum() / 1e9,
                  "inad_pct": (g["p3_1_inadimplencia"] * g["carteira_credito"]).sum()
                              / g.loc[g["p3_1_inadimplencia"].notna(), "carteira_credito"].sum() * 100,
                  "probl_pct": (g["p3_5_ativos_problematicos"] * g["carteira_credito"]).sum()
                               / g.loc[g["p3_5_ativos_problematicos"].notna(), "carteira_credito"].sum() * 100,
              }), include_groups=False)
              .reset_index())

    ref_carteira = (sgs[sgs["codigo_sgs"] == 20539].set_index("mes")["valor"] / 1e3)  # R$ mi -> R$ bi
    ref_inad = sgs[sgs["codigo_sgs"] == 21082].set_index("mes")["valor"]
    ref_probl = (scr[(scr["modalidade"] == "Todas") & (scr["cliente"] == "Todos")]
                 .set_index("mes")["ativo_problematico"])

    agg["sgs_carteira_bi"] = agg["data_base"].map(ref_carteira)
    agg["sgs_inad_pct"] = agg["data_base"].map(ref_inad)
    agg["scr_probl_pct"] = agg["data_base"].map(ref_probl)
    agg["razao_carteira"] = agg["carteira_bi"] / agg["sgs_carteira_bi"]

    pd.set_option("display.width", 200)
    print("PAINEL (IF.data) x FONTES INDEPENDENTES\n")
    print(agg.tail(10).round(2).to_string(index=False))

    print("\nleitura:")
    print(f"  carteira do painel / SGS 20539  : media {agg['razao_carteira'].mean():.2f} "
          f"(min {agg['razao_carteira'].min():.2f}, max {agg['razao_carteira'].max():.2f})")
    d_inad = (agg["inad_pct"] - agg["sgs_inad_pct"]).abs()
    print(f"  |inadimplencia painel - SGS|    : media {d_inad.mean():.2f} p.p.")
    d_probl = (agg["probl_pct"] - agg["scr_probl_pct"]).abs().dropna()
    if not d_probl.empty:
        print(f"  |ativo problematico - SCR|      : media {d_probl.mean():.2f} p.p.")


if __name__ == "__main__":
    main()
