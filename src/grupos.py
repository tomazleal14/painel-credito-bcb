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


def colapsa(lista: pd.DataFrame, univ: pd.DataFrame | None = None,
            minimo: int = MINIMO_PARA_AGRUPAR,
            col_grupo: str = "grupo") -> pd.DataFrame:
    """Uma linha por sistema no lugar das singulares dele; as demais, intactas.

    `lista` e a agenda ja ordenada. `univ` e o recorte inteiro do trimestre, usado
    so para contar quantas singulares do sistema existem no recorte -- e o
    denominador do "11 de 13" que da sentido ao numero.

    A linha de sistema herda a linha da singular de MAIOR score (a representante),
    para os campos de identificacao. Os campos que sao razao -- inadimplencia,
    cobertura, Basileia, crescimento -- NAO sao herdados nem agregados: quem monta
    a tabela le `linha_tipo` e deixa vazio. Media de razao entre instituicoes
    diferentes nao e a razao do conjunto, e aqui campo vazio e preferivel a numero
    inventado.

    Colunas acrescentadas:
      linha_tipo        "sistema" ou "instituicao"
      rotulo            o que vai na coluna Instituicao
      n_sinalizadas     membros do sistema NESTA lista
      n_recorte         membros do sistema no recorte do trimestre
      carteira_grupo    soma da carteira das SINALIZADAS -- e o que a linha
                        representa, e soma de niveis (aditivo, rastreavel)
      carteira_recorte  soma da carteira do sistema inteiro no recorte, para o
                        detalhamento
    """
    if lista.empty:
        vazio = lista.copy()
        for c, v in (("linha_tipo", "instituicao"), ("rotulo", ""),
                     ("n_sinalizadas", 0), ("n_recorte", 0),
                     ("carteira_grupo", 0.0), ("carteira_recorte", 0.0)):
            vazio[c] = v
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
