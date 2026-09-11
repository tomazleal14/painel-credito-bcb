"""
crosswalk.py -- ponte OFICIAL entre o universo 1005 e o 1009, publicada pelo IF.data.

Problema que resolve
--------------------
Com a Res. 4.966, os relatorios de credito migram do tipo 1005 (Conglomerados
Financeiros e Instituicoes Independentes) para o 1009 (Conglomerados Prudenciais). Os
codigos mudam: o Itau e `10069` em 202412 e `1000080099` em 202503. Qualquer comparacao
de 12 meses que atravesse 202412->202503 fica sem par para os 582 conglomerados.

A ponte NAO e heuristica de nome
--------------------------------
O proprio cadastro do tipo 1005 declara o vinculo, em dois campos:
  c15 -- codigo do conglomerado prudencial, com 8 digitos ('00080075')
  c22 -- nome do conglomerado prudencial ('BRADESCO - PRUDENCIAL')

O codigo publicado no tipo 1009 e '1000' + os 6 digitos significativos de c15:
  BRADESCO   c0=10045  c15='00080075'  ->  1000080075   (confere com o 1009)
Verificado nos oito maiores e em 629 dos 638 vinculos de 202412.

Quem NAO precisa de ponte
-------------------------
As instituicoes independentes aparecem nos dois universos com o MESMO codigo (sao 782
em comum entre 202412 e 202503, todas de codigo curto). So os 582 codigos de 10 digitos
-- os conglomerados -- precisam da ponte.

Agregacao
---------
Um conglomerado prudencial reune varias entidades 1005. Reconstruir a serie dele antes
de 2025 exige SOMAR as entidades vinculadas, e nao escolher uma. Em 202412 sao 45 os
codigos 1009 que recebem mais de uma entidade 1005.
"""
from __future__ import annotations

import json

import pandas as pd

from comum import DATA_PROC, DATA_RAW

IFDATA = DATA_RAW / "ifdata"
TIPO_1005 = 1005
PREFIXO_1009 = "1000"
DIGITOS_1009 = 6


def _cadastro(dt: int, tipo: int) -> pd.DataFrame:
    p = IFDATA / str(dt) / f"cadastro{dt}_{tipo}.json"
    if not p.exists():
        return pd.DataFrame()
    return pd.DataFrame(json.loads(p.read_text(encoding="utf-8")))


def cod_prudencial(c15: str) -> str | None:
    """'00080075' -> '1000080075'. Vazio ou nao numerico -> None."""
    s = str(c15 or "").strip()
    if not s or not s.isdigit() or int(s) == 0:
        return None
    return PREFIXO_1009 + str(int(s)).zfill(DIGITOS_1009)


def monta(datas: list[int] | None = None) -> pd.DataFrame:
    """[data_base, cod_1005, cod_1009, nome_1009] para cada data-base com cadastro 1005."""
    if datas is None:
        datas = sorted(int(p.name) for p in IFDATA.iterdir()
                       if p.is_dir() and p.name.isdigit())
    linhas = []
    for dt in datas:
        cad = _cadastro(dt, TIPO_1005)
        if cad.empty or "c15" not in cad.columns:
            continue
        sub = cad[["c0", "c2", "c15"] + (["c22"] if "c22" in cad.columns else [])].copy()
        sub["cod_1009"] = sub["c15"].map(cod_prudencial)
        sub = sub[sub["cod_1009"].notna()]
        linhas.append(pd.DataFrame({
            "data_base": dt,
            "cod_1005": sub["c0"].astype(str),
            "cod_1009": sub["cod_1009"],
            "nome_1005": sub["c2"].astype(str),
            "nome_1009": (sub["c22"].astype(str) if "c22" in sub else ""),
        }))
    if not linhas:
        return pd.DataFrame(columns=["data_base", "cod_1005", "cod_1009",
                                     "nome_1005", "nome_1009"])
    return pd.concat(linhas, ignore_index=True)


def salva() -> pd.DataFrame:
    cw = monta()
    DATA_PROC.mkdir(parents=True, exist_ok=True)
    cw.to_parquet(DATA_PROC / "crosswalk_1005_1009.parquet", index=False)
    return cw


def main() -> None:
    cw = salva()
    print(f"crosswalk 1005 -> 1009: {len(cw):,} vinculos em "
          f"{cw['data_base'].nunique()} data-bases\n")
    print(f"   {'data-base':>10s} {'vinculos':>9s} {'conglomerados':>14s} "
          f"{'com >1 entidade':>16s}")
    for dt, g in cw.groupby("data_base"):
        n1 = int((g.groupby("cod_1009").size() > 1).sum())
        print(f"   {dt:>10d} {len(g):>9d} {g['cod_1009'].nunique():>14d} {n1:>16d}")

    # prova: os oito maiores de 202412 e o codigo 1009 que a ponte produz
    ult = cw[cw["data_base"] == cw["data_base"].max()]
    print(f"\n   amostra ({ult['data_base'].iloc[0]}) -- nome 1005 -> codigo e nome 1009")
    for r in ult.head(6).itertuples():
        print(f"     {r.nome_1005[:32]:32s} {r.cod_1005:>10s} -> {r.cod_1009} "
              f"· {r.nome_1009[:30]}")
    print(f"\n   salvo em {DATA_PROC / 'crosswalk_1005_1009.parquet'}")


if __name__ == "__main__":
    main()
