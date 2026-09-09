# Nota de verificação — P1 · Crescimento da carteira PJ

`p1_10_cresc_pj_aa`

| campo | conteúdo |
|---|---|
| Pergunta | **P1** |
| Fonte primária | IF.data · Carteira PJ por modalidade · Total (deflacionado) |
| Campos de origem |  |
| Fórmula | `pj_total_real(t) / pj_total_real(t−4) − 1` |
| Referência de comparação | ver o glossario do painel |
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
| AA-H (Res. 2.682) | 53.5% |
| Res. 4.966 (ECL) | 45.7% |

Observações válidas no último trimestre (202603): **826**.

## Estatísticas na janela

| medida | valor |
|---|---|
| mediana | 0.1738 |
| p10 | -0.2391 |
| p90 | 0.9004 |

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
