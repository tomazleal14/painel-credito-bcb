# Nota de verificação — P1 · Credit gap

`p1_2_credit_gap`

| campo | conteúdo |
|---|---|
| Pergunta | **P1** |
| Fonte primária | IF.data · Resumo · Carteira de Crédito |
| Campos de origem |  |
| Fórmula | `ciclo do filtro Hodrick-Prescott (λ=1600) sobre ln(carteira real)` |
| Referência de comparação | exige 12 trimestres de série no mesmo universo |
| Unidade | razão, % ou p.p. conforme a fórmula acima |
| Deflator | **Essencial.** IPCA, SGS 433 — o indicador compara períodos, então valores nominais inflariam o resultado. Valores reais em R$ de 03/2026 (ver `00_deflator_ipca.md`). |
| Recorte | IF.data trimestral por instituição; universo fixado em `00_fontes_confirmadas.md` §2 |
| Janela | 201903 – 202603 (29 trimestres) |
| Data de extração (UTC) | 2026-08-12T00:23:41Z |
| Rastreabilidade do bruto | `data_raw/manifesto_coleta.csv` — 974 arquivos com URL e SHA-256 |

## Contas COSIF de origem

- (indicador derivado de razões; ver os campos de origem acima)

## Cobertura observada (% de linhas com valor)

| regime contábil | preenchimento |
|---|---|
| AA-H (Res. 2.682) | 76.4% |
| Res. 4.966 (ECL) | 10.6% |

Observações válidas no último trimestre (202603): **731**.

## Estatísticas na janela

| medida | valor |
|---|---|
| mediana | 0.0086 |
| p10 | -0.1401 |
| p90 | 0.1504 |

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
