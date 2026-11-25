"""Roteiro do video tutorial da Estacao 1 — Cadastro societario, sede, QSA e responsavel tecnica.

Executar:  python -m sistema.video.roteiro_estacao1 [--teste] [--forcar]
           (grava uma cena por clipe; cenas inalteradas sao reaproveitadas do cache)
Saida:     plataforma/exportacoes/videos/Tutorial_Estacao1_Cadastro_QSA_RT.mp4 (+ .srt)

Nada e gravado no banco: o roteiro so abre, preenche para demonstrar e cancela;
alem disso o motor bloqueia qualquer POST durante a gravacao.
"""

from __future__ import annotations

from sistema.video.motor_video import Cena, F, Gravacao, gravar_por_cenas

LOGO = '<img src="/static/brand/logo_prisma_jrna_hd.png" alt="PRISMA JRNA">'
SOCIA = "#socios details[data-item]"
REG = "#lista-registros details[data-item]:not([hidden])"
TAG = "Estação 1 · Cadastro, QSA e RT"


def saltar(g: Gravacao, sel: str, margem: int = 70) -> None:
    """Posiciona a pagina instantaneamente (estado inicial da cena, fora do video)."""
    g.page.evaluate(
        "([s, m]) => { const el = document.querySelector(s); if (el) window.scrollTo(0, el.getBoundingClientRect().top + scrollY - m); }",
        [sel, margem],
    )


def em_empresa(g: Gravacao) -> None:
    saltar(g, "#empresa")


def em_estabelecimentos(g: Gravacao) -> None:
    saltar(g, "#estabelecimentos")


def em_registros(g: Gravacao) -> None:
    saltar(g, "#registros")


def registro_crc_aberto(g: Gravacao) -> None:
    g.page.fill("#registros [data-busca]", "CRC")
    g.page.locator(f"{REG} > summary").first.click()
    saltar(g, "#registros")


def abertura_antes(g: Gravacao) -> None:
    g.cartao(LOGO + "<h1>Estação 1 — Cadastro societário, sede, QSA e RT</h1><div class='rule'></div>"
             "<p>Tutorial da plataforma contábil · Dossiê 1</p><p>Cadastro da sociedade, quadro de sócias, registros e enquadramento tributário</p>")



def ir_estacao(g: Gravacao) -> None:
    g.esperar(0.4)
    g.mover('nav.nav-links a[href="/cadastro"]')
    g.destacar('nav.nav-links a[href="/cadastro"]', 3)
    g.esperar(0.6)
    g.limpar()
    with g.page.expect_navigation(wait_until="networkidle"):
        g.mover('nav.nav-links a[href="/cadastro"]', clicar=True)
    g.page.evaluate("document.fonts.ready")
    g.page.mouse.move(*g.mouse)
    g.tag("Estação 1 · Cadastro, QSA e RT")


def menu(g: Gravacao) -> None:
    g.destacar('nav.nav-links a[href="/cadastro"]', 3)
    g.na_frase(1)
    g.destacar('nav.nav-links a[href="/cadastro"] .pg', 4)
    g.mover('nav.nav-links a[href="/cadastro"] .pg')


def cabecalho(g: Gravacao) -> None:
    g.destacar(".topbar .kpi")
    g.mover(".topbar .kpi .val")
    g.na_frase(1)
    g.destacar("#modo-bar", 4)
    g.mover("#modo-badge")


def guia_e_ajuda(g: Gravacao) -> None:
    g.limpar()
    g.mover("details.guia > summary", clicar=True)
    g.destacar("details.guia")
    g.na_frase(1)
    g.limpar()
    g.mover("details.guia > summary", clicar=True)
    g.mover(".topbar .kpi .tip")
    g.esperar(0.6)
    g.mover(".topbar .kpi .tip", clicar=True)
    g.na_frase(1, 4.0)
    g.page.keyboard.press("Escape")


def identificacao(g: Gravacao) -> None:
    g.rolar("#empresa")
    g.destacar("#empresa > p .badge", 4)
    g.mover("#empresa > p .badge")
    g.na_frase(1)
    g.destacar("#empresa .compare")
    g.mover("#empresa .compare .ref-at")


def editar_homologar(g: Gravacao) -> None:
    g.limpar()
    g.mover("#empresa .js-crud-editar", clicar=True)
    g.destacar("#empresa .crud-ctrl", 4)
    g.na_frase(1)
    g.limpar()
    g.digitar("#empresa input[name=justificativa_contadora]", "")
    g.mover('#empresa button[value="homologar"]', clicar=True)
    g.destacar("#empresa label:has(input[name=justificativa_contadora])")
    g.na_frase(2)
    g.digitar("#empresa input[name=justificativa_contadora]", "Denominação conferida: CC art. 1.158 e viabilidade de nome na JUCIS-DF.")
    g.limpar()
    g.mover('#empresa button[value="homologar"]')
    g.destacar('#empresa .barra-acoes', 4)
    g.na_frase(3)
    g.limpar()
    g.mover("#empresa .js-crud-bloquear", clicar=True)



def estabelecimento(g: Gravacao) -> None:
    g.rolar("#estabelecimentos")
    g.mover("#estabelecimentos details[data-item] > summary", clicar=True)
    g.destacar("#estabelecimentos details[data-item] > summary")
    g.na_frase(1)
    g.destacar("#estabelecimentos details[data-item] label:has(input[name=municipio])")
    g.mover("#estabelecimentos details[data-item] input[name=municipio]")
    g.na_frase(2)
    g.destacar("#estabelecimentos details[data-item] label:has(input[name=cnpj])")
    g.mover("#estabelecimentos details[data-item] input[name=cnpj]")


def socias(g: Gravacao) -> None:
    g.limpar()
    g.rolar("#socios")
    g.mover(f"{SOCIA} > summary", clicar=True)
    g.destacar(f"{SOCIA} > summary")
    g.na_frase(1)
    g.limpar()
    g.mover(f"{SOCIA} .js-crud-editar", clicar=True)
    g.digitar(f"{SOCIA} input[name=valor_reais]", "20000")
    g.page.evaluate("document.activeElement.blur()")  # Tab levaria o foco ao icone de ajuda seguinte
    g.destacar(f"{SOCIA} label:has(input[name=valor_reais])")
    g.na_frase(2)
    g.digitar(f"{SOCIA} input[name=percentual]", "cinquenta")
    g.destacar(f"{SOCIA} label:has(input[name=percentual])")
    g.na_frase(3)
    g.limpar()
    g.rolar("body", margem=0)
    g.destacar(".topbar .kpi")
    g.mover(".topbar .kpi .val")


def registros(g: Gravacao) -> None:
    g.limpar()
    g.rolar("#registros")
    g.destacar("#registros .filtros", 4)
    g.na_frase(1)
    g.mover('#registros .chip[data-st="pendente_revisao"]', clicar=True)
    g.esperar(1.0)
    g.mover('#registros .chip[data-st=""]', clicar=True)
    g.digitar("#registros [data-busca]", "CRC")
    g.na_frase(2)
    g.limpar()
    g.mover(f"{REG} > summary", clicar=True)
    g.destacar(f"{REG} label.check")
    g.mover(f"{REG} label.check")


def excluir_seguro(g: Gravacao) -> None:
    g.limpar()
    g.mover(f"{REG} .js-crud-editar", clicar=True)
    g.mover(f"{REG} form.js-confirm button", clicar=True)
    g.page.wait_for_selector("dialog.confirma[open]")
    g.na_frase(1)
    g.mover("dialog.confirma button[value=nao]")
    g.esperar(0.8)
    g.mover("dialog.confirma button[value=nao]", clicar=True)


def enquadramento(g: Gravacao) -> None:
    g.limpar()
    g.rolar("#enquadramento")
    g.destacar("#enquadramento")
    g.na_frase(1)
    g.destacar("#enquadramento label:has(input[name=cnaes_secundarios])")
    g.mover("#enquadramento input[name=cnaes_secundarios]")
    g.na_frase(2)
    g.destacar("#enquadramento label:has(select[name=responsavel_tecnico_pessoa_id])")
    g.mover("#enquadramento select[name=responsavel_tecnico_pessoa_id]")


def fechamento_antes(g: Gravacao) -> None:
    g.limpar()
    g.tag("")
    g.cartao(LOGO + "<h1>Resumo da Estação 1</h1><div class='rule'></div>"
             "<p>1. Revise cada registro e compare com a v1 e com o apontamento da auditoria</p>"
             "<p>2. Registre a justificativa técnica</p><p>3. Clique em Homologar decisão</p>"
             "<p style='margin-top:18px'>Próximo vídeo: Estação 2 — Contrato Social e MoU</p>")


CENAS = [
    Cena("Abertura", [
        F("Neste vídeo você vai aprender a usar a Estação 1 da plataforma contábil da PRISMA JRNA.",
          "Neste vídeo você vai aprender a usar a Estação 1 da plataforma contábil da Prisma J R N A."),
        F("Aqui você cadastra a sociedade, a sede, as sócias, os registros e o enquadramento tributário."),
    ], preparar=abertura_antes, pausa_final=1.0),
    Cena("Menu", [
        F("Pelo menu lateral, abra a Estação 1: Cadastro, QSA e RT.", "Pelo menu lateral, abra a Estação 1: Cadastro, quê ésse á, e érre tê."),
        F("O número ao lado mostra quantos registros já foram homologados."),
    ], acoes=menu, antes=ir_estacao, rota="/"),
    Cena("Cabeçalho", [
        F("No topo, este quadro confirma que as sócias somam 100% do capital: 40 mil reais.",
          "No topo, este quadro confirma que as sócias somam cem por cento do capital: quarenta mil reais."),
        F("A tela sempre abre em Modo Consulta: os campos ficam travados para evitar alterações por engano."),
    ], acoes=cabecalho, rota="/cadastro", tag=TAG),
    Cena("Ajuda", [
        F("Clique em “Como usar esta estação” para ver o que fazer, o que conferir e como isso alimenta o Dossiê 1.",
          "Clique em: Como usar esta estação, para ver o que fazer, o que conferir, e como isso alimenta o Dossiê 1."),
        F("Em qualquer ícone de informação aparece a explicação do campo, com a base legal. Esc fecha a explicação."),
    ], acoes=guia_e_ajuda, rota="/cadastro", tag=TAG),
    Cena("1.1 Identificação", [
        F("O bloco 1.1 traz a identificação da sociedade. A etiqueta amarela indica que o dado está pendente de revisão.",
          "O bloco um ponto um traz a identificação da sociedade. A etiqueta amarela indica que o dado está pendente de revisão."),
        F("Logo abaixo, compare como o dado estava na primeira entrega com o apontamento da auditoria."),
    ], acoes=identificacao, rota="/cadastro", tag=TAG),
    Cena("Editar e homologar", [
        F("Para alterar, clique em “Habilitar edição”. Só este bloco é destravado.", "Para alterar, clique em: Habilitar edição. Só este bloco é destravado."),
        F("Para homologar, a justificativa técnica é obrigatória. Sem ela, o sistema bloqueia e marca o campo em vermelho."),
        F("Escreva a fundamentação, por exemplo o artigo do Código Civil que embasa o nome da sociedade."),
        F("Depois clique em “Homologar decisão”. Neste vídeo não vamos gravar: clique em Concluir para travar o bloco de novo.",
          "Depois clique em: Homologar decisão. Neste vídeo não vamos gravar nada. Clique em Concluir para travar o bloco de novo."),
    ], acoes=editar_homologar, rota="/cadastro", tag=TAG, preparar=em_empresa),
    Cena("1.2 Sede", [
        F("No bloco 1.2 fica a sede. Clique na linha para abrir o registro.", "No bloco um ponto dois fica a sede. Clique na linha para abrir o registro."),
        F("No Distrito Federal não há município: informe a Região Administrativa, que emite a viabilidade de localização."),
        F("O CNPJ é um dado didático fictício, e por isso continua em quarentena até a sua revisão.",
          "O Cê Ene Pê Jota é um dado didático fictício, e por isso continua em quarentena até a sua revisão."),
    ], acoes=estabelecimento, rota="/cadastro", tag=TAG, preparar=em_empresa),
    Cena("1.3 Quadro de Sócias", [
        F("No Quadro de Sócias, cada sócia mostra participação, capital e número de quotas."),
        F("Os valores seguem o padrão brasileiro: se você digitar 20000 sem pontuação, o sistema formata sozinho.",
          "Os valores seguem o padrão brasileiro: se você digitar vinte mil sem pontuação, o sistema formata sozinho."),
        F("Se o formato estiver errado, o campo fica vermelho e explica como corrigir."),
        F("Lembre: as quotas precisam fechar 100% e o capital precisa ser igual ao do Plano Financeiro.",
          "Lembre: as quotas precisam fechar cem por cento, e o capital precisa ser igual ao do Plano Financeiro."),
    ], acoes=socias, rota="/cadastro", tag=TAG, preparar=em_estabelecimentos),
    Cena("1.4 Registros", [
        F("O bloco 1.4 reúne CPF, CNPJ e CRC das sócias e da sociedade.", "O bloco um ponto quatro reúne os registros de CPF, Cê Ene Pê Jota e C R C, das sócias e da sociedade."),
        F("Use os filtros rápidos para ver só os pendentes, ou a busca para achar um registro, como o CRC.",
          "Use os filtros rápidos para ver só os pendentes, ou a busca para achar um registro, como o C R C."),
        F("Em cada registro, marque se é um dado didático fictício. O PDF informa isso e nunca o apresenta como real."),
    ], acoes=registros, rota="/cadastro", tag=TAG),
    Cena("Excluir com segurança", [
        F("Para excluir, habilite a edição e clique em Excluir."),
        F("O sistema sempre pede confirmação antes de apagar. Aqui vamos clicar em Cancelar."),
    ], acoes=excluir_seguro, rota="/cadastro", tag=TAG, preparar=registro_crc_aberto),
    Cena("1.5 Enquadramento", [
        F("Por fim, o bloco 1.5: porte, regime tributário, CNAEs e a responsável técnica.",
          "Por fim, o bloco um ponto cinco: porte, regime tributário, os códigos C N A E, e a responsável técnica."),
        F("Se o contrato prevê auditoria, o CNAE 6920-6/02 precisa constar aqui; senão, o Painel mostra um alerta.",
          "Se o contrato prevê auditoria, o código seis nove dois zero, barra zero dois, precisa constar aqui. Senão, o Painel mostra um alerta."),
        F("A responsável técnica precisa ter um registro CRC ativo cadastrado no bloco 1.4.",
          "A responsável técnica precisa ter um registro C R C ativo, cadastrado no bloco um ponto quatro."),
    ], acoes=enquadramento, rota="/cadastro", tag=TAG, preparar=em_registros),
    Cena("Encerramento", [
        F("Resumindo: revise cada registro, registre a justificativa técnica e homologue."),
        F("Esses dados alimentam o Contrato Social, o Memorando e o Plano de Negócios. No próximo vídeo: a Estação 2.",
          "Esses dados alimentam o Contrato Social, o Memorando e o Plano de Negócios. No próximo vídeo: a Estação 2."),
    ], preparar=fechamento_antes, pausa_final=1.5),
]


def _teste(g: Gravacao) -> None:
    g.destacar(".topbar .kpi")
    g.mover(".topbar .kpi .val")


# Clipe de ~10 s para validar enquadramento, cursor, destaque, legenda, navegacao e audio
CENAS_TESTE = [
    Cena("Teste", [F("Teste de gravação: quadro de quotas da Estação 1.")], acoes=_teste, antes=ir_estacao, pausa_final=1.0),
]


def main() -> None:
    import sys

    forcar = "--forcar" in sys.argv
    if "--teste" in sys.argv:
        print(gravar_por_cenas("Teste_10s_Estacao1", CENAS_TESTE, forcar))
    else:
        print(gravar_por_cenas("Tutorial_Estacao1_Cadastro_QSA_RT", CENAS, forcar))


if __name__ == "__main__":
    main()
