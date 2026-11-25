"""Motor de videos tutoriais: grava a plataforma REAL e sincroniza narracao e legendas.

Fidelidade: nada e desenhado ou simulado — o Edge (Playwright) abre o sistema Flask real,
lendo o PostgreSQL real, e cada cena executa cliques de verdade. Sobre a tela sao injetados
apenas elementos de apresentacao (cursor visivel, destaque, legenda, cartao de abertura).

Narracao: voz local do Windows (SAPI, "Microsoft Maria Desktop", pt-BR), sem enviar texto
para servicos externos. Uma faixa WAV por frase permite legendas com tempo exato.

Uso: ver roteiro_estacao1.py. Nenhum roteiro deve submeter formularios (nao grava no banco).
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import threading
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from sistema.config import PLATAFORMA_DIR

VIDEOS_DIR = PLATAFORMA_DIR / "exportacoes" / "videos"
CACHE_TTS = VIDEOS_DIR / "_tts"
# Narracao: "neural" (Microsoft Edge TTS, voz natural; o texto do roteiro e enviado ao servico
# da Microsoft — nunca coloque dados pessoais nas falas) ou "sapi" (voz local do Windows, offline).
MOTOR_TTS = "neural"
VOZ_NEURAL = "pt-BR-FranciscaNeural"     # alternativas: pt-BR-ThalitaMultilingualNeural, pt-BR-AntonioNeural
VELOCIDADE_NEURAL = "+0%"
VOZ = "Microsoft Maria Desktop"
VELOCIDADE = 1   # SAPI: -10 a 10

# Pronuncia para a voz neural (a legenda continua com a grafia oficial)
PRONUNCIA_NEURAL = {
    "CNAE 6920-6/02": "C N A E seis nove dois zero, traço seis, barra zero dois",
    "CNAEs": "C N A Es",
    "QSA": "Q S A",
    " RT": " R T",
    "CRC": "C R C",
    "1.1": "um ponto um", "1.2": "um ponto dois", "1.3": "um ponto três", "1.4": "um ponto quatro", "1.5": "um ponto cinco",
    "20000": "vinte mil",
}
LARGURA, ALTURA = 1600, 900   # gravado em 1600x900 e ampliado para 1920x1080 no MP4
PAUSA_FRASE = 0.35

# ---------------------------------------------------------------------------
# Camada de apresentacao injetada em toda pagina (nao altera o sistema)
# ---------------------------------------------------------------------------
OVERLAY_JS = r"""
(() => {
 const montar = () => {
  if (window.__v) return;
  const css = `
  #v-cursor{position:fixed;left:0;top:0;width:22px;height:22px;z-index:2147483647;pointer-events:none;transform:translate(-100px,-100px);transition:transform .02s linear}
  #v-cursor svg{filter:drop-shadow(0 1px 2px rgba(0,0,0,.35))}
  #v-ripple{position:fixed;width:34px;height:34px;margin:-17px 0 0 -17px;border-radius:50%;border:3px solid #1E40AF;z-index:2147483646;pointer-events:none;opacity:0}
  #v-ripple.on{animation:vr .5s ease-out}
  @keyframes vr{from{opacity:.9;transform:scale(.4)}to{opacity:0;transform:scale(1.6)}}
  #v-leg{position:fixed;left:50%;bottom:26px;transform:translateX(-50%);max-width:78%;background:rgba(17,24,39,.9);color:#fff;
    font:500 19px/1.45 "Adwaita Sans","Segoe UI",sans-serif;padding:10px 18px;border-radius:8px;z-index:2147483645;text-align:center;pointer-events:none}
  #v-leg:empty{display:none}
  #v-tag{position:fixed;right:18px;bottom:30px;background:#1F2937;color:#fff;font:650 13px "Adwaita Sans",sans-serif;padding:6px 12px;border-radius:6px;z-index:2147483645;pointer-events:none;letter-spacing:.02em}
  #v-tag:empty{display:none}
  #v-hl{position:fixed;border:3px solid #1E40AF;border-radius:8px;box-shadow:0 0 0 9999px rgba(17,24,39,.18);z-index:2147483644;pointer-events:none;transition:all .35s ease;opacity:0}
  #v-card{position:fixed;inset:0;background:#fff;z-index:2147483646;display:none;flex-direction:column;align-items:center;justify-content:center;font-family:"Adwaita Sans",sans-serif;color:#111827;text-align:center}
  #v-card .band{position:absolute;top:0;left:0;right:0;height:26px;background:#1F2937}
  #v-card img{height:150px;margin-bottom:26px}
  #v-card h1{font-size:34px;margin:0 0 10px;font-weight:700}
  #v-card p{font-size:18px;color:#6B7280;margin:4px 0;max-width:900px}
  #v-card .rule{width:60px;height:3px;background:#1F2937;margin:20px auto}`;
  const st = document.createElement('style'); st.textContent = css; document.documentElement.appendChild(st);
  const mk = (id, html='') => { const d = document.createElement('div'); d.id = id; d.innerHTML = html; document.documentElement.appendChild(d); return d; };
  const cur = mk('v-cursor', '<svg viewBox="0 0 24 24" width="22" height="22"><path d="M3 2l7 19 2.6-7.6L20 11z" fill="#111827" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>');
  const rip = mk('v-ripple'); const leg = mk('v-leg'); const tag = mk('v-tag'); const hl = mk('v-hl'); const card = mk('v-card');
  document.addEventListener('mousemove', e => { cur.style.transform = `translate(${e.clientX - 3}px,${e.clientY - 2}px)`; }, true);
  document.addEventListener('mousedown', e => { rip.style.left = e.clientX + 'px'; rip.style.top = e.clientY + 'px'; rip.classList.remove('on'); void rip.offsetWidth; rip.classList.add('on'); }, true);
  let timers = [];
  window.__v = {
    legendas(lista) { timers.forEach(clearTimeout); timers = []; lista.forEach(([t, ms]) => timers.push(setTimeout(() => { leg.textContent = t; }, ms))); },
    legenda(t) { timers.forEach(clearTimeout); timers = []; leg.textContent = t || ''; },
    tag(t) { tag.textContent = t || ''; },
    destacar(sel, pad = 6) {
      const el = sel && document.querySelector(sel);
      if (!el) { hl.style.opacity = 0; return; }
      const r = el.getBoundingClientRect();
      Object.assign(hl.style, { left: (r.left - pad) + 'px', top: (r.top - pad) + 'px', width: (r.width + 2 * pad) + 'px', height: (r.height + 2 * pad) + 'px', opacity: 1 });
    },
    limpar() { hl.style.opacity = 0; },
    cartao(html) { if (!html) { card.style.display = 'none'; return; } card.innerHTML = '<div class="band"></div>' + html; card.style.display = 'flex'; },
  };
 };
 if (document.documentElement && document.body) montar(); else document.addEventListener('DOMContentLoaded', montar);
})();
"""


@dataclass
class Frase:
    legenda: str
    fala: str = ""          # texto pronunciado (se vazio, usa a legenda)
    wav: Path | None = None
    dur: float = 0.0


@dataclass
class Cena:
    titulo: str
    frases: list[Frase]
    acoes: Callable[["Gravacao"], None] | None = None
    antes: Callable[["Gravacao"], None] | None = None   # sem narracao (ex.: navegar)
    depois: Callable[["Gravacao"], None] | None = None
    pausa_final: float = 0.7
    rota: str = "/"                  # pagina aberta (fora do video) antes da cena — modo por cena
    preparar: Callable[["Gravacao"], None] | None = None   # estado inicial silencioso, recortado do video
    tag: str | None = None           # etiqueta da estacao exibida durante a cena
    offsets: list[float] = field(default_factory=list)


def F(legenda: str, fala: str = "") -> Frase:
    return Frase(legenda, fala)


# ---------------------------------------------------------------------------
# Narracao offline (SAPI)
# ---------------------------------------------------------------------------
PS_TTS = r"""
param([string]$Lista)
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice('%VOZ%')
$s.Rate = %VEL%
$itens = Get-Content -Raw -Encoding UTF8 $Lista | ConvertFrom-Json
foreach ($i in $itens) {
  $s.SetOutputToWaveFile($i.arquivo)
  $s.Speak($i.texto)
  $s.SetOutputToNull()
}
"""


def _texto_neural(f: Frase) -> str:
    t = f.legenda
    for a, b in PRONUNCIA_NEURAL.items():
        t = t.replace(a, b)
    return t.replace("“", "").replace("”", "")


def _sintetizar_neural(cenas: list[Cena]) -> None:
    import asyncio

    import edge_tts
    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    pendentes = []
    for c in cenas:
        for f in c.frases:
            txt = _texto_neural(f)
            h = hashlib.sha1(f"{VOZ_NEURAL}|{VELOCIDADE_NEURAL}|{txt}".encode()).hexdigest()[:16]
            f.wav = CACHE_TTS / f"n_{h}.wav"
            if not f.wav.exists():
                pendentes.append((txt, f.wav))

    async def gerar() -> None:
        for txt, wav in pendentes:
            mp3 = wav.with_suffix(".mp3")
            await edge_tts.Communicate(txt, VOZ_NEURAL, rate=VELOCIDADE_NEURAL).save(str(mp3))
            subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", str(mp3), "-ar", "48000", "-ac", "1", str(wav)], check=True)
            mp3.unlink(missing_ok=True)

    if pendentes:
        asyncio.run(gerar())


def sintetizar(cenas: list[Cena]) -> None:
    CACHE_TTS.mkdir(parents=True, exist_ok=True)
    if MOTOR_TTS == "neural":
        _sintetizar_neural(cenas)
        for c in cenas:
            for f in c.frases:
                with wave.open(str(f.wav)) as w:
                    f.dur = w.getnframes() / float(w.getframerate())
        return
    pendentes = []
    for c in cenas:
        for f in c.frases:
            txt = f.fala or f.legenda
            h = hashlib.sha1(f"{VOZ}|{VELOCIDADE}|{txt}".encode()).hexdigest()[:16]
            f.wav = CACHE_TTS / f"{h}.wav"
            if not f.wav.exists():
                pendentes.append({"arquivo": str(f.wav), "texto": txt})
    if pendentes:
        lista = CACHE_TTS / "_lista.json"
        lista.write_text(json.dumps(pendentes, ensure_ascii=False), encoding="utf-8")
        ps1 = CACHE_TTS / "_tts.ps1"
        ps1.write_text("﻿" + PS_TTS.replace("%VOZ%", VOZ).replace("%VEL%", str(VELOCIDADE)), encoding="utf-8")
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1), "-Lista", str(lista)], check=True)
    for c in cenas:
        for f in c.frases:
            with wave.open(str(f.wav)) as w:
                f.dur = w.getnframes() / float(w.getframerate())


# ---------------------------------------------------------------------------
# Servidor Flask real em segundo plano
# ---------------------------------------------------------------------------
def iniciar_servidor() -> tuple[str, Callable[[], None]]:
    import logging

    from werkzeug.serving import make_server

    logging.getLogger("werkzeug").setLevel(logging.ERROR)

    from sistema.web.app import create_app

    srv = make_server("127.0.0.1", 0, create_app(), threaded=True)
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    return f"http://127.0.0.1:{srv.server_port}", srv.shutdown


# ---------------------------------------------------------------------------
# Gravacao
# ---------------------------------------------------------------------------
class Gravacao:
    def __init__(self, page, base: str) -> None:
        self.page = page
        self.base = base
        self.t0 = time.monotonic()
        self.mouse = (LARGURA / 2, ALTURA / 2)
        self.trilha: list[tuple[float, Path]] = []      # (inicio em s, wav)
        self.srt: list[tuple[float, float, str]] = []
        self._cena_ini = 0.0
        self._cena: Cena | None = None

    # --- tempo ---
    def agora(self) -> float:
        return time.monotonic() - self.t0

    def esperar(self, s: float) -> None:
        self.page.wait_for_timeout(int(s * 1000))

    def na_frase(self, i: int, atraso: float = 0.0) -> None:
        """Espera ate a frase i da cena atual comecar (sincroniza acao com a fala)."""
        alvo = self._cena_ini + self._cena.offsets[i] + atraso
        falta = alvo - self.agora()
        if falta > 0:
            self.esperar(falta)

    # --- navegacao e interacao visiveis ---
    def abrir(self, rota: str) -> None:
        self.page.goto(self.base + rota, wait_until="networkidle")
        self.page.evaluate("document.fonts.ready")
        self.page.mouse.move(*self.mouse)

    def rolar(self, sel: str, bloco: str = "start", margem: int = 70) -> None:
        self.page.evaluate(
            """([s, b, m]) => { const el = document.querySelector(s); if (!el) return;
                 const r = el.getBoundingClientRect();
                 const y = b === 'center' ? r.top + window.scrollY - (innerHeight - r.height) / 2 : r.top + window.scrollY - m;
                 window.scrollTo({top: Math.max(0, y), behavior: 'smooth'}); }""",
            [sel, bloco, margem],
        )
        self.esperar(0.9)

    def mover(self, sel: str, clicar: bool = False, passos: int = 28, dx: float = 0.5, dy: float = 0.5) -> None:
        loc = self.page.locator(sel).first
        loc.scroll_into_view_if_needed()
        box = loc.bounding_box()
        if not box:
            return
        x, y = box["x"] + box["width"] * dx, box["y"] + box["height"] * dy
        self.page.mouse.move(x, y, steps=passos)
        self.mouse = (x, y)
        if clicar:
            self.esperar(0.15)
            self.page.mouse.down()
            self.page.mouse.up()
            self.esperar(0.35)

    def digitar(self, sel: str, texto: str, limpar: bool = True) -> None:
        self.mover(sel, clicar=True)
        if limpar:
            self.page.locator(sel).first.fill("")
        self.page.locator(sel).first.type(texto, delay=70)

    def destacar(self, sel: str | None, pad: int = 6) -> None:
        self.page.evaluate("([s, p]) => window.__v.destacar(s, p)", [sel, pad])

    def limpar(self) -> None:
        self.page.evaluate("window.__v.limpar()")

    def tag(self, texto: str) -> None:
        self.page.evaluate("t => window.__v.tag(t)", texto)

    def cartao(self, html: str | None) -> None:
        self.page.evaluate("h => window.__v.cartao(h)", html)

    # --- cena ---
    def executar(self, c: Cena) -> None:
        if c.antes:
            c.antes(self)
        self._cena = c
        self._cena_ini = self.agora() + 0.2
        c.offsets, t = [], 0.0
        for f in c.frases:
            c.offsets.append(t)
            self.trilha.append((self._cena_ini + t, f.wav))
            self.srt.append((self._cena_ini + t, self._cena_ini + t + f.dur, f.legenda))
            t += f.dur + PAUSA_FRASE
        self.page.evaluate("l => window.__v.legendas(l)", [[f.legenda, int((0.2 + o) * 1000)] for f, o in zip(c.frases, c.offsets)])
        if c.acoes:
            c.acoes(self)
        fim = self._cena_ini + t + c.pausa_final
        if fim > self.agora():
            self.esperar(fim - self.agora())
        self.page.evaluate("window.__v.legenda('')")
        if c.depois:
            c.depois(self)


def _fmt_srt(s: float) -> str:
    ms = int(round(s * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    seg, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{seg:02d},{ms:03d}"


def gravar_video(nome: str, rota_inicial: str, cenas: list[Cena]) -> Path:
    """Grava o tutorial e devolve o caminho do MP4 final (com legenda .srt ao lado)."""
    import imageio_ffmpeg
    from playwright.sync_api import sync_playwright

    VIDEOS_DIR.mkdir(parents=True, exist_ok=True)
    tmp = VIDEOS_DIR / "_tmp"
    tmp.mkdir(exist_ok=True)
    sintetizar(cenas)
    base, parar = iniciar_servidor()
    try:
        with sync_playwright() as pw:
            nav = pw.chromium.launch(channel="msedge")
            ctx = nav.new_context(
                viewport={"width": LARGURA, "height": ALTURA}, locale="pt-BR",
                record_video_dir=str(tmp), record_video_size={"width": LARGURA, "height": ALTURA},
            )
            ctx.add_init_script(OVERLAY_JS)
            # Rede de seguranca: o tutorial nunca grava no banco (todo POST e bloqueado)
            ctx.route("**/*", lambda r: r.abort() if r.request.method == "POST" else r.continue_())
            page = ctx.new_page()
            g = Gravacao(page, base)
            g.abrir(rota_inicial)
            for c in cenas:
                g.executar(c)
            g.esperar(0.5)
            video = Path(page.video.path())
            ctx.close()
            nav.close()
    finally:
        parar()

    saida = VIDEOS_DIR / f"{nome}.mp4"
    _montar(video, g.trilha, saida, recodificar_video=True)
    _gravar_srt(saida, g.srt)
    video.unlink(missing_ok=True)
    return saida


def _montar(video: Path, trilha: list[tuple[float, Path]], saida: Path, recodificar_video: bool) -> None:
    """Mistura as frases (cada uma no seu instante) e junta com o video."""
    import imageio_ffmpeg

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    entradas = ["-i", str(video)]
    filtros, rotulos = [], []
    for k, (ini, wav) in enumerate(trilha, start=1):
        entradas += ["-i", str(wav)]
        atraso = max(0, int(ini * 1000))
        filtros.append(f"[{k}:a]aresample=48000,adelay={atraso}|{atraso}[a{k}]")
        rotulos.append(f"[a{k}]")
    ganho = "1.6" if MOTOR_TTS == "sapi" else "1.0"
    filtros.append(f"{''.join(rotulos)}amix=inputs={len(rotulos)}:normalize=0,volume={ganho}[aud]")
    video_args = (["-vf", "scale=1920:1080:flags=lanczos", "-c:v", "libx264", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-r", "30"]
                  if recodificar_video else ["-c:v", "copy"])
    subprocess.run(
        [ffmpeg, "-y", "-loglevel", "error", *entradas, "-filter_complex", ";".join(filtros),
         "-map", "0:v", "-map", "[aud]", *video_args, "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(saida)],
        check=True,
    )


def _gravar_srt(saida: Path, srt: list[tuple[float, float, str]]) -> None:
    linhas = []
    for i, (a, b, t) in enumerate(srt, start=1):
        linhas += [str(i), f"{_fmt_srt(a)} --> {_fmt_srt(b)}", t, ""]
    saida.with_suffix(".srt").write_text("\n".join(linhas), encoding="utf-8")


def _ler_srt(caminho: Path) -> list[float]:
    import re

    inicios = []
    for m in re.finditer(r"(\d+):(\d+):(\d+),(\d+) -->", caminho.read_text(encoding="utf-8")):
        h, mi, se, ms = map(int, m.groups())
        inicios.append(h * 3600 + mi * 60 + se + ms / 1000)
    return inicios


def redublar(nome: str, cenas: list[Cena]) -> Path:
    """Troca so a narracao de um video ja gravado (imagem copiada sem recodificar).

    Cada frase nova entra no mesmo instante da legenda original (.srt). Se a voz nova
    for mais longa que o intervalo ate a proxima frase, avisa a sobreposicao.
    """
    mp4 = VIDEOS_DIR / f"{nome}.mp4"
    inicios = _ler_srt(mp4.with_suffix(".srt"))
    frases = [f for c in cenas for f in c.frases]
    if len(frases) != len(inicios):
        raise ValueError(f"Roteiro tem {len(frases)} frases, mas a legenda do video tem {len(inicios)}.")
    sintetizar(cenas)
    trilha, srt = [], []
    for i, (f, ini) in enumerate(zip(frases, inicios)):
        prox = inicios[i + 1] if i + 1 < len(inicios) else None
        if prox is not None and ini + f.dur > prox:
            print(f"Aviso: frase {i + 1} ({f.dur:.1f}s) invade a seguinte em {ini + f.dur - prox:.1f}s")
        trilha.append((ini, f.wav))
        srt.append((ini, ini + f.dur, f.legenda))
    original = mp4.with_name(mp4.stem + "_video_original.mp4")
    if not original.exists():
        mp4.replace(original)
    _montar(original, trilha, mp4, recodificar_video=False)
    _gravar_srt(mp4, srt)
    return mp4


# ---------------------------------------------------------------------------
# Gravacao por cena: cada cena e um clipe em cache; corrigir uma cena regrava so ela
# ---------------------------------------------------------------------------
VERSAO_MOTOR = "2"


def _assinatura(c: Cena) -> str:
    import inspect

    partes = [VERSAO_MOTOR, MOTOR_TTS, VOZ_NEURAL, VELOCIDADE_NEURAL, VOZ, str(VELOCIDADE), c.titulo, c.rota, str(c.tag), str(c.pausa_final)]
    partes += [f.legenda + "|" + f.fala for f in c.frases]
    for fn in (c.preparar, c.antes, c.acoes, c.depois):
        try:
            partes.append(inspect.getsource(fn) if fn else "-")
        except (OSError, TypeError):
            partes.append(repr(fn))
    partes.append(OVERLAY_JS)
    return hashlib.sha1("\n".join(partes).encode("utf-8")).hexdigest()[:12]


def _duracao(ffmpeg: str, arq: Path) -> float:
    import re

    out = subprocess.run([ffmpeg, "-hide_banner", "-i", str(arq)], capture_output=True, text=True).stderr
    h, m, s_ = re.search(r"Duration: (\d+):(\d+):([\d.]+)", out).groups()
    return int(h) * 3600 + int(m) * 60 + float(s_)


def _gravar_clipe(pw, base: str, c: Cena, destino: Path, tmp: Path) -> list[tuple[float, float, str]]:
    import imageio_ffmpeg

    nav = pw.chromium.launch(channel="msedge")
    ctx = nav.new_context(viewport={"width": LARGURA, "height": ALTURA}, locale="pt-BR",
                          record_video_dir=str(tmp), record_video_size={"width": LARGURA, "height": ALTURA})
    ctx.add_init_script(OVERLAY_JS)
    ctx.route("**/*", lambda r: r.abort() if r.request.method == "POST" else r.continue_())
    page = ctx.new_page()
    g = Gravacao(page, base)
    g.abrir(c.rota)
    if c.tag:
        g.tag(c.tag)
    if c.preparar:
        c.preparar(g)
    g.esperar(0.3)
    inicio = g.agora()
    g.executar(c)
    fim = g.agora()
    webm = Path(page.video.path())
    ctx.close()
    nav.close()

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    corte = tmp / f"{destino.stem}_corte.mp4"
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-ss", f"{inicio:.3f}", "-i", str(webm), "-t", f"{fim - inicio:.3f}",
                    "-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "12", str(corte)], check=True)
    webm.unlink(missing_ok=True)
    trilha = [(ini - inicio, wav) for ini, wav in g.trilha]
    _montar(corte, trilha, destino, recodificar_video=True)
    corte.unlink(missing_ok=True)
    return [(a - inicio, b - inicio, t) for a, b, t in g.srt]


def gravar_por_cenas(nome: str, cenas: list[Cena], forcar: bool = False) -> Path:
    """Grava (ou reaproveita do cache) um clipe por cena e concatena no MP4 final com .srt."""
    import imageio_ffmpeg
    from playwright.sync_api import sync_playwright

    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    pasta = VIDEOS_DIR / "_cenas" / nome
    tmp = VIDEOS_DIR / "_tmp"
    pasta.mkdir(parents=True, exist_ok=True)
    tmp.mkdir(parents=True, exist_ok=True)
    sintetizar(cenas)
    clipes: list[tuple[Path, list]] = []
    a_gravar = []
    for i, c in enumerate(cenas, start=1):
        arq = pasta / f"{i:02d}_{_assinatura(c)}.mp4"
        meta = arq.with_suffix(".json")
        clipes.append((arq, meta))
        if forcar or not (arq.exists() and meta.exists()):
            a_gravar.append((i, c, arq, meta))
        else:
            print(f"Cena {i:02d} ({c.titulo}): reaproveitada do cache")
    if a_gravar:
        base, parar = iniciar_servidor()
        try:
            with sync_playwright() as pw:
                for i, c, arq, meta in a_gravar:
                    t = time.monotonic()
                    srt = _gravar_clipe(pw, base, c, arq, tmp)
                    meta.write_text(json.dumps(srt, ensure_ascii=False), encoding="utf-8")
                    print(f"Cena {i:02d} ({c.titulo}): gravada em {time.monotonic() - t:.0f}s")
        finally:
            parar()
    # limpa clipes antigos (assinaturas que nao existem mais)
    validos = {a.name for a, _ in clipes} | {m.name for _, m in clipes}
    for velho in pasta.glob("*"):
        if velho.name not in validos:
            velho.unlink(missing_ok=True)

    lista = tmp / f"{nome}_lista.txt"
    lista.write_text("".join(f"file '{a.as_posix()}'\n" for a, _ in clipes), encoding="utf-8")
    saida = VIDEOS_DIR / f"{nome}.mp4"
    subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy",
                    "-movflags", "+faststart", str(saida)], check=True)
    srt, deslocamento = [], 0.0
    for arq, meta in clipes:
        for a, b, t in json.loads(meta.read_text(encoding="utf-8")):
            srt.append((a + deslocamento, b + deslocamento, t))
        deslocamento += _duracao(ffmpeg, arq)
    _gravar_srt(saida, srt)
    return saida
