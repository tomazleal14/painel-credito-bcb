# Nota de verificação — P2 · Crédito ÷ ativo total

`p2_9_credito_sobre_ativo`

| campo | conteúdo |
|---|---|
| Pergunta | **P2** |
| Fonte primária | IF.data · Resumo · Carteira de Crédito e Ativo Total |
| Campos de origem |  |
| Fórmula | `carteira_real ÷ ativo_total_real` |
| Referência de comparação | quanto do balanço está exposto a risco de crédito |
| Unidade | razão, % ou p.p. conforme a fórmula acima |
| Deflator | **Não altera o resultado.** É uma razão entre valores da mesma data-base: o fator do IPCA aparece no numerador e no denominador e se cancela. O cálculo usa as colunas `_real` por consistência, mas o número seria idêntico em termos nominais. |
| Recorte | IF.data trimestral por instituição; universo fixado em `00_fontes_confirmadas.md` §2 |
| Janela | 201903 – 202603 (29 trimestres) |
| Data de extração (UTC) | 2026-08-12T00:23:41Z |
| Rastreabilidade do bruto | `data_raw/manifesto_coleta.csv` — 974 arquivos com URL e SHA-256 |

## Contas COSIF de origem

- (indicador derivado de razões; ver os campos de origem acima)

## Cobertura observada (% de linhas com valor)

| regime contábil | preenchimento |
|---|---|
| AA-H (Res. 2.682) | 99.7% |
| Res. 4.966 (ECL) | 98.1% |

Observações válidas no último trimestre (202603): **1.353**.

## Estatísticas na janela

| medida | valor |
|---|---|
| mediana | 0.5240 |
| p10 | 0.0000 |
| p90 | 0.7967 |

## Como reproduzir

```bash
.venv/Scripts/python.exe src/coleta_ifdata.py     # baixa o bruto
.venv/Scripts/python.exe src/constroi_base.py     # monta o painel e deflaciona
.venv/Scripts/python.exe src/indicadores.py       # calcula este indicador
```

## Limites

Ver `01_mapa_indicadores.md` — quebra de regime da Res. 4.966, validação cruzada contra
SGS/SCR e os quatro episódios de erro corrigidos — e a seção "O que este painel NÃO permite
concluir", exibida na aba Visão geral do painel.
