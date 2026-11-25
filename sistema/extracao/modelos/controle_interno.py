"""Modelos da familia de controle interno (fechamento de caixa, memorandos, recibos e carta)."""

from __future__ import annotations

from sistema.extracao.modelos.base import SpecModelo

MODELOS: dict[str, SpecModelo] = {
    "Fechamento-caixa": SpecModelo(
        nome="Fechamento-caixa",
        tipo="controle_interno",
        familia="controle_interno",
        rotulos_numero=("DEPÓSITO VINCULADO",),
        rotulos_data=("PERÍODO DO FECHAMENTO",),
        rotulos_valor=("TOTAL EM DINHEIRO NO PERÍODO", "TOTAL DAS VENDAS EM DINHEIRO"),
    ),
    "Memorando-transferencia": SpecModelo(
        nome="Memorando-transferencia",
        tipo="controle_interno",
        familia="controle_interno",
        rotulos_numero=("Nº",),
        rotulos_data=("DATA",),
        rotulos_valor=("VALOR AUTORIZADO",),
    ),
    "Recibo-aluguel": SpecModelo(
        nome="Recibo-aluguel",
        tipo="controle_interno",
        familia="controle_interno",
        eh_prosa=True,
    ),
    "Recibo-autonomo": SpecModelo(
        nome="Recibo-autonomo",
        tipo="controle_interno",
        familia="controle_interno",
        eh_prosa=True,
    ),
    "Recibo-prolabore": SpecModelo(
        nome="Recibo-prolabore",
        tipo="controle_interno",
        familia="controle_interno",
        eh_prosa=True,
    ),
    "Recibo-retirada-socio": SpecModelo(
        nome="Recibo-retirada-socio",
        tipo="controle_interno",
        familia="controle_interno",
        eh_prosa=True,
    ),
    "Carta-socios-Goiania": SpecModelo(
        nome="Carta-socios-Goiania",
        tipo="controle_interno",
        familia="controle_interno",
        eh_prosa=True,
    ),
}
