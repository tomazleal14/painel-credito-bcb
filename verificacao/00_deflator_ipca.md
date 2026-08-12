# Nota de verificacao -- DEFLATOR (IPCA)

| campo | conteudo |
|---|---|
| Fonte | Banco Central do Brasil -- Sistema Gerenciador de Series Temporais (SGS) |
| Serie | **433** -- Indice nacional de precos ao consumidor-amplo (IPCA) |
| Nome conferido no catalogo | sim (ver `data_processed/catalogo_series_sgs.csv`, status CONFIRMADO) |
| Endpoint de dados | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial={DATA_INICIAL}` |
| Endpoint de catalogo | `https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS?method=getUltimoValorXML&codigoSerie=433` |
| Unidade da fonte | Var. % mensal |
| Periodicidade | Mensal |
| Recorte | Brasil, indice cheio (nao e nucleo nem grupo) |
| Data de extracao (UTC) | 2026-08-12T00:28:52Z |
| Hash do arquivo bruto | ver `data_raw/manifesto_coleta.csv`, linha `data_raw/sgs/sgs_433.json` |

## Transformacao aplicada

1. O SGS publica **variacao percentual mensal**, nao numero-indice.
2. Numero-indice construido por acumulacao: `I_t = I_(t-1) * (1 + var_t/100)`, com `I_0 = 100`
   no primeiro mes da amostra (01/2015). O nivel de `I_0` e arbitrario e
   **nao afeta** o resultado, pois so se usa a RAZAO entre indices.
3. Base de referencia: **202603** (indice = 185.8570).
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
