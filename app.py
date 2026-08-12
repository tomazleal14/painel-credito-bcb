"""
app.py -- Painel decisorio de credito | persona: Supervisao do Banco Central
Trabalho Intermediario -- FGV / Prof. Genaro Lins

Rodar local:  .venv/Scripts/streamlit.exe run app.py

Estrutura: 4 abas (Visao geral + P1/P2/P3), grade 2x2 de graficos por pergunta,
Leitura e Consequencia visiveis na tela, Referencia em expander.
TEMA ISOLADO em src/tema.py e .streamlit/config.toml.
"""
from __future__ import annotations

import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import cartoes
import filtros
import textos as _textos
from scoring import EIXOS, PESOS_PADRAO, agenda, agenda_grandes, calcula_scores
from tema import (ALTURA_GRAFICO, ALTURA_GRAFICO_GRANDE, ICONE_SEMAFORO,
                  SEMAFORO, TEMA, layout_base, monta_css)

DATA_PROC = RAIZ / "data_processed"
MIN_BASILEIA = 10.5
LIMIAR_BOOM = 0.15

st.set_page_config(page_title="Painel de Supervisão de Crédito — BCB",
                   page_icon="◧", layout="wide",
                   initial_sidebar_state="expanded")


# ------------------------------------------------------------------ dados
@st.cache_data(show_spinner="Carregando base…")
def carrega():
    # app_indicadores.parquet e a versao enxuta gerada por src/prepara_deploy.py (4 MB),
    # que e a versionada para o Streamlit Cloud. Em desenvolvimento local, cai no
    # arquivo completo se o enxuto ainda nao tiver sido gerado.
    enxuto = DATA_PROC / "app_indicadores.parquet"
    ind = pd.read_parquet(enxuto if enxuto.exists()
                          else DATA_PROC / "indicadores.parquet")
    sgs = pd.read_parquet(DATA_PROC / "sgs_series.parquet")
    scr = pd.read_parquet(DATA_PROC / "scr_agregado.parquet")
    cat = pd.read_csv(DATA_PROC / "catalogo_series_sgs.csv")
    defl = pd.read_csv(DATA_PROC / "deflator_ipca.csv")
    return ind, sgs, scr, cat, defl


ind, sgs, scr, cat_sgs, defl = carrega()
BASE_DEFL = int(defl["base_do_indice"].iloc[0])


# Textos: cache com chave no mtime de textos.toml. Salvar o arquivo muda o mtime,
# invalida este cache e o texto novo aparece ao recarregar a pagina -- sem reiniciar.
@st.cache_data(show_spinner=False)
def carrega_textos(assinatura: float):
    return _textos.carrega(assinatura)


T = carrega_textos(_textos.assinatura_arquivo())
LRC = T.LRC
NAO_PERMITE_CONCLUIR = T.NAO_PERMITE_CONCLUIR

# o CSS depende dos tamanhos de fonte definidos em [aparencia] no textos.toml
st.markdown(monta_css(T.aparencia), unsafe_allow_html=True)


def fmt_trimestre(dt: int) -> str:
    return f"{str(dt)[4:6]}/{str(dt)[:4]}"


def bloco_lrc(chave: str) -> None:
    """Leitura + Consequencia na tela; Referencia em expander (escolha do autor).

    Leitura e Consequencia vao dentro de uma <div> propria, entao o Markdown do
    textos.toml precisa ser convertido a mao (T.lrc). A Referencia usa st.markdown,
    que ja interpreta Markdown sozinho.
    """
    st.markdown(
        f"<div class='bloco-lrc'><b>Leitura.</b> {T.lrc(chave, 'leitura')}<br>"
        f"<b>Consequência.</b> {T.lrc(chave, 'consequencia')}</div>",
        unsafe_allow_html=True)
    with st.expander("Referência — contra o que isto é comparado"):
        st.markdown(LRC[chave]["referencia"])


def sem_html(nivel: str) -> str:
    return (f"<span style='color:{SEMAFORO[nivel]};font-size:1.15rem'>"
            f"{ICONE_SEMAFORO[nivel]}</span>")


def sem_grafico(fig: go.Figure, titulo: str = "", altura: int | None = None):
    fig.update_layout(**layout_base(titulo, altura))
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


def fonte(txt: str) -> None:
    st.markdown(f"<div class='rodape-fonte'>Fonte: {txt}</div>", unsafe_allow_html=True)


# ------------------------------------------------------------------ barra lateral
trimestres = sorted(ind["data_base"].unique())
f = filtros.barra_lateral(ind, PESOS_PADRAO, EIXOS)
dt_sel, tcb_sel = f["dt_sel"], f["tcb_sel"]
seg_sel, porte_min, pesos = f["seg_sel"], f["porte_min"], f["pesos"]
limiar, cobertura = f["limiar"], f["cobertura"]

# aplica filtros
base = ind[ind["tcb"].isin(tcb_sel) & ind["segmento_sr"].isin(seg_sel)].copy()
if base.empty:
    st.sidebar.error("Nenhuma instituição atende a esta combinação.")
    st.error("Nenhuma instituição atende aos filtros. Amplie a seleção na barra lateral.")
    st.stop()

scored = calcula_scores(base, grupo_pares="tcb", pesos=pesos)
univ = scored[(scored["data_base"] == dt_sel)
              & (scored["carteira_credito_real"] >= porte_min)].copy()

# resumo do recorte -- fecha o ciclo: o usuario ve o efeito do que escolheu
_carteira_tri = cartoes.num(univ["carteira_credito_real"].sum() / 1e12, 2)
st.sidebar.markdown(
    f"<div class='filtro-resumo'>Recorte atual<br>"
    f"<b>{len(univ)}</b> instituições · carteira somada "
    f"<b>R$ {_carteira_tri} tri</b><br>"
    f"data-base <b>{fmt_trimestre(dt_sel)}</b> · corte de "
    f"<b>{filtros.fmt_reais(porte_min)}</b></div>",
    unsafe_allow_html=True)
st.sidebar.caption(
    f"Valores reais em R$ de {fmt_trimestre(BASE_DEFL)}, deflacionados pelo IPCA (SGS 433). "
    f"Universo: IF.data, {fmt_trimestre(min(trimestres))}–{fmt_trimestre(max(trimestres))}.")


# ------------------------------------------------------------------ cabecalho
# Se textos.toml tiver erro de sintaxe, avisa em vez de quebrar o painel.
if T.erro:
    st.error(f"**Problema em `textos.toml`** — o painel segue com os textos padrão.\n\n"
             f"```\n{T.erro}\n```")
elif T.avisos:
    st.warning("Avisos de `textos.toml`: " + " · ".join(T.avisos))

st.markdown(
    f"<div class='cabecalho'><h1>{T.txt('cabecalho.titulo')}</h1>"
    f"<div class='sub'>{T.txt('cabecalho.subtitulo')}</div>"
    f"<div class='assinatura'>{T.txt('cabecalho.assinatura')}</div></div>",
    unsafe_allow_html=True)

aba0, aba1, aba2, aba3, aba4 = st.tabs([
    "Visão geral", "P1 · Crescimento", "P2 · Concentração",
    "P3 · Deterioração", "Comparador"])


# ================================================================== VISÃO GERAL
with aba0:
    lista = agenda(scored, dt_sel, minimo_carteira=porte_min, limiar=limiar)
    lista_grandes = agenda_grandes(scored, dt_sel, cobertura=cobertura)

    # o `help` de cada métrica decifra a sigla sem exigir que se saia da tela
    c = st.columns(5)
    c[0].metric("Instituições no recorte", cartoes.num(len(univ), 0),
                help="Quantas instituições passam pelos filtros da barra lateral, "
                     "incluindo o corte de carteira mínima.")
    c[1].metric("Carteira do recorte",
                f"R$ {cartoes.num(univ['carteira_credito_real'].sum()/1e12, 2)} tri",
                help=f"Soma da carteira de crédito das instituições do recorte, em reais "
                     f"de {fmt_trimestre(BASE_DEFL)} (deflacionada pelo IPCA).")
    hhi = univ["p2_1_hhi_sistema"].dropna()
    c[2].metric("HHI do sistema",
                cartoes.num(hhi.iloc[0], 0) if len(hhi) else "—",
                help="Índice Herfindahl-Hirschman: soma dos quadrados das participações "
                     "de mercado, de 0 a 10.000. Abaixo de 1.500 = desconcentrado; "
                     "1.500 a 2.500 = moderadamente concentrado; acima = concentrado.")
    cr5 = univ["p2_2_cr5_sistema_pct"].dropna()
    c[3].metric("CR5",
                f"{cartoes.num(cr5.iloc[0], 1)}%" if len(cr5) else "—",
                help="Concentration ratio dos 5 maiores: fatia da carteira detida pelas "
                     "cinco maiores instituições. Complementa o HHI, que pode ser baixo "
                     "por haver milhares de cooperativas pequenas.")
    cresc_med = univ["p1_1_cresc_real_aa"].median()
    c[4].metric("Crescimento real mediano",
                f"{cartoes.num(cresc_med*100, 1)}%" if pd.notna(cresc_med) else "—",
                help="Mediana do crescimento da carteira em 12 meses, já descontada a "
                     "inflação (IPCA). É a variável-mestra de P1.")

    # ---- cartoes por eixo: score, sparkline e decomposicao nos indicadores ----
    st.markdown(f"#### {T.bruto('sintese.titulo', 'Os três eixos, decompostos')}")
    hist = scored[scored["carteira_credito_real"] >= porte_min]
    gloss_ind = T.glossario_indicadores
    cols_eixo = st.columns(3, gap="medium")
    for i, eixo in enumerate(EIXOS):
        with cols_eixo[i]:
            st.markdown(
                cartoes.cartao_eixo(
                    hist, univ, eixo,
                    T.txt(f"eixos.{eixo}.rotulo", eixo.capitalize()),
                    T.txt(f"eixos.{eixo}.descricao", ""),
                    glossario=gloss_ind,
                    # os eixos NAO tem o mesmo numero de percentis: concentracao usa 4,
                    # porque HHI do sistema e CR5 sao iguais para todas as instituicoes
                    # e nao geram percentil. Isso fica declarado no cartao.
                    n_percentis=len(cartoes.INDICADORES_POR_EIXO.get(eixo, []))),
                unsafe_allow_html=True)

    # ---- o que o numero grande significa, e a sintese dos achados ----
    st.markdown(
        f"<div class='bloco-lrc'><b>O que é o número.</b> {T.txt('sintese.o_que_e_o_numero')}"
        f"<br><br><b>Como ler.</b> {T.txt('sintese.como_ler')}"
        f"<br><br><b>Quem é marcado como risco alto.</b> "
        f"{T.txt('sintese.por_que_decompor')}"
        f"<br><br><b>Os componentes.</b> {T.txt('sintese.os_componentes')}</div>",
        unsafe_allow_html=True)

    # sintese factual do trimestre, calculada -- nao escrita a mao.
    # Ordena a pressao por CARTEIRA EXPOSTA, nao por contagem de instituicoes: 54
    # cooperativas pequenas sinalizadas pesam menos que um grande banco sinalizado.
    exposta = {e: cartoes.carteira_exposta(univ, e) for e in EIXOS}
    exposta = {e: (float(s.iloc[-1]) if len(s) else 0.0) for e, s in exposta.items()}
    n_alto = {e: int((univ[f"sem_{e}"] == "alto").sum()) for e in EIXOS}
    pior = max(exposta, key=exposta.get)
    rot = {e: T.bruto(f"eixos.{e}.rotulo", e).lower() for e in EIXOS}
    quadrante = univ[(univ["p1_1_cresc_real_aa"] > univ["p1_1_cresc_real_aa"].median())
                     & (univ["p3_1_inadimplencia"] < univ["p3_1_inadimplencia"].median())]
    carteira_quadrante = (quadrante["carteira_credito_real"].sum()
                          / univ["carteira_credito_real"].sum() * 100
                          if univ["carteira_credito_real"].sum() else 0.0)
    st.markdown(
        f"<div class='aviso'><b>Neste recorte ({fmt_trimestre(dt_sel)}):</b> "
        f"a carteira exposta a risco alto é de "
        f"<b>{cartoes.num(exposta['crescimento'], 1)}%</b> em crescimento, "
        f"<b>{cartoes.num(exposta['concentracao'], 1)}%</b> em concentração e "
        f"<b>{cartoes.num(exposta['deterioracao'], 1)}%</b> em deterioração — "
        f"a maior pressão vem de <b>{rot[pior]}</b> "
        f"({n_alto[pior]} instituições sinalizadas). "
        f"<b>{len(quadrante)}</b> instituições, com "
        f"<b>{cartoes.num(carteira_quadrante, 1)}%</b> da carteira, estão no "
        f"quadrante-assinatura de P3 — crescem acima da mediana e ainda exibem "
        f"inadimplência abaixo dela, que é onde o efeito denominador costuma esconder "
        f"perda futura.</div>",
        unsafe_allow_html=True)

    with st.expander("O que cada indicador mede — glossário dos 18"):
        st.markdown(cartoes.tabela_glossario(gloss_ind), unsafe_allow_html=True)
        st.markdown(
            f"<div class='rodape-fonte' style='margin-top:10px'>"
            f"<b>HHI do sistema</b> e <b>CR5</b> descrevem o mercado inteiro e são iguais "
            f"para todas as instituições no trimestre — por isso são dois dos 18 "
            f"indicadores, mas não entram no score de nenhuma instituição: ranqueá-las "
            f"por um número idêntico para todas não teria sentido. Eles definem o "
            f"contexto em que o resto é lido.<br><br>"
            f"Os textos deste glossário ficam em <code>textos.toml</code>, seção "
            f"<code>[glossario_indicadores]</code>. Cada indicador também aparece como "
            f"dica ao passar o mouse sobre o nome, nos cartões.</div>",
            unsafe_allow_html=True)

    st.markdown(f"#### {T.txt('agenda.titulo')} — {fmt_trimestre(dt_sel)}")
    st.markdown(
        f"<div class='bloco-lrc'><b>Leitura.</b> {T.txt('agenda.leitura')}<br>"
        f"<b>Consequência.</b> {T.txt('agenda.consequencia')}</div>",
        unsafe_allow_html=True)

    # ---- duas listas, porque sao duas perguntas diferentes ----
    # O score mede ATIPICIDADE dentro do grupo de pares. Isso nao e o mesmo que
    # relevancia sistemica: com uma lista so, os cinco maiores bancos do pais ficavam
    # entre a 548a e a 1046a posicao e nao entravam na agenda.
    def monta_tabela(dados: pd.DataFrame) -> pd.DataFrame:
        return pd.DataFrame([{
            "#": int(r.posicao),
            "Instituição": r.instituicao,
            "TCB": r.tcb,
            "Seg.": r.segmento_sr,
            "Carteira": r.carteira_credito_real / 1e9,
            "Cresc. real a.a.": r.p1_1_cresc_real_aa,
            "Inadimpl.": r.p3_1_inadimplencia,
            "Cobertura": r.p3_2_cobertura,
            "Basileia": r.indice_basileia,
            "Cresc.": ICONE_SEMAFORO[r.sem_crescimento],
            "Conc.": ICONE_SEMAFORO[r.sem_concentracao],
            "Deter.": ICONE_SEMAFORO[r.sem_deterioracao],
            "Score": r.score_final,
        } for r in dados.itertuples()])

    # `help` de cada coluna: e onde a variavel e decifrada, sem sair da tabela
    COLUNAS = {
        "#": st.column_config.NumberColumn(
            "#", width="small", format="%d",
            help="Posição NESTA lista, da mais prioritária para a menos. "
                 "Não é o ranking geral do sistema."),
        "Instituição": st.column_config.TextColumn("Instituição", width="large"),
        "TCB": st.column_config.TextColumn(
            "TCB", width="small",
            help="Tipo de Consolidado Bancário — a classificação do BCB por modelo de "
                 "negócio. O glossário completo está na barra lateral."),
        "Seg.": st.column_config.TextColumn(
            "Seg.", width="small",
            help="Segmento prudencial da Res. 4.553/2017. S1 são as maiores; "
                 "S5, as de perfil simplificado."),
        "Carteira": st.column_config.NumberColumn(
            "Carteira (R$ bi)", format="%.1f",
            help="Carteira de crédito, em bilhões de reais de 03/2026, deflacionada "
                 "pelo IPCA (SGS 433)."),
        "Cresc. real a.a.": st.column_config.NumberColumn(
            "Cresc. real a.a.", format="percent",
            help="Crescimento da carteira em 12 meses, já descontada a inflação. "
                 "É a variável-mestra de P1: acima de 15% a.a. real é o limiar de "
                 "crescimento acelerado adotado aqui."),
        "Inadimpl.": st.column_config.NumberColumn(
            "Inadimpl.", format="percent",
            help="Carteira em atraso acima de 90 dias, sobre a carteira total. "
                 "Cuidado com o efeito denominador: carteira que cresce rápido dilui "
                 "este índice e esconde perda futura."),
        "Cobertura": st.column_config.NumberColumn(
            "Cobertura", format="percent",
            help="Provisão dividida pela carteira em atraso. 100% cobre integralmente "
                 "o atraso; abaixo disso há perda ainda não reconhecida no balanço."),
        "Basileia": st.column_config.NumberColumn(
            "Basileia", format="percent",
            help="Índice de Basileia: capital sobre ativos ponderados pelo risco. "
                 "O mínimo de referência é 10,5% (8% de requisito mais 2,5% de "
                 "conservação)."),
        "Cresc.": st.column_config.TextColumn("Cresc.", width="small",
                                              help="Semáforo do eixo Crescimento."),
        "Conc.": st.column_config.TextColumn("Conc.", width="small",
                                             help="Semáforo do eixo Concentração."),
        "Deter.": st.column_config.TextColumn("Deter.", width="small",
                                              help="Semáforo do eixo Deterioração."),
        "Score": st.column_config.ProgressColumn(
            "Score", format="%.3f", min_value=0.0, max_value=1.0,
            help="Score composto de posição relativa, de 0 a 1: média dos percentis dos "
                 "indicadores dentro do grupo de pares (mesmo TCB), ponderada pelos "
                 "pesos da barra lateral. 0,50 = mediana do grupo."),
    }

    t1, t2 = st.tabs([f"Atípicas no grupo de pares ({len(lista)})",
                      f"Grandes com sinal ({len(lista_grandes)})"])

    with t1:
        st.markdown(
            f"<div class='aviso'>Entram as instituições com <b>score ≥ {limiar:.2f}</b> "
            f"e carteira ≥ {filtros.fmt_reais(porte_min)}: <b>{len(lista)}</b> de "
            f"{len(univ)} no recorte. Esta lista mede <b>atipicidade dentro do grupo de "
            f"pares</b> — quem está muito fora do padrão do próprio tipo de instituição. "
            f"Não mede relevância sistêmica: as {len(lista)} somam "
            f"{lista['carteira_credito_real'].sum()/univ['carteira_credito_real'].sum()*100:.1f}% "
            f"da carteira do recorte.</div>",
            unsafe_allow_html=True)
        if lista.empty:
            st.warning(f"Nenhuma instituição atinge score {limiar:.2f}. "
                       "Baixe o limiar na barra lateral.")
        else:
            st.dataframe(monta_tabela(lista), width='stretch', hide_index=True,
                         height=min(560, 60 + 35 * len(lista)), column_config=COLUNAS)

    with t2:
        st.markdown(
            f"<div class='aviso'>As maiores instituições que somadas respondem por "
            f"<b>{cobertura:.0%}</b> da carteira do recorte — <b>{len(lista_grandes)}</b> "
            f"instituições. Todas estão na alçada da supervisão por tamanho; aqui o score "
            f"não decide quem entra, decide <b>a ordem em que se olha</b>. É a correção da "
            f"distorção da primeira lista, em que os cinco maiores bancos do país ficavam "
            f"de fora da agenda.</div>",
            unsafe_allow_html=True)
        if lista_grandes.empty:
            st.warning("Sem dados de carteira no recorte.")
        else:
            st.dataframe(monta_tabela(lista_grandes), width='stretch', hide_index=True,
                         height=min(560, 60 + 35 * len(lista_grandes)),
                         column_config=COLUNAS)

    st.markdown(
        f"<div class='rodape-fonte'>"
        f"{sem_html('alto')} risco alto (percentil ≥ 75 no grupo de pares) &nbsp;·&nbsp; "
        f"{sem_html('medio')} atenção (≥ 50) &nbsp;·&nbsp; "
        f"{sem_html('baixo')} baixo (&lt; 50) &nbsp;·&nbsp; "
        f"{sem_html('sem')} sem dado suficiente &nbsp;·&nbsp; "
        f"passe o mouse no cabeçalho de cada coluna para ver o que ela mede</div>",
        unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    if not lista.empty:
        c1.download_button(
            "Baixar lista de atípicas (CSV)",
            monta_tabela(lista).to_csv(index=False).encode("utf-8-sig"),
            file_name=f"agenda_atipicas_{dt_sel}.csv", mime="text/csv")
    if not lista_grandes.empty:
        c2.download_button(
            "Baixar lista de grandes (CSV)",
            monta_tabela(lista_grandes).to_csv(index=False).encode("utf-8-sig"),
            file_name=f"agenda_grandes_{dt_sel}.csv", mime="text/csv")

    fonte(f"BCB/IF.data, data-base {fmt_trimestre(dt_sel)}. Valores reais em R$ de "
          f"{fmt_trimestre(BASE_DEFL)} (IPCA, SGS 433). Extração em 12/08/2026.")

    st.markdown("---")
    st.markdown(NAO_PERMITE_CONCLUIR)


# ------------------------------------------------------------------ auxiliares de grafico
def _hover(d: pd.DataFrame) -> list[str]:
    return [f"<b>{r.instituicao}</b><br>TCB {r.tcb} · Seg. {r.segmento_sr}"
            f"<br>Carteira: R$ {r.carteira_credito_real/1e9:,.1f} bi"
            for r in d.itertuples()]


def _tamanho(d: pd.DataFrame, maximo: int = 46) -> pd.Series:
    v = d["carteira_credito_real"].clip(lower=0).pow(0.5)
    if v.max() and v.max() > 0:
        return 8 + (v / v.max()) * maximo
    return pd.Series(12, index=d.index)


INDICADORES_DA_ABA = {
    "p1": ["p1_1_cresc_real_aa", "p1_2_credit_gap", "p1_3_trim_consec_acima",
           "p1_4_cresc_carteira_sobre_capital", "p1_5_cresc_alto_risco_aa",
           "p1_6_var_share_pp"],
    "p2": ["p2_1_hhi_sistema", "p2_2_cr5_sistema_pct", "p2_3_pct_alto_risco",
           "p2_4_hhi_regional", "p2_5_pct_grande_porte", "p2_6_loan_to_deposit"],
    "p3": ["p3_1_inadimplencia", "p3_2_cobertura", "p3_3_provisao_sobre_carteira",
           "p3_4_inadimplencia_ajustada", "p3_5_ativos_problematicos",
           "p3_6_folga_capital_pp"],
}
NOTAS_CARTAO = {
    "p2_5_pct_grande_porte": "só carteira PJ; sem PJ o campo fica vazio",
    "p3_1_inadimplencia": "regime ECL, a partir de 2025Q1",
    "p3_2_cobertura": "≥ 100% cobre todo o atraso",
    "p3_6_folga_capital_pp": "sobre o mínimo de 10,5%",
    "p1_2_credit_gap": "exige 12 trimestres no mesmo universo",
}


def faixa_cartoes(pergunta: str) -> None:
    """Os 6 indicadores da pergunta como cartoes: valor, minisserie e faixa do universo."""
    cols = INDICADORES_DA_ABA[pergunta]
    hist = scored[scored["carteira_credito_real"] >= porte_min]
    linha1, linha2 = st.columns(3, gap="medium"), None
    for i, c in enumerate(cols):
        if i == 3:
            linha2 = st.columns(3, gap="medium")
        alvo = (linha1 if i < 3 else linha2)[i % 3]
        with alvo:
            st.markdown(
                cartoes.cartao_indicador(hist, univ, c, NOTAS_CARTAO.get(c, ""),
                                         glossario=T.glossario_indicadores),
                unsafe_allow_html=True)
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def cresc_por_modalidade(_df: pd.DataFrame, dt: int) -> pd.DataFrame:
    """Crescimento real anual por modalidade PF, por instituição."""
    mods = {"pf_cartao_real": "Cartão", "pf_sem_consignacao_real": "Sem consignação",
            "pf_consignado_real": "Consignado", "pf_veiculos_real": "Veículos",
            "pf_habitacao_real": "Habitação", "pf_rural_real": "Rural"}
    mods = {k: v for k, v in mods.items() if k in _df.columns}
    d = _df.sort_values(["cod_inst", "data_base"])
    saida = d[["data_base", "cod_inst", "instituicao"]].copy()
    for col, nome in mods.items():
        saida[nome] = d.groupby("cod_inst")[col].transform(lambda s: s / s.shift(4) - 1)
    return saida[saida["data_base"] == dt]


# ================================================================== P1
with aba1:
    st.markdown(f"#### {T.txt('abas.p1')}")
    faixa_cartoes("p1")
    d = univ.dropna(subset=["p1_1_cresc_real_aa"]).copy()
    l1c1, l1c2 = st.columns(2)

    # ---- 1. scatter crescimento x market share
    with l1c1:
        st.markdown(f"**{LRC['p1_1']['titulo']}**")
        if d.empty:
            st.info("Sem dados para o recorte.")
        else:
            med = d["p1_1_cresc_real_aa"].median()
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=d["p1_1_cresc_real_aa"] * 100, y=d["share_carteira"] * 100,
                mode="markers", text=_hover(d), hoverinfo="text",
                marker=dict(size=_tamanho(d), color=TEMA["marca"], opacity=0.55,
                            line=dict(width=0.5, color="white"))))
            fig.add_vline(x=med * 100, line=dict(color=TEMA["referencia"], width=1),
                          annotation_text="mediana", annotation_position="top")
            fig.add_vline(x=LIMIAR_BOOM * 100,
                          line=dict(color=TEMA["risco_alto"], width=1, dash="dash"),
                          annotation_text="15% a.a.", annotation_position="top right")
            fig.update_yaxes(type="log", title="Participação na carteira (%, log)")
            fig.update_xaxes(title="Crescimento real da carteira (% a.a.)")
            sem_grafico(fig)
        bloco_lrc("p1_1")

    # ---- 2. carteira x tendencia HP
    with l1c2:
        st.markdown(f"**{LRC['p1_2']['titulo']}**")
        cands = (univ.dropna(subset=["p1_2_credit_gap"])
                     .nlargest(4, "p1_2_credit_gap")["cod_inst"].tolist())
        if not cands:
            st.info("Série insuficiente para o filtro HP no recorte.")
        else:
            hist = scored[scored["cod_inst"].isin(cands)].sort_values("data_base")
            fig = go.Figure()
            cores = TEMA["sequencial"][2:]
            for i, cod in enumerate(cands):
                h = hist[hist["cod_inst"] == cod]
                nome = h["instituicao"].iloc[-1][:26]
                fig.add_trace(go.Scatter(
                    x=[fmt_trimestre(x) for x in h["data_base"]],
                    y=h["p1_2_credit_gap"] * 100, mode="lines+markers", name=nome,
                    line=dict(width=2, color=cores[i % len(cores)]),
                    marker=dict(size=4)))
            fig.add_hline(y=0, line=dict(color=TEMA["referencia"], width=1))
            fig.update_yaxes(title="Desvio da própria tendência (%)")
            sem_grafico(fig)
        bloco_lrc("p1_2")

    l2c1, l2c2 = st.columns(2)

    # ---- 3. heatmap crescimento por modalidade
    with l2c1:
        st.markdown(f"**{LRC['p1_3']['titulo']}**")
        cm = cresc_por_modalidade(scored, dt_sel)
        cm = cm[cm["cod_inst"].isin(univ["cod_inst"])]
        mods = [c for c in cm.columns if c not in ("data_base", "cod_inst", "instituicao")]
        cm = cm.dropna(subset=mods, how="all")
        if cm.empty:
            st.info("Sem dados de modalidade no recorte.")
        else:
            ordem = (univ.set_index("cod_inst")["p1_1_cresc_real_aa"]
                          .reindex(cm["cod_inst"]).fillna(-9).values)
            cm = cm.assign(_o=ordem).nlargest(14, "_o")
            z = cm[mods].astype(float).values * 100
            fig = go.Figure(go.Heatmap(
                z=z, x=mods, y=[n[:26] for n in cm["instituicao"]],
                colorscale=[[0, TEMA["risco_baixo"]], [0.5, "#F2F2F2"],
                            [1, TEMA["risco_alto"]]],
                zmid=0, zmin=-50, zmax=100,
                colorbar=dict(title="% a.a.", thickness=10),
                hovertemplate="%{y}<br>%{x}: %{z:.1f}% a.a.<extra></extra>"))
            sem_grafico(fig)
        bloco_lrc("p1_3")

    # ---- 4. crescimento carteira vs capital
    with l2c2:
        st.markdown(f"**{LRC['p1_4']['titulo']}**")
        dc = univ.dropna(subset=["p1_4_cresc_carteira_sobre_capital"]).copy()
        dc = dc[dc["p1_4_cresc_carteira_sobre_capital"].between(0, 4)]
        dc = dc.nlargest(15, "p1_4_cresc_carteira_sobre_capital")
        if dc.empty:
            st.info("Sem dados de capital no recorte (relatório só existe a partir de 2023Q3).")
        else:
            cores = [TEMA["risco_alto"] if v > 1.2 else
                     TEMA["risco_medio"] if v > 1.0 else TEMA["marca"]
                     for v in dc["p1_4_cresc_carteira_sobre_capital"]]
            fig = go.Figure(go.Bar(
                x=dc["p1_4_cresc_carteira_sobre_capital"],
                y=[n[:28] for n in dc["instituicao"]],
                orientation="h", marker_color=cores,
                hovertemplate="%{y}<br>razão: %{x:.2f}<extra></extra>"))
            fig.add_vline(x=1.0, line=dict(color=TEMA["referencia"], width=1.5, dash="dash"),
                          annotation_text="pari passu")
            fig.update_xaxes(title="Crescimento da carteira ÷ crescimento do capital")
            fig.update_yaxes(autorange="reversed")
            sem_grafico(fig)
        bloco_lrc("p1_4")

    fonte("BCB/IF.data (Resumo e Informações de Capital) e BCB/SCR.data. "
          f"Valores reais em R$ de {fmt_trimestre(BASE_DEFL)}.")


# ================================================================== P2
with aba2:
    st.markdown(f"#### {T.txt('abas.p2')}")
    faixa_cartoes("p2")
    m1c1, m1c2 = st.columns(2)

    # ---- 1. HHI e CR5 do sistema
    with m1c1:
        st.markdown(f"**{LRC['p2_1']['titulo']}**")
        sist = (scored.groupby("data_base")
                      .agg(hhi=("p2_1_hhi_sistema", "first"),
                           cr5=("p2_2_cr5_sistema_pct", "first"))
                      .reset_index())
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[fmt_trimestre(x) for x in sist["data_base"]],
                                 y=sist["hhi"], name="HHI", mode="lines+markers",
                                 line=dict(color=TEMA["marca"], width=2.5),
                                 marker=dict(size=4)))
        fig.add_trace(go.Scatter(x=[fmt_trimestre(x) for x in sist["data_base"]],
                                 y=sist["cr5"], name="CR5 (%)", mode="lines+markers",
                                 yaxis="y2", line=dict(color=TEMA["risco_medio"], width=2.5),
                                 marker=dict(size=4)))
        fig.add_hline(y=1500, line=dict(color=TEMA["referencia"], width=1, dash="dot"),
                      annotation_text="1.500 — moderadamente concentrado")
        fig.update_layout(yaxis=dict(title="HHI"),
                          yaxis2=dict(title="CR5 (%)", overlaying="y", side="right",
                                      showgrid=False))
        sem_grafico(fig)
        bloco_lrc("p2_1")

    # ---- 2. composicao da carteira PF
    with m1c2:
        st.markdown(f"**{LRC['p2_2']['titulo']}**")
        mods = {"pf_cartao_real": "Cartão", "pf_sem_consignacao_real": "Sem consignação",
                "pf_consignado_real": "Consignado", "pf_veiculos_real": "Veículos",
                "pf_habitacao_real": "Habitação", "pf_rural_real": "Rural",
                "pf_outros_real": "Outros"}
        mods = {k: v for k, v in mods.items() if k in univ.columns}
        dp = univ.dropna(subset=["pf_total_real"])
        dp = dp[dp["pf_total_real"] > 0].nlargest(12, "p2_3_pct_alto_risco")
        if dp.empty:
            st.info("Sem carteira PF relevante no recorte.")
        else:
            fig = go.Figure()
            paleta = {"Cartão": TEMA["risco_alto"], "Sem consignação": TEMA["risco_medio"],
                      "Consignado": TEMA["marca_clara"], "Veículos": TEMA["marca"],
                      "Habitação": TEMA["sequencial"][2], "Rural": TEMA["sequencial"][1],
                      "Outros": TEMA["neutro"]}
            for col, nome in mods.items():
                fig.add_trace(go.Bar(
                    y=[n[:24] for n in dp["instituicao"]],
                    x=(dp[col] / dp["pf_total_real"] * 100).fillna(0),
                    name=nome, orientation="h",
                    marker_color=paleta.get(nome, TEMA["neutro"]),
                    hovertemplate="%{y}<br>" + nome + ": %{x:.1f}%<extra></extra>"))
            fig.update_layout(barmode="stack")
            fig.update_xaxes(title="% da carteira PF")
            fig.update_yaxes(autorange="reversed")
            sem_grafico(fig)
        bloco_lrc("p2_2")

    m2c1, m2c2 = st.columns(2)

    # ---- 3. concentracao regional
    with m2c1:
        st.markdown(f"**{LRC['p2_3']['titulo']}**")
        cols_reg = {"reg_sudeste_real": "Sudeste", "reg_sul_real": "Sul",
                    "reg_nordeste_real": "Nordeste", "reg_norte_real": "Norte",
                    "reg_centro_oeste_real": "Centro-oeste"}
        cols_reg = {k: v for k, v in cols_reg.items() if k in univ.columns}
        dr = univ.dropna(subset=["p2_4_hhi_regional"]).nlargest(12, "p2_4_hhi_regional")
        if dr.empty or not cols_reg:
            st.info("Sem dados regionais no recorte.")
        else:
            tot = dr[list(cols_reg)].sum(axis=1).replace(0, pd.NA)
            fig = go.Figure()
            for i, (col, nome) in enumerate(cols_reg.items()):
                fig.add_trace(go.Bar(
                    y=[n[:24] for n in dr["instituicao"]],
                    x=(dr[col] / tot * 100).fillna(0), name=nome, orientation="h",
                    marker_color=TEMA["sequencial"][(i + 1) % len(TEMA["sequencial"])],
                    hovertemplate="%{y}<br>" + nome + ": %{x:.1f}%<extra></extra>"))
            fig.update_layout(barmode="stack")
            fig.update_xaxes(title="% da carteira por região")
            fig.update_yaxes(autorange="reversed")
            sem_grafico(fig)
        bloco_lrc("p2_3")

    # ---- 4. loan-to-deposit x crescimento
    with m2c2:
        st.markdown(f"**{LRC['p2_4']['titulo']}**")
        dl = univ.dropna(subset=["p2_6_loan_to_deposit", "p1_1_cresc_real_aa"])
        dl = dl[dl["p2_6_loan_to_deposit"].between(0, 5)]
        if dl.empty:
            st.info("Sem dados de funding no recorte.")
        else:
            fig = go.Figure(go.Scatter(
                x=dl["p1_1_cresc_real_aa"] * 100, y=dl["p2_6_loan_to_deposit"],
                mode="markers", text=_hover(dl), hoverinfo="text",
                marker=dict(size=_tamanho(dl), color=TEMA["marca"], opacity=0.55,
                            line=dict(width=0.5, color="white"))))
            fig.add_hline(y=1.0, line=dict(color=TEMA["referencia"], width=1, dash="dash"),
                          annotation_text="carteira = captações")
            fig.add_vline(x=dl["p1_1_cresc_real_aa"].median() * 100,
                          line=dict(color=TEMA["referencia"], width=1),
                          annotation_text="mediana")
            fig.update_xaxes(title="Crescimento real da carteira (% a.a.)")
            fig.update_yaxes(title="Carteira ÷ captações")
            sem_grafico(fig)
        bloco_lrc("p2_4")

    fonte("BCB/IF.data (Resumo, carteira por modalidade e por região geográfica); "
          "ESTBAN para detalhe municipal (corte transversal, últimos 6 meses).")


# ================================================================== P3
with aba3:
    st.markdown(f"#### {T.txt('abas.p3')}")
    faixa_cartoes("p3")

    regime = univ["regime_contabil"].dropna().unique()
    if len(regime):
        st.markdown(
            f"<div class='aviso'><b>Regime contábil desta data-base:</b> {regime[0]}. "
            "A Res. CMN 4.966/2021 trocou a classificação AA–H por perda esperada em 01/2025. "
            "As duas metodologias <b>não formam série contínua</b> e o painel não as encadeia — "
            "a soma dos níveis E–H fica cerca de 2,5 p.p. acima da inadimplência de 90 dias.</div>",
            unsafe_allow_html=True)

    # ---- 1. GRÁFICO-ASSINATURA (linha inteira da grade)
    st.markdown(f"**{LRC['p3_1']['titulo']}**")
    da = univ.dropna(subset=["p1_1_cresc_real_aa", "p3_1_inadimplencia"]).copy()
    if da.empty:
        st.info("Sem dados de inadimplência nesta data-base (disponível a partir de 2025Q1).")
    else:
        med_x = da["p1_1_cresc_real_aa"].median()
        med_y = da["p3_1_inadimplencia"].median()
        cob = da["p3_2_cobertura"].clip(0, 3)

        fig = go.Figure()
        # quadrante de agenda prioritária: cresce muito + inadimplência ainda baixa
        fig.add_shape(type="rect", x0=med_x * 100, x1=max(da["p1_1_cresc_real_aa"]) * 100 * 1.06,
                      y0=0, y1=med_y * 100,
                      fillcolor="rgba(179,38,30,0.07)",
                      line=dict(color=TEMA["risco_alto"], width=1, dash="dot"), layer="below")
        fig.add_annotation(x=max(da["p1_1_cresc_real_aa"]) * 100 * 0.99, y=med_y * 100 * 0.06,
                           text="<b>AGENDA PRIORITÁRIA</b><br>cresce muito · inadimplência ainda baixa",
                           showarrow=False, xanchor="right", align="right",
                           font=dict(size=11, color=TEMA["risco_alto"]))

        fig.add_trace(go.Scatter(
            x=da["p1_1_cresc_real_aa"] * 100, y=da["p3_1_inadimplencia"] * 100,
            mode="markers",
            text=[f"<b>{r.instituicao}</b><br>TCB {r.tcb} · Seg. {r.segmento_sr}"
                  f"<br>Carteira: R$ {r.carteira_credito_real/1e9:,.1f} bi"
                  f"<br>Crescimento real: {r.p1_1_cresc_real_aa*100:.1f}% a.a."
                  f"<br>Inadimplência: {r.p3_1_inadimplencia*100:.2f}%"
                  f"<br>Cobertura: " + (f"{r.p3_2_cobertura*100:.0f}%"
                                        if pd.notna(r.p3_2_cobertura) else "sem dado")
                  for r in da.itertuples()],
            hoverinfo="text",
            marker=dict(size=_tamanho(da, 54), color=cob,
                        colorscale=[[0, TEMA["risco_alto"]], [0.45, TEMA["risco_medio"]],
                                    [1, TEMA["risco_baixo"]]],
                        cmin=0, cmax=3, opacity=0.78,
                        line=dict(width=0.6, color="white"),
                        colorbar=dict(title="Cobertura<br>(provisão÷atraso)", thickness=12,
                                      tickvals=[0, 1, 2, 3],
                                      ticktext=["0%", "100%", "200%", "300%"]))))
        fig.add_vline(x=med_x * 100, line=dict(color=TEMA["referencia"], width=1),
                      annotation_text="mediana de crescimento")
        fig.add_hline(y=med_y * 100, line=dict(color=TEMA["referencia"], width=1),
                      annotation_text="mediana de inadimplência")
        fig.update_xaxes(title="Crescimento real da carteira (% a.a.)")
        fig.update_yaxes(title="Inadimplência sobre a carteira (%)")
        sem_grafico(fig, altura=ALTURA_GRAFICO_GRANDE)

        prio = da[(da["p1_1_cresc_real_aa"] > med_x) & (da["p3_1_inadimplencia"] < med_y)]
        baixa_prov = prio[prio["p3_3_provisao_sobre_carteira"]
                          < prio["p3_3_provisao_sobre_carteira"].median()]
        st.markdown(
            f"<div class='aviso'><b>{len(prio)}</b> instituições estão no quadrante de agenda "
            f"prioritária; <b>{len(baixa_prov)}</b> delas também provisionam abaixo da mediana "
            f"do quadrante — a combinação que o trabalho persegue.</div>",
            unsafe_allow_html=True)
    bloco_lrc("p3_1")

    n1, n2, n3 = st.columns(3)

    # ---- 2. efeito denominador
    with n1:
        st.markdown(f"**{LRC['p3_2']['titulo']}**")
        dd = univ.dropna(subset=["p3_1_inadimplencia", "p3_4_inadimplencia_ajustada"])
        if dd.empty:
            st.info("Sem dados nesta data-base.")
        else:
            lim = max(dd["p3_4_inadimplencia_ajustada"].quantile(0.97),
                      dd["p3_1_inadimplencia"].quantile(0.97)) * 100
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=[0, lim], y=[0, lim], mode="lines",
                                     line=dict(color=TEMA["referencia"], width=1, dash="dash"),
                                     name="igualdade", hoverinfo="skip"))
            fig.add_trace(go.Scatter(
                x=dd["p3_1_inadimplencia"] * 100, y=dd["p3_4_inadimplencia_ajustada"] * 100,
                mode="markers", text=_hover(dd), hoverinfo="text", showlegend=False,
                marker=dict(size=_tamanho(dd, 34), color=TEMA["marca"], opacity=0.55,
                            line=dict(width=0.5, color="white"))))
            fig.update_xaxes(title="Inadimplência corrente (%)", range=[0, lim])
            fig.update_yaxes(title="Ajustada ao crescimento (%)", range=[0, lim])
            sem_grafico(fig)
        bloco_lrc("p3_2")

    # ---- 3. cobertura x ativos problematicos
    with n2:
        st.markdown(f"**{LRC['p3_3']['titulo']}**")
        dq = univ.dropna(subset=["p3_2_cobertura", "p3_5_ativos_problematicos"])
        dq = dq[dq["p3_2_cobertura"].between(0, 5)]
        ref_scr = scr[(scr["modalidade"] == "Todas") & (scr["cliente"] == "Todos")
                      & (scr["mes"] == dt_sel)]["ativo_problematico"]
        if dq.empty:
            st.info("Sem dados nesta data-base.")
        else:
            fig = go.Figure(go.Scatter(
                x=dq["p3_2_cobertura"] * 100, y=dq["p3_5_ativos_problematicos"] * 100,
                mode="markers", text=_hover(dq), hoverinfo="text",
                marker=dict(size=_tamanho(dq, 34), color=TEMA["marca"], opacity=0.55,
                            line=dict(width=0.5, color="white"))))
            fig.add_vline(x=100, line=dict(color=TEMA["risco_alto"], width=1.2, dash="dash"),
                          annotation_text="cobertura 100%")
            if len(ref_scr):
                fig.add_hline(y=float(ref_scr.iloc[0]),
                              line=dict(color=TEMA["referencia"], width=1),
                              annotation_text="sistema (SCR)")
            fig.update_xaxes(title="Cobertura de provisões (%)")
            fig.update_yaxes(title="Ativos problemáticos (% da carteira)")
            sem_grafico(fig)
        bloco_lrc("p3_3")

    # ---- 4. folga de capital
    with n3:
        st.markdown(f"**{LRC['p3_4']['titulo']}**")
        dk = univ.dropna(subset=["p3_6_folga_capital_pp"]).nsmallest(15, "p3_6_folga_capital_pp")
        if dk.empty:
            st.info("Sem dados de capital nesta data-base.")
        else:
            cores = [TEMA["risco_alto"] if v < 2 else
                     TEMA["risco_medio"] if v < 5 else TEMA["marca"]
                     for v in dk["p3_6_folga_capital_pp"]]
            fig = go.Figure(go.Bar(
                x=dk["p3_6_folga_capital_pp"], y=[n[:22] for n in dk["instituicao"]],
                orientation="h", marker_color=cores,
                hovertemplate="%{y}<br>folga: %{x:.2f} p.p.<extra></extra>"))
            fig.add_vline(x=0, line=dict(color=TEMA["risco_alto"], width=1.5),
                          annotation_text=f"mínimo {MIN_BASILEIA}%")
            fig.update_xaxes(title="Folga sobre o mínimo (p.p.)")
            fig.update_yaxes(autorange="reversed")
            sem_grafico(fig)
        bloco_lrc("p3_4")

    fonte("BCB/IF.data (carteira por instrumentos financeiros, Ativo e Informações de Capital); "
          "BCB/SCR.data para a referência de sistema; SGS 21082/21112/21086 para inadimplência agregada.")


# ================================================================== COMPARADOR
with aba4:
    st.markdown(f"#### {T.txt('comparador.titulo')}")
    st.markdown(
        f"<div class='bloco-lrc'><b>Leitura.</b> {T.txt('comparador.leitura')}<br>"
        f"<b>Consequência.</b> {T.txt('comparador.consequencia')}</div>",
        unsafe_allow_html=True)

    opcoes = (univ.sort_values("carteira_credito_real", ascending=False)
                  [["cod_inst", "instituicao"]].drop_duplicates("cod_inst"))
    mapa = dict(zip(opcoes["cod_inst"], opcoes["instituicao"]))
    # pre-seleciona as tres primeiras da agenda de atipicas do trimestre
    padrao = lista["cod_inst"].head(3).tolist() if not lista.empty else []
    padrao = [c for c in padrao if c in mapa][:3]

    sel = st.multiselect("Instituições (2 a 4)", list(mapa), default=padrao,
                         format_func=lambda c: mapa.get(c, c), max_selections=4)

    if len(sel) < 2:
        st.info("Selecione ao menos duas instituições.")
    else:
        comp = univ[univ["cod_inst"].isin(sel)]
        LINHAS = [
            ("Carteira de crédito (R$ bi)", "carteira_credito_real", lambda v: v / 1e9, "{:,.1f}"),
            ("Participação no sistema (%)", "share_carteira", lambda v: v * 100, "{:.3f}"),
            ("P1·1 Crescimento real (% a.a.)", "p1_1_cresc_real_aa", lambda v: v * 100, "{:.1f}"),
            ("P1·2 Credit gap (%)", "p1_2_credit_gap", lambda v: v * 100, "{:.1f}"),
            ("P1·3 Trimestres seguidos >15%", "p1_3_trim_consec_acima", lambda v: v, "{:.0f}"),
            ("P1·4 Carteira ÷ capital", "p1_4_cresc_carteira_sobre_capital", lambda v: v, "{:.2f}"),
            ("P1·5 Cresc. alto risco (% a.a.)", "p1_5_cresc_alto_risco_aa", lambda v: v * 100, "{:.1f}"),
            ("P1·6 Var. de share (p.p.)", "p1_6_var_share_pp", lambda v: v, "{:.3f}"),
            ("P2·3 % em alto risco", "p2_3_pct_alto_risco", lambda v: v * 100, "{:.1f}"),
            ("P2·4 HHI regional", "p2_4_hhi_regional", lambda v: v, "{:,.0f}"),
            ("P2·5 % da carteira PJ em grande porte", "p2_5_pct_grande_porte",
             lambda v: v * 100, "{:.1f}"),
            ("P2·6 Carteira ÷ captações", "p2_6_loan_to_deposit", lambda v: v, "{:.2f}"),
            ("P3·1 Inadimplência (%)", "p3_1_inadimplencia", lambda v: v * 100, "{:.2f}"),
            ("P3·2 Cobertura (%)", "p3_2_cobertura", lambda v: v * 100, "{:.0f}"),
            ("P3·3 Provisão ÷ carteira (%)", "p3_3_provisao_sobre_carteira", lambda v: v * 100, "{:.2f}"),
            ("P3·4 Inadimpl. ajustada (%)", "p3_4_inadimplencia_ajustada", lambda v: v * 100, "{:.2f}"),
            ("P3·5 Ativos problemáticos (%)", "p3_5_ativos_problematicos", lambda v: v * 100, "{:.2f}"),
            ("P3·6 Folga de capital (p.p.)", "p3_6_folga_capital_pp", lambda v: v, "{:.2f}"),
            ("Score final", "score_final", lambda v: v, "{:.3f}"),
            # contexto descritivo -- NAO entra no score nem conta como um dos 18 indicadores
            ("(contexto) Ticket médio por cliente (R$ mil)", "ctx_ticket_medio_real",
             lambda v: v / 1e3, "{:,.1f}"),
        ]
        linhas = []
        for rotulo, col, tr, f in LINHAS:
            reg = {"Indicador": rotulo}
            for cod in sel:
                r = comp[comp["cod_inst"] == cod]
                v = r[col].iloc[0] if (len(r) and col in r.columns) else None
                reg[mapa[cod][:22]] = f.format(tr(v)) if pd.notna(v) else "—"
            mediana = univ[col].median() if col in univ.columns else None
            reg["Mediana do recorte"] = f.format(tr(mediana)) if pd.notna(mediana) else "—"
            linhas.append(reg)
        st.dataframe(pd.DataFrame(linhas), width='stretch',
                     hide_index=True, height=720)

        st.markdown("##### Semáforo por eixo")
        cols = st.columns(len(sel))
        for i, cod in enumerate(sel):
            r = comp[comp["cod_inst"] == cod].iloc[0]
            with cols[i]:
                st.markdown(f"**{mapa[cod][:30]}**")
                for eixo in EIXOS:
                    st.markdown(
                        f"{sem_html(r[f'sem_{eixo}'])} {eixo.capitalize()} — "
                        f"{r[f'score_{eixo}']:.2f}" if pd.notna(r[f"score_{eixo}"])
                        else f"{sem_html('sem')} {eixo.capitalize()} — sem dado",
                        unsafe_allow_html=True)

    fonte(f"BCB/IF.data, data-base {fmt_trimestre(dt_sel)}. "
          f"Valores reais em R$ de {fmt_trimestre(BASE_DEFL)}.")
