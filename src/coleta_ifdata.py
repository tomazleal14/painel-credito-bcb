"""
coleta_ifdata.py -- coleta rastreavel do IF.data (BCB), base trimestral por instituicao.

ENDPOINTS OFICIAIS (os mesmos que a interface publica https://www3.bcb.gov.br/ifdata/ usa;
confirmados por inspecao de rede em 12/08/2026, ver verificacao/00_fontes_confirmadas.md):

  indice de periodos  GET /ifdata/rest/relatorios2000a2024
                      GET /ifdata/rest/relatorios2025a2030
  arquivo             GET /ifdata/rest/arquivos?nomeArquivo={caminho}

ESTRUTURA DOS ARQUIVOS (engenharia reversa documentada):
  info{AAAAMM}.json          dicionario de campos:
                             {id, n=nome PT, ni=nome EN, d=FORMULA COSIF, lid=chave nos dados, ty}
  trel{AAAAMM}_{id}.json     definicao do relatorio: .n=nome, .s[].id=tipo de instituicao,
                             .c[].ifd=id de coluna (-> info.id), .cp=legenda/unidade, .ge=data de geracao
  cadastro{AAAAMM}_{tipo}.json  cadastro das IFs: c0=codigo, c2=nome, c3=TCB, c10=UF,
                             c11=municipio, c12=segmento SR, c7=controle
  dados{AAAAMM}_{n}.json     valores esparsos: {id, values:[{e=codigo da IF, v:[{i=info.lid, v=valor}]}]}

UNIDADES (confirmado contra a tela do IF.data em 12/08/2026):
  - valores monetarios no JSON bruto estao em R$ (UNIDADES); a interface divide por 1.000
    para exibir "R$ mil". Ex.: ITAU-PRUDENCIAL 202603 Carteira de Credito =
    1.221.119.970.501,64 no bruto  ->  1.221.119.971 (R$ mil) na tela.
  - indices (Basileia, imobilizacao) vem como FRACAO decimal (0,147697 -> 14,77%).

TIPOS DE INSTITUICAO:
  1005 Conglomerados Financeiros e Instituicoes Independentes  (desde 200001)
  1006 Instituicoes Individuais                                (desde 200001)
  1009 Conglomerados Prudenciais e Instituicoes Independentes  (desde 202309)

Este projeto usa 1005 como universo primario: e o unico com serie longa E com os
relatorios detalhados de carteira de credito (modalidade, regiao, nivel de risco).
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import quote

import pandas as pd

from comum import DATA_PROC, DATA_RAW, baixa, carrega_json, registra, agora_utc

BASE = "https://www3.bcb.gov.br/ifdata/rest"
INDICES = ["relatorios2000a2024", "relatorios2025a2030"]
RAW = DATA_RAW / "ifdata"

TIPO_PADRAO = 1005
TIPOS = {
    1005: "Conglomerados Financeiros e Instituicoes Independentes",
    1006: "Instituicoes Individuais",
    1009: "Conglomerados Prudenciais e Instituicoes Independentes",
}

# relatorios que alimentam os 18 indicadores (casados por NOME, pois o id do trel muda a cada periodo)
RELATORIOS_ALVO = [
    "Resumo",
    "Informações de Capital",
    "Carteira de crédito ativa Pessoa Física - modalidade e prazo de vencimento",
    "Carteira de crédito ativa Pessoa Jurídica - modalidade e prazo de vencimento",
    "Carteira de crédito ativa - por região geográfica",
    "Carteira de crédito ativa - por nível de risco da operação",
    "Carteira de crédito ativa - quantidade de clientes e de operações",
    "Carteira de crédito ativa Pessoa Jurídica -  por atividade econômica (CNAE)",
    "Carteira de crédito ativa Pessoa Jurídica - por porte do tomador",
    "Carteira de crédito ativa - por carteiras de instrumentos financeiros",
    "Passivo",
]


def url_arquivo(nome: str) -> str:
    return f"{BASE}/arquivos?nomeArquivo={quote(nome, safe='')}"


def baixa_indices() -> list[dict]:
    """Baixa os dois indices de periodos e devolve a lista unificada."""
    periodos: list[dict] = []
    for idx in INDICES:
        url = f"{BASE}/{idx}"
        destino = RAW / "indice" / f"{idx}.json"
        conteudo = baixa(url, destino, fonte="BCB/IF.data",
                         observacao="indice de periodos e arquivos publicados")
        periodos.extend(json.loads(conteudo.decode("utf-8")))
    periodos.sort(key=lambda d: d["dt"])
    return periodos


def coleta_periodo(p: dict, tipo: int) -> None:
    """Baixa info + cadastro + dados + trel de um trimestre."""
    dt = p["dt"]
    arquivos = [f["f"] for f in p.get("files", [])]
    pasta = RAW / str(dt)

    for nome in arquivos:
        base_nome = nome.split("/")[-1]
        eh_cadastro = base_nome.startswith("cadastro")
        eh_trel = base_nome.startswith("trel")
        # cadastro: so o tipo de instituicao escolhido
        if eh_cadastro and not base_nome.endswith(f"_{tipo}.json"):
            continue
        # ignorar arquivos que nao usamos
        if base_nome.startswith(("filtro",)):
            continue
        # dados sao grandes -> guardar comprimido (sha256 do original preservado)
        comprimir = base_nome.startswith("dados")
        try:
            baixa(url_arquivo(nome), pasta / base_nome, fonte="BCB/IF.data",
                  comprimir=comprimir,
                  observacao=f"IF.data data-base {dt}" + (f" tipo {tipo}" if eh_cadastro else ""))
        except Exception as e:  # noqa: BLE001
            print(f"  ! falha em {base_nome}: {e}")

    print(f"  {dt}: {len(arquivos)} arquivos processados")


def monta_dicionario(dt: int, tipo: int) -> pd.DataFrame:
    """Dicionario de campos do trimestre: relatorio -> coluna -> formula COSIF -> chave nos dados.

    As colunas do IF.data sao HIERARQUICAS: `trel.c[]` traz as colunas de primeiro nivel e
    cada uma pode ter sub-colunas em `sc[]` (o recurso "Composicao de Colunas" da interface).
    Campos essenciais para P3 -- como "Provisao sobre Operacoes de Credito" (COSIF 16900008),
    sob "Operacoes de Credito" -- so aparecem nesse segundo nivel, por isso a descida e
    recursiva. Ignorar `sc` faz o dicionario perder as provisoes e os prazos de vencimento.
    """
    pasta = RAW / str(dt)
    info = {i["id"]: i for i in carrega_json(pasta / f"info{dt}.json")}
    linhas: list[dict] = []

    def desce(colunas: list[dict], trel: dict, nivel: int = 0, pai: str = "") -> None:
        for ordem, col in enumerate(colunas):
            meta = info.get(col.get("ifd"), {})
            nome = meta.get("n", "")
            linhas.append({
                "data_base": dt,
                "tipo_instituicao": tipo,
                "relatorio": trel.get("n", ""),
                "trel_id": trel.get("id"),
                "relatorio_gerado_em": trel.get("ge", ""),
                "legenda_unidade": (trel.get("cp") or "").replace("<br />", " ").strip(),
                "nivel": nivel,
                "coluna_pai": pai,
                "ordem_coluna": ordem,
                "coluna_id": col.get("ifd"),
                "coluna_nome": nome,
                "coluna_nome_en": meta.get("ni", ""),
                "formula_cosif": meta.get("d", ""),
                "chave_dados_lid": meta.get("lid"),
                "tipo_valor": meta.get("ty"),
            })
            if col.get("sc"):
                desce(col["sc"], trel, nivel + 1, nome)

    for trel_path in sorted(pasta.glob(f"trel{dt}_*.json")):
        trel = carrega_json(trel_path)
        if tipo not in [s["id"] for s in trel.get("s", [])]:
            continue
        desce(trel.get("c", []), trel)

    return pd.DataFrame(linhas)


def extrai_valores(dt: int, tipo: int) -> pd.DataFrame:
    """Junta cadastro + dados + dicionario num painel longo (uma linha por IF x coluna)."""
    pasta = RAW / str(dt)
    dic = monta_dicionario(dt, tipo)
    if dic.empty:
        return pd.DataFrame()

    # cadastro das instituicoes
    cad_path = pasta / f"cadastro{dt}_{tipo}.json"
    if not cad_path.exists():
        return pd.DataFrame()
    cad = pd.DataFrame(carrega_json(cad_path))
    cad = cad.rename(columns={
        "c0": "cod_inst", "c2": "instituicao", "c3": "tcb", "c5": "td_desc",
        "c7": "controle", "c10": "uf", "c11": "municipio", "c12": "segmento_sr",
    })
    cols_cad = [c for c in ["cod_inst", "instituicao", "tcb", "td_desc", "controle",
                            "uf", "municipio", "segmento_sr"] if c in cad.columns]
    cad = cad[cols_cad].drop_duplicates("cod_inst")

    # valores esparsos: lid -> valor, por instituicao
    valores: dict[tuple[str, int], float] = {}
    for dados_path in sorted(pasta.glob(f"dados{dt}_*.json.gz")):
        bloco = carrega_json(dados_path)
        for ent in bloco.get("values", []):
            cod = str(ent.get("e"))
            for item in ent.get("v", []):
                valores[(cod, item["i"])] = item["v"]

    lids = dic.dropna(subset=["chave_dados_lid"])
    registros = []
    for cod in cad["cod_inst"]:
        for row in lids.itertuples():
            v = valores.get((str(cod), int(row.chave_dados_lid)))
            if v is None:
                continue
            registros.append({
                "data_base": dt,
                "cod_inst": cod,
                "relatorio": row.relatorio,
                "coluna_id": row.coluna_id,
                "coluna_nome": row.coluna_nome,
                "valor": v,
            })
    if not registros:
        return pd.DataFrame()
    df = pd.DataFrame(registros).merge(cad, on="cod_inst", how="left")
    return df


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--de", type=int, default=201903, help="data-base inicial AAAAMM")
    ap.add_argument("--ate", type=int, default=202603, help="data-base final AAAAMM")
    ap.add_argument("--tipo", type=int, default=TIPO_PADRAO)
    ap.add_argument("--so-indice", action="store_true")
    args = ap.parse_args()

    print(f"[{agora_utc()}] IF.data -- indice de periodos")
    periodos = baixa_indices()
    sel = [p for p in periodos if args.de <= p["dt"] <= args.ate]
    print(f"  periodos publicados: {len(periodos)} | selecionados: {len(sel)} "
          f"({sel[0]['dt']}..{sel[-1]['dt']})")
    if args.so_indice:
        return

    for p in sel:
        coleta_periodo(p, args.tipo)

    # dicionario de campos consolidado
    dics = [monta_dicionario(p["dt"], args.tipo) for p in sel]
    dics = [d for d in dics if not d.empty]
    if dics:
        dic = pd.concat(dics, ignore_index=True)
        DATA_PROC.mkdir(parents=True, exist_ok=True)
        saida = DATA_PROC / "dicionario_campos_ifdata.csv"
        dic.to_csv(saida, index=False, encoding="utf-8-sig")
        print(f"  dicionario de campos: {len(dic)} colunas-periodo -> {saida.name}")


if __name__ == "__main__":
    main()
