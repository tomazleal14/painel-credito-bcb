"""
cartoes.py -- cartoes de indicador no padrao do observatorio de referencia:
numero grande, releitura em linguagem simples, delta de tendencia, sparkline e
decomposicao em componentes.

Principio de leitura adotado: o cartao nunca mostra so o numero. Ele mostra o numero,
o que aquele numero QUER DIZER em portugues, contra o que esta sendo comparado, e de
que partes ele e feito. Um valor sozinho nao sustenta decisao de supervisao.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from tema import SEMAFORO, SEMAFORO_SOFT, TEMA, sparkline
from textos import md_html

# como formatar e como narrar cada indicador
# chave -> (rotulo, unidade, fator, casas, sentido)
#   sentido = "maior_pior" | "menor_pior" | "neutro"
FORMATO = {
    "p1_1_cresc_real_aa":               ("Crescimento real da carteira", "% a.a.", 100, 1, "maior_pior"),
    "p1_2_credit_gap":                  ("Credit gap", "%", 100, 1, "maior_pior"),
    "p1_3_trim_consec_acima":           ("Trimestres seguidos > 15%", "trim.", 1, 0, "maior_pior"),
    "p1_4_cresc_carteira_sobre_capital": ("Carteira ÷ capital", "×", 1, 2, "maior_pior"),
    "p1_5_cresc_alto_risco_aa":         ("Crescimento em alto risco", "% a.a.", 100, 1, "maior_pior"),
    "p1_6_var_share_pp":                ("Ganho de market share", "p.p.", 1, 3, "maior_pior"),

    "p2_1_hhi_sistema":                 ("HHI do sistema", "", 1, 0, "maior_pior"),
    "p2_2_cr5_sistema_pct":             ("CR5", "%", 1, 1, "maior_pior"),
    "p2_3_pct_alto_risco":              ("Carteira PF em alto risco", "%", 100, 1, "maior_pior"),
    "p2_4_hhi_regional":                ("HHI regional", "", 1, 0, "maior_pior"),
    "p2_5_pct_grande_porte":            ("Carteira PJ em grande porte", "%", 100, 1, "maior_pior"),
    "p2_6_loan_to_deposit":             ("Carteira ÷ captações", "×", 1, 2, "maior_pior"),

    "p3_1_inadimplencia":               ("Inadimplência", "%", 100, 2, "maior_pior"),
    "p3_2_cobertura":                   ("Cobertura de provisões", "%", 100, 0, "menor_pior"),
    "p3_3_provisao_sobre_carteira":     ("Provisão ÷ carteira", "%", 100, 2, "menor_pior"),
    "p3_4_inadimplencia_ajustada":      ("Inadimplência ajustada", "%", 100, 2, "maior_pior"),
    "p3_5_ativos_problematicos":        ("Ativos problemáticos", "%", 100, 2, "maior_pior"),
    "p3_6_folga_capital_pp":            ("Folga de capital", "p.p.", 1, 1, "menor_pior"),
}

def tabela_glossario(glossario: dict, eixos_indicadores: dict | None = None) -> str:
    """Tabela 'o que cada indicador mede', para o expander da Visao geral.

    Usa OS 18 indicadores do trabalho (6 por pergunta), e nao a decomposicao do score:
    HHI do sistema e CR5 medem o mercado inteiro, nao a instituicao, por isso nao entram
    no percentil de nenhum eixo -- mas continuam sendo dois dos 18 e precisam de verbete.
    """
    eixos_indicadores = eixos_indicadores or INDICADORES_DOS_18
    if not glossario:
        return "<div>glossário indisponível — verifique [glossario_indicadores] em textos.toml</div>"

    titulo_eixo = {"crescimento": "P1 · Crescimento", "concentracao": "P2 · Concentração",
                   "deterioracao": "P3 · Deterioração"}
    linhas = ["<table class='gloss-ind'><tr><th>Indicador</th><th>O que mede</th>"
              "<th>Por que está neste eixo</th><th>Como ler</th></tr>"]
    for eixo, cols in eixos_indicadores.items():
        linhas.append(f"<tr class='sep'><td colspan='4'>{titulo_eixo.get(eixo, eixo)}</td></tr>")
        for c in cols:
            rotulo = FORMATO.get(c, (c,))[0]
            # aqui, ao contrario da dica, o Markdown VIRA HTML (a tabela renderiza)
            bruto = md_html(str(glossario.get(c, "")))
            partes = [" ".join(p.split()) for p in bruto.split("|")]
            partes += [""] * (3 - len(partes))
            cels = "".join(f"<td>{p}</td>" for p in partes[:3])
            linhas.append(f"<tr><td class='nome'>{rotulo}</td>{cels}</tr>")
    linhas.append("</table>")
    return "".join(linhas)


# Decomposicao do SCORE: so indicadores medidos POR INSTITUICAO entram no percentil.
# HHI do sistema e CR5 descrevem o mercado inteiro e sao iguais para todas as
# instituicoes no trimestre -- ranquea-las por eles nao teria sentido.
INDICADORES_POR_EIXO = {
    "crescimento": ["p1_1_cresc_real_aa", "p1_2_credit_gap", "p1_3_trim_consec_acima",
                    "p1_4_cresc_carteira_sobre_capital", "p1_5_cresc_alto_risco_aa",
                    "p1_6_var_share_pp"],
    "concentracao": ["p2_3_pct_alto_risco", "p2_4_hhi_regional",
                     "p2_5_pct_grande_porte", "p2_6_loan_to_deposit"],
    "deterioracao": ["p3_1_inadimplencia", "p3_2_cobertura", "p3_3_provisao_sobre_carteira",
                     "p3_4_inadimplencia_ajustada", "p3_5_ativos_problematicos",
                     "p3_6_folga_capital_pp"],
}

# OS 18 do trabalho (6 por pergunta) -- inclui os dois de sistema, para o glossario.
INDICADORES_DOS_18 = {
    "crescimento": INDICADORES_POR_EIXO["crescimento"],
    "concentracao": ["p2_1_hhi_sistema", "p2_2_cr5_sistema_pct"]
                    + INDICADORES_POR_EIXO["concentracao"],
    "deterioracao": INDICADORES_POR_EIXO["deterioracao"],
}


def num(v: float, casas: int) -> str:
    """Formata no padrao pt-BR: milhar com ponto, decimal com virgula."""
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "—"
    return f"{v:,.{casas}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def _serie_mediana(df: pd.DataFrame, col: str) -> pd.Series:
    """Mediana do universo por trimestre -- a serie que o sparkline desenha."""
    if col not in df.columns:
        return pd.Series(dtype=float)
    return (df.replace([np.inf, -np.inf], np.nan)
              .groupby("data_base")[col].median().dropna().sort_index())


def cartao_indicador(df_hist: pd.DataFrame, df_atual: pd.DataFrame, col: str,
                     nota: str = "", glossario: dict | None = None) -> str:
    """HTML de um cartao de indicador (valor = mediana do universo no trimestre)."""
    rotulo, unidade, fator, casas, sentido = FORMATO.get(
        col, (col, "", 1, 2, "neutro"))
    dica = _dica(glossario, col)

    serie = _serie_mediana(df_hist, col) * fator
    atual = df_atual[col].replace([np.inf, -np.inf], np.nan).dropna() if col in df_atual else pd.Series(dtype=float)
    valor = float(atual.median()) * fator if len(atual) else float("nan")
    n = len(atual)

    # variacao contra 4 trimestres atras (mesma data-base do ano anterior)
    delta_txt, cor_delta = "—", TEMA["texto_3"]
    if len(serie) >= 5:
        d = serie.iloc[-1] - serie.iloc[-5]
        piora = (d > 0) if sentido == "maior_pior" else (d < 0)
        cor_delta = TEMA["risco_alto"] if piora else TEMA["risco_baixo"]
        seta = "▲" if d > 0 else ("▼" if d < 0 else "•")
        delta_txt = f"{seta} {num(abs(d), casas)} em 12 meses"

    cor_linha = TEMA["acento"]
    spark = sparkline(list(serie.values), cor=cor_linha,
                      linha_base=float(serie.median()) if len(serie) else None)

    p10 = float(atual.quantile(0.10)) * fator if n else float("nan")
    p90 = float(atual.quantile(0.90)) * fator if n else float("nan")

    return f"""
    <div class="cartao">
      <div class="cartao-topo"><span class="cartao-rotulo termo"
        {f'title="{dica}"' if dica else ''}>{rotulo}</span></div>
      <div class="cartao-valor">{num(valor, casas)}<span class="unidade"> {unidade}</span></div>
      <div class="cartao-releitura">mediana das {n} instituições do recorte</div>
      <div class="cartao-spark">{spark}</div>
      <div class="cartao-meta" style="color:{cor_delta}">{delta_txt}</div>
      <div class="cartao-comp">
        faixa do universo: <b>{num(p10, casas)}</b> a <b>{num(p90, casas)}</b> {unidade}
        (p10–p90){('<br>' + nota) if nota else ''}
      </div>
    </div>
    """


def _dica(glossario: dict, chave: str) -> str:
    """Texto do atributo title= (dica ao passar o mouse). O glossario guarda
    'o que mede | por que esta neste eixo | como ler'; aqui vira tres linhas."""
    bruto = (glossario or {}).get(chave, "")
    if not bruto:
        return ""
    # o atributo title= nao renderiza HTML: o Markdown do glossario e removido, nao convertido
    bruto = re.sub(r"\*{1,2}([^*]+?)\*{1,2}", r"\1", str(bruto))
    partes = [" ".join(p.split()) for p in bruto.split("|")]
    rotulos = ["O que mede: ", "Por que está aqui: ", "Como ler: "]
    linhas = [r + p for r, p in zip(rotulos, partes) if p]
    texto = "\n".join(linhas)
    # escapa para caber dentro de um atributo HTML
    return (texto.replace("&", "&amp;").replace('"', "&quot;")
                 .replace("<", "&lt;").replace(">", "&gt;")
                 .replace("\n", "&#10;"))


def cartao_eixo(df_hist: pd.DataFrame, df_atual: pd.DataFrame, eixo: str,
                rotulo: str, descricao: str, glossario: dict | None = None) -> str:
    """Cartao de um EIXO (crescimento / concentracao / deterioracao), no padrao
    subindice -> componentes: score do eixo, sparkline e a decomposicao nos
    indicadores que o formam."""
    col_score = f"score_{eixo}"
    col_sem = f"sem_{eixo}"

    serie = _serie_mediana(df_hist, col_score)
    atual = df_atual[col_score].dropna() if col_score in df_atual else pd.Series(dtype=float)
    valor = float(atual.median()) if len(atual) else float("nan")

    # quantas instituicoes estao em risco alto neste eixo
    n_alto = int((df_atual[col_sem] == "alto").sum()) if col_sem in df_atual else 0
    n_tot = int(df_atual[col_sem].isin(["alto", "medio", "baixo"]).sum()) if col_sem in df_atual else 0

    nivel = "alto" if valor >= 0.75 else "medio" if valor >= 0.50 else "baixo"
    cor, soft = SEMAFORO[nivel], SEMAFORO_SOFT[nivel]

    spark = sparkline(list(serie.values), cor=cor,
                      linha_base=0.5 if len(serie) else None)

    delta_txt = ""
    if len(serie) >= 5:
        d = serie.iloc[-1] - serie.iloc[-5]
        seta = "▲" if d > 0 else ("▼" if d < 0 else "•")
        rumo = "subindo" if d > 0.02 else ("cedendo" if d < -0.02 else "estável")
        delta_txt = f"{rumo} · {seta} {num(abs(d), 3)} em 12 meses"

    # decomposicao: os indicadores do eixo, com a mediana de cada um.
    # Cada nome carrega a dica do glossario no title=, para decifrar a sigla sem sair da tela.
    partes = []
    for c in INDICADORES_POR_EIXO.get(eixo, []):
        if c not in df_atual.columns:
            continue
        r, u, f, ca, _s = FORMATO.get(c, (c, "", 1, 2, "neutro"))
        s = df_atual[c].replace([np.inf, -np.inf], np.nan).dropna()
        valor_txt = "—" if s.empty else f"{num(float(s.median()) * f, ca)}{u}"
        dica = _dica(glossario, c)
        nome = (f'<span class="termo" title="{dica}">{r}</span>' if dica else r)
        partes.append(f"{nome} <b>{valor_txt}</b>")

    return f"""
    <div class="cartao">
      <div class="cartao-topo">
        <span class="cartao-rotulo">{rotulo}</span>
        <span class="selo" style="background:{soft};color:{cor}">{n_alto} em risco alto</span>
      </div>
      <div class="cartao-valor" style="color:{cor}">{num(valor, 2)}<span
        class="unidade" title="Score de posição relativa dentro do grupo de pares.&#10;0 = menor risco do grupo · 0,50 = mediana · 1 = maior risco.">
        de 1,00</span></div>
      <div class="cartao-escala">score de posição relativa · 0,50 = mediana dos pares</div>
      <div class="cartao-releitura">{descricao}</div>
      <div class="cartao-spark">{spark}</div>
      <div class="cartao-meta">{delta_txt} · {n_tot} instituições avaliadas</div>
      <div class="cartao-comp">componentes (mediana do recorte, em unidades reais):<br>{' · '.join(partes)}</div>
    </div>
    """
