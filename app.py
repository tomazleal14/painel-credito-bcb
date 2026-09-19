"""
app.py -- Painel decisorio de credito | persona: Supervisao do Banco Central
Trabalho Intermediario -- FGV / Prof. Genaro Lins

Rodar local:  .venv/Scripts/streamlit.exe run app.py

Estrutura: 4 abas (Visao geral + P1/P2/P3), grade 2x2 de graficos por pergunta,
Leitura e Consequencia visiveis na tela, Referencia em expander.
TEMA ISOLADO em src/tema.py e .streamlit/config.toml.
"""
from __future__ import annotations

import hashlib
import math
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path.insert(0, str(RAIZ / "src"))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import cartoes
import catalogo
import filtros
import grupos
import textos as _textos
from scoring import (CORTE_ALTO, EIXOS, FRACAO_MINIMA, MIN_INDICADORES, PESOS_PADRAO,
                     agenda, agenda_grandes, calcula_scores)
from tema import (ALTURA_GRAFICO, ALTURA_GRAFICO_GRANDE, ICONE_SEMAFORO,
                  SEMAFORO, SEMAFORO_SOFT, TEMA, layout_base, monta_css, regua)

DATA_PROC = RAIZ / "data_processed"
MIN_BASILEIA = 10.5
LIMIAR_BOOM = 0.15

# Carimbo de build. O Streamlit Cloud ja serviu tres vezes uma versao defasada do
# repositorio, e nao havia como distinguir "o painel esta errado" de "o Cloud nao
# atualizou" olhando a tela. VERSAO muda a cada alteracao que mexe nos numeros; a
# impressao digital e do arquivo de dados. Se o que aparece no rodape da barra lateral
# do Cloud nao bater com o local, o Cloud esta atrasado -- e nao ha o que depurar.
VERSAO = ("2026-09-18d · nota de leitura da linha de sistema; cache da base passa a "
          "seguir o arquivo, para código novo não servir dado velho")

st.set_page_config(page_title="Painel de Supervisão de Crédito — BCB",
                   page_icon="◧", layout="wide",
                   initial_sidebar_state="expanded")


# ------------------------------------------------------------------ dados
def assinatura_dados() -> str:
    """Impressão barata (tamanho + mtime) dos arquivos que `carrega` lê.

    É a CHAVE do cache de `carrega`. Sem ela, `carrega()` não tem argumento nenhum e
    o `@st.cache_data` devolve para sempre o primeiro resultado do processo: um
    deploy que troca o .parquet mas reaproveita o processo serve CÓDIGO NOVO com
    DADO VELHO. Foi o que aconteceu quando a linha de sistema passou a somar
    inadimplência e provisão — os contadores, que são só código, apareceram; as
    razões, que dependiam de duas colunas novas no arquivo, ficaram vazias.
    """
    partes = []
    for nome in ("app_indicadores.parquet", "indicadores.parquet",
                 "sgs_series.parquet", "scr_agregado.parquet"):
        alvo = DATA_PROC / nome
        if alvo.exists():
            st_ = alvo.stat()
            partes.append(f"{nome}:{st_.st_size}:{int(st_.st_mtime)}")
    return "|".join(partes)


@st.cache_data(show_spinner="Carregando base…")
def carrega(assinatura: str):
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


ind, sgs, scr, cat_sgs, defl = carrega(assinatura_dados())
BASE_DEFL = int(defl["base_do_indice"].iloc[0])

# Rotulo de sistema cooperativo. E SO APRESENTACAO: nenhuma conta usa esta coluna --
# src/checa_grupos.py verifica que as 91 colunas numericas ficam identicas com e sem
# ela. Existe porque 154 das 258 instituicoes do recorte sao cooperativas singulares
# e 11 das 21 vagas da agenda eram singulares do mesmo sistema. Ver src/grupos.py.
ind["grupo"] = grupos.atribui(ind)


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


SUFIXOS_COMUNS = (" - PRUDENCIAL", " - PRUDENCIA", " – PRUDENCIAL")


def nome_curto(s: str, n: int = 26) -> str:
    """Nome da instituição sem o sufixo que TODAS carregam, antes de truncar.

    No universo 1009 toda instituição termina em " - PRUDENCIAL". Truncar em 24
    caracteres gastava 12 deles nesse sufixo: "UBS (BRASIL) - PRUDENCIA" perdia só o
    "L" final e o que distinguia uma da outra ficava fora da tela. Tirando o sufixo
    comum, os 24 caracteres passam a carregar informação.
    """
    t = str(s or "").strip()
    for suf in SUFIXOS_COMUNS:
        if t.upper().endswith(suf):
            t = t[: -len(suf)].strip()
            break
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def nomes_distintos(nomes: list[str], n: int = 44) -> list[str]:
    """Rótulos truncados que continuam DISTINGUINDO uma instituição da outra.

    Truncar pela cabeça falha quando os nomes compartilham um prefixo longo: as
    sinalizadas em crescimento com série longa são quase todas cooperativas, e quatro
    delas viravam a mesma legenda, "COOPERATIVA DE CRÉDITO, POUPANÇA E INVESTIM…".
    Quando há colisão, o rótulo passa a mostrar começo E fim — é no fim que mora o que
    diferencia ("… - SICOOB ARACOOP").

    Rótulo IGUAL não é o único fracasso: "COOPERATIVA DE CRÉDITO E INVE…" e
    "COOPERATIVA DE CRÉDITO DE LIV…" são formalmente distintos e, na prática,
    indistinguíveis. Por isso o gatilho é o prefixo comum, não só a igualdade.
    """
    base = [nome_curto(x, n) for x in nomes]
    limite = max(8, n * 3 // 4)

    def confundem(a: str, b: str) -> bool:
        comum = 0
        for x, y in zip(a, b):
            if x != y:
                break
            comum += 1
        return a == b or comum >= limite

    if not any(confundem(base[i], base[j])
               for i in range(len(base)) for j in range(i + 1, len(base))):
        return base
    saida = []
    for bruto in nomes:
        t = nome_curto(bruto, 10_000)
        if len(t) <= n:
            saida.append(t)
            continue
        cabeca, cauda = (n - 3) // 2, (n - 3) - (n - 3) // 2
        saida.append(f"{t[:cabeca].rstrip()}…{t[-cauda:].lstrip()}")
    return saida


def sem_grafico(fig: go.Figure, titulo: str = "", altura: int | None = None):
    """Aplica o layout comum e põe a legenda ACIMA do gráfico.

    A legenda ficava embaixo, em y=-0,18, disputando a margem inferior com o título do
    eixo — e o Plotly não empilha um sobre o outro: "Outros" caía em cima de "% da
    carteira PF". Reservar mais margem não resolve, porque os dois continuam ancorados
    no mesmo ponto.

    Acima do gráfico não há concorrente: o título de cada figura é um `st.markdown`
    fora do Plotly, e o `title` interno fica vazio. O espaço é reservado pelo número de
    itens no pior caso (um por linha, que é o que acontece em coluna estreita), e a
    altura cresce junto para a área de plotagem não encolher.
    """
    itens = sum(1 for t in fig.data
                if getattr(t, "showlegend", None) is not False and getattr(t, "name", None))
    extra = 20 * itens if itens > 1 else 0
    lay = layout_base(titulo, (altura or ALTURA_GRAFICO) + extra)
    if extra:
        lay["margin"] = {**lay["margin"], "t": lay["margin"]["t"] + extra}
        lay["legend"] = {**lay["legend"], "yanchor": "bottom", "y": 1.0, "x": 0,
                         "xanchor": "left"}
    fig.update_layout(**lay)
    st.plotly_chart(fig, width='stretch', config={"displayModeBar": False})


def fonte(txt: str) -> None:
    st.markdown(f"<div class='rodape-fonte'>Fonte: {txt}</div>", unsafe_allow_html=True)


# ------------------------------------------------------------------ barra lateral
trimestres = sorted(ind["data_base"].unique())
f = filtros.barra_lateral(ind, PESOS_PADRAO, EIXOS)
# Leitura TOLERANTE das escolhas da barra lateral.
# Motivo concreto: o Streamlit Cloud ja serviu, duas vezes, uma versao mista dos
# arquivos -- app.py novo com src/ antigo -- e o painel morreu com KeyError em plena
# tela. Chave que faltar cai no padrao e o painel avisa, em vez de quebrar.
_faltando = [k for k in ("dt_sel", "tcb_sel", "seg_sel", "porte_min", "pesos",
                         "limiar", "cobertura", "ativos", "corte_alto") if k not in f]
dt_sel = f.get("dt_sel", max(ind["data_base"]))
tcb_sel = f.get("tcb_sel") or sorted(ind["tcb"].dropna().unique())
seg_sel = f.get("seg_sel") or sorted(ind["segmento_sr"].fillna("").unique())
porte_min = f.get("porte_min", 1e9)
pesos = f.get("pesos") or PESOS_PADRAO
limiar = f.get("limiar", 0.65)
cobertura = f.get("cobertura", 0.80)
corte_alto = f.get("corte_alto", CORTE_ALTO)
ativos = f.get("ativos") or {e: catalogo.padrao_do_eixo(e) for e in EIXOS}

# aplica filtros
base = ind[ind["tcb"].isin(tcb_sel) & ind["segmento_sr"].isin(seg_sel)].copy()
if base.empty:
    st.sidebar.error("Nenhuma instituição atende a esta combinação.")
    st.error("Nenhuma instituição atende aos filtros. Amplie a seleção na barra lateral.")
    st.stop()

scored = calcula_scores(base, grupo_pares="tcb", pesos=pesos, ativos=ativos,
                        corte_alto=corte_alto)
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


@st.cache_data(show_spinner=False)
def impressao_dados(assinatura: str = "") -> str:
    """Hash curto do arquivo de dados, para identificar o build servido.

    `assinatura` não é usada no corpo: existe só para o cache acompanhar a troca do
    arquivo, pelo mesmo motivo de `carrega`.
    """
    alvo = DATA_PROC / "app_indicadores.parquet"
    if not alvo.exists():
        alvo = DATA_PROC / "indicadores.parquet"
    h = hashlib.sha256()
    with open(alvo, "rb") as fh:
        for pedaco in iter(lambda: fh.read(1 << 20), b""):
            h.update(pedaco)
    return h.hexdigest()[:8]


# Quantos trimestres do indicador-âncora de P1 sobrevivem: 21 é a versão com a máscara
# da Res. 4.966 aplicada, 25 é a versão anterior. É a checagem mais direta de defasagem.
_trim_p1 = int(ind.loc[ind["p1_1_cresc_real_aa"].notna(), "data_base"].nunique()) \
    if "p1_1_cresc_real_aa" in ind else 0
# O separador de milhar vai para o padrao pt-BR SO no numero de linhas. O `.replace`
# aplicado à frase inteira, como estava, comia qualquer virgula da mensagem de build:
# "(só apresentação), com coluna" virava "(só apresentação). com coluna".
_linhas_fmt = f"{len(ind):,}".replace(",", ".")
st.sidebar.caption(
    f"**Build:** {VERSAO}  \n"
    f"dados `{impressao_dados(assinatura_dados())}` · {_linhas_fmt} linhas · "
    f"P1 com {_trim_p1} trimestres")


# ------------------------------------------------------------------ cabecalho
# Se textos.toml tiver erro de sintaxe, avisa em vez de quebrar o painel.
if T.erro:
    st.error(f"**Problema em `textos.toml`** — o painel segue com os textos padrão.\n\n"
             f"```\n{T.erro}\n```")
elif T.avisos:
    st.warning("Avisos de `textos.toml`: " + " · ".join(T.avisos))

if _faltando:
    st.warning(
        f"Versões desencontradas dos arquivos: a barra lateral não devolveu "
        f"{', '.join('`' + k + '`' for k in _faltando)}. O painel seguiu com os valores "
        f"padrão. No Streamlit Cloud isso costuma ser deploy defasado — use "
        f"**Manage app → Reboot app**.")
for _av in f.get("avisos_indicadores", []):
    st.warning(f"Seleção de indicadores: {_av}")

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
    # recalculados sobre o recorte, e nao lidos da coluna gravada (ver cartoes.hhi_cr5)
    _hhi_r, _cr5_r = cartoes.hhi_cr5(univ)
    _hhi_s, _cr5_s = cartoes.hhi_cr5(ind[ind["data_base"] == dt_sel])
    c[2].metric("HHI do recorte",
                cartoes.num(_hhi_r, 0) if pd.notna(_hhi_r) else "—",
                help=f"Índice Herfindahl-Hirschman: soma dos quadrados das participações "
                     f"de mercado das {len(univ)} instituições do recorte, de 0 a 10.000. "
                     f"Abaixo de 1.500 = desconcentrado; 1.500 a 2.500 = moderadamente "
                     f"concentrado; acima = concentrado. Responde aos filtros — no "
                     f"universo inteiro do IF.data é {cartoes.num(_hhi_s, 0)}.")
    c[3].metric("CR5 do recorte",
                f"{cartoes.num(_cr5_r, 1)}%" if pd.notna(_cr5_r) else "—",
                help=f"Concentration ratio dos 5 maiores: fatia da carteira detida pelas "
                     f"cinco maiores instituições do recorte. Complementa o HHI, que pode "
                     f"ser baixo por haver milhares de instituições pequenas. Responde "
                     f"aos filtros — no universo inteiro é "
                     f"{cartoes.num(_cr5_s, 1)}%.")
    cresc_med = univ["p1_1_cresc_real_aa"].median()
    c[4].metric("Crescimento real mediano",
                f"{cartoes.num(cresc_med*100, 1)}%" if pd.notna(cresc_med) else "—",
                help="Mediana do crescimento da carteira em 12 meses, já descontada a "
                     "inflação (IPCA). É a variável-mestra de P1.")

    # ---- cartoes por eixo: score, sparkline e decomposicao nos indicadores ----
    st.markdown(f"#### {T.bruto('sintese.titulo', 'Os três eixos, decompostos')}")
    hist = scored[scored["carteira_credito_real"] >= porte_min]
    gloss_ind = T.glossario_indicadores
    comp_eixo = cartoes.indicadores_por_eixo(ativos)
    cols_eixo = st.columns(3, gap="medium")
    for i, eixo in enumerate(EIXOS):
        with cols_eixo[i]:
            st.markdown(
                cartoes.cartao_eixo(
                    univ, eixo,
                    T.txt(f"eixos.{eixo}.rotulo", eixo.capitalize()),
                    T.txt(f"eixos.{eixo}.descricao", ""),
                    glossario=gloss_ind,
                    # os eixos NAO tem o mesmo numero de percentis: concentracao usa 4,
                    # porque HHI do sistema e CR5 sao iguais para todas as instituicoes
                    # e nao geram percentil. Isso fica declarado no cartao.
                    n_percentis=len(comp_eixo.get(eixo, [])),
                    componentes=comp_eixo.get(eixo, []),
                    corte_alto=corte_alto),
                unsafe_allow_html=True)
    # A cobertura de cada eixo saiu dos cartoes e virou UMA linha para os tres: repetida
    # em cada cartao, ela ocupava mais espaco que o dado e ainda assim so podia ser lida
    # comparando os tres textos entre si. O detalhe por indicador esta em P1/P2/P3.
    st.markdown(
        f"<div class='rodape-fonte'>Os cartões acima descrevem <b>apenas "
        f"{fmt_trimestre(dt_sel)}</b> — composição da carteira no trimestre, que está "
        f"sempre completa. O histórico de cada eixo, com as lacunas que a Res. 4.966 e "
        f"a idade das séries impõem, fica nas páginas P1, P2 e P3, ao lado da "
        f"justificativa de cada indicador.</div>",
        unsafe_allow_html=True)

    # ---- o que o numero grande significa (retratil, como o glossario) ----
    with st.expander(T.bruto("sintese.rotulo_expander",
                             "Como ler estes números — o cálculo passo a passo")):
        st.markdown(
            f"<div class='explicacao'>"
            f"<b>O que é o número.</b> {T.txt('sintese.o_que_e_o_numero')}"
            f"<br><br><b>Como ler.</b> {T.txt('sintese.como_ler')}"
            f"<br><br><b>Quem é marcado como risco alto.</b> "
            f"{T.txt('sintese.por_que_decompor')}"
            f"<br><br><b>A barra de composição.</b> {T.txt('sintese.a_composicao')}"
            f"<br><br><b>Por que não há série histórica aqui.</b> "
            f"{T.txt('sintese.sem_serie')}"
            f"<br><br><b>Os componentes.</b> {T.txt('sintese.os_componentes')}</div>",
            unsafe_allow_html=True)

    # sintese factual do trimestre, calculada -- nao escrita a mao.
    # Ordena a pressao por CARTEIRA EXPOSTA, nao por contagem de instituicoes: 54
    # cooperativas pequenas sinalizadas pesam menos que um grande banco sinalizado.
    # Mesmo numero dos cartoes, medido no MESMO trimestre. NaN significa eixo nao
    # avaliavel no trimestre -- nao entra na disputa de "maior pressao", porque um eixo
    # sem medida nao pode ser declarado o menor nem o maior.
    exposta = {e: cartoes.exposta_no_trimestre(univ, e) for e in EIXOS}
    n_alto = {e: int((univ[f"sem_{e}"] == "alto").sum()) for e in EIXOS}
    rot = {e: T.bruto(f"eixos.{e}.rotulo", e).lower() for e in EIXOS}
    medidos = {e: v for e, v in exposta.items() if pd.notna(v)}
    vazios = [rot[e] for e in EIXOS if e not in medidos]

    def _exp(e: str) -> str:
        return (f"<b>{cartoes.num(exposta[e], 1)}%</b>" if e in medidos
                else "<b>sem medida</b>")

    if medidos:
        pior = max(medidos, key=medidos.get)
        frase_pior = (f"a maior pressão vem de <b>{rot[pior]}</b> "
                      f"({n_alto[pior]} instituições sinalizadas)")
        if vazios:
            frase_pior += (f", entre os eixos que podem ser medidos — "
                           f"{' e '.join(vazios)} "
                           f"{'está' if len(vazios) == 1 else 'estão'} sem score neste "
                           f"trimestre")
    else:
        frase_pior = ("nenhum eixo pode ser avaliado neste trimestre — todos ficam sem "
                      "score, e a comparação entre eles não existe")

    quadrante = univ[(univ["p1_1_cresc_real_aa"] > univ["p1_1_cresc_real_aa"].median())
                     & (univ["p3_1_inadimplencia"] < univ["p3_1_inadimplencia"].median())]
    carteira_quadrante = (quadrante["carteira_credito_real"].sum()
                          / univ["carteira_credito_real"].sum() * 100
                          if univ["carteira_credito_real"].sum() else 0.0)
    frase_quadrante = (
        f"<b>{len(quadrante)}</b> instituições, com "
        f"<b>{cartoes.num(carteira_quadrante, 1)}%</b> da carteira, estão no "
        f"quadrante-assinatura de P3 — crescem acima da mediana e ainda exibem "
        f"inadimplência abaixo dela, que é onde o efeito denominador costuma esconder "
        f"perda futura."
        if len(quadrante) else
        "O quadrante-assinatura de P3 não pode ser montado neste trimestre: ele cruza "
        "crescimento real com inadimplência, e um dos dois não tem dado aqui.")

    st.markdown(
        f"<div class='aviso'><b>Neste recorte ({fmt_trimestre(dt_sel)}):</b> "
        f"a carteira exposta a risco alto é de "
        f"{_exp('crescimento')} em crescimento, "
        f"{_exp('concentracao')} em concentração e "
        f"{_exp('deterioracao')} em deterioração — {frase_pior}. "
        f"{frase_quadrante}</div>",
        unsafe_allow_html=True)

    with st.expander("O que cada indicador mede — glossário dos 18"):
        st.markdown(cartoes.tabela_glossario(gloss_ind, cartoes.indicadores_dos_18(ativos)),
                    unsafe_allow_html=True)
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
        """Uma linha por item. Linhas de SISTEMA não trazem razão nenhuma.

        Carteira é nível, e nível soma. Inadimplência, cobertura, Basileia e
        crescimento são razão — e a razão de um conjunto não é a média das razões
        dos membros: cada uma teria de ser refeita a partir dos numeradores e
        denominadores somados, o que é consolidar de fato, e não é o que este
        agrupamento faz. Campo vazio é a leitura honesta; o detalhamento abaixo da
        tabela traz os números de cada singular.
        """
        def pc(v, aplicavel: bool = True) -> str:
            """Percentual pt-BR, ou travessão quando não há valor.

            As quatro colunas de razão saem como TEXTO, e não como número, porque
            esta versão do Streamlit escreve o literal "None" em toda célula
            numérica vazia — verificado isoladamente, vale para float64 e para
            Float64, com ou sem `format`, e um Styler com `na_rep` não alcança o
            grid. Como razão que falta é a regra neste painel, e não a exceção,
            "None" apareceria com frequência. O preço é a ordenação da coluna, que
            passa a ser alfabética; Carteira e Score seguem numéricas.
            """
            if not aplicavel or v is None or not math.isfinite(v):
                return "—"
            return f"{cartoes.num(v * 100, 2)}%"

        linhas = []
        for r in dados.itertuples():
            sis = getattr(r, "linha_tipo", "instituicao") == "sistema"
            # NaN é verdadeiro em Python: `nan or "—"` devolveria nan, e a célula
            # sairia com o texto "nan". Só string não vazia vale como sistema.
            g = getattr(r, "grupo", "")
            linhas.append({
                "#": int(r.posicao),
                "Instituição": getattr(r, "rotulo", r.instituicao),
                "Sistema": g if isinstance(g, str) and g else "—",
                "TCB": r.tcb,
                "Seg.": "—" if sis else r.segmento_sr,
                "Carteira": (getattr(r, "carteira_grupo", r.carteira_credito_real)
                             if sis else r.carteira_credito_real) / 1e9,
                # Na linha de sistema, estas três são a razão DO CONJUNTO — soma do
                # numerador sobre soma do denominador, calculada em grupos.agrega.
                # Nunca a média das razões, e nunca o número da representante.
                "Cresc. real a.a.": (pc(getattr(r, "agg_cresc", None)) if sis
                                     else pc(r.p1_1_cresc_real_aa)),
                "Inadimpl.": (pc(getattr(r, "agg_inadimplencia", None)) if sis
                              else pc(r.p3_1_inadimplencia)),
                "Cobertura": (pc(getattr(r, "agg_cobertura", None)) if sis
                              else pc(r.p3_2_cobertura)),
                # Basileia não: capital de cooperativas independentes não é fungível,
                # e ΣPR/ΣRWA não é o índice de nenhuma delas.
                "Basileia": pc(r.indice_basileia, not sis),
                # Semáforo é categoria: não se soma, mas se conta.
                "Cresc.": (f"{getattr(r, 'n_alto_crescimento', 0)} de {r.n_sinalizadas}"
                           if sis else ICONE_SEMAFORO[r.sem_crescimento]),
                "Conc.": (f"{getattr(r, 'n_alto_concentracao', 0)} de {r.n_sinalizadas}"
                          if sis else ICONE_SEMAFORO[r.sem_concentracao]),
                "Deter.": (f"{getattr(r, 'n_alto_deterioracao', 0)} de {r.n_sinalizadas}"
                           if sis else ICONE_SEMAFORO[r.sem_deterioracao]),
                "Score": r.score_final,
            })
        return pd.DataFrame(linhas)

    def nota_sistemas(colapsada: pd.DataFrame) -> None:
        """Explica a linha de sistema: o que cada coluna vira, e por que há vazios.

        A linha agrupada troca o significado de sete colunas de uma vez. Sem esta nota
        o leitor precisa abrir sete dicas de cabeçalho para descobrir que "0 de 11" é
        informação e não ausência, e que o travessão da Basileia não é falta de dado.
        O exemplo sai da própria seleção, para não descrever um recorte que não está
        na tela.
        """
        sistemas = colapsada[colapsada["linha_tipo"] == "sistema"]
        if sistemas.empty:
            return
        r = sistemas.iloc[0]
        nome = str(r["grupo"]).upper()
        n = int(r["n_sinalizadas"])
        exemplo = (
            f"A {nome} está <b>{int(r['n_alto_crescimento'])} de {n}</b> em crescimento "
            f"e <b>{int(r['n_alto_concentracao'])} de {n}</b> em concentração: as "
            f"sinalizadas entraram na agenda por um eixo, não pelo outro."
        )
        st.markdown(
            f"<div class='aviso'><b>Como ler a linha de um sistema.</b> Ela descreve o "
            f"<b>conjunto das singulares sinalizadas</b>, não o sistema inteiro — e não é "
            f"um balanço consolidado.<br><br>"
            f"<b>Carteira, crescimento, inadimplência e cobertura</b> somam o numerador e "
            f"o denominador do conjunto (Σ ÷ Σ). Nunca a média das razões dos membros, que "
            f"seria outra coisa.<br>"
            f"<b>Cresc., Conc. e Deter.</b> deixam de ser semáforo e viram contagem: "
            f"quantas singulares estão com risco alto naquele eixo. Semáforo é categoria, "
            f"não se soma — mas contar não inventa nada. <b>“0 de {n}” não é falta de "
            f"dado</b>, é a informação de que nenhuma delas está no topo daquele eixo. "
            f"{exemplo}<br>"
            f"<b>Basileia</b> fica <b>sempre</b> vazia, e não por falta de dado: capital "
            f"de cooperativas juridicamente independentes não é fungível — nenhuma pode "
            f"usar o capital da outra —, então a soma não é o índice de ninguém.<br>"
            f"<b>As demais só ficam vazias</b> quando o conjunto medido não seria o "
            f"conjunto anunciado na linha: o crescimento exige todos os membros já "
            f"existindo 12 meses antes, e desaparece em todos os trimestres de 2025 pela "
            f"quebra da Res. 4.966; inadimplência e cobertura exigem o numerador em todos "
            f"os membros, porque um ausente encolheria só o numerador."
            f"</div>",
            unsafe_allow_html=True)

    def detalha_sistemas(colapsada: pd.DataFrame, completa: pd.DataFrame) -> None:
        """Abre, sistema a sistema, as singulares que a linha agrupada representa."""
        sistemas = colapsada[colapsada["linha_tipo"] == "sistema"]
        if sistemas.empty:
            return
        st.markdown("<div class='rodape-fonte'>Detalhamento das linhas de sistema — "
                    "cada uma abre a lista completa das singulares que representa."
                    "</div>", unsafe_allow_html=True)
        for r in sistemas.itertuples():
            # o rotulo do expander e markdown, e DOIS cifroes na mesma linha abrem
            # modo matematico: "R$ 18,9 bi de R$ 21,9 bi" virava LaTeX. Escapa-se.
            titulo = (f"{str(r.grupo).upper()} — {r.n_sinalizadas} de {r.n_recorte} "
                      f"singulares sinalizadas · "
                      f"R\\$ {cartoes.num(r.carteira_grupo / 1e9, 1)} bi de "
                      f"R\\$ {cartoes.num(r.carteira_recorte / 1e9, 1)} bi no recorte")
            with st.expander(titulo):
                membros = grupos.membros(completa, r.grupo)
                tab = monta_tabela(membros)
                # As singulares de um sistema compartilham um prefixo longo -- as onze
                # da Cresol comecam com os mesmos 55 caracteres, e o que as distingue
                # ("- CRESOL FRONTEIRAS", "- CRESOL CENTRO SUL") mora no fim do nome.
                # Truncar pela cabeca devolvia onze rotulos identicos.
                tab["Instituição"] = nomes_distintos(
                    membros["instituicao"].tolist(), n=52)
                st.dataframe(tab, width='stretch', hide_index=True,
                             height=min(460, 60 + 35 * len(membros)),
                             column_config=COLUNAS)

    # `help` de cada coluna: e onde a variavel e decifrada, sem sair da tabela
    COLUNAS = {
        "#": st.column_config.NumberColumn(
            "#", width="small", format="%d",
            help="Posição NESTA lista, da mais prioritária para a menos. "
                 "Não é o ranking geral do sistema."),
        "Instituição": st.column_config.TextColumn(
            "Instituição", width="large",
            help="Uma linha que começa com SISTEMA reúne as cooperativas singulares "
                 "de um mesmo sistema. O '11 de 13' lê-se: 11 singulares "
                 "sinalizadas entre as 13 que estão no recorte. Abra o "
                 "detalhamento abaixo da tabela para ver cada uma."),
        "Sistema": st.column_config.TextColumn(
            "Sistema", width="small",
            help="Sistema cooperativo a que a instituição pertence. NÃO é campo do "
                 "IF.data, que não publica o vínculo e classifica toda singular como "
                 "instituição independente: é deduzido da marca no nome publicado e "
                 "alcança 63% das cooperativas. Travessão = banco, ou cooperativa sem "
                 "marca no nome legal — que segue listada individualmente. A coluna "
                 "aparece com o agrupamento ligado ou desligado, e vai no CSV."),
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
                 "pelo IPCA (SGS 433). Na linha de um sistema, é a soma das "
                 "singulares sinalizadas — carteira é nível, e nível soma. As "
                 "demais colunas da linha de sistema ficam vazias porque são "
                 "razões, e razão de conjunto não é média de razões."),
        "Cresc. real a.a.": st.column_config.TextColumn(
            "Cresc. real a.a.",
            help="Crescimento da carteira em 12 meses, já descontada a inflação. "
                 "É a variável-mestra de P1: acima de 15% a.a. real é o limiar de "
                 "crescimento acelerado adotado aqui. Na linha de um sistema é o "
                 "crescimento DO CONJUNTO sinalizado — carteira somada de hoje sobre "
                 "carteira somada de 12 meses atrás —, e fica vazio se algum membro "
                 "não existia lá atrás."),
        "Inadimpl.": st.column_config.TextColumn(
            "Inadimpl.",
            help="Carteira em atraso acima de 90 dias, sobre a carteira total. "
                 "Cuidado com o efeito denominador: carteira que cresce rápido dilui "
                 "este índice e esconde perda futura. Na linha de um sistema é o "
                 "atraso somado sobre a carteira somada do conjunto sinalizado — a "
                 "razão do conjunto, não a média das razões dos membros."),
        "Cobertura": st.column_config.TextColumn(
            "Cobertura",
            help="Provisão dividida pela carteira em atraso. 100% cobre integralmente "
                 "o atraso; abaixo disso há perda ainda não reconhecida no balanço. "
                 "Na linha de um sistema é a provisão somada sobre o atraso somado do "
                 "conjunto sinalizado."),
        "Basileia": st.column_config.TextColumn(
            "Basileia",
            help="Índice de Basileia: capital sobre ativos ponderados pelo risco. "
                 "O mínimo de referência é 10,5% (8% de requisito mais 2,5% de "
                 "conservação). É a ÚNICA coluna que fica vazia na linha de um "
                 "sistema, e não por falta de dado: capital de cooperativas "
                 "juridicamente independentes não é fungível — nenhuma pode usar o "
                 "capital da outra —, então a soma não é o índice de ninguém."),
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
                 "pesos da barra lateral. 0,50 = mediana do grupo. Na linha de um "
                 "sistema é o MAIOR score entre as singulares sinalizadas — o pior "
                 "caso do sistema —, nunca uma média."),
    }

    # ---- agrupamento por sistema cooperativo ----
    # Sem isto, 11 das 21 vagas da agenda de 03/2026 eram singulares Cresol: onze
    # linhas quase identicas empurrando o resto do recorte para fora da tela. O
    # agrupamento e so de apresentacao -- nenhum score muda (src/checa_grupos.py).
    # A chave fica visivel para que a escolha metodologica possa ser desfeita na
    # propria tela, e nao escondida no codigo.
    agrupar = st.toggle(
        "Agrupar cooperativas do mesmo sistema", value=True,
        help="Reúne numa linha só as singulares do mesmo sistema cooperativo "
             "(Sicredi, Sicoob, Cresol…). Nenhum número é recalculado: o score de "
             "cada singular continua sendo o dela, e a lista completa fica no "
             "detalhamento e no CSV. A filiação é deduzida da marca no nome "
             "publicado pelo IF.data — que não divulga o vínculo —, e cobre 63% "
             "das cooperativas; as demais seguem individuais.")
    # `scored` vai como histórico: o crescimento do conjunto precisa da carteira
    # somada de quatro trimestres antes, que não está na lista do trimestre.
    vis = grupos.colapsa(lista, univ, hist=scored) if agrupar else lista

    t1, t2 = st.tabs([f"Atípicas no grupo de pares ({len(vis)})",
                      f"Grandes com sinal ({len(lista_grandes)})"])

    with t1:
        colapso = (f" Onde havia várias singulares do mesmo sistema, a lista mostra "
                   f"<b>uma linha por sistema</b>: {len(lista)} instituições em "
                   f"<b>{len(vis)}</b> linhas."
                   if agrupar and len(vis) < len(lista) else "")
        st.markdown(
            f"<div class='aviso'>Entram as instituições com <b>score ≥ {limiar:.2f}</b> "
            f"e carteira ≥ {filtros.fmt_reais(porte_min)}: <b>{len(lista)}</b> de "
            f"{len(univ)} no recorte. Esta lista mede <b>atipicidade dentro do grupo de "
            f"pares</b> — quem está muito fora do padrão do próprio tipo de instituição. "
            f"Não mede relevância sistêmica: as {len(lista)} somam "
            f"{lista['carteira_credito_real'].sum()/univ['carteira_credito_real'].sum()*100:.1f}% "
            f"da carteira do recorte.{colapso}</div>",
            unsafe_allow_html=True)
        if lista.empty:
            st.warning(f"Nenhuma instituição atinge score {limiar:.2f}. "
                       "Baixe o limiar na barra lateral.")
        else:
            st.dataframe(monta_tabela(vis), width='stretch', hide_index=True,
                         height=min(560, 60 + 35 * len(vis)), column_config=COLUNAS)
            if agrupar:
                nota_sistemas(vis)
                detalha_sistemas(vis, lista)

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
        f"<b>—</b> célula sem valor: ou o dado não existe no trimestre, ou é uma "
        f"linha de sistema, e razão de conjunto não se soma &nbsp;·&nbsp; "
        f"passe o mouse no cabeçalho de cada coluna para ver o que ela mede</div>",
        unsafe_allow_html=True)

    def para_csv(dados: pd.DataFrame) -> bytes:
        """O CSV sai SEMPRE por instituição, mesmo com o agrupamento ligado.

        A tela agrupa para caber; o arquivo é o registro, e registro não pode
        depender de uma chave de exibição. A coluna Sistema, que `monta_tabela`
        já produz, preserva o vínculo no arquivo.
        """
        return monta_tabela(dados).to_csv(index=False).encode("utf-8-sig")

    c1, c2 = st.columns(2)
    if not lista.empty:
        c1.download_button(
            "Baixar lista de atípicas (CSV)", para_csv(lista),
            file_name=f"agenda_atipicas_{dt_sel}.csv", mime="text/csv",
            help="Uma linha por instituição, com a coluna Sistema — não agrupado.")
    if not lista_grandes.empty:
        c2.download_button(
            "Baixar lista de grandes (CSV)", para_csv(lista_grandes),
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


def faixas_de_trimestres(dts: list[int]) -> str:
    """Agrupa data-bases em intervalos CONTIGUOS: '03/2019 a 12/2019 e 03/2025 a 12/2025'.

    Existe porque as lacunas de P1 sao duas, separadas por cinco anos com score. Escrever
    'da primeira a ultima' descreveria um buraco continuo que nao existe.
    """
    def prox(d: int) -> int:
        a, m = divmod(d, 100)
        return a * 100 + m + 3 if m < 12 else (a + 1) * 100 + 3

    grupos: list[list[int]] = []
    for d in sorted(int(x) for x in dts):
        if grupos and prox(grupos[-1][-1]) == d:
            grupos[-1].append(d)
        else:
            grupos.append([d])

    partes = [fmt_trimestre(g[0]) if len(g) == 1
              else f"{fmt_trimestre(g[0])} a {fmt_trimestre(g[-1])}" for g in grupos]
    return partes[0] if len(partes) == 1 else ", ".join(partes[:-1]) + f" e {partes[-1]}"


def cobertura_indicadores(eixo: str, cols: list[str]) -> None:
    """Quantos trimestres cada indicador do eixo cobre, e por quê.

    Existe porque os indicadores de uma mesma pergunta NÃO têm a mesma série: em P1,
    carteira ÷ capital tem 3 trimestres e credit gap tem 25. Isso muda o tamanho do
    score ao longo do tempo — um degrau de composição que precisa ficar visível.
    """
    hist = scored[scored["carteira_credito_real"] >= porte_min]
    dts = sorted(hist["data_base"].unique())

    linhas = []
    for c in cols:
        pres = [d for d in dts
                if hist.loc[hist["data_base"] == d, c].notna().any()] if c in hist else []
        just = T.bruto(f"series_indicador.{c}", "")
        linhas.append({
            "Indicador": catalogo.rotulo(c),
            "Trimestres": len(pres),
            "de": len(dts),
            "Período": (f"{fmt_trimestre(pres[0])} a {fmt_trimestre(pres[-1])}"
                        if pres else "—"),
            "Por que não é a série toda":
                just if not just.startswith("(") else "cobre toda a janela do painel",
        })
    tab = pd.DataFrame(linhas)

    # so contam os trimestres em que o score EXISTE: onde a instituicao nao atinge o
    # minimo de indicadores (metade dos ativos, piso 2) o score e descartado, e anunciar
    # esse n no titulo sugeriria um score que o painel nao publica.
    com_score = hist[hist[f"score_{eixo}"].notna()]
    n_por_trim = com_score.groupby("data_base")[f"n_ind_{eixo}"].median()
    variacao = sorted(int(v) for v in n_por_trim.dropna().unique() if v > 0)
    sem_score = sorted(set(hist["data_base"]) - set(com_score["data_base"]))

    with st.expander(
            f"Cobertura de cada indicador · o score deste eixo usa "
            f"{'/'.join(str(v) for v in variacao) or '—'} indicadores conforme o trimestre",
            expanded=False):
        st.dataframe(
            tab, width='stretch', hide_index=True, height=60 + 38 * len(tab),
            column_config={
                "Trimestres": st.column_config.NumberColumn(
                    "Trim.", width="small", format="%d",
                    help="Quantos trimestres do painel têm dado para este indicador."),
                "de": st.column_config.NumberColumn("de", width="small", format="%d"),
                "Período": st.column_config.TextColumn("Período", width="small"),
                "Por que não é a série toda": st.column_config.TextColumn(
                    "Por que a série é essa", width="large"),
            })
        minimo = max(MIN_INDICADORES, math.ceil(len(cols) * FRACAO_MINIMA))
        faixa = ""
        if sem_score:
            faixa = (f" Sem score em {faixas_de_trimestres(sem_score)}: nesses trimestres "
                     f"nenhuma instituição chega ao mínimo, e o eixo fica <b>vazio</b> — "
                     f"selecionar uma dessas data-bases na barra lateral mostra o cartão "
                     f"sem número, e não um zero.")
        st.markdown(
            f"<div class='rodape-fonte'>O score é a média dos percentis "
            f"<b>disponíveis</b>: um indicador ausente reduz o divisor, não entra como "
            f"zero. Para o score existir, a instituição precisa de ao menos "
            f"<b>{minimo} dos {len(cols)}</b> indicadores deste eixo.{faixa}</div>",
            unsafe_allow_html=True)

        nota = T.txt(f"quebra.{eixo}.nota", "")
        if nota and not nota.startswith("("):
            st.markdown(f"<div class='cartao-just' style='font-size:12px'>{nota}</div>",
                        unsafe_allow_html=True)


def tabela_sinalizadas(eixo: str, cols: list[str]) -> None:
    """Quem foi sinalizado neste eixo, com o valor de cada indicador e o percentil.

    Fecha o circuito da pergunta: os cartões dizem o QUE distingue as sinalizadas, e
    esta tabela diz QUAIS são. Sem ela, o eixo termina num agregado sem nomes.
    """
    marc = univ[univ[f"sem_{eixo}"] == "alto"].sort_values(
        f"score_{eixo}", ascending=False)
    rot = T.bruto(f"eixos.{eixo}.rotulo", eixo).lower()

    with st.expander(f"As {len(marc)} instituições sinalizadas em {rot} — "
                     f"valor e percentil de cada indicador", expanded=False):
        if marc.empty:
            st.info("Nenhuma instituição atinge risco alto neste eixo, com os filtros atuais.")
            return

        linhas = []
        for r in marc.itertuples():
            reg = {
                "#": int(getattr(r, f"score_{eixo}") * 0) + len(linhas) + 1,
                "Instituição": r.instituicao,
                "TCB": r.tcb,
                "Carteira (R$ bi)": r.carteira_credito_real / 1e9,
                "Score do eixo": getattr(r, f"score_{eixo}"),
            }
            for c in cols:
                meta = catalogo.POR_CHAVE[c]
                v = getattr(r, c, None)
                p = getattr(r, f"pct_{c}", None)
                reg[meta.rotulo] = (f"{cartoes.num(v * meta.fator, meta.casas)}"
                                    f"{meta.unidade}" if pd.notna(v) else "—")
                reg[f"pct · {meta.rotulo}"] = round(p, 3) if pd.notna(p) else None
            linhas.append(reg)

        tab = pd.DataFrame(linhas)
        conf = {
            "#": st.column_config.NumberColumn("#", width="small", format="%d",
                                               help="Ordem por score do eixo."),
            "Instituição": st.column_config.TextColumn("Instituição", width="large"),
            "Carteira (R$ bi)": st.column_config.NumberColumn(
                "Carteira (R$ bi)", format="%.1f",
                help=f"Em reais de {fmt_trimestre(BASE_DEFL)}, deflacionada pelo IPCA."),
            "Score do eixo": st.column_config.ProgressColumn(
                "Score do eixo", format="%.3f", min_value=0.0, max_value=1.0,
                help=f"Média dos percentis dos indicadores deste eixo. "
                     f"≥ {cartoes.num(corte_alto, 2)} = risco alto."),
        }
        for c in cols:
            meta = catalogo.POR_CHAVE[c]
            conf[f"pct · {meta.rotulo}"] = st.column_config.NumberColumn(
                f"pct {meta.rotulo[:14]}", format="%.2f",
                help=f"Percentil de {meta.rotulo} dentro do grupo de pares (mesmo TCB). "
                     f"{'Invertido: maior é melhor.' if meta.sentido == 'menor_pior' else ''}")
        st.dataframe(tab, width='stretch', hide_index=True,
                     height=min(460, 60 + 35 * len(tab)), column_config=conf)

        st.markdown(
            f"<div class='rodape-fonte'>O <b>percentil</b> é a posição da instituição "
            f"dentro do seu grupo de pares (mesmo TCB), no trimestre — não no recorte "
            f"filtrado. Indicadores em que maior é melhor entram invertidos. "
            f"Um percentil só não sinaliza: é a <b>média</b> deles que compara com "
            f"<b>{cartoes.num(corte_alto, 2)}</b>"
            f"{'' if abs(corte_alto - CORTE_ALTO) < 1e-9 else ' (ajustado na barra lateral; o padrão é 0,75)'}"
            f".</div>", unsafe_allow_html=True)
        st.download_button(
            f"Baixar as sinalizadas em {rot} (CSV)",
            tab.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"sinalizadas_{eixo}_{dt_sel}.csv", mime="text/csv",
            key=f"dl_{eixo}")


def faixa_cartoes(pergunta: str) -> None:
    """Os 6 indicadores da pergunta como cartoes: valor, minisserie e faixa do universo."""
    eixo = {"p1": "crescimento", "p2": "concentracao", "p3": "deterioracao"}[pergunta]
    cols = ativos[eixo]
    hist = scored[scored["carteira_credito_real"] >= porte_min]
    linha1, linha2 = st.columns(3, gap="medium"), None
    for i, c in enumerate(cols):
        if i == 3:
            linha2 = st.columns(3, gap="medium")
        alvo = (linha1 if i < 3 else linha2)[i % 3]
        with alvo:
            st.markdown(
                cartoes.cartao_indicador(
                    univ, c, NOTAS_CARTAO.get(c, ""),
                    glossario=T.glossario_indicadores,
                    eixo=eixo,
                    rotulo_eixo=T.bruto(f"eixos.{eixo}.rotulo", eixo).lower(),
                    data_base=dt_sel),
                unsafe_allow_html=True)
    n_marc = int((univ[f"sem_{eixo}"] == "alto").sum())
    st.markdown(
        f"<div class='rodape-fonte'>Cada cartão traz os <b>dois</b> valores: a mediana "
        f"das <b>{n_marc}</b> sinalizadas neste eixo — as mesmas que formam o número da "
        f"Visão geral — e a do recorte inteiro ({len(univ)} instituições), como "
        f"referência.<br>"
        f"<b>O gráfico é a distribuição do recorte em {fmt_trimestre(dt_sel)}</b>, não "
        f"uma série no tempo: o histograma claro dá a forma, a barra azul é o intervalo "
        f"p25–p75 com o traço escuro na mediana, e os riscos vermelhos são cada uma das "
        f"{n_marc} sinalizadas — o traço vermelho é a mediana delas. É exatamente o que o "
        f"<b>percentil</b> mede, e o percentil é o que decide a seleção. A escala vai do "
        f"p05 ao p95 do recorte; quem fica fora é contado no texto, e não desenhado fora "
        f"de proporção.<br>"
        f"A <b>cobertura no tempo</b> de cada indicador — que varia de 3 a 29 trimestres "
        f"— está no bloco abaixo.</div><div style='height:6px'></div>",
        unsafe_allow_html=True)
    st.markdown(
        f"<div class='aviso'><b>Cobertura da série neste eixo.</b> "
        f"{T.txt(f'series.{eixo}.curta', '')}</div>", unsafe_allow_html=True)
    cobertura_indicadores(eixo, cols)
    tabela_sinalizadas(eixo, cols)


def destaque(df: pd.DataFrame, eixo: str) -> dict:
    """Cores, tamanhos e rótulo para separar as SINALIZADAS do resto num gráfico.

    Os gráficos sempre responderam aos filtros — medido: com o corte em R$ 100 bi o
    scatter de P1 cai de 257 para 9 pontos. O que faltava era ligá-los à SELEÇÃO: com
    todos os pontos da mesma cor, nada na figura dizia quais são as instituições que a
    página inteira está discutindo, e o gráfico parecia indiferente ao que se escolhia.
    """
    col = f"sem_{eixo}"
    marc = (df[col] == "alto") if col in df.columns else pd.Series(False, index=df.index)
    n = int(marc.sum())
    return {
        "marcada": marc,
        "n": n,
        "cor": [TEMA["risco_alto"] if m else TEMA["marca_clara"] for m in marc],
        "borda": [TEMA["risco_alto"] if m else TEMA["eixo"] for m in marc],
        "opacidade": [0.92 if m else 0.40 for m in marc],
        "legenda": (f"<span style='color:{TEMA['risco_alto']}'>●</span> "
                    f"<b>{n}</b> sinalizadas neste eixo · "
                    f"<span style='color:{TEMA['marca_clara']}'>●</span> "
                    f"demais {len(df) - n} do recorte"),
    }


def _preferir_sinalizadas(df: pd.DataFrame, eixo: str, col: str,
                          n: int) -> pd.DataFrame:
    """As `n` maiores em `col`, mas dando a vez às SINALIZADAS do eixo.

    Um "top 12 por indicador" escolhido sem olhar a seleção põe na tela instituições
    que a página não está discutindo, e deixa de fora as que estão na agenda.
    """
    col_sem = f"sem_{eixo}"
    if col_sem not in df.columns:
        return df.nlargest(n, col)
    marc = df[df[col_sem] == "alto"].nlargest(n, col)
    falta = n - len(marc)
    if falta <= 0:
        return marc
    resto = df[~df.index.isin(marc.index)].nlargest(falta, col)
    return pd.concat([marc, resto]).sort_values(col, ascending=False)


def nota_destaque(d: dict) -> None:
    st.markdown(f"<div class='rodape-fonte'>{d['legenda']}</div>",
                unsafe_allow_html=True)


@st.cache_data(show_spinner=False)
def cresc_por_modalidade(_df: pd.DataFrame, dt: int, chave: str = "") -> pd.DataFrame:
    """Crescimento real anual por modalidade PF, por instituição.

    `chave` existe para o cache NAO mentir. O Streamlit ignora argumentos prefixados com
    `_` ao montar a chave do cache, entao `_df` nao entra nela: sem `chave`, trocar o
    filtro devolveria o resultado calculado com o filtro anterior. Aqui o risco era
    baixo -- o crescimento por modalidade e por instituicao e nao depende do conjunto --,
    mas um cache que ignora a entrada e uma armadilha esperando o proximo indicador.
    """
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
            dst = destaque(d, "crescimento")
            fig = go.Figure()
            for marcada, nome in ((False, "demais do recorte"), (True, "sinalizadas")):
                sub = d[dst["marcada"].values == marcada]
                if sub.empty:
                    continue
                fig.add_trace(go.Scatter(
                    x=sub["p1_1_cresc_real_aa"] * 100, y=sub["share_carteira"] * 100,
                    mode="markers", text=_hover(sub), hoverinfo="text", name=nome,
                    marker=dict(size=_tamanho(sub),
                                color=TEMA["risco_alto"] if marcada else TEMA["marca_clara"],
                                opacity=0.9 if marcada else 0.45,
                                line=dict(width=0.8 if marcada else 0.4,
                                          color="white"))))
            fig.add_vline(x=med * 100, line=dict(color=TEMA["referencia"], width=1),
                          annotation_text="mediana", annotation_position="top")
            fig.add_vline(x=LIMIAR_BOOM * 100,
                          line=dict(color=TEMA["risco_alto"], width=1, dash="dash"),
                          annotation_text="15% a.a.", annotation_position="top right")
            fig.update_yaxes(type="log", title="Participação na carteira (%, log)")
            fig.update_xaxes(title="Crescimento real da carteira (% a.a.)")
            sem_grafico(fig)
            nota_destaque(dst)
        bloco_lrc("p1_1")

    # ---- 2. carteira x tendencia HP
    with l1c2:
        st.markdown(f"**{LRC['p1_2']['titulo']}**")
        # CRITÉRIO: sinalizadas, com série longa o bastante, as maiores por carteira.
        #
        # Antes era "as 4 de maior credit gap", e isso selecionava sistematicamente as
        # séries menos informativas: gap alto anda junto com série curta e volátil, que
        # é o perfil de cooperativa pequena. Medido, o gráfico vinha com séries de
        # 1, 4, 4 e 1 pontos — duas delas um ponto só, que não desenha linha.
        # Exigir MIN_PONTOS_HP e ordenar por carteira traz quem tem história para
        # mostrar e peso para justificar a tela.
        MIN_PONTOS_HP = 12
        _pontos = (scored.dropna(subset=["p1_2_credit_gap"])
                         .groupby("cod_inst")["data_base"].nunique())
        _longas = set(_pontos[_pontos >= MIN_PONTOS_HP].index)
        _cg = univ.dropna(subset=["p1_2_credit_gap"])
        _cg = _cg[_cg["cod_inst"].isin(_longas)]
        _marc = _cg[_cg["sem_crescimento"] == "alto"] if "sem_crescimento" in _cg else _cg
        cands = _marc.nlargest(4, "carteira_credito_real")["cod_inst"].tolist()
        # completa com as maiores do recorte que tenham série longa, se faltar
        cands += [c for c in _cg.nlargest(8, "carteira_credito_real")["cod_inst"]
                  if c not in cands][:max(0, 4 - len(cands))]
        if not cands:
            st.info("Série insuficiente para o filtro HP no recorte.")
        else:
            hist = scored[scored["cod_inst"].isin(cands)].sort_values("data_base")
            # O eixo x e CATEGORICO. Sem ordem declarada, o Plotly monta as categorias
            # na ordem em que os traces as apresentam -- medido aqui: 202603, 202406,
            # 202409, 202412, porque o primeiro traco so tem o ultimo trimestre. O
            # resultado eram rotulos fora de ordem e linhas saltando no tempo.
            eixo_x = [fmt_trimestre(x) for x in sorted(scored["data_base"].unique())]
            _brutos = [hist[hist["cod_inst"] == c]["instituicao"].iloc[-1]
                       for c in cands if not hist[hist["cod_inst"] == c].empty]
            _rotulos = dict(zip(cands, nomes_distintos(_brutos, 44)))
            fig = go.Figure()
            cores = TEMA["sequencial"][2:]
            for i, cod in enumerate(cands):
                h = hist[hist["cod_inst"] == cod].dropna(subset=["p1_2_credit_gap"])
                if h.empty:
                    continue
                nome = _rotulos.get(cod, nome_curto(h["instituicao"].iloc[-1], 44))
                # um unico ponto nao desenha linha: vira marcador visivel
                so_um = len(h) == 1
                fig.add_trace(go.Scatter(
                    x=[fmt_trimestre(x) for x in h["data_base"]],
                    y=h["p1_2_credit_gap"] * 100,
                    mode="markers" if so_um else "lines+markers",
                    name=f"{nome} (1 trim.)" if so_um else nome,
                    line=dict(width=2, color=cores[i % len(cores)]),
                    marker=dict(size=9 if so_um else 4,
                                color=cores[i % len(cores)],
                                symbol="diamond" if so_um else "circle")))
            fig.add_hline(y=0, line=dict(color=TEMA["referencia"], width=1))
            fig.update_xaxes(categoryorder="array", categoryarray=eixo_x,
                             tickangle=-45, nticks=10)
            fig.update_yaxes(title="Desvio da própria tendência (%)")
            sem_grafico(fig)
            st.markdown(
                f"<div class='rodape-fonte'>Critério: entre as <b>sinalizadas em "
                f"crescimento</b> com pelo menos <b>{MIN_PONTOS_HP} trimestres</b> de "
                f"série, as <b>maiores por carteira</b>. O filtro HP precisa de "
                f"história: ordenar por maior gap traria justamente as séries mais "
                f"curtas, porque gap alto e série curta andam juntos.</div>",
                unsafe_allow_html=True)
        bloco_lrc("p1_2")

    l2c1, l2c2 = st.columns(2)

    # ---- 3. heatmap crescimento por modalidade
    with l2c1:
        st.markdown(f"**{LRC['p1_3']['titulo']}**")
        cm = cresc_por_modalidade(
            scored, dt_sel,
            chave=f"{sorted(tcb_sel)}|{sorted(seg_sel)}|{porte_min}")
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
                z=z, x=mods, y=[nome_curto(n, 30) for n in cm["instituicao"]],
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
            dst = destaque(dc, "crescimento")
            fig = go.Figure(go.Bar(
                x=dc["p1_4_cresc_carteira_sobre_capital"],
                y=[nome_curto(n, 30) for n in dc["instituicao"]],
                orientation="h", marker_color=dst["cor"],
                marker_line=dict(width=1, color=dst["borda"]),
                customdata=["sinalizada" if m else "não sinalizada"
                            for m in dst["marcada"]],
                hovertemplate="%{y}<br>razão: %{x:.2f}<br>%{customdata}<extra></extra>"))
            fig.add_vline(x=1.0, line=dict(color=TEMA["referencia"], width=1.5, dash="dash"),
                          annotation_text="pari passu")
            fig.update_xaxes(title="Crescimento da carteira ÷ crescimento do capital")
            fig.update_yaxes(autorange="reversed", tickmode="linear", dtick=1)
            sem_grafico(fig)
            nota_destaque(dst)
        bloco_lrc("p1_4")

    fonte("BCB/IF.data (Resumo e Informações de Capital) e BCB/SCR.data. "
          f"Valores reais em R$ de {fmt_trimestre(BASE_DEFL)}.")


# ================================================================== P2
def contexto_sistema() -> None:
    """HHI e CR5 como CONTEXTO, e nao como indicador da instituição.

    Os dois têm um único valor por trimestre, idêntico para as 258 instituições do
    recorte. Nunca entraram no score — o escopo "sistema" já os excluía —, mas ocupavam
    duas das seis vagas de P2, que por isso pontuava com 4 percentis enquanto P1 e P3
    pontuavam com 6. Como cartão eram piores ainda: sem dispersão, o gráfico de
    distribuição fabricava um teto de escala.

    Aqui eles ficam onde fazem sentido: uma faixa de contexto, lida contra os limiares
    de referência, antes dos seis indicadores que de fato distinguem instituições.
    """
    # RECALCULADOS sobre o recorte. Concentracao e propriedade DO CONJUNTO: com o
    # recorte em carteira >= R$ 10 bi o HHI vai de 951 para 1.169 e o CR5 de 64,8% para
    # 71,9%. Ler a coluna gravada (que e do universo inteiro) fazia a tela nao responder
    # a filtro nenhum.
    hhi_r, cr5_r = cartoes.hhi_cr5(univ)
    sistema = ind[ind["data_base"] == dt_sel]
    hhi_s, cr5_s = cartoes.hhi_cr5(sistema)
    if pd.isna(hhi_r) and pd.isna(cr5_r):
        return
    filtrado = len(univ) < len(sistema)

    def _ref(v_r, v_s, casas, unid=""):
        if not filtrado or pd.isna(v_s):
            return ""
        return (f" No universo inteiro do IF.data ({len(sistema)} instituições): "
                f"<b>{cartoes.num(v_s, casas)}{unid}</b> — é a marca tracejada na régua.")

    c1, c2 = st.columns(2, gap="medium")
    if pd.notna(hhi_r):
        nivel = ("baixo" if hhi_r < 1500 else "medio" if hhi_r < 2500 else "alto")
        with c1:
            st.markdown(
                f"<div class='cartao'>"
                f"<div class='cartao-topo'><span class='cartao-rotulo'>HHI do recorte"
                f"</span><span class='selo' style='background:{SEMAFORO_SOFT[nivel]};"
                f"color:{SEMAFORO[nivel]}'>"
                f"{'desconcentrado' if nivel == 'baixo' else 'moderado' if nivel == 'medio' else 'concentrado'}"
                f"</span></div>"
                f"<div class='cartao-valor'>{cartoes.num(hhi_r, 0)}</div>"
                f"<div class='cartao-releitura'>soma dos quadrados das participações de "
                f"mercado das <b>{len(univ)}</b> instituições do recorte, de 0 a 10.000"
                f"</div>"
                f"<div class='cartao-dist'>{regua(hhi_r, 0, 5000, [(1500, TEMA['risco_baixo']), (2500, TEMA['risco_medio']), (5000, TEMA['risco_alto'])], referencia=hhi_s)}</div>"
                f"<div class='dist-eixo'><span>0</span><span>1.500</span>"
                f"<span>2.500</span><span>5.000</span></div>"
                f"<div class='cartao-escala'>abaixo de 1.500 desconcentrado · 1.500 a "
                f"2.500 moderadamente concentrado · acima de 2.500 concentrado. A régua "
                f"vai até 5.000; o máximo teórico é 10.000 (monopólio)."
                f"{_ref(hhi_r, hhi_s, 0)}</div></div>",
                unsafe_allow_html=True)
    if pd.notna(cr5_r):
        with c2:
            st.markdown(
                f"<div class='cartao'>"
                f"<div class='cartao-topo'><span class='cartao-rotulo'>CR5 do recorte"
                f"</span></div>"
                f"<div class='cartao-valor'>{cartoes.num(cr5_r, 1)}<span class='unidade'>%"
                f"</span></div>"
                f"<div class='cartao-releitura'>fatia da carteira nas cinco maiores das "
                f"<b>{len(univ)}</b> instituições do recorte</div>"
                f"<div class='cartao-dist'>{regua(cr5_r, 0, 100, [(100, TEMA['marca_clara'])], referencia=cr5_s)}</div>"
                f"<div class='dist-eixo'><span>0%</span><span>50%</span>"
                f"<span>100%</span></div>"
                f"<div class='cartao-escala'>Complementa o HHI, que pode ser baixo só "
                f"por haver milhares de instituições pequenas. Não há limiar oficial: "
                f"é leitura de nível e de tendência.{_ref(cr5_r, cr5_s, 1, '%')}</div>"
                f"</div>",
                unsafe_allow_html=True)

    st.markdown(
        f"<div class='rodape-fonte'>Estes <b>dois números descrevem o conjunto, não a "
        f"instituição</b>: uma vez fixado o recorte, valem igualmente para todas as "
        f"{len(univ)}. Por isso não geram percentil e <b>não entram no score</b> — "
        f"ranquear instituições por um número igual para todas não diria nada. Eles "
        f"definem o contexto em que os seis indicadores abaixo são lidos, e "
        f"<b>respondem aos filtros</b>: restringir o recorte a instituições maiores "
        f"eleva os dois, porque concentração é propriedade do conjunto que se escolhe "
        f"olhar.</div><div style='height:10px'></div>", unsafe_allow_html=True)


with aba2:
    st.markdown(f"#### {T.txt('abas.p2')}")
    contexto_sistema()
    faixa_cartoes("p2")
    m1c1, m1c2 = st.columns(2)

    # ---- 1. HHI e CR5 do sistema
    with m1c1:
        st.markdown(f"**{LRC['p2_1']['titulo']}**")
        # recalculado por trimestre sobre o RECORTE (hist ja tem os filtros e o corte
        # de carteira aplicados), e nao lido da coluna gravada, que e do universo
        # inteiro e nao responderia a filtro nenhum
        _h = scored[scored["carteira_credito_real"] >= porte_min]
        sist = pd.DataFrame(
            [{"data_base": d, **dict(zip(("hhi", "cr5"), cartoes.hhi_cr5(g)))}
             for d, g in _h.groupby("data_base")]).sort_values("data_base")
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
        dp = dp[dp["pf_total_real"] > 0]
        dp = _preferir_sinalizadas(dp, "concentracao", "p2_3_pct_alto_risco", 12)
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
                    y=[nome_curto(n, 30) for n in dp["instituicao"]],
                    x=(dp[col] / dp["pf_total_real"] * 100).fillna(0),
                    name=nome, orientation="h",
                    marker_color=paleta.get(nome, TEMA["neutro"]),
                    hovertemplate="%{y}<br>" + nome + ": %{x:.1f}%<extra></extra>"))
            fig.update_layout(barmode="stack")
            fig.update_xaxes(title="% da carteira PF")
            fig.update_yaxes(autorange="reversed", tickmode="linear", dtick=1,
                             automargin=True)
            sem_grafico(fig)
            st.markdown(
                "<div class='rodape-fonte'>Critério: as <b>12 de maior fatia em "
                "modalidades de alto risco</b>, com as <b>sinalizadas em concentração</b> "
                "entrando primeiro.</div>", unsafe_allow_html=True)
        bloco_lrc("p2_2")

    m2c1, m2c2 = st.columns(2)

    # ---- 3. concentracao regional
    with m2c1:
        st.markdown(f"**{LRC['p2_3']['titulo']}**")
        cols_reg = {"reg_sudeste_real": "Sudeste", "reg_sul_real": "Sul",
                    "reg_nordeste_real": "Nordeste", "reg_norte_real": "Norte",
                    "reg_centro_oeste_real": "Centro-oeste"}
        cols_reg = {k: v for k, v in cols_reg.items() if k in univ.columns}
        # CRITÉRIO: sinalizadas, as maiores por carteira.
        #
        # Antes era "as 12 de maior HHI regional", e isso é selecionar quem é
        # monorregional por construção: medido, 7 das 12 tinham mais de 95% da carteira
        # numa única região, com mediana de 97,4%. O gráfico virava doze barras de uma
        # cor só — a figura se anulava. Ordenar por carteira entre as sinalizadas mostra
        # a composição regional de quem pesa, e aí há variedade para ver.
        dr = _preferir_sinalizadas(univ.dropna(subset=["p2_4_hhi_regional"]),
                                   "concentracao", "carteira_credito_real", 12)
        if dr.empty or not cols_reg:
            st.info("Sem dados regionais no recorte.")
        else:
            tot = dr[list(cols_reg)].sum(axis=1).replace(0, pd.NA)
            fig = go.Figure()
            for i, (col, nome) in enumerate(cols_reg.items()):
                fig.add_trace(go.Bar(
                    y=[nome_curto(n, 30) for n in dr["instituicao"]],
                    x=(dr[col] / tot * 100).fillna(0), name=nome, orientation="h",
                    marker_color=TEMA["sequencial"][(i + 1) % len(TEMA["sequencial"])],
                    hovertemplate="%{y}<br>" + nome + ": %{x:.1f}%<extra></extra>"))
            fig.update_layout(barmode="stack")
            fig.update_xaxes(title="% da carteira por região")
            fig.update_yaxes(autorange="reversed", tickmode="linear", dtick=1,
                             automargin=True)
            sem_grafico(fig)
            st.markdown(
                "<div class='rodape-fonte'>Critério: entre as <b>sinalizadas em "
                "concentração</b>, as <b>maiores por carteira</b>. Ordenar por maior "
                "HHI regional selecionaria quem é monorregional por construção — e as "
                "barras sairiam todas de uma cor só.</div>",
                unsafe_allow_html=True)
        bloco_lrc("p2_3")

    # ---- 4. loan-to-deposit x crescimento
    with m2c2:
        st.markdown(f"**{LRC['p2_4']['titulo']}**")
        dl = univ.dropna(subset=["p2_6_loan_to_deposit", "p1_1_cresc_real_aa"])
        dl = dl[dl["p2_6_loan_to_deposit"].between(0, 5)]
        if dl.empty:
            st.info("Sem dados de funding no recorte.")
        else:
            dst = destaque(dl, "concentracao")
            fig = go.Figure()
            for marcada, nome in ((False, "demais do recorte"), (True, "sinalizadas")):
                sub = dl[dst["marcada"].values == marcada]
                if sub.empty:
                    continue
                fig.add_trace(go.Scatter(
                    x=sub["p1_1_cresc_real_aa"] * 100, y=sub["p2_6_loan_to_deposit"],
                    mode="markers", text=_hover(sub), hoverinfo="text", name=nome,
                    marker=dict(size=_tamanho(sub),
                                color=TEMA["risco_alto"] if marcada else TEMA["marca_clara"],
                                opacity=0.9 if marcada else 0.45,
                                line=dict(width=0.8 if marcada else 0.4, color="white"))))
            fig.add_hline(y=1.0, line=dict(color=TEMA["referencia"], width=1, dash="dash"),
                          annotation_text="carteira = captações")
            fig.add_vline(x=dl["p1_1_cresc_real_aa"].median() * 100,
                          line=dict(color=TEMA["referencia"], width=1),
                          annotation_text="mediana")
            fig.update_xaxes(title="Crescimento real da carteira (% a.a.)")
            fig.update_yaxes(title="Carteira ÷ captações")
            sem_grafico(fig)
            nota_destaque(dst)
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
            # a COR ja codifica cobertura, entao as sinalizadas sao marcadas pelo
            # CONTORNO -- distingue a selecao sem disputar com a escala de cor
            marker=dict(size=_tamanho(da, 54), color=cob,
                        colorscale=[[0, TEMA["risco_alto"]], [0.45, TEMA["risco_medio"]],
                                    [1, TEMA["risco_baixo"]]],
                        cmin=0, cmax=3, opacity=0.78,
                        line=dict(
                            width=[2.4 if m else 0.6
                                   for m in (da["sem_deterioracao"] == "alto")],
                            color=[TEMA["texto"] if m else "white"
                                   for m in (da["sem_deterioracao"] == "alto")]),
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
        _n_marc = int((da["sem_deterioracao"] == "alto").sum())
        st.markdown(
            f"<div class='rodape-fonte'>A <b>cor</b> é a cobertura de provisões; o "
            f"<b>contorno escuro</b> marca as <b>{_n_marc}</b> instituições sinalizadas "
            f"em deterioração dentro deste recorte, e o tamanho é a carteira. Mudar os "
            f"filtros muda quem aparece e quem é contornado.</div>",
            unsafe_allow_html=True)

        prio = da[(da["p1_1_cresc_real_aa"] > med_x) & (da["p3_1_inadimplencia"] < med_y)]
        baixa_prov = prio[prio["p3_3_provisao_sobre_carteira"]
                          < prio["p3_3_provisao_sobre_carteira"].median()]
        st.markdown(
            f"<div class='aviso'><b>{len(prio)}</b> instituições estão no quadrante de agenda "
            f"prioritária; <b>{len(baixa_prov)}</b> delas também provisionam abaixo da mediana "
            f"do quadrante — a combinação que o trabalho persegue.</div>",
            unsafe_allow_html=True)
    bloco_lrc("p3_1")

    # Duas colunas, e não três: o gráfico de folga é de barras horizontais com 15 nomes
    # de instituição, e em 1/3 da largura o Plotly cortava o começo do rótulo
    # ("ERATIVA DE CRÉDITO DE LIV…"), a anotação do mínimo e o título do eixo. Ele passa
    # a ocupar a linha inteira, abaixo.
    n1, n2 = st.columns(2)

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
            _d = destaque(dd, "deterioracao")
            for _m, _n in ((False, "demais do recorte"), (True, "sinalizadas")):
                _s = dd[_d["marcada"].values == _m]
                if _s.empty:
                    continue
                fig.add_trace(go.Scatter(
                    x=_s["p3_1_inadimplencia"] * 100,
                    y=_s["p3_4_inadimplencia_ajustada"] * 100,
                    mode="markers", text=_hover(_s), hoverinfo="text", name=_n,
                    marker=dict(size=_tamanho(_s, 34),
                                color=TEMA["risco_alto"] if _m else TEMA["marca_clara"],
                                opacity=0.9 if _m else 0.45,
                                line=dict(width=0.8 if _m else 0.4, color="white"))))
            fig.update_xaxes(title="Inadimplência corrente (%)", range=[0, lim])
            fig.update_yaxes(title="Ajustada ao crescimento (%)", range=[0, lim])
            sem_grafico(fig)
            nota_destaque(_d)
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
            dqd = destaque(dq, "deterioracao")
            fig = go.Figure()
            for _m, _n in ((False, "demais do recorte"), (True, "sinalizadas")):
                _s = dq[dqd["marcada"].values == _m]
                if _s.empty:
                    continue
                fig.add_trace(go.Scatter(
                    x=_s["p3_2_cobertura"] * 100,
                    y=_s["p3_5_ativos_problematicos"] * 100,
                    mode="markers", text=_hover(_s), hoverinfo="text", name=_n,
                    marker=dict(size=_tamanho(_s, 34),
                                color=TEMA["risco_alto"] if _m else TEMA["marca_clara"],
                                opacity=0.92 if _m else 0.45,
                                line=dict(width=0.8 if _m else 0.4, color="white"))))
            fig.add_vline(x=100, line=dict(color=TEMA["risco_alto"], width=1.2, dash="dash"),
                          annotation_text="cobertura 100%")
            if len(ref_scr):
                fig.add_hline(y=float(ref_scr.iloc[0]),
                              line=dict(color=TEMA["referencia"], width=1),
                              annotation_text="sistema (SCR)")
            fig.update_xaxes(title="Cobertura de provisões (%)")
            fig.update_yaxes(title="Ativos problemáticos (% da carteira)")
            sem_grafico(fig)
            nota_destaque(dqd)
        bloco_lrc("p3_3")

    # ---- 4. folga de capital (linha inteira: 15 nomes não cabem em 1/3 da largura)
    st.markdown(f"**{LRC['p3_4']['titulo']}**")
    dk = univ.dropna(subset=["p3_6_folga_capital_pp"]).nsmallest(15, "p3_6_folga_capital_pp")
    if dk.empty:
        st.info("Sem dados de capital nesta data-base.")
    else:
        # A COR mede a distância do mínimo regulatório, que é a leitura do gráfico.
        # O CONTORNO marca quem está sinalizado em deterioração — assim as duas
        # informações convivem sem uma apagar a outra.
        cores = [TEMA["risco_alto"] if v < 2 else
                 TEMA["risco_medio"] if v < 5 else TEMA["marca"]
                 for v in dk["p3_6_folga_capital_pp"]]
        marc = (dk["sem_deterioracao"] == "alto") if "sem_deterioracao" in dk else \
            pd.Series(False, index=dk.index)
        fig = go.Figure(go.Bar(
            x=dk["p3_6_folga_capital_pp"],
            y=[nome_curto(n, 44) for n in dk["instituicao"]],
            orientation="h", marker_color=cores,
            marker_line=dict(width=[2.2 if m else 0.5 for m in marc],
                             color=[TEMA["texto"] if m else "white" for m in marc]),
            customdata=[("sinalizada em deterioração" if m else "não sinalizada")
                        for m in marc],
            hovertemplate="%{y}<br>folga: %{x:.2f} p.p.<br>%{customdata}<extra></extra>"))
        fig.add_vline(x=0, line=dict(color=TEMA["risco_alto"], width=1.5),
                      annotation_text=f"mínimo {MIN_BASILEIA}%",
                      annotation_position="bottom right")
        fig.update_xaxes(title="Folga sobre o mínimo (p.p.)", automargin=True)
        fig.update_yaxes(autorange="reversed", tickmode="linear", dtick=1,
                         automargin=True)
        sem_grafico(fig, altura=460)
        st.markdown(
            f"<div class='rodape-fonte'>As <b>15 menores folgas</b> do recorte. A cor "
            f"mede a distância do mínimo de {cartoes.num(MIN_BASILEIA, 1)}% — "
            f"<span style='color:{TEMA['risco_alto']}'>■</span> abaixo de 2 p.p., "
            f"<span style='color:{TEMA['risco_medio']}'>■</span> de 2 a 5 p.p., "
            f"<span style='color:{TEMA['marca']}'>■</span> acima — e o "
            f"<b>contorno escuro</b> marca as <b>{int(marc.sum())}</b> que também estão "
            f"sinalizadas em deterioração. Barra à esquerda do zero = capital abaixo do "
            f"exigido.</div>", unsafe_allow_html=True)
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
    # Pre-seleciona as tres primeiras da agenda, UMA POR SISTEMA. Sem isso a tela
    # abria comparando tres singulares Cresol entre si -- tres colunas parecidas
    # que nao respondem a pergunta do comparador, que e contrastar perfis.
    if lista.empty:
        padrao = []
    else:
        vistos, padrao = set(), []
        for r in lista.itertuples():
            chave = grupos.chave_linha(getattr(r, "grupo", ""), r.cod_inst)
            if chave in vistos or r.cod_inst not in mapa:
                continue
            vistos.add(chave)
            padrao.append(r.cod_inst)
            if len(padrao) == 3:
                break

    sel = st.multiselect("Instituições (2 a 4)", list(mapa), default=padrao,
                         format_func=lambda c: mapa.get(c, c), max_selections=4)

    if len(sel) < 2:
        st.info("Selecione ao menos duas instituições.")
    else:
        comp = univ[univ["cod_inst"].isin(sel)]
        # A lista de linhas e MONTADA a partir da selecao ativa: trocar um indicador na
        # barra lateral troca a linha aqui tambem, sem editar codigo.
        rot_p = {"crescimento": "P1", "concentracao": "P2", "deterioracao": "P3"}
        LINHAS = [
            ("Carteira de crédito (R$ bi)", "carteira_credito_real", lambda v: v / 1e9, "{:,.1f}"),
            ("Participação no sistema (%)", "share_carteira", lambda v: v * 100, "{:.3f}"),
        ]
        for eixo in EIXOS:
            for i, chave in enumerate(ativos[eixo], start=1):
                meta = catalogo.POR_CHAVE[chave]
                sufixo = f" ({meta.unidade})" if meta.unidade else ""
                LINHAS.append((
                    f"{rot_p[eixo]}·{i} {meta.rotulo}{sufixo}", chave,
                    (lambda fat: (lambda v: v * fat))(meta.fator),
                    "{:,." + str(meta.casas) + "f}"))
        LINHAS += [
            ("Score final", "score_final", lambda v: v, "{:.3f}"),
            # contexto descritivo -- NAO entra no score nem conta como um dos 18 indicadores
            ("(contexto) Ticket médio por cliente (R$ mil)", "ctx_ticket_medio_real",
             lambda v: v / 1e3, "{:,.1f}"),
        ]
        # Cortar o nome em 22 caracteres fazia DUAS cooperativas do mesmo sistema
        # virarem a mesma chave do dicionario -- "COOPERATIVA DE CRÉDITO" e
        # "COOPERATIVA DE CRÉDITO" --, e a segunda sobrescrevia a primeira: o
        # comparador mostrava tres selecionadas e duas colunas, sem avisar.
        rotulos = dict(zip(sel, nomes_distintos([mapa[c] for c in sel], n=30)))

        linhas = []
        for rotulo, col, tr, f in LINHAS:
            reg = {"Indicador": rotulo}
            for cod in sel:
                r = comp[comp["cod_inst"] == cod]
                v = r[col].iloc[0] if (len(r) and col in r.columns) else None
                reg[rotulos[cod]] = f.format(tr(v)) if pd.notna(v) else "—"
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
                st.markdown(f"**{rotulos[cod]}**")
                for eixo in EIXOS:
                    st.markdown(
                        f"{sem_html(r[f'sem_{eixo}'])} {eixo.capitalize()} — "
                        f"{r[f'score_{eixo}']:.2f}" if pd.notna(r[f"score_{eixo}"])
                        else f"{sem_html('sem')} {eixo.capitalize()} — sem dado",
                        unsafe_allow_html=True)

    fonte(f"BCB/IF.data, data-base {fmt_trimestre(dt_sel)}. "
          f"Valores reais em R$ de {fmt_trimestre(BASE_DEFL)}.")
