"""checa_virada.py -- o crescimento na virada 202412->202503 e real ou artefato?"""
from __future__ import annotations

import numpy as np
import pandas as pd

from comum import DATA_PROC

ALVOS = ["ITAU", "BRADESCO", "BNDES", "BTG PACTUAL", "CAIXA"]


def main() -> None:
    longo = pd.read_parquet(DATA_PROC / "painel_ifdata_longo.parquet",
                            columns=["data_base", "cod_inst", "instituicao",
                                     "carteira_credito_real", "tipo_instituicao"])
    prud = pd.read_parquet(DATA_PROC / "painel_ifdata_prudencial.parquet",
                           columns=["data_base", "cod_inst", "instituicao",
                                    "carteira_credito_real"])
    ind = pd.read_parquet(DATA_PROC / "app_indicadores.parquet",
                          columns=["data_base", "cod_inst", "instituicao",
                                   "carteira_credito_real", "p1_1_cresc_real_aa"])

    print("CARTEIRA (R$ bi) NA VIRADA — painel LONGO x painel PRUDENCIAL\n")
    print(f"   {'instituicao':22s} {'painel':>11s} "
          f"{'202412':>10s} {'202503':>10s} {'var%':>8s}")
    for nome in ALVOS:
        for rot, df in [("longo", longo), ("prudencial", prud)]:
            d = df[df["instituicao"].str.contains(nome, na=False)]
            a = d[d["data_base"] == 202412]["carteira_credito_real"].sum() / 1e9
            b = d[d["data_base"] == 202503]["carteira_credito_real"].sum() / 1e9
            var = (b / a - 1) * 100 if a else float("nan")
            print(f"   {nome:22s} {rot:>11s} {a:>10.1f} {b:>10.1f} {var:>7.1f}%")
        print()

    print("O QUE FOI PARAR NO INDICADOR (app_indicadores)\n")
    print(f"   {'instituicao':30s} {'cresc. 202503':>14s}")
    for nome in ALVOS:
        d = ind[(ind["data_base"] == 202503)
                & ind["instituicao"].str.contains(nome, na=False)]
        for r in d.itertuples():
            v = r.p1_1_cresc_real_aa
            print(f"   {str(r.instituicao)[:30]:30s} "
                  f"{(v*100 if pd.notna(v) else float('nan')):>13.1f}%")

    print("\nCODIGOS DE INSTITUICAO MUDAM NA VIRADA?\n")
    for dt in [202412, 202503]:
        d = longo[longo["data_base"] == dt]
        it = d[d["instituicao"].str.contains("ITAU", na=False)]
        print(f"   {dt}: tipo {d['tipo_instituicao'].iloc[0]} · "
              f"ITAU -> cod {list(it['cod_inst'])} · nome {list(it['instituicao'])}")

    print("\nDISTRIBUICAO DO CRESCIMENTO NO TRIMESTRE DA VIRADA\n")
    for dt in [202412, 202503, 202506]:
        s = ind[(ind["data_base"] == dt)
                & (ind["carteira_credito_real"] >= 1e9)]["p1_1_cresc_real_aa"]
        s = s.replace([np.inf, -np.inf], np.nan).dropna()
        print(f"   {dt}: mediana {s.median()*100:>6.1f}%  "
              f"p75 {s.quantile(.75)*100:>6.1f}%  p90 {s.quantile(.9)*100:>7.1f}%  "
              f"acima de 15%: {(s >= .15).mean()*100:>4.0f}%")


if __name__ == "__main__":
    main()
