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


# ---------------------------------------------------------------- sparkline
def sparkline(valores, largura: int = 168, altura: int = 34,
              cor: str | None = None, linha_base: float | None = None) -> str:
    """SVG inline de uma minissérie. Leve de proposito: um grafico Plotly por cartao
    deixaria a pagina lenta, e aqui basta a FORMA da serie, nao a leitura precisa."""
    v = [float(x) for x in valores if x is not None and x == x]
    if len(v) < 2:
        return (f'<svg width="{largura}" height="{altura}"></svg>')

    lo, hi = min(v), max(v)
    span = (hi - lo) or 1.0
    pad = 3
    dx = (largura - 2 * pad) / (len(v) - 1)

    def y(val: float) -> float:
        return altura - pad - (val - lo) / span * (altura - 2 * pad)

    pontos = " ".join(f"{pad + i * dx:.1f},{y(val):.1f}" for i, val in enumerate(v))
    cor = cor or TEMA["acento"]

    base = ""
    if linha_base is not None and lo <= linha_base <= hi:
        yb = y(linha_base)
        base = (f'<line x1="{pad}" y1="{yb:.1f}" x2="{largura - pad}" y2="{yb:.1f}" '
                f'stroke="{TEMA["eixo"]}" stroke-width="1" stroke-dasharray="2,2" '
                f'opacity="0.55"/>')

    area = (f'<polygon points="{pad},{altura - pad} {pontos} '
            f'{largura - pad},{altura - pad}" fill="{cor}" opacity="0.10"/>')
    ultimo_x = pad + (len(v) - 1) * dx
    ponta = (f'<circle cx="{ultimo_x:.1f}" cy="{y(v[-1]):.1f}" r="2.6" fill="{cor}"/>')

    return (f'<svg width="{largura}" height="{altura}" viewBox="0 0 {largura} {altura}" '
            f'preserveAspectRatio="none" style="display:block">{base}{area}'
            f'<polyline points="{pontos}" fill="none" stroke="{cor}" '
            f'stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round"/>'
            f'{ponta}</svg>')


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
  .cartao-comp {{ font-size: {t["cartao_rodape"]}px; color: {TEMA['texto_3']}; line-height: 1.65;
                  border-top: 1px solid {TEMA['borda']}; padding-top: 8px;
                  margin-top: 9px; }}
  .cartao-comp b {{ color: {TEMA['texto_2']}; font-weight: 570; }}
  .cartao-comp .ref {{ color: {TEMA['texto_3']}; font-size: 0.92em; }}
  .cartao-escala {{ font-size: 10.5px; color: {TEMA['texto_3']}; margin: -2px 0 6px 0;
                    letter-spacing: 0.01em; }}

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
