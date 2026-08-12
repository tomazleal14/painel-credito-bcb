"""
coleta_estban.py -- coleta rastreavel do ESTBAN (Estatistica Bancaria Mensal por
municipio), BCB.

ENDPOINT OFICIAL (capturado do botao "Baixar arquivo" da pagina
https://www.bcb.gov.br/estatisticas/estatisticabancariamunicipios em 12/08/2026):
  GET https://www.bcb.gov.br/content/estatisticas/estatistica_bancaria_estban/municipio/{AAAAMM}_ESTBAN.csv.zip

LIMITE DECLARADO PELA PROPRIA FONTE (texto da pagina oficial):
  "Sua atualizacao e mensal, e abrange os ultimos 6 (seis) meses publicados."
  => o ESTBAN NAO permite montar serie longa por este endpoint. Ele entra no painel
     apenas como CORTE TRANSVERSAL de concentracao regional na data mais recente.
     Qualquer leitura de tendencia regional de longo prazo esta fora do alcance
     desta fonte (ver "O que este painel NAO permite concluir").

ESCOPO DECLARADO: bancos comerciais e bancos multiplos com carteira comercial
(documento 4500). Nao cobre todo o SFN -- por isso NAO e comparavel ao universo
do IF.data sem ressalva.
"""
from __future__ import annotations

import io
import zipfile

import pandas as pd

from comum import DATA_PROC, DATA_RAW, agora_utc, baixa

RAW = DATA_RAW / "estban"
URL = ("https://www.bcb.gov.br/content/estatisticas/estatistica_bancaria_estban/"
       "municipio/{ref}_ESTBAN.csv.zip")

# ultimos meses publicados (a fonte mantem apenas ~6); ajustar conforme disponibilidade
REFERENCIAS = [202603, 202602, 202601, 202512, 202511, 202510]


def coleta() -> pd.DataFrame:
    quadros = []
    for ref in REFERENCIAS:
        url = URL.format(ref=ref)
        try:
            conteudo = baixa(url, RAW / f"{ref}_ESTBAN.csv.zip", fonte="BCB/ESTBAN",
                             observacao=f"saldos por municipio, data-base {ref}")
        except Exception as e:  # noqa: BLE001
            print(f"  [INDISPONIVEL] {ref}: {e}")
            continue

        with zipfile.ZipFile(io.BytesIO(conteudo)) as z:
            nome_csv = z.namelist()[0]
            with z.open(nome_csv) as fh:
                # layout oficial: 2 linhas de cabecalho antes da tabela, separador ';'
                df = pd.read_csv(fh, sep=";", encoding="latin-1", skiprows=2,
                                 decimal=",", low_memory=False)
        df["data_base"] = ref
        quadros.append(df)
        print(f"  [OK] {ref}: {len(df):>7,} linhas | {len(df.columns)} colunas | "
              f"arquivo interno: {nome_csv}")

    if not quadros:
        print("  nenhuma data-base disponivel")
        return pd.DataFrame()

    est = pd.concat(quadros, ignore_index=True)
    DATA_PROC.mkdir(parents=True, exist_ok=True)
    est.to_parquet(DATA_PROC / "estban_municipio.parquet", index=False)
    print(f"\n  ESTBAN: {len(est):,} linhas | datas-base {sorted(est['data_base'].unique())}")
    print(f"  colunas: {list(est.columns)[:12]}")
    return est


if __name__ == "__main__":
    print(f"[{agora_utc()}] ESTBAN -- coleta por municipio")
    coleta()
