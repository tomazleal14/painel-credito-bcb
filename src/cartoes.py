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
from tema import (COMPOSICAO_CORES, SEMAFORO, SEMAFORO_SOFT, TEMA,
                  barra_composicao, legenda_composicao, sparkline)
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


def _serie_mediana(df: pd.DataFrame, col: str,
                   indice: list | None = None) -> pd.Series:
    """Mediana por trimestre -- a serie que o sparkline desenha.

    NAO remove os trimestres vazios: eles precisam chegar como NaN para o sparkline
    desenhar um buraco. Removê-los encostaria os pontos vizinhos e inventaria uma
    continuidade que o dado nao tem.

    `indice` e a lista COMPLETA de data-bases do painel, e e obrigatorio quando `df` ja
    vem filtrado (ex.: so as instituicoes sinalizadas). Sem ele, um trimestre em que
    NINGUEM foi sinalizado nao gera grupo nenhum no groupby e simplesmente desaparece do
    indice -- o oposto do que esta docstring promete. Foi o que acontecia em P1: a serie
    tinha 21 pontos contiguos em vez de 29 com buraco em 2025, o sparkline ligava
    2024Q4 a 2026Q1, e o delta de `iloc[-5]` caia em 2024Q1 e era rotulado "em 12 meses"
    sendo uma distancia de dois anos.
    """
    if col not in df.columns:
        return pd.Series(dtype=float)
    s = (df.replace([np.inf, -np.inf], np.nan)
           .groupby("data_base")[col].median().sort_index())
    if indice is not None:
        s = s.reindex(sorted(indice))
    return s


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

    # o indice vem de df_hist (todas as instituicoes), nao de hist_marc: e o calendario
    # do painel, e nao o subconjunto de trimestres em que houve alguem sinalizado
    calendario = sorted(df_hist["data_base"].unique()) if "data_base" in df_hist else None
    serie = _serie_mediana(hist_marc, col, indice=calendario) * fator
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
    elif len(serie) >= 5 and pd.notna(serie.iloc[-1]):
        # a ponta de 4 trimestres atras cai numa lacuna: qualquer numero aqui seria a
        # diferenca contra outro ano, nao contra 12 meses
        delta_txt = "sem comparação de 12 meses — há lacuna 4 trimestres atrás"
    elif len(serie) < 5:
        delta_txt = f"série curta demais para 12 meses ({len(serie.dropna())} trim.)"

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


DICA_NIVEL = {
    "alto": "Score do eixo ≥ 0,75 — quartil superior do grupo de pares (mesmo TCB). "
            "É esta fatia que forma o número de destaque do cartão.",
    "medio": "Score do eixo entre 0,50 e 0,75 — acima da mediana do grupo de pares, "
             "sem atingir o corte de risco alto.",
    "baixo": "Score do eixo abaixo de 0,50 — na metade inferior do grupo de pares.",
    "sem": "Sem score neste eixo: a instituição não tem metade dos indicadores do "
           "eixo com dado no trimestre, e o painel não publica score sobre "
           "fragmento. Não significa risco baixo — significa não avaliável.",
}
ROTULO_NIVEL = {"alto": "Risco alto", "medio": "Atenção",
                "baixo": "Risco baixo", "sem": "Não avaliável"}


def composicao_carteira(df_atual: pd.DataFrame, eixo: str) -> list[tuple]:
    """Fatias da carteira do trimestre por nivel de risco, com dica pronta.

    Sempre completa: descreve so o corte transversal corrente, entao nao depende de
    historico e nao e afetada pelas quebras de serie que esvaziam os graficos de
    trimestre. E a leitura que resta quando a serie temporal nao pode ser lida.
    """
    col_sem = f"sem_{eixo}"
    if col_sem not in df_atual.columns or "carteira_credito_real" not in df_atual.columns:
        return []
    tot = float(df_atual["carteira_credito_real"].sum())
    if tot <= 0:
        return []

    fatias = []
    for nivel in ("alto", "medio", "baixo", "sem"):
        d = df_atual[df_atual[col_sem] == nivel]
        v = float(d["carteira_credito_real"].sum())
        if v <= 0:
            continue
        dica = (f"{ROTULO_NIVEL[nivel]} · {len(d)} "
                f"{'instituição' if len(d) == 1 else 'instituições'} · "
                f"R$ {num(v / 1e9, 1)} bi = {num(v / tot * 100, 1)}% da carteira do "
                f"recorte.&#10;&#10;{DICA_NIVEL[nivel]}")
        fatias.append((ROTULO_NIVEL[nivel], v, COMPOSICAO_CORES[nivel], dica))
    return fatias


def exposta_no_trimestre(df_atual: pd.DataFrame, eixo: str) -> float:
    """Carteira exposta a risco alto NO TRIMESTRE SELECIONADO, em % do recorte.

    Antes o numero de destaque saia de `carteira_exposta(df_hist).dropna().iloc[-1]` --
    o ultimo trimestre COM DADO da serie inteira, e nao o trimestre escolhido na barra
    lateral. O cartao entao exibia 2026Q1 mesmo com 12/2025 selecionado, ao lado de uma
    barra de composicao que obedecia a selecao: dois trimestres no mesmo cartao.

    Retorna NaN, nao zero, quando nenhuma instituicao do recorte tem score neste eixo:
    zero diria "nada em risco alto", quando o correto e "nao da para avaliar".
    """
    col_sem, col_score = f"sem_{eixo}", f"score_{eixo}"
    if col_sem not in df_atual.columns or "carteira_credito_real" not in df_atual.columns:
        return float("nan")
    if col_score in df_atual.columns and not df_atual[col_score].notna().any():
        return float("nan")
    tot = float(df_atual["carteira_credito_real"].sum())
    if tot <= 0:
        return float("nan")
    alto = float(df_atual.loc[df_atual[col_sem] == "alto", "carteira_credito_real"].sum())
    return alto / tot * 100


def cartao_eixo(df_atual: pd.DataFrame, eixo: str,
                rotulo: str, descricao: str, glossario: dict | None = None,
                n_percentis: int | None = None,
                componentes: list[str] | None = None) -> str:
    """Cartao de um EIXO na Visao geral: numero de destaque -> composicao -> por que.

    Recebe SO o corte do trimestre selecionado (`df_atual`). O historico saiu junto com
    a minisserie, e manter um `df_hist` aqui era o que permitia o cartao ler um
    trimestre no numero e outro na composicao.

    Nao tem serie temporal. As tres series tem 21, 29 e 5 trimestres, e as duas
    primeiras tem lacuna no meio -- de modo que o cartao gastava metade da altura com
    um grafico que so podia ser lido depois de tres paragrafos de ressalva (cobertura,
    justificativa de quebra, aviso de delta ausente). Historico e leitura de P1/P2/P3,
    onde ha espaco para a ressalva ao lado do dado; aqui fica a composicao da carteira,
    que descreve o trimestre corrente e esta sempre completa.

    Destaque: CARTEIRA EXPOSTA a risco alto (% do recorte) -- ver `carteira_exposta`.
    """
    col_sem = f"sem_{eixo}"

    valor = exposta_no_trimestre(df_atual, eixo)
    avaliavel = pd.notna(valor)

    n_alto = int((df_atual[col_sem] == "alto").sum()) if col_sem in df_atual else 0
    n_tot = int(df_atual[col_sem].isin(["alto", "medio", "baixo"]).sum()) if col_sem in df_atual else 0

    # faixas de exposicao da carteira -- nao sao percentis, sao fatias do recorte
    nivel = ("alto" if valor >= 20 else "medio" if valor >= 5 else "baixo") \
        if avaliavel else "sem"
    cor, soft = SEMAFORO[nivel], SEMAFORO_SOFT[nivel]

    fatias = composicao_carteira(df_atual, eixo)
    composicao = barra_composicao(fatias) if fatias else ""
    legenda = legenda_composicao(fatias) if fatias else ""

    selo = (f"{n_alto} de {n_tot} IFs" if avaliavel else "sem score")
    releitura = ("da carteira do recorte está em instituições sinalizadas neste eixo"
                 if avaliavel else
                 "nenhuma instituição do recorte pode ser avaliada neste eixo neste "
                 "trimestre")

    n_sem = int((df_atual[col_sem] == "sem").sum()) if col_sem in df_atual else 0
    if not avaliavel:
        nota_sem = (
            f"<div class='comp-nota'>Todas as <b>{n_sem}</b> instituições do recorte "
            f"ficam sem score neste eixo neste trimestre — nenhuma tem metade dos "
            f"indicadores com dado. O painel não publica score sobre fragmento, e por "
            f"isso o número fica vazio em vez de zero: <b>não é ausência de risco, é "
            f"ausência de medida.</b> O porquê está na página da pergunta.</div>")
    elif n_sem:
        nota_sem = (
            f"<div class='comp-nota'>{n_sem} "
            f"{'instituição fica' if n_sem == 1 else 'instituições ficam'} em "
            f"<b>não avaliável</b> neste eixo — sem indicadores suficientes no trimestre. "
            f"{'Ela não conta' if n_sem == 1 else 'Elas não contam'} como risco baixo."
            f"</div>")
    else:
        nota_sem = ""

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

    if not avaliavel:
        # sem sinalizadas, a mediana delas e vazia em todos os indicadores: o travessao
        # e a leitura correta, e o valor do recorte ao lado mostra o que ainda existe
        comp_txt = ("nenhuma instituição foi sinalizada neste trimestre — resta o valor "
                    "do recorte, nos indicadores que ainda têm dado:")
    elif n_percentis:
        comp_txt = (f"por que estas {n_alto} foram sinalizadas — mediana delas em cada "
                    f"um dos <b>{n_percentis}</b> indicadores que formam o score:")
    else:
        comp_txt = "componentes:"

    unidade = (f'<span class="unidade" title="Soma da carteira das instituições '
               f'sinalizadas como risco alto neste eixo, dividida pela carteira total '
               f'do recorte.">%</span>') if avaliavel else ""

    return f"""
    <div class="cartao">
      <div class="cartao-topo">
        <span class="cartao-rotulo">{rotulo}</span>
        <span class="selo" style="background:{soft};color:{cor}">{selo}</span>
      </div>
      <div class="cartao-valor" style="color:{cor}">{num(valor, 1)}{unidade}</div>
      <div class="cartao-escala">{releitura}</div>
      <div class="cartao-releitura">{descricao}</div>
      <div class="comp-titulo">Composição da carteira · {rotulo.lower()}</div>
      <div class="cartao-comp-barra">{composicao}</div>
      {legenda}
      {nota_sem}
      <div class="cartao-comp">{comp_txt}<br>{' · '.join(partes)}</div>
    </div>
    """
