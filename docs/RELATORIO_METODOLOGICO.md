# Relatório metodológico — Painel decisório de crédito

**Persona:** Supervisão do Banco Central · **Trabalho Intermediário** — FGV / Prof. Genaro Lins
**Grupo:** Tomaz Leal, Roberto Gomides e Diana Cabral
**Data de extração das fontes:** 12/08/2026 · **Janela:** 2019Q1 – 2026Q1 (29 trimestres)

---

## 1. Fontes primárias

Quatro fontes, todas do Banco Central. Nenhum número do painel vem de outra origem.

| Fonte | O que fornece | Endpoint | Papel |
|---|---|---|---|
| **IF.data** | trimestral, **por instituição**: carteira, capital, provisão, inadimplência, modalidades, região, porte do tomador | `www3.bcb.gov.br/ifdata/rest/arquivos?nomeArquivo=…` | **base central** — a decisão é sobre instituições |
| **SGS** | séries agregadas do SFN e o **IPCA** (deflator) | `api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados` | referência de sistema e deflator |
| **SCR.data** | carteira, inadimplência e **ativo problemático** por modalidade | `bcb.gov.br/api/servico/sitebcb/sistemainformacaocredito` | referência de sistema por modalidade |
| **ESTBAN** | saldos por município, por instituição | `bcb.gov.br/content/estatisticas/estatistica_bancaria_estban/municipio/{AAAAMM}_ESTBAN.csv.zip` | corte transversal regional |

**Trava contra código inventado.** Nenhuma série do SGS é baixada antes de o nome oficial
ser lido do catálogo do BCB e conferido contra o nome esperado. Resultado: **14 de 14
séries confirmadas** (`data_processed/catalogo_series_sgs.csv`). Os códigos não vieram de
memória: varreram-se as faixas do bloco de crédito, catalogando **424 séries** pelo nome
oficial (`data_raw/sgs/catalogo/varredura_sgs.csv`).

**Prova de decodificação do IF.data.** O `src/testa_extracao.py` reproduz, dígito a dígito,
três valores exibidos na tela oficial (ITAÚ, 03/2026): Ativo Total, Carteira de Crédito e
Índice de Basileia. Isso valida a engenharia reversa do formato JSON do IF.data.

---

## 2. Transformações aplicadas

Na ordem em que acontecem, de `data_raw/` até a tela:

### 2.1 Decodificação do IF.data
Os arquivos do IF.data são JSON esparsos com estrutura própria. A junção é
`dados[i] = info.lid` → `info.id` = `trel.c[].ifd`, e o cadastro liga `cod_inst` ao nome.
O dicionário de campos resultante tem **15.512 linhas** e traz a **fórmula COSIF** de cada
conta (`data_processed/dicionario_campos_ifdata.csv`).

**Unidades verificadas, não presumidas:** a legenda diz "R$ mil", mas o JSON bruto está em
**R$ unidades** — a interface é que divide por 1.000. Índices (Basileia) vêm como **fração
decimal**. Assumir a legenda deixaria todo o painel 1.000× errado.

### 2.2 Sinal das contas retificadoras
Provisão e Perda Esperada são contas **redutoras** do ativo no COSIF: o saldo publicado é
negativo (26.129 valores negativos, **nenhum** positivo — `src/checa_sinais.py`). Aplica-se
valor absoluto **apenas** nelas; inadimplência e ativos problemáticos já vêm positivos.

### 2.3 Deflacionamento
Todo valor monetário é deflacionado pelo **IPCA (SGS 433)**, base **03/2026**. O SGS publica
a variação mensal; o número-índice é construído por acumulação. Como os saldos do IF.data
são **estoques na data-base**, usa-se o índice do mês da data-base, não a média do trimestre.

O deflator só altera indicadores que **comparam períodos** (7 dos 18). Em razões dentro da
mesma data-base, o fator aparece no numerador e no denominador e **se cancela** — as notas
de verificação declaram isso por indicador.

### 2.4 Universo fixado
| dimensão | escolha |
|---|---|
| Tipo de instituição | **1009** (Conglomerados Prudenciais) em 2025+; **1005** (Conglomerados Financeiros) até 2024 |
| Denominador de share e HHI | **Carteira de Crédito** do relatório Resumo |
| Grupo de pares | mesmo **TCB** (tipo de consolidado bancário), no mesmo trimestre |

---

## 3. Quebra estrutural — o que não se encadeia

A **Res. CMN 4.966/2021** (vigente 01/01/2025) substituiu a classificação AA–H por perda
esperada. Isso aparece nos dados:

| evidência | efeito |
|---|---|
| Relatório "por nível de risco" (AA–H) | existe até 202412; **some** em 2025 |
| Relatório "por carteiras de instrumentos financeiros" | **novo** em 2025, traz Inadimplência e Ativos problemáticos |
| Relatórios de crédito | migram do tipo 1005 para o 1009 |

**Validação cruzada** (`src/valida_cruzada.py`) contra o SGS 21082 mostrou por que as duas
metodologias não se somam: a soma dos níveis E–H fica **~2,5 p.p. acima** da inadimplência
de 90 dias. Separadas, a métrica do regime ECL fica a **0,34 p.p.** da série oficial.

O painel marca cada linha com `regime_contabil` e **não traça série contínua** entre os dois.

### 3.1 A quebra também atinge o crescimento

A mesma resolução trocou a conta do Resumo: **"Carteira de Crédito Classificada"** (até
202412) passou a **"Carteira de Crédito"** (2025+). Não é só o rótulo — é outra medida.
Verificado dentro do **mesmo** universo prudencial, sem troca de tipo:

| | 202412 | 202503 | variação num trimestre |
|---|---|---|---|
| Itaú | R$ 1.088,0 bi | R$ 1.187,8 bi | **+9,2%** |
| universo | R$ 7,57 tri | R$ 7,65 tri | +1,1% |

Um degrau de nível desse tamanho contamina toda comparação de 12 meses que o atravesse.
O efeito era visível e grave: a carteira exposta a risco de crescimento saltava para
**40,7%** entre 2025Q1 e 2025Q4, com Itaú, Bradesco e BNDES sinalizados como risco alto
de crescimento — o que é falso.

**Regra adotada:** todo indicador que compara `t` com `t−4` fica **vazio** nas data-bases
2025Q1 a 2025Q4 (`TRIMESTRES_CONTAMINADOS` em `src/indicadores.py`). Perde-se um ano de
P1; o alternativo seria publicar crescimento produzido pela mudança contábil. Após a
correção, a carteira exposta nesses trimestres cai para 1,4%–2,0%, e **2026Q1 — a
data-base padrão do painel — não é afetada**, porque suas duas pontas são pós-quebra.

Reprodução: `src/diagnostica_salto.py` e `src/checa_virada.py`.

### 3.2 Mínimo de indicadores por eixo

Anular as comparações anuais deixou P1 com **um** indicador (o credit gap) em 2025 — e o
score continuava sendo calculado sobre esse fragmento, sinalizando 32 a 46 instituições.
Um score feito de 1 de 6 indicadores não é a mesma medida que um feito de 6, e compará-los
no tempo é inválido.

**Regra:** o score de um eixo só existe se a instituição tiver ao menos **metade** dos
indicadores ativos daquele eixo, com piso de 2 (`FRACAO_MINIMA` e `MIN_INDICADORES` em
`src/scoring.py`). Abaixo disso o score fica vazio e a instituição não entra em contagem
nenhuma.

Consequências, todas honestas e antes ocultas:

| eixo | janela sem score | motivo |
|---|---|---|
| P1 · Crescimento | 2019Q1–2019Q4 | crescimento exige quatro trimestres anteriores |
| P1 · Crescimento | 2025Q1–2025Q4 | comparações anuais anuladas pela quebra da Res. 4.966 |
| P3 · Deterioração | 2019Q1–2024Q4 | quatro dos seis indicadores só existem no regime ECL |

A minissérie desenha **lacuna** nesses trechos, em vez de ligar os pontos: unir as pontas
inventaria uma queda e uma recuperação que não aconteceram. O delta de 12 meses também é
suprimido quando alguma das pontas cai numa lacuna.

### 3.3 Como as séries são exibidas

As três séries têm tamanhos diferentes — 21, 29 e 5 trimestres —, o que a linha original
escondia: normalizada para a mesma largura, uma série de 5 pontos parecia cobrir o mesmo
período de uma de 29. Duas mudanças resolveram:

**Barras, não linha.** Cada trimestre é uma barra medida a partir do zero. Trimestre sem
dado simplesmente não tem barra — a ausência fica legível sem legenda, e nada é
interpolado. A linha antiga, além de sugerir continuidade, usava autoescala: uma variação
de 0,1% a 0,4% ocupava a altura inteira do cartão, com o mesmo drama de uma de 0% a 40%.

**Barra de composição.** Acima da série, uma barra empilhada mostra como a carteira do
trimestre se reparte entre risco alto, atenção, baixo e sem dado. Ela está **sempre
completa**, porque descreve apenas o corte transversal corrente, e decompõe diretamente o
número de destaque. Em 2026Q1 ela revela algo que a série não mostrava: em deterioração,
**59% da carteira está em "atenção"** embora só 0,2% esteja em "risco alto".

Cada cartão declara a cobertura (`21 de 29 trimestres · 03/2020 a 03/2026 · máx. 7,9%`) e
traz, logo abaixo, a **justificativa** de por que a série é incompleta. O mesmo texto
abre a aba da pergunta correspondente, e é editável em `textos.toml`, seção `[series]`.

### 3.4 Sobre os degraus de P2

Os saltos da minissérie de concentração **não são erro de cálculo** — a cobertura dos
quatro indicadores é estável em toda a janela. São granulosidade: com 3 a 12 instituições
sinalizadas e ponderação por tamanho, uma única instituição grande move a série inteira.
O patamar de ~5% entre 2022Q3 e 2024Q4 é, essencialmente, **o BNDES** (R$ 325 bi) dentro
do conjunto sinalizado; ele sai na virada de universo de 2025 e a série volta a 0,8%.

---

## 4. Os 18 indicadores

Cada indicador é declarado uma única vez em **`src/catalogo.py`**, com rótulo, unidade,
sentido, fonte e fórmula. O catálogo tem **36 indicadores** (12 por eixo); **18 estão ativos**
(6 por pergunta) e os demais ficam disponíveis para troca.

### P1 — Crescimento
*Por que este eixo primeiro: é a variável-mestra do curso. O problema não é crescer, é crescer
por muito tempo, concentrado e com critérios frouxos.*

| # | Indicador | Fórmula | Fonte | Sentido |
|---|---|---|---|---|
| 1 | Crescimento real da carteira | `carteira_real(t) ÷ carteira_real(t−4) − 1` | IF.data · Resumo | maior = pior |
| 2 | Credit gap | ciclo do filtro HP (λ=1600) sobre `ln(carteira real)` | IF.data · Resumo | maior = pior |
| 3 | Trimestres seguidos > 15% | contagem consecutiva com crescimento real ≥ 15% a.a. | derivado de #1 | maior = pior |
| 4 | Carteira ÷ capital | `(1+cresc. carteira) ÷ (1+cresc. PR)` | IF.data · Informações de Capital | maior = pior |
| 5 | Crescimento em alto risco | variação 12m de (cartão + sem consignação) | IF.data · Carteira PF | maior = pior |
| 6 | Ganho de market share | `share(t) − share(t−4)`, em p.p. | IF.data · Resumo | maior = pior |

### P2 — Concentração
*Qualifica o risco: onde ele se concentra importa mais que o total.*

| # | Indicador | Fórmula | Fonte | Sentido |
|---|---|---|---|---|
| 1 | HHI do sistema | `Σ share² × 10.000` | IF.data · Resumo | contexto (sistema) |
| 2 | CR5 | share somado das 5 maiores | IF.data · Resumo | contexto (sistema) |
| 3 | Carteira PF em alto risco | `(cartão + sem consignação) ÷ total PF` | IF.data · Carteira PF | maior = pior |
| 4 | HHI regional | `Σ share_região² × 10.000` | IF.data · Região geográfica | maior = pior |
| 5 | Carteira PJ em grande porte | `PJ grande porte ÷ total PJ do mesmo relatório` | IF.data · Porte do tomador | maior = pior |
| 6 | Carteira ÷ captações | `carteira_real ÷ captações_real` | IF.data · Resumo | maior = pior |

### P3 — Deterioração
*Prioriza: qualidade da carteira frente ao ritmo de crescimento e à folga de capital.*

| # | Indicador | Fórmula | Fonte | Sentido |
|---|---|---|---|---|
| 1 | Inadimplência | `atraso 90+ ÷ carteira` | IF.data · Instrumentos financeiros | maior = pior |
| 2 | Cobertura de provisões | `provisão ÷ atraso` | IF.data · Ativo (Perda Esperada) | **menor = pior** |
| 3 | Provisão ÷ carteira | `provisão ÷ carteira` | IF.data · Ativo | **menor = pior** |
| 4 | Inadimplência ajustada | `atraso(t) ÷ carteira_real(t−4)` | IF.data | maior = pior |
| 5 | Ativos problemáticos | `problemáticos ÷ carteira` | IF.data · Instrumentos financeiros | maior = pior |
| 6 | Folga de capital | `Basileia × 100 − 10,5` | IF.data · Informações de Capital | **menor = pior** |

> **O indicador 4 é o coração do trabalho.** Ele ataca o **efeito denominador**: carteira
> que cresce rápido dilui `atraso ÷ carteira` e esconde perda futura. Usar a carteira de
> quatro trimestres antes mostra o atraso contra a base que de fato o originou.

---

## 5. Como os indicadores compõem o score

Quatro passos, todos verificáveis em `src/rastreia_cartao.py`:

**1. Grupo de pares.** Instituições do **mesmo TCB**, no mesmo trimestre. Percentil, e não
valor absoluto, porque 15% de crescimento significa coisas diferentes para o Itaú e para uma
cooperativa singular.

**2. Percentil.** Cada indicador vira um percentil (0 a 1) dentro do grupo. Indicadores de
sentido invertido (cobertura, folga de capital) entram como `1 − percentil`.

**3. Média.** O score do eixo é a média dos percentis disponíveis. **Dado ausente reduz o
divisor, não conta como zero.**

**4. Corte.** Score **≥ 0,75** marca a instituição como *risco alto* naquele eixo. A carteira
dela soma no número de destaque do cartão.

O **score final** pondera os três eixos (padrão 0,30 / 0,25 / 0,45, ajustável na barra
lateral), refletindo o encadeamento **P1 filtra → P2 qualifica → P3 prioriza**.

### Exemplo rastreado — Nu Pagamentos, 03/2026, eixo Crescimento

| indicador | valor | percentil |
|---|---|---|
| Crescimento real da carteira | 32,7% a.a. | 0,719 |
| Credit gap | *sem dado* | — |
| Trimestres seguidos > 15% | 1 | 0,740 |
| Carteira ÷ capital | 1,20× | 0,730 |
| Crescimento em alto risco | 34,1% a.a. | 0,698 |
| Ganho de market share | 0,413 p.p. | **1,000** |

`(0,719 + 0,740 + 0,730 + 0,698 + 1,000) ÷ 5 = 0,777` → **risco alto**.

Foram 5 e não 6 percentis: o credit gap exige 12 trimestres de série e o Nubank não tem.

### Dois indicadores não pontuam
**HHI do sistema** e **CR5** medem o mercado inteiro e têm valor idêntico para todas as
instituições do trimestre (confirmado: assumem **um único valor** no recorte). Ranquear por
um número igual para todas não faria sentido — eles são dois dos 18, mas definem o contexto,
não a posição. Por isso Concentração compõe seu score com **4 percentis**, não 6.

### O número de destaque dos cartões
Não é o score: é a **fatia da carteira do recorte em instituições sinalizadas** naquele eixo.
Motivo medido: percentil tem mediana 0,50 por construção, e a mediana dos scores variou
apenas **0,037** em 29 trimestres no eixo Concentração. Já a carteira exposta variou de **7%
a 43%** e pondera por tamanho (`src/diagnostica_score.py`).

---

## 6. Duas agendas, porque são duas perguntas

O score mede **atipicidade dentro do grupo de pares** — que não é relevância sistêmica. Com
uma lista única, os cinco maiores bancos do país ficavam entre a 548ª e a 1046ª posição e a
agenda cobria 1% da carteira (`src/diagnostica_agenda.py`).

| lista | critério | cobertura |
|---|---|---|
| **Atípicas no grupo de pares** | score ≥ limiar (padrão 0,65) e carteira ≥ R$ 1 bi | 21 IFs · 0,8% da carteira |
| **Grandes com sinal** | as maiores que somam 80% da carteira | 14 IFs · 82,2% da carteira |

Juntas: 35 instituições, 83% da carteira, **sem sobreposição**.

---

## 7. Troca de indicador ao vivo

O painel calcula **todos os 36** indicadores do catálogo e os guarda na base. Trocar um
indicador **não recalcula nada** — muda apenas quais colunas alimentam o score.

**Na apresentação:** barra lateral → *Trocar indicadores* → *Escolher os 6 de cada pergunta*.
A troca é imediata e propaga para cartões, agenda, glossário e comparador.

**Para fixar:** editar `indicadores.toml` na raiz. O painel recusa lista com tamanho
diferente de 6 e avisa na tela, preservando a regra do trabalho.

Alternativas disponíveis, por eixo (6 cada):

| eixo | alternativas |
|---|---|
| P1 | crescimento do ativo · das captações · do nº de clientes · da carteira PJ · aceleração · crescimento do ticket médio |
| P2 | HHI de modalidades PF · maior região · crédito ÷ ativo · ticket médio · PJ em capital de giro · HHI de porte |
| P3 | folga de capital principal · razão de alavancagem · distância problemático−inadimplência · problemáticos ÷ PL · variação da inadimplência · retorno sobre PL |

`src/testa_troca.py` demonstra o mecanismo: trocando 3 indicadores, a agenda passou de 21
para 34 instituições (14 entradas, 1 saída).

---

## 8. Verificação — como conferir

| script | o que garante | resultado |
|---|---|---|
| `testa_extracao.py` | decodificação bate com a tela oficial do IF.data | **validado** |
| `valida_cruzada.py` | inadimplência × SGS 21082 | **0,34 p.p.** |
| `audita_raw.py` | integridade dos brutos | **950 arquivos, 0 inválidos** |
| `checa_catalogo.py` | todo indicador existe e há 6 por eixo | **OK** |
| `checa_dependencias.py` | app só importa o declarado no requirements | **OK** |
| `testa_app.py` | painel não quebra em nenhum trimestre | **29/29** |
| `checa_app_colunas.py` | regra dos 6 por pergunta | **6/6/6** |
| `rastreia_cartao.py` | cálculo passo a passo numa IF real | reprodutível |
| `diagnostica_agenda.py` / `diagnostica_score.py` | por que duas listas e por que o destaque mudou | reprodutível |

**Manifesto de coleta:** `data_raw/manifesto_coleta.csv` — 973 arquivos com URL, data/hora
de extração e SHA-256.

---

## 9. O que este painel não permite concluir

Está na aba *Visão geral* do painel e em `textos.toml`. Em resumo: não identifica tomador
nem safra; não mede concentração em poucos devedores; não compara 2024 com 2025 em qualidade
de crédito; não afirma irregularidade nem insolvência; não enxerga fora do balanço; não
permite leitura regional de longo prazo; a carteira do IF.data não é a do SGS; e os dados
estão sujeitos a reapresentação.

Acrescente-se: **o score não mede relevância sistêmica**, e scores de grupos de pares
diferentes não são diretamente comparáveis entre si.
