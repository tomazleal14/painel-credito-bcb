"""
explica_score.py -- o cálculo do percentil e do score, passo a passo, com números reais.

Feito para a defesa: mostra o que é TCB, como um valor vira percentil dentro do grupo
de pares, como os percentis viram o score de cada pergunta, e como o sinal invertido
funciona nos indicadores em que "maior é melhor".
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


def secao(t: str) -> None:
    print("\n" + "=" * 82)
    print(t)
    print("=" * 82)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instituicao", default="NU PAGAMENTOS",
                    help="trecho do nome da instituição de exemplo")
    args = ap.parse_args()

    ind = pd.read_parquet(DATA_PROC / "app_indicadores.parquet")
    ativos, _ = catalogo.carrega_ativos()
    sc = calcula_scores(ind, grupo_pares="tcb", pesos=PESOS_PADRAO, ativos=ativos)
    dt = int(sc["data_base"].max())
    trim = sc[sc["data_base"] == dt]
    comp = indicadores_por_eixo(ativos)

    # ---------------------------------------------------------------- TCB
    secao("1) O QUE É TCB")
    print("""
TCB = Tipo de Consolidado Bancário. É a classificação que o BCB usa para agrupar
instituições por MODELO DE NEGÓCIO -- não por tamanho. Ela vem no cadastro do
IF.data e é publicada pelo próprio Banco Central.

É ela que define o GRUPO DE PARES: cada instituição é comparada apenas com as do
mesmo TCB, no mesmo trimestre. Comparar uma cooperativa singular com o Itaú em
nível absoluto não diria nada -- 15% de crescimento significa coisas diferentes
para cada um. O percentil resolve isso comparando cada uma com seus semelhantes.
""")
    gl = pd.read_csv(DATA_PROC / "glossario_filtros.csv", dtype=str).fillna("")
    tcb_desc = dict(zip(gl[gl["dimensao"] == "tcb"]["codigo"],
                        gl[gl["dimensao"] == "tcb"]["descricao"]))
    print(f"   {'TCB':5s} {'no trimestre':>13s} {'no recorte':>11s}  descrição")
    rec = trim[trim["carteira_credito_real"] >= CORTE]
    for cod, n in trim["tcb"].value_counts().items():
        print(f"   {cod:5s} {n:>13} {int((rec['tcb'] == cod).sum()):>11}  "
              f"{tcb_desc.get(cod, '')[:52]}")
    print(f"\n   total: {len(trim)} instituições no trimestre, {len(rec)} no recorte")

    # ---------------------------------------------------------------- exemplo
    alvo = trim[trim["instituicao"].str.contains(args.instituicao, na=False)]
    if alvo.empty:
        print(f"\ninstituição '{args.instituicao}' não encontrada")
        return
    r = alvo.iloc[0]
    grupo = trim[trim["tcb"] == r["tcb"]]

    secao(f"2) O PERCENTIL, POSIÇÃO A POSIÇÃO — {r['instituicao']}")
    print(f"\n   TCB {r['tcb']} ({tcb_desc.get(r['tcb'], '')})")
    print(f"   grupo de pares: as {len(grupo)} instituições TCB '{r['tcb']}' no trimestre {dt}")
    print(f"   ATENÇÃO: o grupo inclui TODAS do TCB, mesmo abaixo do corte de carteira.")

    col = "p1_1_cresc_real_aa"
    s = grupo[col].replace([np.inf, -np.inf], np.nan).dropna().sort_values()
    valor = r[col]
    posicao = int((s <= valor).sum())
    print(f"\n   Indicador de exemplo: {catalogo.rotulo(col)}")
    print(f"   valor da instituição: {catalogo.formata(col, valor)}")
    print(f"\n   ordenando as {len(s)} do grupo que têm este dado, do menor para o maior:")
    for q in [0.0, 0.25, 0.5, 0.75, 0.9, 1.0]:
        print(f"      posição {int(q*len(s)) or 1:>4} de {len(s)}  "
              f"({q*100:>5.0f}%)  {catalogo.formata(col, s.quantile(q))}")
    print(f"\n   a instituição é a {posicao}ª de {len(s)}, do menor para o maior")
    print(f"   percentil = {posicao} / {len(s)} = {posicao/len(s):.3f}")
    print(f"   percentil na base                = {r[f'pct_{col}']:.3f}")
    print(f"\n   LEITURA: {r[f'pct_{col}']*100:.0f}% do grupo cresce MENOS que ela.")

    # ---------------------------------------------------------------- inversao
    secao("3) O SINAL INVERTIDO — quando MAIOR é MELHOR")
    inv = "p3_2_cobertura"
    meta = catalogo.POR_CHAVE[inv]
    s2 = grupo[inv].replace([np.inf, -np.inf], np.nan).dropna().sort_values()
    if pd.notna(r.get(inv)) and len(s2):
        pos2 = int((s2 <= r[inv]).sum())
        print(f"""
   {meta.rotulo} é "{meta.sentido}": provisão alta frente ao atraso é BOM.
   Se entrasse direto, quem provisiona bem pontuaria alto em risco -- o oposto.

   valor da instituição : {catalogo.formata(inv, r[inv])}
   posição no grupo     : {pos2}ª de {len(s2)}  ->  percentil bruto {pos2/len(s2):.3f}
   entra no score como  : 1 - {pos2/len(s2):.3f} = {1 - pos2/len(s2):.3f}
   percentil na base    : {r[f'pct_{inv}']:.3f}
""")
    print("   Dos 18 indicadores, 3 são invertidos: cobertura de provisões,")
    print("   provisão ÷ carteira e folga de capital. Os outros 15 entram direto.")

    # ---------------------------------------------------------------- os 3 scores
    secao("4) DOS PERCENTIS AO SCORE DE CADA PERGUNTA")
    rot = {"crescimento": "P1", "concentracao": "P2", "deterioracao": "P3"}
    for eixo in EIXOS:
        cols = comp[eixo]
        print(f"\n   {rot[eixo]} · {eixo.upper()}  ({len(cols)} indicadores pontuam)")
        pcts = []
        for c in cols:
            p = r.get(f"pct_{c}")
            inv_txt = " (invertido)" if catalogo.POR_CHAVE[c].sentido == "menor_pior" else ""
            if pd.isna(p):
                print(f"      {catalogo.rotulo(c):32s} {'sem dado':>10s}   "
                      f"-> não entra na média")
            else:
                pcts.append(p)
                print(f"      {catalogo.rotulo(c):32s} "
                      f"{catalogo.formata(c, r.get(c)):>10s}   percentil {p:.3f}{inv_txt}")
        if pcts:
            print(f"      {'':32s} {'':>10s}   média de {len(pcts)}: "
                  f"({' + '.join(f'{p:.3f}' for p in pcts)}) / {len(pcts)}")
            print(f"      score do eixo = {np.mean(pcts):.3f}   "
                  f"(na base: {r[f'score_{eixo}']:.3f})  "
                  f"-> {'RISCO ALTO' if r[f'score_{eixo}'] >= CORTE_ALTO else 'não sinalizada'}")

    # ---------------------------------------------------------------- score final
    secao("5) O SCORE FINAL — como os três se combinam")
    partes = []
    for e in EIXOS:
        v = r[f"score_{e}"]
        if pd.notna(v):
            partes.append(f"{v:.3f} × {PESOS_PADRAO[e]:.2f}")
    print(f"\n   score final = ({' + '.join(partes)}) / "
          f"{sum(PESOS_PADRAO[e] for e in EIXOS if pd.notna(r[f'score_{e}'])):.2f}")
    print(f"               = {r['score_final']:.3f}")
    print(f"\n   limiar da agenda: 0,65  ->  "
          f"{'ENTRA na agenda' if r['score_final'] >= 0.65 else 'fica fora da agenda'}")
    print("""
   Os pesos (0,30 / 0,25 / 0,45) refletem o encadeamento do trabalho:
   P1 filtra, P2 qualifica, P3 prioriza -- por isso deterioração pesa mais.
   Eixo sem dado nenhum sai da conta e reduz o divisor, em vez de virar zero.
""")


if __name__ == "__main__":
    main()
