# Mapa dos 18 indicadores → campo, fonte e fórmula

Cada linha aponta para um campo **existente e conferido** em `data_processed/`.
O dicionário completo (com a fórmula COSIF de cada conta) está em
`data_processed/dicionario_campos_ifdata.csv` — 15.512 linhas, 17 relatórios.

**Convenções**
`P` = `painel_ifdata_longo.parquet` (2019Q1–2026Q1) · `PR` = `painel_ifdata_prudencial.parquet`
(2023Q3–2026Q1) · `S` = `sgs_series.parquet` · `SCR` = `scr_agregado.parquet` ·
`E` = `estban_municipio.parquet`.
Sufixo `_real` = já deflacionado pelo IPCA, em **R$ de 03/2026**.

---

## P1 — CRESCIMENTO

| # | Indicador | Campo / fonte | Fórmula | Referência |
|---|---|---|---|---|
| 1 | Crescimento real anual da carteira | `P.carteira_credito_real` (IF.data Resumo) | `x_t / x_{t-4} − 1` | mediana do universo no trimestre + própria média histórica |
| 2 | Credit gap da IF | `P.carteira_credito_real` | desvio % da tendência HP (λ=1600, trimestral) | +1 desvio-padrão do próprio gap |
| 3 | Persistência do boom | derivado de #1 | nº de trimestres consecutivos com crescimento real ≥ 15% a.a. | ≥ 8 trimestres = boom (FMI, Aula 2) |
| 4 | Crescimento da carteira ÷ crescimento do capital | `PR.carteira_credito_real` ÷ `PR.pr_real` (Informações de Capital) | `(cart_t/cart_{t-4}) ÷ (pr_t/pr_{t-4})` | 1,0 = cresce *pari passu* ao capital |
| 5 | Crescimento nas modalidades de maior risco | `P.pf_cartao_real`, `P.pf_sem_consignacao_real` | var. % a.a. real da soma | mesma modalidade no sistema: `SCR` (PF – Cartão de crédito; PF – Empréstimo sem consignação) |
| 6 | Velocidade de ganho de *market share* | `P.carteira_credito_real` | `share_t − share_{t-4}` em p.p., share = IF ÷ soma do universo | variação de share dos pares (mesmo TCB) |

> **Denominador fixado:** *share* e HHI usam **Carteira de Crédito** do relatório Resumo —
> não Ativo Total, não crédito livre. (Trata o risco nº 3 da proposta.)

## P2 — CONCENTRAÇÃO

| # | Indicador | Campo / fonte | Fórmula | Referência |
|---|---|---|---|---|
| 1 | HHI do sistema | `P.carteira_credito_real` | `Σ share_i² × 10.000` | faixas antitruste 1.500 / 2.500 |
| 2 | CR5 | `P.carteira_credito_real` | soma do share dos 5 maiores | própria série no tempo |
| 3 | % da carteira em modalidades de alto risco | `P.pf_cartao_real`, `P.pf_sem_consignacao_real`, `P.pf_total_real` | `(cartão + sem consignação) ÷ total PF` | mesma razão agregada do universo e do `SCR` |
| 4 | Concentração regional | `P.reg_sudeste_real` … `P.reg_centro_oeste_real` | HHI das 5 regiões | HHI regional do universo; `E` para detalhe municipal (corte transversal) |
| 5 | Exposição a tomadores de grande porte | `P.pj_porte_grande_real` ÷ `P.pj_total_porte_real` (IF.data · Carteira PJ por porte do tomador) | razão | mediana dos pares (mesmo TCB); p75 do universo = 24,1% |
| 6 | Dependência de funding / *loan-to-deposit* | `P.carteira_credito_real` ÷ `P.captacoes_real` | razão | mediana dos pares (mesmo TCB) |

> **O indicador 5 foi trocado.** A primeira versão usava **ticket médio** (carteira ÷ nº de
> clientes) como *proxy* de concentração em grandes tomadores. Proxy é o oposto de fonte direta,
> e o indicador não media o que o nome prometia: ticket médio é granularidade média, não
> exposição a grandes devedores.
>
> No lugar entrou um campo **publicado diretamente pelo IF.data por instituição** — a repartição
> da carteira PJ por **porte do tomador** (Micro / Pequena / Média / Grande). O indicador é a
> fatia em *Grande*.
>
> **Denominador:** o total de PJ do **próprio relatório de porte**, não a "Carteira de Crédito"
> do Resumo. Os dois recortes diferem (o relatório de crédito inclui exterior e exclui itens que
> o Resumo agrega) e misturá-los produziria razões acima de 100%.
>
> **Cobertura:** 93% no universo que entra na agenda (carteira ≥ R$ 1 bi); 37% sem corte de
> porte, porque o indicador é **PJ-only**. Instituições sem carteira PJ — emissores puros de
> cartão como Carrefour/CSF, Midway, CredSystem — ficam com o campo **vazio, não zero**, e não
> pontuam neste item.
>
> **O que ele ainda não faz:** não é Herfindahl sobre devedores. Mede exposição ao *segmento* de
> grandes tomadores, onde vive o risco de nome único, mas um banco com muitos clientes grandes
> aparece igual a um com poucos. Concentração em poucos nomes segue fora do alcance do painel —
> o SCR agregado publicado não divulga exposição por devedor.
>
> O ticket médio permanece no comparador como **contexto descritivo** (`ctx_ticket_medio_real`),
> explicitamente fora do score e fora da contagem dos 18 indicadores.

## P3 — DETERIORAÇÃO

| # | Indicador | Campo / fonte | Fórmula | Referência |
|---|---|---|---|---|
| 1 | Inadimplência por IF | 2025+: `PR.inadimplencia_valor_real` ÷ `PR.carteira_credito_real`; até 2024: `P.risco_e..risco_h` ÷ `P.risco_total_geral` | razão | sistema: `SGS 21082` (total), `21112` (PF livre), `21086` (PJ livre) |
| 2 | Índice de cobertura | 2025+: `PR.perda_esperada_real` ÷ `PR.inadimplencia_valor_real`; até 2024: `P.provisao_antiga_real` ÷ (`risco_e..h`) | razão | ≥ 100% e própria série |
| 3 | Provisão ÷ carteira total | 2025+: `PR.perda_esperada_real` ÷ `PR.carteira_credito_real`; até 2024: `P.provisao_antiga_real` ÷ `P.carteira_credito_real` | razão | mediana dos pares |
| 4 | Inadimplência ajustada ao crescimento | #1 e P1#1 | inadimplência sobre a carteira **defasada 4 trimestres** (`atraso_t ÷ carteira_{t-4}`) | mesma métrica nas IFs de baixo crescimento |
| 5 | Ativos problemáticos | `PR.ativos_problematicos_valor_real` ÷ `PR.carteira_credito_real` | razão | `SCR.ativo_problematico` (sistema) |
| 6 | Índice de Basileia / folga de capital | `PR.indice_basileia`, `PR.indice_capital_principal`, `PR.razao_alavancagem` | folga = Basileia − 10,5 p.p. | mínimo regulatório 8% + adicionais ≈ 10,5% |

> **Indicador 4 é o coração do trabalho.** Ele existe para atacar o **efeito denominador**:
> `atraso_t ÷ carteira_t` cai artificialmente quando a carteira cresce rápido. Usar a carteira
> de 4 trimestres antes no denominador mostra o atraso contra a base que de fato o originou.

---

## Quebra de regime — o que NÃO se encadeia

A Res. CMN 4.966/2021 (vigente 01/01/2025) trocou o modelo AA–H por perda esperada (ECL).
Consequência prática nos indicadores P3 #1, #2 e #3:

| até 202412 | de 202503 |
|---|---|
| provisão = "Provisão sobre Operações de Crédito" (COSIF 16900008) | provisão = "Perda Esperada" (ECL) |
| qualidade = carteira por nível de risco AA–H | qualidade = "Inadimplência" e "Ativos problemáticos" (em R$) |
| universo dos relatórios de crédito = tipo 1005 | universo = tipo 1009 |

As duas metodologias **não formam uma série contínua**. O painel marca cada linha com
`regime_contabil` e trata 202412 como ponto de corte visual — nunca liga os dois trechos
com uma única linha.

## Validação cruzada contra fontes independentes (`src/valida_cruzada.py`)

O painel (IF.data, por instituição) foi confrontado com séries que **não** participam da sua
construção. Não se espera igualdade — os recortes diferem —, espera-se mesma ordem de
grandeza e mesma direção.

| confronto | resultado |
|---|---|
| carteira agregada do painel ÷ **SGS 20539** | razão estável **1,07–1,12** em 29 trimestres. O IF.data é mais amplo (inclui arrendamento e outras operações com característica de crédito). Diferença de recorte, estável — não é erro. |
| inadimplência agregada × **SGS 21082** | divergência média **0,34 p.p.** |
| ativos problemáticos × **SCR.data** | divergência média **1,18 p.p.**, mesma direção |

### Episódio de erro nº 1 — detectado e corrigido por esta validação

A primeira versão preenchia a inadimplência anterior a 2025 com a soma dos níveis de risco
**E–H**. A validação acusou divergência média de **2,23 p.p.** contra o SGS 21082, sempre
para cima. Causa: **E–H é classificação de risco, não atraso acima de 90 dias** — são conceitos
diferentes, e a soma E–H é sistematicamente maior.

Correção: a métrica AA–H passou a viver em coluna própria (`p3_1b_niveis_eh`, rotulada
"carteira em níveis E–H") e **nunca** preenche a lacuna da inadimplência 90+
(`p3_1_inadimplencia`, só regime ECL). Após a correção a divergência caiu para **0,34 p.p.**

### Episódio de erro nº 2 — sinal das contas retificadoras

Provisão e Perda Esperada são contas **redutoras** do ativo no COSIF: o saldo publicado é
negativo (26.129 valores negativos, **nenhum** positivo — `src/checa_sinais.py`). A primeira
versão produzia cobertura de **−1,45** e provisão/carteira de **−5,9%**. Corrigido com valor
absoluto **apenas** nas contas retificadoras; inadimplência e ativos problemáticos já vêm
positivos e não levam `abs()`.

### Episódio de erro nº 3 — variação anual comparando instituições diferentes

O código da instituição (`cod_inst`) **não é o mesmo** nos universos 1005 (até 202412) e
1009 (2025+). Como o painel longo emenda os dois, toda variação de 12 meses que cruzasse
202412→202503 comparava códigos distintos e voltava vazia. O sintoma: em 2025Q1 o
crescimento real existia para apenas **149 de 257** instituições, e o indicador
carteira÷capital para **nenhuma**.

Correção: as variações anuais passaram a ser calculadas **dentro de cada universo** e só
depois combinadas (`_colunas_crescimento` em `src/indicadores.py`). Resultado: crescimento
em 2025Q1 vai de 149 para **256** instituições e carteira÷capital de 0 para **256**.

> Resíduo conhecido: o *credit gap* (P1 nº 2) continua em ~154 instituições nos trimestres
> de 2025. O filtro HP exige no mínimo 12 trimestres consecutivos no mesmo universo, e o
> universo prudencial só tem 11 (202309–202603). É limitação de janela, não erro — e está
> declarada na seção de limites.

### Episódio de erro nº 4 — arquivos corrompidos aceitos como dado

O endpoint do IF.data responde **HTTP 200 com corpo `"Erro interno - Internal error"`** de
forma intermitente. Três de 941 arquivos entraram assim em `data_raw`. Correção: o coletor
passou a validar que a resposta é JSON antes de gravar (`src/comum.py`) e existe uma
auditoria de integridade (`src/audita_raw.py`) — hoje **941 arquivos, 0 inválidos**.

## Cobertura verificada (% de linhas preenchidas)

| campo | universo `longo` | universo `prudencial` |
|---|---|---|
| `carteira_credito` | 99,7% (2019–2024) / 98,1% (2025+) | 99,7% / 98,1% |
| `pr`, `indice_basileia` | — (relatório inexistente no tipo 1005) | **99,6% / 97,2%** |
| `provisao_antiga` | 99,7% até 202412 | 99,7% até 202412 |
| `perda_esperada` | 98,0% de 202503 | 98,0% de 202503 |
| `inadimplencia_valor`, `ativos_problematicos_valor` | 79,6% de 202503 | 79,6% de 202503 |
| `pf_cartao` / `pf_sem_consignacao` | 20,4% / 66,2% | só 2025+ |
| `qtd_clientes` | 83,3% / 79,2% | 79,2% (2025+) |

> `pf_cartao` em 20,4% não é falha de coleta: a maioria das ~1.400 instituições do universo
> (cooperativas singulares, bancos de nicho) simplesmente **não opera cartão de crédito**, e o
> IF.data não publica linha zerada. O painel deve tratar ausência como "não opera", não como
> "dado faltante" — e o ranking de P2 #3 só considera IFs com carteira PF relevante.

## Pendências (campos que ficam VAZIOS, por decisão)

| item | motivo |
|---|---|
| Exposição aos maiores tomadores | não publicada no SCR agregado — usa-se proxy declarada |
| `pj_cheque_especial` em 7 de 29 trimestres | variação de nomenclatura no relatório PJ em anos iniciais — campo secundário, não usado no ranking |
| Endividamento / comprometimento de renda | nenhuma série localizada na varredura do catálogo SGS |
| ESTBAN série longa | fonte publica apenas os últimos 6 meses |
