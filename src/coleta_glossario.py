"""
coleta_glossario.py -- baixa o dicionario OFICIAL das siglas de filtro do IF.data.

Motivo: a barra de filtros mostra codigos como "b1", "b3S", "S1" -- que nao dizem nada
para quem nao convive com o IF.data. As descricoes NAO sao escritas de memoria: vem do
arquivo `filtro{AAAAMM}.json`, o mesmo que a interface oficial usa para montar seus menus.

Endpoint: https://www3.bcb.gov.br/ifdata/rest/arquivos?nomeArquivo=...filtro{AAAAMM}.json
Saida   : data_processed/glossario_filtros.csv (dimensao, codigo, descricao)
"""
from __future__ import annotations

import json
from urllib.parse import quote

import pandas as pd

from comum import DATA_PROC, DATA_RAW, agora_utc, baixa

BASE = "https://www3.bcb.gov.br/ifdata/rest/arquivos?nomeArquivo="
RAW = DATA_RAW / "ifdata"

# dimensao no arquivo -> nome curto usado no painel
DIMENSOES = {
    "TCB": "tcb",
    "SR": "segmento_sr",
    "TC": "controle",
    "TD": "consolidacao",
}


def main(data_base: int = 202603, pasta_remota: str = "ifdata_2025_2030") -> None:
    nome = f"{pasta_remota}//{data_base}/filtro{data_base}.json"
    conteudo = baixa(BASE + quote(nome, safe=""),
                     RAW / str(data_base) / f"filtro{data_base}.json",
                     fonte="BCB/IF.data",
                     observacao=f"dicionario de siglas dos filtros, data-base {data_base}")
    filtros = json.loads(conteudo.decode("utf-8"))

    linhas = []
    for f in filtros:
        rotulo = f.get("n", "")
        sigla = rotulo.split(" - ")[0].strip()
        curto = DIMENSOES.get(sigla)
        if not curto:
            continue
        for d in f.get("d", []):
            desc = d.get("n", "")
            # o proprio BCB escreve "b1 - Banco Comercial..."; separa codigo e texto
            codigo = d.get("v", "")
            texto = desc.split(" - ", 1)[1] if " - " in desc else desc
            linhas.append({
                "dimensao": curto,
                "dimensao_rotulo": rotulo,
                "codigo": codigo,
                "descricao": texto.strip(),
                "data_base": data_base,
            })

    if not linhas:
        print("nenhuma dimensao reconhecida no arquivo de filtros")
        return

    df = pd.DataFrame(linhas).drop_duplicates(subset=["dimensao", "codigo"])

    # O arquivo do BCB rotula os segmentos apenas como "Segmento 1".."Segmento 5",
    # sem os criterios da Res. 4.553/2017. Em vez de escrever os limiares de memoria
    # -- o que violaria a regra de rastreabilidade do projeto --, acrescenta-se o que
    # e OBSERVAVEL nos proprios dados: quantas instituicoes ha em cada codigo e a
    # faixa de carteira que elas ocupam. E factual e verificavel.
    caminho = DATA_PROC / "app_indicadores.parquet"
    if not caminho.exists():
        caminho = DATA_PROC / "indicadores.parquet"
    if caminho.exists():
        p = pd.read_parquet(caminho, columns=["data_base", "tcb", "segmento_sr",
                                              "carteira_credito_real"])
        p = p[p["data_base"] == p["data_base"].max()]
        obs = []
        for r in df.itertuples():
            col = {"tcb": "tcb", "segmento_sr": "segmento_sr"}.get(r.dimensao)
            if not col:
                obs.append(("", "", ""))
                continue
            s = p[p[col] == r.codigo]["carteira_credito_real"].dropna()
            s = s[s > 0]
            obs.append((len(p[p[col] == r.codigo]),
                        f"{s.min()/1e9:.2f}" if len(s) else "",
                        f"{s.max()/1e9:.1f}" if len(s) else ""))
        df["n_instituicoes"] = [o[0] for o in obs]
        df["carteira_min_bi"] = [o[1] for o in obs]
        df["carteira_max_bi"] = [o[2] for o in obs]
        df["data_base_observado"] = int(p["data_base"].iloc[0])

    DATA_PROC.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATA_PROC / "glossario_filtros.csv", index=False, encoding="utf-8-sig")
    print(f"[{agora_utc()}] glossario: {len(df)} termos")
    for dim, g in df.groupby("dimensao"):
        print(f"\n  {dim} ({g['dimensao_rotulo'].iloc[0]})")
        for r in g.itertuples():
            extra = ""
            if getattr(r, "n_instituicoes", "") not in ("", None):
                extra = f"  [{r.n_instituicoes} IFs"
                if r.carteira_max_bi:
                    extra += f", carteira R$ {r.carteira_min_bi}–{r.carteira_max_bi} bi"
                extra += "]"
            print(f"    {r.codigo:5s} {r.descricao[:70]}{extra}")


if __name__ == "__main__":
    main()
