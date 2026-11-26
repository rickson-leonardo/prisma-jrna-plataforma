"""Formatacao compartilhada entre telas e PDFs: markdown seguro e numeros contabeis pt-BR."""

from __future__ import annotations

import re

import markdown
from markupsafe import Markup


def _md() -> markdown.Markdown:
    md = markdown.Markdown(extensions=["tables", "sane_lists"], output_format="html")
    # Bloqueia HTML cru vindo do banco: tudo vira texto escapado
    md.preprocessors.deregister("html_block")
    md.inlinePatterns.deregister("html")
    return md


_ITEM = re.compile(r"^\s*(?:[-*+]|\d+\.)\s")


def _separar_listas(txt: str) -> str:
    """Insere linha em branco antes de uma lista colada ao paragrafo (senao o markdown a ignora)."""
    out: list[str] = []
    for ln in txt.splitlines():
        if _ITEM.match(ln) and out and out[-1].strip() and not _ITEM.match(out[-1]) and not out[-1].lstrip().startswith("|"):
            out.append("")
        out.append(ln)
    return "\n".join(out)


def md_html(txt: str | None) -> Markup:
    """Converte markdown (negrito, listas, tabelas) em HTML sem permitir HTML embutido."""
    if not txt:
        return Markup("")
    html = _md().convert(_separar_listas(str(txt)))
    # DMA v3 §05: celulas alinhadas a direita (markdown ---:) viram coluna numerica mono
    html = re.sub(r'<(td|th) (?:align="right"|style="text-align: right;")>', r'<\1 class="num">', html)
    html = re.sub(r'<(td|th) (?:align="(?:left|center)"|style="text-align: (?:left|center);")>', r"<\1>", html)
    return Markup(html)


def md_inline(txt: str | None) -> Markup:
    """Markdown de uma linha (titulos): remove o <p> externo."""
    h = str(md_html(txt))
    return Markup(re.sub(r"^<p>(.*)</p>$", r"\1", h.strip(), flags=re.S))


def _br(v: float, casas: int = 2) -> str:
    return f"{abs(v):,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def brl(centavos: int | None) -> str:
    """Moeda em texto corrido: R$ 1.500,00 (negativo: -R$ 10,00)."""
    v = int(centavos or 0) / 100.0
    return ("-R$ " if v < 0 else "R$ ") + _br(v)


def brl_tab(centavos: int | None) -> str:
    """Valor em tabela (unidade no cabecalho): 1.500,00 · negativo (142,25) · zero –."""
    v = int(centavos or 0) / 100.0
    if abs(v) < 0.005:
        return "–"
    return f"({_br(v)})" if v < 0 else _br(v)


def pct_micro(micro: int | None, casas: int = 2) -> str:
    return _br(int(micro or 0) / 10_000.0, casas) + "%"


def num_br(v: float | int | None, casas: int = 2) -> str:
    if v is None:
        return "–"
    return ("-" if v < 0 else "") + _br(float(v), casas)


def tir_br(tir_pct: float | int | None, vpl_centavos: int | None = None) -> str:
    """TIR com '%'; quando nao ha taxa que zere o VPL, explica o motivo em vez de deixar em branco.

    Sem TIR e VPL negativo: o VPL fica abaixo de zero em qualquer taxa (nenhuma raiz real).
    Sem TIR e fluxos todos de mesmo sinal: tambem nao existe raiz.
    """
    if tir_pct is not None:
        return num_br(tir_pct) + "%"
    if vpl_centavos is not None and int(vpl_centavos) < 0:
        return "Inexistente (VPL negativo)"
    return "Inexistente"
