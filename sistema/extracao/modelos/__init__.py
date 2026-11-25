"""Catalogo consolidado dos 51 modelos de documentos PDF do D4."""

from __future__ import annotations

from sistema.extracao.modelos.base import SpecModelo
from sistema.extracao.modelos.comprovantes import MODELOS as COMPROVANTES
from sistema.extracao.modelos.controle_interno import MODELOS as CONTROLE_INTERNO
from sistema.extracao.modelos.credito_cartao import MODELOS as CREDITO_CARTAO
from sistema.extracao.modelos.fiscal import MODELOS as FISCAL
from sistema.extracao.modelos.importacao import MODELOS as IMPORTACAO
from sistema.extracao.modelos.tributos import MODELOS as TRIBUTOS

CATALOGO_MODELOS: dict[str, SpecModelo] = {
    **FISCAL,
    **COMPROVANTES,
    **TRIBUTOS,
    **IMPORTACAO,
    **CREDITO_CARTAO,
    **CONTROLE_INTERNO,
}
