"""
Material characterization setup window for NanoVNA devices.
"""

from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import os
import sys

from pathlib import Path

logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.getLogger('matplotlib.pyplot').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QMainWindow, QVBoxLayout, QWidget, QPushButton,
    QHBoxLayout, QComboBox, QFrame, QSizePolicy, QFileDialog, QMessageBox
)
from NanoVNA_UTN_Toolkit.modules.material_characterization.calibration import kit_store
from PySide6.QtGui import QGuiApplication

try:
    from NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils import get_settings
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.shared.utils.dark_light_mode.light_dark_mode import dark_light_config
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    sys.exit(1)

apply_window_icon = safe_import("NanoVNA_UTN_Toolkit.shared.utils.icon.app_icon", "apply_window_icon")
CharacterizationResourceLoader = safe_import("NanoVNA_UTN_Toolkit.shared.resources.characterization_resource_loader", "CharacterizationResourceLoader")

# ------------------------------------------------------------------------------------------------------------------ #

_CARD = """
    QWidget#card {
        background-color: #252525;
        border: 1px solid #3d3d3d;
        border-radius: 10px;
    }
"""

_BTN_PRIMARY = """
    QPushButton {
        background-color: #1a3a5c;
        color: white;
        border: 1px solid #2d5a8e;
        border-radius: 6px;
        font-size: 13px;
        font-weight: bold;
        padding: 11px;
    }
    QPushButton:hover  { background-color: #254e7a; }
    QPushButton:pressed { background-color: #12263d; }
"""

_BTN_SECONDARY = """
    QPushButton {
        background-color: transparent;
        color: #4da6ff;
        border: 1px solid #2d5a8e;
        border-radius: 6px;
        font-size: 13px;
        font-weight: bold;
        padding: 11px;
    }
    QPushButton:hover  { background-color: #1a3a5c; color: #aacfff; border: 1px solid #4da6ff; }
    QPushButton:pressed { background-color: #12263d; }
"""

_BTN_BACK = """
    QPushButton {
        background-color: #1c2533;
        color: #7ab3f5;
        border: 1px solid #2d5a8e;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 500;
        padding: 9px 28px;
        letter-spacing: 0.3px;
    }
    QPushButton:hover {
        background-color: #1a3a5c;
        color: #aacfff;
        border: 1px solid #4da6ff;
    }
    QPushButton:pressed { background-color: #12263d; }
"""

_COMBO = """
    QComboBox {
        background-color: #333333;
        color: white;
        border: 1px solid #505050;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
        min-height: 38px;
    }
    QComboBox:hover  { border: 1px solid #4da6ff; }
    QComboBox:focus  { border: 1px solid #4da6ff; }
    QComboBox::drop-down { width: 0px; border: none; background: transparent; }
    QComboBox::down-arrow { image: none; width: 0px; height: 0px; }
    QComboBox QAbstractItemView {
        background-color: #333333;
        color: white;
        selection-background-color: #2d5a8e;
        border: 1px solid #505050;
        padding: 4px;
    }
"""

# ------------------------------------------------------------------------------------------------------------------ #

def _hsep(color="#363636"):
    """Thin horizontal separator line."""
    line = QWidget()
    line.setFixedHeight(1)
    line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    line.setStyleSheet(f"background-color: {color};")
    return line


def _bullet_row(icon, text, icon_color="#4da6ff"):
    row = QHBoxLayout()
    row.setSpacing(10)
    row.setContentsMargins(0, 0, 0, 0)

    icon_lbl = QLabel(icon)
    icon_lbl.setStyleSheet(f"color: {icon_color}; font-size: 14px; background: transparent;")
    icon_lbl.setFixedWidth(20)

    text_lbl = QLabel(text)
    text_lbl.setWordWrap(True)
    text_lbl.setStyleSheet("color: #aaaaaa; font-size: 12px; background: transparent;")

    row.addWidget(icon_lbl, alignment=Qt.AlignTop)
    row.addWidget(text_lbl, stretch=1)
    return row

# ------------------------------------------------------------------------------------------------------------------ #

class MaterialCharacterizationWelcome(QMainWindow):

    def __init__(self, s11=None, freqs=None, vna_device=None):
        super().__init__()

        self.vna = vna_device

        settings = get_settings(
            "INI/dut_measurement/preferences/preferences.ini",
            "shared/utils/preferences/preferences.ini",
            Path(__file__).resolve()
        )
        current_lang = settings.value("Preferences/language", "en")
        resourceLoader = CharacterizationResourceLoader(
            self_window=self,
            module="material_characterization",
            lang=current_lang,
            json_resource="characterization_welcome.json"
        )
        resourceLoader.load_characterization_welcome_resources()

        dark_light_config(self)

        self.vna_device = vna_device

        logging.info(
            "[material_characterization_welcome.__init__] Initializing material characterization welcome window"
        )

        apply_window_icon(self)

        self.setWindowTitle(self.charac_welcome_ui_window_title)
        self.setGeometry(100, 100, 980, 480)
        self.setFixedSize(980, 480)

        screen = QGuiApplication.primaryScreen().availableGeometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen.center())
        self.move(window_geometry.topLeft())

        central = QWidget()
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setSpacing(14)
        root.setContentsMargins(24, 18, 24, 18)

        self._build_header(root)
        root.addWidget(_hsep())
        self._build_main_cards(root)
        root.addWidget(_hsep())
        self._build_footer(root)

        self._create_menus()

# ------------------------------------------------------------------------------------------------------------------ #

    def _build_header(self, parent):
        center = QVBoxLayout()
        center.setSpacing(4)
        center.setContentsMargins(0, 0, 0, 0)

        title = QLabel(self.charac_welcome_ui_header_title)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")

        subtitle = QLabel(self.charac_welcome_ui_descriptions[0] if self.charac_welcome_ui_descriptions else "")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size: 12px; color: #666666;")

        center.addWidget(title)
        center.addWidget(subtitle)
        parent.addLayout(center)

# ------------------------------------------------------------------------------------------------------------------ #

    def _build_footer(self, parent):
        row = QHBoxLayout()
        row.setContentsMargins(0, 4, 0, 0)

        back = QPushButton(self.charac_welcome_ui_back_button)
        back.setFixedSize(200, 38)
        back.setStyleSheet(_BTN_BACK)
        back.clicked.connect(self.return_to_menu_window)

        row.addStretch(1)
        row.addWidget(back)
        row.addStretch(1)
        parent.addLayout(row)

# ------------------------------------------------------------------------------------------------------------------ #

    def _build_main_cards(self, parent):
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(self._build_left_card(), stretch=1)
        row.addWidget(self._build_right_card(), stretch=1)
        parent.addLayout(row, stretch=1)

# ------------------------------------------------------------------------------------------------------------------ #

    def _build_left_card(self):
        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet(_CARD)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(0)

        # Card title
        title_lbl = QLabel(self.charac_welcome_ui_method_selection_title)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff; background: transparent;")
        layout.addWidget(title_lbl)

        layout.addSpacing(6)
        layout.addWidget(_hsep())
        layout.addSpacing(14)

        # Subtitle
        sub = QLabel(self.charac_welcome_ui_kit_selection_subtitle)
        sub.setWordWrap(True)
        sub.setStyleSheet("font-size: 12px; color: #777777; background: transparent;")
        layout.addWidget(sub)

        layout.addSpacing(14)

        # Dropdown
        self._load_characterization_kits()
        self.kit_dropdown = QComboBox()
        self.kit_dropdown.setStyleSheet(_COMBO)
        self.kit_dropdown.addItem("None")
        self._set_current_kit_selection()
        self.kit_dropdown.currentTextChanged.connect(self._on_kit_selection_changed)
        layout.addWidget(self.kit_dropdown)

        current_text = self.kit_dropdown.currentText()
        self.selected_kit_name = None if current_text.startswith("None") else current_text

        layout.addSpacing(10)

        # Kit info label
        self.kit_info_label = QLabel(self.charac_welcome_ui_no_characterization_selected)
        self.kit_info_label.setWordWrap(True)
        self.kit_info_label.setStyleSheet(
            "font-size: 12px; color: #555555; background: transparent; font-style: italic;"
        )
        layout.addWidget(self.kit_info_label)
        self._update_kit_info_display()

        layout.addStretch(1)

        # Primary button
        self.characterization_methods_button = QPushButton(self.charac_welcome_ui_open_methods_button)
        self.characterization_methods_button.setFixedHeight(44)
        self.characterization_methods_button.setStyleSheet(_BTN_PRIMARY)
        self.characterization_methods_button.clicked.connect(self.open_characterization_methods)
        layout.addWidget(self.characterization_methods_button)

        return card

# ------------------------------------------------------------------------------------------------------------------ #

    def _build_right_card(self):
        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet(_CARD)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(0)

        # Card title
        title_lbl = QLabel(self.charac_welcome_ui_import_section_title)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff; background: transparent;")
        layout.addWidget(title_lbl)

        layout.addSpacing(6)
        layout.addWidget(_hsep())
        layout.addSpacing(14)

        # Main description
        desc = QLabel(self.charac_welcome_ui_import_description)
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; color: #999999; background: transparent;")
        layout.addWidget(desc)

        layout.addSpacing(18)

        # Feature bullets
        for text in self.charac_welcome_ui_features:
            row = _bullet_row("✓", text, "#5cb85c")
            layout.addLayout(row)
            layout.addSpacing(8)

        layout.addStretch(1)

        # Secondary button
        self.import_button = QPushButton(self.charac_welcome_ui_import_button_text)
        self.import_button.setFixedHeight(44)
        self.import_button.setStyleSheet(_BTN_PRIMARY)
        self.import_button.clicked.connect(self.import_characterization_package)
        layout.addWidget(self.import_button)

        return card

# ------------------------------------------------------------------------------------------------------------------ #

    def _create_menus(self):
        pass

# ------------------------------------------------------------------------------------------------------------------ #

    def _load_characterization_kits(self):
        """Scan the kit directory and cache all valid KitMeta objects."""
        self._kit_metas: dict = {}  # name -> KitMeta
        try:
            for meta in kit_store.list_kits():
                self._kit_metas[meta.name] = meta
        except Exception:
            logging.exception("[characterization_welcome] failed to load kits")

    def _set_current_kit_selection(self):
        """Populate the dropdown with kit items and restore last selection."""
        for meta in self._kit_metas.values():
            self.kit_dropdown.addItem(meta.display_name or meta.name)
        # No persistent last-selection for now; leave at "None"

    def _on_kit_selection_changed(self, selected_text):
        if selected_text and selected_text != "None":
            # Find by display_name
            self.selected_kit_name = next(
                (n for n, m in self._kit_metas.items()
                 if (m.display_name or m.name) == selected_text),
                None,
            )
        else:
            self.selected_kit_name = None
        self._update_kit_info_display()
        # Update the primary button label to reflect whether a kit is active
        if hasattr(self, "characterization_methods_button"):
            if self.selected_kit_name:
                self.characterization_methods_button.setText("▶  Measure unknown liquid")
            else:
                self.characterization_methods_button.setText(
                    self.charac_welcome_ui_open_methods_button
                )

    def _update_kit_info_display(self):
        if not hasattr(self, "kit_info_label"):
            return
        if self.selected_kit_name and self.selected_kit_name in self._kit_metas:
            meta = self._kit_metas[self.selected_kit_name]
            self.kit_info_label.setText("\n".join(meta.summary_lines()))
            self.kit_info_label.setStyleSheet(
                "font-size: 12px; color: #333333; background: transparent;"
            )
        else:
            self.kit_info_label.setText(self.charac_welcome_ui_no_characterization_selected)
            self.kit_info_label.setStyleSheet(
                "font-size: 12px; color: #555555; background: transparent; font-style: italic;"
            )

    def _get_current_calibration_name(self):
        settings_calibration = get_settings(
            "INI/dut_measurement/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve()
        )
        return settings_calibration.value("Calibration/Name", "No Calibration")

# ------------------------------------------------------------------------------------------------------------------ #

    def import_characterization_package(self):
        """Let the user pick a kit folder from anywhere and copy it into the kits directory."""
        src_dir = QFileDialog.getExistingDirectory(
            self, "Select kit folder", str(Path.home())
        )
        if not src_dir:
            return
        src_path = Path(src_dir)
        manifest = src_path / "manifest.json"
        if not manifest.exists():
            QMessageBox.warning(self, "Invalid kit", "The selected folder does not contain a valid kit (manifest.json not found).")
            return
        import shutil
        dest = kit_store.get_kit_dir() / src_path.name
        if dest.exists():
            QMessageBox.warning(self, "Kit already exists", f"A kit named '{src_path.name}' already exists.")
            return
        try:
            shutil.copytree(str(src_path), str(dest))
            # Reload kits and refresh dropdown
            self._load_characterization_kits()
            self.kit_dropdown.clear()
            self.kit_dropdown.addItem("None")
            self._set_current_kit_selection()
            QMessageBox.information(self, "Kit imported", f"Kit '{src_path.name}' imported successfully.")
        except Exception as exc:
            QMessageBox.critical(self, "Import failed", str(exc))

    def open_characterization_methods(self):
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.wizard_methods_window import CharacterizationWizard
        from NanoVNA_UTN_Toolkit.modules.material_characterization.ui.wizard_methods_window.steps.steps_manager import update_step_screen
        from NanoVNA_UTN_Toolkit.modules.material_characterization.techniques import get as get_technique

        logging.info("[material_characterization_welcome.open_characterization_methods] Opening characterization methods window")

        kit_name = getattr(self, "selected_kit_name", None)

        if self.vna:
            wizard = CharacterizationWizard(vna_device=self.vna)
        else:
            wizard = CharacterizationWizard()

        if kit_name and kit_name in getattr(self, "_kit_metas", {}):
            try:
                cal_data, meta = kit_store.load_kit(kit_name)
                descriptor = get_technique(meta.technique_id)

                wizard.selected_technique_id = meta.technique_id
                wizard.selected_method = descriptor.name_token
                wizard.temperature_c = meta.temperature_c
                if meta.f_start_hz is not None:
                    wizard.sweep_start_freq = meta.f_start_hz
                if meta.f_stop_hz is not None:
                    wizard.sweep_stop_freq = meta.f_stop_hz
                if meta.points is not None:
                    wizard.sweep_steps = meta.points
                wizard.perm_calibration.set_reference_liquids(meta.ref1_key, meta.ref2_key)
                wizard.perm_calibration.set_temperature(meta.temperature_c)

                for key, (freqs, s11) in cal_data.items():
                    wizard.perm_calibration.set_measurement(
                        key, freqs, s11, source=f"kit:{meta.name}"
                    )

                # Find the DUT step index (current_step = descriptor index + 1)
                dut_step = next(
                    (i + 1 for i, s in enumerate(descriptor.steps)
                     if s.standard is not None and s.standard.key == "dut"),
                    None,
                )
                if dut_step is not None:
                    wizard.current_step = dut_step
                    update_step_screen(wizard)

            except Exception as exc:
                logging.exception("[open_characterization_methods] failed to load kit '%s'", kit_name)
                QMessageBox.critical(wizard, "Kit load failed", str(exc))

        self.welcome_windows = wizard
        wizard.show()
        self.close()

    def return_to_menu_window(self):
        from NanoVNA_UTN_Toolkit.modules.menu_window import ModuleSelectionWindow

        if self.vna:
            self.menu_windows = ModuleSelectionWindow(vna_device=self.vna)
        else:
            self.menu_windows = ModuleSelectionWindow()

        self.menu_windows.show()
        self.close()

# ------------------------------------------------------------------------------------------------------------------ #

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    ventana = MaterialCharacterizationWelcome()
    ventana.show()
    sys.exit(app.exec())
