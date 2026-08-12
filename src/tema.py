"""
tema.py -- ARQUIVO DE TEMA. Isolado de proposito: para mudar a aparencia do painel,
edite so este arquivo (e .streamlit/config.toml, que espelha as cores base).

Identidade: editorial "papel", modo claro.
  - fundo creme e superficies quentes, no lugar do branco puro -- reduz o brilho e
    da o ar de relatorio impresso;
  - acento marrom para a estrutura (titulos, reguas, links);
  - vermelho / ambar / verde reservados EXCLUSIVAMENTE a sinalizacao de risco, para
    que o semaforo salte aos olhos e nada mais compita com ele;
  - escala tipografica e de espacamento fixas, para densidade consistente.
"""
from __future__ import annotations

# ---------------------------------------------------------------- cores
TEMA = {
    # superficies
    "fundo":        "#F3EFE5",   # papel
    "surface":      "#FAF8F2",   # cartao
    "surface_2":    "#EFEADD",
    "surface_3":    "#E7E1D1",
    "borda":        "#D8D2C6",
    "borda_forte":  "#C8C0B0",

    # texto (tres niveis)
    "texto":        "#1A1D21",
    "texto_2":      "#3D4147",
    "texto_3":      "#636562",

    # estrutura
    "acento":       "#8F6644",
    "acento_ink":   "#7C5638",
    "acento_soft":  "#EDE3D3",

    # sinalizacao de risco (usar SO para risco)
    "risco_alto":   "#B32626",
    "risco_medio":  "#925D0B",
    "risco_baixo":  "#177245",
    "alto_soft":    "#F6E6E0",
    "medio_soft":   "#F4EAD3",
    "baixo_soft":   "#E3EFE4",
    "neutro":       "#6E6F69",

    # graficos
    # O marrom do acento e cor de ESTRUTURA (titulos, reguas, bordas). As marcas de
    # dados usam teal, para nao competir com o marrom nem com o vermelho/ambar do risco.
    "marca":        "#0E707F",   # cor padrao de ponto/barra/linha
    "marca_clara":  "#5FA3AC",
    "grid":         "#E9E3D4",
    "eixo":         "#8A867A",
    "referencia":   "#6E6F69",
    "serie_1":      "#1A1D21",
    "serie_2":      "#0E707F",
    "serie_3":      "#925D0B",
    "sequencial":   ["#F0E9DC", "#DCCDB6", "#C4AA8A", "#A98764", "#8F6644", "#6E4B31"],
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
CSS = f"""
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

  /* ---------- cabecalho ---------- */
  .cabecalho {{ border-bottom: 2px solid {TEMA['acento']}; padding-bottom: 12px;
                margin-bottom: 4px; }}
  .cabecalho h1 {{ font-size: 30px; line-height: 1.12; letter-spacing: -0.018em;
                   font-weight: 650; margin: 0 0 6px 0; color: {TEMA['texto']}; }}
  .cabecalho .sub {{ font-size: 15px; line-height: 1.55; color: {TEMA['texto_2']};
                     max-width: 78ch; }}
  .cabecalho .assinatura {{ font-size: 12px; color: {TEMA['texto_3']}; margin-top: 8px;
                            letter-spacing: 0.03em; }}

  /* ---------- bloco Leitura / Consequencia ---------- */
  .bloco-lrc {{ border-left: 3px solid {TEMA['acento']}; background: {TEMA['surface']};
                padding: 11px 15px; margin: 8px 0 16px 0; border-radius: 0 3px 3px 0;
                font-size: 13.5px; line-height: 1.6; color: {TEMA['texto_2']};
                border-top: 1px solid {TEMA['borda']};
                border-right: 1px solid {TEMA['borda']};
                border-bottom: 1px solid {TEMA['borda']}; }}
  .bloco-lrc b {{ color: {TEMA['acento_ink']}; font-weight: 570; }}

  .aviso {{ border-left: 3px solid {TEMA['risco_medio']}; background: {TEMA['medio_soft']};
            padding: 10px 14px; margin: 10px 0; font-size: 12.5px; line-height: 1.55;
            border-radius: 0 3px 3px 0; color: {TEMA['texto_2']}; }}

  .rodape-fonte {{ font-size: 11px; color: {TEMA['texto_3']}; margin-top: 2px;
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
  .cartao-valor {{ font-size: 34px; line-height: 1.12; letter-spacing: -0.018em;
                   font-weight: 650; color: {TEMA['texto']}; margin: 4px 0 0 0;
                   font-variant-numeric: tabular-nums; }}
  .cartao-valor .unidade {{ font-size: 16px; font-weight: 500;
                            color: {TEMA['texto_3']}; letter-spacing: 0; }}
  .cartao-releitura {{ font-size: 12.5px; line-height: 1.5; color: {TEMA['texto_2']};
                       margin: 5px 0 9px 0; }}
  .cartao-meta {{ font-size: 11px; color: {TEMA['texto_3']}; margin-top: 7px;
                  line-height: 1.5; }}
  .cartao-spark {{ margin: 4px 0 2px 0; }}
  .cartao-comp {{ font-size: 11px; color: {TEMA['texto_3']}; line-height: 1.65;
                  border-top: 1px solid {TEMA['borda']}; padding-top: 8px;
                  margin-top: 9px; }}
  .cartao-comp b {{ color: {TEMA['texto_2']}; font-weight: 500; }}

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
