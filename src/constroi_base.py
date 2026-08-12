"""
constroi_base.py -- transforma data_raw/ifdata em um painel trimestral por instituicao,
ja deflacionado, pronto para o calculo dos 18 indicadores.

Saidas em data_processed/:
  dicionario_campos_ifdata.csv  dicionario completo (todo periodo x tipo x relatorio x coluna,
                                com formula COSIF e chave de juncao)
  painel_ifdata.parquet         painel largo: uma linha por (data_base, instituicao)
  painel_ifdata_amostra.csv     amostra legivel para conferencia manual

REGIME CONTABIL -- o painel cobre os dois lados da Res. CMN 4.966/2021:
  ate 202412 : provisao = "Provisao sobre Operacoes de Credito" (COSIF 16900008)
               qualidade = carteira por nivel de risco AA..H
  de 202503  : provisao = "Perda Esperada" (ECL)
               qualidade = "Inadimplencia" e "Ativos problematicos" (valores em R$)
A coluna `regime_contabil` marca cada linha. As duas metodologias NAO sao encadeadas
numa serie unica -- ver verificacao/00_fontes_confirmadas.md, secao 3.
"""
from __future__ import annotations

import re
import unicodedata

import pandas as pd

from coleta_ifdata import RAW, monta_dicionario
from comum import DATA_PROC, agora_utc, carrega_json

TIPO_ATE_2024 = 1005   # Conglomerados Financeiros e Instituicoes Independentes
TIPO_DE_2025 = 1009    # Conglomerados Prudenciais e Instituicoes Independentes
CORTE_REGIME = 202503  # primeira data-base sob Res. 4.966

# (relatorio, coluna no IF.data) -> nome curto no painel.
# O casamento e por nome NORMALIZADO (sem acento, sem "(d1)", sem quebra de linha).
CAMPOS = {
    "Resumo": {
        "ativo total": "ativo_total",
        # o nome muda com a Res. 4.966: ate 202412 "Carteira de Credito Classificada",
        # de 202503 em diante "Carteira de Credito". Sao a mesma coluna do relatorio Resumo.
        "carteira de credito classificada|carteira de credito": "carteira_credito",
        "captacoes": "captacoes",
        "patrimonio liquido": "patrimonio_liquido",
        "lucro liquido": "lucro_liquido",
        "numero de agencias": "n_agencias",
    },
    "Informações de Capital": {
        "patrimonio de referencia para comparacao com o rwa": "pr",
        "ativos ponderados pelo risco (rwa)": "rwa",
        "indice de basileia": "indice_basileia",
        "indice de capital principal": "indice_capital_principal",
        "razao de alavancagem": "razao_alavancagem",
    },
    "Ativo": {
        # regime antigo (ate 202412)
        "operacoes de credito (d1)": "credito_bruto_antigo",
        "provisao sobre operacoes de credito (d2)": "provisao_antiga",
        # regime novo (2025+)
        "valor contabil bruto (e1)": "credito_bruto_novo",
        "perda esperada (e2)": "perda_esperada",
    },
    "Carteira de crédito ativa - por carteiras de instrumentos financeiros": {
        "total geral": "carteira_ativa_total",
        "inadimplencia": "inadimplencia_valor",
        "ativos problematicos": "ativos_problematicos_valor",
    },
    "Carteira de crédito ativa - por nível de risco da operação": {
        "total geral": "risco_total_geral",
        "e": "risco_e", "f": "risco_f", "g": "risco_g", "h": "risco_h",
        "d": "risco_d", "c": "risco_c",
    },
    "Carteira de crédito ativa Pessoa Física - modalidade e prazo de vencimento": {
        "total da carteira de pessoa fisica": "pf_total",
        "cartao de credito": "pf_cartao",
        "emprestimo sem consignacao em folha": "pf_sem_consignacao",
        "emprestimo com consignacao em folha": "pf_consignado",
        "veiculos": "pf_veiculos",
        "habitacao": "pf_habitacao",
        "rural e agroindustrial": "pf_rural",
        "outros creditos": "pf_outros",
    },
    "Carteira de crédito ativa Pessoa Jurídica - modalidade e prazo de vencimento": {
        "total da carteira de pessoa juridica": "pj_total",
        "capital de giro": "pj_capital_giro",
        "cheque especial e conta garantida": "pj_cheque_especial",
    },
    # P2 nº 5 -- exposicao a tomadores de grande porte, com FONTE DIRETA por instituicao.
    # Substitui a proxy de ticket medio (carteira / nº de clientes), que nao media
    # exposicao a grandes tomadores. O denominador vem do PROPRIO relatorio, para nao
    # misturar recortes.
    "Carteira de crédito ativa Pessoa Jurídica - por porte do tomador": {
        "total da carteira de pessoa juridica": "pj_total_porte",
        "micro": "pj_porte_micro",
        "pequena": "pj_porte_pequena",
        "media": "pj_porte_media",
        "grande": "pj_porte_grande",
    },
    "Carteira de crédito ativa - por região geográfica": {
        "total geral": "reg_total",
        "sudeste": "reg_sudeste", "sul": "reg_sul", "nordeste": "reg_nordeste",
        "norte": "reg_norte", "centro-oeste": "reg_centro_oeste",
    },
    "Carteira de crédito ativa - quantidade de clientes e de operações": {
        "quantidade de clientes com operacoes ativas": "qtd_clientes",
        "quantidade de operacoes ativas": "qtd_operacoes",
    },
}


def normaliza(s: str) -> str:
    """'Provisão sobre Operações de Crédito \\n(d2)' -> 'provisao sobre operacoes de credito (d2)'"""
    s = (s or "").replace("\n", " ")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    s = re.sub(r"\s*=.*$", "", s)          # corta " = (a) + (b)"
    s = re.sub(r"\s+", " ", s).strip().lower()
    return s


def sem_rotulo(s: str) -> str:
    """Remove o rotulo de composicao no fim do nome: 'indice de basileia (n)' -> 'indice de basileia'.

    NAO se usa como chave primaria porque no relatorio "Ativo" o rotulo e o UNICO
    diferenciador entre 'operacoes de credito (d1)' (bruto) e 'operacoes de credito (d)'
    (liquido de provisao). Por isso o casamento tenta primeiro o nome COM rotulo.
    """
    return re.sub(r"\s*\([a-z]{1,2}\d?\)\s*$", "", normaliza(s)).strip()


INICIO_1009 = 202309  # primeira data-base em que o tipo 1009 e publicado

# Dois universos, por uma razao concreta:
#  "longo"      -- serie longa de crescimento (P1). Usa 1005 ate 202412 e 1009 de 202503,
#                  porque os relatorios de credito mudam de tipo com a Res. 4.966.
#                  NAO tem Informacoes de Capital antes de 2025 (o relatorio so existe em 1009).
#  "prudencial" -- 1009 do inicio ao fim (202309+). Universo homogeneo, com capital
#                  (PR, RWA, Basileia) em toda a janela. E o universo da AGENDA de supervisao.
UNIVERSOS = {
    "longo": {"tipo": None, "de": None},
    "prudencial": {"tipo": TIPO_DE_2025, "de": INICIO_1009},
}


def tipo_do_periodo(dt: int) -> int:
    return TIPO_DE_2025 if dt >= CORTE_REGIME else TIPO_ATE_2024


def periodos_disponiveis() -> list[int]:
    return sorted(int(p.name) for p in RAW.iterdir()
                  if p.is_dir() and re.fullmatch(r"\d{6}", p.name))


def extrai_periodo(dt: int, tipo: int | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Devolve (painel largo do trimestre, dicionario do trimestre).

    Campos do mapa CAMPOS que nao existirem no trimestre ficam registrados em
    `extrai_periodo.ausentes` -- ausencia e informacao (regime contabil, relatorio
    descontinuado), nao erro, e precisa aparecer no relatorio de cobertura.
    """
    tipo = tipo if tipo is not None else tipo_do_periodo(dt)
    pasta = RAW / str(dt)
    dic = monta_dicionario(dt, tipo)
    if dic.empty:
        return pd.DataFrame(), dic

    cad_path = pasta / f"cadastro{dt}_{tipo}.json"
    if not cad_path.exists():
        return pd.DataFrame(), dic
    cad = pd.DataFrame(carrega_json(cad_path)).rename(columns={
        "c0": "cod_inst", "c2": "instituicao", "c3": "tcb", "c7": "controle",
        "c10": "uf", "c11": "municipio", "c12": "segmento_sr",
    })
    cols_cad = [c for c in ["cod_inst", "instituicao", "tcb", "controle",
                            "uf", "municipio", "segmento_sr"] if c in cad.columns]
    cad = cad[cols_cad].drop_duplicates("cod_inst").reset_index(drop=True)

    # valores esparsos {(cod_inst, lid): valor}
    valores: dict[tuple[str, int], float] = {}
    for dados_path in sorted(pasta.glob(f"dados{dt}_*.json.gz")):
        for ent in carrega_json(dados_path).get("values", []):
            cod = str(ent.get("e"))
            for item in ent.get("v", []):
                valores[(cod, item["i"])] = item["v"]

    # coluna do painel -> lid deste trimestre
    dic = dic.assign(_norm=dic["coluna_nome"].map(normaliza),
                     _sem=dic["coluna_nome"].map(sem_rotulo))
    lid_por_campo: dict[str, int] = {}
    nao_encontrados: list[str] = []
    for relatorio, mapa in CAMPOS.items():
        sub = dic[dic["relatorio"].str.strip() == relatorio]
        if sub.empty:
            continue
        for chave, curto in mapa.items():
            achou = pd.DataFrame()
            for nome_norm in chave.split("|"):          # aliases entre regimes contabeis
                # 1) nome exato COM rotulo; 2) fallback sem rotulo (ex.: "indice de basileia (n)")
                achou = sub[sub["_norm"] == nome_norm]
                if achou.empty:
                    achou = sub[sub["_sem"] == sem_rotulo(nome_norm)]
                if not achou.empty:
                    break
            if achou.empty:
                nao_encontrados.append(f"{relatorio} :: {chave}")
                continue

            linha = achou.iloc[0]
            # Colunas-pai nao carregam valor: o saldo mora numa sub-coluna. Ha dois padroes:
            #  (a) relatorios de modalidade ate 202412 -- filha chamada "Total" (as irmas sao
            #      as faixas de vencimento);
            #  (b) Informacoes de Capital -- filha com o MESMO nome do pai, distinguida so
            #      pelo rotulo. Ex.: pai "Patrimonio de Referencia para Comparacao com o RWA"
            #      -> filha "... (e)"; pai "Ativos Ponderados pelo Risco (RWA)" -> filha "(j)".
            filhas = sub[sub["coluna_pai"] == linha["coluna_nome"]]
            if not filhas.empty:
                mesma = filhas[filhas["_sem"] == sem_rotulo(linha["coluna_nome"])]
                total = filhas[filhas["_norm"] == "total"]
                if not mesma.empty:
                    linha = mesma.iloc[0]
                elif not total.empty:
                    linha = total.iloc[0]

            if pd.notna(linha["chave_dados_lid"]):
                lid_por_campo[curto] = int(linha["chave_dados_lid"])
    if nao_encontrados:
        extrai_periodo.ausentes[dt] = nao_encontrados  # type: ignore[attr-defined]

    painel = cad.copy()
    for curto, lid in lid_por_campo.items():
        painel[curto] = [valores.get((str(c), lid)) for c in painel["cod_inst"]]

    painel.insert(0, "data_base", dt)
    painel["regime_contabil"] = "Res. 4.966 (ECL)" if dt >= CORTE_REGIME else "AA-H (Res. 2.682)"
    painel["tipo_instituicao"] = tipo
    return painel, dic


extrai_periodo.ausentes = {}  # type: ignore[attr-defined]


def deflaciona(painel: pd.DataFrame) -> tuple[pd.DataFrame, int, list[str]]:
    """Aplica o deflator IPCA (Tarefa 4). So colunas MONETARIAS ganham par '_real'."""
    defl = pd.read_csv(DATA_PROC / "deflator_ipca.csv")
    fator = dict(zip(defl["mes"], defl["fator_para_base"]))
    base_indice = int(defl["base_do_indice"].iloc[0])
    painel["fator_deflator"] = painel["data_base"].map(fator)

    faltando = painel[painel["fator_deflator"].isna()]["data_base"].unique()
    if len(faltando):
        print(f"  ATENCAO: sem deflator para {sorted(faltando)} -- valores reais ficarao vazios")

    nao_monetarios = {
        "indice_basileia", "indice_capital_principal", "razao_alavancagem",
        "qtd_clientes", "qtd_operacoes", "n_agencias", "fator_deflator",
        "data_base", "tipo_instituicao",
    }
    monetarios = [c for c in painel.columns
                  if painel[c].dtype.kind in "fi" and c not in nao_monetarios]
    for c in monetarios:
        painel[f"{c}_real"] = painel[c] * painel["fator_deflator"]
    painel["base_deflator"] = base_indice
    return painel, base_indice, monetarios


def constroi_universo(nome: str, cfg: dict, periodos: list[int]) -> list[pd.DataFrame]:
    """Monta um universo (ver UNIVERSOS) e grava data_processed/painel_ifdata_{nome}.parquet."""
    print(f"\n--- universo '{nome}' "
          f"(tipo {cfg['tipo'] or 'misto 1005/1009'}, de {cfg['de'] or periodos[0]}) ---")
    paineis, dicionarios = [], []
    for dt in periodos:
        if cfg["de"] and dt < cfg["de"]:
            continue
        p, d = extrai_periodo(dt, cfg["tipo"])
        if not d.empty:
            dicionarios.append(d)
        if p.empty:
            print(f"  {dt}: SEM DADOS")
            continue
        paineis.append(p)
        print(f"  {dt}: {len(p):>5} instituicoes | "
              f"{sum(p[c].notna().any() for c in p.columns)} campos preenchidos")

    if not paineis:
        return dicionarios

    painel = pd.concat(paineis, ignore_index=True)
    painel, base_indice, monetarios = deflaciona(painel)
    painel.to_parquet(DATA_PROC / f"painel_ifdata_{nome}.parquet", index=False)
    (painel.sort_values(["data_base", "carteira_credito"], ascending=[False, False])
           .groupby("data_base").head(15)
           .to_csv(DATA_PROC / f"painel_ifdata_{nome}_amostra.csv",
                   index=False, encoding="utf-8-sig"))
    print(f"  => {len(painel):,} linhas x {len(painel.columns)} colunas | "
          f"{painel['cod_inst'].nunique():,} instituicoes | "
          f"{len(monetarios)} colunas deflacionadas (R$ de {base_indice})")
    return dicionarios


def main() -> None:
    print(f"[{agora_utc()}] construindo base processada")
    periodos = periodos_disponiveis()
    print(f"  periodos em data_raw: {len(periodos)} ({periodos[0]}..{periodos[-1]})")
    DATA_PROC.mkdir(parents=True, exist_ok=True)

    dicionarios: list[pd.DataFrame] = []
    for nome, cfg in UNIVERSOS.items():
        dicionarios += constroi_universo(nome, cfg, periodos)

    if dicionarios:
        dic = (pd.concat(dicionarios, ignore_index=True)
                 .drop(columns=["_norm", "_sem"], errors="ignore")
                 .drop_duplicates())
        dic.to_csv(DATA_PROC / "dicionario_campos_ifdata.csv", index=False, encoding="utf-8-sig")
        print(f"\n  dicionario de campos: {len(dic):,} linhas "
              f"({dic['relatorio'].nunique()} relatorios distintos)")

    ausentes = extrai_periodo.ausentes  # type: ignore[attr-defined]
    if ausentes:
        # um campo so e "problema" se faltar em TODOS os trimestres do regime em que deveria existir
        from collections import Counter
        contagem = Counter(c for lista in ausentes.values() for c in lista)
        print(f"\n  campos ausentes por trimestre (esperado quando o relatorio muda de regime):")
        for campo, n in contagem.most_common():
            print(f"    {n:>2}/{len(periodos)} trimestres sem: {campo}")


if __name__ == "__main__":
    main()
