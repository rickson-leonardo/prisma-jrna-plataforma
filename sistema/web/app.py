"""Aplicacao web Flask — Sistema Contabil Real + Sustentacao (Etapa 1 / Dossie 1)."""

from __future__ import annotations

import hmac
import io
import json
import os
import secrets
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse

import psycopg2
from flask import Flask, abort, flash, g, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash

from sistema.web import ajuda as ajuda_mod
from sistema.web import repo, repo_d2, rotulos, texto


def _fmt_num_input(centavos: int | None) -> str:
    return texto.num_br(int(centavos or 0) / 100.0)


def _fmt_pct_num_input(micro: int | None) -> str:
    return texto.num_br(int(micro or 0) / 10_000.0)


def _fmt_data_br(val: Any) -> str:
    """Formata data (date/datetime ou YYYY-MM-DD) para DD/MM/AAAA."""
    if not val:
        return "—"
    if hasattr(val, "strftime"):
        return val.strftime("%d/%m/%Y")
    s = str(val).strip()
    if len(s) >= 10 and s[4] == "-" and s[7] == "-" and s[:4].isdigit() and s[5:7].isdigit() and s[8:10].isdigit():
        return f"{s[8:10]}/{s[5:7]}/{s[:4]}"
    return s


# Campo de justificativa exigido para homologar, por tipo de formulario
_CAMPOS_JUSTIFICATIVA = ("justificativa_contadora", "justificativa_sustentacao", "revisao_humana")


def form_governanca(form: Any) -> dict[str, str]:
    """Copia o formulario aplicando a acao do botao clicado.

    - acao=homologar: exige justificativa preenchida e marca 'homologado_contadora';
    - acao=rascunho : grava sem homologar (mantem a situacao escolhida).
    Formularios sem 'acao' (clientes antigos/testes) seguem o status enviado.
    """
    dados = {k: form.get(k) for k in form.keys()}
    acao = dados.pop("acao", None)
    if acao == "homologar":
        campo = next((c for c in _CAMPOS_JUSTIFICATIVA if c in dados), None)
        if campo and not (dados.get(campo) or "").strip():
            raise ValueError("para homologar, registre a justificativa técnica da contadora (campo obrigatório).")
        dados["status_validacao"] = "homologado_contadora"
    elif acao == "rascunho" and not dados.get("status_validacao"):
        dados["status_validacao"] = "pendente_revisao"
    return dados


def _msg(base: str, dados: dict[str, str]) -> str:
    return base + (" Decisão homologada." if dados.get("status_validacao") == "homologado_contadora" else "")


def _ajuda_json() -> str:
    """Dicionario de ajuda serializado uma vez por pagina (os icones referenciam a chave)."""
    import json

    return json.dumps(ajuda_mod.AJUDA, ensure_ascii=False).replace("</", "<\\/")


def _usuarios_configurados() -> dict[str, str]:
    bruto = os.environ.get("APP_USUARIOS_JSON", "").strip()
    if bruto:
        dados = json.loads(bruto)
        return {str(k).strip().lower(): str(v) for k, v in dados.items() if str(k).strip()}
    senha = os.environ.get("APP_AUTH_SENHA", "").strip()
    if senha:
        usuario = (os.environ.get("APP_AUTH_USUARIO") or "equipe").strip().lower()
        return {usuario: senha}
    return {}


def _auth_obrigatoria() -> bool:
    return bool(os.environ.get("VERCEL") or _usuarios_configurados())


def _verificar_credenciais(usuario: str, senha: str) -> bool:
    usuarios = _usuarios_configurados()
    alvo = usuarios.get(usuario.strip().lower())
    if not alvo or not senha:
        return False
    if alvo.startswith(("pbkdf2:", "scrypt:")):
        return check_password_hash(alvo, senha)
    return hmac.compare_digest(alvo, senha)


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    modo_cloud = bool(os.environ.get("VERCEL"))
    app.secret_key = os.environ.get("FLASK_SECRET_KEY") or secrets.token_hex(32)
    app.config.update(SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_HTTPONLY=True, MAX_CONTENT_LENGTH=2 * 1024 * 1024)

    @app.before_request
    def sincronizar_contexto_dossie():
        d = (request.args.get("dossie") or "").strip().upper()
        if d in repo.DOSSIES_VALIDOS and session.get("dossie_ativo") != d:
            session["dossie_ativo"] = d

    @app.before_request
    def exigir_autenticacao():
        if request.endpoint in ("static", "login", "post_login", "logout") or not _auth_obrigatoria():
            return None
        if not _usuarios_configurados() or (modo_cloud and not os.environ.get("FLASK_SECRET_KEY")):
            abort(503, description="Autenticação ou FLASK_SECRET_KEY não configurada no servidor.")
        if not session.get("usuario"):
            prox = request.full_path.rstrip("?") if request.query_string else request.path
            return redirect(url_for("login", next=prox))
        return None

    # ------------------------------------------------------------------
    # CSRF leve: token por sessao + verificacao de origem
    # ------------------------------------------------------------------
    def csrf_token() -> str:
        if "csrf" not in session:
            session["csrf"] = secrets.token_urlsafe(32)
        return session["csrf"]

    @app.before_request
    def proteger_csrf():
        if request.method != "POST":
            return None
        origem = request.headers.get("Origin") or request.headers.get("Referer")
        if not origem:
            # Clientes nao-navegador (testes, scripts locais) nao enviam Origin/Referer.
            # Navegadores sempre enviam Origin em POST de formulario, entao a requisicao
            # forjada por outro site cai obrigatoriamente no ramo abaixo.
            return None
        if urlparse(origem).netloc != request.host:
            abort(403, description="Origem da requisicao nao confere com o sistema (CSRF).")
        enviado = request.form.get("csrf_token", "")
        if not enviado or not hmac.compare_digest(enviado, session.get("csrf", "")):
            flash("Sessão expirada ou formulário antigo: recarregue a página e repita a operação (proteção CSRF).", "erro")
            return redirect(request.referrer or url_for("painel"))
        return None

    # ------------------------------------------------------------------
    # Tratamento amigavel de erros de regra
    # ------------------------------------------------------------------
    @app.errorhandler(ValueError)
    def handle_value_error(exc: ValueError):
        flash(f"Dado inválido: {exc}", "erro")
        return redirect(request.referrer or url_for("painel"))

    @app.errorhandler(PermissionError)
    def handle_perm_error(exc: PermissionError):
        flash(f"Operação bloqueada: {exc}", "erro")
        return redirect(request.referrer or url_for("painel"))

    @app.errorhandler(psycopg2.Error)
    def handle_pg_error(exc: psycopg2.Error):
        flash(f"Regra do banco de dados violada: {exc.pgerror or exc}", "erro")
        return redirect(request.referrer or url_for("painel"))

    # ------------------------------------------------------------------
    # Filtros e globais de template
    # ------------------------------------------------------------------
    app.jinja_env.filters.update(
        brl=texto.brl,
        brl_tab=texto.brl_tab,
        reais_in=_fmt_num_input,
        pct_micro=texto.pct_micro,
        pct_in=_fmt_pct_num_input,
        rotulo=rotulos.rotulo,
        md=texto.md_html,
        md_inline=texto.md_inline,
        num_br=texto.num_br,
        tir_br=texto.tir_br,
        data_br=_fmt_data_br,
    )

    def progresso_estacoes() -> dict[str, dict[str, int]]:
        if "prog_est" not in g:
            try:
                g.prog_est = repo.progresso_por_estacao()
            except Exception:  # noqa: BLE001 — menu nao pode derrubar a pagina
                g.prog_est = {}
        return g.prog_est

    app.jinja_env.globals.update(
        ajuda=ajuda_mod.ajuda,
        estacao=lambda k: ajuda_mod.ESTACOES[k],
        opcoes=rotulos.opcoes,
        classe_status=lambda v: rotulos.CLASSE_STATUS.get(str(v), "neutro"),
        csrf_token=csrf_token,
        progresso_estacoes=progresso_estacoes,
        ajuda_json=_ajuda_json,
        modo_cloud=modo_cloud,
        dossie_ativo=repo.dossie_em_foco,
        endpoint_existe=lambda ep: ep in app.view_functions,
    )

    @app.post("/contexto/selecionar")
    def post_contexto_selecionar():
        d = (request.form.get("dossie") or "D1").strip().upper()
        if d not in repo.DOSSIES_VALIDOS:
            d = "D1"
        session["dossie_ativo"] = d
        prox = (request.form.get("next") or request.referrer or url_for("painel")).strip()
        flash(f"Contexto alterado para o Dossiê {d}.", "info")
        # Remove ?dossie= do destino: o parametro na URL tem precedencia sobre a sessao e desfaria a troca
        parsed = urlparse(prox)
        query = urlencode([(k, v) for k, v in parse_qsl(parsed.query) if k != "dossie"])
        prox = (parsed.path or "/") + (f"?{query}" if query else "")  # descarta host: so redireciona internamente
        if prox.startswith("/") and not prox.startswith("//"):
            # Se a pagina anterior e exclusiva de outro dossie, volta para o painel
            if d == "D2" and prox.startswith("/planejamento"):
                return redirect(url_for("painel"))
            if d == "D1" and prox.startswith(("/onboarding", "/dp", "/folha")):
                return redirect(url_for("painel"))
            if prox.startswith("/sustentacao"):
                return redirect(url_for("sustentacao"))
            return redirect(prox)
        return redirect(url_for("painel"))

    # -------------------------------------------------------------------------
    # AUTENTICACAO (obrigatória online / quando configurada)
    # -------------------------------------------------------------------------
    @app.get("/login")
    def login():
        if session.get("usuario") or not _auth_obrigatoria():
            return redirect(url_for("painel"))
        return render_template("login.html", next_url=request.args.get("next", ""))

    @app.post("/login")
    def post_login():
        usuario = (request.form.get("usuario") or "").strip().lower()
        senha = request.form.get("senha") or ""
        prox = (request.form.get("next") or "").strip()
        if not _verificar_credenciais(usuario, senha):
            flash("Usuário ou senha inválidos.", "erro")
            return redirect(url_for("login", next=prox) if prox else url_for("login"))
        session["usuario"] = usuario
        flash(f"Bem-vinda(o), {usuario}.", "ok")
        if prox.startswith("/") and not prox.startswith("//"):
            return redirect(prox)
        return redirect(url_for("painel"))

    @app.post("/logout")
    def logout():
        session.pop("usuario", None)
        flash("Sessão encerrada.", "info")
        return redirect(url_for("login") if _auth_obrigatoria() else url_for("painel"))

    # -------------------------------------------------------------------------
    # ESTACAO 0: PAINEL GERAL & RADAR DE COERENCIA
    # -------------------------------------------------------------------------
    @app.get("/")
    def painel():
        return render_template("painel.html", **repo.carregar_painel_geral())

    @app.post("/auditoria/revalidar")
    def post_revalidar():
        alertas = repo.revalidar_coerencia()
        flash(f"Auditoria cruzada reexecutada ({len(alertas)} apontamentos ativos).", "info")
        return redirect(url_for("painel"))

    # -------------------------------------------------------------------------
    # ESTACAO 1: CADASTRO SOCIETARIO, QSA E RESPONSABILIDADE TECNICA
    # -------------------------------------------------------------------------
    @app.get("/cadastro")
    def cadastro():
        return render_template("cadastro.html", **repo.carregar_cadastro())

    @app.post("/cadastro/empresa")
    def post_empresa():
        f = form_governanca(request.form)
        repo.salvar_empresa(f)
        flash(_msg("Dados cadastrais da sociedade gravados.", f), "ok")
        return redirect(url_for("cadastro") + "#empresa")

    @app.post("/cadastro/estabelecimento/novo")
    def post_est_novo():
        repo.criar_ou_salvar_estabelecimento(None, form_governanca(request.form))
        flash("Estabelecimento incluído.", "ok")
        return redirect(url_for("cadastro") + "#estabelecimentos")

    @app.post("/cadastro/estabelecimento/<int:est_id>/salvar")
    def post_est_salvar(est_id: int):
        f = form_governanca(request.form)
        repo.criar_ou_salvar_estabelecimento(est_id, f)
        flash(_msg("Estabelecimento atualizado.", f), "ok")
        return redirect(url_for("cadastro") + f"#estab-{est_id}")

    @app.post("/cadastro/estabelecimento/<int:est_id>/excluir")
    def post_est_excluir(est_id: int):
        repo.excluir_estabelecimento(est_id)
        flash("Estabelecimento removido.", "info")
        return redirect(url_for("cadastro"))

    @app.post("/cadastro/socio/novo")
    def post_socio_novo():
        repo.salvar_socio(None, form_governanca(request.form))
        flash("Sócia adicionada ao QSA.", "ok")
        return redirect(url_for("cadastro") + "#socios")

    @app.post("/cadastro/socio/<int:ps_id>/salvar")
    def post_socio_salvar(ps_id: int):
        f = form_governanca(request.form)
        repo.salvar_socio(ps_id, f)
        flash(_msg("Participação societária atualizada.", f), "ok")
        return redirect(url_for("cadastro") + f"#socia-{ps_id}")

    @app.post("/cadastro/socio/<int:ps_id>/excluir")
    def post_socio_excluir(ps_id: int):
        repo.excluir_socio(ps_id)
        flash("Participação societária removida.", "info")
        return redirect(url_for("cadastro") + "#socios")

    @app.post("/cadastro/identificador/novo")
    def post_ident_novo():
        repo.salvar_identificador(None, form_governanca(request.form))
        flash("Registro incluído.", "ok")
        return redirect(url_for("cadastro") + "#registros")

    @app.post("/cadastro/identificador/<int:pid_id>/salvar")
    def post_ident_salvar(pid_id: int):
        f = form_governanca(request.form)
        repo.salvar_identificador(pid_id, f)
        flash(_msg("Registro atualizado.", f), "ok")
        return redirect(url_for("cadastro") + f"#registro-{pid_id}")

    @app.post("/cadastro/identificador/<int:pid_id>/excluir")
    def post_ident_excluir(pid_id: int):
        repo.excluir_identificador(pid_id)
        flash("Registro removido.", "info")
        return redirect(url_for("cadastro") + "#registros")

    @app.post("/cadastro/enquadramento/<int:enq_id>/salvar")
    def post_enq_salvar(enq_id: int):
        f = form_governanca(request.form)
        repo.salvar_enquadramento(enq_id, f)
        flash(_msg("Enquadramento tributário e RT gravados.", f), "ok")
        return redirect(url_for("cadastro") + "#enquadramento")

    # -------------------------------------------------------------------------
    # ESTACAO 2: INSTRUMENTOS SOCIETARIOS (CONTRATO <-> MOU)
    # -------------------------------------------------------------------------
    @app.get("/instrumentos")
    def instrumentos():
        filtro = request.args.get("filtro", "todos")
        return render_template("instrumentos.html", **repo.carregar_instrumentos(filtro))

    @app.post("/instrumentos/clausula/nova")
    def post_clausula_nova():
        repo.criar_clausula(form_governanca(request.form))
        flash("Nova cláusula societária criada e validada contra conflitos.", "ok")
        return redirect(url_for("instrumentos"))

    @app.post("/instrumentos/clausula/<int:cl_id>/salvar")
    def post_clausula_salvar(cl_id: int):
        f = form_governanca(request.form)
        repo.salvar_clausula(cl_id, f)
        flash(_msg("Cláusula gravada e validada contra conflitos MoU × Contrato.", f), "ok")
        return redirect(url_for("instrumentos", filtro=f.get("filtro_atual", "todos")) + f"#clausula-{cl_id}")

    @app.post("/instrumentos/clausula/<int:cl_id>/excluir")
    def post_clausula_excluir(cl_id: int):
        repo.excluir_clausula(cl_id)
        flash("Cláusula removida.", "info")
        return redirect(url_for("instrumentos"))

    # -------------------------------------------------------------------------
    # ESTACAO 3: LEGALIZACAO DF / REDESIM / BPMN
    # -------------------------------------------------------------------------
    @app.get("/legalizacao")
    def legalizacao():
        return render_template("legalizacao.html", **repo.carregar_legalizacao())

    @app.post("/legalizacao/etapa/nova")
    def post_etapa_nova():
        repo.criar_etapa_legalizacao(form_governanca(request.form))
        flash("Etapa paralegal incluída no fluxo do DF.", "ok")
        return redirect(url_for("legalizacao"))

    @app.post("/legalizacao/etapa/<int:etapa_id>/salvar")
    def post_etapa_salvar(etapa_id: int):
        f = form_governanca(request.form)
        repo.salvar_etapa_legalizacao(etapa_id, f)
        flash(_msg("Etapa paralegal atualizada.", f), "ok")
        return redirect(url_for("legalizacao") + f"#etapa-{etapa_id}")

    @app.post("/legalizacao/etapa/<int:etapa_id>/excluir")
    def post_etapa_excluir(etapa_id: int):
        repo.excluir_etapa_legalizacao(etapa_id)
        flash("Etapa removida do fluxo.", "info")
        return redirect(url_for("legalizacao"))

    # -------------------------------------------------------------------------
    # ESTACAO 4: PLANEJAMENTO FINANCEIRO & SIMULADOR TRIBUTARIO (36 MESES)
    # -------------------------------------------------------------------------
    @app.get("/planejamento")
    def planejamento():
        cenario_id = request.args.get("cenario_id", type=int)
        ano_mensal = request.args.get("ano", default=1, type=int)
        if ano_mensal not in (1, 2, 3):
            ano_mensal = 1
        return render_template("planejamento.html", **repo.carregar_planejamento(cenario_id=cenario_id, ano_mensal=ano_mensal))

    @app.post("/planejamento/cenario/novo")
    def post_cenario_novo():
        novo_id = repo.salvar_cenario(None, form_governanca(request.form))
        flash("Novo cenário calculado e salvo (BP fechado a R$ 0,00).", "ok")
        return redirect(url_for("planejamento", cenario_id=novo_id))

    @app.post("/planejamento/cenario/<int:cen_id>/salvar")
    def post_cenario_salvar(cen_id: int):
        f = form_governanca(request.form)
        repo.salvar_cenario(cen_id, f)
        flash(_msg("Premissas recalculadas (DRE, fluxo M0–M36, BP e VPL/TIR atualizados).", f), "ok")
        return redirect(url_for("planejamento", cenario_id=cen_id))

    @app.post("/planejamento/cenario/<int:cen_id>/clonar")
    def post_cenario_clonar(cen_id: int):
        novo_id = repo.clonar_cenario(cen_id)
        flash("Cenário clonado para simulação independente.", "info")
        return redirect(url_for("planejamento", cenario_id=novo_id))

    @app.post("/planejamento/cenario/<int:cen_id>/oficial")
    def post_cenario_oficial(cen_id: int):
        repo.definir_cenario_oficial(cen_id)
        flash("Cenário promovido a oficial: passa a alimentar o Plano de Negócios e a planilha.", "ok")
        return redirect(url_for("planejamento", cenario_id=cen_id))

    @app.post("/planejamento/cenario/<int:cen_id>/excluir")
    def post_cenario_excluir(cen_id: int):
        ok = repo.excluir_cenario(cen_id)
        flash("Cenário simulado removido." if ok else "Não é possível excluir o cenário oficial ativo.", "info")
        return redirect(url_for("planejamento"))

    # -------------------------------------------------------------------------
    # ESTACAO 5: CONSULTAS NORMATIVAS, CONFORMIDADE (200), DIARIO IA
    # -------------------------------------------------------------------------
    @app.get("/sustentacao")
    def sustentacao():
        cod = repo.dossie_em_foco()
        validas = repo.MATRIZES_D2 if cod == "D2" else repo.MATRIZES_D1
        matriz = request.args.get("matriz", validas[0])
        if matriz not in validas:
            matriz = validas[0]
        pend = request.args.get("pendentes") == "1"
        return render_template("sustentacao.html", **repo.carregar_sustentacao(matriz=matriz, apenas_pendentes=pend))

    @app.post("/sustentacao/consulta/nova")
    def post_consulta_nova():
        repo.salvar_consulta(None, form_governanca(request.form))
        flash("Consulta normativa registrada.", "ok")
        return redirect(url_for("sustentacao") + "#consultas")

    @app.post("/sustentacao/consulta/<int:cons_id>/salvar")
    def post_consulta_salvar(cons_id: int):
        f = form_governanca(request.form)
        repo.salvar_consulta(cons_id, f)
        flash(_msg("Consulta normativa atualizada.", f), "ok")
        return redirect(url_for("sustentacao") + f"#consulta-{cons_id}")

    @app.post("/sustentacao/consulta/<int:cons_id>/excluir")
    def post_consulta_excluir(cons_id: int):
        repo.excluir_consulta(cons_id)
        flash("Consulta removida.", "info")
        return redirect(url_for("sustentacao") + "#consultas")

    @app.post("/sustentacao/criterio/<int:av_id>/salvar")
    def post_criterio_salvar(av_id: int):
        f = form_governanca(request.form)
        repo.salvar_avaliacao_criterio(av_id, f)
        flash(_msg("Critério avaliado e placar IABP recalculado.", f), "ok")
        return redirect(url_for("sustentacao", matriz=f.get("matriz_ativa", "plano_negocios")) + f"#criterio-{av_id}")

    @app.post("/sustentacao/ia/novo")
    def post_ia_novo():
        repo.salvar_diario_ia(None, form_governanca(request.form))
        flash("Registro adicionado ao Diário de Uso de IA.", "ok")
        return redirect(url_for("sustentacao") + "#diario-ia")

    @app.post("/sustentacao/ia/<int:ia_id>/salvar")
    def post_ia_salvar(ia_id: int):
        f = form_governanca(request.form)
        repo.salvar_diario_ia(ia_id, f)
        flash(_msg("Registro do Diário de IA atualizado.", f), "ok")
        return redirect(url_for("sustentacao") + f"#ia-{ia_id}")

    @app.post("/sustentacao/ia/<int:ia_id>/excluir")
    def post_ia_excluir(ia_id: int):
        repo.excluir_diario_ia(ia_id)
        flash("Registro de IA removido.", "info")
        return redirect(url_for("sustentacao") + "#diario-ia")

    # -------------------------------------------------------------------------
    # ESTACAO 6: EMISSAO DOS DOCUMENTOS (D1 e D2) E TEXTOS
    # -------------------------------------------------------------------------
    from sistema.web import emissor_dossie1, emissor_dossie2

    def _emissor_ativo():
        return emissor_dossie2 if repo.dossie_em_foco() == "D2" else emissor_dossie1

    @app.get("/emissao")
    def emissao():
        em = _emissor_ativo()
        dados = repo.carregar_emissao()
        dados["pacote"] = em.situacao_pacote()
        dados["documentos_pdf"] = em.DOCUMENTOS
        return render_template("emissao.html", **dados)

    @app.post("/emissao/emitir")
    def post_emitir():
        if modo_cloud:
            flash("Na versão online, use ‘Abrir / Salvar PDF’ em cada documento (Ctrl+P -> Salvar como PDF) e ‘Baixar planilha (.xlsx)’.", "info")
            return redirect(url_for("emissao") + "#pacote")
        em = _emissor_ativo()
        doc = request.form.get("doc") or None
        if doc and doc not in em.DOCUMENTOS:
            abort(404)
        res = em.emitir_pacote(somente=[doc] if doc else None)
        falhas = [v["arquivo"] for v in res["verificacoes"] if not v["ok"]]
        msg = f"{len(res['arquivos'])} arquivo(s) emitido(s) em {res['diretorio']}."
        if res["pendencias_quarentena"]:
            msg += f" Atenção: {res['pendencias_quarentena']} registros ainda em quarentena — os PDFs saem com aviso de governança."
        if falhas:
            msg += f" Verificação editorial reprovou: {', '.join(falhas)}."
        flash(msg, "erro" if falhas else "ok")
        return redirect(url_for("emissao") + "#pacote")

    @app.get("/emissao/arquivo/<path:nome>")
    def baixar_arquivo(nome: str):
        em = _emissor_ativo()
        caminho = em.caminho_arquivo(nome)
        if caminho is None:
            abort(404)
        return send_file(caminho, as_attachment=request.args.get("ver") != "1")

    @app.get("/emissao/pacote.zip")
    def baixar_zip():
        em = _emissor_ativo()
        caminho = em.compactar_pacote()
        if caminho is None:
            flash("Nenhum arquivo emitido ainda: clique em “Emitir pacote completo”.", "info")
            return redirect(url_for("emissao"))
        nome_zip = "Dossie2_Rota_Sul_G07.zip" if em is emissor_dossie2 else "Dossie1_PRISMA_JRNA.zip"
        return send_file(caminho, as_attachment=True, download_name=nome_zip)

    @app.get("/emissao/previa/<doc>")
    def previa(doc: str):
        em = _emissor_ativo()
        if doc not in em.DOCUMENTOS and doc in emissor_dossie2.DOCUMENTOS:
            em = emissor_dossie2
        elif doc not in em.DOCUMENTOS and doc in emissor_dossie1.DOCUMENTOS:
            em = emissor_dossie1
        if doc not in em.DOCUMENTOS:
            abort(404)
        return em.html_documento(doc, para_web=True)

    @app.get("/emissao/planilha.xlsx")
    def baixar_xlsx_online():
        if repo.dossie_em_foco() == "D2":
            from sistema.web.planilha_dossie2 import gravar_xlsx_bytes_d2

            raw = gravar_xlsx_bytes_d2(emissor_dossie2.carregar_dados_dossie2())
            nome = emissor_dossie2.XLSX_NOME
        else:
            from sistema.web.dados_dossie1 import carregar_dados_dossie1
            from sistema.web.planilha_dossie1 import gravar_xlsx_bytes

            raw = gravar_xlsx_bytes(carregar_dados_dossie1())
            nome = emissor_dossie1.XLSX_NOME

        return send_file(
            io.BytesIO(raw),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            as_attachment=True,
            download_name=nome,
        )

    @app.post("/emissao/secao/nova")
    def post_secao_nova():
        sid = repo.salvar_secao(None, form_governanca(request.form))
        flash("Seção de documento criada.", "ok")
        return redirect(url_for("emissao") + f"#secao-{sid}")

    @app.post("/emissao/secao/<int:sec_id>/salvar")
    def post_secao_salvar(sec_id: int):
        f = form_governanca(request.form)
        repo.salvar_secao(sec_id, f)
        flash(_msg("Texto da seção gravado.", f), "ok")
        return redirect(url_for("emissao") + f"#secao-{sec_id}")

    @app.post("/emissao/secao/<int:sec_id>/excluir")
    def post_secao_excluir(sec_id: int):
        repo.excluir_secao(sec_id)
        flash("Seção removida.", "info")
        return redirect(url_for("emissao") + "#secoes")

    # -------------------------------------------------------------------------
    # ESTACOES 7, 8 E 9: DOSSIE 2 — ROTA SUL (ONBOARDING, DP, FOLHA E AUDITORIA)
    # -------------------------------------------------------------------------
    @app.get("/onboarding")
    def onboarding():
        session["dossie_ativo"] = "D2"
        tipo = request.args.get("tipo", "todos")
        return render_template("onboarding.html", **repo_d2.carregar_onboarding(tipo_filtro=tipo))

    @app.post("/onboarding/contrato/<int:cs_id>/salvar")
    def post_onboarding_contrato(cs_id: int):
        session["dossie_ativo"] = "D2"
        f = form_governanca(request.form)
        repo_d2.salvar_contrato_servico(cs_id, f)
        flash(_msg("Instrumento contratual atualizado.", f), "ok")
        return redirect(url_for("onboarding") + f"#contrato-srv-{cs_id}")

    @app.post("/onboarding/diligencia/nova")
    def post_diligencia_nova():
        session["dossie_ativo"] = "D2"
        did = repo_d2.salvar_diligencia(None, form_governanca(request.form))
        flash("Item de diligência incluído.", "ok")
        return redirect(url_for("onboarding") + f"#diligencia-{did}")

    @app.post("/onboarding/diligencia/<int:dil_id>/salvar")
    def post_diligencia_salvar(dil_id: int):
        session["dossie_ativo"] = "D2"
        f = form_governanca(request.form)
        repo_d2.salvar_diligencia(dil_id, f)
        flash(_msg("Item de diligência atualizado.", f), "ok")
        return redirect(url_for("onboarding") + f"#diligencia-{dil_id}")

    @app.post("/onboarding/diligencia/<int:dil_id>/excluir")
    def post_diligencia_excluir(dil_id: int):
        session["dossie_ativo"] = "D2"
        repo_d2.excluir_diligencia(dil_id)
        flash("Item de diligência removido.", "info")
        return redirect(url_for("onboarding") + "#diligencia")

    @app.get("/dp")
    def dp():
        session["dossie_ativo"] = "D2"
        return render_template("dp.html", **repo_d2.carregar_dp())

    @app.post("/dp/contrato/<int:ct_id>/salvar")
    def post_dp_contrato(ct_id: int):
        session["dossie_ativo"] = "D2"
        f = form_governanca(request.form)
        repo_d2.salvar_contrato_trabalho(ct_id, f)
        flash(_msg("Contrato de trabalho atualizado.", f), "ok")
        return redirect(url_for("dp") + f"#contrato-{ct_id}")

    @app.post("/dp/parametro/<int:par_id>/salvar")
    def post_dp_parametro(par_id: int):
        session["dossie_ativo"] = "D2"
        f = form_governanca(request.form)
        repo_d2.salvar_parametro_legal(par_id, f)
        flash(_msg("Parâmetro legal atualizado e folha recalculada.", f), "ok")
        return redirect(url_for("dp") + f"#param-{par_id}")

    @app.post("/dp/esocial/<int:ev_id>/salvar")
    def post_dp_esocial(ev_id: int):
        session["dossie_ativo"] = "D2"
        f = form_governanca(request.form)
        repo_d2.salvar_esocial_evento(ev_id, f)
        flash(_msg("Evento eSocial atualizado.", f), "ok")
        return redirect(url_for("dp") + f"#esocial-{ev_id}")

    @app.get("/folha")
    def folha():
        session["dossie_ativo"] = "D2"
        return render_template("folha.html", **repo_d2.carregar_folha())

    @app.post("/folha/recalcular")
    def post_folha_recalcular():
        session["dossie_ativo"] = "D2"
        res = repo_d2.executar_recalculo_folha_d2()
        flash(
            f"Folha 09/2026 recalculada (Bruto {texto.brl(res['totais']['bruto'])} | "
            f"Líquido {texto.brl(res['totais']['liq_a' if res['cenario_negocial'] == 'A_desconta' else 'liq_b'])} | "
            f"Partidas D=C {texto.brl(res['partidas_debito_centavos'])}).",
            "ok",
        )
        return redirect(url_for("folha"))

    @app.post("/folha/competencia/<int:comp_id>/salvar")
    def post_folha_competencia(comp_id: int):
        session["dossie_ativo"] = "D2"
        f = form_governanca(request.form)
        res = repo_d2.salvar_competencia_e_recalcular(comp_id, f)
        flash(_msg(f"Competência salva e recalculada (Bruto {texto.brl(res['totais']['bruto'])}).", f), "ok")
        return redirect(url_for("folha"))

    @app.post("/folha/auditoria/<int:aud_id>/salvar")
    def post_folha_auditoria(aud_id: int):
        session["dossie_ativo"] = "D2"
        f = form_governanca(request.form)
        repo_d2.salvar_auditoria_item(aud_id, f)
        flash(_msg("Item de auditoria atualizado.", f), "ok")
        return redirect(url_for("folha") + f"#aud-{aud_id}")

    return app


if __name__ == "__main__":
    create_app().run(host="127.0.0.1", port=5000, debug=False)
