"""Ajudantes compartilhados pelos roteiros das estacoes (cartoes, navegacao, localizacao de blocos)."""

from __future__ import annotations

from typing import Callable

from sistema.video.motor_video import Cena, F, Gravacao

LOGO = '<img src="/static/brand/logo_prisma_jrna_hd.png" alt="PRISMA JRNA">'


def cartao_abertura(titulo: str, subtitulo: str) -> Callable[[Gravacao], None]:
    def preparar(g: Gravacao) -> None:
        g.cartao(f"{LOGO}<h1>{titulo}</h1><div class='rule'></div><p>Tutorial da plataforma contábil · Dossiê 1</p><p>{subtitulo}</p>")
    return preparar


def cartao_resumo(titulo: str, itens: list[str], proximo: str) -> Callable[[Gravacao], None]:
    def preparar(g: Gravacao) -> None:
        corpo = "".join(f"<p>{i}. {t}</p>" for i, t in enumerate(itens, start=1))
        g.cartao(f"{LOGO}<h1>{titulo}</h1><div class='rule'></div>{corpo}<p style='margin-top:18px'>{proximo}</p>")
    return preparar


def ir_por_menu(rota: str, tag: str) -> Callable[[Gravacao], None]:
    """Clique visivel no menu lateral (sem narracao) ate a estacao."""
    link = f'nav.nav-links a[href="{rota}"]'

    def antes(g: Gravacao) -> None:
        g.esperar(0.4)
        g.mover(link)
        g.destacar(link, 3)
        g.esperar(0.6)
        g.limpar()
        with g.page.expect_navigation(wait_until="networkidle"):
            g.mover(link, clicar=True)
        g.page.evaluate("document.fonts.ready")
        g.page.mouse.move(*g.mouse)
        g.tag(tag)
    return antes


def saltar(g: Gravacao, sel: str, margem: int = 70) -> None:
    """Posiciona a pagina instantaneamente (estado inicial da cena, fora do video)."""
    g.page.evaluate(
        "([s, m]) => { const el = document.querySelector(s); if (el) window.scrollTo(0, el.getBoundingClientRect().top + scrollY - m); }",
        [sel, margem],
    )


def card(g: Gravacao, titulo: str, nome: str) -> str:
    """Marca o card cujo titulo (h3) contem `titulo` e devolve um seletor CSS estavel para ele."""
    g.page.evaluate(
        """([t, n]) => { const h = [...document.querySelectorAll('h3')].find(x => x.textContent.includes(t));
                         const c = h && (h.closest('.card') || h.closest('section')); if (c) c.setAttribute('data-v', n); }""",
        [titulo, nome],
    )
    return f'[data-v="{nome}"]'


def fim(titulo: str, itens: list[str], proximo: str, falas: list) -> Cena:
    return Cena("Encerramento", falas, preparar=cartao_resumo(titulo, itens, proximo), pausa_final=1.5)


__all__ = ["Cena", "F", "Gravacao", "LOGO", "card", "cartao_abertura", "cartao_resumo", "fim", "ir_por_menu", "saltar"]
