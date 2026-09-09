"""
rastreia_eixo.py -- quem foi sinalizado num eixo, e por qual indicador.

Responde, com numeros: como as instituicoes de um eixo foram selecionadas, o que
distingue elas do resto do recorte, e qual indicador puxou cada uma para cima.
"""
from __future__ import annotations

import argparse

import numpy as np
import pandas as pd

import catalogo
from cartoes import indicadores_por_eixo
from comum import DATA_PROC
from scoring import CORTE_ALTO, EIXOS, PESOS_PADRAO, calcula_scores

CORTE = 1e9


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--eixo", default="deterioracao", choices=list(EIXOS))
    args = ap.parse_args()
    eixo = args.eixo

    ind = pd.read_parquet(DATA_PROC / "app_indicadores.parquet")
    ativos, _ = catalogo.carrega_ativos()
    sc = calcula_scores(ind, grupo_pares="tcb", pesos=PESOS_PADRAO, ativos=ativos)
    dt = int(sc["data_base"].max())
    u = sc[(sc["data_base"] == dt) & (sc["carteira_credito_real"] >= CORTE)].copy()

    cols = indicadores_por_eixo(ativos)[eixo]
    marc = u[u[f"sem_{eixo}"] == "alto"]

    print(f"EIXO {eixo.upper()} · data-base {dt} · recorte {len(u)} instituicoes")
    print(f"corte: score do eixo >= {CORTE_ALTO}  ->  {len(marc)} sinalizadas")
    print(f"carteira delas: {marc['carteira_credito_real'].sum()/u['carteira_credito_real'].sum()*100:.1f}%"
          f" do recorte\n")

    print("1) O QUE O CARTAO MOSTRA HOJE  x  O QUE DISTINGUE AS SINALIZADAS")
    print(f"   {'indicador':30s} {'recorte (' + str(len(u)) + ')':>16s} "
          f"{'sinalizadas (' + str(len(marc)) + ')':>18s}")
    for c in cols:
        a = u[c].replace([np.inf, -np.inf], np.nan).dropna()
        b = marc[c].replace([np.inf, -np.inf], np.nan).dropna()
        print(f"   {catalogo.rotulo(c):30s} "
              f"{catalogo.formata(c, a.median()) if len(a) else '—':>16s} "
              f"{catalogo.formata(c, b.median()) if len(b) else '—':>18s}")

    print(f"\n2) AS {len(marc)} SINALIZADAS, E O PERCENTIL DE CADA UMA")
    print(f"   {'instituicao':30s} {'TCB':>4s} {'score':>6s} " +
          " ".join(f"{catalogo.rotulo(c)[:9]:>10s}" for c in cols))
    for r in marc.nlargest(12, f"score_{eixo}").itertuples():
        pcts = []
        for c in cols:
            p = getattr(r, f"pct_{c}", np.nan)
            pcts.append(f"{p:>10.2f}" if pd.notna(p) else f"{'—':>10s}")
        print(f"   {str(r.instituicao)[:30]:30s} {r.tcb:>4s} "
              f"{getattr(r, f'score_{eixo}'):>6.3f} " + " ".join(pcts))

    print("\n3) QUAL INDICADOR PUXOU CADA UMA (percentil mais alto)")
    contagem: dict[str, int] = {}
    for r in marc.itertuples():
        melhor, valor = None, -1.0
        for c in cols:
            p = getattr(r, f"pct_{c}", np.nan)
            if pd.notna(p) and p > valor:
                melhor, valor = c, p
        if melhor:
            contagem[melhor] = contagem.get(melhor, 0) + 1
    for c, n in sorted(contagem.items(), key=lambda x: -x[1]):
        print(f"   {n:>2} de {len(marc)}  {catalogo.rotulo(c)}")

    print("\n4) INTERACAO COM OS OUTROS EIXOS")
    for e in EIXOS:
        n = int((marc[f"sem_{e}"] == "alto").sum())
        print(f"   das {len(marc)} sinalizadas em {eixo}, {n} tambem sao risco alto em {e}")
    print(f"\n   peso de cada eixo no score final: " +
          " · ".join(f"{e} {PESOS_PADRAO[e]:.2f}" for e in EIXOS))
    na_agenda = marc[marc["score_final"] >= 0.65]
    print(f"   das {len(marc)} sinalizadas em {eixo}, {len(na_agenda)} entram na agenda "
          f"(score final >= 0,65)")


if __name__ == "__main__":
    main()
