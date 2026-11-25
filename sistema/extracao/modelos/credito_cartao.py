"""Modelos da familia de credito, cartoes e boletos de cobranca."""

from __future__ import annotations

from sistema.extracao.modelos.base import SpecModelo

MODELOS: dict[str, SpecModelo] = {
    "CCB": SpecModelo(
        nome="CCB",
        tipo="credito_cartao",
        familia="credito_cartao",
        rotulos_numero=("CONTA DE DÉBITO DOS ENCARGOS E DAS PARCELAS",),
        rotulos_data=("DATA DE LIBERAÇÃO",),
        rotulos_valor=("VALOR LÍQUIDO LIBERADO (PRINCIPAL)", "VALOR LÍQUIDO LIBERADO"),
    ),
    "Cronograma-pagamentos": SpecModelo(
        nome="Cronograma-pagamentos",
        tipo="credito_cartao",
        familia="credito_cartao",
        rotulos_numero=("EMITENTE",),
        rotulos_data=(),
        rotulos_valor=("PRINCIPAL",),
    ),
    "Demonstrativo-encargos-PF": SpecModelo(
        nome="Demonstrativo-encargos-PF",
        tipo="credito_cartao",
        familia="credito_cartao",
        rotulos_numero=("CONTA PESSOAL DEBITADA",),
        rotulos_data=(),
        rotulos_valor=("TOTAL DE ENCARGOS DEBITADOS NA CONTA PESSOAL",),
    ),
    "Posicao-contrato-parcelas-pagas": SpecModelo(
        nome="Posicao-contrato-parcelas-pagas",
        tipo="credito_cartao",
        familia="credito_cartao",
        rotulos_numero=("PARCELAS LIQUIDADAS",),
        rotulos_data=(),
        rotulos_valor=("SALDO DEVEDOR DE PRINCIPAL",),
    ),
    "Extrato-liquidacao-cartao": SpecModelo(
        nome="Extrato-liquidacao-cartao",
        tipo="credito_cartao",
        familia="credito_cartao",
        rotulos_numero=("ESTABELECIMENTO (EC)",),
        rotulos_data=(),
        rotulos_valor=("VALOR LÍQUIDO CREDITADO",),
    ),
    "Boleto-aluguel": SpecModelo(
        nome="Boleto-aluguel",
        tipo="titulo",
        familia="credito_cartao",
        rotulos_numero=("Nº DO DOCUMENTO",),
        rotulos_data=("VENCIMENTO",),
        rotulos_valor=("VALOR DO DOCUMENTO",),
    ),
    "Boleto-condominio": SpecModelo(
        nome="Boleto-condominio",
        tipo="titulo",
        familia="credito_cartao",
        rotulos_numero=("Nº DO DOCUMENTO",),
        rotulos_data=("VENCIMENTO",),
        rotulos_valor=("VALOR DO DOCUMENTO",),
    ),
}
