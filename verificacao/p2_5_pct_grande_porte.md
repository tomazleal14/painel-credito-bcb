# Nota de verificação — P2 · Exposição a tomadores de grande porte

`p2_5_pct_grande_porte`

| campo | conteúdo |
|---|---|
| Pergunta | **P2** |
| Fonte primária | IF.data · Carteira de crédito ativa PJ por porte do tomador |
| Campos de origem | `pj_porte_grande`, `pj_total_porte` |
| Fórmula | `carteira PJ em tomadores de grande porte / total da carteira PJ` |
| Referência de comparação | Mediana dos pares do mesmo TCB; p75 do universo = 24,1% |
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
| AA-H (Res. 2.682) | 30.7% |
| Res. 4.966 (ECL) | 37.3% |

Observações válidas no último trimestre (202603): **502**.

## Estatísticas na janela

| medida | valor |
|---|---|
| mediana | 0.0687 |
| p10 | 0.0030 |
| p90 | 0.5565 |

## Como reproduzir

```bash
.venv/Scripts/python.exe src/coleta_ifdata.py     # baixa o bruto
.venv/Scripts/python.exe src/constroi_base.py     # monta o painel e deflaciona
.venv/Scripts/python.exe src/indicadores.py       # calcula este indicador
```

## Limites

O denominador e o **total de PJ do proprio relatorio de porte**, e nao a "Carteira de Credito" do Resumo: os dois recortes diferem (o relatorio de credito inclui o exterior e exclui operacoes que o Resumo agrega), e mistura-los produziria razoes acima de 100%.

O indicador e **PJ-only**. Instituicoes sem carteira PJ -- emissores puros de cartao, por exemplo -- ficam com o campo **VAZIO, nao zero**, e simplesmente nao pontuam neste item (o score usa a media dos indicadores disponiveis). No universo que entra na agenda (carteira >= R$ 1 bi) a cobertura e de **93%**; sem corte de porte, 37%.

Mede **exposicao a tomadores de grande porte**, que e onde vive o risco de nome unico. Nao e um indice de Herfindahl sobre devedores: um banco com muitos clientes grandes aparece igual a um banco com poucos. O SCR agregado publicado nao divulga exposicao por devedor, entao a concentracao em poucos nomes continua fora do alcance do painel.

Ver `01_mapa_indicadores.md` — quebra de regime da Res. 4.966, validação cruzada contra
SGS/SCR e os quatro episódios de erro corrigidos — e a seção "O que este painel NÃO permite
concluir", exibida na aba Visão geral do painel.
