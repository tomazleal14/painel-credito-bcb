"""
comum.py -- utilitarios compartilhados de coleta rastreavel.

Regra do projeto: todo arquivo baixado entra em data_raw/ INTOCADO e gera um
registro no manifesto (URL, data/hora de extracao, sha256, bytes). Nenhum numero
do painel pode existir sem uma linha correspondente no manifesto.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

# `requests` e importado DENTRO de baixa(), nao aqui no topo, de proposito:
# o painel importa este modulo apenas para saber os caminhos (DATA_PROC, DATA_RAW),
# e nao baixa nada em execucao. Com o import no topo, o app exigiria `requests`
# instalado no Streamlit Cloud so para ler uma constante -- e quebrava com
# ImportError quando a dependencia saiu do requirements.txt de execucao.
# Os scripts de coleta continuam funcionando normalmente (ver requirements-dev.txt).

RAIZ = Path(__file__).resolve().parent.parent
DATA_RAW = RAIZ / "data_raw"
DATA_PROC = RAIZ / "data_processed"
VERIFICACAO = RAIZ / "verificacao"
MANIFESTO = DATA_RAW / "manifesto_coleta.csv"

COLUNAS_MANIFESTO = [
    "arquivo", "fonte", "url", "data_extracao_utc",
    "sha256_conteudo", "bytes_originais", "armazenado_como", "observacao",
]

UA = {"User-Agent": "painel-credito-bcb/1.0 (trabalho academico FGV)"}


def agora_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def registra(arquivo: Path, fonte: str, url: str, conteudo: bytes,
             armazenado_como: str = "original", observacao: str = "") -> None:
    """Anexa uma linha ao manifesto de coleta."""
    MANIFESTO.parent.mkdir(parents=True, exist_ok=True)
    novo = not MANIFESTO.exists()
    with MANIFESTO.open("a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUNAS_MANIFESTO)
        if novo:
            w.writeheader()
        w.writerow({
            "arquivo": str(arquivo.relative_to(RAIZ)).replace("\\", "/"),
            "fonte": fonte,
            "url": url,
            "data_extracao_utc": agora_utc(),
            "sha256_conteudo": sha256_bytes(conteudo),
            "bytes_originais": len(conteudo),
            "armazenado_como": armazenado_como,
            "observacao": observacao,
        })


def baixa(url: str, destino: Path, fonte: str, comprimir: bool = False,
          observacao: str = "", tentativas: int = 4, pular_se_existe: bool = True) -> bytes:
    """Baixa uma URL, grava em data_raw e registra no manifesto.

    O sha256 registrado e SEMPRE o do conteudo original descomprimido, para que a
    verificacao independa da forma de armazenamento.
    """
    import requests  # dependencia de COLETA, nao de execucao do painel

    destino.parent.mkdir(parents=True, exist_ok=True)
    alvo = destino.with_suffix(destino.suffix + ".gz") if comprimir else destino

    if pular_se_existe and alvo.exists():
        if comprimir:
            with gzip.open(alvo, "rb") as fh:
                return fh.read()
        return alvo.read_bytes()

    # o endpoint do IF.data as vezes responde HTTP 200 com corpo "Erro interno - Internal
    # error"; sem validar o conteudo, esse lixo entraria em data_raw como se fosse dado.
    espera_json = destino.name.endswith(".json")

    ultimo_erro: Exception | None = None
    for i in range(tentativas):
        try:
            r = requests.get(url, headers=UA, timeout=180)
            r.raise_for_status()
            conteudo = r.content
            if espera_json:
                json.loads(conteudo.decode("utf-8"))
            break
        except Exception as e:  # noqa: BLE001
            ultimo_erro = e
            time.sleep(2 * (i + 1))
    else:
        raise RuntimeError(f"falha ao baixar {url}: {ultimo_erro}")

    if comprimir:
        with gzip.open(alvo, "wb") as fh:
            fh.write(conteudo)
    else:
        alvo.write_bytes(conteudo)

    registra(alvo, fonte, url, conteudo,
             armazenado_como="gzip do original" if comprimir else "original",
             observacao=observacao)
    return conteudo


def carrega_json(caminho: Path):
    if caminho.suffix == ".gz":
        with gzip.open(caminho, "rb") as fh:
            return json.loads(fh.read().decode("utf-8"))
    return json.loads(caminho.read_text(encoding="utf-8"))
