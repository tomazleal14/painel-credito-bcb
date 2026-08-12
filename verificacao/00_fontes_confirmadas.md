# Nota de verificação mestre — fontes, endpoints e travas

**Projeto:** Painel decisório de crédito — persona Supervisão do BCB (FGV / Prof. Genaro Lins)
**Data de confirmação das fontes:** 12/08/2026 (UTC)
**Regra:** nenhum número entra no painel sem uma linha correspondente em
`data_raw/manifesto_coleta.csv` (URL, data/hora de extração, SHA-256, bytes).

---

## 1. Como cada fonte foi confirmada

### 1.1 SGS — Sistema Gerenciador de Séries Temporais

O risco nº 5 da proposta ("o LLM acerta um número plausível de uma série que não existe")
foi tratado com uma **trava de catálogo**: antes de baixar qualquer série, o coletor lê o
nome oficial no catálogo do BCB e compara com o nome que o projeto espera. Divergiu, a série
é marcada `A CONFIRMAR` e **não é baixada**.

| item | valor |
|---|---|
| Endpoint de catálogo | `https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS?method=getUltimoValorXML&codigoSerie={cod}` |
| Devolve | `<NOME>`, `<PERIODICIDADE>`, `<UNIDADE>` oficiais |
| Endpoint de dados | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados?formato=json&dataInicial=01/01/2015` |
| Script | `src/coleta_sgs.py` (trava), `src/valida_sgs.ps1` e `src/varre_catalogo_sgs.ps1` (descoberta) |
| Resultado | **14 de 14 séries CONFIRMADAS** — `data_processed/catalogo_series_sgs.csv` |

Os códigos **não foram escolhidos de memória**. Varreram-se as faixas do bloco de crédito do
SGS (20539–20900, 21082–21150, 21255–21310, 25400–25420) lendo o nome oficial de cada código;
**424 séries** foram catalogadas em `data_raw/sgs/catalogo/varredura_sgs.csv` e os códigos
usados saíram dessa lista, por nome.

> **Prova de que a trava funciona:** o código 1737, testado na varredura, devolveu nome vazio
> (série inexistente) e foi descartado. As faixas 25400–25420 (endividamento/comprometimento
> de renda das famílias) **não retornaram nenhuma série** — por isso esses indicadores
> **não** entram no painel, em vez de receberem um código chutado.

### 1.2 IF.data — base central (por instituição, trimestral)

A API OData documentada (`olinda.bcb.gov.br/olinda/servico/IFDATA`) responde ao catálogo
(`ListaDeRelatorio`) mas retorna **HTTP 500 "Erro desconhecido"** em toda chamada de dados
(`IfDataValores`, `IfDataCadastro`), testada em vários períodos e nas duas sintaxes de
parâmetro em 12/08/2026. **Não foi usada.**

Em seu lugar usa-se o mesmo backend que a interface pública consome, confirmado por inspeção
de rede em `https://www3.bcb.gov.br/ifdata/`:

| item | valor |
|---|---|
| Índice de períodos | `GET /ifdata/rest/relatorios2000a2024` e `/ifdata/rest/relatorios2025a2030` |
| Arquivo | `GET /ifdata/rest/arquivos?nomeArquivo={caminho}` |
| Períodos publicados | **105** (200003 … 202603) |
| Período coletado | **201903 … 202603** (29 trimestres) |
| Script | `src/coleta_ifdata.py` |

**Estrutura dos arquivos (engenharia reversa documentada):**

| arquivo | conteúdo |
|---|---|
| `info{AAAAMM}.json` | dicionário de campos: `id`, `n` (nome PT), `ni` (nome EN), **`d` = fórmula COSIF**, `lid` (chave de junção nos dados), `ty` |
| `trel{AAAAMM}_{id}.json` | definição do relatório: `n` (nome), `s[].id` (tipo de instituição), `c[].ifd` (id da coluna → `info.id`), `cp` (legenda/unidade), `ge` (data de geração) |
| `cadastro{AAAAMM}_{tipo}.json` | cadastro das IFs: `c0`=código, `c2`=nome, `c3`=TCB, `c7`=controle, `c10`=UF, `c11`=município, `c12`=segmento SR |
| `dados{AAAAMM}_{n}.json` | valores esparsos: `{id, values:[{e=código da IF, v:[{i=info.lid, v=valor}]}]}` |

**Unidades — verificadas, não presumidas.** A legenda do relatório diz "Valores monetários em
R$ mil", mas **o JSON bruto está em R$ (unidades)**: a interface divide por 1.000 na exibição.
Índices (Basileia, imobilização) vêm como **fração decimal**.

**Prova de ponta a ponta** (`src/testa_extracao.py`, executável e reprodutível) — compara o
valor decodificado com o que a tela oficial exibe, para ITAU-PRUDENCIAL, 03/2026, Resumo:

| campo | bruto no JSON | após transformação | tela oficial | resultado |
|---|---|---|---|---|
| Ativo Total | 2.834.355.732.183,17 | 2.834.355.732 (R$ mil) | 2.834.355.732 | **OK** |
| Carteira de Crédito | 1.221.119.970.501,64 | 1.221.119.971 (R$ mil) | 1.221.119.971 | **OK** |
| Índice de Basileia | 0,147697088305565 | 14,77 % | 14,77 % | **OK** |

### 1.3 SCR agregado

| item | valor |
|---|---|
| Endpoint (painel SCR.data) | `https://www.bcb.gov.br/api/servico/sitebcb/sistemainformacaocredito?dataIn=&dataFim=&uf_filtro=&modalidade_filtro=&cliente_filtro=…` |
| Dimensões | `…/sistemainformacaocredito_{modalidade,porte,indexador,cnae_ocupacao}` |
| Campos | `data_base`, `carteira_ativa` (R$ unidades), `inadimplencia` (%), **`ativo_problematico` (%)** |
| Coletado | 201501 … 202606, 8 modalidades × 3 recortes de cliente = 2.346 linhas |
| Script | `src/coleta_scr.py` |

Existe também o serviço OData `scr_sub_regiao` (com classificação de risco AA–H), porém com
dados **apenas até 202412** — ver a quebra estrutural na seção 3.

**Papel no painel:** o SCR agregado **não identifica a instituição**. Entra exclusivamente como
*referência de sistema* contra a qual as IFs do IF.data são comparadas.

### 1.4 ESTBAN

| item | valor |
|---|---|
| Endpoint | `https://www.bcb.gov.br/content/estatisticas/estatistica_bancaria_estban/municipio/{AAAAMM}_ESTBAN.csv.zip` |
| Como foi obtido | captura do `href` do botão "Baixar arquivo" da página oficial (a página é SPA; não há link estático) |
| Coletado | 202510 … 202603 (6 datas-base), 48.185 linhas, 55 colunas |
| Identifica a IF? | **Sim** — traz `CNPJ` e `NOME_INSTITUICAO` por município |
| Script | `src/coleta_estban.py` |

**Limite declarado pela própria fonte:** *"Sua atualização é mensal, e abrange os últimos 6
(seis) meses publicados."* O ESTBAN, por este endpoint, **não permite série longa** — entra
como corte transversal de concentração regional. O recorte por agência
(`…/agencia/{AAAAMM}_ESTBAN.csv.zip`) retorna **404** e não foi usado.

**Escopo:** bancos comerciais e bancos múltiplos com carteira comercial (documento 4500).
**Não cobre todo o SFN** e portanto não é diretamente comparável ao universo do IF.data.

### 1.5 Deflator

IPCA, **SGS 433**, unidade "Var. % mensal". O número-índice é construído por acumulação e a
base é a última data-base do painel (**202603**). Detalhes e limites em
`verificacao/00_deflator_ipca.md`.

---

## 2. Universo do painel — decisão explícita

O risco nº 3 da proposta é "denominador/recorte trocado". O universo fica **fixado e declarado**:

| dimensão | escolha |
|---|---|
| Tipo de instituição | **1009 — Conglomerados Prudenciais e Instituições Independentes** (2025+) / **1005 — Conglomerados Financeiros e Instituições Independentes** (até 2024) |
| Denominador de *market share* e HHI | **Carteira de Crédito** do relatório Resumo (não Ativo Total, não crédito livre) |
| Periodicidade | trimestral (datas-base 03, 06, 09, 12) |
| Janela | 201903 … 202603 |

> **Ressalva obrigatória:** o tipo 1009 só existe a partir de **202309**. A série longa exige
> o tipo 1005. Os dois universos **não são idênticos** (conglomerado prudencial inclui
> entidades não financeiras do grupo). Toda comparação que cruze 202312→202503 precisa
> declarar isso — está registrado na seção "o que o painel NÃO permite concluir".

---

## 3. Quebras estruturais encontradas (achado de coleta, não de literatura)

**Resolução CMN 4.966/2021, vigente desde 01/01/2025**, substituiu o modelo de provisionamento
por classificação de risco AA–H pelo de **perda esperada (ECL)**. Isso aparece nos dados:

| evidência | observação |
|---|---|
| IF.data, relatório "Carteira de crédito ativa — por nível de risco da operação" | presente até **202412**; **ausente** de 202503 em diante |
| IF.data, relatório "Carteira de crédito ativa — por carteiras de instrumentos financeiros" | **novo**, aparece em 2025+ |
| SCR `scr_sub_regiao` (com campo `RISCO` AA–H) | devolve dados até **202412**; **vazio** em 202506 e 202512 |
| Relatórios de crédito do IF.data | publicados sob tipo **1005** até 202412 e sob tipo **1009** em 2025+ |

**Consequência para P3:** o índice de cobertura baseado em provisão AA–H **não é calculável de
forma homogênea** ao longo de toda a janela. O painel precisa tratar 202412 como ponto de
corte e **não** encadear as duas metodologias numa única série contínua.

---

## 4. Pendências registradas (campos que ficam VAZIOS)

| item | situação |
|---|---|
| Endividamento / comprometimento de renda das famílias | nenhuma série encontrada nas faixas varridas — **não usado** |
| ESTBAN por agência | endpoint retorna 404 — **não usado** |
| ESTBAN série longa | fonte publica só 6 meses — **corte transversal apenas** |
| Concentração em grandes tomadores (P2 nº 5) | o SCR agregado publicado **não traz** exposição por tomador; ver `01_mapa_indicadores.md` para a proxy adotada e sua limitação |
| API OData oficial do IF.data | HTTP 500 na data de coleta — **não usada** (backend público equivalente no lugar) |
