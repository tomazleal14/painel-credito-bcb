"""
checa_grupos.py -- trava o agrupamento por sistema cooperativo.

O agrupamento e a unica peca do painel cujo vinculo NAO vem do IF.data: ele e
deduzido do nome publicado. Por isso precisa de um teste que garanta as duas
promessas feitas no Caderno de Processo:

  1. o agrupamento e so de APRESENTACAO -- nenhum indicador, percentil ou score
     muda por causa dele;
  2. o perimetro e so de cooperativas, e nenhuma instituicao cai em dois
     sistemas.

Tambem exporta verificacao/grupos_cooperativos.csv, a lista de filiacao que
sustenta cada linha "SISTEMA X" da tela.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

import catalogo  # noqa: E402
import grupos  # noqa: E402
from comum import DATA_PROC  # noqa: E402
from scoring import PESOS_PADRAO, agenda, calcula_scores  # noqa: E402

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = RAIZ / "verificacao" / "grupos_cooperativos.csv"
falhas: list[str] = []


def exige(ok: bool, msg: str) -> None:
    print(f"  {'OK  ' if ok else 'FALHA'}  {msg}")
    if not ok:
        falhas.append(msg)


def main() -> None:
    d = pd.read_parquet(DATA_PROC / "app_indicadores.parquet")
    d["grupo"] = grupos.atribui(d)

    print("== perimetro ==")
    fora = d[(d["grupo"] != "") & (~d["tcb"].isin(grupos.TCB_COOPERATIVO))]
    exige(fora.empty,
          f"so cooperativas recebem sistema (fora do perimetro: {len(fora)})")

    # Trocar de sistema ao longo da serie e legitimo -- sao filiacoes que mudaram
    # de verdade, e o IF.data renomeia a instituicao quando isso acontece. O que
    # nao pode e uma migrante ser grande o bastante para entrar no recorte: ali
    # ela apareceria sob dois sistemas em trimestres diferentes, sem explicacao.
    mig = grupos.migracoes(d)
    codigos = mig["cod_inst"].nunique() if not mig.empty else 0
    grandes = mig[mig["carteira_credito_real"] >= 1e9] if not mig.empty else mig
    print(f"        ({codigos} cooperativas trocaram de sistema no periodo)")
    for r in mig.itertuples():
        print(f"          {r.data_base} [{r.grupo:9s}] {str(r.instituicao)[:58]}")
    exige(grandes.empty,
          f"nenhuma migrante alcanca o recorte de R$ 1 bi ({len(grandes)} alcancam)")

    print("\n== o agrupamento nao altera numero nenhum ==")
    ativos, _ = catalogo.carrega_ativos()
    sem = calcula_scores(d.drop(columns=["grupo"]), grupo_pares="tcb",
                         pesos=PESOS_PADRAO, ativos=ativos)
    com = calcula_scores(d, grupo_pares="tcb", pesos=PESOS_PADRAO, ativos=ativos)
    num = [c for c in sem.columns if pd.api.types.is_numeric_dtype(sem[c])]
    iguais = all(sem[c].equals(com[c]) for c in num)
    exige(iguais, f"as {len(num)} colunas numericas sao identicas com e sem a coluna grupo")

    print("\n== colapso da agenda ==")
    for dt in sorted(d["data_base"].unique())[-4:]:
        ag = agenda(com, int(dt), minimo_carteira=1e9, limiar=0.65)
        univ = com[(com["data_base"] == dt) & (com["carteira_credito_real"] >= 1e9)]
        col = grupos.colapsa(ag, univ)
        # o colapso nao pode PERDER instituicao: cada linha de sistema tem de
        # responder por todas as sinalizadas dele
        soma = int(col["n_sinalizadas"].sum())
        exige(soma == len(ag),
              f"{dt}: {len(ag)} sinalizadas -> {len(col)} linhas, "
              f"somando {soma} membros")
        piores = col[col["linha_tipo"] == "sistema"]
        exige(bool((piores["n_recorte"] >= piores["n_sinalizadas"]).all()),
              f"{dt}: denominador do sistema nunca menor que o numerador")

    print("\n== razoes do conjunto na linha de sistema ==")
    # Uma razao de somas e media PONDERADA das razoes dos membros: tem de cair
    # entre o menor e o maior valor individual. Se sair fora, o numerador e o
    # denominador nao vieram do mesmo conjunto -- que e exatamente o erro que a
    # regra de "todos os membros presentes" existe para impedir.
    PARES = (("agg_cresc", "p1_1_cresc_real_aa"),
             ("agg_inadimplencia", "p3_1_inadimplencia"),
             ("agg_cobertura", "p3_2_cobertura"))
    for dt in sorted(d["data_base"].unique())[-4:]:
        ag = agenda(com, int(dt), minimo_carteira=1e9, limiar=0.65)
        univ = com[(com["data_base"] == dt) & (com["carteira_credito_real"] >= 1e9)]
        col = grupos.colapsa(ag, univ, hist=com)
        for r in col[col["linha_tipo"] == "sistema"].itertuples():
            membros = grupos.membros(ag, r.grupo)
            for campo, individual in PARES:
                v = getattr(r, campo)
                if v is None or pd.isna(v):
                    continue
                lo, hi = membros[individual].min(), membros[individual].max()
                exige(bool(lo - 1e-9 <= v <= hi + 1e-9),
                      f"{dt} {r.grupo}: {campo} {v:.4f} dentro de "
                      f"[{lo:.4f}, {hi:.4f}] dos membros")
            # Basileia e a unica que NAO pode ser agregada
            exige(not hasattr(r, "agg_basileia"),
                  f"{dt} {r.grupo}: Basileia nao e agregada")

    print("\n== cobertura da regra ==")
    cob = grupos.cobertura(d)
    tot = int(cob["cooperativas"].sum())
    com_marca = int(cob[cob["grupo"] != "(sem marca no nome)"]["cooperativas"].sum())
    print(cob.to_string(index=False))
    print(f"  -> {com_marca} de {tot} cooperativas com marca ({com_marca/tot*100:.0f}%)")

    coop = d[d["tcb"].isin(grupos.TCB_COOPERATIVO)]
    export = (coop.sort_values("data_base")
                  .drop_duplicates("cod_inst", keep="last")
                  [["cod_inst", "instituicao", "tcb", "uf", "grupo",
                    "data_base", "carteira_credito_real"]]
                  .rename(columns={"grupo": "sistema_atribuido",
                                   "data_base": "ultimo_trimestre",
                                   "carteira_credito_real": "carteira_real"})
                  .sort_values(["sistema_atribuido", "carteira_real"],
                               ascending=[True, False]))
    export["sistema_atribuido"] = export["sistema_atribuido"].replace(
        "", "(sem marca no nome - segue individual)")
    DESTINO.parent.mkdir(exist_ok=True)
    export.to_csv(DESTINO, index=False, encoding="utf-8-sig")
    print(f"\nlista de filiacao: {DESTINO.relative_to(RAIZ)} ({len(export)} cooperativas)")

    print("\n" + ("TUDO OK" if not falhas else f"{len(falhas)} FALHA(S)"))
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
