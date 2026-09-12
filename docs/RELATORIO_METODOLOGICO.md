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

São 14 os indicadores anulados nesses quatro trimestres, e o mascaramento apaga 5.514
linhas de comparação anual.

**O credit gap também entra na lista, embora não seja uma razão `t/t−4`.** O filtro
Hodrick-Prescott (λ = 1600) é ajustado sobre o **nível** da carteira, que é exatamente
onde está o degrau de definição. Um salto de +9,2% num trimestre entra na estimativa da
tendência e o hiato resultante mede a mudança contábil, não o ciclo de crédito — a
tendência suavizada não acompanha o degrau, então o nível pós-quebra aparece como hiato
positivo grande. Por isso `p1_2_credit_gap` está em `COMPARAM_COM_T4` apesar do nome da
constante. Efeito: a série do credit gap cai de 29 para 25 trimestres, e a série de
crescimento da Visão geral passa a exibir **21 de 29 trimestres, 03/2020 a 03/2026**, com
2025 vazio.

### Por que não compatibilizar os regimes — as três vias testadas

A pergunta é legítima e vai ser feita: *por que jogar fora um ano de P1 em vez de
encadear as séries?* A resposta está medida em `src/avalia_ponte.py`, e são **duas**
descontinuidades — a primeira tem solução, a segunda não.

**A identidade tem solução, e ela é oficial.** O `cod_inst` muda (Itaú é `10069` no 1005 e
`1000080099` no 1009), mas o próprio cadastro do IF.data declara o vínculo nos campos
`c15` (código do conglomerado prudencial) e `c22` (nome). A regra
`"1000" + int(c15).zfill(6)` acerta 8 de 8 nos maiores e 629 de 638 vínculos.
`src/crosswalk.py` monta essa ponte nas 29 data-bases, e ela é **validada contra o dado
oficial**: em 202309–202412 os dois universos coexistem com a carteira contábil, e somar
as entidades 1005 vinculadas reproduz o valor 1009 publicado com **erro mediano de
0,000%** (3% dos conglomerados ficam fora da tolerância de 1%, porque o escopo prudencial
consolida entidades que não publicam no 1005). Ou seja: **não falta com quem comparar.**

**A medida não tem solução.** Três vias, todas descartadas por evidência:

| via testada | resultado |
|---|---|
| Ajustar o degrau por um fator comum | **Não.** No prudencial, com os mesmos códigos, o IQR da variação trimestral abre de 8,6 para 13,9 p.p. (**1,62×**) e o p05 vai de −16,0% para −33,3%. O efeito é idiossincrático — cada instituição se move para um lado. |
| Usar "Operações de Crédito (d1)" do Ativo, que existe nos dois regimes | **Não.** Ela mudou de significado: em 2025 vale exatamente `e1 − \|e2\|` (bruto menos perda esperada). A identidade fecha em **1,0000** do p25 ao p75, nas 1.059 instituições. Era bruta, virou líquida. |
| Usar a família "Carteira de crédito ativa" (base SCR) | **Não.** Até 202412 a razão `reg_total ÷ carteira_credito` é **1,0000** do p25 ao p75, em todas as data-bases: os dois relatórios publicam o **mesmo número**. A carteira ativa só vira conceito próprio em 202503 (razão 1,036) — ou seja, depois da quebra, quando já não serve de ponte para trás. |

A terceira via merece um aviso, porque **quase nos enganou**. Comparada só nas
instituições cujo código não mudou — os independentes —, `reg_total` parece atravessar a
quebra sem degrau (mediana +0,6%, dispersão *encolhendo*). Mas essas são exatamente a
subamostra em que a quebra de identidade nunca existiu, e os grandes bancos ficam de fora
dela por construção. O teste correto é a razão contra a carteira do Resumo **dentro do
mesmo trimestre**, e ele mostra que não há fonte independente antes de 2025.

**Conclusão.** O crescimento de 2025 *seria calculável* — o pareamento existe e é oficial.
O que ele mediria é que é o problema: é exatamente esse pareamento correto que produz o
Itaú a +9,2% num trimestre. A máscara existe porque a comparação é **tecnicamente possível
e economicamente sem sentido**, e porque nenhuma das três vias de compatibilização
sobrevive ao teste.

Reprodução: `src/avalia_ponte.py` e `src/crosswalk.py`.

**Contaminação de segunda ordem.** A máscara geral roda no fim de `calcula()`, o que basta
para os indicadores que são eles próprios uma razão `t/t−4`. Não bastava para dois que se
*apoiam* no crescimento:

- **`p1_3` (trimestres seguidos acima de 15%)** contava a sequência sobre o crescimento
  ainda contaminado. A sequência atravessava 2025 e chegava a 2026Q1 inflada: o máximo do
  recorte ia de **20** trimestres em 202412 para **25** em 202603 — somando os quatro
  trimestres que o painel declara não saber medir.
- **`p1_11` (aceleração)** é `cresc(t) − cresc(t−4)`; em 202603 o `t−4` é 202503, que não
  existe.

Corrigido movendo a máscara das colunas de crescimento para **antes** das derivações. A
sequência agora **reinicia na lacuna** (máximo 1 em 202603) e `p1_11` nasce vazia. Efeito
na seleção: a carteira exposta em crescimento passa de 7,2% para **7,5%** em 03/2026, com
as mesmas 54 instituições; o corte de 0,80 vai de 35 para 31.

Reprodução: `src/diagnostica_salto.py`, `src/checa_virada.py` e `src/checa_serie_cartao.py`.

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

### 3.2b O score não tem o mesmo tamanho em todos os trimestres

Os seis indicadores de uma pergunta **não começam juntos**. Em P1:

| indicador de P1 | trimestres | período |
|---|---|---|
| Crescimento real a.a. | 21 | 03/2020 – 03/2026 |
| Credit gap | 25 | 03/2020 – 03/2026 |
| Trimestres consecutivos > 15% | 25 | 03/2019 – 03/2026 |
| **Carteira ÷ capital** | **3** | 09/2024, 12/2024, 03/2026 |
| Crescimento do alto risco a.a. | 21 | 03/2020 – 03/2026 |
| Ganho de market share | 21 | 03/2020 – 03/2026 |

**Por que carteira ÷ capital tem só 3 trimestres.** O denominador é o Patrimônio de
Referência, que só existe no relatório **Informações de Capital**, publicado no tipo 1009
a partir de **2023Q3**. O indicador é um *crescimento* da razão, então precisa de mais
quatro trimestres anteriores: o primeiro valor possível é 2024Q3. Dos cinco trimestres
seguintes, 2025Q1–2025Q4 caem na máscara da Res. 4.966 (§3.1). Sobram 2024Q3, 2024Q4 e
2026Q1. Não é dado faltante nem erro de extração — é a idade da própria série na fonte.

**A consequência tem que ser lida junto com a série.** Como o score de um eixo é a média
dos percentis **disponíveis**, o número de indicadores que o sustenta muda ao longo do
tempo:

| janela | indicadores disponíveis | score de P1 |
|---|---|---|
| 2019Q1–2019Q4 | 2 (credit gap, trimestres seguidos) | **não existe** — abaixo do mínimo de 3 |
| 2020Q1–2024Q2 | 5 | média de 5 percentis |
| 2024Q3–2024Q4 | 6 | média de 6 percentis |
| 2025Q1–2025Q4 | 0 | **não existe** — máscara da Res. 4.966 |
| 2026Q1 | 6 | média de 6 percentis |

A entrada de carteira ÷ capital em 2024Q3 é, portanto, um **degrau de composição**: o
score muda de tamanho, não de risco. Quem lê a minissérie de P1 como uma trajetória
contínua de risco lê errado nesse ponto — e é por isso que o painel declara
explicitamente, em cada página de pergunta, o expander **"Cobertura de cada indicador · o
score deste eixo usa 5/6 indicadores conforme o trimestre"**, com a tabela acima, a regra
do mínimo e a justificativa por indicador (`textos.toml`, seção `[series_indicador]`).

Reprodução: `src/checa_cobertura_ind.py --eixo crescimento` (idem para `concentracao` e
`deterioracao`).

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

### 3.4 P2 tem série completa e mesmo assim tem quebra estrutural — por quê

Este é o caso que mais engana, porque as duas afirmações são verdadeiras ao mesmo tempo:
a série de concentração cobre **29 de 29 trimestres** (03/2019 a 03/2026, sem lacuna) e,
ainda assim, o gráfico da Visão geral tem um patamar visível entre 2022Q3 e 2024Q4. Não é
contradição, e **não é erro de cálculo** — a cobertura dos indicadores de P2 é estável em
toda a janela (o expander de cobertura mostra o **mesmo número de indicadores em todos os
trimestres**, sem o degrau de composição que P1 e P3 têm).

A explicação é de **granulosidade do conjunto sinalizado**, não da série. O número de
destaque é *carteira exposta*: a soma da carteira das instituições sinalizadas, sobre a
carteira do recorte. Com apenas 3 a 12 instituições sinalizadas em concentração, **uma
única instituição grande entrando ou saindo move a série inteira**. O patamar de ~5% é,
essencialmente, **o BNDES**:

| data-base | score P2 do BNDES | semáforo | o que mudou | carteira exposta |
|---|---|---|---|---|
| 2022Q2 | 0,600 | médio | carteira ÷ captações em 1,10× (percentil 0,500) | 0,7% |
| 2022Q3 | **0,750** | **alto** | razão sobe a 1,18× → percentil 0,500 **→ 1,000** | **5,5%** |
| 2025Q1 | 0,600 | médio | percentil da razão cai a 0,250 | 0,6% |

Três leituras que precisam ficar juntas:

1. **O degrau é do numerador, não do denominador.** Os R$ 325 bi de carteira do BNDES
   sozinhos explicam a passagem de 0,7% para 5,4%. Nada aconteceu com as outras
   instituições nem com a definição da série.
2. **O que moveu o score foi um percentil, e um só.** A razão carteira ÷ captações passou
   de 1,10× para 1,18× — variação pequena no indicador, mas suficiente para levar o BNDES
   ao topo do seu grupo de pares. O percentil é **posição relativa**, e uma posição pode
   saltar de 0,50 para 1,00 com um movimento marginal quando o grupo é apertado.
3. **O score do BNDES foi calculado sobre 3 indicadores válidos, não 6** (ele não tem
   carteira PF, o que zera os indicadores de composição PF). Está acima do mínimo de
   metade exigido em §3.2, então é um score legítimo — mas é um score estreito, e a média
   de 3 percentis é mais volátil que a de 6.

Ou seja: a quebra de 2022–2025 em P2 é **quebra de composição do conjunto sinalizado**,
não quebra contábil (§3.1) nem quebra de cobertura (§3.2b). Por isso o texto de P2 em
`textos.toml` diz "**Série completa**, mas com um degrau" — a série está inteira; o que
muda é *quem* ela está somando. Este é também o argumento para ler a Visão geral como
mapa de atenção e a agenda como decisão: um patamar de carteira exposta que depende de uma
instituição não é um fato sobre o sistema.

Reprodução: `src/diagnostica_score.py` e `src/checa_cobertura_ind.py --eixo concentracao`.

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
| 1 | Crédito ÷ ativo total | `carteira ÷ ativo total` | IF.data · Resumo | maior = pior |
| 2 | HHI de modalidades PF | `Σ share_modalidade² × 10.000` | IF.data · Carteira PF (7 modalidades) | maior = pior |
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

### O corte de 0,75 é escolha nossa, e é ajustável

São **dois** cortes diferentes, e confundi-los é fácil:

| | valor | onde | o que decide | ajustável |
|---|---|---|---|---|
| `CORTE_ALTO` | 0,75 | `src/scoring.py` + barra lateral | quem é *risco alto* **em cada eixo** | **sim** |
| `LIMIAR_AGENDA` | 0,65 | `src/scoring.py` + barra lateral | quem entra na **agenda**, pelo score final | **sim** |

0,75 é o **quartil superior** do grupo de pares. Não vem de norma nem de estimação: é
convenção de triagem, e a defesa dela é que seleciona um conjunto pequeno o bastante para
caber num ciclo de supervisão. Por ser arbitrária, tem que ser movível na frente de quem
discorda — `src/testa_corte.py` mede o efeito, em 03/2026:

| corte | Crescimento | Concentração | Deterioração |
|---|---|---|---|
| 0,65 | 82 IFs · 10,5% | 26 IFs · 1,9% | 50 IFs · 2,6% |
| 0,70 | 69 IFs · 9,1% | 13 IFs · 1,0% | 26 IFs · 1,2% |
| **0,75** | **54 IFs · 7,5%** | **7 IFs · 0,8%** | **10 IFs · 0,2%** |
| 0,80 | 31 IFs · 2,7% | 3 IFs · 0,4% | 3 IFs · 0,1% |
| 0,85 | 19 IFs · 0,8% | 1 IF · 0,0% | 0 IFs · 0,0% |

O mesmo script trava a **monotonicidade**: baixar o corte nunca pode reduzir o número de
sinalizadas nem a carteira exposta. Se reduzisse, o semáforo estaria invertido em algum
ponto.

Repare na sensibilidade assimétrica: em Deterioração, sair de 0,75 para 0,70 vai de 10 para
26 instituições — mais que dobra. Em Crescimento, o mesmo movimento vai de 54 para 69. O
corte é mais decisivo onde a distribuição de scores é mais densa, e isso é argumento para
mostrá-lo ajustável em vez de defender um número.

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

### HHI e CR5 saíram dos 18 e viraram contexto do sistema

**HHI do sistema** e **CR5** medem o mercado inteiro: no recorte de 03/2026 assumem **um
único valor** para as 258 instituições (951 e 64,8%). Ranquear instituições por um número
igual para todas não diz nada, e por isso o escopo `sistema` do catálogo sempre os excluiu
do percentil.

Até 09/2026 eles ocupavam duas das seis vagas de P2 mesmo assim, com três consequências
ruins: **(i)** Concentração pontuava com **4 percentis** enquanto P1 e P3 pontuavam com 6
— base mais estreita e mais volátil, que é o que produz saltos como o do BNDES; **(ii)** o
cartão deles era degenerado — sem dispersão, o gráfico de distribuição fabricava um teto
de escala, e o eixo do CR5 chegava a exibir **129,6%**, impossível por definição; **(iii)**
o par "sinalizadas × recorte" mostrava o mesmo número duas vezes.

Agora os dois aparecem como **faixa de contexto no topo da página de P2**, lidos contra os
limiares de referência (HHI abaixo de 1.500 desconcentrado, 1.500–2.500 moderado, acima
concentrado) — que é o que dá sentido a um número de sistema, já que ele não tem posição
relativa. Continuam também nas métricas do topo da Visão geral.

As duas vagas foram para **Crédito ÷ ativo total** (cobertura integral, 258 de 258, e mede
uma dimensão que P2 não tinha: quanto do balanço está exposto a crédito) e **HHI de
modalidades PF** (concentração de produto, complementando o % em alto risco PF sem
duplicá-lo). Evitaram-se "Maior região" e "HHI de porte do tomador", redundantes com o HHI
regional e com o % em grande porte, já presentes.

Efeito na seleção em 03/2026, com o corte padrão: Concentração passa de 7 para **6**
instituições sinalizadas, e a carteira exposta de 0,8% para **0,5%**. Os três eixos passam
a pontuar com 6.

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
