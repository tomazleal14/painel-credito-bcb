# Nota de verificação — P3 · Inadimplência sobre a carteira

`p3_1_inadimplencia`

| campo | conteúdo |
|---|---|
| Pergunta | **P3** |
| Fonte primária | IF.data · Carteira por instrumentos financeiros |
| Campos de origem | `inadimplencia_valor`, `carteira_credito` |
| Fórmula | `carteira inadimplida / carteira` |
| Referência de comparação | SGS 21082 (SFN), 21112 (PF livre), 21086 (PJ livre) |
| Unidade | razão, % ou p.p. conforme a fórmula acima |
| Deflator | **Não altera o resultado.** É uma razão entre valores da mesma data-base: o fator do IPCA aparece no numerador e no denominador e se cancela. O cálculo usa as colunas `_real` por consistência, mas o número seria idêntico em termos nominais. |
| Recorte | IF.data trimestral por instituição; universo fixado em `00_fontes_confirmadas.md` §2 |
| Janela | 201903 – 202603 (29 trimestres) |
| Data de extração (UTC) | 2026-08-12T00:23:41Z |
| Rastreabilidade do bruto | `data_raw/manifesto_coleta.csv` — 973 arquivos com URL e SHA-256 |

## Contas COSIF de origem

- `carteira_credito` = [31000000]

## Cobertura observada (% de linhas com valor)

| regime contábil | preenchimento |
|---|---|
| AA-H (Res. 2.682) | 0.0% |
| Res. 4.966 (ECL) | 76.6% |

Observações válidas no último trimestre (202603): **1.044**.

## Estatísticas na janela

| medida | valor |
|---|---|
| mediana | 0.0357 |
| p10 | 0.0000 |
| p90 | 0.1356 |

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
