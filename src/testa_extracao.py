"""
testa_extracao.py -- prova de ponta a ponta do decodificador do IF.data.

Compara o valor extraido do JSON bruto com o valor EXIBIDO na tela oficial do
IF.data (https://www3.bcb.gov.br/ifdata/), capturado em 12/08/2026:

  Conglomerados Prudenciais (tipo 1009), data-base 03/2026, relatorio "Resumo",
  ITAU - PRUDENCIAL:
      Ativo Total          2.834.355.732  (R$ mil)
      Carteira de Credito  1.221.119.971  (R$ mil)
      Indice de Basileia   14,77%

Se o decodificador estiver certo, o bruto/1000 arredondado deve bater exatamente.
"""
from __future__ import annotations

import sys

from coleta_ifdata import extrai_valores

ESPERADO_TELA = {  # valores como exibidos na interface oficial (R$ mil)
    "Ativo Total": 2_834_355_732,
    "Carteira de Crédito": 1_221_119_971,
}
ESPERADO_BASILEIA_PCT = 14.77


def main() -> int:
    df = extrai_valores(202603, 1009)
    if df.empty:
        print("FALHA: extracao vazia (rode a coleta do periodo 202603 com --tipo 1009)")
        return 1

    itau = df[(df["instituicao"].str.contains("ITAU", na=False))
              & (df["relatorio"] == "Resumo")]
    if itau.empty:
        print("FALHA: ITAU nao encontrado no relatorio Resumo")
        return 1

    nome = itau["instituicao"].iloc[0]
    print(f"instituicao encontrada: {nome}\n")

    ok = True
    for coluna, esperado_mil in ESPERADO_TELA.items():
        linha = itau[itau["coluna_nome"] == coluna]
        if linha.empty:
            print(f"  FALHA  {coluna}: coluna ausente")
            ok = False
            continue
        bruto = float(linha["valor"].iloc[0])
        obtido_mil = round(bruto / 1000)
        marca = "OK  " if obtido_mil == esperado_mil else "FALHA"
        if obtido_mil != esperado_mil:
            ok = False
        print(f"  {marca} {coluna}")
        print(f"        bruto (R$)      = {bruto:,.2f}")
        print(f"        /1000 (R$ mil)  = {obtido_mil:,}")
        print(f"        tela oficial    = {esperado_mil:,}")

    linha = itau[itau["coluna_nome"] == "Índice de Basileia"]
    if not linha.empty:
        bruto = float(linha["valor"].iloc[0])
        obtido = round(bruto * 100, 2)
        marca = "OK  " if obtido == ESPERADO_BASILEIA_PCT else "FALHA"
        if obtido != ESPERADO_BASILEIA_PCT:
            ok = False
        print(f"  {marca} Índice de Basileia")
        print(f"        bruto (fracao)  = {bruto}")
        print(f"        x100 (%)        = {obtido}")
        print(f"        tela oficial    = {ESPERADO_BASILEIA_PCT}")

    print("\n" + ("DECODIFICADOR VALIDADO" if ok else "DIVERGENCIA -- NAO USAR"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
