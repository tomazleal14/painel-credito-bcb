"""
coleta_scr.py -- coleta rastreavel do SCR agregado (BCB), via a API que alimenta o
painel oficial SCR.data (https://www.bcb.gov.br/estabilidadefinanceira/scrdata).

ENDPOINTS OFICIAIS (confirmados por inspecao de rede em 12/08/2026):
  dimensoes  GET /api/servico/sitebcb/sistemainformacaocredito_modalidade
             GET /api/servico/sitebcb/sistemainformacaocredito_porte
             GET /api/servico/sitebcb/sistemainformacaocredito_indexador
             GET /api/servico/sitebcb/sistemainformacaocredito_cnae_ocupacao
  serie      GET /api/servico/sitebcb/sistemainformacaocredito
                 ?dataIn=AAAA-MM-DD&dataFim=AAAA-MM-DD&uf_filtro=&cnaeocup_filtro=
                 &porte_filtro=&modalidade_filtro=&origem_filtro=&indexador_filtro=
                 &cliente_filtro=&subModalidade_filtro=&segmento_filtro=

CAMPOS DEVOLVIDOS
  data_base          fim do mes (AAAA-MM-DD)
  carteira_ativa     R$ (UNIDADES)
  inadimplencia      % da carteira ativa (atraso acima de 90 dias)
  ativo_problematico % da carteira ativa (conceito Res. 4.557: inclui reestruturados
                     e operacoes com indicio de nao recebimento integral)

PAPEL NO PAINEL
  O SCR agregado NAO identifica a instituicao. Ele entra como REFERENCIA DE SISTEMA
  contra a qual as IFs do IF.data sao comparadas (modalidade de alto risco em P2,
  inadimplencia e ativo problematico em P3).
"""
from __future__ import annotations

import json

import pandas as pd

from comum import DATA_PROC, DATA_RAW, agora_utc, baixa

RAW = DATA_RAW / "scr"
BASE = "https://www.bcb.gov.br/api/servico/sitebcb"

DATA_IN = "2015-01-01"
DATA_FIM = "2026-06-30"

# modalidades de ALTO RISCO no sentido da Aula 3 (rotativo / sem garantia real)
MODALIDADES = [
    "Todas",
    "PF - Cartão de crédito",
    "PF - Empréstimo sem consignação em folha",
    "PF - Empréstimo com consignação em folha",
    "PF - Habitacional",
    "PF - Veículos",
    "PJ - Capital de giro",
    "PJ - Cheque especial e conta garantida",
]
CLIENTES = ["Todos", "PF", "PJ"]


def url_serie(modalidade: str = "Todas", cliente: str = "Todos", uf: str = "Todas") -> str:
    return (f"{BASE}/sistemainformacaocredito"
            f"?dataIn={DATA_IN}&dataFim={DATA_FIM}"
            f"&uf_filtro={uf}&cnaeocup_filtro=Todos&porte_filtro=Todos"
            f"&modalidade_filtro={modalidade}&origem_filtro=Todas&indexador_filtro=Todos"
            f"&cliente_filtro={cliente}&subModalidade_filtro=Todas&segmento_filtro=Todos")


def slug(s: str) -> str:
    return (s.replace(" - ", "_").replace(" ", "-").replace("/", "-")
            .replace("ã", "a").replace("ç", "c").replace("é", "e").replace("í", "i")
            .replace("ú", "u").replace("â", "a").replace("õ", "o"))


def coleta() -> pd.DataFrame:
    # dimensoes (dicionario de dominio)
    for dim in ["modalidade", "porte", "indexador", "cnae_ocupacao"]:
        baixa(f"{BASE}/sistemainformacaocredito_{dim}", RAW / f"dominio_{dim}.json",
              fonte="BCB/SCR.data", observacao=f"dominio da dimensao {dim}")

    quadros = []
    for cliente in CLIENTES:
        for modalidade in MODALIDADES:
            # PF/PJ so combinam com modalidades do proprio prefixo
            if modalidade != "Todas" and cliente != "Todos" and not modalidade.startswith(cliente):
                continue
            url = url_serie(modalidade=modalidade, cliente=cliente)
            nome = f"scr_{slug(cliente)}_{slug(modalidade)}.json"
            conteudo = baixa(url, RAW / nome, fonte="BCB/SCR.data",
                             observacao=f"cliente={cliente} | modalidade={modalidade} | "
                                        f"{DATA_IN}..{DATA_FIM}")
            reg = json.loads(conteudo.decode("utf-8")).get("conteudo", [])
            if not reg:
                print(f"  [VAZIO] cliente={cliente} modalidade={modalidade}")
                continue
            df = pd.DataFrame(reg)
            quadros.append(df)
            print(f"  [OK] cliente={cliente:5s} modalidade={modalidade[:45]:45s} {len(df):3d} meses")

    if not quadros:
        return pd.DataFrame()

    scr = pd.concat(quadros, ignore_index=True)
    scr["data_base"] = pd.to_datetime(scr["data_base"])
    scr["mes"] = scr["data_base"].dt.strftime("%Y%m").astype(int)
    DATA_PROC.mkdir(parents=True, exist_ok=True)
    scr.to_parquet(DATA_PROC / "scr_agregado.parquet", index=False)
    print(f"\n  SCR agregado: {len(scr)} linhas | "
          f"{scr['mes'].min()}..{scr['mes'].max()} | "
          f"{scr['modalidade'].nunique()} modalidades")
    return scr


if __name__ == "__main__":
    print(f"[{agora_utc()}] SCR.data -- coleta agregada")
    coleta()
