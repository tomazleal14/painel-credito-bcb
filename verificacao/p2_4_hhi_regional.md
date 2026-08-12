# Nota de verificação — P2 · Concentração regional da carteira

`p2_4_hhi_regional`

| campo | conteúdo |
|---|---|
| Pergunta | **P2** |
| Fonte primária | IF.data · Carteira por região geográfica |
| Campos de origem | `reg_sudeste`, `reg_sul`, `reg_nordeste`, `reg_norte`, `reg_centro_oeste` |
| Fórmula | `HHI entre as 5 regiões x 10.000` |
| Referência de comparação | HHI regional do universo; ESTBAN para detalhe municipal |
| Unidade | razão, % ou p.p. conforme a fórmula acima |
| Deflator | **Não altera o resultado.** É uma razão entre valores da mesma data-base: o fator do IPCA aparece no numerador e no denominador e se cancela. O cálculo usa as colunas `_real` por consistência, mas o número seria idêntico em termos nominais. |
| Recorte | IF.data trimestral por instituição; universo fixado em `00_fontes_confirmadas.md` §2 |
| Janela | 201903 – 202603 (29 trimestres) |
| Data de extração (UTC) | 2026-08-12T00:23:41Z |
| Rastreabilidade do bruto | `data_raw/manifesto_coleta.csv` — 973 arquivos com URL e SHA-256 |

## Contas COSIF de origem

- (indicador derivado de razões; ver os campos de origem acima)

## Cobertura observada (% de linhas com valor)

| regime contábil | preenchimento |
|---|---|
| AA-H (Res. 2.682) | 83.3% |
| Res. 4.966 (ECL) | 78.6% |

Observações válidas no último trimestre (202603): **1.075**.

## Estatísticas na janela

| medida | valor |
|---|---|
| mediana | 9653.0105 |
| p10 | 4069.0997 |
| p90 | 9996.7442 |

## Como reproduzir

```bash
.venv/Scripts/python.exe src/coleta_ifdata.py     # baixa o bruto
.venv/Scripts/python.exe src/constroi_base.py     # monta o painel e deflaciona
.venv/Scripts/python.exe src/indicadores.py       # calcula este indicador
```

## Limites

Valores proximos de 10.000 indicam atuacao praticamente em uma unica regiao -- comum e esperado em cooperativas singulares, que por desenho atuam num territorio. A leitura de risco so faz sentido contra os pares do mesmo TCB.

Ver `01_mapa_indicadores.md` — quebra de regime da Res. 4.966, validação cruzada contra
SGS/SCR e os quatro episódios de erro corrigidos — e a seção "O que este painel NÃO permite
concluir", exibida na aba Visão geral do painel.
