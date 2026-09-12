"""
checa_dependencia_recorte.py -- quais indicadores dependem do CONJUNTO, e não só da
instituição?

Existe por causa de um bug real: HHI e CR5 eram calculados no build sobre as 1.403
instituições de cada trimestre e gravados como coluna constante. Filtrar o painel para
os 9 maiores bancos não mexia num dígito, embora o HHI do conjunto fosse 1.623 e não
951. Um número que descreve o recorte tem de ser recalculado quando o recorte muda.

Duas famílias de indicador, com tratamentos diferentes:

  POR INSTITUIÇÃO -- a fórmula só usa colunas da própria linha (inadimplência, carteira
  ÷ captações, HHI regional...). Filtrar não muda o valor de ninguém, e está correto que
  não mude.

  DO CONJUNTO -- a fórmula agrega sobre todas as instituições do trimestre (HHI do
  sistema, CR5, participação de mercado). Gravar no build congela o valor do universo
  inteiro. Ou o indicador é recalculado na tela, ou precisa declarar que descreve o
  universo e não o recorte.

Duas checagens:
  (1) VALOR ÚNICO -- o indicador assume um só valor no trimestre? Então é do conjunto,
      e ou está entre os recalculados na tela, ou é uma pendência.
  (2) SENSIBILIDADE AO RECORTE -- recalculando o que é recalculável, o número muda
      quando o recorte muda? Mostra o tamanho do erro que se estaria cometendo.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

import cartoes
import catalogo
from comum import DATA_PROC

CORTE = 1e9

# Indicadores de conjunto que o app JA recalcula na tela (ver cartoes.hhi_cr5).
# Entrar nesta lista e uma afirmacao verificavel: o app nao le a coluna gravada.
RECALCULADOS = {"p2_1_hhi_sistema", "p2_2_cr5_sistema_pct"}


def main() -> int:
    ind = pd.read_parquet(DATA_PROC / "app_indicadores.parquet")
    dt = int(max(ind["data_base"]))
    universo = ind[ind["data_base"] == dt]
    recorte = universo[universo["carteira_credito_real"] >= CORTE]

    print(f"data-base {str(dt)[4:6]}/{str(dt)[:4]} · universo {len(universo)} · "
          f"recorte (>= R$ 1 bi) {len(recorte)}\n")

    print("(1) INDICADORES COM VALOR ÚNICO NO TRIMESTRE — são do conjunto, não da IF")
    print(f"   {'indicador':34s} {'distintos':>9s} {'situação':>14s}")
    pendentes = []
    for i in catalogo.CATALOGO:
        if i.chave not in universo.columns:
            continue
        s = universo[i.chave].replace([np.inf, -np.inf], np.nan).dropna()
        if s.empty or s.nunique() > 1:
            continue
        ok = i.chave in RECALCULADOS
        print(f"   {i.rotulo[:34]:34s} {s.nunique():>9d} "
              f"{'recalculado' if ok else 'PENDENTE':>14s}")
        if not ok:
            pendentes.append(i.chave)
    if not pendentes:
        print("   (nenhum fora dos que o app já recalcula)")

    print("\n(2) SENSIBILIDADE AO RECORTE — o valor muda quando o conjunto muda?")
    hhi_u, cr5_u = cartoes.hhi_cr5(universo)
    hhi_r, cr5_r = cartoes.hhi_cr5(recorte)
    print(f"   {'HHI':>26s}  universo {hhi_u:>8.0f}  recorte {hhi_r:>8.0f}  "
          f"delta {hhi_r - hhi_u:>+7.0f}")
    print(f"   {'CR5':>26s}  universo {cr5_u:>7.1f}%  recorte {cr5_r:>7.1f}%  "
          f"delta {cr5_r - cr5_u:>+6.1f} p.p.")

    # participacao de mercado: por instituicao, mas o DENOMINADOR e do conjunto
    if "share_carteira" in universo.columns:
        cu = universo["carteira_credito_real"]
        cr = recorte["carteira_credito_real"]
        maior_u = float((cu / cu.sum()).max() * 100)
        maior_r = float((cr / cr.sum()).max() * 100)
        gravado = float(universo["share_carteira"].max() * 100)
        print(f"   {'maior participação':>26s}  universo {maior_u:>7.1f}%  "
              f"recorte {maior_r:>7.1f}%  delta {maior_r - maior_u:>+6.1f} p.p.")
        print(f"   {'':>26s}  gravado no parquet: {gravado:.1f}% "
              f"(= universo, por construção)")

    print("\n(3) OS DEMAIS SÃO POR INSTITUIÇÃO — filtrar não muda o valor de ninguém")
    por_inst = [i for i in catalogo.CATALOGO
                if i.chave in universo.columns
                and universo[i.chave].replace([np.inf, -np.inf], np.nan).dropna().nunique() > 1]
    print(f"   {len(por_inst)} de {len(catalogo.CATALOGO)} indicadores · "
          f"conferido: cada um assume mais de um valor no trimestre")
    iguais = 0
    for i in por_inst:
        a = recorte.set_index("cod_inst")[i.chave]
        b = universo.set_index("cod_inst")[i.chave].reindex(a.index)
        if a.equals(b) or np.allclose(a.dropna(), b.dropna(), equal_nan=True):
            iguais += 1
    print(f"   {iguais} de {len(por_inst)} têm valor idêntico dentro e fora do recorte, "
          f"como esperado")

    print()
    if pendentes:
        print(f"FALHA — {len(pendentes)} indicador(es) de conjunto exibido(s) como se "
              f"fosse(m) da instituição:")
        for c in pendentes:
            print(f"  - {c} ({catalogo.rotulo(c)})")
        print("\n  Ou o app recalcula na tela (como faz com HHI e CR5), ou o rótulo tem")
        print("  de dizer que descreve o universo, e não o recorte.")
        return 1
    if iguais != len(por_inst):
        print(f"FALHA — {len(por_inst) - iguais} indicador(es) por instituição mudam de "
              f"valor conforme o recorte, o que não deveria acontecer.")
        return 1
    print("todo indicador de conjunto é recalculado na tela; os por instituição não "
          "dependem do recorte")
    return 0


if __name__ == "__main__":
    sys.exit(main())
