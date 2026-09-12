# Nota de verificação — P2 · Funding de resgate imediato

`p2_13_dep_imediato_pct`

| campo | conteúdo |
|---|---|
| Pergunta | **P2** |
| Fonte primária | IF.data · Passivo · Depósitos à Vista e de Poupança ÷ Captações |
| Campos de origem |  |
| Fórmula | `(depósito à vista + poupança) ÷ captações totais` |
| Referência de comparação | mede a COMPOSIÇÃO do funding, que a razão carteira ÷ captações não distingue; é piso, não total — CDB com liquidez diária também é resgatável de imediato e o relatório não abre prazo |
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
| AA-H (Res. 2.682) | 71.7% |
| Res. 4.966 (ECL) | 72.8% |

Observações válidas no último trimestre (202603): **1.004**.

## Estatísticas na janela

| medida | valor |
|---|---|
| mediana | 0.1678 |
| p10 | 0.0000 |
| p90 | 0.3647 |

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
