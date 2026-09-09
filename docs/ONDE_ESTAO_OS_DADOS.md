# Onde estão os dados — guia de conferência

Gerado por `src/inventario.py` em 09/09/2026 00:48 UTC.

Este documento existe para a apresentação: qualquer número do painel pode ser rastreado até o arquivo bruto que o originou.

## Caminho da pasta

```
C:\Users\tomaz\OneDrive\Doutorado EPGE\Crédito no Varejo\painel_credito_bcb
```

## Estrutura

| pasta | arquivos | tamanho | conteúdo |
|---|---|---|---|
| `data_raw/ifdata/` | 916 | 132.7 MB | **brutos do IF.data** — JSON originais, por trimestre |
| `data_raw/sgs/` | 45 | 0.2 MB | **brutos do SGS** — séries e XML do catálogo oficial |
| `data_raw/scr/` | 21 | 0.6 MB | **brutos do SCR.data** — séries por modalidade |
| `data_raw/estban/` | 6 | 5.0 MB | **brutos do ESTBAN** — ZIP por data-base |
| `data_processed/` | 14 | 76.1 MB | **derivados** — painéis, indicadores, dicionário, deflator |
| `verificacao/` | 22 | 0.1 MB | **notas de verificação** — uma por indicador e por fonte |
| `src/` | 45 | 0.3 MB | **código** — coleta, transformação, cálculo e verificação |

## Manifesto de coleta

`data_raw/manifesto_coleta.csv` — **974 registros**, cada um com URL, data/hora de extração (UTC), SHA-256 e tamanho em bytes.

| fonte | arquivos baixados |
|---|---|
| BCB/IF.data | 919 |
| BCB/SCR.data | 21 |
| BCB/SGS (catalogo) | 14 |
| BCB/SGS | 14 |
| BCB/ESTBAN | 6 |

## Arquivos derivados (data_processed/)

| arquivo | tamanho | o que é |
|---|---|---|
| `app_indicadores.parquet` | 6.1 MB | **base que o painel lê** — 36 indicadores + campos de apoio |
| `catalogo_series_sgs.csv` | 0.0 MB | **as 14 séries do SGS**, com nome oficial conferido |
| `deflator_ipca.csv` | 0.0 MB | **deflator IPCA** — índice e fator por mês |
| `dicionario_campos_ifdata.csv` | 13.9 MB | **dicionário de campos do IF.data**, com fórmula COSIF |
| `dicionario_campos_ifdata.parquet` | 0.1 MB | o mesmo dicionário, comprimido para o painel |
| `estban_municipio.parquet` | 9.0 MB | ESTBAN consolidado por município |
| `glossario_filtros.csv` | 0.0 MB | descrições oficiais das siglas TCB, SR e TC |
| `indicadores.parquet` | 24.5 MB | base completa, com todas as colunas intermediárias |
| `painel_ifdata_longo.parquet` | 17.5 MB | painel por instituição, universo de série longa (1005→1009) |
| `painel_ifdata_longo_amostra.csv` | 0.5 MB | derivado |
| `painel_ifdata_prudencial.parquet` | 4.5 MB | painel por instituição, universo prudencial (1009) |
| `painel_ifdata_prudencial_amostra.csv` | 0.1 MB | derivado |
| `scr_agregado.parquet` | 0.0 MB | SCR por modalidade e tipo de cliente |
| `sgs_series.parquet` | 0.0 MB | observações das séries do SGS |

## Como conferir um número, ao vivo

1. **A série do SGS existe e é a certa?**
   `data_processed/catalogo_series_sgs.csv` traz o nome oficial lido do catálogo do
   BCB e o status `CONFIRMADO`. O XML de resposta está em
   `data_raw/sgs/catalogo/sgs_{codigo}_catalogo.xml`.

2. **De onde vem um campo do IF.data?**
   `data_processed/dicionario_campos_ifdata.csv` — filtre pelo nome da coluna e veja
   o relatório, a data de geração e a **fórmula COSIF** da conta.

3. **O arquivo bruto é o que dizemos que é?**
   `data_raw/manifesto_coleta.csv` tem URL, hora da extração e SHA-256 de cada
   arquivo. `src/audita_raw.py` revalida a integridade de todos.

4. **O decodificador está certo?**
   `src/testa_extracao.py` compara três valores com a tela oficial do IF.data.

5. **Como um indicador vira score?**
   `src/rastreia_cartao.py` mostra a cadeia numa instituição real: valor → percentil
   → média → corte → carteira exposta.

## Nota sobre o que está no GitHub

Os brutos do IF.data ocupam 132.7 MB em disco (guardados comprimidos; o SHA-256 registrado é o do arquivo original) e **não** são
versionados — são reproduzíveis por `src/coleta_ifdata.py`. O que vai ao repositório é o manifesto
(com URL e SHA-256 de cada arquivo), os XML do catálogo do SGS e os derivados que o
painel usa. A rastreabilidade não depende de guardar os blobs: depende do manifesto
e do script que os regenera.