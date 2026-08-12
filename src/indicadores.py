"""
indicadores.py -- calcula os 18 indicadores (6 por pergunta) a partir dos paineis
processados. Sem nenhum numero digitado a mao: tudo deriva de data_processed/.

Ver verificacao/01_mapa_indicadores.md para a origem campo a campo.

Saida: data_processed/indicadores.parquet  (uma linha por data_base x instituicao)
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.filters.hp_filter import hpfilter

from comum import DATA_PROC, agora_utc

LIMIAR_BOOM = 0.15        # 15% a.a. real -- limiar de "crescimento acelerado"
TRIM_POR_ANO = 4
MIN_TRIM_HP = 12          # minimo de trimestres para rodar o filtro HP
LAMBDA_HP = 1600          # padrao para serie trimestral
BASILEIA_MINIMA = 10.5    # 8% + conservacao 2,5% (adicionais podem elevar)


def _var_anual(s: pd.Series) -> pd.Series:
    return s / s.shift(TRIM_POR_ANO) - 1


def _credit_gap(s: pd.Series) -> pd.Series:
    """Desvio % da tendencia HP. Exige serie suficientemente longa e positiva."""
    v = s.dropna()
    if len(v) < MIN_TRIM_HP or (v <= 0).any():
        return pd.Series(np.nan, index=s.index)
    ciclo, tendencia = hpfilter(np.log(v), lamb=LAMBDA_HP)
    gap = pd.Series(np.nan, index=s.index)
    gap.loc[v.index] = ciclo  # em log -> aproxima desvio proporcional
    return gap


def _sequencia_acima(flag: pd.Series) -> pd.Series:
    """Conta trimestres consecutivos com flag=True ate cada ponto."""
    grupo = (~flag.fillna(False)).cumsum()
    return flag.fillna(False).groupby(grupo).cumsum()


def _hhi_linhas(df: pd.DataFrame, cols: list[str]) -> pd.Series:
    """HHI (0-10.000) entre as colunas de cada linha -- usado para regioes."""
    m = df[cols].astype(float)
    total = m.sum(axis=1)
    shares = m.div(total.where(total > 0), axis=0)
    return (shares.pow(2).sum(axis=1) * 10_000).where(total > 0)


def _colunas_crescimento(painel: pd.DataFrame) -> pd.DataFrame:
    """Colunas que dependem de comparacao com t-4, calculadas DENTRO de um unico universo.

    Por que isto existe: o codigo da instituicao (`cod_inst`) NAO e o mesmo nos universos
    1005 (ate 202412) e 1009 (2025+). O painel `longo` emenda os dois, entao qualquer
    variacao anual que cruze 202412->202503 compara codigos diferentes e volta vazia --
    na pratica, o crescimento de 2025 so existia para as IFs cujo codigo por acaso nao
    mudou (149 de 257). Calculando dentro de cada universo separadamente e depois
    combinando, o crescimento fica correto dos dois lados da quebra.
    """
    p = painel.sort_values(["cod_inst", "data_base"]).copy()
    g = p.groupby("cod_inst", group_keys=False)

    fora = pd.DataFrame(index=p.index)
    fora["data_base"] = p["data_base"]
    fora["cod_inst"] = p["cod_inst"]
    fora["p1_1_cresc_real_aa"] = g["carteira_credito_real"].apply(_var_anual)
    fora["p1_2_credit_gap"] = g["carteira_credito_real"].apply(_credit_gap)

    if "pr_real" in p.columns:
        cresc_pr = g["pr_real"].apply(_var_anual)
        fora["p1_4_cresc_carteira_sobre_capital"] = (
            (1 + fora["p1_1_cresc_real_aa"]) / (1 + cresc_pr).replace(0, np.nan))

    total = p.groupby("data_base")["carteira_credito_real"].transform("sum")
    share = p["carteira_credito_real"] / total
    fora["share_carteira"] = share
    fora["p1_6_var_share_pp"] = (p.assign(_s=share).groupby("cod_inst")["_s"]
                                 .transform(lambda s: (s - s.shift(TRIM_POR_ANO)) * 100))
    fora["_carteira_defasada"] = g["carteira_credito_real"].apply(
        lambda s: s.shift(TRIM_POR_ANO))
    return fora


def calcula() -> pd.DataFrame:
    longo = pd.read_parquet(DATA_PROC / "painel_ifdata_longo.parquet")
    prud = pd.read_parquet(DATA_PROC / "painel_ifdata_prudencial.parquet")

    # capital vem do universo prudencial (unico com Informacoes de Capital)
    cap = prud[["data_base", "cod_inst", "pr_real", "rwa_real", "indice_basileia",
                "indice_capital_principal", "razao_alavancagem",
                "inadimplencia_valor_real", "ativos_problematicos_valor_real",
                "perda_esperada_real"]].copy()

    df = longo.merge(cap, on=["data_base", "cod_inst"], how="left", suffixes=("", "_prud"))
    for c in ["inadimplencia_valor_real", "ativos_problematicos_valor_real", "perda_esperada_real"]:
        if f"{c}_prud" in df.columns:
            df[c] = df[c].fillna(df[f"{c}_prud"])
            df = df.drop(columns=[f"{c}_prud"])

    df = df.sort_values(["cod_inst", "data_base"]).reset_index(drop=True)
    g = df.groupby("cod_inst", group_keys=False)

    # ---------------- P1 ----------------
    # crescimento calculado dentro de cada universo e depois combinado (ver _colunas_crescimento).
    # O universo prudencial (1009, codigos estaveis desde 202309) preenche o que a emenda
    # 1005->1009 do painel longo deixa vazio na virada 202412->202503.
    cres_longo = _colunas_crescimento(longo)
    cres_prud = _colunas_crescimento(prud)
    cres = (cres_longo.set_index(["data_base", "cod_inst"])
            .combine_first(cres_prud.set_index(["data_base", "cod_inst"])))
    # onde o longo nao conseguiu (codigo mudou na quebra), usa o prudencial
    cres = cres.fillna(cres_prud.set_index(["data_base", "cod_inst"]))
    df = df.merge(cres.reset_index(), on=["data_base", "cod_inst"], how="left")

    acima = df["p1_1_cresc_real_aa"] >= LIMIAR_BOOM
    df["p1_3_trim_consec_acima"] = (df.assign(_a=acima)
                                      .sort_values(["cod_inst", "data_base"])
                                      .groupby("cod_inst")["_a"]
                                      .transform(lambda s: _sequencia_acima(s)))
    df["_alto_risco_real"] = df[["pf_cartao_real", "pf_sem_consignacao_real"]].sum(
        axis=1, min_count=1)
    df["p1_5_cresc_alto_risco_aa"] = (df.sort_values(["cod_inst", "data_base"])
                                        .groupby("cod_inst", group_keys=False)["_alto_risco_real"]
                                        .apply(_var_anual))

    # ---------------- P2 ----------------
    # HHI e CR5 sao do SISTEMA (um numero por trimestre), replicados em cada linha
    hhi = (df.groupby("data_base")["share_carteira"]
             .transform(lambda s: (s.pow(2).sum()) * 10_000))
    df["p2_1_hhi_sistema"] = hhi
    cr5 = (df.groupby("data_base")["share_carteira"]
             .transform(lambda s: s.nlargest(5).sum() * 100))
    df["p2_2_cr5_sistema_pct"] = cr5

    df["p2_3_pct_alto_risco"] = (df["_alto_risco_real"]
                                 / df["pf_total_real"].where(df["pf_total_real"] > 0))
    cols_reg = ["reg_sudeste_real", "reg_sul_real", "reg_nordeste_real",
                "reg_norte_real", "reg_centro_oeste_real"]
    cols_reg = [c for c in cols_reg if c in df.columns]
    df["p2_4_hhi_regional"] = _hhi_linhas(df, cols_reg) if cols_reg else np.nan
    # P2 nº 5 -- exposicao a tomadores de GRANDE PORTE, com fonte direta por instituicao
    # (IF.data, "Carteira de credito ativa PJ - por porte do tomador").
    # Substituiu a proxy de ticket medio: aquela dividia carteira por nº de clientes e
    # media granularidade media, NAO exposicao a grandes tomadores.
    # Denominador: o total de PJ do PROPRIO relatorio, para nao cruzar recortes.
    base_pj = df["pj_total_porte_real"].where(df["pj_total_porte_real"] > 0)
    df["p2_5_pct_grande_porte"] = df["pj_porte_grande_real"] / base_pj
    # ticket medio segue calculado como CONTEXTO descritivo (nao entra no score)
    df["ctx_ticket_medio_real"] = (df["carteira_credito_real"]
                                   / df["qtd_clientes"].where(df["qtd_clientes"] > 0))
    df["p2_6_loan_to_deposit"] = (df["carteira_credito_real"]
                                  / df["captacoes_real"].where(df["captacoes_real"] > 0))

    # ---------------- P3 ----------------
    # ATENCAO -- as duas metricas de qualidade NAO sao a mesma coisa e NAO se encadeiam.
    # Validacao cruzada (src/valida_cruzada.py) contra o SGS 21082:
    #   regime ECL (2025+): "Inadimplencia" do IF.data fica a ~0,3-0,4 p.p. do SGS  -> comparavel
    #   regime AA-H (<=2024): a soma dos niveis E..H fica ~2,5 p.p. ACIMA do SGS    -> NAO comparavel
    # Motivo: E..H e classificacao de risco, nao atraso acima de 90 dias. Por isso a serie
    # AA-H vive numa coluna PROPRIA, rotulada como "carteira em niveis E-H", e nunca preenche
    # a lacuna da inadimplencia 90+.
    df["_atraso_real"] = df["inadimplencia_valor_real"]          # so regime ECL (2025+)
    df["_niveis_eh_real"] = (df[["risco_e_real", "risco_f_real", "risco_g_real", "risco_h_real"]]
                             .sum(axis=1, min_count=1)
                             if "risco_h_real" in df.columns else np.nan)
    # Provisao / perda esperada sao contas RETIFICADORAS do ativo no COSIF: o saldo
    # publicado e NEGATIVO (verificado em src/checa_sinais.py -- 26.129 valores negativos,
    # nenhum positivo). Sem o valor absoluto, cobertura e provisao/carteira saem negativas.
    # Inadimplencia e ativos problematicos ja vem positivos e NAO levam abs().
    df["_provisao_real"] = (df["perda_esperada_real"]
                            .fillna(df.get("provisao_antiga_real"))
                            .abs())

    carteira_pos = df["carteira_credito_real"].where(df["carteira_credito_real"] > 0)
    df["p3_1_inadimplencia"] = df["_atraso_real"] / carteira_pos          # 90+ , 2025+
    df["p3_1b_niveis_eh"] = df["_niveis_eh_real"] / carteira_pos          # AA-H , ate 2024
    # cobertura no regime ECL usa o atraso 90+; no regime AA-H usa a carteira E-H
    base_cobertura = df["_atraso_real"].fillna(df["_niveis_eh_real"])
    df["p3_2_cobertura"] = df["_provisao_real"] / base_cobertura.where(base_cobertura > 0)
    df["p3_3_provisao_sobre_carteira"] = (df["_provisao_real"]
                                          / df["carteira_credito_real"].where(
                                              df["carteira_credito_real"] > 0))
    # efeito denominador: atraso de hoje sobre a carteira que o originou (4 trimestres atras)
    carteira_def = df["_carteira_defasada"]
    df["p3_4_inadimplencia_ajustada"] = (df["_atraso_real"]
                                         / carteira_def.where(carteira_def > 0))
    df["p3_5_ativos_problematicos"] = (df["ativos_problematicos_valor_real"]
                                       / df["carteira_credito_real"].where(
                                           df["carteira_credito_real"] > 0))
    df["p3_6_folga_capital_pp"] = df["indice_basileia"] * 100 - BASILEIA_MINIMA

    df = df.drop(columns=[c for c in ["_alto_risco_real", "_atraso_real", "_provisao_real",
                                      "_niveis_eh_real", "_carteira_defasada"]
                          if c in df.columns])

    DATA_PROC.mkdir(parents=True, exist_ok=True)
    df.to_parquet(DATA_PROC / "indicadores.parquet", index=False)
    return df


def relatorio(df: pd.DataFrame) -> None:
    inds = [c for c in df.columns if c[:2] in ("p1", "p2", "p3")]
    ult = df["data_base"].max()
    u = df[df["data_base"] == ult]
    print(f"\nindicadores calculados: {len(inds)} | ultimo trimestre: {ult}")
    print(f"{'indicador':38s} {'preench.':>9s} {'mediana':>12s} {'p90':>12s}")
    for c in sorted(inds):
        s = u[c].replace([np.inf, -np.inf], np.nan).dropna()
        if s.empty:
            print(f"{c:38s} {'0':>9s} {'-':>12s} {'-':>12s}")
            continue
        print(f"{c:38s} {len(s):>9,} {s.median():>12.4f} {s.quantile(0.9):>12.4f}")


if __name__ == "__main__":
    print(f"[{agora_utc()}] calculando indicadores")
    relatorio(calcula())
