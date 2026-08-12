"""busca_campo.py -- procura um termo no dicionario de campos do IF.data (info{AAAAMM}.json)."""
from __future__ import annotations

import argparse
import unicodedata

from comum import DATA_RAW, carrega_json

RAW = DATA_RAW / "ifdata"


def normaliza(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", (s or "").lower())
                   if unicodedata.category(c) != "Mn")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("termo")
    ap.add_argument("--data-base", type=int, action="append", required=True)
    args = ap.parse_args()

    alvo = normaliza(args.termo)
    for dt in args.data_base:
        caminho = RAW / str(dt) / f"info{dt}.json"
        if not caminho.exists():
            print(f"== {dt}: info ausente (nao coletado)")
            continue
        info = carrega_json(caminho)
        achados = [i for i in info if alvo in normaliza(i.get("n", ""))]
        print(f"== {dt}: {len(achados)} campo(s) com '{args.termo}' (de {len(info)})")
        for i in achados:
            print(f"   [{i['id']}] {i.get('n')}")
            if i.get("d") and i["d"] != i.get("n"):
                print(f"        COSIF/def: {str(i['d'])[:160]}")


if __name__ == "__main__":
    main()
