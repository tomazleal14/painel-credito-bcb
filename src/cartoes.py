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

import catalogo
from tema import (SEMAFORO, SEMAFORO_SOFT, TEMA, barra_composicao, barras,
                  sparkline)
from textos import md_html

# FORMATO e derivado do catalogo, para nao haver duas listas de indicadores no projeto.
# Formato mantido como (rotulo, unidade, fator, casas, sentido) por compatibilidade
# com o codigo ja escrito.
FORMATO = {i.chave: (i.rotulo, i.unidade, i.fator, i.casas, i.sentido)
           for i in catalogo.CATALOGO}

def tabela_glossario(glossario: dict, eixos_indicadores: dict | None = None) -> str:
    """Tabela 'o que cada indicador mede', para o expander da Visao geral.

    Usa OS 18 ATIVOS (6 por pergunta), e nao a decomposicao do score: HHI do sistema e
    CR5 medem o mercado inteiro, nao a instituicao, por isso nao entram no percentil de
    nenhum eixo -- mas continuam sendo dois dos 18 e precisam de verbete.
    """
    eixos_indicadores = eixos_indicadores or INDICADORES_DOS_18
    if not glossario:
        return ("<div>glossário indisponível — verifique [glosario_indicadores] "
                "em textos.toml</div>")

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


def indicadores_por_eixo(ativos: dict | None = None) -> dict[str, list[str]]:
    """Decomposicao do SCORE: so indicadores medidos POR INSTITUICAO entram no percentil.

    HHI do sistema e CR5 descrevem o mercado inteiro e sao iguais para todas as
    instituicoes no trimestre -- ranquea-las por eles nao teria sentido, entao ficam
    de fora daqui (mas continuam entre os 18 e no glossario).
    """
    ativos = ativos or {e: catalogo.padrao_do_eixo(e) for e in catalogo.EIXOS}
    return {eixo: [c for c in chaves
                   if catalogo.POR_CHAVE.get(c) and
                   catalogo.POR_CHAVE[c].escopo != "sistema"]
            for eixo, chaves in ativos.items()}


def indicadores_dos_18(ativos: dict | None = None) -> dict[str, list[str]]:
    """Os 18 do trabalho (6 por pergunta), inclusive os de sistema -- para o glossario."""
    return dict(ativos or {e: catalogo.padrao_do_eixo(e) for e in catalogo.EIXOS})


# compatibilidade com scripts que usam a selecao padrao
INDICADORES_POR_EIXO = indicadores_por_eixo()
INDICADORES_DOS_18 = indicadores_dos_18()


def num(v: float, casas: int) -> str:
    """Formata no padrao pt-BR: milhar com ponto, decimal com virgula."""
    if v is None or (isinstance(v, float) and not np.isfinite(v)):
        return "—"
    return f"{v:,.{casas}f}".replace(",", " ").replace(".", ",").replace(" ", ".")


def _serie_mediana(df: pd.DataFrame, col: str) -> pd.Series:
    """Mediana por trimestre -- a serie que o sparkline desenha.

    NAO remove os trimestres vazios: eles precisam chegar como NaN para o sparkline
    desenhar um buraco. Removê-los encostaria os pontos vizinhos e inventaria uma
    continuidade que o dado nao tem.
    """
    if col not in df.columns:
        return pd.Series(dtype=float)
    return (df.replace([np.inf, -np.inf], np.nan)
              .groupby("data_base")[col].median().sort_index())


def cartao_indicador(df_hist: pd.DataFrame, df_atual: pd.DataFrame, col: str,
                     nota: str = "", glossario: dict | None = None,
                     eixo: str | None = None, rotulo_eixo: str = "") -> str:
    """HTML de um cartao de indicador.

    O valor em destaque e a mediana das instituicoes SINALIZADAS naquele eixo -- as
    mesmas que compoem o numero da Visao geral --, com o recorte inteiro entre
    parenteses como referencia.

    Antes o cartao mostrava a mediana das 258 do recorte, o que descrevia outra
    populacao: em 03/2026 exibia inadimplencia de 4,03% (o recorte) sob o titulo de um
    eixo cujas 10 sinalizadas tinham 8,61%. Nao dava para relacionar o cartao com a
    selecao, porque de fato nao havia relacao.
    """
    rotulo, unidade, fator, casas, sentido = FORMATO.get(
        col, (col, "", 1, 2, "neutro"))
    dica = _dica(glossario, col)

    col_sem = f"sem_{eixo}" if eixo else None
    tem_marca = bool(col_sem and col_sem in df_atual.columns)
    marcadas = df_atual[df_atual[col_sem] == "alto"] if tem_marca else df_atual
    hist_marc = df_hist[df_hist[col_sem] == "alto"] if (
        tem_marca and col_sem in df_hist.columns) else df_hist

    serie = _serie_mediana(hist_marc, col) * fator
    atual = (marcadas[col].replace([np.inf, -np.inf], np.nan).dropna()
             if col in marcadas else pd.Series(dtype=float))
    todas = (df_atual[col].replace([np.inf, -np.inf], np.nan).dropna()
             if col in df_atual else pd.Series(dtype=float))
    valor = float(atual.median()) * fator if len(atual) else float("nan")
    n = len(atual)

    # variacao contra 4 trimestres atras (mesma data-base do ano anterior)
    # so compara se AMBAS as pontas existem: com buraco no meio, um delta seria inventado
    delta_txt, cor_delta = "—", TEMA["texto_3"]
    if len(serie) >= 5 and pd.notna(serie.iloc[-1]) and pd.notna(serie.iloc[-5]):
        d = serie.iloc[-1] - serie.iloc[-5]
        piora = (d > 0) if sentido == "maior_pior" else (d < 0)
        cor_delta = TEMA["risco_alto"] if piora else TEMA["risco_baixo"]
        seta = "▲" if d > 0 else ("▼" if d < 0 else "•")
        delta_txt = f"{seta} {num(abs(d), casas)} em 12 meses"

    cor_linha = TEMA["acento"]
    _s = serie.dropna()
    spark = sparkline(list(serie.values), cor=cor_linha,
                      linha_base=float(_s.median()) if len(_s) else None)
    # amplitude declarada: sem isso, a autoescala faz variacao minima parecer drama
    faixa_serie = (f"série: {num(_s.min(), casas)} a {num(_s.max(), casas)}{unidade} "
                   f"em {len(_s)} trim." if len(_s) else "")

    p10 = float(todas.quantile(0.10)) * fator if len(todas) else float("nan")
    p90 = float(todas.quantile(0.90)) * fator if len(todas) else float("nan")
    med_recorte = float(todas.median()) * fator if len(todas) else float("nan")

    # Os DOIS valores lado a lado: as sinalizadas (que explicam a selecao) e o recorte
    # inteiro (a referencia). Sem o par, o cartao ou descreve a populacao errada ou
    # esconde a base de comparacao.
    if tem_marca:
        par = f"""
      <div class="cartao-par">
        <div class="par-col">
          <div class="par-rot">sinalizadas ({n})</div>
          <div class="par-val destaque">{num(valor, casas)}<span class="u">{unidade}</span></div>
        </div>
        <div class="par-col">
          <div class="par-rot">recorte ({len(todas)})</div>
          <div class="par-val">{num(med_recorte, casas)}<span class="u">{unidade}</span></div>
        </div>
      </div>
      <div class="cartao-releitura">medianas · faixa do recorte
        {num(p10, casas)} a {num(p90, casas)} (p10–p90)</div>"""
    else:
        par = f"""
      <div class="cartao-valor">{num(valor, casas)}<span class="unidade"> {unidade}</span></div>
      <div class="cartao-releitura">mediana das {n} instituições do recorte</div>"""

    return f"""
    <div class="cartao">
      <div class="cartao-topo"><span class="cartao-rotulo termo"
        {f'title="{dica}"' if dica else ''}>{rotulo}</span></div>
      {par}
      <div class="cartao-spark">{spark}</div>
      <div class="cartao-escala">{faixa_serie}</div>
      <div class="cartao-meta" style="color:{cor_delta}">{delta_txt}</div>
      <div class="cartao-comp">{nota or '&nbsp;'}</div>
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


def carteira_exposta(df: pd.DataFrame, eixo: str) -> pd.Series:
    """Por trimestre: fatia da carteira do recorte que esta em instituicoes sinalizadas
    como risco alto naquele eixo.

    Por que esta e a medida de destaque, e nao a mediana dos scores: o score e um
    PERCENTIL, e percentil tem mediana 0,50 por construcao. Medido em 29 trimestres, o
    numero de concentracao variou 0,037 no total -- e some o recorte inteiro e ele vai a
    0,50 exatamente. Ja a carteira exposta variou de 7% a 43% e pondera por tamanho, que
    e o que separa uma cooperativa de R$ 2 bi da Caixa.
    """
    col_sem = f"sem_{eixo}"
    col_score = f"score_{eixo}"
    if col_sem not in df.columns or "carteira_credito_real" not in df.columns:
        return pd.Series(dtype=float)
    g = df.groupby("data_base")
    total = g["carteira_credito_real"].sum()
    alto = (df[df[col_sem] == "alto"].groupby("data_base")["carteira_credito_real"]
              .sum().reindex(total.index, fill_value=0.0))
    serie = (alto / total.where(total > 0) * 100)

    # Trimestre em que NENHUMA instituicao pode ser avaliada (score do eixo vazio para
    # todas) nao vale zero: vale BURACO. Zero diria "nada em risco", quando o correto e
    # "nao da para saber" -- e a minisserie desenharia um mergulho inexistente.
    if col_score in df.columns:
        avaliaveis = g[col_score].apply(lambda s: s.notna().sum())
        serie = serie.where(avaliaveis.reindex(serie.index).fillna(0) > 0)
    return serie.sort_index()


def cartao_eixo(df_hist: pd.DataFrame, df_atual: pd.DataFrame, eixo: str,
                rotulo: str, descricao: str, glossario: dict | None = None,
                n_percentis: int | None = None,
                componentes: list[str] | None = None,
                justificativa: str = "") -> str:
    """Cartao de um EIXO, no padrao subindice -> componentes.

    Destaque: CARTEIRA EXPOSTA a risco alto (% do recorte). O score do eixo continua
    calculado e usado no ranking, mas nao lidera o cartao -- ver `carteira_exposta`.
    """
    col_score = f"score_{eixo}"
    col_sem = f"sem_{eixo}"

    serie = carteira_exposta(df_hist, eixo)
    _val = serie.dropna()
    valor = float(_val.iloc[-1]) if len(_val) else float("nan")

    n_alto = int((df_atual[col_sem] == "alto").sum()) if col_sem in df_atual else 0
    n_tot = int(df_atual[col_sem].isin(["alto", "medio", "baixo"]).sum()) if col_sem in df_atual else 0
    score_mediano = (float(df_atual[col_score].dropna().median())
                     if col_score in df_atual and df_atual[col_score].notna().any()
                     else float("nan"))

    # faixas de exposicao da carteira -- nao sao percentis, sao fatias do recorte
    nivel = "alto" if valor >= 20 else "medio" if valor >= 5 else "baixo"
    cor, soft = SEMAFORO[nivel], SEMAFORO_SOFT[nivel]

    # BARRAS, nao linha: trimestre sem dado nao ganha barra, e a ausencia fica legivel
    # sem inventar continuidade. Altura sempre proporcional ao valor, a partir do zero.
    _s = serie.dropna()
    rotulos = [(f"{str(d)[2:4]}" if str(d)[4:6] == "03" else "") for d in serie.index]
    grafico = barras(list(serie.values), rotulos=rotulos, cor=cor)

    faixa_txt = ""
    if len(_s):
        pi, pf = _s.index.min(), _s.index.max()
        faixa_txt = (f"{len(_s)} de {len(serie)} trimestres · "
                     f"{str(pi)[4:6]}/{str(pi)[:4]} a {str(pf)[4:6]}/{str(pf)[:4]} · "
                     f"máx. {num(_s.max(), 1)}%")

    # composicao da carteira do trimestre por nivel de risco -- SEMPRE completa,
    # porque descreve so o corte transversal atual e nao depende de historico
    comp_fatias = []
    if col_sem in df_atual.columns and "carteira_credito_real" in df_atual.columns:
        tot_cart = df_atual["carteira_credito_real"].sum()
        for nivel, rot_n in [("alto", "risco alto"), ("medio", "atenção"),
                             ("baixo", "baixo"), ("sem", "sem dado")]:
            v = df_atual.loc[df_atual[col_sem] == nivel, "carteira_credito_real"].sum()
            if tot_cart > 0 and v > 0:
                comp_fatias.append((f"{rot_n} — {v/tot_cart*100:.1f}% da carteira",
                                    float(v), SEMAFORO[nivel]))
    composicao = barra_composicao(comp_fatias) if comp_fatias else ""

    delta_txt = ""
    if len(serie) >= 5 and pd.notna(serie.iloc[-1]) and pd.notna(serie.iloc[-5]):
        d = serie.iloc[-1] - serie.iloc[-5]
        seta = "▲" if d > 0 else ("▼" if d < 0 else "•")
        rumo = "subindo" if d > 1 else ("cedendo" if d < -1 else "estável")
        delta_txt = f"{rumo} · {seta} {num(abs(d), 1)} p.p. em 12 meses"
    elif len(serie) >= 5:
        delta_txt = "sem comparação de 12 meses (série com lacuna)"

    # Decomposicao: a mediana de cada indicador NAS INSTITUICOES SINALIZADAS -- as
    # mesmas que formam o numero de destaque. Antes a mediana era de todo o recorte, o
    # que descrevia outra populacao e nao explicava o destaque: no 03/2026 o cartao
    # mostrava credit gap -6,7% e 0 trimestres acima de 15% (perfil de sistema calmo)
    # logo abaixo de "7,2% da carteira sinalizada".
    # Entre parenteses vai o valor do recorte inteiro, como REFERENCIA de comparacao.
    marcadas = df_atual[df_atual[col_sem] == "alto"] if col_sem in df_atual else df_atual.iloc[0:0]
    partes = []
    for c in (componentes if componentes is not None
              else INDICADORES_POR_EIXO.get(eixo, [])):
        if c not in df_atual.columns:
            continue
        r, u, f, ca, _s = FORMATO.get(c, (c, "", 1, 2, "neutro"))
        sinal = marcadas[c].replace([np.inf, -np.inf], np.nan).dropna()
        todas = df_atual[c].replace([np.inf, -np.inf], np.nan).dropna()
        v_sinal = "—" if sinal.empty else f"{num(float(sinal.median()) * f, ca)}{u}"
        v_todas = "—" if todas.empty else f"{num(float(todas.median()) * f, ca)}{u}"
        dica = _dica(glossario, c)
        nome = (f'<span class="termo" title="{dica}">{r}</span>' if dica else r)
        partes.append(f"{nome} <b>{v_sinal}</b> "
                      f"<span class='ref'>(recorte {v_todas})</span>")

    comp_txt = (f"por que estas {n_alto} foram sinalizadas — mediana delas em cada um dos "
                f"<b>{n_percentis}</b> indicadores que formam o score:"
                if n_percentis else "componentes:")

    return f"""
    <div class="cartao">
      <div class="cartao-topo">
        <span class="cartao-rotulo">{rotulo}</span>
        <span class="selo" style="background:{soft};color:{cor}">{n_alto} de {n_tot} IFs</span>
      </div>
      <div class="cartao-valor" style="color:{cor}">{num(valor, 1)}<span
        class="unidade" title="Soma da carteira das instituições sinalizadas como risco alto neste eixo, dividida pela carteira total do recorte.">%</span></div>
      <div class="cartao-escala">da carteira do recorte está em instituições sinalizadas
        neste eixo</div>
      <div class="cartao-releitura">{descricao}</div>
      <div class="cartao-comp-barra">{composicao}</div>
      <div class="cartao-escala">composição da carteira do trimestre por nível de risco</div>
      <div class="cartao-spark">{grafico}</div>
      <div class="cartao-escala">{faixa_txt}</div>
      <div class="cartao-just">{justificativa}</div>
      <div class="cartao-meta">{delta_txt} · score mediano {num(score_mediano, 2)}</div>
      <div class="cartao-comp">{comp_txt}<br>{' · '.join(partes)}</div>
    </div>
    """
