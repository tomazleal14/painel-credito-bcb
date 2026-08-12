"""mostra_dicionario.py -- imprime o dicionario de campos do IF.data por relatorio."""
from __future__ import annotations

import argparse

from coleta_ifdata import monta_dicionario


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-base", type=int, default=202603)
    ap.add_argument("--tipo", type=int, default=1005)
    ap.add_argument("--relatorio", default=None, help="filtra por trecho do nome")
    ap.add_argument("--formula", action="store_true", help="mostra a formula COSIF")
    args = ap.parse_args()

    d = monta_dicionario(args.data_base, args.tipo)
    if d.empty:
        print("dicionario vazio -- rode a coleta deste periodo/tipo antes")
        return
    if args.relatorio:
        d = d[d["relatorio"].str.contains(args.relatorio, case=False, na=False)]

    for rel, g in d.groupby("relatorio", sort=False):
        print("=" * 96)
        print(f"### {rel}")
        print(f"    unidade: {g['legenda_unidade'].iloc[0][:88]}")
        print(f"    gerado em: {g['relatorio_gerado_em'].iloc[0]} | colunas: {len(g)}")
        for r in g.itertuples():
            recuo = "    " + "    " * int(r.nivel)
            nome = str(r.coluna_nome).replace("\n", " ")
            print(f"{recuo}- {nome}")
            if args.formula and r.formula_cosif:
                print(f"{recuo}    COSIF: {str(r.formula_cosif)[:140]}")


if __name__ == "__main__":
    main()
