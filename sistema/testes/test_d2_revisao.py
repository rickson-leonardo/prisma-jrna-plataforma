"""Testes puros (sem banco) das correções da revisão das fases 1–5 do D2."""
from __future__ import annotations

from pathlib import Path

from sistema.erp.motor_folha import detectar_residuos_texto_d2
from sistema.web.app import create_app

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
