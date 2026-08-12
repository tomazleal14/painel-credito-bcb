"""
filtros.py -- barra de filtros do painel, com rotulos legiveis e glossario.

Dois problemas que este modulo resolve:

1. Os codigos do IF.data ("b1", "b3S", "S4") sao opacos para quem nao convive com a base.
   Cada um aparece com a descricao OFICIAL do BCB e quantas instituicoes representa, e ha
   um glossario completo num expander. As descricoes vem de
   data_processed/glossario_filtros.csv, gerado por src/coleta_glossario.py a partir do
   arquivo de filtros do proprio IF.data -- nao sao escritas de memoria.

2. Um `multiselect` com todas as opcoes pre-selecionadas vira uma parede de etiquetas
   empilhadas numa barra de 300px, com o conteudo cortado. Aqui usa-se `st.pills`, que
   mostra os codigos lado a lado em poucas linhas, e a selecao fina so aparece quando
   pedida.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from comum import DATA_PROC
from tema import TEMA

# atalhos de recorte -- combinacoes que o supervisor usa com frequencia
PERFIS = {
    "Todas": None,
    "Bancos": ["b1", "b2", "b4"],
    "Cooperativas": ["b3S", "b3C"],
    "Não bancárias": ["n1", "n2", "n4"],
}
AJUDA_PERFIL = {
    "Todas": "todo o universo do IF.data",
    "Bancos": "comercial, múltiplo, investimento, câmbio e desenvolvimento",
    "Cooperativas": "singulares, centrais e confederações",
    "Não bancárias": "crédito, mercado de capitais e instituições de pagamento",
}

# o IF.data publica instituicoes sem segmento atribuido; o codigo vem vazio
SEM_SEGMENTO = "—"
ROTULO_SEM_SEGMENTO = "n/c"


@st.cache_data(show_spinner=False)
def carrega_glossario() -> pd.DataFrame:
    caminho = DATA_PROC / "glossario_filtros.csv"
    if not caminho.exists():
        return pd.DataFrame(columns=["dimensao", "codigo", "descricao"])
    return pd.read_csv(caminho, dtype=str).fillna("")


def _mapa(gloss: pd.DataFrame, dimensao: str) -> dict[str, str]:
    sub = gloss[gloss["dimensao"] == dimensao]
    return dict(zip(sub["codigo"], sub["descricao"]))


def fmt_reais(v: float) -> str:
    if v == 0:
        return "sem corte"
    if v >= 1e9:
        return f"R$ {v/1e9:,.0f} bi".replace(",", ".")
    return f"R$ {v/1e6:,.0f} mi".replace(",", ".")


def glossario_html(gloss: pd.DataFrame) -> str:
    """Tabela de siglas para o expander da barra lateral."""
    if gloss.empty:
        return "<div class='glossario'>glossário indisponível — rode src/coleta_glossario.py</div>"

    ordem = [("tcb", "TCB — Tipo de Consolidado Bancário"),
             ("segmento_sr", "SR — Segmento (Res. 4.553/2017)"),
             ("controle", "TC — Tipo de Controle")]
    partes = ["<div class='glossario'>"]
    for dim, titulo in ordem:
        sub = gloss[gloss["dimensao"] == dim]
        if sub.empty:
            continue
        partes.append(f"<div class='dim'>{titulo}</div><table>")
        for r in sub.itertuples():
            faixa = ""
            if getattr(r, "carteira_max_bi", ""):
                faixa = (f"<br><span style='color:{TEMA['texto_3']}'>"
                         f"carteira até R$ {r.carteira_max_bi} bi</span>")
            n = getattr(r, "n_instituicoes", "")
            partes.append(f"<tr><td class='cod'>{r.codigo}</td>"
                          f"<td>{r.descricao}{faixa}</td>"
                          f"<td class='qtd'>{n + ' IFs' if n else ''}</td></tr>")
        partes.append("</table>")
    partes.append(
        f"<div style='margin-top:10px;font-size:11px;color:{TEMA['texto_3']}'>"
        "Contagens e faixas de carteira são <b>observadas</b> na data-base mais recente "
        "do painel. A Res. 4.553/2017 define os segmentos por porte relativo ao PIB e "
        "perfil de risco; o IF.data publica apenas o rótulo — por isso aqui se mostra o "
        "que os dados revelam, e não os limiares da norma. "
        f"<b>{ROTULO_SEM_SEGMENTO}</b> = sem segmento atribuído na fonte.</div></div>")
    return "".join(partes)


def barra_lateral(ind: pd.DataFrame, pesos_padrao: dict, eixos: list[str]) -> dict:
    """Desenha a barra de filtros e devolve as escolhas."""
    gloss = carrega_glossario()
    sb = st.sidebar

    # ---------------------------------------------------------------- recorte
    sb.markdown("<div class='filtro-titulo'>Recorte</div>", unsafe_allow_html=True)

    trimestres = sorted(ind["data_base"].unique())
    dt_sel = sb.selectbox(
        "Data-base", trimestres, index=len(trimestres) - 1,
        format_func=lambda d: f"{str(d)[4:6]}/{str(d)[:4]}",
        help="Trimestre de referência. O IF.data publica em março, junho, setembro e dezembro.")

    u = ind[ind["data_base"] == dt_sel]
    desc_tcb = _mapa(gloss, "tcb")
    cont_tcb = u["tcb"].value_counts().to_dict()
    tcbs = sorted(ind["tcb"].dropna().unique())

    perfil = sb.segmented_control(
        "Tipo de instituição", list(PERFIS), default="Todas",
        help="Atalhos para os recortes mais usados.")
    perfil = perfil or "Todas"
    sb.markdown(f"<div class='filtro-ajuda'>{AJUDA_PERFIL[perfil]}</div>",
                unsafe_allow_html=True)

    if PERFIS[perfil] is None:
        # a selecao fina so aparece quando pedida -- evita a parede de etiquetas
        if sb.toggle("Escolher tipos manualmente", value=False):
            tcb_sel = sb.pills(
                "Tipos (TCB)", tcbs, selection_mode="multi", default=tcbs,
                format_func=lambda c: f"{c} ({cont_tcb.get(c, 0)})",
                help="Passe o mouse ou abra o glossário abaixo para ver o que cada sigla significa.")
            tcb_sel = tcb_sel or tcbs
        else:
            tcb_sel = tcbs
    else:
        tcb_sel = [c for c in PERFIS[perfil] if c in tcbs]
    # resumo dos tipos: so os codigos. Cortar a descricao no meio da palavra
    # ("Banco Multiplo sem Car") polui e nao informa -- quem precisa do significado
    # abre o glossario logo abaixo.
    if len(tcb_sel) == len(tcbs):
        resumo_tcb = f"todos os {len(tcbs)} tipos"
    else:
        resumo_tcb = " · ".join(f"<b>{c}</b>" for c in tcb_sel)
    n_ifs = int(u["tcb"].isin(tcb_sel).sum())
    sb.markdown(
        f"<div class='filtro-ajuda'>{resumo_tcb} — {n_ifs} instituições</div>",
        unsafe_allow_html=True)

    # ---------------------------------------------------------------- segmento
    cont_sr = u["segmento_sr"].fillna(SEM_SEGMENTO).replace("", SEM_SEGMENTO).value_counts().to_dict()
    segs_brutos = sorted({s if s else SEM_SEGMENTO
                          for s in ind["segmento_sr"].fillna(SEM_SEGMENTO)})
    seg_escolha = sb.pills(
        "Segmento prudencial (SR)", segs_brutos, selection_mode="multi",
        default=segs_brutos,
        format_func=lambda c: (f"{ROTULO_SEM_SEGMENTO} ({cont_sr.get(c, 0)})"
                               if c == SEM_SEGMENTO else f"{c} ({cont_sr.get(c, 0)})"),
        help="S1 são as maiores; S5, as de perfil simplificado. "
             f"{ROTULO_SEM_SEGMENTO} = sem segmento atribuído na fonte.")
    seg_escolha = seg_escolha or segs_brutos
    # traduz de volta o rotulo do "sem segmento" para o valor real da base
    seg_sel = [("" if s == SEM_SEGMENTO else s) for s in seg_escolha]

    porte_min = sb.select_slider(
        "Carteira mínima", options=[0, 1e8, 5e8, 1e9, 5e9, 2e10, 1e11],
        value=1e9, format_func=fmt_reais,
        help="Percentil não distingue relevância: sem corte de tamanho, uma cooperativa "
             "de R$ 3 milhões pode liderar o ranking de crescimento sem qualquer "
             "consequência sistêmica.")

    with sb.expander("O que significam as siglas?"):
        st.markdown(glossario_html(gloss), unsafe_allow_html=True)

    # ---------------------------------------------------------------- agenda
    sb.markdown("<div class='filtro-titulo'>Critério da agenda</div>",
                unsafe_allow_html=True)
    limiar = sb.slider(
        "Score mínimo para entrar", 0.30, 0.95, 0.65, 0.01,
        help="Entra na agenda quem tiver score acima deste valor. Um limiar explícito é "
             "mais defensável que um corte em 'as N primeiras': com top-N, a última "
             "incluída e a primeira excluída podem diferir em 0,002 de score.")
    cobertura = sb.slider(
        "Cobertura da lista de grandes", 0.50, 0.95, 0.80, 0.05,
        format="%.0f%%",
        help="A segunda lista reúne as maiores instituições que, somadas, respondem por "
             "esta fatia da carteira do recorte. Todas estão na alçada da supervisão por "
             "tamanho; o score define a ordem em que se olha.")

    # ---------------------------------------------------------------- pesos
    sb.markdown("<div class='filtro-titulo'>Pesos do score</div>", unsafe_allow_html=True)
    sb.markdown(
        "<div class='filtro-ajuda'>O encadeamento é P1 filtra → P2 qualifica → P3 prioriza. "
        "Mudar os pesos muda a ordem da agenda — e isso é parte da decisão.</div>",
        unsafe_allow_html=True)
    rotulo_eixo = {"crescimento": "Crescimento", "concentracao": "Concentração",
                   "deterioracao": "Deterioração"}
    pesos = {e: sb.slider(rotulo_eixo.get(e, e.capitalize()), 0.0, 1.0,
                          pesos_padrao[e], 0.05) for e in eixos}
    if sum(pesos.values()) == 0:
        pesos = dict(pesos_padrao)
        sb.warning("Todos os pesos em zero — usando os padrões.")

    return {"dt_sel": dt_sel, "tcb_sel": tcb_sel, "seg_sel": seg_sel,
            "porte_min": porte_min, "pesos": pesos, "perfil": perfil,
            "limiar": limiar, "cobertura": cobertura}
