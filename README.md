# Painel decisório de crédito — Supervisão do Banco Central

Trabalho Intermediário · FGV / Prof. Genaro Lins
**Pergunta:** quais instituições devem entrar na agenda de supervisão do próximo ciclo, dado o
perfil de **crescimento**, **concentração** e **potencial de deterioração** da carteira?

## Estado atual — todas as etapas concluídas

| etapa | situação |
|---|---|
| 1. 18 indicadores mapeados | `verificacao/01_mapa_indicadores.md` |
| 2. Códigos/endpoints confirmados | `verificacao/00_fontes_confirmadas.md` |
| 3. Estrutura do projeto | `data_raw` · `data_processed` · `src` · `verificacao` |
| 4. Deflacionamento por IPCA | `verificacao/00_deflator_ipca.md` |
| 5. Tema e estrutura definidos | 4 abas · grade 2×2 · claro · azul-petróleo |
| 6. App Streamlit | `app.py` — tema isolado em `src/tema.py` |
| 7. Gráfico-assinatura de P3 | aba P3, com o quadrante de agenda destacado |
| 8. "O que o painel NÃO permite concluir" | `src/textos.py`, exibido na Visão geral |

## Rodar o painel

```bash
.venv/Scripts/streamlit.exe run app.py
```

## Reproduzir os dados do zero

```bash
.venv/Scripts/python.exe src/coleta_sgs.py        # SGS (valida catalogo antes de baixar)
.venv/Scripts/python.exe src/coleta_ifdata.py     # IF.data 201903..202603
.venv/Scripts/python.exe src/coleta_scr.py        # SCR agregado
.venv/Scripts/python.exe src/coleta_estban.py     # ESTBAN (ultimos 6 meses)
.venv/Scripts/python.exe src/audita_raw.py        # integridade dos brutos
.venv/Scripts/python.exe src/deflator.py          # deflator IPCA
.venv/Scripts/python.exe src/constroi_base.py     # paineis processados
.venv/Scripts/python.exe src/indicadores.py       # os 18 indicadores
.venv/Scripts/python.exe src/prepara_deploy.py    # versao enxuta para o Cloud (4 MB)
```

## Conferir (tudo reexecutável)

```bash
.venv/Scripts/python.exe src/testa_extracao.py     # reproduz a tela oficial do IF.data
.venv/Scripts/python.exe src/valida_cruzada.py     # confronta com SGS e SCR
.venv/Scripts/python.exe src/audita_raw.py         # 950 arquivos, 0 invalidos
.venv/Scripts/python.exe src/testa_app.py          # o painel em todos os 29 trimestres
.venv/Scripts/python.exe src/checa_app_colunas.py  # regra dos 6 indicadores por pergunta
.venv/Scripts/python.exe src/checa_sinais.py       # sinal das contas retificadoras
.venv/Scripts/python.exe src/checa_p2_5.py         # cobertura do indicador P2 nº 5
.venv/Scripts/python.exe src/gera_notas.py         # uma nota de verificacao por indicador
.venv/Scripts/python.exe src/mostra_agenda.py      # a agenda de supervisao no terminal
```

## Publicar no Streamlit Community Cloud

O repositório versionado tem **4,6 MB** (69 arquivos): os brutos e os painéis largos ficam
fora, porque são reproduzíveis pelos scripts acima. O que o app lê é
`data_processed/app_indicadores.parquet` (4 MB). O manifesto de coleta e os XML do catálogo
SGS **continuam versionados** — a rastreabilidade não depende de guardar os blobs.

1. `git init && git add . && git commit -m "painel de supervisão de crédito"`
2. Subir para um repositório no GitHub.
3. Em share.streamlit.io, apontar para o repositório, arquivo principal `app.py`.

## Estrutura

```
data_raw/          arquivos originais, intocados  + manifesto_coleta.csv (URL, hora, SHA-256)
data_processed/    derivados (paineis, indicadores, dicionario de campos, deflator)
src/               coleta, transformacao e calculo
verificacao/       uma nota por fonte/indicador
```

## Travas de rastreabilidade

1. **Catálogo antes do dado.** Nenhuma série SGS é baixada antes de o nome oficial ser lido do
   catálogo do BCB e conferido. 14/14 confirmadas.
2. **Manifesto.** Todo arquivo bruto tem URL, data/hora de extração, SHA-256 e tamanho.
3. **Prova de decodificação.** `src/testa_extracao.py` reproduz, dígito a dígito, três valores
   exibidos na tela oficial do IF.data.
4. **Auditoria de integridade.** `src/audita_raw.py` — 941 arquivos, 0 inválidos.
5. **Validação cruzada.** `src/valida_cruzada.py` — confronto com SGS e SCR.
6. **Pendência é campo vazio.** O que não foi confirmado fica vazio e registrado, nunca estimado.

## Fontes

BCB/SGS · BCB/IF.data · BCB/SCR.data · BCB/ESTBAN. Data de confirmação: **12/08/2026**.
