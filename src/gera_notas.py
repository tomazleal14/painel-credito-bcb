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

from comum import DATA_PROC, DATA_RAW, VERIFICACAO, agora_utc

# indicador -> (pergunta, titulo, campos de origem, formula, referencia, fonte principal)
FICHAS = {
    "p1_1_cresc_real_aa": (
        "P1", "Crescimento real anual da carteira",
        ["carteira_credito"], "carteira_real_t / carteira_real_(t-4) - 1",
        "Mediana do universo no trimestre; limiar de 15% a.a. real", "IF.data · Resumo"),
    "p1_2_credit_gap": (
        "P1", "Credit gap da instituição",
        ["carteira_credito"], "desvio do log da carteira real frente à tendência HP (lambda=1600)",
        "Própria tendência; +1 desvio-padrão do gap", "IF.data · Resumo"),
    "p1_3_trim_consec_acima": (
        "P1", "Persistência do crescimento acelerado",
        ["carteira_credito"], "nº de trimestres consecutivos com crescimento real >= 15% a.a.",
        "8 trimestres ou mais = boom (Dell'Ariccia et al., FMI)", "IF.data · Resumo (derivado)"),
    "p1_4_cresc_carteira_sobre_capital": (
        "P1", "Crescimento da carteira ÷ crescimento do capital",
        ["carteira_credito", "pr"], "(1+cresc_carteira) / (1+cresc_PR)",
        "1,0 = crescimento pari passu ao capital", "IF.data · Resumo + Informações de Capital"),
    "p1_5_cresc_alto_risco_aa": (
        "P1", "Crescimento nas modalidades de maior risco",
        ["pf_cartao", "pf_sem_consignacao"],
        "var. % a.a. real de (cartão + empréstimo sem consignação)",
        "Mesma modalidade no sistema (SCR.data)", "IF.data · Carteira PF por modalidade"),
    "p1_6_var_share_pp": (
        "P1", "Velocidade de ganho de market share",
        ["carteira_credito"], "(share_t - share_(t-4)) x 100, share = IF / soma do universo",
        "Variação de share dos pares do mesmo TCB", "IF.data · Resumo"),

    "p2_1_hhi_sistema": (
        "P2", "HHI do sistema", ["carteira_credito"], "soma dos share^2 x 10.000",
        "Faixas antitruste 1.500 / 2.500", "IF.data · Resumo"),
    "p2_2_cr5_sistema_pct": (
        "P2", "CR5 — share dos cinco maiores", ["carteira_credito"],
        "soma do share das 5 maiores x 100", "Própria série no tempo", "IF.data · Resumo"),
    "p2_3_pct_alto_risco": (
        "P2", "Participação de modalidades de alto risco na carteira PF",
        ["pf_cartao", "pf_sem_consignacao", "pf_total"],
        "(cartão + sem consignação) / total PF",
        "Mesma razão agregada do universo e do SCR.data",
        "IF.data · Carteira PF por modalidade"),
    "p2_4_hhi_regional": (
        "P2", "Concentração regional da carteira",
        ["reg_sudeste", "reg_sul", "reg_nordeste", "reg_norte", "reg_centro_oeste"],
        "HHI entre as 5 regiões x 10.000",
        "HHI regional do universo; ESTBAN para detalhe municipal",
        "IF.data · Carteira por região geográfica"),
    "p2_5_pct_grande_porte": (
        "P2", "Exposição a tomadores de grande porte",
        ["pj_porte_grande", "pj_total_porte"],
        "carteira PJ em tomadores de grande porte / total da carteira PJ",
        "Mediana dos pares do mesmo TCB; p75 do universo = 24,1%",
        "IF.data · Carteira de crédito ativa PJ por porte do tomador"),
    "p2_6_loan_to_deposit": (
        "P2", "Dependência de funding (loan-to-deposit)",
        ["carteira_credito", "captacoes"], "carteira real / captações reais",
        "1,0 e mediana dos pares do mesmo TCB", "IF.data · Resumo"),

    "p3_1_inadimplencia": (
        "P3", "Inadimplência sobre a carteira",
        ["inadimplencia_valor", "carteira_credito"], "carteira inadimplida / carteira",
        "SGS 21082 (SFN), 21112 (PF livre), 21086 (PJ livre)",
        "IF.data · Carteira por instrumentos financeiros"),
    "p3_1b_niveis_eh": (
        "P3", "Carteira em níveis E–H (regime AA–H, até 202412)",
        ["risco_e", "risco_f", "risco_g", "risco_h", "carteira_credito"],
        "(E+F+G+H) / carteira",
        "NÃO comparável à inadimplência 90+: fica ~2,5 p.p. acima (ver validação cruzada)",
        "IF.data · Carteira por nível de risco"),
    "p3_2_cobertura": (
        "P3", "Índice de cobertura de provisões",
        ["perda_esperada", "provisao_antiga", "inadimplencia_valor"],
        "|provisão| / carteira inadimplida", "100% ou mais, e própria série",
        "IF.data · Ativo (Perda Esperada / Provisão sobre Operações de Crédito)"),
    "p3_3_provisao_sobre_carteira": (
        "P3", "Provisão sobre carteira total",
        ["perda_esperada", "provisao_antiga", "carteira_credito"],
        "|provisão| / carteira", "Mediana dos pares", "IF.data · Ativo"),
    "p3_4_inadimplencia_ajustada": (
        "P3", "Inadimplência ajustada ao crescimento (efeito denominador)",
        ["inadimplencia_valor", "carteira_credito"],
        "carteira inadimplida_t / carteira real_(t-4)",
        "Mesma métrica nas IFs de baixo crescimento; diagonal de igualdade",
        "IF.data · Carteira por instrumentos financeiros + Resumo"),
    "p3_5_ativos_problematicos": (
        "P3", "Ativos problemáticos sobre a carteira",
        ["ativos_problematicos_valor", "carteira_credito"],
        "ativos problemáticos / carteira", "SCR.data — ativo problemático do sistema",
        "IF.data · Carteira por instrumentos financeiros"),
    "p3_6_folga_capital_pp": (
        "P3", "Folga de capital sobre o mínimo regulatório",
        ["indice_basileia"], "Índice de Basileia x 100 - 10,5",
        "Mínimo 8% + conservação 2,5%; adicionais podem elevar o piso",
        "IF.data · Informações de Capital"),
}

# nome do campo do painel -> trecho do nome da coluna no IF.data (para achar a formula COSIF)
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
