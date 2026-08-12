"""
textos.py -- carrega os textos do painel a partir de textos.toml.

O conteudo editavel NAO vive aqui: vive em textos.toml, na raiz do projeto, para que se
possa mudar qualquer frase da tela sem tocar em codigo Python.

Este modulo faz tres coisas:
  1. le o TOML (tomllib e biblioteca padrao do Python 3.11+, sem dependencia nova);
  2. valida que os 12 blocos de visualizacao existem e tem os tres textos obrigatorios
     (Leitura / Referencia / Consequencia) -- a regra do trabalho;
  3. devolve tudo num objeto Textos, RECARREGAVEL.

Por que recarregavel: o Python guarda modulos importados em cache, entao um textos.toml
editado com o painel aberto nao teria efeito ate reiniciar o processo. Como o app chama
`carrega(mtime_do_arquivo)` dentro de um cache do Streamlit, salvar o arquivo muda o
mtime, invalida o cache e o texto novo aparece ao recarregar a pagina -- sem reiniciar.

Se o arquivo tiver erro de sintaxe, `erro` guarda a mensagem com o numero da linha e o
app mostra o aviso na tela em vez de quebrar.
"""
from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ARQUIVO = Path(__file__).resolve().parent.parent / "textos.toml"

# os 12 blocos de visualizacao, na ordem em que aparecem no painel
BLOCOS = ["p1_1", "p1_2", "p1_3", "p1_4",
          "p2_1", "p2_2", "p2_3", "p2_4",
          "p3_1", "p3_2", "p3_3", "p3_4"]
OBRIGATORIOS = ("titulo", "leitura", "referencia", "consequencia")


def _limpa(v):
    """Junta as quebras de linha do TOML numa unica linha e remove espacos duplicados."""
    return " ".join(v.split()) if isinstance(v, str) else v


def md_html(s: str) -> str:
    """Converte a formatacao inline do Markdown para HTML.

    Necessario porque varios textos sao injetados dentro de <div> proprias (cabecalho,
    cartoes, blocos de leitura). Nesses lugares o Streamlit NAO interpreta Markdown --
    o `**negrito**` apareceria literal na tela. Aqui a conversao e feita a mao, para o
    subconjunto que o textos.toml promete suportar.

    Ordem importa: ** antes de *, senao o negrito seria consumido como italico.
    """
    if not isinstance(s, str):
        return s
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)          # **negrito**
    s = re.sub(r"(?<![\*\w])\*([^*]+?)\*(?!\*)", r"<i>\1</i>", s)   # *italico*
    s = re.sub(r"`([^`]+?)`", r"<code>\1</code>", s)       # `codigo`
    return s


@dataclass
class Textos:
    dados: dict = field(default_factory=dict)
    LRC: dict = field(default_factory=dict)
    erro: str | None = None
    avisos: list = field(default_factory=list)

    def txt(self, caminho: str, padrao: str = "") -> str:
        """Le um texto por caminho pontilhado, ex.: txt('cabecalho.titulo').

        Ja devolve o Markdown inline convertido para HTML, porque quase todo texto do
        painel e injetado dentro de <div> proprias. Para o texto cru, use `bruto`.
        """
        return md_html(self.bruto(caminho, padrao))

    def bruto(self, caminho: str, padrao: str = "") -> str:
        """Igual a txt(), mas sem converter Markdown -- para st.markdown()."""
        no = self.dados
        for parte in caminho.split("."):
            if not isinstance(no, dict) or parte not in no:
                return padrao or f"({caminho} não definido em textos.toml)"
            no = no[parte]
        return _limpa(no) if isinstance(no, str) else no

    def lrc(self, chave: str, campo: str) -> str:
        """Texto de um bloco de visualizacao, com Markdown ja convertido."""
        return md_html(self.LRC.get(chave, {}).get(campo, ""))

    @property
    def aparencia(self) -> dict:
        return self.dados.get("aparencia", {})

    @property
    def glossario_indicadores(self) -> dict:
        return self.dados.get("glossario_indicadores", {})

    @property
    def NAO_PERMITE_CONCLUIR(self) -> str:
        lim = self.dados.get("limites", {})
        titulo = lim.get("titulo", "O que este painel não permite concluir")
        return f"### {titulo}\n\n{lim.get('corpo', '')}"


def carrega(_assinatura: float | None = None) -> Textos:
    """Le textos.toml. O parametro `_assinatura` (mtime do arquivo) existe so para
    servir de chave de cache no app -- nao e usado aqui dentro."""
    t = Textos()
    try:
        with ARQUIVO.open("rb") as fh:
            t.dados = tomllib.load(fh)
    except FileNotFoundError:
        t.erro = f"textos.toml não encontrado em {ARQUIVO}"
        return t
    except tomllib.TOMLDecodeError as e:
        t.erro = (f"Erro de sintaxe em textos.toml: {e}\n\n"
                  "Causas comuns: aspas triplas não fechadas, aspas simples no lugar de "
                  "triplas, ou um bloco [nome] repetido.")
        return t
    except Exception as e:  # noqa: BLE001
        t.erro = f"Não foi possível ler textos.toml: {type(e).__name__}: {e}"
        return t

    for b in BLOCOS:
        bloco = t.dados.get(b, {})
        if not bloco:
            t.avisos.append(f"bloco [{b}] ausente")
            t.LRC[b] = {k: f"(texto de {b}.{k} não definido em textos.toml)"
                        for k in OBRIGATORIOS}
            continue
        faltando = [k for k in OBRIGATORIOS if not bloco.get(k)]
        if faltando:
            t.avisos.append(f"bloco [{b}] sem: {', '.join(faltando)}")
        t.LRC[b] = {k: _limpa(bloco.get(k, f"(faltando: {k})")) for k in OBRIGATORIOS}
    return t


def assinatura_arquivo() -> float:
    """mtime de textos.toml -- muda a cada salvamento e invalida o cache do app."""
    try:
        return ARQUIVO.stat().st_mtime
    except OSError:
        return 0.0


# compatibilidade para scripts que importam direto (fora do Streamlit)
_padrao = carrega()
LRC = _padrao.LRC
NAO_PERMITE_CONCLUIR = _padrao.NAO_PERMITE_CONCLUIR
erro_carregamento = _padrao.erro
avisos = _padrao.avisos
txt = _padrao.txt
