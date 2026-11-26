"""Testes puros (sem banco) das correções da revisão das fases 1–5 do D2."""
from __future__ import annotations

from pathlib import Path

from sistema.erp.motor_folha import detectar_residuos_texto_d2
from sistema.testes.test_web_dossie2 import _fixture_dados_d2
from sistema.web.app import create_app
from sistema.web.emissor_dossie2 import _capital_doc01, _normalizar_docs_admissao, html_documento

TEMPLATES = Path(__file__).resolve().parents[1] / "web" / "templates"


def _secao(texto: str) -> dict[str, str]:
    return {"documento": "d2_teste", "codigo_secao": "s", "conteudo_md": texto}


def test_residuo_1555_aceita_qualquer_forma_de_revogacao() -> None:
    # Frases reais de produção (26/11/2026) que geravam alerta crítico falso
    termo_rt = ("*(Contrato de prestação de serviços contábeis, a transferência de responsabilidade técnica "
                "e o distrato, revogando a Resolução CFC nº 1.555/2018)*")
    diario_ia = ("| **Responsabilidade Técnica Contábil e Ética** | Revogação da Resolução CFC nº 1.555/2018 e "
                 "exigências vigentes de contrato escrito, distrato, Carta de Responsabilidade e sigilo profissional. |")
    assert detectar_residuos_texto_d2([_secao(termo_rt), _secao(diario_ia)], []) == []
    # A norma revogada citada como vigente continua gerando alerta
    achados = detectar_residuos_texto_d2([_secao("Emitido nos termos da Resolução CFC nº 1.555/2018.")], [])
    assert [a["padrao"] for a in achados] == ["1.555/2018"]


def _macros():
    app = create_app()
    with app.test_request_context():
        return app.jinja_env.get_template("_macros.html").make_module({})


def test_select_rotulos_com_opcao_vazia_nao_inventa_classificacao() -> None:
    m = _macros()
    sem_valor = str(m.select_rotulos("risco_tipo", "risco_tipo", None, "— não classificado —"))
    assert '<option value="" selected' in sem_valor
    assert 'value="formal" selected' not in sem_valor
    com_valor = str(m.select_rotulos("risco_tipo", "risco_tipo", "material", "— não classificado —"))
    assert 'value="material" selected' in com_valor
    assert '<option value="" selected' not in com_valor
    # Sem o parâmetro `vazio` o select fica como antes (D1 inalterado)
    assert 'value=""' not in str(m.select_rotulos("risco_tipo", "risco_tipo", "formal"))


def test_instrumentos_d2_sem_risco_pre_selecionado() -> None:
    html = (TEMPLATES / "instrumentos.html").read_text(encoding="utf-8")
    assert "or 'formal'" not in html and "or 'medio'" not in html
    assert "'risco_tipo', 'formal')" not in html and "'risco_nivel', 'medio')" not in html
    assert html.count("'— não classificado —'") == 4


def test_pdf_sem_fallback_providencia_e_impacto() -> None:
    dados = _fixture_dados_d2()
    dados["clausulas_d2"][0]["providencia"] = None
    dados["clausulas_d2"][0]["apontamento_auditoria"] = "NOTA-X"
    html_doc01 = html_documento("d2_01_diagnostico", para_web=True, dados=dados)
    assert "NOTA-X" not in html_doc01

    dados["consultas"][0]["impacto_se_alterada"] = None
    dados["consultas"][0]["decisao_impactada"] = "DEC-Y"
    html_doc14 = html_documento("d2_14_premissas", para_web=True, dados=dados)
    ini_t2 = html_doc14.index("Tabela 2 — Quadro de decisões")
    fim_t2 = html_doc14.index("Tabela 3 — Tabelas oficiais")
    tabela2 = html_doc14[ini_t2:fim_t2]
    assert "DEC-Y" in html_doc14[:ini_t2]
    assert "DEC-Y" not in tabela2


def test_prontuario_nao_afirma_entrega_sem_status() -> None:
    pecas_str = _normalizar_docs_admissao({"docs_admissionais_json": ["RG/CPF"], "aso_status": "pendente_critico"})
    assert pecas_str[0] == {"peca": "RG/CPF", "status": "Não informado", "observacao": "Status não registrado no banco"}
    assert "ASO Admissional" in pecas_str[-1]["peca"]

    pecas_sem_st = _normalizar_docs_admissao({"docs_admissionais_json": [{"documento": "CTPS"}], "aso_status": "apto"})
    assert pecas_sem_st[0] == {"peca": "CTPS", "status": "Não informado", "observacao": "Status não registrado no banco"}

    pecas_com_st = _normalizar_docs_admissao({"docs_admissionais_json": [{"documento": "CTPS", "status": "entregue"}]})
    assert pecas_com_st[0]["status"] == "entregue"
    assert "ASO Admissional" in pecas_com_st[-1]["peca"]


def test_capital_integralizado_exige_fato_explicito() -> None:
    dados = _fixture_dados_d2()
    cap_com = _capital_doc01(dados)
    assert cap_com == {"subscrito": 150_000_000, "integralizado": 100_000_000, "a_integralizar": 50_000_000}

    dados["fatos_capital"] = [
        {"atributo": "capital_social", "valor_centavos": 100_000_000, "vigente_ate": "2026-09-13"},
        {"atributo": "capital_social", "valor_centavos": 150_000_000, "vigente_ate": None},
    ]
    cap_sem = _capital_doc01(dados)
    assert cap_sem == {"subscrito": 150_000_000, "integralizado": None, "a_integralizar": None}

    html = html_documento("d2_01_diagnostico", para_web=True, dados=dados)
    assert "Integralizado: <span class=\"mono\">— (não registrado)</span>" in html
    assert "A integralizar: <span class=\"mono\">— (não registrado)</span>" in html
    assert "R$\xa0500.000,00" not in html



