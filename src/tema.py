"""
tema.py -- ARQUIVO DE TEMA. Isolado de proposito: para mudar a aparencia do painel,
edite so este arquivo (e .streamlit/config.toml, que espelha as cores base).

Identidade escolhida: institucional sobria, modo claro.
  - azul-petroleo como cor estrutural (neutra, tecnica)
  - ambar e vermelho reservados EXCLUSIVAMENTE a sinalizacao de risco, para que o
    semaforo salte aos olhos e nada mais compita com ele
  - cinzas para contexto, referencia e series de apoio
"""
from __future__ import annotations

# ---------------------------------------------------------------- cores
TEMA = {
    # estrutura
    "primaria":        "#0F4C5C",   # azul-petroleo
    "primaria_clara":  "#3E7B8C",
    "primaria_fraca":  "#D6E4E8",
    "fundo":           "#FFFFFF",
    "fundo_alt":       "#F5F7F8",
    "texto":           "#1A2428",
    "texto_fraco":     "#5C6B70",
    "linha":           "#D9E0E2",

    # sinalizacao de risco (usar SO para risco)
    "risco_alto":      "#B3261E",   # vermelho
    "risco_medio":     "#E08A1E",   # ambar
    "risco_baixo":     "#2E7D52",   # verde
    "neutro":          "#8A9AA0",

    # series de apoio
    "referencia":      "#8A9AA0",   # medianas, limiares, sistema
    "destaque":        "#0F4C5C",
    "sequencial":      ["#EAF1F3", "#C3D8DE", "#8FB9C4", "#5A96A6", "#2E7488", "#0F4C5C"],
    "divergente":      ["#2E7D52", "#8FBF9F", "#EDEDED", "#E8B37A", "#B3261E"],
}

SEMAFORO = {
    "alto":  TEMA["risco_alto"],
    "medio": TEMA["risco_medio"],
    "baixo": TEMA["risco_baixo"],
    "sem":   TEMA["neutro"],
}
ICONE_SEMAFORO = {"alto": "●", "medio": "●", "baixo": "●", "sem": "○"}

# ---------------------------------------------------------------- tipografia / layout
FONTE = "Source Sans Pro, -apple-system, Segoe UI, sans-serif"
TAM_TITULO = 15
TAM_EIXO = 12
ALTURA_GRAFICO = 380
ALTURA_GRAFICO_GRANDE = 520


def layout_base(titulo: str = "", altura: int | None = None) -> dict:
    """Layout Plotly comum a todos os graficos do painel."""
    return {
        "title": {"text": titulo, "font": {"size": TAM_TITULO, "color": TEMA["texto"]},
                  "x": 0, "xanchor": "left"},
        "height": altura or ALTURA_GRAFICO,
        "paper_bgcolor": TEMA["fundo"],
        "plot_bgcolor": TEMA["fundo"],
        "font": {"family": FONTE, "size": TAM_EIXO, "color": TEMA["texto"]},
        "margin": {"l": 60, "r": 20, "t": 46 if titulo else 16, "b": 48},
        "xaxis": {"gridcolor": TEMA["linha"], "zerolinecolor": TEMA["linha"],
                  "linecolor": TEMA["linha"]},
        "yaxis": {"gridcolor": TEMA["linha"], "zerolinecolor": TEMA["linha"],
                  "linecolor": TEMA["linha"]},
        "legend": {"orientation": "h", "y": -0.18, "x": 0,
                   "font": {"size": 11}, "bgcolor": "rgba(0,0,0,0)"},
        "hoverlabel": {"font": {"family": FONTE, "size": 12}},
    }


CSS = f"""
<style>
  .bloco-lrc {{
      border-left: 3px solid {TEMA['primaria']};
      background: {TEMA['fundo_alt']};
      padding: 10px 14px; margin: 6px 0 14px 0; border-radius: 0 4px 4px 0;
      font-size: 0.88rem; line-height: 1.5; color: {TEMA['texto']};
  }}
  .bloco-lrc b {{ color: {TEMA['primaria']}; }}
  .cabecalho {{
      border-bottom: 2px solid {TEMA['primaria']};
      padding-bottom: 10px; margin-bottom: 6px;
  }}
  .cabecalho h1 {{ font-size: 1.5rem; margin: 0; color: {TEMA['primaria']}; }}
  .cabecalho .sub {{ font-size: 0.85rem; color: {TEMA['texto_fraco']}; }}
  .aviso {{
      border-left: 3px solid {TEMA['risco_medio']};
      background: #FDF6EC; padding: 9px 13px; margin: 8px 0;
      font-size: 0.83rem; border-radius: 0 4px 4px 0;
  }}
  .rodape-fonte {{ font-size: 0.74rem; color: {TEMA['texto_fraco']}; margin-top: -6px; }}
  div[data-testid="stMetricValue"] {{ font-size: 1.35rem; }}
</style>
"""
