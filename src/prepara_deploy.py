"""
prepara_deploy.py -- gera a versao enxuta de data_processed/ que o app precisa.

Motivo: o Streamlit Community Cloud clona o repositorio inteiro. Os brutos do IF.data
(~790 MB) e os paineis largos nao sao necessarios em execucao -- o app le apenas os
indicadores ja calculados e as series de referencia.

O que continua versionado (rastreabilidade):
  data_raw/manifesto_coleta.csv        URL, hora de extracao, SHA-256 de CADA arquivo
  data_raw/sgs/catalogo/*.xml          prova de que o nome da serie foi conferido
  data_processed/catalogo_series_sgs.csv
  data_processed/dicionario_campos_ifdata.csv (comprimido)
Os blobs sao reproduziveis rodando src/coleta_*.py.
"""
from __future__ import annotations

import pandas as pd

from comum import DATA_PROC

# colunas que o app realmente usa
IDENT = ["data_base", "cod_inst", "instituicao", "tcb", "controle", "uf", "municipio",
         "segmento_sr", "regime_contabil", "tipo_instituicao", "base_deflator"]
NIVEIS = ["carteira_credito_real", "carteira_credito", "share_carteira",
          "indice_basileia", "indice_capital_principal", "razao_alavancagem",
          "pf_total_real", "pf_cartao_real", "pf_sem_consignacao_real",
          "pf_consignado_real", "pf_veiculos_real", "pf_habitacao_real",
          "pf_rural_real", "pf_outros_real",
          "reg_sudeste_real", "reg_sul_real", "reg_nordeste_real",
          "reg_norte_real", "reg_centro_oeste_real",
          "pj_total_porte_real", "pj_porte_grande_real",
          "ctx_ticket_medio_real"]  # contexto descritivo, fora do score


def main() -> None:
    ind = pd.read_parquet(DATA_PROC / "indicadores.parquet")
    inds = [c for c in ind.columns if c[:2] in ("p1", "p2", "p3")]
    cols = [c for c in IDENT + NIVEIS + inds if c in ind.columns]

    enxuto = ind[cols].copy()
    # float32 corta o arquivo pela metade sem perda relevante para exibicao
    for c in enxuto.columns:
        if enxuto[c].dtype == "float64":
            enxuto[c] = enxuto[c].astype("float32")

    destino = DATA_PROC / "app_indicadores.parquet"
    enxuto.to_parquet(destino, index=False, compression="zstd")

    dic = pd.read_csv(DATA_PROC / "dicionario_campos_ifdata.csv")
    dic.to_parquet(DATA_PROC / "dicionario_campos_ifdata.parquet",
                   index=False, compression="zstd")

    mb = destino.stat().st_size / 1024 ** 2
    print(f"app_indicadores.parquet: {len(enxuto):,} linhas x {len(cols)} colunas | {mb:.1f} MB")
    print(f"  indicadores incluidos: {len(inds)}")
    dic_mb = (DATA_PROC / 'dicionario_campos_ifdata.parquet').stat().st_size / 1024 ** 2
    print(f"dicionario_campos_ifdata.parquet: {dic_mb:.1f} MB "
          f"(csv original: {(DATA_PROC / 'dicionario_campos_ifdata.csv').stat().st_size/1024**2:.1f} MB)")


if __name__ == "__main__":
    main()
