"""
Technique registry.

EN: Holds the registered ``TechniqueDescriptor`` objects keyed by id. The
    introduction screen populates its dropdown from ``all_descriptors()`` and
    the step manager resolves the active technique via ``get(id)``.

ES: Contiene los ``TechniqueDescriptor`` registrados, indexados por id. La
    pantalla de introduccion arma su desplegable desde ``all_descriptors()`` y
    el administrador de pasos resuelve la tecnica activa con ``get(id)``.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques.base import (
    TechniqueDescriptor,
)

logger = logging.getLogger(__name__)

_TECHNIQUES: Dict[str, TechniqueDescriptor] = {}


def register(descriptor: TechniqueDescriptor) -> None:
    """Register (or replace) a technique descriptor by its id."""
    if descriptor.id in _TECHNIQUES:
        logger.warning("[techniques] Overriding technique '%s'", descriptor.id)
    _TECHNIQUES[descriptor.id] = descriptor


def get(technique_id: str) -> TechniqueDescriptor:
    """Return the descriptor registered under ``technique_id``."""
    return _TECHNIQUES[technique_id]


def all_descriptors() -> List[TechniqueDescriptor]:
    """Return all registered descriptors, in insertion order."""
    return list(_TECHNIQUES.values())
