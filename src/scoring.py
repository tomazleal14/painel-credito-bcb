"""
scoring.py -- transforma os 18 indicadores numa LISTA PRIORIZADA com semaforo por eixo.

Metodo, explicito de proposito (o supervisor precisa poder discordar do criterio):
  1. Cada indicador vira um PERCENTIL dentro do grupo de pares do mesmo trimestre.
     Percentil, e nao valor absoluto, porque cooperativa singular e banco S1 nao sao
     comparaveis em nivel -- so em posicao relativa.
  2. Indicadores em que "maior = mais risco" entram direto; os de sinal invertido
     (cobertura, folga de capital) entram como 1 - percentil.
  3. Cada eixo (crescimento / concentracao / deterioracao) e a media dos percentis
     disponiveis daquele eixo. Falta de dado NAO conta como zero: reduz o denominador.
  4. Semaforo por eixo: >= 0,75 alto | >= 0,50 medio | < 0,50 baixo.
  5. Score final PONDERADO, seguindo o encadeamento P1 filtra -> P2 qualifica -> P3 prioriza.

O painel deixa os pesos visiveis e ajustaveis: mudar o criterio faz parte da decisao.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# indicador -> (eixo, inverter?)  inverter=True quando MAIOR valor significa MENOS risco
INDICADORES_SCORE = {
    "p1_1_cresc_real_aa":               ("crescimento", False),
    "p1_2_credit_gap":                  ("crescimento", False),
    "p1_3_trim_consec_acima":           ("crescimento", False),
    "p1_4_cresc_carteira_sobre_capital": ("crescimento", False),
    "p1_5_cresc_alto_risco_aa":         ("crescimento", False),
    "p1_6_var_share_pp":                ("crescimento", False),

    "p2_3_pct_alto_risco":              ("concentracao", False),
    "p2_4_hhi_regional":                ("concentracao", False),
    "p2_5_pct_grande_porte":            ("concentracao", False),
    "p2_6_loan_to_deposit":             ("concentracao", False),

    "p3_1_inadimplencia":               ("deterioracao", False),
    "p3_2_cobertura":                   ("deterioracao", True),
    "p3_3_provisao_sobre_carteira":     ("deterioracao", True),
    "p3_4_inadimplencia_ajustada":      ("deterioracao", False),
    "p3_5_ativos_problematicos":        ("deterioracao", False),
    "p3_6_folga_capital_pp":            ("deterioracao", True),
}

EIXOS = ["crescimento", "concentracao", "deterioracao"]
PESOS_PADRAO = {"crescimento": 0.30, "concentracao": 0.25, "deterioracao": 0.45}

CORTE_ALTO = 0.75
CORTE_MEDIO = 0.50


def semaforo(v: float) -> str:
    if pd.isna(v):
        return "sem"
    if v >= CORTE_ALTO:
        return "alto"
    if v >= CORTE_MEDIO:
        return "medio"
    return "baixo"


def calcula_scores(df: pd.DataFrame, grupo_pares: str | None = "tcb",
                   pesos: dict[str, float] | None = None) -> pd.DataFrame:
    """Adiciona percentis, scores por eixo, semaforos e score final.

    `grupo_pares`: coluna que define o grupo de comparacao (None = todo o universo).
    """
    pesos = pesos or PESOS_PADRAO
    d = df.copy()

    chaves = ["data_base"] + ([grupo_pares] if grupo_pares else [])
    for col, (_eixo, inverter) in INDICADORES_SCORE.items():
        if col not in d.columns:
            continue
        s = d[col].replace([np.inf, -np.inf], np.nan)
        pct = s.groupby([d[k] for k in chaves]).rank(pct=True)
        d[f"pct_{col}"] = (1 - pct) if inverter else pct

    for eixo in EIXOS:
        cols = [f"pct_{c}" for c, (e, _) in INDICADORES_SCORE.items()
                if e == eixo and f"pct_{c}" in d.columns]
        # media ignorando ausentes: falta de dado reduz o denominador, nao vira zero
        d[f"score_{eixo}"] = d[cols].mean(axis=1, skipna=True) if cols else np.nan
        d[f"sem_{eixo}"] = d[f"score_{eixo}"].map(semaforo)
        d[f"n_ind_{eixo}"] = d[cols].notna().sum(axis=1) if cols else 0

    partes = [d[f"score_{e}"] * pesos[e] for e in EIXOS]
    pesos_validos = sum(
        (d[f"score_{e}"].notna() * pesos[e]) for e in EIXOS
    ).replace(0, np.nan)
    d["score_final"] = sum(p.fillna(0) for p in partes) / pesos_validos

    d["prioridade"] = d.groupby("data_base")["score_final"].rank(
        ascending=False, method="min")
    return d


def agenda(df: pd.DataFrame, data_base: int, minimo_carteira: float = 1e9,
           n: int = 25) -> pd.DataFrame:
    """Lista priorizada do trimestre, restrita a instituicoes com carteira relevante.

    O corte por tamanho existe porque percentil nao distingue relevancia: uma
    cooperativa com R$ 3 milhoes de carteira pode liderar todos os percentis de
    crescimento sem qualquer consequencia sistemica.
    """
    u = df[(df["data_base"] == data_base)
           & (df["carteira_credito_real"] >= minimo_carteira)].copy()
    u = u.sort_values("score_final", ascending=False).head(n)
    return u
