"""
gera_notas.py -- gera UMA NOTA DE VERIFICACAO POR INDICADOR em verificacao/.

Cada nota e montada a partir dos artefatos reais da coleta -- nao de texto digitado:
  - fonte, endpoint e data de extracao vem de data_raw/manifesto_coleta.csv
  - o SHA-256 do arquivo bruto vem do mesmo manifesto
  - a formula COSIF e a unidade vem de data_processed/dicionario_campos_ifdata.parquet
  - a cobertura (% de linhas preenchidas) e medida no proprio painel de indicadores
Assim a nota nao pode divergir do dado: ela e derivada dele.
"""
from __future__ import annotations

import pandas as pd

import catalogo
from comum import DATA_PROC, DATA_RAW, VERIFICACAO, agora_utc

# indicador -> (pergunta, titulo, campos de origem, formula, referencia, fonte principal)
# As fichas sao DERIVADAS do catalogo (src/catalogo.py), para nao existir uma segunda
# lista de indicadores no projeto. Assim, qualquer indicador que entre numa troca ao
# vivo ja nasce com nota de verificacao.
FICHAS = {
    ind.chave: (
        {"crescimento": "P1", "concentracao": "P2", "deterioracao": "P3"}[ind.eixo],
        ind.rotulo,
        [],                      # campos de origem: descritos na propria formula
        ind.formula,
        ind.nota or "ver o glossario do painel",
        ind.fonte,
    )
    for ind in catalogo.CATALOGO
}

ROTULO = {
    "carteira_credito": "carteira de cr", "pr": "patrim",
    "captacoes": "capta", "qtd_clientes": "quantidade de clientes",
    "perda_esperada": "perda esperada", "provisao_antiga": "provis",
    "inadimplencia_valor": "inadimpl", "ativos_problematicos_valor": "problem",
    "indice_basileia": "basileia", "pj_porte_grande": "grande",
    "pj_total_porte": "total da carteira de pessoa jur",
}

# O deflator so muda o resultado quando o indicador COMPARA PERIODOS. Numa razao entre
# dois valores da MESMA data-base o fator de deflacionamento aparece no numerador e no
# denominador e se cancela -- dizer que "foi deflacionado" ali seria impreciso.
DEFLATOR_ESSENCIAL = {
    "p1_1_cresc_real_aa", "p1_2_credit_gap", "p1_3_trim_consec_acima",
    "p1_4_cresc_carteira_sobre_capital", "p1_5_cresc_alto_risco_aa",
    "p1_6_var_share_pp", "p3_4_inadimplencia_ajustada",
}
TEXTO_DEFLATOR_ESSENCIAL = (
    "**Essencial.** IPCA, SGS 433 — o indicador compara períodos, então valores nominais "
    "inflariam o resultado. Valores reais em R$ de 03/2026 (ver `00_deflator_ipca.md`).")
TEXTO_DEFLATOR_CANCELA = (
    "**Não altera o resultado.** É uma razão entre valores da mesma data-base: o fator do "
    "IPCA aparece no numerador e no denominador e se cancela. O cálculo usa as colunas "
    "`_real` por consistência, mas o número seria idêntico em termos nominais.")

# ressalvas especificas, anexadas a nota do indicador
RESSALVAS = {
    "p2_5_pct_grande_porte": (
        "O denominador e o **total de PJ do proprio relatorio de porte**, e nao a "
        "\"Carteira de Credito\" do Resumo: os dois recortes diferem (o relatorio de credito "
        "inclui o exterior e exclui operacoes que o Resumo agrega), e mistura-los produziria "
        "razoes acima de 100%.\n\n"
        "O indicador e **PJ-only**. Instituicoes sem carteira PJ -- emissores puros de cartao, "
        "por exemplo -- ficam com o campo **VAZIO, nao zero**, e simplesmente nao pontuam neste "
        "item (o score usa a media dos indicadores disponiveis). No universo que entra na "
        "agenda (carteira >= R$ 1 bi) a cobertura e de **93%**; sem corte de porte, 37%.\n\n"
        "Mede **exposicao a tomadores de grande porte**, que e onde vive o risco de nome unico. "
        "Nao e um indice de Herfindahl sobre devedores: um banco com muitos clientes grandes "
        "aparece igual a um banco com poucos. O SCR agregado publicado nao divulga exposicao "
        "por devedor, entao a concentracao em poucos nomes continua fora do alcance do painel."),
    "p2_4_hhi_regional": (
        "Valores proximos de 10.000 indicam atuacao praticamente em uma unica regiao -- comum "
        "e esperado em cooperativas singulares, que por desenho atuam num territorio. A leitura "
        "de risco so faz sentido contra os pares do mesmo TCB."),
}


def mil(n: int) -> str:
    """Separador de milhar no padrao pt-BR."""
    return f"{n:,}".replace(",", ".")


def main() -> None:
    ind = pd.read_parquet(DATA_PROC / "indicadores.parquet")
    dic = pd.read_parquet(DATA_PROC / "dicionario_campos_ifdata.parquet")
    man = pd.read_csv(DATA_RAW / "manifesto_coleta.csv")

    man_if = man[man["fonte"] == "BCB/IF.data"]
    extracao = man_if["data_extracao_utc"].min() if len(man_if) else "—"
    n_arquivos = len(man)
    dt_max = ind["data_base"].max()
    janela = f"{ind['data_base'].min()} – {dt_max} ({ind['data_base'].nunique()} trimestres)"

    gerados = 0
    for col, (perg, titulo, campos, formula, referencia, fonte) in FICHAS.items():
        if col not in ind.columns:
            continue

        s = ind[col].replace([float("inf"), float("-inf")], pd.NA).dropna()
        por_regime = (ind.assign(_v=ind[col].notna())
                        .groupby("regime_contabil")["_v"].mean() * 100).round(1)
        n_ultimo = int(((ind["data_base"] == dt_max) & ind[col].notna()).sum())

        cosif = []
        for c in campos:
            alvo = ROTULO.get(c, c.replace("_", " "))
            achou = dic[dic["coluna_nome"].str.lower().str.contains(alvo, na=False, regex=False)
                        & dic["formula_cosif"].astype(str).str.startswith("[")]
            if len(achou):
                cosif.append(f"`{c}` = {str(achou['formula_cosif'].iloc[0])[:150]}")

        linhas_cob = "\n".join(f"| {k} | {v}% |" for k, v in por_regime.items())
        linhas_cosif = ("\n".join(f"- {x}" for x in cosif) if cosif
                        else "- (indicador derivado de razões; ver os campos de origem acima)")
        campos_fmt = ", ".join(f"`{c}`" for c in campos)
        ressalva = f"\n{RESSALVAS[col]}\n" if col in RESSALVAS else ""
        txt_defl = (TEXTO_DEFLATOR_ESSENCIAL if col in DEFLATOR_ESSENCIAL
                    else TEXTO_DEFLATOR_CANCELA)

        nota = f"""# Nota de verificação — {perg} · {titulo}

`{col}`

| campo | conteúdo |
|---|---|
| Pergunta | **{perg}** |
| Fonte primária | {fonte} |
| Campos de origem | {campos_fmt} |
| Fórmula | `{formula}` |
| Referência de comparação | {referencia} |
| Unidade | razão, % ou p.p. conforme a fórmula acima |
| Deflator | {txt_defl} |
| Recorte | IF.data trimestral por instituição; universo fixado em `00_fontes_confirmadas.md` §2 |
| Janela | {janela} |
| Data de extração (UTC) | {extracao} |
| Rastreabilidade do bruto | `data_raw/manifesto_coleta.csv` — {mil(n_arquivos)} arquivos com URL e SHA-256 |

## Contas COSIF de origem

{linhas_cosif}

## Cobertura observada (% de linhas com valor)

| regime contábil | preenchimento |
|---|---|
{linhas_cob}

Observações válidas no último trimestre ({dt_max}): **{mil(n_ultimo)}**.

## Estatísticas na janela

| medida | valor |
|---|---|
| mediana | {s.median():.4f} |
| p10 | {s.quantile(0.10):.4f} |
| p90 | {s.quantile(0.90):.4f} |

## Como reproduzir

```bash
.venv/Scripts/python.exe src/coleta_ifdata.py     # baixa o bruto
.venv/Scripts/python.exe src/constroi_base.py     # monta o painel e deflaciona
.venv/Scripts/python.exe src/indicadores.py       # calcula este indicador
```

## Limites
{ressalva}
Ver `01_mapa_indicadores.md` — quebra de regime da Res. 4.966, validação cruzada contra
SGS/SCR e os quatro episódios de erro corrigidos — e a seção "O que este painel NÃO permite
concluir", exibida na aba Visão geral do painel.
"""
        (VERIFICACAO / f"{col}.md").write_text(nota, encoding="utf-8")
        gerados += 1

    print(f"[{agora_utc()}] notas geradas: {gerados} (uma por indicador) em verificacao/")


if __name__ == "__main__":
    main()
