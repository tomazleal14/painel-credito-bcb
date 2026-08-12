"""
coleta_sgs.py -- coleta rastreavel de series do SGS/BCB, com VALIDACAO DE CATALOGO.

Trava contra "codigo plausivel porem errado" (risco 5 da proposta):
nenhuma serie e baixada antes de o nome oficial ser lido do catalogo do BCB e
conferido contra o nome que ESTE projeto espera. Se divergir, a serie e marcada
A CONFIRMAR e nao entra no painel.

Endpoints oficiais:
  catalogo  GET https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS
                ?method=getUltimoValorXML&codigoSerie={codigo}
            -> devolve <NOME>, <PERIODICIDADE>, <UNIDADE> oficiais
  dados     GET https://api.bcb.gov.br/dados/serie/bcdata.sgs.{codigo}/dados?formato=json
            (parametros opcionais dataInicial/dataFinal em dd/MM/aaaa)
"""
from __future__ import annotations

import html
import io
import json
import re
from pathlib import Path

import pandas as pd
import requests

from comum import DATA_PROC, DATA_RAW, UA, agora_utc, baixa, registra

RAW = DATA_RAW / "sgs"
CATALOGO = "https://www3.bcb.gov.br/wssgs/services/FachadaWSSGS?method=getUltimoValorXML&codigoSerie={cod}"
DADOS = "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{cod}/dados?formato=json"

DATA_INICIAL = "01/01/2015"  # folga para o deflator e para a tendencia historica

# codigo -> nome oficial ESPERADO (conferido na varredura do catalogo em 12/08/2026)
# papel: para que serve no painel.
SERIES = {
    433: ("Índice nacional de preços ao consumidor-amplo (IPCA)",
          "DEFLATOR - IPCA var.% mensal; base do indice de precos usado em todo o painel"),
    # --- P1: referencia de sistema para crescimento ---
    20539: ("Saldo da carteira de crédito - Total",
            "P1 - carteira do SFN (referencia de crescimento do sistema)"),
    20542: ("Saldo da carteira de crédito com recursos livres - Total",
            "P1 - carteira livre do SFN (recorte alternativo)"),
    20622: ("Saldo da carteira de crédito em relação ao PIB",
            "P1 - credito/PIB: contexto de ciclo (faixas de risco, nao limiar unico)"),
    # --- P2: referencia de sistema para modalidades de alto risco ---
    20572: ("Saldo da carteira de crédito com recursos livres rotativo - Pessoas físicas",
            "P2 - rotativo PF no sistema (referencia de concentracao em alto risco)"),
    20587: ("Saldo da carteira de crédito com recursos livres - Pessoas físicas - Cartão de crédito rotativo",
            "P2 - cartao rotativo PF no sistema"),
    20574: ("Saldo da carteira de crédito com recursos livres - Pessoas físicas - Crédito pessoal não consignado total",
            "P2 - credito pessoal nao consignado (sem garantia) no sistema"),
    20573: ("Saldo da carteira de crédito com recursos livres - Pessoas físicas - Cheque especial",
            "P2 - cheque especial PF no sistema"),
    # --- P3: referencia de sistema para deterioracao ---
    21082: ("Inadimplência da carteira de crédito - Total",
            "P3 - inadimplencia 90+ do SFN (referencia central de P3)"),
    21084: ("Inadimplência da carteira de crédito - Pessoas físicas - Total",
            "P3 - inadimplencia PF do SFN"),
    21112: ("Inadimplência da carteira de crédito com recursos livres - Pessoas físicas - Total",
            "P3 - inadimplencia PF livre (comparavel a Aula 3)"),
    21086: ("Inadimplência da carteira de crédito com recursos livres - Pessoas jurídicas - Total",
            "P3 - inadimplencia PJ livre (comparavel a Aula 3)"),
    21127: ("Inadimplência da carteira de crédito com recursos livres - Pessoas físicas - Cartão de crédito rotativo",
            "P3 - inadimplencia do rotativo: modalidade-farol da Aula 3"),
    21114: ("Inadimplência da carteira de crédito com recursos livres - Pessoas físicas - Crédito pessoal não consignado total",
            "P3 - inadimplencia do sem-garantia"),
}


def le_catalogo(cod: int) -> dict:
    """Le NOME/PERIODICIDADE/UNIDADE oficiais do catalogo do SGS e guarda o XML bruto."""
    url = CATALOGO.format(cod=cod)
    conteudo = baixa(url, RAW / "catalogo" / f"sgs_{cod}_catalogo.xml", fonte="BCB/SGS (catalogo)",
                     observacao=f"metadados oficiais da serie {cod}")
    txt = html.unescape(conteudo.decode("utf-8", errors="replace"))

    def tag(t: str) -> str:
        m = re.search(rf"<{t}>(.*?)</{t}>", txt, re.S)
        return m.group(1).strip() if m else ""

    return {"nome": tag("NOME"), "periodicidade": tag("PERIODICIDADE"), "unidade": tag("UNIDADE")}


def coleta() -> pd.DataFrame:
    linhas, dados_frames = [], []

    for cod, (nome_esperado, papel) in SERIES.items():
        meta = le_catalogo(cod)
        nome_oficial = meta["nome"]
        confere = (nome_oficial == nome_esperado)
        status = "CONFIRMADO" if confere else ("A CONFIRMAR" if nome_oficial else "INEXISTENTE")

        registro = {
            "codigo_sgs": cod,
            "nome_esperado": nome_esperado,
            "nome_oficial_catalogo": nome_oficial,
            "status": status,
            "periodicidade": meta["periodicidade"],
            "unidade": meta["unidade"],
            "papel_no_painel": papel,
            "url_catalogo": CATALOGO.format(cod=cod),
            "url_dados": DADOS.format(cod=cod),
            "data_extracao_utc": agora_utc(),
            "n_observacoes": 0,
            "primeira_obs": "",
            "ultima_obs": "",
        }

        if not confere:
            print(f"  [{status}] {cod}: catalogo diz '{nome_oficial}' -- NAO baixado")
            linhas.append(registro)
            continue

        url = DADOS.format(cod=cod) + f"&dataInicial={DATA_INICIAL}"
        conteudo = baixa(url, RAW / f"sgs_{cod}.json", fonte="BCB/SGS",
                         observacao=f"{nome_oficial} | unidade: {meta['unidade']}")
        obs = json.loads(conteudo.decode("utf-8"))
        df = pd.DataFrame(obs)
        df["data"] = pd.to_datetime(df["data"], format="%d/%m/%Y")
        df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
        df["codigo_sgs"] = cod
        dados_frames.append(df[["codigo_sgs", "data", "valor"]])

        registro.update({
            "n_observacoes": len(df),
            "primeira_obs": df["data"].min().strftime("%Y-%m-%d"),
            "ultima_obs": df["data"].max().strftime("%Y-%m-%d"),
        })
        print(f"  [OK] {cod}: {len(df)} obs ({registro['primeira_obs']}..{registro['ultima_obs']}) "
              f"| {meta['unidade']} | {nome_oficial[:60]}")
        linhas.append(registro)

    DATA_PROC.mkdir(parents=True, exist_ok=True)
    cat = pd.DataFrame(linhas)
    cat.to_csv(DATA_PROC / "catalogo_series_sgs.csv", index=False, encoding="utf-8-sig")

    if dados_frames:
        painel = pd.concat(dados_frames, ignore_index=True)
        painel.to_parquet(DATA_PROC / "sgs_series.parquet", index=False)
        print(f"\n  series confirmadas: {(cat['status'] == 'CONFIRMADO').sum()}/{len(cat)}")
        print(f"  observacoes gravadas: {len(painel)}")
    return cat


if __name__ == "__main__":
    print(f"[{agora_utc()}] SGS -- validacao de catalogo + coleta")
    coleta()
