"""
Edit window for the permittivity chart (Material Characterization module).

Allows the user to customize colors and line widths for the ε' and ε'' curves.
Settings are persisted in characterization_chart_config.ini.
Labels are loaded from the module JSON resource files (EN/ES).
"""

from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTabWidget, QFrame,
)

from NanoVNA_UTN_Toolkit.utils import safe_import
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.resources_loader import load_text
from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.measurement_main_window.edit_characterization.edit_characterization_utils import (
    create_tab_real,
    create_tab_imag,
    _INI_EXE,
    _INI_DEV,
    _DL_INI_EXE,
    _DL_INI_DEV,
    _separator,
)

get_settings = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings"
)
dark_light_config = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.dark_light_mode.light_dark_mode", "dark_light_config"
)
apply_window_icon = safe_import(
    "NanoVNA_UTN_Toolkit.shared.utils.icon.app_icon", "apply_window_icon"
)

logger = logging.getLogger(__name__)


class EditCharacterization(QMainWindow):
    def __init__(self, main_window):
        super().__init__()

        apply_window_icon(self)
        dark_light_config(self)

        self._main_window = main_window

        # Load i18n texts
        texts = load_text("characterization_edit_chart.json")
        btn_texts = texts.get("buttons", {})
        tab_texts = texts.get("tabs", {})

        self.setWindowTitle(texts.get("window_title", "Edit Permittivity Chart"))
        self.setFixedSize(800, 630)

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # --- Tabs ---
        tabs = QTabWidget()

        (
            tab1, get_tc1, get_tw1,
            get_mc1_1, get_mc2_1, get_ms1_1, get_ms2_1,
            get_bg, get_txt, get_ax
        ) = create_tab_real(main_window, texts)

        (
            tab2, get_tc2, get_tw2,
            get_mc1_2, get_mc2_2, get_ms1_2, get_ms2_2
        ) = create_tab_imag(main_window, texts)

        tabs.addTab(tab1, tab_texts.get("real", "ε′  (Real Part)"))
        tabs.addTab(tab2, tab_texts.get("imag", "ε″  (Losses)"))
        layout.addWidget(tabs)

        # --- Separator above buttons (same color as tabs' internal separators) ---
        _dl_s = get_settings(_DL_INI_EXE, _DL_INI_DEV, Path(__file__).resolve())
        qfc = _dl_s.value("Dark_Light/QFrame/background-color", "white")
        layout.addWidget(_separator(qfc))

        # --- Buttons ---
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_cancel = QPushButton(btn_texts.get("cancel", "Cancel"))
        btn_apply = QPushButton(btn_texts.get("apply", "Apply"))
        btn_cancel.clicked.connect(self.close)
        btn_apply.clicked.connect(
            lambda: self._on_apply(
                get_tc1, get_tw1, get_mc1_1, get_mc2_1, get_ms1_1, get_ms2_1,
                get_bg, get_txt, get_ax,
                get_tc2, get_tw2, get_mc1_2, get_mc2_2, get_ms1_2, get_ms2_2,
            )
        )
        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_apply)
        layout.addLayout(btn_row)

        self.setCentralWidget(central)

    # ------------------------------------------------------------------ #

    def _on_apply(self, get_tc1, get_tw1, get_mc1_1, get_mc2_1, get_ms1_1, get_ms2_1,
                  get_bg, get_txt, get_ax,
                  get_tc2, get_tw2, get_mc1_2, get_mc2_2, get_ms1_2, get_ms2_2):
        try:
            settings = get_settings(_INI_EXE, _INI_DEV, Path(__file__).resolve())

            # Tab ε'
            settings.setValue("Epsilon_Real/TraceColor", get_tc1())
            settings.setValue("Epsilon_Real/TraceWidth", get_tw1())
            settings.setValue("Epsilon_Real/MarkerColor1", get_mc1_1())
            settings.setValue("Epsilon_Real/MarkerColor2", get_mc2_1())
            settings.setValue("Epsilon_Real/MarkerWidth1", get_ms1_1())
            settings.setValue("Epsilon_Real/MarkerWidth2", get_ms2_1())
            settings.setValue("Epsilon_Real/BackgroundColor", get_bg())
            settings.setValue("Epsilon_Real/TextColor", get_txt())
            settings.setValue("Epsilon_Real/AxisColor", get_ax())

            # Tab ε''
            settings.setValue("Epsilon_Imag/TraceColor", get_tc2())
            settings.setValue("Epsilon_Imag/TraceWidth", get_tw2())
            settings.setValue("Epsilon_Imag/MarkerColor1", get_mc1_2())
            settings.setValue("Epsilon_Imag/MarkerColor2", get_mc2_2())
            settings.setValue("Epsilon_Imag/MarkerWidth1", get_ms1_2())
            settings.setValue("Epsilon_Imag/MarkerWidth2", get_ms2_2())
            settings.sync()

            # Update the live chart config
            mw = self._main_window
            if hasattr(mw, "_epsilon_manager") and mw._epsilon_manager is not None:
                cfg = mw._epsilon_manager.config
                cfg.real_color = get_tc1()
                cfg.real_linewidth = float(get_tw1())
                cfg.loss_color = get_tc2()
                cfg.loss_linewidth = float(get_tw2())
                cfg.background_color = get_bg()
                cfg.text_color = get_txt()
                cfg.spine_color = get_ax()
                cfg.grid_color = get_ax()

            if hasattr(mw, "redraw_chart"):
                mw.redraw_chart()

        except Exception as exc:
            logger.error("[EditCharacterization] apply failed: %s", exc)

        self.close()
