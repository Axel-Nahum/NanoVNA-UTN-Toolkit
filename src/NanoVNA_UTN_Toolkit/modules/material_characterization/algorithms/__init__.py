"""
Material characterization algorithms (pure NumPy, no Qt / no hardware).

This subpackage contains the numerical core for estimating the complex
relative permittivity (epsilon_r) of a liquid Material-Under-Test (MUT)
measured with an open-ended coaxial probe on a NanoVNA.

Subpackage layout / Estructura del subpaquete:
    reference_liquids   - Reference-liquid library + temperature-dependent
                          Debye permittivity models (Water, IPA).
    pattern_constants   - VNA + probe calibration constants (Gn, Y refs).
    permittivity_solver - 5th-order solver + cross-frequency root tracking.

Algorithm source / Fuente del algoritmo:
    "Mediciones de permitividad mediante una sonda coaxial", Medidas
    Electronicas II, UTN-FRBA, 2024 (eqs. 1-17), and the reference MATLAB
    implementation in ``medicion_fluidos/App_ME2/src/measurements``.
"""

from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.reference_liquids import (
    ReferenceLiquid,
    REFERENCE_LIQUIDS,
    get_reference_liquid,
    list_reference_liquids,
    evaluate_epsilon_r,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.pattern_constants import (
    PatternConstants,
    compute_pattern_constants,
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.algorithms.permittivity_solver import (
    EpsilonResult,
    compute_third_term,
    solve_epsilon_r,
)

__all__ = [
    "ReferenceLiquid",
    "REFERENCE_LIQUIDS",
    "get_reference_liquid",
    "list_reference_liquids",
    "evaluate_epsilon_r",
    "PatternConstants",
    "compute_pattern_constants",
    "EpsilonResult",
    "compute_third_term",
    "solve_epsilon_r",
]
