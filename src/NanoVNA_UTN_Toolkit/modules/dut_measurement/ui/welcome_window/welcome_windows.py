"""
Welcome setup window for NanoVNA devices.
"""

from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import os
import sys

from datetime import datetime

from pathlib import Path

logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.getLogger('matplotlib.pyplot').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel, QMainWindow, QSizePolicy, QVBoxLayout, QWidget, QPushButton,
    QHBoxLayout, QGroupBox, QComboBox, QFrame
)
from PySide6.QtGui import QColor

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_window import NanoVNAGraphics
except ImportError as e:
    logging.error("Failed to import NanoVNAGraphics: %s", e)
    NanoVNAGraphics = None

CalibrationWizard = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.wizard_cal_windows.wizard_windows", "CalibrationWizard")

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.calibration.calibration_manager import OSMCalibrationManager, THRUCalibrationManager
except ImportError as e:
    logging.error("Failed to import OSMCalibrationManager: %s", e)
    logging.error("Failed to import THRUCalibrationManager: %s", e)
    OSMCalibrationManager = None
    THRUCalibrationManager = None

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")
dark_light_config = safe_import("NanoVNA_UTN_Toolkit.shared.utils.dark_light_mode.light_dark_mode", "dark_light_config")
apply_window_icon = safe_import("NanoVNA_UTN_Toolkit.shared.utils.icon.app_icon", "apply_window_icon")
DutResourceLoader = safe_import("NanoVNA_UTN_Toolkit.shared.resources.dut_resource_loader", "DutResourceLoader")
stop_realtime = safe_import("NanoVNA_UTN_Toolkit.shared.utils.real_time.real_time", "stop_realtime")

# ------------------------------------------------------------------------------------------------------------------ #

_CARD_DARK = """
    QWidget#card {
        background-color: #252538;
        border: 1px solid #383850;
        border-radius: 10px;
    }
"""

_CARD_LIGHT = """
    QWidget#card {
        background-color: #e8e8f4;
        border: 1px solid #c4c4d8;
        border-radius: 10px;
    }
"""

_BTN_PRIMARY_DARK = """
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

_BTN_PRIMARY_LIGHT = """
    QPushButton {
        background-color: #2d5a8e;
        color: white;
        border: 1px solid #a0bcd8;
        border-radius: 6px;
        font-size: 13px;
        font-weight: bold;
        padding: 11px;
    }
    QPushButton:hover  { background-color: #3a6fa8; }
    QPushButton:pressed { background-color: #1a4a7a; }
"""

_BTN_SECONDARY_DARK = """
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

_BTN_SECONDARY_LIGHT = """
    QPushButton {
        background-color: transparent;
        color: #2d5a8e;
        border: 1px solid #a0bcd8;
        border-radius: 6px;
        font-size: 13px;
        font-weight: bold;
        padding: 11px;
    }
    QPushButton:hover  { background-color: #dce8f8; color: #1a3a5c; border: 1px solid #5a8fc0; }
    QPushButton:pressed { background-color: #c8d8f0; }
"""

_BTN_BACK_DARK = """
    QPushButton {
        background-color: #1c2533;
        color: #7ab3f5;
        border: 1px solid #2d5a8e;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 500;
        padding: 9px 28px;
    }
    QPushButton:hover  { background-color: #1a3a5c; color: #aacfff; border: 1px solid #4da6ff; }
    QPushButton:pressed { background-color: #12263d; }
"""

_BTN_BACK_LIGHT = """
    QPushButton {
        background-color: #e0e0f0;
        color: #1e1e2e;
        border: 1px solid #c4c4d8;
        border-radius: 6px;
        font-size: 13px;
        font-weight: 500;
        padding: 9px 28px;
    }
    QPushButton:hover  { background-color: #d0d0e8; }
    QPushButton:pressed { background-color: #c0c0d8; }
"""

_COMBO_DARK = """
    QComboBox {
        background-color: #2a2a3e;
        color: white;
        border: 1px solid #383850;
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
        background-color: #2a2a3e;
        color: white;
        selection-background-color: #2d5a8e;
        border: 1px solid #383850;
        padding: 4px;
    }
"""

_COMBO_LIGHT = """
    QComboBox {
        background-color: #ebebf5;
        color: #1e1e2e;
        border: 1px solid #c4c4d8;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
        min-height: 38px;
    }
    QComboBox:hover  { border: 1px solid #4d90fe; }
    QComboBox:focus  { border: 1px solid #4d90fe; }
    QComboBox::drop-down { width: 0px; border: none; background: transparent; }
    QComboBox::down-arrow { image: none; width: 0px; height: 0px; }
    QComboBox QAbstractItemView {
        background-color: #f8f8ff;
        color: #1e1e2e;
        selection-background-color: #dcdcf0;
        border: 1px solid #c4c4d8;
        padding: 4px;
    }
"""

# ------------------------------------------------------------------------------------------------------------------ #

def _hsep(color="#383850"):
    line = QWidget()
    line.setFixedHeight(1)
    line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    line.setStyleSheet(f"background-color: {color};")
    return line


def _bullet_row(icon, text, icon_color="#5cb85c", text_color="#aaaaaa"):
    row = QHBoxLayout()
    row.setSpacing(10)
    row.setContentsMargins(0, 0, 0, 0)
    icon_lbl = QLabel(icon)
    icon_lbl.setStyleSheet(f"color: {icon_color}; font-size: 13px; background: transparent;")
    icon_lbl.setFixedWidth(18)
    text_lbl = QLabel(text)
    text_lbl.setWordWrap(True)
    text_lbl.setStyleSheet(f"color: {text_color}; font-size: 12px; background: transparent;")
    row.addWidget(icon_lbl, alignment=Qt.AlignTop)
    row.addWidget(text_lbl, stretch=1)
    return row

# ------------------------------------------------------------------------------------------------------------------ #

class NanoVNAWelcome(QMainWindow):

    def __init__(self, s11=None, freqs=None, vna_device=None):
        super().__init__()

        settings = get_settings(
            "INI/dut_measurement/preferences/preferences.ini",
            "shared/utils/preferences/preferences.ini",
            Path(__file__).resolve()
        )
        current_lang = settings.value("Preferences/language", "en")
        resourceLoader = DutResourceLoader(
            self_window=self,
            module="dut_measurement",
            lang=current_lang,
            json_resource="dut_measurement_welcome.json"
        )
        resourceLoader.load_dut_measurement_welcome_resources()

        dark_light_config(self)

        _theme = get_settings(
            "INI/dut_measurement/dark_light_config/dark_light_config.ini",
            "shared/utils/dark_light_mode/dark_light_config.ini",
            Path(__file__).resolve()
        )
        self.is_dark_mode = _theme.value("Dark_Light/is_dark_mode", False, type=bool)
        _is_dark = not self.is_dark_mode
        if _is_dark:
            self._card_style    = _CARD_DARK
            self._combo_style   = _COMBO_DARK
            self._btn_primary   = _BTN_PRIMARY_DARK
            self._btn_secondary = _BTN_SECONDARY_DARK
            self._btn_back      = _BTN_BACK_DARK
            self._sep_color     = "#383850"
            self._title_color   = "#ffffff"
            self._secondary_color = "#8888aa"
            self._muted_color   = "#8888aa"
            self._bullet_color  = "#8888aa"
        else:
            self._card_style    = _CARD_LIGHT
            self._combo_style   = _COMBO_LIGHT
            self._btn_primary   = _BTN_PRIMARY_LIGHT
            self._btn_secondary = _BTN_SECONDARY_LIGHT
            self._btn_back      = _BTN_BACK_LIGHT
            self._sep_color     = "#c4c4d8"
            self._title_color   = "#1e1e2e"
            self._secondary_color = "#5a5a78"
            self._muted_color   = "#8888aa"
            self._bullet_color  = "#5a5a78"

        self.vna_device = vna_device
        logging.info("[welcome_windows.__init__] Initializing welcome window")

        apply_window_icon(self)

        if OSMCalibrationManager:
            self.osm_calibration = OSMCalibrationManager()
            if vna_device and hasattr(vna_device, 'name'):
                self.osm_calibration.device_name = vna_device.name
        else:
            self.osm_calibration = None

        if THRUCalibrationManager:
            self.thru_calibration = THRUCalibrationManager()
            if vna_device and hasattr(vna_device, 'name'):
                self.thru_calibration.device_name = vna_device.name
        else:
            self.thru_calibration = None

        self.setWindowTitle(self.dut_welcome_ui_window_title)
        self.setFixedSize(1050, 520)

        central = QWidget()
        central.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setSpacing(14)
        root.setContentsMargins(24, 18, 24, 18)

        self._build_header(root)
        root.addWidget(_hsep())
        self._build_main_cards(root)
        root.addWidget(_hsep())
        self._build_footer(root)

# ------------------------------------------------------------------------------------------------------------------ #

    def _build_header(self, parent):
        layout = QVBoxLayout()
        layout.setSpacing(4)
        layout.setContentsMargins(0, 0, 0, 0)

        title = QLabel(self.dut_welcome_ui_window_title)
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet(f"font-size: 20px; font-weight: bold; color: {self._title_color};")

        subtitle = QLabel(self.dut_welcome_ui_descriptions if isinstance(self.dut_welcome_ui_descriptions, str)
                          else (self.dut_welcome_ui_descriptions[0] if self.dut_welcome_ui_descriptions else ""))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(f"font-size: 12px; color: {self._muted_color};")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        parent.addLayout(layout)

# ------------------------------------------------------------------------------------------------------------------ #

    def _build_footer(self, parent):
        row = QHBoxLayout()
        row.setContentsMargins(0, 4, 0, 0)
        back = QPushButton(self.dut_welcome_ui_back_button)
        back.setFixedSize(200, 38)
        back.setStyleSheet(self._btn_back)
        back.clicked.connect(self.return_to_menu_window)
        row.addStretch(1)
        row.addWidget(back)
        row.addStretch(1)
        parent.addLayout(row)

# ------------------------------------------------------------------------------------------------------------------ #

    def _build_main_cards(self, parent):
        row = QHBoxLayout()
        row.setSpacing(14)
        row.addWidget(self._build_card_calibration(), stretch=1)
        row.addWidget(self._build_card_measurements(), stretch=1)
        row.addWidget(self._build_card_import(), stretch=1)
        parent.addLayout(row, stretch=1)

# ------------------------------------------------------------------------------------------------------------------ #

    def _build_card_calibration(self):
        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet(self._card_style)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        # Title row
        title_lbl = QLabel(self.dut_welcome_ui_calibration_title)
        title_lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {self._title_color}; background: transparent;")
        layout.addWidget(title_lbl)

        layout.addSpacing(6)
        layout.addWidget(_hsep(self._sep_color))
        layout.addSpacing(14)

        desc = QLabel(self.dut_welcome_ui_descriptions if isinstance(self.dut_welcome_ui_descriptions, str)
                      else "  ".join(self.dut_welcome_ui_descriptions))
        desc.setWordWrap(True)
        desc.setStyleSheet(f"font-size: 12px; color: {self._secondary_color}; background: transparent;")
        layout.addWidget(desc)

        layout.addSpacing(14)

        features = [
            ("○", "Short, Open, Load, Match (OSM) standards"),
            ("○", "Thru standard for transmission calibration"),
            ("○", "Step-by-step guided measurement wizard"),
        ]
        for bullet, text in features:
            layout.addLayout(_bullet_row(bullet, text, "#4da6ff", self._bullet_color))
            layout.addSpacing(6)

        layout.addStretch(1)

        self.calibration_wizard_button = QPushButton(self.dut_welcome_ui_label_calibration_button)
        self.calibration_wizard_button.setFixedHeight(44)
        self.calibration_wizard_button.setStyleSheet(self._btn_primary)
        self.calibration_wizard_button.clicked.connect(self.open_calibration_wizard)
        layout.addWidget(self.calibration_wizard_button)

        return card

# ------------------------------------------------------------------------------------------------------------------ #

    def _build_card_measurements(self):
        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet(self._card_style)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        # Title row
        title_lbl = QLabel(self.dut_welcome_ui_kit_title)
        title_lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {self._title_color}; background: transparent;")
        layout.addWidget(title_lbl)

        layout.addSpacing(6)
        layout.addWidget(_hsep(self._sep_color))
        layout.addSpacing(14)

        kit_lbl = QLabel(self.dut_welcome_ui_kit_selection_title)
        kit_lbl.setStyleSheet(f"font-size: 12px; color: {self._muted_color}; background: transparent;")
        layout.addWidget(kit_lbl)

        layout.addSpacing(10)

        self._load_calibration_kits()

        self.kit_dropdown = QComboBox()
        self.kit_dropdown.setStyleSheet(self._combo_style)
        self.kit_dropdown.addItem("None")
        for kit_name in self.kit_names:
            self.kit_dropdown.addItem(kit_name)
        self._set_current_kit_selection()
        self.kit_dropdown.currentTextChanged.connect(self._on_kit_selection_changed)
        layout.addWidget(self.kit_dropdown)

        current_text = self.kit_dropdown.currentText()
        self.selected_kit_name = None if current_text.startswith("None") else current_text

        layout.addSpacing(10)

        self.kit_info_label = QLabel(self.dut_welcome_ui_no_kit_selected)
        self.kit_info_label.setWordWrap(True)
        self.kit_info_label.setStyleSheet(
            f"font-size: 12px; color: {self._secondary_color}; background: transparent; font-style: italic;"
        )
        layout.addWidget(self.kit_info_label)
        self._update_kit_info_display()

        layout.addStretch(1)

        self.graphics_button = QPushButton(self.dut_welcome_ui_label_kit_button)
        self.graphics_button.setFixedHeight(44)
        self.graphics_button.setStyleSheet(self._btn_primary)
        self.graphics_button.clicked.connect(self.graphics_clicked)
        layout.addWidget(self.graphics_button)

        return card

# ------------------------------------------------------------------------------------------------------------------ #

    def _build_card_import(self):
        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet(self._card_style)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        # Title row
        title_lbl = QLabel(self.dut_welcome_ui_import_calibration_title)
        title_lbl.setStyleSheet(f"font-size: 14px; font-weight: bold; color: {self._title_color}; background: transparent;")
        layout.addWidget(title_lbl)

        layout.addSpacing(6)
        layout.addWidget(_hsep(self._sep_color))
        layout.addSpacing(14)

        desc = QLabel("Import a previously exported calibration kit ZIP file. The kit will be registered and ready to use.")
        desc.setWordWrap(True)
        desc.setStyleSheet(f"font-size: 12px; color: {self._secondary_color}; background: transparent;")
        layout.addWidget(desc)

        layout.addSpacing(16)

        files_lbl = QLabel("The ZIP must contain:")
        files_lbl.setStyleSheet(f"font-size: 12px; color: {self._muted_color}; background: transparent;")
        layout.addWidget(files_lbl)

        layout.addSpacing(8)

        for item in ["kit_info.ini (metadata)", "errors/ (calibration errors)", "measurements/ (raw data)"]:
            layout.addLayout(_bullet_row("✓", item, "#5cb85c", self._bullet_color))
            layout.addSpacing(5)

        layout.addStretch(1)

        self.import_button = QPushButton("Import Calibration Kit")
        self.import_button.setFixedHeight(44)
        self.import_button.setStyleSheet(self._btn_primary)
        self.import_button.clicked.connect(self.import_calibration)
        layout.addWidget(self.import_button)

        return card

# ------------------------------------------------------------------------------------------------------------------ #
# Functional methods — untouched
# ------------------------------------------------------------------------------------------------------------------ #

    def _set_current_kit_selection(self):
        calibration_name = self._get_current_calibration_name()

        if "_" in str(calibration_name):
            calibration_name_split = str(calibration_name).rsplit("_", 1)[0]
        else:
            calibration_name_split = str(calibration_name)

        if calibration_name_split in self.kit_names:
            kit_index = self.kit_names.index(calibration_name_split) + 1
            self.kit_dropdown.setCurrentIndex(kit_index)
        else:
            self.kit_dropdown.setCurrentIndex(0)

    def _on_kit_selection_changed(self, selected_text):
        logging.info(f"[welcome_windows._on_kit_selection_changed] Kit selection changed to: {selected_text}")
        if selected_text.startswith("None"):
            self.selected_kit_name = None
        else:
            self.selected_kit_name = selected_text
        self._update_kit_info_display()

    def _update_kit_info_display(self):
        if hasattr(self, 'selected_kit_name') and self.selected_kit_name:
            self.kit_info_label.setContentsMargins(0, 0, 0, 0)
            if self.selected_kit_name in self.kit_names:
                kit_index = self.kit_names.index(self.selected_kit_name)
                kit_id = self.kit_ids[kit_index] if kit_index < len(self.kit_ids) else "Unknown"
                settings = get_settings(
                    "INI/dut_measurement/calibration_config/calibration_config.ini",
                    "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
                    Path(__file__).resolve()
                )
                kit_method   = settings.value(f"Kit_{kit_id}/method", "Unknown")
                kit_datetime = settings.value(f"Kit_{kit_id}/DateTime_Kits", "Unknown")
                start_hz     = settings.value(f"Kit_{kit_id}/StartFreqHz", 0)
                stop_hz      = settings.value(f"Kit_{kit_id}/StopFreqHz",  0)
                segments     = settings.value(f"Kit_{kit_id}/Segments",    0)

                def _auto_fmt(hz):
                    try:
                        hz = float(hz)
                    except (TypeError, ValueError):
                        return str(hz)
                    if hz >= 1e9:   return f"{hz / 1e9:g} GHz"
                    elif hz >= 1e6: return f"{hz / 1e6:g} MHz"
                    elif hz >= 1e3: return f"{hz / 1e3:g} kHz"
                    else:           return f"{hz:g} Hz"

                info_text = f"Method: {kit_method}\nCreated: {kit_datetime}"
                try:
                    s = float(start_hz); e = float(stop_hz); pts = int(float(segments))
                    if s and e:
                        info_text += f"\nFrequency: {_auto_fmt(s)} – {_auto_fmt(e)},  {pts} pts"
                except (TypeError, ValueError):
                    pass
                self.kit_info_label.setText(info_text)
            else:
                self.kit_info_label.setText(f"Selected Kit: {self.selected_kit_name}\n(Kit details not found)")
        else:
            self.kit_info_label.setContentsMargins(0, 0, 0, 0)
            self.kit_info_label.setText(f"{self.dut_welcome_ui_no_kit_selected}")

    def _load_calibration_kits(self):
        logging.info("[welcome_windows._load_calibration_kits] Loading calibration kits")
        settings_calibration = get_settings(
            "INI/dut_measurement/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve()
        )
        kit_groups = [g for g in settings_calibration.childGroups() if g.startswith("Kit_")]
        self.kit_names = [settings_calibration.value(f"{g}/kit_name", "") for g in kit_groups]
        self.kit_ids = [int(settings_calibration.value(f"{g}/id", 0)) for g in kit_groups]

    def _get_current_calibration_name(self):
        settings_calibration = get_settings(
            "INI/dut_measurement/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve()
        )
        calibration_name = settings_calibration.value("Calibration/Name", "No Calibration")
        if "_" in calibration_name:
            calibration_name_split = calibration_name.rsplit("_", 1)[0]
        else:
            calibration_name_split = calibration_name
        matched_id = 0
        self.current_index = -1
        if calibration_name_split in self.kit_names:
            self.current_index = self.kit_names.index(calibration_name_split)
            matched_id = self.kit_ids[self.current_index]
        return calibration_name

    def import_calibration(self):
        import zipfile
        import configparser
        from PySide6.QtWidgets import QFileDialog, QMessageBox, QDialog
        from NanoVNA_UTN_Toolkit.shared.utils.resources.calibration_path_utils import get_calibration_path
        from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.calibration_menu.save_calibration.save_calibration import _ImportKitDialog

        zip_path, _ = QFileDialog.getOpenFileName(
            self, "Select calibration kit ZIP", "", "ZIP files (*.zip)"
        )
        if not zip_path:
            return

        try:
            with zipfile.ZipFile(zip_path, 'r') as zf:
                if "kit_info.ini" not in zf.namelist():
                    QMessageBox.warning(
                        self, "Invalid kit file",
                        "The selected ZIP does not contain a kit_info.ini.\n"
                        "Make sure it was exported using File → Export Calibration Kit."
                    )
                    return
                ini_bytes = zf.read("kit_info.ini").decode("utf-8")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not open ZIP:\n{e}")
            return

        cfg = configparser.ConfigParser()
        cfg.read_string(ini_bytes)
        kit_info = dict(cfg["Kit"]) if "Kit" in cfg else {}

        zip_kit_name = kit_info.get("name", "") or os.path.splitext(os.path.basename(zip_path))[0]

        dlg = _ImportKitDialog(self, zip_kit_name, kit_info)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        name = dlg.kit_name
        if not name:
            return

        settings_cal = get_settings(
            "INI/dut_measurement/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve()
        )
        existing_groups = settings_cal.childGroups()
        for g in existing_groups:
            if g.startswith("Kit_") and settings_cal.value(f"{g}/kit_name", "") == name:
                QMessageBox.warning(self, "Duplicate name",
                                    f"A kit named '{name}' already exists. Please choose another name.")
                return

        kits_base = get_calibration_path(
            "modules/dut_measurement/calibration/kits",
            "modules/dut_measurement/calibration/kits",
            Path(__file__).resolve()
        )
        kit_folder = os.path.join(kits_base, name)

        try:
            os.makedirs(kit_folder, exist_ok=True)
            with zipfile.ZipFile(zip_path, 'r') as zf:
                for member in zf.namelist():
                    if member == "kit_info.ini":
                        continue
                    zf.extract(member, kit_folder)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not extract kit:\n{e}")
            return

        kit_ids = [int(g.split("_")[1]) for g in existing_groups if g.startswith("Kit_") and g.split("_")[1].isdigit()]
        next_id = max(kit_ids, default=0) + 1
        calibration_entry_name = f"Kit_{next_id}"
        full_calibration_name = f"{name}_{next_id}"
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        method     = kit_info.get("method", "")
        start_hz   = kit_info.get("start_freq_hz", 0)
        stop_hz    = kit_info.get("stop_freq_hz", 0)
        segments   = kit_info.get("segments", 101)
        start_unit = kit_info.get("start_unit", "MHz")
        stop_unit  = kit_info.get("stop_unit", "MHz")

        settings_cal.beginGroup(calibration_entry_name)
        settings_cal.setValue("kit_name", name)
        settings_cal.setValue("method", method)
        settings_cal.setValue("id", next_id)
        settings_cal.setValue("DateTime_Kits", current_datetime)
        settings_cal.setValue("StartFreqHz", int(float(start_hz)) if start_hz else 0)
        settings_cal.setValue("StopFreqHz",  int(float(stop_hz))  if stop_hz  else 0)
        settings_cal.setValue("Segments",    int(segments))
        settings_cal.setValue("StartUnit",   start_unit)
        settings_cal.setValue("StopUnit",    stop_unit)
        settings_cal.endGroup()

        if method == "OSM (Open - Short - Match)":
            parameter = "S11"
        elif method == "Thru Normalization":
            parameter = "S21"
        elif method == "Open/Short Normalization":
            parameter = "S11"
        else:
            parameter = "S11, S21"

        settings_cal.beginGroup("Calibration")
        settings_cal.setValue("Name", full_calibration_name)
        settings_cal.setValue("id", next_id)
        settings_cal.setValue("Method", method)
        settings_cal.setValue("DateTime_Kits", current_datetime)
        settings_cal.setValue("Kits", True)
        settings_cal.setValue("NoCalibration", False)
        settings_cal.setValue("Parameter", parameter)
        settings_cal.endGroup()
        settings_cal.sync()

        if start_hz and stop_hz:
            sweep_settings = get_settings(
                "INI/dut_measurement/sweep_config/sweep_config.ini",
                "modules/dut_measurement/ui/sweep_window/sweep_config/sweep_config.ini",
                Path(__file__).resolve()
            )
            sweep_settings.setValue("Frequency/StartFreqHz", int(float(start_hz)))
            sweep_settings.setValue("Frequency/StopFreqHz",  int(float(stop_hz)))
            sweep_settings.setValue("Frequency/Segments",    int(segments))
            sweep_settings.setValue("Frequency/StartUnit",   start_unit)
            sweep_settings.setValue("Frequency/StopUnit",    stop_unit)
            sweep_settings.sync()

        logging.info(f"[welcome_windows.import_calibration] Imported kit '{name}' as {full_calibration_name}")

        # Refresh kit dropdown and select the new kit
        self._load_calibration_kits()
        self.kit_dropdown.blockSignals(True)
        self.kit_dropdown.clear()
        self.kit_dropdown.addItem("None")
        for kit_name in self.kit_names:
            self.kit_dropdown.addItem(kit_name)
        idx = self.kit_names.index(name) + 1 if name in self.kit_names else 0
        self.kit_dropdown.setCurrentIndex(idx)
        self.kit_dropdown.blockSignals(False)
        self._on_kit_selection_changed(self.kit_dropdown.currentText())

    def start_calibration(self, files, selected_method, dialog):
        print(f"Starting calibration with method: {selected_method}")
        for f in files:
            print(f)
        dialog.accept()
        self.save_calibration_dialog(selected_method, files)

    def save_calibration_dialog(self, selected_method, files):
        from PySide6.QtWidgets import QMessageBox
        if not self.osm_calibration:
            return
        if not self.thru_calibration:
            return

        osm_status = self.osm_calibration.is_complete_true()
        thru_status = self.thru_calibration.is_complete_true()

        from PySide6.QtWidgets import QInputDialog

        if selected_method == "OSM (Open - Short - Match)":
            prefix = "OSM"
        elif selected_method == "Thru Normalization":
            prefix = "Thru_Normalization"
        elif selected_method == "1-Port+N":
            prefix = "1PortN"
        elif selected_method == "Enhanced-Response":
            prefix = "Enhanced Response"

        name, ok = QInputDialog.getText(
            self,
            'Save Calibration',
            'Enter calibration name:',
            text=f'{prefix}_Calibration_{self.get_current_timestamp()}'
        )

        is_external_kit = True

        if ok and name:
            try:
                success = self.osm_calibration.save_calibration_file(name, selected_method, is_external_kit, files)
                if success:
                    QMessageBox.information(
                        self, "Success",
                        f"Calibration '{name}' saved successfully!\n\nFiles saved in:\n- Touchstone format\n- .cal format"
                    )

                success = self.thru_calibration.save_calibration_file(name, selected_method, is_external_kit, files, osm_instance=self.osm_calibration)
                if success:
                    QMessageBox.information(
                        self, "Success",
                        f"Calibration '{name}' saved successfully!\n\nFiles saved in:\n- Touchstone format\n- .cal format"
                    )

                settings_calibration = get_settings(
                    "INI/dut_measurement/calibration_config/calibration_config.ini",
                    "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
                    Path(__file__).resolve()
                )

                existing_groups = settings_calibration.childGroups()
                for g in existing_groups:
                    if g.startswith("Kit_"):
                        existing_name = settings_calibration.value(f"{g}/kit_name", "")
                        if existing_name == name:
                            from PySide6.QtWidgets import QMessageBox
                            QMessageBox.warning(self, "Duplicate Name",
                                                f"The kit name '{name}' already exists.\nPlease choose another name.")
                            return

                if getattr(self, 'last_saved_kit_id', None):
                    next_id = self.last_saved_kit_id
                else:
                    kit_ids = [int(g.split("_")[1]) for g in existing_groups if g.startswith("Kit_") and g.split("_")[1].isdigit()]
                    next_id = max(kit_ids, default=0) + 1
                    self.last_saved_kit_id = next_id

                calibration_entry_name = f"Kit_{next_id}"
                full_calibration_name = f"{name}_{next_id}"
                current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                settings_calibration.beginGroup(calibration_entry_name)
                settings_calibration.setValue("kit_name", name)
                settings_calibration.setValue("method", selected_method)
                settings_calibration.setValue("id", next_id)
                settings_calibration.setValue("DateTime_Kits", current_datetime)
                settings_calibration.endGroup()

                settings_calibration.beginGroup("Calibration")
                settings_calibration.setValue("Name", full_calibration_name)
                settings_calibration.endGroup()
                settings_calibration.sync()

                settings_calibration.setValue("Calibration/Kits", True)
                settings_calibration.setValue("Calibration/NoCalibration", False)
                settings_calibration.setValue("Calibration/CalibrationWizard", False)

                if selected_method == "OSM (Open - Short - Match)":
                    parameter = "S11"
                elif selected_method == "Thru Normalization":
                    parameter = "S21"
                elif selected_method == "Open/Short Normalization":
                    parameter = "S11"
                else:
                    parameter = "S11, S21"

                settings_calibration.setValue("Calibration/Parameter", parameter)
                settings_calibration.sync()

            except Exception as e:
                logging.error(f"[CalibrationWelcome] Error saving calibration: {e}")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"Error saving calibration: {str(e)}")

    def get_current_timestamp(self):
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def open_calibration_wizard(self):
        settings_calibration = get_settings(
            "INI/dut_measurement/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve()
        )
        settings_calibration.setValue("Calibration/Kits", False)
        settings_calibration.setValue("Calibration/NoCalibration", False)
        settings_calibration.setValue("Calibration/CalibrationWizard", True)
        settings_calibration.sync()

        logging.info("[welcome_windows.open_calibration_wizard] Opening calibration wizard")

        stop_realtime = safe_import("NanoVNA_UTN_Toolkit.shared.utils.real_time.real_time", "stop_realtime")
        try:
            stop_realtime(self)
        except:
            pass

        if self.vna_device:
            self.welcome_windows = CalibrationWizard(self.vna_device, caller="welcome")
        else:
            self.welcome_windows = CalibrationWizard()
        self.welcome_windows.show()
        self.close()

    def graphics_clicked(self):
        logging.info("[welcome_windows.graphics_clicked] Opening graphics window")
        settings_calibration = get_settings(
            "INI/dut_measurement/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve()
        )
        current_selection = self.kit_dropdown.currentText()
        if current_selection and not current_selection.startswith("None"):
            self._apply_selected_kit_calibration(current_selection)
        else:
            settings_calibration.setValue("Calibration/Kits", False)
            settings_calibration.setValue("Calibration/NoCalibration", True)
            settings_calibration.setValue("Calibration/CalibrationWizard", False)
            settings_calibration.sync()

        try:
            stop_realtime(self)
        except:
            pass

        if self.vna_device:
            graphics_window = NanoVNAGraphics(vna_device=self.vna_device)
        else:
            graphics_window = NanoVNAGraphics()
        graphics_window.show()
        self.close()

    def _apply_selected_kit_calibration(self, kit_name):
        logging.info(f"[welcome_windows._apply_selected_kit_calibration] Applying kit: {kit_name}")
        settings_calibration = get_settings(
            "INI/dut_measurement/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve()
        )
        kit_groups = [g for g in settings_calibration.childGroups() if g.startswith("Kit_")]
        kit_names = [settings_calibration.value(f"{g}/kit_name", "") for g in kit_groups]
        kit_ids = [int(settings_calibration.value(f"{g}/id", 0)) for g in kit_groups]
        kit_methods = [settings_calibration.value(f"{g}/method", "") for g in kit_groups]
        kit_date_times = [settings_calibration.value(f"{g}/DateTime_Kits", "") for g in kit_groups]

        if kit_name in kit_names:
            idx = kit_names.index(kit_name)
            matched_id = kit_ids[idx]
            matched_method = kit_methods[idx]
            matched_date_time_kit = kit_date_times[idx]
            kit_name_with_id = f"{kit_name}_{matched_id}"

            settings_calibration.setValue("Calibration/Name", kit_name_with_id)
            settings_calibration.setValue("Calibration/id", matched_id)
            settings_calibration.setValue("Calibration/Method", matched_method)
            settings_calibration.setValue("Calibration/DateTime_Kits", matched_date_time_kit)

            if matched_method == "OSM (Open - Short - Match)":
                parameter = "S11"
            elif matched_method == "Thru Normalization":
                parameter = "S21"
            elif matched_method == "Open/Short Normalization":
                parameter = "S11"
            else:
                parameter = "S11, S21"

            settings_calibration.setValue("Calibration/Parameter", parameter)
            settings_calibration.setValue("Calibration/Kits", True)
            settings_calibration.setValue("Calibration/NoCalibration", False)
            settings_calibration.setValue("Calibration/CalibrationWizard", False)
            settings_calibration.sync()

    def return_to_menu_window(self):
        from NanoVNA_UTN_Toolkit.modules.menu_window import ModuleSelectionWindow
        if self.vna_device:
            self.menu_window = ModuleSelectionWindow(vna_device=self.vna_device)
        else:
            self.menu_window = ModuleSelectionWindow()
        self.menu_window.show()
        self.close()

# ------------------------------------------------------------------------------------------------------------------ #

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    ventana = NanoVNAWelcome()
    ventana.show()
    sys.exit(app.exec())
