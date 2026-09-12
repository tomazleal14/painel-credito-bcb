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


# --------------------------------------------------------------------------- quebra
# A Res. CMN 4.966/2021 trocou a conta do Resumo em 202503: "Carteira de Credito
# Classificada" (ate 202412) passou a "Carteira de Credito". Nao e so nome -- e outra
# medida. Verificado no PROPRIO painel prudencial, universo constante:
#     ITAU  202412 R$ 1.088,0 bi  ->  202503 R$ 1.187,8 bi   (+9,2% em UM trimestre)
#     universo                    +1,1% no mesmo trimestre
# Um degrau de nivel desses contamina toda comparacao de 12 meses que o atravesse, e
# por isso a "carteira exposta" de P1 saltou para 40% entre 202503 e 202512, com Itau,
# Bradesco e BNDES aparecendo como risco alto de crescimento.
#
# Regra adotada: indicador que compara t com t-4 fica VAZIO quando a janela cruza a
# quebra. Perde-se um ano de P1 (4 trimestres), mas o alternativo seria publicar
# crescimento inventado pela mudanca contabil. 202603 em diante ja e limpo.
QUEBRA_DEFINICAO = 202503
TRIMESTRES_CONTAMINADOS = (202503, 202506, 202509, 202512)


def _mascara_quebra(datas: pd.Series) -> pd.Series:
    """True onde a janela de 12 meses cruza a mudanca de definicao da carteira."""
    return datas.isin(TRIMESTRES_CONTAMINADOS)


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

    # ANULA A QUEBRA ANTES DE DERIVAR QUALQUER COISA DELA.
    # A mascara geral roda no fim de calcula(), o que basta para os indicadores que sao
    # eles proprios uma razao t/t-4. Nao basta para os que se APOIAM no crescimento:
    #   - p1_3 conta trimestres seguidos acima de 15%. Rodando sobre o crescimento
    #     contaminado, a sequencia atravessava 2025 e chegava a 2026Q1 inflada: o maximo
    #     do recorte ia de 20 trimestres em 202412 para 25 em 202603, somando os quatro
    #     trimestres que o painel declara nao saber medir.
    #   - p1_11 e cresc(t) - cresc(t-4); em 202603 o t-4 e 202503, que nao existe.
    # Mascarar aqui faz a sequencia REINICIAR na lacuna e p1_11 nascer vazio, que e a
    # leitura honesta: nao da para contar uma sequencia atraves de um buraco.
    _contaminadas = _mascara_quebra(df["data_base"])
    for _c in ("p1_1_cresc_real_aa", "p1_2_credit_gap",
               "p1_4_cresc_carteira_sobre_capital", "p1_6_var_share_pp"):
        if _c in df.columns:
            df.loc[_contaminadas, _c] = np.nan

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

    # COMPOSICAO do funding, e nao o nivel dele.
    # p2_6 (carteira / captacoes) NAO distingue funding estavel de volatil: a conta
    # "Captacoes" do Resumo agrega [4.1] depositos + [4.2] compromissadas + [4.3]
    # aceites e emissao de titulos + [4.6] emprestimos e repasses, ou seja, CDB e Letra
    # Financeira ja estao no denominador. E LF tem prazo minimo de dois anos SEM resgate
    # antecipado -- e mais estavel que deposito a vista, nao menos.
    # Este indicador mede a fatia do funding que pode ser sacada a qualquer momento:
    # deposito a vista e poupanca. E um PISO, nao o total: CDB com liquidez diaria
    # tambem e resgatavel de imediato, e o relatorio Passivo nao abre prazo de resgate.
    _imediato = df[[c for c in ("dep_vista_real", "dep_poupanca_real")
                    if c in df.columns]].sum(axis=1, min_count=1)
    df["p2_13_dep_imediato_pct"] = (_imediato
                                    / df["captacoes_real"].where(df["captacoes_real"] > 0))

    # ---- GUARDA DE TICKET para P2 nº 3 (carteira PF em alto risco) -------------
    # p2_3 usa a MODALIDADE como proxy de risco, e a proxy e calibrada para VAREJO:
    # "emprestimo sem consignacao em folha" e caro e inadimplente quando o tomador e
    # pessoa fisica de varejo. Fora do varejo a mesma rubrica abriga outra coisa.
    #
    # Caso que revelou o problema: a UBS (Brasil) marcava 100% de "carteira PF em alto
    # risco" com 72 clientes, ticket medio de R$ 45,2 milhoes e inadimplencia de 0,00%.
    # Aquilo e credito lombard -- colateralizado pela carteira de investimentos do
    # cliente --, que o IF.data nao tem modalidade para registrar. O indicador invertia
    # o sinal: marcava risco alto onde o risco e o mais baixo do recorte.
    #
    # Regra: acima do p90 do ticket medio do recorte padrao (carteira >= R$ 1 bi), no
    # proprio trimestre, a proxy nao se aplica e o campo fica VAZIO -- em vez de entrar
    # no score com o sinal trocado. E a mesma regra do resto do painel: o que nao e
    # medivel nao vira numero.
    #
    # Trade-off assumido: um quantil mascara ~10% por construcao, inclusive instituicoes
    # em que a proxy seria valida. Verificado em 03/2026: das 26 acima do p90, todas sao
    # bancos de atacado ou de investimento (Scotiabank, Credit Agricole, MUFG, Mizuho,
    # JP Morgan, BofA, Citibank, Deutsche, UBS...), e so 15 tinham p2_3 para perder.
    # Um limiar absoluto seria mais estavel no tempo -- o p90 vai de R$ 27,3 milhoes em
    # 2019 a R$ 989 mil em 2026, porque o recorte dobra de tamanho --, mas seria fixado
    # por arbitrio nosso em vez de pela distribuicao observada.
    Q_TICKET = 0.90
    CORTE_RECORTE = 1e9
    _lim = (df[df["carteira_credito_real"] >= CORTE_RECORTE]
            .groupby("data_base")["ctx_ticket_medio_real"].quantile(Q_TICKET))
    df["ctx_ticket_limiar_real"] = df["data_base"].map(_lim)
    _atacado = (df["ctx_ticket_medio_real"] > df["ctx_ticket_limiar_real"]).fillna(False)
    df["ctx_ticket_acima_p90"] = _atacado
    _perdidos = int((_atacado & df["p2_3_pct_alto_risco"].notna()).sum())
    df.loc[_atacado, "p2_3_pct_alto_risco"] = np.nan
    print(f"  guarda de ticket em p2_3: {int(_atacado.sum())} linhas acima do p90 do "
          f"recorte, {_perdidos} tinham o indicador e ficaram vazias")

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

    # ------------- ALTERNATIVAS DO CATALOGO (disponiveis para troca ao vivo) -------------
    # Sao calculadas SEMPRE, mesmo sem estarem entre os 6 ativos de cada pergunta: e o que
    # permite trocar um indicador por outro na barra lateral sem recalcular a base.
    # Ver src/catalogo.py para a ficha de cada um.
    df = df.sort_values(["cod_inst", "data_base"]).reset_index(drop=True)
    gg = df.groupby("cod_inst", group_keys=False)

    def _yoy(col: str):
        if col not in df.columns:
            return np.nan
        return gg[col].apply(_var_anual)

    # --- P1 ---
    df["p1_7_cresc_ativo_aa"] = _yoy("ativo_total_real")
    df["p1_8_cresc_captacoes_aa"] = _yoy("captacoes_real")
    df["p1_9_cresc_clientes_aa"] = _yoy("qtd_clientes")
    df["p1_10_cresc_pj_aa"] = _yoy("pj_total_real")
    df["p1_11_aceleracao_pp"] = gg["p1_1_cresc_real_aa"].apply(
        lambda s: s - s.shift(TRIM_POR_ANO))
    df["_ticket"] = (df["carteira_credito_real"]
                     / df["qtd_clientes"].where(df["qtd_clientes"] > 0))
    df["p1_12_cresc_ticket_aa"] = gg["_ticket"].apply(_var_anual)

    # --- P2 ---
    cols_pf = [c for c in ["pf_cartao_real", "pf_sem_consignacao_real", "pf_consignado_real",
                           "pf_veiculos_real", "pf_habitacao_real", "pf_rural_real",
                           "pf_outros_real"] if c in df.columns]
    df["p2_7_hhi_modalidade_pf"] = _hhi_linhas(df, cols_pf) if cols_pf else np.nan
    if cols_reg:
        soma_reg = df[cols_reg].sum(axis=1, min_count=1)
        df["p2_8_max_regiao_pct"] = (df[cols_reg].max(axis=1)
                                     / soma_reg.where(soma_reg > 0))
    else:
        df["p2_8_max_regiao_pct"] = np.nan
    df["p2_9_credito_sobre_ativo"] = (df["carteira_credito_real"]
                                      / df["ativo_total_real"].where(
                                          df["ativo_total_real"] > 0))
    df["p2_10_ticket_medio"] = df["_ticket"]
    df["p2_11_pct_capital_giro"] = (df.get("pj_capital_giro_real")
                                    / df["pj_total_real"].where(df["pj_total_real"] > 0)
                                    if "pj_capital_giro_real" in df.columns else np.nan)
    cols_porte = [c for c in ["pj_porte_micro_real", "pj_porte_pequena_real",
                              "pj_porte_media_real", "pj_porte_grande_real"]
                  if c in df.columns]
    df["p2_12_hhi_porte_pj"] = _hhi_linhas(df, cols_porte) if cols_porte else np.nan

    # --- P3 ---
    df["p3_7_folga_capital_principal_pp"] = (df["indice_capital_principal"] * 100 - 7.0
                                             if "indice_capital_principal" in df.columns
                                             else np.nan)
    df["p3_8_razao_alavancagem"] = df.get("razao_alavancagem", np.nan)
    df["p3_9_gap_problematico_pp"] = (df["p3_5_ativos_problematicos"]
                                      - df["p3_1_inadimplencia"])
    df["p3_10_problematico_sobre_pl"] = (df["ativos_problematicos_valor_real"]
                                         / df["patrimonio_liquido_real"].where(
                                             df["patrimonio_liquido_real"] > 0))
    df["p3_11_var_inadimplencia_pp"] = gg["p3_1_inadimplencia"].apply(
        lambda s: s - s.shift(TRIM_POR_ANO))
    df["p3_12_retorno_sobre_pl"] = (df["lucro_liquido_real"]
                                    / df["patrimonio_liquido_real"].where(
                                        df["patrimonio_liquido_real"] > 0))

    # ---- anula o que atravessa a quebra de definicao da carteira (ver QUEBRA_DEFINICAO) ----
    contaminadas = _mascara_quebra(df["data_base"])
    COMPARAM_COM_T4 = [
        # o credit gap nao compara com t-4, mas tambem nao sobrevive a quebra: o filtro
        # HP e ajustado sobre o NIVEL da carteira, e o degrau de definicao entra na
        # tendencia estimada. Sem isto, P1 exibia dado em 2025 contradizendo a propria
        # justificativa de que a janela esta contaminada.
        "p1_2_credit_gap",
        "p1_1_cresc_real_aa", "p1_3_trim_consec_acima",
        "p1_4_cresc_carteira_sobre_capital", "p1_5_cresc_alto_risco_aa",
        "p1_6_var_share_pp", "p1_7_cresc_ativo_aa", "p1_8_cresc_captacoes_aa",
        "p1_9_cresc_clientes_aa", "p1_10_cresc_pj_aa", "p1_11_aceleracao_pp",
        "p1_12_cresc_ticket_aa", "p3_4_inadimplencia_ajustada",
        "p3_11_var_inadimplencia_pp",
    ]
    for c in COMPARAM_COM_T4:
        if c in df.columns:
            df.loc[contaminadas, c] = np.nan
    print(f"  quebra Res. 4.966: {int(contaminadas.sum())} linhas em "
          f"{list(TRIMESTRES_CONTAMINADOS)} tiveram os {len(COMPARAM_COM_T4)} indicadores "
          f"de comparacao anual anulados")

    df = df.drop(columns=[c for c in ["_alto_risco_real", "_atraso_real", "_provisao_real",
                                      "_niveis_eh_real", "_carteira_defasada", "_ticket"]
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
