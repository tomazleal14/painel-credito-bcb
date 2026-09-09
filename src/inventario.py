"""
inventario.py -- gera o mapa dos dados para conferência na apresentação.

Percorre data_raw/ e data_processed/, conta arquivos, mede tamanho e cruza com o
manifesto de coleta. A saída vai para docs/ONDE_ESTAO_OS_DADOS.md, para que no dia
da apresentação baste abrir a pasta e apontar.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from comum import DATA_PROC, DATA_RAW, RAIZ

DOCS = RAIZ / "docs"


def tamanho(p: Path) -> int:
    return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())


def mb(n: int) -> str:
    return f"{n/1048576:,.1f} MB".replace(",", ".")


def conta(p: Path, padrao: str = "*") -> int:
    return sum(1 for f in p.rglob(padrao) if f.is_file())


def linha_pasta(p: Path, descricao: str) -> str:
    if not p.exists():
        return f"| `{p.relative_to(RAIZ)}` | — | — | {descricao} (ausente) |"
    return (f"| `{p.relative_to(RAIZ).as_posix()}/` | {conta(p):,} |".replace(",", ".")
            + f" {mb(tamanho(p))} | {descricao} |")


def main() -> None:
    man = pd.read_csv(DATA_RAW / "manifesto_coleta.csv") if (DATA_RAW / "manifesto_coleta.csv").exists() else pd.DataFrame()
    por_fonte = man["fonte"].value_counts().to_dict() if len(man) else {}

    partes = [
        "# Onde estão os dados — guia de conferência",
        "",
        f"Gerado por `src/inventario.py` em "
        f"{datetime.now(timezone.utc):%d/%m/%Y %H:%M} UTC.",
        "",
        "Este documento existe para a apresentação: qualquer número do painel pode ser "
        "rastreado até o arquivo bruto que o originou.",
        "",
        "## Caminho da pasta",
        "",
        "```",
        str(RAIZ),
        "```",
        "",
        "## Estrutura",
        "",
        "| pasta | arquivos | tamanho | conteúdo |",
        "|---|---|---|---|",
        linha_pasta(DATA_RAW / "ifdata", "**brutos do IF.data** — JSON originais, por trimestre"),
        linha_pasta(DATA_RAW / "sgs", "**brutos do SGS** — séries e XML do catálogo oficial"),
        linha_pasta(DATA_RAW / "scr", "**brutos do SCR.data** — séries por modalidade"),
        linha_pasta(DATA_RAW / "estban", "**brutos do ESTBAN** — ZIP por data-base"),
        linha_pasta(DATA_PROC, "**derivados** — painéis, indicadores, dicionário, deflator"),
        linha_pasta(RAIZ / "verificacao", "**notas de verificação** — uma por indicador e por fonte"),
        linha_pasta(RAIZ / "src", "**código** — coleta, transformação, cálculo e verificação"),
        "",
        "## Manifesto de coleta",
        "",
        f"`data_raw/manifesto_coleta.csv` — **{len(man):,} registros**".replace(",", ".") +
        ", cada um com URL, data/hora de extração (UTC), SHA-256 e tamanho em bytes.",
        "",
        "| fonte | arquivos baixados |",
        "|---|---|",
    ]
    for fonte, n in sorted(por_fonte.items(), key=lambda x: -x[1]):
        partes.append(f"| {fonte} | {n:,} |".replace(",", "."))

    partes += [
        "",
        "## Arquivos derivados (data_processed/)",
        "",
        "| arquivo | tamanho | o que é |",
        "|---|---|---|",
    ]
    descr = {
        "app_indicadores.parquet": "**base que o painel lê** — 36 indicadores + campos de apoio",
        "indicadores.parquet": "base completa, com todas as colunas intermediárias",
        "painel_ifdata_longo.parquet": "painel por instituição, universo de série longa (1005→1009)",
        "painel_ifdata_prudencial.parquet": "painel por instituição, universo prudencial (1009)",
        "dicionario_campos_ifdata.csv": "**dicionário de campos do IF.data**, com fórmula COSIF",
        "dicionario_campos_ifdata.parquet": "o mesmo dicionário, comprimido para o painel",
        "catalogo_series_sgs.csv": "**as 14 séries do SGS**, com nome oficial conferido",
        "sgs_series.parquet": "observações das séries do SGS",
        "scr_agregado.parquet": "SCR por modalidade e tipo de cliente",
        "estban_municipio.parquet": "ESTBAN consolidado por município",
        "deflator_ipca.csv": "**deflator IPCA** — índice e fator por mês",
        "glossario_filtros.csv": "descrições oficiais das siglas TCB, SR e TC",
    }
    if DATA_PROC.exists():
        for f in sorted(DATA_PROC.iterdir()):
            if f.is_file():
                partes.append(f"| `{f.name}` | {mb(f.stat().st_size)} | "
                              f"{descr.get(f.name, 'derivado')} |")

    partes += [
        "",
        "## Como conferir um número, ao vivo",
        "",
        "1. **A série do SGS existe e é a certa?**",
        "   `data_processed/catalogo_series_sgs.csv` traz o nome oficial lido do catálogo do",
        "   BCB e o status `CONFIRMADO`. O XML de resposta está em",
        "   `data_raw/sgs/catalogo/sgs_{codigo}_catalogo.xml`.",
        "",
        "2. **De onde vem um campo do IF.data?**",
        "   `data_processed/dicionario_campos_ifdata.csv` — filtre pelo nome da coluna e veja",
        "   o relatório, a data de geração e a **fórmula COSIF** da conta.",
        "",
        "3. **O arquivo bruto é o que dizemos que é?**",
        "   `data_raw/manifesto_coleta.csv` tem URL, hora da extração e SHA-256 de cada",
        "   arquivo. `src/audita_raw.py` revalida a integridade de todos.",
        "",
        "4. **O decodificador está certo?**",
        "   `src/testa_extracao.py` compara três valores com a tela oficial do IF.data.",
        "",
        "5. **Como um indicador vira score?**",
        "   `src/rastreia_cartao.py` mostra a cadeia numa instituição real: valor → percentil",
        "   → média → corte → carteira exposta.",
        "",
        "## Nota sobre o que está no GitHub",
        "",
        f"Os brutos do IF.data ocupam {mb(tamanho(DATA_RAW / 'ifdata'))} em disco "
        "(guardados comprimidos; o SHA-256 registrado é o do arquivo original) e **não** são",
        "versionados — são reproduzíveis por `src/coleta_ifdata.py`. O que vai ao "
        "repositório é o manifesto",
        "(com URL e SHA-256 de cada arquivo), os XML do catálogo do SGS e os derivados que o",
        "painel usa. A rastreabilidade não depende de guardar os blobs: depende do manifesto",
        "e do script que os regenera.",
    ]

    DOCS.mkdir(parents=True, exist_ok=True)
    (DOCS / "ONDE_ESTAO_OS_DADOS.md").write_text("\n".join(partes), encoding="utf-8")
    print("\n".join(partes[:40]))
    print(f"\n... gerado em docs/ONDE_ESTAO_OS_DADOS.md")


if __name__ == "__main__":
    main()
