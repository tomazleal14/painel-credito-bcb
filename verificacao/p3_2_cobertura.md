# Nota de verificação — P3 · Índice de cobertura de provisões

`p3_2_cobertura`

| campo | conteúdo |
|---|---|
| Pergunta | **P3** |
| Fonte primária | IF.data · Ativo (Perda Esperada / Provisão sobre Operações de Crédito) |
| Campos de origem | `perda_esperada`, `provisao_antiga`, `inadimplencia_valor` |
| Fórmula | `|provisão| / carteira inadimplida` |
| Referência de comparação | 100% ou mais, e própria série |
| Unidade | razão, % ou p.p. conforme a fórmula acima |
| Deflator | **Não altera o resultado.** É uma razão entre valores da mesma data-base: o fator do IPCA aparece no numerador e no denominador e se cancela. O cálculo usa as colunas `_real` por consistência, mas o número seria idêntico em termos nominais. |
| Recorte | IF.data trimestral por instituição; universo fixado em `00_fontes_confirmadas.md` §2 |
| Janela | 201903 – 202603 (29 trimestres) |
| Data de extração (UTC) | 2026-08-12T00:23:41Z |
| Rastreabilidade do bruto | `data_raw/manifesto_coleta.csv` — 973 arquivos com URL e SHA-256 |

## Contas COSIF de origem

- `perda_esperada` = [1611001404] + [1611001507] + [1611001600] + [1612001403] + [1612001506] + [1612001609] + [1613001402] + [1613001505] + [1613001608] + [1630501404] + 
- `provisao_antiga` = [16900008]

## Cobertura observada (% de linhas com valor)

| regime contábil | preenchimento |
|---|---|
| AA-H (Res. 2.682) | 75.9% |
| Res. 4.966 (ECL) | 69.6% |

Observações válidas no último trimestre (202603): **948**.

## Estatísticas na janela

| medida | valor |
|---|---|
| mediana | 0.9470 |
| p10 | 0.7142 |
| p90 | 1.8887 |

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
