"""
deflator.py -- constroi o deflator IPCA usado em TODA serie de valor do painel.

DECISOES EXPLICITAS (risco 2 da proposta: "serie nominal vs. real"):
  Indice de precos : IPCA, SGS 433 (Var. % mensal), fonte BCB/SGS.
                     O SGS publica a VARIACAO mensal; o numero-indice e construido
                     aqui por acumulacao: I_t = I_{t-1} * (1 + var_t/100), I_0 = 100.
  Base do indice   : ultima data-base do IF.data disponivel no painel (default 202603).
                     Todo valor real fica expresso em "R$ de <base>".
  Alinhamento      : IF.data e trimestral (marco/junho/setembro/dezembro). Usa-se o
                     IPCA do MES DA DATA-BASE (indice de fim de trimestre), nao a media
                     do trimestre, porque os saldos do IF.data sao ESTOQUES na data-base.
  Series de %      : inadimplencia, Basileia, cobertura NAO sao deflacionadas.

Saida: data_processed/deflator_ipca.csv  (mes, ipca_var_pct, indice_ipca, fator_para_base)
       valor_real = valor_nominal * fator_para_base
"""
from __future__ import annotations

import pandas as pd

from comum import DATA_PROC, VERIFICACAO, agora_utc

COD_IPCA = 433
BASE_PADRAO = 202603


def constroi(base: int = BASE_PADRAO) -> pd.DataFrame:
    sgs = pd.read_parquet(DATA_PROC / "sgs_series.parquet")
    ipca = sgs[sgs["codigo_sgs"] == COD_IPCA].sort_values("data").reset_index(drop=True)
    if ipca.empty:
        raise RuntimeError("serie 433 (IPCA) ausente -- rode src/coleta_sgs.py antes")

    ipca = ipca.rename(columns={"valor": "ipca_var_pct"})
    # numero-indice por acumulacao da variacao mensal
    ipca["indice_ipca"] = 100.0 * (1.0 + ipca["ipca_var_pct"] / 100.0).cumprod()
    ipca["mes"] = ipca["data"].dt.strftime("%Y%m").astype(int)

    linha_base = ipca.loc[ipca["mes"] == base]
    if linha_base.empty:
        raise RuntimeError(f"IPCA sem observacao para a base {base}; ultimo mes disponivel: "
                           f"{ipca['mes'].max()}")
    indice_base = float(linha_base["indice_ipca"].iloc[0])

    # fator que leva um valor NOMINAL do mes t para R$ da data-base
    ipca["fator_para_base"] = indice_base / ipca["indice_ipca"]
    ipca["base_do_indice"] = base

    saida = ipca[["mes", "data", "ipca_var_pct", "indice_ipca", "fator_para_base", "base_do_indice"]]
    DATA_PROC.mkdir(parents=True, exist_ok=True)
    saida.to_csv(DATA_PROC / "deflator_ipca.csv", index=False, encoding="utf-8-sig")

    nota = f"""# Nota de verificacao -- DEFLATOR (IPCA)

| campo | conteudo |
|---|---|
| Fonte | Banco Central do Brasil -- Sistema Gerenciador de Series Temporais (SGS) |
| Serie | **433** -- Indice nacional de precos ao consumidor-amplo (IPCA) |
| Nome conferido no catalogo | sim (ver `data_processed/catalogo_series_sgs.csv`, status CONFIRMADO) |
| Endpoint de dados | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial={{DATA_INICIAL}}` |
| Endpoint de catalogo | `https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS?method=getUltimoValorXML&codigoSerie=433` |
| Unidade da fonte | Var. % mensal |
| Periodicidade | Mensal |
| Recorte | Brasil, indice cheio (nao e nucleo nem grupo) |
| Data de extracao (UTC) | {agora_utc()} |
| Hash do arquivo bruto | ver `data_raw/manifesto_coleta.csv`, linha `data_raw/sgs/sgs_433.json` |

## Transformacao aplicada

1. O SGS publica **variacao percentual mensal**, nao numero-indice.
2. Numero-indice construido por acumulacao: `I_t = I_(t-1) * (1 + var_t/100)`, com `I_0 = 100`
   no primeiro mes da amostra ({ipca['data'].min():%m/%Y}). O nivel de `I_0` e arbitrario e
   **nao afeta** o resultado, pois so se usa a RAZAO entre indices.
3. Base de referencia: **{base}** (indice = {indice_base:.4f}).
4. Fator de deflacionamento: `fator_t = I_base / I_t`; `valor_real = valor_nominal * fator_t`.
5. Alinhamento trimestral: saldos do IF.data sao **estoques na data-base**, entao se usa o
   indice do **mes da data-base** (fim de trimestre), nao a media do trimestre.

## O que NAO e deflacionado

Inadimplencia, indice de Basileia, indice de cobertura, participacoes (%) e razoes entre
valores do mesmo periodo ja sao adimensionais -- deflacionar seria erro.

## Limite conhecido

O IPCA e um deflator de precos ao consumidor. Aplicado a carteira de credito, ele mede o
crescimento em **poder de compra**, nao em unidades de credito nem ajustado por renda.
Nao substitui uma analise de credito/PIB (que o painel traz em separado, SGS 20622).
"""
    VERIFICACAO.mkdir(parents=True, exist_ok=True)
    (VERIFICACAO / "00_deflator_ipca.md").write_text(nota, encoding="utf-8")

    print(f"deflator IPCA construido | base {base} | indice_base={indice_base:.4f} | "
          f"{len(saida)} meses ({saida['mes'].min()}..{saida['mes'].max()})")
    print(saida.tail(4).to_string(index=False))
    return saida


if __name__ == "__main__":
    constroi()
