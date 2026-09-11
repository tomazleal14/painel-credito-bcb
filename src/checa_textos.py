"""
checa_textos.py -- o textos.toml carrega, e todo indicador ATIVO tem verbete?

Duas travas, as duas nascidas de falhas reais:

1. BOM. Editar o textos.toml com uma ferramenta que grava UTF-8 com BOM (o
   `Set-Content -Encoding utf8` do PowerShell faz isso) poe tres bytes invisiveis no
   inicio do arquivo, e o `tomllib` recusa com "Invalid statement at line 1, column 1".
   O painel cai inteiro por um caractere que nao se ve.

2. Verbete ausente. O glossario cobria so os 18 indicadores ativos na epoca em que foi
   escrito. Trocar um indicador -- que e uma funcionalidade do painel, pensada para ser
   usada AO VIVO na apresentacao -- podia trazer para a tela um indicador sem "o que
   mede", sem dica ao passar o mouse e com linha vazia na tabela do glossario.

Falha (exit 1) se o arquivo nao carregar ou se algum indicador ATIVO nao tiver verbete.
Avisa, sem falhar, sobre os indicadores do pool de troca que ainda nao tem.
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import catalogo

RAIZ = Path(__file__).resolve().parent.parent
ARQ = RAIZ / "textos.toml"


def main() -> int:
    bruto = ARQ.read_bytes()
    if bruto.startswith(b"\xef\xbb\xbf"):
        print("FALHA: textos.toml comeca com BOM (EF BB BF).")
        print("  O tomllib recusa o arquivo e o painel nao abre.")
        print("  Correcao: regravar sem BOM (no PowerShell, use")
        print("  [System.IO.File]::WriteAllText(caminho, texto) em vez de Set-Content).")
        return 1

    try:
        t = tomllib.loads(bruto.decode("utf-8"))
    except tomllib.TOMLDecodeError as e:
        print(f"FALHA: textos.toml nao e TOML valido -- {e}")
        return 1
    except UnicodeDecodeError as e:
        print(f"FALHA: textos.toml nao esta em UTF-8 -- {e}")
        return 1

    print(f"textos.toml carrega · {len(t)} secoes")

    gloss = t.get("glossario_indicadores", {})
    ativos, avisos = catalogo.carrega_ativos()
    for a in avisos:
        print(f"  aviso do catalogo: {a}")

    faltando_ativos, faltando_pool = [], []
    for ind in catalogo.CATALOGO:
        if not str(gloss.get(ind.chave, "")).strip():
            alvo = (faltando_ativos if ind.chave in ativos.get(ind.eixo, [])
                    else faltando_pool)
            alvo.append(ind.chave)

    n_ativos = sum(len(v) for v in ativos.values())
    print(f"verbetes: {len(gloss)} · indicadores ativos: {n_ativos} · "
          f"catalogo: {len(catalogo.CATALOGO)}")

    if faltando_ativos:
        print(f"\nFALHA -- indicador ATIVO sem verbete ({len(faltando_ativos)}):")
        for c in faltando_ativos:
            print(f"  - {c} ({catalogo.rotulo(c)})")
        print("\n  Acrescente o verbete em [glossario_indicadores], no formato")
        print("  'o que mede | por que esta neste eixo | como ler'.")
        return 1

    if faltando_pool:
        print(f"\naviso -- no pool de troca, sem verbete ({len(faltando_pool)}):")
        for c in faltando_pool:
            print(f"  - {c} ({catalogo.rotulo(c)})")
        print("  Trocar um destes ao vivo deixa a dica e a tabela do glossario vazias.")

    print("\ntodo indicador ativo tem verbete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
