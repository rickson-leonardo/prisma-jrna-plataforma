"""UX, ajuda contextual, seguranca (CSRF), governanca de homologacao e emissao dos PDFs do Dossie 1."""

from __future__ import annotations

import re
from pathlib import Path

import openpyxl
import pytest

from sistema.pg.db import ENV_PATH, conectar_pg, obter_database_url
from sistema.web.app import create_app

ROTAS = ("/", "/cadastro", "/instrumentos", "/legalizacao", "/planejamento", "/sustentacao", "/emissao")


def _pg_disponivel() -> bool:
    try:
        obter_database_url()
        conectar_pg().close()
        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _pg_disponivel(), reason=f"PostgreSQL indisponivel ({ENV_PATH}).")


def _edge_disponivel() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            pw.chromium.launch(channel="msedge").close()
        return True
    except Exception:
        return False


@pytest.fixture(scope="module")
def client():
    from sistema.erp.importar_rascunhos_nath import importar_dossie1_quarentena
    from sistema.pg.migrar_para_pg import aplicar_migracoes_pg

    with conectar_pg() as c:
        aplicar_migracoes_pg(c)
    importar_dossie1_quarentena()
    app = create_app()
    return app.test_client()


def test_ajuda_contextual_em_100_por_cento_dos_rotulos(client) -> None:
    for rota in ROTAS:
        html = client.get(rota).data.decode("utf-8")
        assert "Como usar esta estação" in html, f"{rota} sem guia da estação"
        assert "data-help-missing" not in html, f"{rota} tem chave de ajuda inexistente"
        labels = re.findall(r"<label\b.*?</label>", html, flags=re.S)
        if rota != "/":
            assert labels, rota
        sem_tip = [lb[:120] for lb in labels if 'class="tip"' not in lb]
        assert not sem_tip, f"{rota}: rótulos sem ícone de ajuda: {sem_tip[:3]}"
        # Cabeçalhos de colunas técnicas e títulos de tabela também têm ajuda
        assert html.count('class="tip"') > 10
        # Dicionário de ajuda vai uma vez por página (ícones referenciam a chave)
        assert html.count('id="ajuda-json"') == 1


def test_rotulos_legiveis_sem_jargao_de_banco(client) -> None:
    for rota in ROTAS:
        html = client.get(rota).data.decode("utf-8")
        for cru in ("pendente_revisao", "homologado_contadora", "alerta_inconsistencia", "simples_segregado", "acervo_sigaa", "importado_rascunho_v2"):
            assert not re.search(rf">\s*{cru}\s*<", html), f"{rota} exibe código cru {cru}"
        assert "Pendente de revisão" in html or rota == "/"


def test_painel_alerta_com_atalho_para_registro(client) -> None:
    html = client.get("/").data.decode("utf-8")
    assert "Ir ao registro" in html
    assert re.search(r'href="/planejamento\?cenario_id=\d+#cenario-\d+"', html)


def test_marca_e_fontes_oficiais_servidas(client) -> None:
    html = client.get("/").data.decode("utf-8")
    assert "brand/wordmark_prisma_jrna.png" in html
    for arq in ("brand/wordmark_prisma_jrna.png", "brand/fonts/AdwaitaSans-Regular.ttf", "brand/fonts/AdwaitaMono-Regular.ttf", "app.js"):
        assert client.get(f"/static/{arq}").status_code == 200
    css = client.get("/static/style.css").data.decode("utf-8")
    assert '"Adwaita Sans"' in css and "#1F2937" in css and "#1D4ED8" in css


def test_csrf_origem_estrangeira_e_token(client) -> None:
    app = create_app()
    c = app.test_client()
    # Origem de outro site: bloqueado
    r = c.post("/auditoria/revalidar", headers={"Origin": "http://site-malicioso.example"})
    assert r.status_code == 403
    # Navegador da própria origem sem token: rejeitado com aviso
    r = c.post("/auditoria/revalidar", headers={"Origin": "http://localhost"}, follow_redirects=True)
    assert "proteção CSRF" in r.data.decode("utf-8")
    # Com token da sessão: aceito
    html = c.get("/").data.decode("utf-8")
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    r = c.post("/auditoria/revalidar", data={"csrf_token": token}, headers={"Origin": "http://localhost"}, follow_redirects=True)
    assert "Auditoria cruzada reexecutada" in r.data.decode("utf-8")


def test_homologar_exige_justificativa(client) -> None:
    base = {
        "ordem": "998", "bloco": "Z", "codigo_criterio": "Z9", "numero_clausula": "Cláusula Teste UX",
        "titulo": "Clausula UX Pytest", "aplica_contrato": "on", "metodo_haveres": "nao_aplicavel",
        "quorum_tipo": "nao_aplicavel", "regra_texto": "Texto.", "status_validacao": "pendente_revisao",
    }
    client.post("/instrumentos/clausula/nova", data=base)
    with conectar_pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM erp.instrumento_societario_clausula WHERE numero_clausula = 'Cláusula Teste UX'")
        cl_id = int(cur.fetchone()["id"])
    try:
        r = client.post(f"/instrumentos/clausula/{cl_id}/salvar", data=dict(base, acao="homologar", justificativa_contadora=""), follow_redirects=True)
        assert "justificativa técnica" in r.data.decode("utf-8")
        with conectar_pg() as conn, conn.cursor() as cur:
            cur.execute("SELECT status_validacao FROM erp.instrumento_societario_clausula WHERE id = %s", (cl_id,))
            assert cur.fetchone()["status_validacao"] == "pendente_revisao"
        client.post(f"/instrumentos/clausula/{cl_id}/salvar", data=dict(base, acao="homologar", justificativa_contadora="CC art. 1.054."))
        with conectar_pg() as conn, conn.cursor() as cur:
            cur.execute("SELECT status_validacao FROM erp.instrumento_societario_clausula WHERE id = %s", (cl_id,))
            assert cur.fetchone()["status_validacao"] == "homologado_contadora"
    finally:
        client.post(f"/instrumentos/clausula/{cl_id}/excluir")


def test_crud_secoes_documento_e_quarentena(client) -> None:
    with conectar_pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS n FROM erp.documento_secao WHERE documento = 'plano_negocios' AND origem_registro = 'importado_rascunho_v2'")
        assert int(cur.fetchone()["n"]) >= 9  # Canvas, TAM/SAM/SOM, PESTEL, Riscos... em quarentena
        cur.execute("SELECT COUNT(*) AS n FROM erp.documento_secao WHERE documento = 'plano_negocios' AND codigo_secao = 'S08'")
        assert int(cur.fetchone()["n"]) == 0  # seção financeira vem do motor, nunca de texto
        cur.execute("SELECT COUNT(*) AS n FROM auditoria.vw_pendencias_quarentena WHERE modulo = 'documentos_dossie1'")
        assert int(cur.fetchone()["n"]) >= 15
        cur.execute("SELECT COUNT(*) AS n FROM auditoria.vw_pg_fks_sem_indice")
        assert int(cur.fetchone()["n"]) == 0
    r = client.post("/emissao/secao/nova", data={"documento": "plano_negocios", "codigo_secao": "S99", "ordem": "99", "titulo": "Seção Pytest", "conteudo_md": "VPL vivo: {{VPL}}"}, follow_redirects=True)
    assert "Seção Pytest" in r.data.decode("utf-8")
    with conectar_pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT id FROM erp.documento_secao WHERE codigo_secao = 's99' AND documento = 'plano_negocios'")
        sid = int(cur.fetchone()["id"])
    try:
        from sistema.web.emissor_dossie1 import html_documento

        html = html_documento("plano_negocios")
        assert "Seção Pytest" in html and "{{VPL}}" not in html and "VPL vivo: R$" in html
        client.post(f"/emissao/secao/{sid}/salvar", data={"ordem": "99", "titulo": "Seção Pytest Editada", "conteudo_md": "x", "status_validacao": "pendente_revisao"})
        assert "Seção Pytest Editada" in client.get("/emissao").data.decode("utf-8")
    finally:
        client.post(f"/emissao/secao/{sid}/excluir")
    assert "Seção Pytest Editada" not in client.get("/emissao").data.decode("utf-8")


def test_bpmn_svg_gerado_do_banco() -> None:
    from sistema.web.bpmn import gerar_svg_bpmn

    with conectar_pg() as conn, conn.cursor() as cur:
        cur.execute("SELECT * FROM erp.processo_legalizacao_etapa ORDER BY ordem")
        etapas = cur.fetchall()
    svg = gerar_svg_bpmn(list(etapas))
    assert svg.startswith("<svg") and "http" not in svg.split(">", 1)[1].replace("http://www.w3.org/2000/svg", "")
    for e in etapas:
        assert f"{e['ordem']} · {e['codigo']}" in svg
    assert "Risco RLE?" in svg  # gateway exclusivo de risco


def test_planilha_xlsx_padrao_dma(tmp_path: Path) -> None:
    from sistema.web.dados_dossie1 import carregar_dados_dossie1
    from sistema.web.planilha_dossie1 import gravar_xlsx

    p = gravar_xlsx(carregar_dados_dossie1(), tmp_path / "plano.xlsx")
    wb = openpyxl.load_workbook(p)
    assert wb.sheetnames[0] == "Leia-me"
    for aba in ("Premissas", "Projecao_Mensal_M0_M36", "DRE_e_BP_3_Anos", "Viabilidade", "Cenarios_Sensibilidade"):
        assert aba in wb.sheetnames
    ws = wb["Premissas"]
    assert ws.freeze_panes == "A5"
    assert ws["C5"].font.color.rgb.endswith("1D4ED8")  # premissa digitada em azul
    assert ws["C6"].font.color.rgb.endswith("15803D")  # vínculo com o QSA em verde
    assert ws["C5"].font.name == "Adwaita Mono"
    textos = [c.value for row in wb["DRE_e_BP_3_Anos"].iter_rows() for c in row if isinstance(c.value, str)]
    assert any(t.startswith("Conforme 0,00") for t in textos)


def test_download_restrito_ao_pacote(client) -> None:
    assert client.get("/emissao/arquivo/..%2F..%2F.env").status_code == 404
    assert client.get("/emissao/arquivo/qualquer.pdf").status_code == 404


def test_modo_consulta_padrao_e_anti_sobreposicao(client) -> None:
    # Painel (Estacao 0) abre sem modo de edicao em massa; estacoes 1-6 abrem travadas em Modo Consulta
    assert 'data-modo="consulta"' not in client.get("/").data.decode("utf-8")
    for rota in ("/cadastro", "/instrumentos", "/legalizacao", "/planejamento", "/sustentacao", "/emissao"):
        html = client.get(rota).data.decode("utf-8")
        assert 'data-modo="consulta"' in html, f"{rota} deveria abrir em Modo Consulta"
        assert "Modo Consulta (Somente leitura)" in html, f"{rota} sem barra de modo consulta"
        assert 'fieldset class="crud-fs" disabled' in html, f"{rota} sem fieldset travado por padrao"
        assert "js-crud-editar" in html, f"{rota} sem botao explicito de habilitar edicao"
    css = client.get("/static/style.css").data.decode("utf-8")
    assert ".item .it-cod" in css
    assert "overflow-wrap: anywhere" in css and "white-space: nowrap;" not in css.split(".item .it-cod", 1)[1].split("}", 1)[0]


def test_login_fail_closed_e_emissao_online(monkeypatch) -> None:
    import io as _io
    from werkzeug.security import generate_password_hash

    # 1. Fail-closed quando VERCEL=1 sem credenciais ou secret
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    monkeypatch.delenv("APP_USUARIOS_JSON", raising=False)
    monkeypatch.delenv("APP_AUTH_SENHA", raising=False)
    c_sem = create_app().test_client()
    assert c_sem.get("/").status_code == 503

    # 2. Autenticacao com hash pbkdf2 + secret configurada
    monkeypatch.setenv("FLASK_SECRET_KEY", "segredo-teste-pytest-12345")
    monkeypatch.setenv("APP_USUARIOS_JSON", f'{{"nathalia": "{generate_password_hash("senha123")}"}}')
    c = create_app().test_client()

    # Nao autenticado redireciona para /login e /login tem ajuda 100%
    r0 = c.get("/")
    assert r0.status_code == 302 and "/login" in r0.headers["Location"]
    login_html = c.get("/login").data.decode("utf-8")
    assert "data-help-missing" not in login_html
    assert 'class="tip"' in login_html

    # Senha errada bloqueada
    r_bad = c.post("/login", data={"usuario": "nathalia", "senha": "errada"}, follow_redirects=True)
    assert "inválidos" in r_bad.data.decode("utf-8")
    assert c.get("/").status_code == 302

    # Senha valida entra e exibe modo nuvem + XLSX em memoria + previa imprimivel
    r_ok = c.post("/login", data={"usuario": "nathalia", "senha": "senha123"}, follow_redirects=True)
    assert r_ok.status_code == 200 and "Painel da Contadora" in r_ok.data.decode("utf-8")

    em_html = c.get("/emissao").data.decode("utf-8")
    assert "Abrir / Salvar PDF" in em_html and "Baixar planilha (.xlsx)" in em_html

    prev = c.get("/emissao/previa/indice")
    assert prev.status_code == 200
    prev_html = prev.data.decode("utf-8")
    assert "Imprimir / Salvar em PDF" in prev_html and "window.print()" in prev_html

    xlsx = c.get("/emissao/planilha.xlsx")
    assert xlsx.status_code == 200
    wb = openpyxl.load_workbook(_io.BytesIO(xlsx.data))
    assert "DRE_e_BP_3_Anos" in wb.sheetnames

    # Logout encerra sessao
    c.post("/logout", follow_redirects=False)
    assert c.get("/").status_code == 302


def test_atalhos_criterios_e_marcadores_vivos(client) -> None:
    sust = client.get("/sustentacao?matriz=plano_negocios").data.decode("utf-8")
    assert "Abrir Sumário Executivo (S01)" in sust
    assert "/emissao#secao-" in sust
    em = client.get("/emissao").data.decode("utf-8")
    assert "js-ins-mk" in em and "{{VPL}}" in em
    js = client.get("/static/app.js").data.decode("utf-8")
    assert "Ver formatado" in js and "Ver texto puro" in js
    css = client.get("/static/style.css").data.decode("utf-8")
    assert ".md-view" in css and ".md-bar" in css


@pytest.mark.skipif(not _edge_disponivel(), reason="Microsoft Edge/Playwright indisponível para renderizar PDFs.")
def test_emissao_pdfs_dossie1_padrao_dma(tmp_path: Path) -> None:
    import pymupdf

    from sistema.web.emissor_dossie1 import DOCUMENTOS, XLSX_NOME, emitir_pacote

    res = emitir_pacote(destino=tmp_path)
    assert (tmp_path / XLSX_NOME).exists()
    assert len(res["verificacoes"]) == 8
    for info in DOCUMENTOS.values():
        assert (tmp_path / info["arquivo"]).exists(), info["arquivo"]
    for v in res["verificacoes"]:
        assert v["so_adwaita"], f"{v['arquivo']}: fontes {v['fontes']}"
        assert not v["paginas_esparsas"], f"{v['arquivo']}: páginas esparsas {v['paginas_esparsas']}"
        assert v["primeira_sem_rodape"], v["arquivo"]
        assert v["orientacao"].startswith("R")  # página 1 sempre em retrato
    planilha = next(v for v in res["verificacoes"] if "Planilha" in v["arquivo"])
    assert "P" in planilha["orientacao"]  # tabelas financeiras em paisagem
    with pymupdf.open(tmp_path / DOCUMENTOS["fluxo_abertura"]["arquivo"]) as pdf:
        paginas_bpmn = [p.number for p in pdf if "Figura 1 — BPMN do processo de abertura" in p.get_text()]
        assert len(paginas_bpmn) == 1  # BPMN inteiro em uma única página (H7)
        assert "Página 2 de" in pdf[1].get_text()
    with pymupdf.open(tmp_path / DOCUMENTOS["plano_negocios"]["arquivo"]) as pdf:
        txt = "".join(p.get_text() for p in pdf)
        assert "8. Plano financeiro (calculado pelo motor contábil)" in txt
        assert "Matriz 5×5" in txt
        if res["pendencias_quarentena"]:
            assert "pré-visualização com itens não homologados" in txt
