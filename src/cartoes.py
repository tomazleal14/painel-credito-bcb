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
from scoring import CORTE_ALTO, CORTE_MEDIO
from tema import (COMPOSICAO_CORES, SEMAFORO, SEMAFORO_SOFT, TEMA,
                  barra_composicao, distribuicao, faixa_escala, fora_da_escala,
                  legenda_composicao)
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


def cartao_indicador(df_atual: pd.DataFrame, col: str,
                     nota: str = "", glossario: dict | None = None,
                     eixo: str | None = None, rotulo_eixo: str = "",
                     data_base: int | None = None) -> str:
    """HTML de um cartao de indicador: a FOTOGRAFIA do trimestre selecionado.

    O valor em destaque e a mediana das instituicoes SINALIZADAS naquele eixo -- as
    mesmas que compoem o numero da Visao geral --, com o recorte inteiro ao lado como
    referencia.

    Antes o cartao mostrava a mediana das 258 do recorte, o que descrevia outra
    populacao: em 03/2026 exibia inadimplencia de 4,03% (o recorte) sob o titulo de um
    eixo cujas 10 sinalizadas tinham 8,61%. Nao dava para relacionar o cartao com a
    selecao, porque de fato nao havia relacao.

    NAO HA MAIS MINISSERIE. Os indicadores tem 3, 21, 25 e 29 trimestres, varios com
    buraco no meio, e desenhar serie temporal sobre dado esparso exigia tres linhas de
    ressalva por cartao -- amplitude declarada, delta que se anula, aviso de lacuna --
    para um grafico que ainda assim induzia a ler continuidade onde nao ha. A cobertura
    temporal, que e informacao relevante, continua no expander "Cobertura de cada
    indicador", onde tem espaco para ser explicada em vez de insinuada.
    """
    rotulo, unidade, fator, casas, _sentido = FORMATO.get(
        col, (col, "", 1, 2, "neutro"))
    dica = _dica(glossario, col)

    col_sem = f"sem_{eixo}" if eixo else None
    tem_marca = bool(col_sem and col_sem in df_atual.columns)
    marcadas = df_atual[df_atual[col_sem] == "alto"] if tem_marca else df_atual

    atual = (marcadas[col].replace([np.inf, -np.inf], np.nan).dropna() * fator
             if col in marcadas else pd.Series(dtype=float))
    todas = (df_atual[col].replace([np.inf, -np.inf], np.nan).dropna() * fator
             if col in df_atual else pd.Series(dtype=float))
    valor = float(atual.median()) if len(atual) else float("nan")
    n = len(atual)

    if data_base is None and "data_base" in df_atual and len(df_atual):
        data_base = int(df_atual["data_base"].iloc[0])
    quando = f"{str(data_base)[4:6]}/{str(data_base)[:4]}" if data_base else "o trimestre"

    grafico, eixo_html, escala_txt = "", "", ""
    grafico = distribuicao(todas, atual) if len(todas) >= 2 else ""
    if grafico:
        lo, hi = faixa_escala(todas)
        eixo_html = (f"<div class='dist-eixo'><span>{num(lo, casas)}{unidade}</span>"
                     f"<span>{num(hi, casas)}{unidade}</span></div>")
        n_abaixo, n_acima = fora_da_escala(atual, lo, hi)
        fora = ""
        if n_abaixo or n_acima:
            partes = []
            if n_abaixo:
                partes.append(f"{n_abaixo} abaixo")
            if n_acima:
                partes.append(f"{n_acima} acima")
            fora = f" · {' e '.join(partes)} da escala"
        escala_txt = (f"distribuição do recorte em {quando} · "
                      f"p10 {num(float(todas.quantile(.10)), casas)}{unidade} · "
                      f"p90 {num(float(todas.quantile(.90)), casas)}{unidade}{fora}")
    elif len(todas) and todas.nunique() < 2:
        # indicador de escopo SISTEMA: um valor por trimestre, igual para todas. Nao ha
        # distribuicao, nao ha percentil e nao ha selecao -- dizer isso e mais honesto
        # que desenhar um pico unico sobre uma escala fabricada.
        escala_txt = (f"valor único do sistema em {quando} — idêntico para as "
                      f"{len(todas)} instituições do recorte, portanto sem distribuição "
                      f"e sem percentil")

    med_recorte = float(todas.median()) if len(todas) else float("nan")

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
      <div class="cartao-releitura">medianas do trimestre</div>"""
    else:
        par = f"""
      <div class="cartao-valor">{num(valor, casas)}<span class="unidade"> {unidade}</span></div>
      <div class="cartao-releitura">mediana das {n} instituições do recorte</div>"""

    return f"""
    <div class="cartao">
      <div class="cartao-topo"><span class="cartao-rotulo termo"
        {f'title="{dica}"' if dica else ''}>{rotulo}</span></div>
      {par}
      <div class="cartao-dist">{grafico}</div>
      {eixo_html}
      <div class="cartao-escala">{escala_txt}</div>
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


ROTULO_NIVEL = {"alto": "Risco alto", "medio": "Atenção",
                "baixo": "Risco baixo", "sem": "Não avaliável"}


def dicas_nivel(corte_alto: float | None = None) -> dict[str, str]:
    """Texto da dica de cada faixa do semaforo, no corte VIGENTE.

    O corte de risco alto e ajustavel na barra lateral, entao deixar "0,75" escrito a
    mao aqui faria a dica mentir assim que alguem movesse o slider.
    """
    ca = CORTE_ALTO if corte_alto is None else float(corte_alto)
    cm = min(CORTE_MEDIO, ca)
    quartil = " — quartil superior do grupo de pares" if abs(ca - 0.75) < 1e-9 else ""
    return {
        "alto": f"Score do eixo ≥ {num(ca, 2)}{quartil} (mesmo TCB). "
                f"É esta fatia que forma o número de destaque do cartão.",
        "medio": f"Score do eixo entre {num(cm, 2)} e {num(ca, 2)} — acima da mediana "
                 f"do grupo de pares, sem atingir o corte de risco alto.",
        "baixo": f"Score do eixo abaixo de {num(cm, 2)} — na metade inferior do grupo "
                 f"de pares.",
        "sem": "Sem score neste eixo: a instituição não tem metade dos indicadores do "
               "eixo com dado no trimestre, e o painel não publica score sobre "
               "fragmento. Não significa risco baixo — significa não avaliável.",
    }


def composicao_carteira(df_atual: pd.DataFrame, eixo: str,
                        corte_alto: float | None = None) -> list[tuple]:
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

    dicas = dicas_nivel(corte_alto)
    fatias = []
    for nivel in ("alto", "medio", "baixo", "sem"):
        d = df_atual[df_atual[col_sem] == nivel]
        v = float(d["carteira_credito_real"].sum())
        if v <= 0:
            continue
        dica = (f"{ROTULO_NIVEL[nivel]} · {len(d)} "
                f"{'instituição' if len(d) == 1 else 'instituições'} · "
                f"R$ {num(v / 1e9, 1)} bi = {num(v / tot * 100, 1)}% da carteira do "
                f"recorte.&#10;&#10;{dicas[nivel]}")
        fatias.append((ROTULO_NIVEL[nivel], v, COMPOSICAO_CORES[nivel], dica))
    return fatias


def hhi_cr5(df: pd.DataFrame) -> tuple[float, float]:
    """HHI (0-10.000) e CR5 (%) calculados SOBRE O CONJUNTO RECEBIDO.

    As colunas `p2_1_hhi_sistema` e `p2_2_cr5_sistema_pct` do parquet sao do universo
    inteiro do IF.data e ficam gravadas no build -- filtro nenhum as alcanca. Isso e
    correto para o que elas dizem ser (o sistema), e errado para o que o painel parecia
    prometer: com o recorte filtrado em bancos com carteira >= R$ 10 bi, a tela seguia
    exibindo HHI 951 e CR5 64,8% quando o recorte tinha 1.169 e 71,9%.

    Concentracao e uma propriedade DO CONJUNTO, entao tem de ser recalculada sempre que
    o conjunto muda. O valor do sistema continua existindo, ao lado, como ancora.
    """
    c = df["carteira_credito_real"].replace([np.inf, -np.inf], np.nan).dropna()
    c = c[c > 0]
    if c.empty:
        return float("nan"), float("nan")
    s = c / c.sum()
    return float((s ** 2).sum() * 10_000), float(s.nlargest(5).sum() * 100)


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
                componentes: list[str] | None = None,
                corte_alto: float | None = None) -> str:
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

    fatias = composicao_carteira(df_atual, eixo, corte_alto)
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
