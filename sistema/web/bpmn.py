"""Diagrama BPMN 2.0 vetorial (SVG puro) gerado das etapas de erp.processo_legalizacao_etapa.

Raias verticais (Sócias · Escritório/RT · Órgãos DF e RFB) e fluxo de cima para baixo, para que
o processo inteiro caiba em uma única página A4 retrato (requisito H7 da matriz), sem internet nem CDN.
Etapas com classificação de risco 'alto'/'alto_na' entram atrás de um gateway exclusivo de risco.
"""

from __future__ import annotations

import textwrap
from html import escape
from typing import Any

RAIAS = (
    ("socias", "Sócias / requerentes"),
    ("escritorio_contabil", "Escritório / contadora RT"),
    ("orgaos_publicos", "Órgãos públicos DF e RFB"),
)
W = 690            # largura em unidades SVG (≈ 170 mm no PDF → fonte 10 ≈ 7 pt)
CAB = 30           # cabeçalho das raias
LANE_W = W / 3
BOX_W, BOX_H = 196, 44
PASSO = 54         # distância vertical entre etapas
EV_PASSO, GW_PASSO = 34, 46
G800, G900, C700, M500, L300, N50 = "#1F2937", "#111827", "#374151", "#6B7280", "#D1D5DB", "#F9FAFB"


def _x_raia(raia: str) -> float:
    idx = next((i for i, (k, _) in enumerate(RAIAS) if k == raia), 1)
    return idx * LANE_W + LANE_W / 2


def _linhas(nome: str, max_chars: int = 31, max_linhas: int = 2) -> list[str]:
    ls = textwrap.wrap(nome, max_chars) or [""]
    if len(ls) > max_linhas:
        ls = ls[:max_linhas]
        ls[-1] = ls[-1][: max_chars - 1].rstrip() + "…"
    return ls


def _seta(pts: list[tuple[float, float]], rotulo: str = "") -> str:
    d = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    s = f'<path d="{d}" fill="none" stroke="{C700}" stroke-width="1.1" marker-end="url(#seta)"/>'
    if rotulo:
        (x1, y1), (x2, y2) = pts[0], pts[1]
        s += f'<text x="{(x1 + x2) / 2 + 4:.1f}" y="{(y1 + y2) / 2 - 3:.1f}" font-size="8.5" fill="{M500}">{escape(rotulo)}</text>'
    return s


def _ortogonal(x1: float, y1: float, x2: float, y2: float) -> list[tuple[float, float]]:
    if abs(x1 - x2) < 0.5:
        return [(x1, y1), (x2, y2)]
    ym = y2 - 9
    return [(x1, y1), (x1, ym), (x2, ym), (x2, y2)]


def gerar_svg_bpmn(etapas: list[dict[str, Any]]) -> str:
    """Retorna o SVG (string) do processo de abertura com raias, eventos, tarefas e gateway."""
    etapas = sorted(etapas, key=lambda e: e["ordem"])
    nos: list[dict[str, Any]] = []
    y = CAB + 10
    primeira = etapas[0]["raia_responsavel"] if etapas else "socias"
    nos.append({"tipo": "inicio", "x": _x_raia(primeira), "y": y, "h": 22})
    y += EV_PASSO
    for e in etapas:
        risco = e.get("classificacao_risco") in ("alto", "alto_na")
        if risco:
            nos.append({"tipo": "gateway", "x": _x_raia(e["raia_responsavel"]), "y": y, "h": 30})
            y += GW_PASSO
        nos.append({"tipo": "tarefa", "x": _x_raia(e["raia_responsavel"]), "y": y, "h": BOX_H, "e": e, "risco": risco})
        y += PASSO
    ultima = etapas[-1]["raia_responsavel"] if etapas else "socias"
    nos.append({"tipo": "fim", "x": _x_raia(ultima), "y": y, "h": 22})
    altura = y + 22 + 12

    p: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {altura:.0f}" width="{W}" height="{altura:.0f}" '
        f'role="img" aria-label="Diagrama BPMN do processo de abertura no Distrito Federal" '
        f'font-family="Adwaita Sans, Segoe UI, sans-serif">',
        f'<defs><marker id="seta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        f'<path d="M0,0 L10,5 L0,10 z" fill="{C700}"/></marker></defs>',
    ]
    # Raias
    for i, (_, nome) in enumerate(RAIAS):
        x0 = i * LANE_W
        p.append(f'<rect x="{x0:.1f}" y="0" width="{LANE_W:.1f}" height="{altura:.0f}" fill="{N50 if i % 2 == 0 else "#FFFFFF"}" stroke="{L300}" stroke-width="0.8"/>')
        p.append(f'<rect x="{x0:.1f}" y="0" width="{LANE_W:.1f}" height="{CAB}" fill="{G800}"/>')
        p.append(f'<text x="{x0 + LANE_W / 2:.1f}" y="19" text-anchor="middle" font-size="10.5" font-weight="650" fill="#FFFFFF">{escape(nome)}</text>')

    def topo(n: dict[str, Any]) -> float:
        return n["y"]

    def base(n: dict[str, Any]) -> float:
        return n["y"] + n["h"]

    # Arestas
    for a, b in zip(nos, nos[1:]):
        if a["tipo"] == "tarefa" and a.get("risco"):
            continue  # saída da tarefa de alto risco é tratada abaixo
        if a["tipo"] == "gateway":
            # ramo "alto risco" para a tarefa logo abaixo
            p.append(_seta(_ortogonal(a["x"], base(a), b["x"], topo(b)), "Alto risco"))
            continue
        p.append(_seta(_ortogonal(a["x"], base(a), b["x"], topo(b))))
    for i, n in enumerate(nos):
        if n["tipo"] != "gateway" or i + 2 >= len(nos):
            continue
        tarefa_risco, proximo = nos[i + 1], nos[i + 2]
        # ramo "baixo risco": contorna a tarefa de alto risco pela lateral da raia
        lado = n["x"] + LANE_W / 2 - 8
        meio = n["y"] + n["h"] / 2
        p.append(_seta([(n["x"] + 15, meio), (lado, meio), (lado, topo(proximo) - 9), (proximo["x"], topo(proximo) - 9), (proximo["x"], topo(proximo))], "Baixo risco"))
        p.append(_seta(_ortogonal(tarefa_risco["x"], base(tarefa_risco), proximo["x"], topo(proximo))))

    # Nós
    for n in nos:
        x, y0 = n["x"], n["y"]
        if n["tipo"] == "inicio":
            p.append(f'<circle cx="{x:.1f}" cy="{y0 + 11:.1f}" r="10" fill="#FFFFFF" stroke="{G800}" stroke-width="1.4"/>')
            p.append(f'<text x="{x + 16:.1f}" y="{y0 + 15:.1f}" font-size="9" fill="{C700}">Início</text>')
        elif n["tipo"] == "fim":
            p.append(f'<circle cx="{x:.1f}" cy="{y0 + 11:.1f}" r="10" fill="#FFFFFF" stroke="{G900}" stroke-width="3"/>')
            p.append(f'<text x="{x + 16:.1f}" y="{y0 + 15:.1f}" font-size="9" fill="{C700}">Fim: apto a operar</text>')
        elif n["tipo"] == "gateway":
            c = y0 + 15
            p.append(f'<path d="M{x:.1f},{c - 15:.1f} L{x + 15:.1f},{c:.1f} L{x:.1f},{c + 15:.1f} L{x - 15:.1f},{c:.1f} z" fill="#FFFFFF" stroke="{G800}" stroke-width="1.3"/>')
            p.append(f'<path d="M{x - 5:.1f},{c - 5:.1f} L{x + 5:.1f},{c + 5:.1f} M{x + 5:.1f},{c - 5:.1f} L{x - 5:.1f},{c + 5:.1f}" stroke="{G800}" stroke-width="1.6"/>')
            p.append(f'<text x="{x - 20:.1f}" y="{c + 4:.1f}" text-anchor="end" font-size="9" fill="{C700}">Risco RLE?</text>')
        else:
            e = n["e"]
            bx, by = x - BOX_W / 2, y0
            tracejado = ' stroke-dasharray="4 3"' if n.get("risco") else ""
            p.append(f'<rect x="{bx:.1f}" y="{by:.1f}" width="{BOX_W}" height="{BOX_H}" rx="6" fill="#FFFFFF" stroke="{G800}" stroke-width="1.1"{tracejado}/>')
            cab = f'{e["ordem"]} · {e["codigo"]}'
            p.append(f'<text x="{bx + 7:.1f}" y="{by + 13:.1f}" font-size="9" font-family="Adwaita Mono, Consolas, monospace" fill="{M500}">{escape(cab)}</text>')
            for k, ln in enumerate(_linhas(str(e["nome_etapa"]))):
                p.append(f'<text x="{bx + 7:.1f}" y="{by + 26 + k * 11.5:.1f}" font-size="10" fill="{G900}">{escape(ln)}</text>')
    p.append("</svg>")
    return "".join(p)
