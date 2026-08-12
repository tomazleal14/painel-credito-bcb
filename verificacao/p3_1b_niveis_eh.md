# Nota de verificação — P3 · Carteira em níveis E–H (regime AA–H, até 202412)

`p3_1b_niveis_eh`

| campo | conteúdo |
|---|---|
| Pergunta | **P3** |
| Fonte primária | IF.data · Carteira por nível de risco |
| Campos de origem | `risco_e`, `risco_f`, `risco_g`, `risco_h`, `carteira_credito` |
| Fórmula | `(E+F+G+H) / carteira` |
| Referência de comparação | NÃO comparável à inadimplência 90+: fica ~2,5 p.p. acima (ver validação cruzada) |
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
| AA-H (Res. 2.682) | 75.6% |
| Res. 4.966 (ECL) | 0.0% |

Observações válidas no último trimestre (202603): **0**.

## Estatísticas na janela

| medida | valor |
|---|---|
| mediana | 0.0478 |
| p10 | 0.0100 |
| p90 | 0.1491 |

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
