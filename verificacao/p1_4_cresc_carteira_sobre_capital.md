# Nota de verificação — P1 · Crescimento da carteira ÷ crescimento do capital

`p1_4_cresc_carteira_sobre_capital`

| campo | conteúdo |
|---|---|
| Pergunta | **P1** |
| Fonte primária | IF.data · Resumo + Informações de Capital |
| Campos de origem | `carteira_credito`, `pr` |
| Fórmula | `(1+cresc_carteira) / (1+cresc_PR)` |
| Referência de comparação | 1,0 = crescimento pari passu ao capital |
| Unidade | razão, % ou p.p. conforme a fórmula acima |
| Deflator | **Essencial.** IPCA, SGS 433 — o indicador compara períodos, então valores nominais inflariam o resultado. Valores reais em R$ de 03/2026 (ver `00_deflator_ipca.md`). |
| Recorte | IF.data trimestral por instituição; universo fixado em `00_fontes_confirmadas.md` §2 |
| Janela | 201903 – 202603 (29 trimestres) |
| Data de extração (UTC) | 2026-08-12T00:23:41Z |
| Rastreabilidade do bruto | `data_raw/manifesto_coleta.csv` — 973 arquivos com URL e SHA-256 |

## Contas COSIF de origem

- `carteira_credito` = [31000000]
- `pr` = [60000002] + [70000009]+ [80000006]

## Cobertura observada (% de linhas com valor)

| regime contábil | preenchimento |
|---|---|
| AA-H (Res. 2.682) | 4.8% |
| Res. 4.966 (ECL) | 77.0% |

Observações válidas no último trimestre (202603): **1.026**.

## Estatísticas na janela

| medida | valor |
|---|---|
| mediana | 0.9499 |
| p10 | 0.6992 |
| p90 | 1.2308 |

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
