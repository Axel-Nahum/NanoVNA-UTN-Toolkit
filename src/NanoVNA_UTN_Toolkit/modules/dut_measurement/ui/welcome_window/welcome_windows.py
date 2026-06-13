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
    }
    QPushButton:hover  { background-color: #1a3a5c; color: #aacfff; border: 1px solid #4da6ff; }
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
    line = QWidget()
    line.setFixedHeight(1)
    line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
    line.setStyleSheet(f"background-color: {color};")
    return line


def _bullet_row(icon, text, icon_color="#5cb85c"):
    row = QHBoxLayout()
    row.setSpacing(10)
    row.setContentsMargins(0, 0, 0, 0)
    icon_lbl = QLabel(icon)
    icon_lbl.setStyleSheet(f"color: {icon_color}; font-size: 13px; background: transparent;")
    icon_lbl.setFixedWidth(18)
    text_lbl = QLabel(text)
    text_lbl.setWordWrap(True)
    text_lbl.setStyleSheet("color: #aaaaaa; font-size: 12px; background: transparent;")
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
        self.resize(1050, 520)
        self.setMinimumSize(900, 460)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

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
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #ffffff;")

        subtitle = QLabel(self.dut_welcome_ui_descriptions if isinstance(self.dut_welcome_ui_descriptions, str)
                          else (self.dut_welcome_ui_descriptions[0] if self.dut_welcome_ui_descriptions else ""))
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("font-size: 12px; color: #666666;")

        layout.addWidget(title)
        layout.addWidget(subtitle)
        parent.addLayout(layout)

# ------------------------------------------------------------------------------------------------------------------ #

    def _build_footer(self, parent):
        row = QHBoxLayout()
        row.setContentsMargins(0, 4, 0, 0)
        back = QPushButton("← Back to Menu")
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
        row.addWidget(self._build_card_calibration(), stretch=1)
        row.addWidget(self._build_card_measurements(), stretch=1)
        row.addWidget(self._build_card_import(), stretch=1)
        parent.addLayout(row, stretch=1)

# ------------------------------------------------------------------------------------------------------------------ #

    def _build_card_calibration(self):
        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet(_CARD)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        # Title row
        title_row = QHBoxLayout()
        icon = QLabel("🔧")
        icon.setStyleSheet("font-size: 15px; background: transparent;")
        title_lbl = QLabel(self.dut_welcome_ui_calibration_title)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff; background: transparent;")
        title_row.addWidget(icon)
        title_row.addWidget(title_lbl, stretch=1)
        layout.addLayout(title_row)

        layout.addSpacing(6)
        layout.addWidget(_hsep())
        layout.addSpacing(14)

        desc = QLabel(self.dut_welcome_ui_descriptions if isinstance(self.dut_welcome_ui_descriptions, str)
                      else "  ".join(self.dut_welcome_ui_descriptions))
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; color: #999999; background: transparent;")
        layout.addWidget(desc)

        layout.addSpacing(14)

        features = [
            ("○", "Short, Open, Load, Match (OSM) standards"),
            ("○", "Thru standard for transmission calibration"),
            ("○", "Step-by-step guided measurement wizard"),
        ]
        for bullet, text in features:
            layout.addLayout(_bullet_row(bullet, text, "#4da6ff"))
            layout.addSpacing(6)

        layout.addStretch(1)

        self.calibration_wizard_button = QPushButton(self.dut_welcome_ui_label_calibration_button)
        self.calibration_wizard_button.setFixedHeight(44)
        self.calibration_wizard_button.setStyleSheet(_BTN_PRIMARY)
        self.calibration_wizard_button.clicked.connect(self.open_calibration_wizard)
        layout.addWidget(self.calibration_wizard_button)

        return card

# ------------------------------------------------------------------------------------------------------------------ #

    def _build_card_measurements(self):
        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet(_CARD)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        # Title row
        title_row = QHBoxLayout()
        icon = QLabel("📊")
        icon.setStyleSheet("font-size: 15px; background: transparent;")
        title_lbl = QLabel(self.dut_welcome_ui_kit_title)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff; background: transparent;")
        title_row.addWidget(icon)
        title_row.addWidget(title_lbl, stretch=1)
        layout.addLayout(title_row)

        layout.addSpacing(6)
        layout.addWidget(_hsep())
        layout.addSpacing(14)

        kit_lbl = QLabel(self.dut_welcome_ui_kit_selection_title)
        kit_lbl.setStyleSheet("font-size: 12px; color: #777777; background: transparent;")
        layout.addWidget(kit_lbl)

        layout.addSpacing(10)

        self._load_calibration_kits()

        self.kit_dropdown = QComboBox()
        self.kit_dropdown.setStyleSheet(_COMBO)
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
            "font-size: 12px; color: #555555; background: transparent; font-style: italic;"
        )
        layout.addWidget(self.kit_info_label)
        self._update_kit_info_display()

        layout.addStretch(1)

        self.graphics_button = QPushButton(self.dut_welcome_ui_label_kit_button)
        self.graphics_button.setFixedHeight(44)
        self.graphics_button.setStyleSheet(_BTN_PRIMARY)
        self.graphics_button.clicked.connect(self.graphics_clicked)
        layout.addWidget(self.graphics_button)

        return card

# ------------------------------------------------------------------------------------------------------------------ #

    def _build_card_import(self):
        card = QWidget()
        card.setObjectName("card")
        card.setStyleSheet(_CARD)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(0)

        # Title row
        title_row = QHBoxLayout()
        icon = QLabel("📁")
        icon.setStyleSheet("font-size: 15px; background: transparent;")
        title_lbl = QLabel(self.dut_welcome_ui_import_calibration_title)
        title_lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #ffffff; background: transparent;")
        title_row.addWidget(icon)
        title_row.addWidget(title_lbl, stretch=1)
        layout.addLayout(title_row)

        layout.addSpacing(6)
        layout.addWidget(_hsep())
        layout.addSpacing(14)

        desc = QLabel(self.dut_welcome_ui_import_calibration_description)
        desc.setWordWrap(True)
        desc.setStyleSheet("font-size: 12px; color: #999999; background: transparent;")
        layout.addWidget(desc)

        layout.addSpacing(16)

        files_lbl = QLabel("Required Touchstone files:")
        files_lbl.setStyleSheet("font-size: 12px; color: #666666; background: transparent;")
        layout.addWidget(files_lbl)

        layout.addSpacing(8)

        for fname in ["open.s1p", "short.s1p", "load/match.s1p", "thru.s2p"]:
            layout.addLayout(_bullet_row("✓", fname, "#5cb85c"))
            layout.addSpacing(5)

        layout.addStretch(1)

        self.import_button = QPushButton("Import Calibration")
        self.import_button.setFixedHeight(44)
        self.import_button.setStyleSheet(_BTN_PRIMARY)
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
                kit_method = settings.value(f"Kit_{kit_id}/method", "Unknown")
                kit_datetime = settings.value(f"Kit_{kit_id}/DateTime_Kits", "Unknown")
                info_text = f"Selected Kit: {self.selected_kit_name}\nMethod: {kit_method}\nCreated: {kit_datetime}"
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
        from PySide6.QtWidgets import QFileDialog, QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QComboBox
        import os

        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Calibration Files",
            "",
            "Touchstone Files (*.s1p *.s2p);;All Files (*)"
        )

        if not files:
            QMessageBox.warning(self, "No Files Selected", "Please select the 4 calibration files.")
            return

        required_names = ["open", "short", "load", "match", "thru"]
        filenames = [os.path.basename(f).lower() for f in files]
        found = {name: any(name in f for f in filenames) for name in required_names}
        has_load_or_match = found["load"] or found["match"]

        missing = []
        if not found["open"]:   missing.append("open")
        if not found["short"]:  missing.append("short")
        if not has_load_or_match: missing.append("load or match")
        if not found["thru"]:   missing.append("thru")

        if missing:
            QMessageBox.warning(self, "Missing Files", f"The following calibration files are missing: {', '.join(missing)}")
            return

        if len(files) != 4:
            QMessageBox.warning(self, "Invalid Selection", "You must select exactly 4 calibration files.")
            return

        QMessageBox.information(self, "Success", "All calibration files selected successfully!")

        dialog = QDialog(self)
        dialog.setWindowTitle("NanoVNA UTN Toolkit - Select Calibration Method")
        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        label = QLabel("Select Method", dialog)
        main_layout.addWidget(label)

        self.select_method = QComboBox()
        self.select_method.setEditable(False)
        self.select_method.addItem("Select Method")
        item = self.select_method.model().item(0)
        item.setEnabled(False)
        item.setForeground(QColor(120, 120, 120))
        self.select_method.addItems([
            "OSM (Open - Short - Match)",
            "Thru Normalization",
            "1-Port+N",
            "Enhanced-Response"
        ])
        main_layout.addWidget(self.select_method)

        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        cancel_button = QPushButton("Cancel", dialog)
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)
        calibrate_button = QPushButton("Calibrate", dialog)
        calibrate_button.clicked.connect(lambda: self.start_calibration(files, self.select_method.currentText(), dialog))
        button_layout.addWidget(calibrate_button)
        main_layout.addLayout(button_layout)

        dialog.exec()

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
