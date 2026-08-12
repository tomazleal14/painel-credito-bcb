"""
audita_raw.py -- verifica a INTEGRIDADE de tudo que esta em data_raw.

Motivo: o endpoint do IF.data devolve HTTP 200 com corpo "Erro interno - Internal error"
para alguns arquivos. Sem esta auditoria, um arquivo invalido entraria silenciosamente
no pipeline. Aqui ele e detectado, listado e (com --remover) apagado para nova coleta.
"""
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path

from comum import DATA_RAW


def le(caminho: Path) -> bytes:
    if caminho.suffix == ".gz":
        with gzip.open(caminho, "rb") as fh:
            return fh.read()
    return caminho.read_bytes()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--remover", action="store_true", help="apaga os arquivos invalidos")
    args = ap.parse_args()

    invalidos: list[tuple[Path, str]] = []
    total = 0
    for caminho in sorted(DATA_RAW.rglob("*")):
        if not caminho.is_file():
            continue
        nome = caminho.name
        if not (nome.endswith(".json") or nome.endswith(".json.gz")):
            continue
        total += 1
        try:
            bruto = le(caminho)
            if not bruto.strip():
                invalidos.append((caminho, "arquivo vazio"))
                continue
            json.loads(bruto.decode("utf-8"))
        except UnicodeDecodeError as e:
            invalidos.append((caminho, f"encoding: {e}"))
        except json.JSONDecodeError:
            trecho = bruto[:120].decode("utf-8", errors="replace").replace("\n", " ")
            invalidos.append((caminho, f"nao e JSON: {trecho!r}"))
        except Exception as e:  # noqa: BLE001
            invalidos.append((caminho, f"{type(e).__name__}: {e}"))

    print(f"arquivos JSON auditados: {total}")
    print(f"invalidos: {len(invalidos)}")
    for caminho, motivo in invalidos:
        print(f"  - {caminho.relative_to(DATA_RAW)}  ::  {motivo}")
        if args.remover:
            caminho.unlink()
    if invalidos and args.remover:
        print("\nremovidos -- rode a coleta novamente para rebaixar")
    elif invalidos:
        print("\nuse --remover para apagar e rebaixar")


if __name__ == "__main__":
    main()
