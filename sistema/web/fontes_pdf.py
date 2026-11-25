"""Instancias estaticas da Adwaita Sans para os PDFs.

A Adwaita Sans oficial e uma fonte variavel (eixos wght/opsz). O Chromium incorpora fontes
variaveis como Type3 sem nome, o que impede conferir no PDF que so ha Adwaita (DMA v3, secao 08)
e piora a renderizacao em alguns leitores. Aqui geramos instancias estaticas nomeadas, a partir
do arquivo oficial copiado de _planejamento/brand/fonts, sem alterar o desenho da fonte.
"""

from __future__ import annotations

from pathlib import Path

FONTES_DIR = Path(__file__).resolve().parent / "static" / "brand" / "fonts"
ESTATICAS_DIR = FONTES_DIR / "estaticas"

# (arquivo de origem, peso, sufixo PostScript, estilo CSS)
INSTANCIAS = (
    ("AdwaitaSans-Regular.ttf", 400, "Regular", "normal"),
    ("AdwaitaSans-Regular.ttf", 650, "SemiBold", "normal"),
    ("AdwaitaSans-Regular.ttf", 700, "Bold", "normal"),
    ("AdwaitaSans-Italic.ttf", 400, "Italic", "italic"),
    ("AdwaitaSans-Italic.ttf", 650, "SemiBoldItalic", "italic"),
    ("AdwaitaSans-Italic.ttf", 700, "BoldItalic", "italic"),
)


def _nomear(fonte, sufixo: str) -> None:
    nome = fonte["name"]
    familia = "Adwaita Sans"
    ps = f"AdwaitaSans-{sufixo}"
    for rec in list(nome.names):
        if rec.nameID in (1, 16):
            nome.setName(familia, rec.nameID, rec.platformID, rec.platEncID, rec.langID)
        elif rec.nameID in (2, 17):
            nome.setName(sufixo, rec.nameID, rec.platformID, rec.platEncID, rec.langID)
        elif rec.nameID == 4:
            nome.setName(f"{familia} {sufixo}", 4, rec.platformID, rec.platEncID, rec.langID)
        elif rec.nameID == 6:
            nome.setName(ps, 6, rec.platformID, rec.platEncID, rec.langID)


def garantir_fontes_estaticas() -> list[tuple[Path, int, str]]:
    """Retorna [(arquivo, peso, estilo)] das instancias estaticas; gera apenas se ausentes em ambiente gravavel."""
    prontas = [(ESTATICAS_DIR / f"AdwaitaSans-{sufixo}.ttf", peso, estilo) for _, peso, sufixo, estilo in INSTANCIAS]
    if all(p.exists() for p, _, _ in prontas):
        return prontas

    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    ESTATICAS_DIR.mkdir(parents=True, exist_ok=True)
    saida = []
    for origem, peso, sufixo, estilo in INSTANCIAS:
        destino = ESTATICAS_DIR / f"AdwaitaSans-{sufixo}.ttf"
        if not destino.exists():
            var = TTFont(FONTES_DIR / origem)
            inst = instancer.instantiateVariableFont(var, {"wght": peso, "opsz": 14})
            _nomear(inst, sufixo)
            inst.save(destino)
        saida.append((destino, peso, estilo))
    return saida
