"""
checa_guarda_ticket.py -- a guarda de ticket em P2 nº 3 acerta o alvo?

P2 nº 3 (carteira PF em alto risco) usa a MODALIDADE como proxy de risco, e essa proxy e
calibrada para varejo. Fora do varejo ela inverte o sinal: a UBS (Brasil) marcava 100% de
"alto risco" com 72 clientes, ticket de R$ 45,2 milhoes e inadimplencia de 0,00% -- e o
que ha ali e credito colateralizado, o mais seguro do recorte.

A guarda esvazia o indicador acima do p90 do ticket medio do recorte. Este teste verifica
que ela:
  1. mascara exatamente o decil superior de ticket, e nada alem disso;
  2. pega a UBS, que e o caso que a motivou;
  3. NAO pega as financeiras de varejo, para quem a proxy funciona -- e onde esta a
     inadimplencia de verdade.

O item 3 e o que importa: uma guarda que tambem apagasse o varejo trocaria um erro por
outro maior.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from comum import DATA_PROC

CORTE = 1e9
DT_TESTE = 202603


def main() -> int:
    ind = pd.read_parquet(DATA_PROC / "app_indicadores.parquet")
    falhas: list[str] = []

    print("1. A GUARDA MASCARA O DECIL SUPERIOR DE TICKET, E SO ELE")
    print(f"   {'data-base':>10s} {'recorte':>8s} {'limiar (R$ mil)':>16s} "
          f"{'mascaradas':>11s} {'esperado':>9s}")
    for d in sorted(ind["data_base"].unique()):
        u = ind[(ind.data_base == d) & (ind.carteira_credito_real >= CORTE)]
        u = u[u["ctx_ticket_medio_real"] > 0]
        if len(u) < 20:
            continue
        lim = float(u["ctx_ticket_medio_real"].quantile(0.90))
        mascaradas = int((u["ctx_ticket_medio_real"] > lim).sum())
        esperado = int(round(len(u) * 0.10))
        if abs(mascaradas - esperado) > max(3, esperado * 0.35):
            falhas.append(f"{d}: {mascaradas} mascaradas, esperado ~{esperado}")
        if not np.isclose(float(u["ctx_ticket_limiar_real"].iloc[0]), lim, rtol=1e-6):
            falhas.append(f"{d}: limiar gravado nao bate com o p90 recalculado")
        if d in (sorted(ind["data_base"].unique())[0], DT_TESTE):
            print(f"   {d:>10d} {len(u):>8d} {lim/1000:>16,.1f} "
                  f"{mascaradas:>11d} {esperado:>9d}")

    print("\n2. TODA LINHA MASCARADA ESTA MESMO ACIMA DO LIMIAR")
    m = ind[ind["ctx_ticket_acima_p90"].fillna(False)]
    ruim = int((m["ctx_ticket_medio_real"] <= m["ctx_ticket_limiar_real"]).sum())
    vazias = int(m["p2_3_pct_alto_risco"].notna().sum())
    print(f"   {len(m):,} linhas marcadas · abaixo do limiar: {ruim} · "
          f"ainda com p2_3: {vazias}")
    if ruim:
        falhas.append(f"{ruim} linhas marcadas sem estar acima do limiar")
    if vazias:
        falhas.append(f"{vazias} linhas marcadas mantiveram p2_3")

    print("\n3. O CASO QUE MOTIVOU A GUARDA, E O QUE NAO PODE SER APAGADO")
    u = ind[(ind.data_base == DT_TESTE) & (ind.carteira_credito_real >= CORTE)]
    casos = [("UBS", True, "banco de investimento — deve ser mascarado"),
             ("CREFISA", False, "financeira de varejo — a proxy funciona"),
             ("AFINZ", False, "financeira de varejo — a proxy funciona"),
             ("MIDWAY", False, "varejo — a proxy funciona")]
    for nome, esperado_mascarado, por_que in casos:
        q = u[u.instituicao.astype(str).str.contains(nome, case=False, na=False)]
        if q.empty:
            print(f"   {nome:10s} ausente do recorte (nao testado)")
            continue
        r = q.iloc[0]
        mascarada = bool(r["ctx_ticket_acima_p90"])
        ok = mascarada == esperado_mascarado
        print(f"   {nome:10s} ticket R$ {r['ctx_ticket_medio_real']/1e6:>8.2f} mi · "
              f"mascarada={str(mascarada):5s} · p2_3="
              f"{'vazio' if pd.isna(r['p2_3_pct_alto_risco']) else f'{r.p2_3_pct_alto_risco*100:.1f}%':>7s}"
              f"  {'OK' if ok else 'FALHA'} — {por_que}")
        if not ok:
            falhas.append(f"{nome}: mascarada={mascarada}, esperado={esperado_mascarado}")

    print()
    if falhas:
        print(f"FALHAS ({len(falhas)}):")
        for f in falhas:
            print(f"  - {f}")
        return 1
    print("a guarda mascara o decil superior de ticket, pega o atacado e preserva o varejo")
    return 0


if __name__ == "__main__":
    sys.exit(main())
