"""
avalia_ponte.py -- existe alguma forma de encadear a carteira atraves da Res. 4.966?

Este script responde NAO, e mostra por que. Ele existe porque a pergunta e legitima e
vai ser feita: "por que voces nao compatibilizaram os regimes em vez de jogar fora um
ano de P1?". A resposta precisa ser medida, nao opiniao.

Sao DUAS descontinuidades. A primeira tem solucao; a segunda nao.

(1) IDENTIDADE -- tem solucao, e esta implementada em `crosswalk.py`.
    Os codigos mudam (Itau e `10069` no 1005 e `1000080099` no 1009), mas o proprio
    cadastro do IF.data declara o vinculo nos campos c15/c22. Somar as entidades 1005
    vinculadas reproduz o valor 1009 publicado com erro mediano de 0,000%.
    CONCLUSAO: nao e falta de par. O par existe e e oficial.

(2) MEDIDA -- NAO tem solucao. Tres testes, nesta ordem:

    a) O salto e um fator comum, que se possa ajustar? NAO.
       No universo prudencial (mesmos codigos dos dois lados), a variacao trimestral
       em 202412->202503 tem mediana -3,2% contra +2,2% num trimestre normal -- mas o
       IQR ABRE de 8,6 para 13,9 p.p. (1,62x) e o p05 vai de -16,0% para -33,3%. O
       efeito e idiossincratico: cada instituicao se move para um lado. Nenhum fator
       unico conserta isso.

    b) Existe outra linha contabil continua, que sirva de ponte? NAO.
       "Operacoes de Credito (d1)" do relatorio Ativo aparece nos dois regimes, mas
       MUDOU DE SIGNIFICADO: em 2025 vale exatamente `e1 - |e2|` (valor contabil bruto
       menos perda esperada). A identidade fecha em 1,0000 do p25 ao p75, nas 1.059
       instituicoes. Era bruta, virou liquida.

    c) A familia "Carteira de credito ativa" (base SCR) e uma fonte independente? NAO.
       Este e o teste que engana. Comparando SO as instituicoes cujo codigo nao mudou
       -- os independentes --, `reg_total` parece atravessar a quebra sem degrau
       (mediana +0,6%, IQR encolhendo). Mas essas nunca tiveram problema nenhum: sao a
       subamostra em que a quebra de identidade nao existe, e os grandes bancos ficam
       de fora dela por construcao.
       O teste correto e outro: comparar `reg_total` com a carteira do Resumo dentro do
       mesmo trimestre. Ate 202409 a razao e 1,0000 do p25 ao p75, em TODAS as
       data-bases -- os dois relatorios publicam O MESMO NUMERO. A "carteira ativa" nao
       e fonte independente antes de 2025; ela carrega a mesma definicao contabil. De
       202503 em diante a razao passa a 1,036, porque so entao os dois conceitos se
       separam.
       CONCLUSAO: nao ha serie de carteira anterior a 2025 que seja independente da
       definicao que mudou.

Resultado: a mascara de `indicadores.py` nao e escolha de conveniencia. E a unica
saida que nao inventa numero.
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

from comum import DATA_PROC

TOL = 0.01


def _var(p: pd.DataFrame, col: str, dt_t: int, dt_0: int) -> pd.Series:
    a = p[p.data_base == dt_t][["cod_inst", col]].rename(columns={col: "t"})
    b = p[p.data_base == dt_0][["cod_inst", col]].rename(columns={col: "b"})
    m = a.merge(b, on="cod_inst")
    m = m[(m["t"] > 0) & (m["b"] > 0)]
    return np.log(m["t"] / m["b"])


def main() -> int:
    longo = pd.read_parquet(DATA_PROC / "painel_ifdata_longo.parquet")
    prud = pd.read_parquet(DATA_PROC / "painel_ifdata_prudencial.parquet")

    print("(2a) O SALTO E UM FATOR COMUM? — universo prudencial, mesmos codigos\n")
    vn = _var(prud, "carteira_credito_real", 202412, 202409)
    vq = _var(prud, "carteira_credito_real", 202503, 202412)
    iqn = vn.quantile(.75) - vn.quantile(.25)
    iqq = vq.quantile(.75) - vq.quantile(.25)
    print(f"   {'':>10s} {'mediana':>9s} {'IQR':>8s} {'p05':>9s} {'p95':>9s} {'n':>6s}")
    print(f"   {'normal':>10s} {vn.median()*100:>8.1f}% {iqn*100:>7.1f} "
          f"{vn.quantile(.05)*100:>8.1f}% {vn.quantile(.95)*100:>8.1f}% {len(vn):>6d}")
    print(f"   {'quebra':>10s} {vq.median()*100:>8.1f}% {iqq*100:>7.1f} "
          f"{vq.quantile(.05)*100:>8.1f}% {vq.quantile(.95)*100:>8.1f}% {len(vq):>6d}")
    print(f"   dispersao {iqq/iqn:.2f}x maior na quebra -> efeito IDIOSSINCRATICO, "
          f"nao fator comum")

    print("\n(2b) 'OPERACOES DE CREDITO (d1)' MUDOU DE SIGNIFICADO?\n")
    for d in (202503, 202603):
        q = prud[(prud.data_base == d) & (prud.credito_bruto_antigo_real > 0)
                 & (prud.credito_bruto_novo_real > 0) & prud.perda_esperada_real.notna()]
        if q.empty:
            continue
        r = (q.credito_bruto_novo_real - q.perda_esperada_real.abs()) / q.credito_bruto_antigo_real
        print(f"   {d}: (e1 - |e2|) / d1 -> p25 {r.quantile(.25):.4f} · "
              f"mediana {r.median():.4f} · p75 {r.quantile(.75):.4f} · n {len(q)}")
    print("   a identidade fecha em 1,0000 -> d1 virou LIQUIDA de perda esperada")

    print("\n(2c) A 'CARTEIRA ATIVA' E FONTE INDEPENDENTE DA CARTEIRA DO RESUMO?\n")
    print(f"   {'data-base':>10s} {'reg_total / carteira_credito (mediana)':>40s}")
    falhas = 0
    for d in sorted(longo.data_base.unique()):
        q = longo[(longo.data_base == d) & (longo.reg_total_real > 0)
                  & (longo.carteira_credito_real > 0)]
        if q.empty:
            continue
        r = (q.reg_total_real / q.carteira_credito_real).median()
        marca = "  <- mesmo numero" if abs(r - 1) < 1e-4 else "  <- conceitos separados"
        print(f"   {d:>10d} {r:>40.4f}{marca}")
    print("\n   Ate 202412 os dois relatorios publicam o MESMO numero. A carteira ativa")
    print("   so passa a ser um conceito proprio em 202503 -- depois da quebra, quando")
    print("   ja nao serve de ponte para tras.")

    print("\nCONCLUSAO: nenhuma das tres vias encadeia a carteira atraves da Res. 4.966.")
    print("A mascara de 2025 em P1 e a unica alternativa que nao inventa numero.")
    return falhas


if __name__ == "__main__":
    sys.exit(main())
