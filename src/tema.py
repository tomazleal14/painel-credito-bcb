"""
tema.py -- ARQUIVO DE TEMA. Isolado de proposito: para mudar a aparencia do painel,
edite so este arquivo (e .streamlit/config.toml, que espelha as cores base).

Identidade: institucional, INSPIRADA na comunicacao do Banco Central -- nao identica,
por ser trabalho academico sem vinculo oficial.

As cores estruturais foram extraidas do proprio site do BCB (www.bcb.gov.br) pela
FREQUENCIA DE USO, e nao das variaveis CSS declaradas, que la sao apenas o Bootstrap
padrao e nao representam a identidade:
    #005C7A / #025C75  teal profundo -- 243 + 192 ocorrencias, cor dominante
    #137A97            teal medio    -- 137
    #3298D5            azul claro    -- 185
    #EDD297            areia/dourado -- 604, o acento quente da marca
    #606060            cinza de texto -- 638

Regras que sobrevivem a troca de paleta:
  - vermelho / ambar / verde seguem EXCLUSIVOS da sinalizacao de risco;
  - o teal profundo e cor de ESTRUTURA (titulos, reguas, bordas), nunca de dado;
  - as marcas de dado usam o azul claro do BCB, distinto do teal estrutural;
  - o areia aparece so no filete do cabecalho -- e cromo de marca, nao informacao,
    e nessa dose nao se confunde com o ambar de risco (#925D0B, bem mais escuro).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------- cores
TEMA = {
    # superficies -- neutro frio levemente azulado, na linha do BCB
    "fundo":        "#F1F4F5",
    "surface":      "#FFFFFF",   # cartao
    "surface_2":    "#E8EDEF",
    "surface_3":    "#DCE3E6",
    "borda":        "#D3DBDF",
    "borda_forte":  "#B7C3C8",

    # texto (tres niveis)
    "texto":        "#14252B",
    "texto_2":      "#3A4A51",
    "texto_3":      "#606060",   # o cinza de texto do proprio BCB

    # estrutura
    "acento":       "#025C75",   # teal profundo do BCB
    "acento_ink":   "#01414F",
    "acento_soft":  "#DCE8ED",
    "areia":        "#EDD297",   # acento quente da marca, so no cabecalho

    # sinalizacao de risco (usar SO para risco)
    "risco_alto":   "#B3261E",
    "risco_medio":  "#8A5A0B",
    "risco_baixo":  "#166B43",
    "alto_soft":    "#F7E4E1",
    "medio_soft":   "#F6EBD6",
    "baixo_soft":   "#E0EFE6",
    "neutro":       "#7A8A90",

    # graficos
    "marca":        "#3298D5",   # azul claro do BCB: distinto do teal estrutural
    "marca_clara":  "#8FC4E5",
    "grid":         "#E4EAEC",
    "eixo":         "#8DA5AC",   # cinza-teal do BCB
    "referencia":   "#7A8A90",
    "serie_1":      "#14252B",
    "serie_2":      "#025C75",
    "serie_3":      "#79939C",   # cinza-teal: terceira serie sem invadir o ambar de risco
    "sequencial":   ["#E8EFF2", "#C3D7DF", "#95BCCA", "#5E9CB0", "#2A7A94", "#025C75"],
}

SEMAFORO = {
    "alto":  TEMA["risco_alto"],
    "medio": TEMA["risco_medio"],
    "baixo": TEMA["risco_baixo"],
    "sem":   TEMA["neutro"],
}
SEMAFORO_SOFT = {
    "alto":  TEMA["alto_soft"],
    "medio": TEMA["medio_soft"],
    "baixo": TEMA["baixo_soft"],
    "sem":   TEMA["surface_2"],
}
# Preenchimento de AREA GRANDE (barra de composicao da Visao geral).
# As cores de SEMAFORO sao calibradas para TEXTO sobre branco -- precisam de contraste
# alto, e por isso sao escuras. Em area grande elas viram outra coisa: o ambar #8A5A0B
# le como marrom e fica a mesma distancia visual do verde #166B43, de modo que as duas
# maiores fatias da barra nao se separam. Estas sao as mesmas tres famílias (vermelho,
# ambar, verde) em versao mais clara e saturada, que e o que area grande pede.
# A convencao do projeto continua valendo: vermelho/ambar/verde SO para risco.
COMPOSICAO_CORES = {
    "alto":  "#D0342C",   # vermelho nitido
    "medio": "#E9A93C",   # ambar dourado -- separa do verde sem virar marrom
    "baixo": "#2E9C6A",   # verde claro
    "sem":   "#C3CFD4",   # cinza-teal, ausencia e nao nivel de risco
}
ICONE_SEMAFORO = {"alto": "●", "medio": "●", "baixo": "●", "sem": "○"}
ROTULO_SEMAFORO = {"alto": "risco alto", "medio": "atenção",
                   "baixo": "baixo", "sem": "sem dado"}

# ---------------------------------------------------------------- tipografia
FONTE = ('Inter, "Source Sans Pro", -apple-system, BlinkMacSystemFont, '
         '"Segoe UI", Roboto, Helvetica, Arial, sans-serif')
TAM_TITULO = 14
TAM_EIXO = 11.5
ALTURA_GRAFICO = 360
ALTURA_GRAFICO_GRANDE = 520


def layout_base(titulo: str = "", altura: int | None = None) -> dict:
    """Layout Plotly comum a todos os graficos do painel."""
    return {
        "title": {"text": titulo, "font": {"size": TAM_TITULO, "color": TEMA["texto"]},
                  "x": 0, "xanchor": "left"},
        "height": altura or ALTURA_GRAFICO,
        "paper_bgcolor": TEMA["surface"],
        "plot_bgcolor": TEMA["surface"],
        "font": {"family": FONTE, "size": TAM_EIXO, "color": TEMA["texto_2"]},
        "margin": {"l": 58, "r": 18, "t": 44 if titulo else 14, "b": 46},
        "xaxis": {"gridcolor": TEMA["grid"], "zerolinecolor": TEMA["grid"],
                  "linecolor": TEMA["borda"], "tickfont": {"color": TEMA["texto_3"]}},
        "yaxis": {"gridcolor": TEMA["grid"], "zerolinecolor": TEMA["grid"],
                  "linecolor": TEMA["borda"], "tickfont": {"color": TEMA["texto_3"]}},
        "legend": {"orientation": "h", "y": -0.18, "x": 0,
                   "font": {"size": 10.5, "color": TEMA["texto_2"]},
                   "bgcolor": "rgba(0,0,0,0)"},
        "hoverlabel": {"font": {"family": FONTE, "size": 11.5},
                       "bgcolor": TEMA["surface"], "bordercolor": TEMA["borda_forte"]},
    }


# ------------------------------------------------- distribuicao do trimestre
def faixa_escala(valores, lo_q: float = 0.05, hi_q: float = 0.95) -> tuple[float, float]:
    """Miolo da distribuicao do recorte, para servir de escala do desenho.

    NAO se estica a escala para caber o extremo. Em crescimento, uma sinalizada a 165%
    comprimiria a caixa inteira num canto de 20px e a figura deixaria de mostrar o que
    importa -- a posicao das sinalizadas DENTRO da distribuicao. Quem fica fora e
    contado e declarado em texto, nao desenhado fora de proporcao.
    """
    v = pd.Series(valores).replace([np.inf, -np.inf], np.nan).dropna()
    if v.empty:
        return 0.0, 1.0
    lo, hi = float(v.quantile(lo_q)), float(v.quantile(hi_q))
    if hi <= lo:
        lo, hi = float(v.min()), float(v.max())
    if hi <= lo:
        hi = lo + (abs(lo) or 1.0)
    return lo, hi


def distribuicao(valores, marcados=None, largura: int = 330, altura: int = 52) -> str:
    """Fotografia do trimestre: forma da distribuicao + caixa + onde estao as marcadas.

    Substitui a minisserie nos cartoes de indicador. A serie temporal nao servia: os
    indicadores tem 3, 21, 25 e 29 trimestres, varios com buraco no meio, e uma linha
    sobre serie esparsa desenha continuidade onde nao ha dado. Esta figura descreve so o
    corte transversal do trimestre escolhido -- nao tem historico, logo nao tem buraco.

    Tres camadas, de cima para baixo:
      histograma claro   a FORMA da distribuicao do recorte (essa instituicao e rara ou
                         tem companhia?)
      caixa azul         p25-p75, com o traco na mediana do recorte
      riscos vermelhos   cada instituicao marcada; o ponto e a mediana delas

    Sem texto dentro do SVG: ele estica com a coluna (preserveAspectRatio="none") e o
    glifo esticaria junto. Rotulos de escala ficam em HTML, no chamador.
    """
    v = pd.Series(valores).replace([np.inf, -np.inf], np.nan).dropna()
    m = (pd.Series(marcados).replace([np.inf, -np.inf], np.nan).dropna()
         if marcados is not None else pd.Series(dtype=float))
    if len(v) < 2:
        return f'<svg width="{largura}" height="{altura}"></svg>'

    lo, hi = faixa_escala(v)
    pad = 4
    util = largura - 2 * pad

    def x(val: float) -> float:
        return pad + (min(max(val, lo), hi) - lo) / (hi - lo) * util

    y_base = altura * 0.52          # linha do eixo: histograma acima, caixa abaixo
    alt_hist = y_base - 3
    partes = []

    nb = 30
    bins = np.linspace(lo, hi, nb + 1)
    h, _ = np.histogram(np.clip(v, lo, hi), bins=bins)
    topo = max(int(h.max()), 1)
    bw = util / nb
    for i, n in enumerate(h):
        if n <= 0:
            continue
        a = n / topo * alt_hist
        partes.append(f'<rect x="{pad + i*bw:.2f}" y="{y_base - a:.2f}" '
                      f'width="{max(bw - 0.8, 0.6):.2f}" height="{a:.2f}" '
                      f'fill="{TEMA["marca_clara"]}" opacity="0.6"/>')
    partes.append(f'<line x1="{pad}" y1="{y_base:.1f}" x2="{largura - pad}" '
                  f'y2="{y_base:.1f}" stroke="{TEMA["eixo"]}" stroke-width="0.8"/>')

    q25, q50, q75 = (float(v.quantile(p)) for p in (.25, .50, .75))
    y_cx = y_base + 2
    partes.append(f'<rect x="{x(q25):.2f}" y="{y_cx:.1f}" '
                  f'width="{max(x(q75) - x(q25), 1.5):.2f}" height="9" '
                  f'fill="{TEMA["marca"]}" opacity="0.5" rx="1.5"/>')
    partes.append(f'<line x1="{x(q50):.2f}" y1="{y_cx - 1:.1f}" x2="{x(q50):.2f}" '
                  f'y2="{y_cx + 10:.1f}" stroke="{TEMA["acento_ink"]}" stroke-width="2"/>')

    y_rug = y_cx + 12
    for val in m[(m >= lo) & (m <= hi)]:
        partes.append(f'<line x1="{x(val):.2f}" y1="{y_rug:.1f}" x2="{x(val):.2f}" '
                      f'y2="{min(y_rug + 6, altura):.1f}" stroke="{TEMA["risco_alto"]}" '
                      f'stroke-width="1.4" opacity="0.8"/>')
    if len(m):
        # traco, e nao circulo: o SVG estica com a coluna (preserveAspectRatio="none")
        # e um <circle> viraria elipse numa tela larga. O traco vertical e imune ao
        # esticamento e ecoa a marca da mediana do recorte, logo acima.
        xm = x(float(m.median()))
        partes.append(f'<line x1="{xm:.2f}" y1="{y_cx - 3:.1f}" x2="{xm:.2f}" '
                      f'y2="{y_rug + 6:.1f}" stroke="#fff" stroke-width="4"/>')
        partes.append(f'<line x1="{xm:.2f}" y1="{y_cx - 3:.1f}" x2="{xm:.2f}" '
                      f'y2="{y_rug + 6:.1f}" stroke="{TEMA["risco_alto"]}" '
                      f'stroke-width="2"/>')

    return (f'<svg width="{largura}" height="{altura}" viewBox="0 0 {largura} {altura}" '
            f'preserveAspectRatio="none" style="display:block;width:100%">'
            f'{"".join(partes)}</svg>')


def fora_da_escala(valores, lo: float, hi: float) -> tuple[int, int]:
    """Quantos ficam abaixo e acima da escala desenhada."""
    v = pd.Series(valores).replace([np.inf, -np.inf], np.nan).dropna()
    return int((v < lo).sum()), int((v > hi).sum())


# --------------------------------------------------- composicao da carteira
def _pct_br(v: float, casas: int = 1) -> str:
    return f"{v:.{casas}f}".replace(".", ",")


def barra_composicao(fatias, largura: int = 200, altura: int = 30) -> str:
    """Barra horizontal empilhada. `fatias` = [(rotulo, valor, cor)] ou
    [(rotulo, valor, cor, dica)].

    Serve onde a serie temporal falha: esta SEMPRE completa, porque descreve o
    trimestre corrente, e decompoe diretamente o numero de destaque do cartao.

    A `dica` (atributo <title>) e usada VERBATIM quando fornecida. Antes esta funcao
    sempre concatenava ": {pct}%" ao rotulo -- e como o chamador ja punha a
    porcentagem no rotulo, a dica saia repetida ("risco alto -- 7.2% da carteira:
    7.2%") e com ponto decimal, fora do padrao pt-BR do resto do painel.

    SEM texto dentro das fatias. O SVG usa preserveAspectRatio="none" para a barra
    esticar ate a largura da coluna -- o que estica o glifo junto, na mesma proporcao
    (viewBox de 200px renderizado a ~400px deforma a fonte em 2x na horizontal). As
    porcentagens ficam na legenda, em HTML, onde a fonte nao sofre transformacao.
    """
    norm = [(f[0], f[1], f[2], f[3] if len(f) > 3 else None) for f in fatias]
    total = sum(max(v, 0) for _, v, _, _ in norm)
    if total <= 0:
        return f'<svg width="{largura}" height="{altura}"></svg>'

    partes, x = [], 0.0
    for rot, val, cor, dica in norm:
        w = max(val, 0) / total * largura
        if w <= 0:
            continue
        titulo = dica if dica is not None else f"{rot}: {_pct_br(val / total * 100)}%"
        partes.append(f'<rect x="{x:.2f}" y="0" width="{w:.2f}" height="{altura}" '
                      f'fill="{cor}"><title>{titulo}</title></rect>')
        x += w
    return (f'<svg width="{largura}" height="{altura}" viewBox="0 0 {largura} {altura}" '
            f'preserveAspectRatio="none" style="display:block;width:100%;'
            f'border-radius:3px">{"".join(partes)}</svg>')


def legenda_composicao(fatias) -> str:
    """Legenda da barra de composicao: quadradinho de cor, rotulo e valor.

    A barra empilhada sem legenda exige que se adivinhe a convencao de cor ou se
    passe o mouse em cada fatia. Fatia estreita (fracao de 1%) e praticamente
    inalcancavel com o mouse, entao a legenda e a UNICA via de leitura dela.
    """
    norm = [(f[0], f[1], f[2], f[3] if len(f) > 3 else None) for f in fatias]
    total = sum(max(v, 0) for _, v, _, _ in norm)
    if total <= 0:
        return ""
    itens = []
    for rot, val, cor, dica in norm:
        pct = max(val, 0) / total * 100
        t = f' title="{dica}"' if dica else ""
        itens.append(
            f'<div class="comp-item"{t}>'
            f'<span class="comp-cor" style="background:{cor}"></span>'
            f'<span class="comp-rot">{rot}</span>'
            f'<span class="comp-val">{_pct_br(pct)}%</span></div>')
    return f'<div class="comp-legenda">{"".join(itens)}</div>'


# ---------------------------------------------------------------- CSS
# Tamanhos padrao, em pixels. Podem ser sobrescritos pela secao [aparencia] do
# textos.toml, para que se ajuste o corpo do texto sem mexer em codigo.
TAMANHOS = {
    "titulo_pagina": 30,
    "subtitulo": 15,
    "assinatura": 12,
    "texto_base": 13.5,
    "cartao_valor": 34,
    "cartao_texto": 12.5,
    "cartao_rodape": 11,
    "rodape": 11,
    "tabela": 13,
}


def monta_css(aparencia: dict | None = None) -> str:
    """CSS do painel. `aparencia` vem da secao [aparencia] do textos.toml.

    O molde fica DENTRO da funcao de proposito: uma f-string ja consome as chaves de
    CSS, e combina-la com .format() depois quebraria em todo `{{ }}` do estilo.
    """
    t = dict(TAMANHOS)
    for k, v in (aparencia or {}).items():
        if k in t:
            try:
                t[k] = float(v)
            except (TypeError, ValueError):
                pass  # valor invalido no TOML: mantem o padrao em vez de quebrar
    return _css(t)


def _css(t: dict) -> str:
    return f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@350;420;500;570;650&display=swap');

  /* A fonte e aplicada por HERANCA a partir da raiz. NAO usar um seletor amplo como
     [class*="st-"]: ele atinge tambem os <span> de icone do Streamlit, que dependem da
     fonte "Material Symbols" para transformar o texto do ligature no desenho do icone.
     Com a fonte trocada, o icone vira o texto cru ("keyboard_arrow_right") na tela. */
  html, body, .stApp {{ font-family: {FONTE}; }}
  .stApp {{ background: {TEMA['fundo']}; }}
  .block-container {{ padding-top: 2.2rem; max-width: 1500px; }}

  /* devolve a fonte de icones para os elementos que dependem dela */
  [data-testid="stIconMaterial"], .material-icons, .material-symbols-rounded,
  span[translate="no"] {{ font-family: "Material Symbols Rounded", "Material Icons" !important; }}

  /* ---------- cabecalho ----------
     filete duplo: teal profundo sobre areia, o par cromatico da comunicacao do BCB.
     E cromo de marca; nenhum dado usa o areia. */
  .cabecalho {{ border-bottom: 3px solid {TEMA['areia']};
                box-shadow: inset 0 -6px 0 -3px {TEMA['acento']};
                padding-bottom: 12px; margin-bottom: 4px; }}
  .cabecalho h1 {{ font-size: {t["titulo_pagina"]}px; line-height: 1.12; letter-spacing: -0.018em;
                   font-weight: 650; margin: 0 0 6px 0; color: {TEMA['acento']}; }}
  .cabecalho .sub {{ font-size: {t["subtitulo"]}px; line-height: 1.55; color: {TEMA['texto_2']};
                     max-width: 78ch; }}
  .cabecalho .assinatura {{ font-size: {t["assinatura"]}px; color: {TEMA['texto_3']}; margin-top: 8px;
                            letter-spacing: 0.03em; }}

  /* ---------- bloco Leitura / Consequencia ---------- */
  .bloco-lrc {{ border-left: 3px solid {TEMA['acento']}; background: {TEMA['surface']};
                padding: 11px 15px; margin: 8px 0 16px 0; border-radius: 0 3px 3px 0;
                font-size: {t["texto_base"]}px; line-height: 1.6; color: {TEMA['texto_2']};
                border-top: 1px solid {TEMA['borda']};
                border-right: 1px solid {TEMA['borda']};
                border-bottom: 1px solid {TEMA['borda']}; }}
  .bloco-lrc b {{ color: {TEMA['acento_ink']}; font-weight: 570; }}

  /* texto explicativo dentro de um expander: sem a moldura do bloco-lrc, que
     duplicaria a borda que o proprio expander ja desenha */
  .explicacao {{ font-size: {t["texto_base"]}px; line-height: 1.6;
                 color: {TEMA['texto_2']}; }}
  .explicacao b {{ color: {TEMA['acento_ink']}; font-weight: 570; }}

  .aviso {{ border-left: 3px solid {TEMA['risco_medio']}; background: {TEMA['medio_soft']};
            padding: 10px 14px; margin: 10px 0; font-size: 12.5px; line-height: 1.55;
            border-radius: 0 3px 3px 0; color: {TEMA['texto_2']}; }}

  .rodape-fonte {{ font-size: {t["rodape"]}px; color: {TEMA['texto_3']}; margin-top: 2px;
                   line-height: 1.5; }}

  /* ---------- cartao de indicador ---------- */
  .cartao {{ background: {TEMA['surface']}; border: 1px solid {TEMA['borda']};
             border-radius: 4px; padding: 14px 16px 12px 16px; height: 100%;
             box-shadow: 0 1px 3px rgba(26,29,33,0.04); }}
  .cartao-topo {{ display: flex; justify-content: space-between; align-items: baseline;
                  gap: 10px; }}
  .cartao-rotulo {{ font-size: 10.5px; text-transform: uppercase;
                    letter-spacing: 0.06em; color: {TEMA['texto_3']};
                    font-weight: 570; }}
  .cartao-valor {{ font-size: {t["cartao_valor"]}px; line-height: 1.12; letter-spacing: -0.018em;
                   font-weight: 650; color: {TEMA['texto']}; margin: 4px 0 0 0;
                   font-variant-numeric: tabular-nums; }}
  .cartao-valor .unidade {{ font-size: 16px; font-weight: 500;
                            color: {TEMA['texto_3']}; letter-spacing: 0; }}
  .cartao-releitura {{ font-size: {t["cartao_texto"]}px; line-height: 1.5; color: {TEMA['texto_2']};
                       margin: 5px 0 9px 0; }}
  .cartao-meta {{ font-size: {t["cartao_rodape"]}px; color: {TEMA['texto_3']}; margin-top: 7px;
                  line-height: 1.5; }}
  .cartao-spark {{ margin: 4px 0 2px 0; }}
  /* distribuicao do trimestre: os rotulos de escala ficam em HTML, nao dentro do SVG,
     porque o SVG estica com a coluna e deformaria o glifo junto */
  .cartao-dist {{ margin: 6px 0 0 0; }}
  .dist-eixo {{ display: flex; justify-content: space-between;
                font-size: 9.5px; color: {TEMA['texto_3']};
                font-variant-numeric: tabular-nums; margin: 1px 0 3px 0; }}
  .cartao-comp {{ font-size: {t["cartao_rodape"]}px; color: {TEMA['texto_3']}; line-height: 1.65;
                  border-top: 1px solid {TEMA['borda']}; padding-top: 8px;
                  margin-top: 9px; }}
  .cartao-comp b {{ color: {TEMA['texto_2']}; font-weight: 570; }}
  .cartao-comp .ref {{ color: {TEMA['texto_3']}; font-size: 0.92em; }}
  .cartao-escala {{ font-size: 10.5px; color: {TEMA['texto_3']}; margin: -2px 0 6px 0;
                    letter-spacing: 0.01em; }}
  .cartao-comp-barra {{ margin: 8px 0 3px 0; }}

  /* ---------- composicao da carteira por nivel de risco (Visao geral) ----------
     Na Visao geral esta barra e o conteudo principal do cartao, nao um adorno: ela
     e a unica leitura que esta SEMPRE completa, porque descreve so o trimestre
     corrente. Por isso ganha titulo, altura e legenda propria. */
  .comp-titulo {{ font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.05em;
                  color: {TEMA['texto_3']}; font-weight: 570; margin: 14px 0 6px 0; }}
  .comp-legenda {{ display: grid; grid-template-columns: 1fr 1fr; gap: 3px 12px;
                   margin: 7px 0 2px 0; }}
  .comp-item {{ display: flex; align-items: center; gap: 6px; font-size: 11px;
                color: {TEMA['texto_2']}; line-height: 1.5; cursor: help; }}
  .comp-cor {{ width: 9px; height: 9px; border-radius: 2px; flex: 0 0 9px; }}
  .comp-rot {{ flex: 1 1 auto; }}
  .comp-val {{ font-variant-numeric: tabular-nums; font-weight: 600;
               color: {TEMA['texto']}; }}
  .comp-nota {{ font-size: 10.5px; color: {TEMA['texto_3']}; line-height: 1.5;
                margin: 6px 0 0 0; }}
  /* justificativa de serie incompleta: fica visivel, nao escondida em nota de rodape */
  .cartao-just {{ font-size: 10.5px; line-height: 1.5; color: {TEMA['texto_2']};
                  background: {TEMA['surface_2']}; border-left: 2px solid {TEMA['eixo']};
                  padding: 6px 9px; margin: 4px 0 8px 0; border-radius: 0 3px 3px 0; }}
  .cartao-just:empty {{ display: none; }}
  .cartao-just b {{ color: {TEMA['acento_ink']}; }}

  /* par sinalizadas x recorte: os dois valores lado a lado, o do recorte em corpo
     menor e cor secundaria -- e referencia, nao protagonista */
  .cartao-par {{ display: flex; gap: 18px; align-items: baseline; margin: 4px 0 2px 0; }}
  .par-col {{ display: flex; flex-direction: column; }}
  .par-rot {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.05em;
              color: {TEMA['texto_3']}; font-weight: 570; }}
  .par-val {{ font-size: 19px; font-weight: 570; color: {TEMA['texto_2']};
              letter-spacing: -0.01em; font-variant-numeric: tabular-nums;
              line-height: 1.2; }}
  .par-val.destaque {{ font-size: {t["cartao_valor"]}px; font-weight: 650;
                       color: {TEMA['texto']}; letter-spacing: -0.018em; }}
  .par-val .u {{ font-size: 0.55em; font-weight: 500; color: {TEMA['texto_3']};
                 margin-left: 2px; }}

  /* termo com dica: sublinhado pontilhado indica que ha explicacao ao passar o mouse */
  .termo {{ border-bottom: 1px dotted {TEMA['borda_forte']}; cursor: help; }}
  .termo:hover {{ border-bottom-color: {TEMA['acento']}; color: {TEMA['acento_ink']}; }}

  /* tabela do glossario de indicadores */
  .gloss-ind {{ font-size: {t["cartao_rodape"]}px; line-height: 1.6; width: 100%;
                border-collapse: collapse; }}
  .gloss-ind th {{ text-align: left; font-size: 10.5px; text-transform: uppercase;
                   letter-spacing: 0.06em; color: {TEMA['texto_3']}; font-weight: 570;
                   border-bottom: 1px solid {TEMA['borda_forte']}; padding: 5px 8px; }}
  .gloss-ind td {{ padding: 6px 8px; border-bottom: 1px solid {TEMA['borda']};
                   vertical-align: top; }}
  .gloss-ind td.nome {{ font-weight: 570; color: {TEMA['acento_ink']};
                        white-space: nowrap; }}
  .gloss-ind tr.sep td {{ background: {TEMA['surface_2']}; font-weight: 570;
                          color: {TEMA['texto_2']}; text-transform: uppercase;
                          font-size: 10.5px; letter-spacing: 0.06em; }}

  .selo {{ display: inline-block; font-size: 10px; letter-spacing: 0.05em;
           text-transform: uppercase; font-weight: 570; padding: 2px 7px;
           border-radius: 3px; vertical-align: middle; }}

  /* ---------- abas ---------- */
  .stTabs [data-baseweb="tab-list"] {{ gap: 2px; border-bottom: 1px solid {TEMA['borda']}; }}
  .stTabs [data-baseweb="tab"] {{ font-size: 13.5px; font-weight: 500;
                                  color: {TEMA['texto_3']}; padding: 9px 15px; }}
  .stTabs [aria-selected="true"] {{ color: {TEMA['acento_ink']}; font-weight: 570; }}

  /* ---------- barra lateral ---------- */
  section[data-testid="stSidebar"] {{ background: {TEMA['surface_2']};
                                      border-right: 1px solid {TEMA['borda']}; }}
  section[data-testid="stSidebar"] .block-container {{ padding-top: 1.2rem; }}

  .filtro-titulo {{ font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.06em;
                    font-weight: 570; color: {TEMA['acento_ink']};
                    border-bottom: 1px solid {TEMA['borda_forte']};
                    padding-bottom: 5px; margin: 16px 0 2px 0; }}
  .filtro-ajuda {{ font-size: 11px; line-height: 1.5; color: {TEMA['texto_3']};
                   margin: -4px 0 8px 0; }}
  .filtro-resumo {{ background: {TEMA['acento_soft']}; border: 1px solid {TEMA['borda_forte']};
                    border-radius: 4px; padding: 9px 11px; font-size: 11.5px;
                    line-height: 1.55; color: {TEMA['texto_2']}; margin-bottom: 6px; }}
  .filtro-resumo b {{ color: {TEMA['acento_ink']}; font-variant-numeric: tabular-nums; }}

  /* glossario de siglas */
  .glossario {{ font-size: 11.5px; line-height: 1.6; }}
  .glossario table {{ width: 100%; border-collapse: collapse; }}
  .glossario td {{ padding: 4px 6px; border-bottom: 1px solid {TEMA['borda']};
                   vertical-align: top; }}
  .glossario td.cod {{ font-weight: 650; color: {TEMA['acento_ink']}; white-space: nowrap;
                       font-variant-numeric: tabular-nums; }}
  .glossario td.qtd {{ color: {TEMA['texto_3']}; white-space: nowrap; text-align: right;
                       font-variant-numeric: tabular-nums; }}
  .glossario .dim {{ font-size: 10.5px; text-transform: uppercase; letter-spacing: 0.06em;
                     color: {TEMA['texto_3']}; font-weight: 570; margin: 12px 0 4px 0; }}

  h4 {{ font-size: 17px; font-weight: 570; letter-spacing: -0.008em;
        color: {TEMA['texto']}; margin-top: 6px; }}
  div[data-testid="stMetricValue"] {{ font-size: 26px; font-weight: 650;
                                      letter-spacing: -0.018em;
                                      font-variant-numeric: tabular-nums; }}
  div[data-testid="stMetricLabel"] {{ font-size: 10.5px; text-transform: uppercase;
                                      letter-spacing: 0.06em; color: {TEMA['texto_3']}; }}
</style>
"""
