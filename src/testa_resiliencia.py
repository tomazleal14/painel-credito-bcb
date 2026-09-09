"""
testa_resiliencia.py -- o painel sobrevive a uma versao MISTA dos arquivos?

Cenario real: o Streamlit Cloud serviu app.py novo com src/ antigo, e o painel morreu
com KeyError em plena tela. Este teste simula a barra lateral devolvendo um dicionario
incompleto (como faria uma versao anterior de filtros.py) e verifica que o app usa os
valores padrao em vez de quebrar.

Nao sobe o Streamlit: testa a leitura tolerante isoladamente.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

import catalogo
from comum import DATA_PROC
from scoring import EIXOS, PESOS_PADRAO, agenda, agenda_grandes, calcula_scores

RAIZ = Path(__file__).resolve().parent.parent

# o que cada versao antiga de filtros.py devolveria
CENARIOS = {
    "versao atual (completa)": ["dt_sel", "tcb_sel", "seg_sel", "porte_min", "pesos",
                                "limiar", "cobertura", "ativos"],
    "sem 'ativos' (antes do catálogo)": ["dt_sel", "tcb_sel", "seg_sel", "porte_min",
                                         "pesos", "limiar", "cobertura"],
    "sem 'limiar'/'cobertura' (antes das 2 listas)": ["dt_sel", "tcb_sel", "seg_sel",
                                                      "porte_min", "pesos"],
    "só o mínimo (versão bem antiga)": ["dt_sel", "pesos"],
}


def le_tolerante(f: dict, ind: pd.DataFrame) -> dict:
    """Replica a leitura tolerante do app.py."""
    return {
        "dt_sel": f.get("dt_sel", max(ind["data_base"])),
        "tcb_sel": f.get("tcb_sel") or sorted(ind["tcb"].dropna().unique()),
        "seg_sel": f.get("seg_sel") or sorted(ind["segmento_sr"].fillna("").unique()),
        "porte_min": f.get("porte_min", 1e9),
        "pesos": f.get("pesos") or PESOS_PADRAO,
        "limiar": f.get("limiar", 0.65),
        "cobertura": f.get("cobertura", 0.80),
        "ativos": f.get("ativos") or {e: catalogo.padrao_do_eixo(e) for e in EIXOS},
    }


def main() -> int:
    ind = pd.read_parquet(DATA_PROC / "app_indicadores.parquet")
    dt = int(ind["data_base"].max())
    completo = {
        "dt_sel": dt,
        "tcb_sel": sorted(ind["tcb"].dropna().unique()),
        "seg_sel": sorted(ind["segmento_sr"].fillna("").unique()),
        "porte_min": 1e9, "pesos": PESOS_PADRAO, "limiar": 0.65, "cobertura": 0.80,
        "ativos": {e: catalogo.padrao_do_eixo(e) for e in EIXOS},
    }

    falhas = 0
    for nome, chaves in CENARIOS.items():
        parcial = {k: v for k, v in completo.items() if k in chaves}
        faltando = [k for k in completo if k not in parcial]
        try:
            c = le_tolerante(parcial, ind)
            base = ind[ind["tcb"].isin(c["tcb_sel"])
                       & ind["segmento_sr"].isin(c["seg_sel"])]
            sc = calcula_scores(base, grupo_pares="tcb", pesos=c["pesos"],
                                ativos=c["ativos"])
            ag = agenda(sc, c["dt_sel"], minimo_carteira=c["porte_min"],
                        limiar=c["limiar"])
            gr = agenda_grandes(sc, c["dt_sel"], cobertura=c["cobertura"])
            print(f"  OK    {nome:46s} faltavam {len(faltando)} · "
                  f"agenda {len(ag)} · grandes {len(gr)}")
        except Exception as e:  # noqa: BLE001
            print(f"  FALHA {nome:46s} {type(e).__name__}: {e}")
            falhas += 1

    # o app.py realmente usa leitura tolerante?
    texto = (RAIZ / "app.py").read_text(encoding="utf-8")
    diretos = re.findall(r'f\["(\w+)"\]', texto)
    print()
    if diretos:
        print(f"FALHA: app.py ainda acessa a barra lateral direto: "
              f"{', '.join(sorted(set(diretos)))}")
        print("Use f.get(...) com valor padrão.")
        return 1
    print("app.py lê a barra lateral só com f.get(), sem acesso direto")

    if falhas:
        print(f"\n{falhas} cenário(s) quebraram")
        return 1
    print("o painel sobrevive a todas as versões mistas testadas")
    return 0


if __name__ == "__main__":
    sys.exit(main())
