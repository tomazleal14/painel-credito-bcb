"""
grupos.py -- agrupamento por SISTEMA COOPERATIVO, apenas para APRESENTACAO.

POR QUE EXISTE
  No recorte de 03/2026 (carteira >= R$ 1 bi), 154 das 258 instituicoes sao
  cooperativas singulares. Onze das 21 posicoes da agenda de atipicas eram
  singulares do mesmo sistema (Cresol), e onze linhas quase identicas empurram
  o resto do recorte para fora da tela. Nao e um acaso do trimestre: em
  12/2021 eram 11 Sicredi e 9 Sicoob numa agenda de 46.

  Colapsadas, as mesmas linhas passam a dizer uma coisa que antes nao se via:
  Cresol tem 11 de 13 singulares sinalizadas (85%), Sicoob tem 2 de 43 (5%).

O QUE ESTE MODULO NAO FAZ
  Nao soma carteira para efeito de calculo, nao consolida balanco, nao recalcula
  NENHUM indicador e nao toca em nenhum score. Cada singular continua pontuada
  individualmente, no grupo de pares dela. O que sai daqui e um ROTULO.

FONTE E LIMITE -- leia antes de usar
  O IF.data NAO publica a filiacao de uma singular a um sistema. Verificado no
  proprio relatorio: os sete filtros disponiveis (TCB, TC, TD, TI, SR, TCip) nao
  tem campo de sistema; os campos de conglomerado do cadastro so vem preenchidos
  para conglomerados; toda singular aparece como "Instituicao independente" --
  o que, do ponto de vista prudencial, ela e.

  Logo, o vinculo aqui e DEDUZIDO da marca que aparece no campo `instituicao`
  do proprio IF.data. E construcao nossa, nao dado do BCB, e esta registrada
  como tal no Caderno de Processo e no relatorio de limites.

  Cobertura: 598 de 953 cooperativas da base (63%). As demais nao trazem marca
  no nome legal -- entre as maiores, Credicitrus (R$ 9,0 bi), Viacredi
  (R$ 8,5 bi), Sisprime (R$ 5,6 bi) e Sul-Serrana (R$ 4,6 bi) -- e seguem
  listadas individualmente. NAO ha chute de filiacao: se a marca nao esta no
  nome publicado, nao ha grupo.

  MODO DE FALHA: um vinculo nao reconhecido deixa a cooperativa sozinha na
  lista, que e exatamente o comportamento anterior a este modulo. Nenhum numero
  muda. Foi por isso que se escolheu agrupar na apresentacao em vez de agregar
  de fato: ali o mesmo erro produziria um numero errado.

PERIMETRO
  A regra vale so para cooperativas (TCB b3S e b3C). Os bancos cooperativos --
  Banco Sicoob, Bco Cooperativo Sicredi -- sao conglomerados prudenciais
  proprios, ja consolidados pelo BCB, e continuam como linha propria: juntar os
  dois seria misturar dois perimetros de consolidacao diferentes num rotulo so.
"""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

# Marca -> padrao procurado no nome publicado pelo IF.data, ja normalizado.
# A ordem importa: vale a PRIMEIRA que casar.
MARCAS: tuple[tuple[str, str], ...] = (
    ("Sicredi", r"SICREDI"),
    ("Sicoob", r"SICOOB"),
    ("Cresol", r"CRESOL"),
    ("Unicred", r"UNICRED"),
    ("Uniprime", r"UNIPRIME"),
    ("Credisis", r"CREDISIS"),
    ("Sulcredi", r"SULCREDI"),
    ("Crehnor", r"CREHNOR"),
    ("Ailos", r"AILOS"),
)

# So cooperativas entram na regra -- ver PERIMETRO no topo.
TCB_COOPERATIVO = ("b3S", "b3C")

# Abaixo disso nao ha o que colapsar: uma "linha de sistema" com um membro so
# esconde o nome da instituicao e nao economiza espaco nenhum.
MINIMO_PARA_AGRUPAR = 2

SEM_GRUPO = ""


def normaliza(s: object) -> str:
    """Maiusculas, sem acento, espacos colapsados -- a base de comparacao.

    O IF.data alterna acentuacao no mesmo nome ao longo do tempo ("CREDITO" e
    "CRÉDITO" na mesma serie), entao comparar sem normalizar perde vinculo.
    """
    t = unicodedata.normalize("NFKD", str(s or ""))
    t = t.encode("ascii", "ignore").decode().upper()
    return re.sub(r"\s+", " ", t).strip()


def atribui(df: pd.DataFrame, col_nome: str = "instituicao",
            col_tcb: str = "tcb") -> pd.Series:
    """Rotulo do sistema de cada linha, ou string vazia quando nao ha marca.

    Devolve uma Series alinhada ao indice de `df`. Nao altera `df`.
    """
    if col_nome not in df.columns:
        return pd.Series(SEM_GRUPO, index=df.index, dtype="object")

    nomes = df[col_nome].map(normaliza)
    saida = pd.Series(SEM_GRUPO, index=df.index, dtype="object")

    if col_tcb in df.columns:
        elegivel = df[col_tcb].isin(TCB_COOPERATIVO)
    else:                                     # base sem TCB: nao arrisca
        elegivel = pd.Series(False, index=df.index)

    for rotulo, padrao in MARCAS:
        alvo = elegivel & (saida == SEM_GRUPO) & nomes.str.contains(padrao, regex=True)
        saida.loc[alvo] = rotulo
    return saida


def chave_linha(grupo: object, cod_inst: object) -> str:
    """Chave de colapso: o sistema quando ha, senao a propria instituicao."""
    g = str(grupo or "")
    return g if g else f"#{cod_inst}"


# Trimestres andam de 3 em 3 meses no formato AAAAMM: 202603 - 100 = 202503.
UM_ANO = 100


def agrega(membros: pd.DataFrame, hist: pd.DataFrame | None = None) -> dict:
    """Razoes DO CONJUNTO de singulares sinalizadas: soma o numerador e o denominador.

    Este e o unico agregado que a linha de sistema exibe, e a distincao importa:
    media das razoes dos membros nao e a razao do conjunto, mas Sigma(numerador) /
    Sigma(denominador) e -- e e assim que se calcula numero de sistema.

    O que NAO sai daqui, e por que:

    Basileia. Os dados existem (PR e RWA), e somados dariam 16,21% para a Cresol em
    03/2026. Mas capital de cooperativas juridicamente independentes NAO e fungivel:
    nenhuma pode usar o capital da outra, cada uma responde pelo proprio requisito.
    Sigma(PR)/Sigma(RWA) nao e o indice de ninguem. Fica vazio por razao de conteudo,
    nao por falta de dado.

    Regras de ausencia, todas no mesmo espirito -- se o conjunto medido nao e o
    conjunto anunciado na linha, o campo fica vazio:
      * crescimento exige TODOS os membros presentes tambem quatro trimestres antes;
        faltando um, a soma de hoje e a de ontem descrevem conjuntos diferentes;
      * inadimplencia e cobertura exigem o numerador em TODOS os membros: um ausente
        encolhe so o numerador e puxa a razao para baixo;
      * crescimento tambem respeita a mascara da Res. 4.966 -- se o trimestre esta
        contaminado, o indicador individual e nulo e o agregado nao pode valer mais
        que ele.
    """
    saida: dict[str, float | None] = {
        "agg_cresc": None, "agg_inadimplencia": None, "agg_cobertura": None}
    if membros.empty:
        return saida

    carteira = membros["carteira_credito_real"].sum()

    # ---- inadimplencia e cobertura do conjunto
    if "inadimplencia_valor_real" in membros.columns:
        atraso = membros["inadimplencia_valor_real"]
        if atraso.notna().all() and carteira > 0:
            saida["agg_inadimplencia"] = float(atraso.sum() / carteira)
            prov = membros.get("provisao_credito_real")
            if prov is not None and prov.notna().all() and atraso.sum() > 0:
                saida["agg_cobertura"] = float(prov.sum() / atraso.sum())

    # ---- crescimento real anual do conjunto
    contaminado = ("p1_1_cresc_real_aa" in membros.columns
                   and not membros["p1_1_cresc_real_aa"].notna().any())
    if hist is not None and not contaminado and "data_base" in membros.columns:
        dt = int(membros["data_base"].iloc[0])
        antes = hist[(hist["data_base"] == dt - UM_ANO)
                     & (hist["cod_inst"].isin(membros["cod_inst"]))]
        completo = set(membros["cod_inst"]) == set(antes["cod_inst"])
        base = antes["carteira_credito_real"].sum()
        if completo and base > 0:
            saida["agg_cresc"] = float(carteira / base - 1)
    return saida


def conta_sinalizadas(membros: pd.DataFrame, eixo: str) -> tuple[int, int]:
    """Quantos membros estao com semaforo alto no eixo, de quantos ao todo.

    Semaforo e categoria, nao razao: nao ha o que somar. Mas contar nao inventa nada,
    e e a contagem que diz ONDE o sistema esta pressionado -- a Cresol tinha 8 de 11
    em crescimento e 0 de 11 em concentracao em 03/2026.
    """
    col = f"sem_{eixo}"
    if col not in membros.columns:
        return 0, len(membros)
    return int((membros[col] == "alto").sum()), len(membros)


def colapsa(lista: pd.DataFrame, univ: pd.DataFrame | None = None,
            minimo: int = MINIMO_PARA_AGRUPAR,
            col_grupo: str = "grupo",
            hist: pd.DataFrame | None = None) -> pd.DataFrame:
    """Uma linha por sistema no lugar das singulares dele; as demais, intactas.

    `lista` e a agenda ja ordenada. `univ` e o recorte inteiro do trimestre, usado
    so para contar quantas singulares do sistema existem no recorte -- e o
    denominador do "11 de 13" que da sentido ao numero.

    `hist` e o painel inteiro, usado so para buscar a carteira de quatro trimestres
    antes no crescimento do conjunto.

    A linha de sistema herda a linha da singular de MAIOR score (a representante),
    para os campos de identificacao. Nenhum campo que e razao e HERDADO dela -- seria
    o numero de uma cooperativa apresentado como o do sistema. Crescimento,
    inadimplencia e cobertura sao RECALCULADOS somando numerador e denominador do
    conjunto (ver `agrega`); Basileia fica vazia porque capital de instituicoes
    independentes nao se soma.

    Colunas acrescentadas:
      linha_tipo        "sistema" ou "instituicao"
      rotulo            o que vai na coluna Instituicao
      n_sinalizadas     membros do sistema NESTA lista
      n_recorte         membros do sistema no recorte do trimestre
      carteira_grupo    soma da carteira das SINALIZADAS -- e o que a linha
                        representa, e soma de niveis (aditivo, rastreavel)
      carteira_recorte  soma da carteira do sistema inteiro no recorte, para o
                        detalhamento
      agg_cresc         crescimento real anual do conjunto sinalizado
      agg_inadimplencia atraso 90+ somado sobre carteira somada
      agg_cobertura     provisao somada sobre atraso somado
      n_alto_<eixo>     quantos membros com semaforo alto em cada eixo
    """
    EIXOS_SEM = ("crescimento", "concentracao", "deterioracao")
    if lista.empty:
        vazio = lista.copy()
        for c, v in (("linha_tipo", "instituicao"), ("rotulo", ""),
                     ("n_sinalizadas", 0), ("n_recorte", 0),
                     ("carteira_grupo", 0.0), ("carteira_recorte", 0.0),
                     ("agg_cresc", None), ("agg_inadimplencia", None),
                     ("agg_cobertura", None)):
            vazio[c] = v
        for e in EIXOS_SEM:
            vazio[f"n_alto_{e}"] = 0
        return vazio

    d = lista.copy()
    if col_grupo not in d.columns:
        d[col_grupo] = SEM_GRUPO
    d[col_grupo] = d[col_grupo].fillna(SEM_GRUPO)
    d["_chave"] = [chave_linha(g, c) for g, c in zip(d[col_grupo], d["cod_inst"])]

    n_por_chave = d["_chave"].value_counts()
    colapsavel = (d[col_grupo] != SEM_GRUPO) & (d["_chave"].map(n_por_chave) >= minimo)

    # denominador e carteira do sistema vem do RECORTE, nao da lista sinalizada
    base = univ if univ is not None and not univ.empty else d
    if col_grupo not in base.columns:
        base = base.assign(**{col_grupo: atribui(base)})
    por_sistema = base[base[col_grupo] != SEM_GRUPO].groupby(col_grupo).agg(
        n_recorte=("cod_inst", "nunique"),
        carteira_recorte=("carteira_credito_real", "sum"))

    solo = d[~colapsavel].copy()
    solo["linha_tipo"] = "instituicao"
    solo["rotulo"] = solo["instituicao"]
    solo["n_sinalizadas"] = 1
    solo["n_recorte"] = 1
    solo["carteira_grupo"] = solo["carteira_credito_real"]
    solo["carteira_recorte"] = solo["carteira_credito_real"]
    for c in ("agg_cresc", "agg_inadimplencia", "agg_cobertura"):
        solo[c] = None
    for e in EIXOS_SEM:
        solo[f"n_alto_{e}"] = 0

    juntas = d[colapsavel]
    representantes = (juntas.sort_values("score_final", ascending=False)
                            .drop_duplicates(col_grupo).copy())
    representantes["linha_tipo"] = "sistema"
    representantes["n_sinalizadas"] = representantes[col_grupo].map(
        juntas[col_grupo].value_counts()).astype(int)
    representantes["n_recorte"] = representantes[col_grupo].map(
        por_sistema["n_recorte"]).fillna(representantes["n_sinalizadas"]).astype(int)
    representantes["carteira_grupo"] = representantes[col_grupo].map(
        juntas.groupby(col_grupo)["carteira_credito_real"].sum())
    representantes["carteira_recorte"] = representantes[col_grupo].map(
        por_sistema["carteira_recorte"]).fillna(representantes["carteira_grupo"])
    representantes["rotulo"] = [
        f"SISTEMA {str(g).upper()} · {n} de {tot} sinalizadas"
        for g, n, tot in zip(representantes[col_grupo],
                             representantes["n_sinalizadas"],
                             representantes["n_recorte"])]

    # razoes DO CONJUNTO, recalculadas -- nunca herdadas da representante
    for col in ("agg_cresc", "agg_inadimplencia", "agg_cobertura"):
        representantes[col] = None
    for e in EIXOS_SEM:
        representantes[f"n_alto_{e}"] = 0
    for rotulo_sis in representantes[col_grupo]:
        membros_sis = juntas[juntas[col_grupo] == rotulo_sis]
        onde = representantes[col_grupo] == rotulo_sis
        for col, val in agrega(membros_sis, hist).items():
            representantes.loc[onde, col] = val
        for e in EIXOS_SEM:
            representantes.loc[onde, f"n_alto_{e}"] = conta_sinalizadas(membros_sis, e)[0]

    saida = (pd.concat([solo, representantes], ignore_index=True)
               .sort_values("score_final", ascending=False)
               .drop(columns=["_chave"]))
    saida["posicao"] = range(1, len(saida) + 1)
    return saida


def membros(lista: pd.DataFrame, rotulo: str,
            col_grupo: str = "grupo") -> pd.DataFrame:
    """As linhas de `lista` que pertencem ao sistema `rotulo`, da pior para a melhor."""
    if col_grupo not in lista.columns:
        return lista.iloc[0:0]
    return lista[lista[col_grupo] == rotulo].sort_values("score_final", ascending=False)


def cobertura(df: pd.DataFrame, col_grupo: str = "grupo") -> pd.DataFrame:
    """Quantas cooperativas distintas cada sistema reune -- artefato de auditoria.

    Conta cada cooperativa UMA vez, pelo rotulo do trimestre mais recente em que
    ela aparece. Somar por trimestre contaria duas vezes as sete que trocaram de
    sistema no periodo (ver `migracoes`), e o total nao fecharia com o numero de
    cooperativas da base.
    """
    d = df.copy()
    if col_grupo not in d.columns:
        d[col_grupo] = atribui(d)
    coop = d[d["tcb"].isin(TCB_COOPERATIVO)] if "tcb" in d.columns else d
    ultimo = coop.sort_values("data_base").drop_duplicates("cod_inst", keep="last")
    tab = (ultimo.groupby(col_grupo)["cod_inst"].nunique()
                 .rename("cooperativas").reset_index()
                 .sort_values("cooperativas", ascending=False))
    tab[col_grupo] = tab[col_grupo].replace(SEM_GRUPO, "(sem marca no nome)")
    return tab


def migracoes(df: pd.DataFrame, col_grupo: str = "grupo") -> pd.DataFrame:
    """Cooperativas cujo rotulo muda ao longo da serie.

    NAO e defeito da regra: sao trocas de filiacao de verdade, e o proprio IF.data
    as registra renomeando a instituicao -- "SICREDI CREDUNI" vira "SICOOB
    CREDUNI", "UNIPRIME OESTE PAULISTA" vira "SICOOB UNISP". O rotulo segue o nome
    do trimestre, que e a leitura correta para uma agenda trimestral.

    O que importa vigiar e o TAMANHO: se uma migrante entrasse no recorte, ela
    apareceria sob dois sistemas em trimestres diferentes sem explicacao na tela.
    E o que `checa_grupos.py` verifica.
    """
    d = df.copy()
    if col_grupo not in d.columns:
        d[col_grupo] = atribui(d)
    d = d[d[col_grupo] != SEM_GRUPO]
    n = d.groupby("cod_inst")[col_grupo].nunique()
    alvo = n[n > 1].index
    if not len(alvo):
        return d.iloc[0:0][["cod_inst", "instituicao", col_grupo]]
    m = d[d["cod_inst"].isin(alvo)].sort_values(["cod_inst", "data_base"])
    troca = m[col_grupo].ne(m.groupby("cod_inst")[col_grupo].shift())
    return m[troca][["cod_inst", "data_base", "instituicao", col_grupo,
                     "carteira_credito_real"]]
