"""
catalogo.py -- REGISTRO ÚNICO de todos os indicadores que o painel sabe calcular.

Por que existe: até aqui, os 18 indicadores estavam repetidos em quatro lugares
(indicadores.py, scoring.py, cartoes.py e textos.toml). Trocar um exigia editar
código em vários arquivos. Agora cada indicador é declarado UMA vez aqui, com
metadados e fórmula, e todo o resto do painel lê deste registro.

Consequência prática: a troca de um indicador por outro é **configuração**, não
programação. O painel calcula TODOS os indicadores do catálogo e guarda no parquet;
a seleção dos 6 ativos por pergunta vive em `indicadores.toml` e pode ser mudada
na barra lateral, em tempo real, sem reiniciar nada.

Campos de cada indicador:
  chave     nome da coluna no parquet
  rotulo    como aparece na tela
  eixo      crescimento | concentracao | deterioracao
  unidade   sufixo exibido ("% a.a.", "×", "p.p.", "")
  fator     multiplicador para exibição (100 converte fração em %)
  casas     casas decimais
  sentido   maior_pior | menor_pior  -- define se o percentil é invertido no score
  escopo    instituicao | sistema    -- "sistema" não gera percentil (valor igual p/ todas)
  fonte     origem primária do dado
  formula   como é calculado, em uma linha
  padrao    True = entra na seleção inicial dos 6 daquele eixo
"""
from __future__ import annotations

from dataclasses import dataclass

EIXOS = ("crescimento", "concentracao", "deterioracao")
TRIM_POR_ANO = 4


@dataclass(frozen=True)
class Indicador:
    chave: str
    rotulo: str
    eixo: str
    unidade: str
    fator: float
    casas: int
    sentido: str
    fonte: str
    formula: str
    padrao: bool = False
    escopo: str = "instituicao"
    nota: str = ""


# --------------------------------------------------------------------------- P1
_P1 = [
    Indicador("p1_1_cresc_real_aa", "Crescimento real da carteira", "crescimento",
              "% a.a.", 100, 1, "maior_pior",
              "IF.data · Resumo · Carteira de Crédito (deflacionada pelo IPCA/SGS 433)",
              "carteira_real(t) / carteira_real(t-4) − 1", padrao=True),
    Indicador("p1_2_credit_gap", "Credit gap", "crescimento",
              "%", 100, 1, "maior_pior",
              "IF.data · Resumo · Carteira de Crédito",
              "ciclo do filtro Hodrick-Prescott (λ=1600) sobre ln(carteira real)",
              padrao=True, nota="exige 12 trimestres de série no mesmo universo"),
    Indicador("p1_3_trim_consec_acima", "Trimestres seguidos > 15%", "crescimento",
              "trim.", 1, 0, "maior_pior",
              "derivado de p1_1_cresc_real_aa",
              "contagem de trimestres consecutivos com crescimento real ≥ 15% a.a.",
              padrao=True),
    Indicador("p1_4_cresc_carteira_sobre_capital", "Carteira ÷ capital", "crescimento",
              "×", 1, 2, "maior_pior",
              "IF.data · Resumo + Informações de Capital (Patrimônio de Referência)",
              "(1+cresc. da carteira) ÷ (1+cresc. do PR), ambos em 12 meses",
              padrao=True, nota="PR só existe no tipo 1009, a partir de 2023Q3"),
    Indicador("p1_5_cresc_alto_risco_aa", "Crescimento em alto risco", "crescimento",
              "% a.a.", 100, 1, "maior_pior",
              "IF.data · Carteira PF por modalidade (cartão + sem consignação)",
              "variação em 12 meses da soma das duas modalidades, deflacionada",
              padrao=True),
    Indicador("p1_6_var_share_pp", "Ganho de market share", "crescimento",
              "p.p.", 1, 3, "maior_pior",
              "IF.data · Resumo · Carteira de Crédito",
              "share(t) − share(t−4), em pontos percentuais da carteira do universo",
              padrao=True),
    # ---- alternativas disponíveis para troca ----
    Indicador("p1_7_cresc_ativo_aa", "Crescimento do ativo total", "crescimento",
              "% a.a.", 100, 1, "maior_pior",
              "IF.data · Resumo · Ativo Total (deflacionado)",
              "ativo_real(t) / ativo_real(t−4) − 1",
              nota="mais amplo que a carteira: capta expansão fora do crédito"),
    Indicador("p1_8_cresc_captacoes_aa", "Crescimento das captações", "crescimento",
              "% a.a.", 100, 1, "maior_pior",
              "IF.data · Resumo · Captações (deflacionado)",
              "captacoes_real(t) / captacoes_real(t−4) − 1",
              nota="funding crescendo muito acima da carteira indica captação antecipada"),
    Indicador("p1_9_cresc_clientes_aa", "Crescimento do nº de clientes", "crescimento",
              "% a.a.", 100, 1, "maior_pior",
              "IF.data · Carteira ativa · Quantidade de clientes com operações ativas",
              "qtd_clientes(t) / qtd_clientes(t−4) − 1",
              nota="separa expansão por novos tomadores de expansão por ticket maior"),
    Indicador("p1_10_cresc_pj_aa", "Crescimento da carteira PJ", "crescimento",
              "% a.a.", 100, 1, "maior_pior",
              "IF.data · Carteira PJ por modalidade · Total (deflacionado)",
              "pj_total_real(t) / pj_total_real(t−4) − 1"),
    Indicador("p1_11_aceleracao_pp", "Aceleração do crescimento", "crescimento",
              "p.p.", 100, 1, "maior_pior",
              "derivado de p1_1_cresc_real_aa",
              "cresc.(t) − cresc.(t−4): variação do próprio ritmo, em p.p.",
              nota="crescimento alto e estável difere de crescimento que está disparando"),
    Indicador("p1_12_cresc_ticket_aa", "Crescimento do ticket médio", "crescimento",
              "% a.a.", 100, 1, "maior_pior",
              "IF.data · Resumo ÷ Quantidade de clientes",
              "(carteira_real/clientes)(t) ÷ (carteira_real/clientes)(t−4) − 1",
              nota="ticket subindo rápido = mais exposição por tomador"),
]

# --------------------------------------------------------------------------- P2
_P2 = [
    Indicador("p2_1_hhi_sistema", "HHI do sistema", "concentracao",
              "", 1, 0, "maior_pior",
              "IF.data · Resumo · Carteira de Crédito (todas as IFs do universo)",
              "Σ share_i² × 10.000, sobre a carteira do universo",
              padrao=True, escopo="sistema"),
    Indicador("p2_2_cr5_sistema_pct", "CR5", "concentracao",
              "%", 1, 1, "maior_pior",
              "IF.data · Resumo · Carteira de Crédito",
              "soma do share das 5 maiores instituições do universo",
              padrao=True, escopo="sistema"),
    Indicador("p2_3_pct_alto_risco", "Carteira PF em alto risco", "concentracao",
              "%", 100, 1, "maior_pior",
              "IF.data · Carteira PF por modalidade",
              "(cartão + sem consignação) ÷ total da carteira PF", padrao=True),
    Indicador("p2_4_hhi_regional", "HHI regional", "concentracao",
              "", 1, 0, "maior_pior",
              "IF.data · Carteira de crédito ativa por região geográfica",
              "Σ share_região² × 10.000, dentro da própria carteira", padrao=True),
    Indicador("p2_5_pct_grande_porte", "Carteira PJ em grande porte", "concentracao",
              "%", 100, 1, "maior_pior",
              "IF.data · Carteira PJ por porte do tomador",
              "carteira PJ em tomadores de grande porte ÷ total PJ do mesmo relatório",
              padrao=True, nota="PJ-only: IFs sem carteira PJ ficam vazias, não zero"),
    Indicador("p2_6_loan_to_deposit", "Carteira ÷ captações", "concentracao",
              "×", 1, 2, "maior_pior",
              "IF.data · Resumo · Carteira de Crédito e Captações",
              "carteira_real ÷ captações_real", padrao=True),
    # ---- alternativas disponíveis para troca ----
    Indicador("p2_7_hhi_modalidade_pf", "HHI de modalidades PF", "concentracao",
              "", 1, 0, "maior_pior",
              "IF.data · Carteira PF por modalidade (7 modalidades)",
              "Σ share_modalidade² × 10.000, dentro da carteira PF",
              nota="mede concentração no MIX de produtos, não no nível de risco"),
    Indicador("p2_8_max_regiao_pct", "Maior região", "concentracao",
              "%", 100, 1, "maior_pior",
              "IF.data · Carteira por região geográfica",
              "fatia da região com maior participação na carteira",
              nota="leitura mais direta que o HHI regional, em % da carteira"),
    Indicador("p2_9_credito_sobre_ativo", "Crédito ÷ ativo total", "concentracao",
              "%", 100, 1, "maior_pior",
              "IF.data · Resumo · Carteira de Crédito e Ativo Total",
              "carteira_real ÷ ativo_total_real",
              nota="quanto do balanço está exposto a risco de crédito"),
    Indicador("p2_10_ticket_medio", "Ticket médio por cliente", "concentracao",
              "R$ mil", 0.001, 1, "maior_pior",
              "IF.data · Resumo ÷ Quantidade de clientes com operações ativas",
              "carteira_real ÷ nº de clientes ativos",
              nota="proxy de granularidade; NÃO mede exposição aos maiores devedores"),
    Indicador("p2_11_pct_capital_giro", "Carteira PJ em capital de giro", "concentracao",
              "%", 100, 1, "maior_pior",
              "IF.data · Carteira PJ por modalidade",
              "capital de giro ÷ total da carteira PJ"),
    Indicador("p2_12_hhi_porte_pj", "HHI de porte do tomador", "concentracao",
              "", 1, 0, "maior_pior",
              "IF.data · Carteira PJ por porte (micro, pequena, média, grande)",
              "Σ share_porte² × 10.000, dentro da carteira PJ",
              nota="alternativa ao % em grande porte: mede dispersão entre portes"),
    Indicador("p2_13_dep_imediato_pct", "Funding de resgate imediato", "concentracao",
              "%", 100, 1, "maior_pior",
              "IF.data · Passivo · Depósitos à Vista e de Poupança ÷ Captações",
              "(depósito à vista + poupança) ÷ captações totais",
              nota="mede a COMPOSIÇÃO do funding, que a razão carteira ÷ captações não "
                   "distingue; é piso, não total — CDB com liquidez diária também é "
                   "resgatável de imediato e o relatório não abre prazo"),
]

# --------------------------------------------------------------------------- P3
_P3 = [
    Indicador("p3_1_inadimplencia", "Inadimplência", "deterioracao",
              "%", 100, 2, "maior_pior",
              "IF.data · Carteira por carteiras de instrumentos financeiros · Inadimplência",
              "carteira em atraso > 90 dias ÷ carteira de crédito",
              padrao=True, nota="regime ECL (Res. 4.966): disponível a partir de 2025Q1"),
    Indicador("p3_2_cobertura", "Cobertura de provisões", "deterioracao",
              "%", 100, 0, "menor_pior",
              "IF.data · Ativo · Perda Esperada (ou Provisão, até 2024)",
              "provisão ÷ carteira em atraso; 100% cobre integralmente o atraso",
              padrao=True),
    Indicador("p3_3_provisao_sobre_carteira", "Provisão ÷ carteira", "deterioracao",
              "%", 100, 2, "menor_pior",
              "IF.data · Ativo · Perda Esperada ÷ Resumo · Carteira de Crédito",
              "provisão ÷ carteira de crédito", padrao=True),
    Indicador("p3_4_inadimplencia_ajustada", "Inadimplência ajustada", "deterioracao",
              "%", 100, 2, "maior_pior",
              "IF.data · Inadimplência ÷ Carteira de 4 trimestres antes",
              "atraso(t) ÷ carteira_real(t−4) — corrige o efeito denominador",
              padrao=True),
    Indicador("p3_5_ativos_problematicos", "Ativos problemáticos", "deterioracao",
              "%", 100, 2, "maior_pior",
              "IF.data · Carteira por instrumentos financeiros · Ativos problemáticos",
              "ativos problemáticos (Res. 4.557) ÷ carteira de crédito", padrao=True),
    Indicador("p3_6_folga_capital_pp", "Folga de capital", "deterioracao",
              "p.p.", 1, 1, "menor_pior",
              "IF.data · Informações de Capital · Índice de Basileia",
              "Basileia × 100 − 10,5 (8% de requisito + 2,5% de conservação)",
              padrao=True),
    # ---- alternativas disponíveis para troca ----
    Indicador("p3_7_folga_capital_principal_pp", "Folga de capital principal", "deterioracao",
              "p.p.", 1, 1, "menor_pior",
              "IF.data · Informações de Capital · Índice de Capital Principal",
              "Capital Principal × 100 − 7,0 (4,5% + 2,5% de conservação)",
              nota="capital de maior qualidade; exigência mais estrita que Basileia"),
    Indicador("p3_8_razao_alavancagem", "Razão de alavancagem", "deterioracao",
              "%", 100, 2, "menor_pior",
              "IF.data · Informações de Capital · Razão de Alavancagem",
              "Nível I ÷ exposição total, sem ponderação por risco",
              nota="não depende do modelo de risco da própria instituição"),
    Indicador("p3_9_gap_problematico_pp", "Distância problemático − inadimplência",
              "deterioracao", "p.p.", 100, 2, "maior_pior",
              "IF.data · Ativos problemáticos e Inadimplência",
              "(ativos problemáticos − atraso 90+) ÷ carteira",
              nota="mede o que foi renegociado ou reestruturado sem virar atraso"),
    Indicador("p3_10_problematico_sobre_pl", "Ativos problemáticos ÷ PL", "deterioracao",
              "%", 100, 1, "maior_pior",
              "IF.data · Ativos problemáticos ÷ Resumo · Patrimônio Líquido",
              "ativos problemáticos ÷ patrimônio líquido",
              nota="capacidade de absorver a perda com capital próprio"),
    Indicador("p3_11_var_inadimplencia_pp", "Variação da inadimplência", "deterioracao",
              "p.p.", 100, 2, "maior_pior",
              "derivado de p3_1_inadimplencia",
              "inadimplência(t) − inadimplência(t−4), em p.p.",
              nota="nível alto e estável difere de nível que está subindo"),
    Indicador("p3_12_retorno_sobre_pl", "Retorno sobre PL", "deterioracao",
              "%", 100, 2, "menor_pior",
              "IF.data · Resumo · Lucro Líquido ÷ Patrimônio Líquido",
              "lucro_liquido_real ÷ patrimonio_liquido_real",
              nota="ATENÇÃO: o lucro do IF.data é acumulado no semestre (jan-mar, "
                   "jan-jun, jul-set, jul-dez), então não é anualizado"),
]

CATALOGO: tuple[Indicador, ...] = tuple(_P1 + _P2 + _P3)
POR_CHAVE: dict[str, Indicador] = {i.chave: i for i in CATALOGO}


def do_eixo(eixo: str) -> list[Indicador]:
    return [i for i in CATALOGO if i.eixo == eixo]


def padrao_do_eixo(eixo: str) -> list[str]:
    return [i.chave for i in CATALOGO if i.eixo == eixo and i.padrao]


def rotulo(chave: str) -> str:
    ind = POR_CHAVE.get(chave)
    return ind.rotulo if ind else chave


def formata(chave: str, valor) -> str:
    """Aplica fator e casas decimais do catálogo, no padrão pt-BR."""
    ind = POR_CHAVE.get(chave)
    if ind is None or valor is None or valor != valor:
        return "—"
    v = float(valor) * ind.fator
    txt = f"{v:,.{ind.casas}f}".replace(",", " ").replace(".", ",").replace(" ", ".")
    return f"{txt}{ind.unidade}"


def carrega_ativos() -> tuple[dict[str, list[str]], list[str]]:
    """Lê indicadores.toml e devolve (seleção ativa, avisos).

    Cai no padrão do catálogo se o arquivo faltar, tiver erro de sintaxe, citar chave
    inexistente ou trazer número diferente de 6 -- a regra do trabalho. Nunca levanta
    excecao: durante uma apresentacao, o painel avisa e segue.
    """
    import tomllib
    from pathlib import Path

    arquivo = Path(__file__).resolve().parent.parent / "indicadores.toml"
    avisos: list[str] = []
    ativos = {e: padrao_do_eixo(e) for e in EIXOS}

    try:
        with arquivo.open("rb") as fh:
            dados = tomllib.load(fh).get("ativos", {})
    except FileNotFoundError:
        return ativos, [f"indicadores.toml não encontrado — usando a seleção padrão"]
    except Exception as e:  # noqa: BLE001
        return ativos, [f"erro em indicadores.toml ({type(e).__name__}) — usando o padrão"]

    for eixo in EIXOS:
        lista = dados.get(eixo)
        if not lista:
            avisos.append(f"[{eixo}] ausente — usando o padrão")
            continue
        desconhecidas = [c for c in lista if c not in POR_CHAVE]
        if desconhecidas:
            avisos.append(f"[{eixo}] chave inexistente: {', '.join(desconhecidas)}")
            lista = [c for c in lista if c in POR_CHAVE]
        fora = [c for c in lista if POR_CHAVE[c].eixo != eixo]
        if fora:
            avisos.append(f"[{eixo}] indicador de outro eixo: {', '.join(fora)}")
            lista = [c for c in lista if POR_CHAVE[c].eixo == eixo]
        if len(lista) != 6:
            avisos.append(f"[{eixo}] tem {len(lista)} indicadores, a regra exige 6 "
                          f"— usando o padrão")
            continue
        ativos[eixo] = lista
    return ativos, avisos


def resumo() -> str:
    """Texto de conferência: quantos indicadores há por eixo e quantos são padrão."""
    linhas = []
    for e in EIXOS:
        do = do_eixo(e)
        pad = [i for i in do if i.padrao]
        linhas.append(f"{e:14s} {len(do):>2} no catálogo · {len(pad)} no padrão")
    return "\n".join(linhas)
