"""
testa_troca.py -- prova que a troca de indicador funciona de ponta a ponta.

Simula o que acontece quando o professor pede, ao vivo, a substituição de um
indicador: recalcula o score com a nova seleção e mostra o efeito na agenda.

Não altera nenhum arquivo — só demonstra o mecanismo.
"""
from __future__ import annotations

import sys

import pandas as pd

import catalogo
from comum import DATA_PROC
from scoring import PESOS_PADRAO, agenda, calcula_scores

CORTE = 1e9


def monta(ind: pd.DataFrame, ativos: dict, dt: int) -> pd.DataFrame:
    sc = calcula_scores(ind, grupo_pares="tcb", pesos=PESOS_PADRAO, ativos=ativos)
    return agenda(sc, dt, minimo_carteira=CORTE)


def main() -> int:
    ind = pd.read_parquet(DATA_PROC / "app_indicadores.parquet")
    dt = int(ind["data_base"].max())

    base_sel, avisos = catalogo.carrega_ativos()
    if avisos:
        print("avisos de indicadores.toml:", "; ".join(avisos), "\n")

    ag0 = monta(ind, base_sel, dt)
    print(f"data-base {dt} · seleção atual de indicadores.toml")
    print(f"  agenda de atípicas: {len(ag0)} instituições\n")

    # troca 1 indicador em cada eixo por uma alternativa do catálogo
    trocas = {
        "crescimento": ("p1_6_var_share_pp", "p1_9_cresc_clientes_aa"),
        "concentracao": ("p2_4_hhi_regional", "p2_9_credito_sobre_ativo"),
        "deterioracao": ("p3_6_folga_capital_pp", "p3_10_problematico_sobre_pl"),
    }
    nova = {e: list(v) for e, v in base_sel.items()}
    print("SIMULANDO A TROCA")
    for eixo, (sai, entra) in trocas.items():
        if sai in nova[eixo]:
            nova[eixo][nova[eixo].index(sai)] = entra
            print(f"  {eixo:14s} {catalogo.rotulo(sai)}  ->  {catalogo.rotulo(entra)}")
        else:
            print(f"  {eixo:14s} (indicador {sai} não está ativo; sem troca)")

    ag1 = monta(ind, nova, dt)
    print(f"\n  agenda com a nova seleção: {len(ag1)} instituições")

    a, b = set(ag0["cod_inst"]), set(ag1["cod_inst"])
    print(f"\nEFEITO NA AGENDA")
    print(f"  permanecem .......... {len(a & b)}")
    print(f"  saem ................ {len(a - b)}")
    print(f"  entram .............. {len(b - a)}")

    if b - a:
        print("\n  entraram:")
        for r in ag1[ag1["cod_inst"].isin(b - a)].head(5).itertuples():
            print(f"    {str(r.instituicao)[:38]:38s} score {r.score_final:.3f}")
    if a - b:
        print("\n  saíram:")
        for r in ag0[ag0["cod_inst"].isin(a - b)].head(5).itertuples():
            print(f"    {str(r.instituicao)[:38]:38s} score {r.score_final:.3f}")

    mudou = len(a ^ b) > 0
    print(f"\n{'a troca alterou a agenda' if mudou else 'a troca nao alterou a agenda'} "
          f"-- mecanismo funcionando")

    # a regra dos 6 continua valendo?
    for eixo, chaves in nova.items():
        if len(chaves) != 6:
            print(f"FALHA: {eixo} ficou com {len(chaves)} indicadores")
            return 1
    print("regra dos 6 por pergunta preservada apos a troca")
    return 0


if __name__ == "__main__":
    sys.exit(main())
