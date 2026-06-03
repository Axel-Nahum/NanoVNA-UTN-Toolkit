from NanoVNA_UTN_Toolkit.utils import safe_import
import logging
import os
import sys

from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QPushButton, QWidget, QScrollArea
)

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6 import QtCore

# Import get_settings 

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

show_calibration_warning, save_kit_dialog = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.calibration_menu.save_calibration.save_calibration", "show_calibration_warning", "save_kit_dialog")

handle_all_kits_deleted, handle_deleted_current_kit = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.calibration_menu.delete_calibration.delete_calibration", "handle_all_kits_deleted", "handle_deleted_current_kit")

get_calibration_path = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.calibration_path_utils", "get_calibration_path")

# ---------------------------------------------------------------------------------------------------------------- #

def open_calibration_wizard(self):
        
        from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.wizard_cal_windows.wizard_windows import CalibrationWizard

        logging.info("[wizard_windows.open_calibration_wizard] Opening calibration wizard")
        
        if self.vna_device:
            self.welcome_windows = CalibrationWizard(self.vna_device, parent = self, caller="graphics")
        else:
            self.welcome_windows = CalibrationWizard(parent = self, caller="graphics")
        self.welcome_windows.show()
        self.close()
        self.deleteLater()

def open_no_calibration(self):

    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_window import NanoVNAGraphics

    logging.info("[graphics_window.open_no_calibration] Opening no calibration")

    # Load configuration for calibration settings
    settings_calibration = get_settings(
        "INI/dut_measurement/calibration_config/calibration_config.ini",
        "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
        Path(__file__).resolve()
    )

    # Save "No Calibration" settings

    settings_calibration.beginGroup("Calibration")
    settings_calibration.setValue("Kits", False)
    settings_calibration.setValue("NoCalibration", True)
    settings_calibration.setValue("CalibrationWizard", False)
    settings_calibration.endGroup()

    if self.vna_device:
        self.graphic_window = NanoVNAGraphics(vna_device = self.vna_device)
    else:
        self.graphic_window = NanoVNAGraphics()
    self.graphic_window.show()
    self.close()
    self.deleteLater()

def select_kit_dialog(self): 

    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_window import NanoVNAGraphics
    
    # --- Create dialog ---
    dialog = QDialog(self)
    dialog.setWindowTitle(f"{self.cal_kit_window_title_select}")
    dialog.setMinimumWidth(400)

    layout = QVBoxLayout(dialog)

    # Load configuration for calibration settings
    settings = get_settings(
        "INI/dut_measurement/calibration_config/calibration_config.ini",
        "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
        Path(__file__).resolve()
    )

    # --- List widget for kits ---
    list_widget = QListWidget()
    select_label = QLabel(f"{self.cal_kit_window_select_text}")
    select_label.setStyleSheet("font-size: 9pt;")
    layout.addWidget(select_label)
    layout.addWidget(list_widget)

    # --- Populate list ---
    groups = settings.childGroups()
    kits_info = {}  # Para guardar info de cada kit
    for g in groups:
        if g.startswith("Kit_"):
            name = settings.value(f"{g}/kit_name", "").strip()
            method = settings.value(f"{g}/method", "").strip()
            kit_id = int(settings.value(f"{g}/id", 0))
            date_time_kits = settings.value(f"{g}/DateTime_Kits", "").strip()
            if name:
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, g)
                list_widget.addItem(item)
                kits_info[name] = {"id": kit_id, "method": method, "DateTime_Kits": date_time_kits}

    # --- Selected tag area (solo uno) ---
    selected_name = [None]  # lista de un elemento para mutabilidad
    selected_area = QHBoxLayout()
    selected_container = QWidget()
    selected_container.setLayout(selected_area)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(selected_container)
    layout.addWidget(scroll)

    # --- Add selected kit to tag area ---
    def add_selected(item):
        # Limpiar selección previa
        for i in reversed(range(selected_area.count())):
            widget = selected_area.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        selected_name[0] = None

        name = item.text()
        selected_name[0] = name

        tag_widget = QWidget()
        tag_layout = QHBoxLayout(tag_widget)
        tag_layout.setContentsMargins(5, 2, 5, 2)
        label = QLabel(name)

        # Botón de “deseleccionar” (cruz roja)
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        icon_path = os.path.join(project_root, "NanoVNA_UTN_Toolkit", "assets", "icons", "delete.svg")

        remove_btn = QPushButton()
        remove_btn.setIcon(QIcon(icon_path))
        remove_btn.setIconSize(QtCore.QSize(20, 20))
        remove_btn.setFixedSize(30, 30)
        remove_btn.setFlat(True)
        remove_btn.setStyleSheet("""
            QPushButton { border: none; background-color: transparent; }
            QPushButton:hover { background-color: rgba(255, 0, 0, 50); }
        """)

        tag_layout.addWidget(label)
        tag_layout.addWidget(remove_btn)

        def remove_tag():
            tag_widget.setParent(None)
            selected_name[0] = None

        remove_btn.clicked.connect(remove_tag)
        selected_area.addWidget(tag_widget)

    # --- Select button action ---
    def select_kit():
        if not selected_name[0]:
            return  # No hay kit seleccionado
        name = selected_name[0]
        kit_info = kits_info[name]

        kit_name_with_id = f"{name}_{kit_info['id']}" 

        if kit_info["method"] == "OSM (Open - Short - Match)":
            parameter = "S11"
        elif kit_info["method"] == "Normalization":
            parameter = "S21"
        else:
            parameter = "S11, S21"

        # Guardar en [Calibration]
        settings.beginGroup("Calibration")
        settings.setValue("Name", kit_name_with_id)
        settings.setValue("id", kit_info["id"])
        settings.setValue("Method", kit_info["method"])
        settings.setValue("DateTime_Kits", kit_info["DateTime_Kits"])
        settings.setValue("Kits", True)
        settings.setValue("NoCalibration", False)
        settings.setValue("Parameter", parameter)
        settings.endGroup()
        settings.sync()

        dialog.accept()  

        if self.vna_device:
            graphics_window = NanoVNAGraphics(vna_device=self.vna_device)
        else:
            graphics_window = NanoVNAGraphics()
        graphics_window.show()
        self.close()

    # --- Buttons ---
    btn_layout = QHBoxLayout()
    btn_cancel = QPushButton(f"{self.cal_kit_window_cancel}")
    btn_select = QPushButton(f"{self.cal_kit_window_select}")
    btn_layout.addWidget(btn_cancel)
    btn_layout.addWidget(btn_select)
    layout.addLayout(btn_layout)

    # --- Connect signals ---
    list_widget.itemClicked.connect(add_selected)
    btn_cancel.clicked.connect(dialog.reject)
    btn_select.clicked.connect(select_kit)  # <--- sin paréntesis

    dialog.exec()

def handle_save_calibration(self):

    # Load configuration for calibration settings
    settings = get_settings(
        "INI/dut_measurement/calibration_config/calibration_config.ini",
        "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
        Path(__file__).resolve()
    )

    settings.sync()

    # Read values from INI
    kits_ok = settings.value("Calibration/Kits", False, type=bool)
    no_calibration = settings.value("Calibration/NoCalibration", False, type=bool)

    # Check if calibration was performed from scratch
    if not kits_ok and not no_calibration:
        # Calibration was done from scratch → execute save
        save_kit_dialog(self)
    else:
        # Calibration was not done from scratch → show warning
        show_calibration_warning(self)

def delete_kit_dialog(self):
    from PySide6.QtWidgets import (
        QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
        QLabel, QPushButton, QWidget, QScrollArea, QMessageBox
    )
    from PySide6.QtCore import Qt, QSettings
    import os
    import shutil
    import logging

    # --- Create dialog ---
    dialog = QDialog(self)
    dialog.setWindowTitle(f"{self.cal_kit_window_title_delete}")
    dialog.setMinimumWidth(400)

    layout = QVBoxLayout(dialog)

    # --- Base directory and ini path ---

    # Load configuration for calibration settings
    settings = get_settings(
        "INI/dut_measurement/calibration_config/calibration_config.ini",
        "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
        Path(__file__).resolve()
    )

    # --- List widget for kits ---
    list_widget = QListWidget()
    layout.addWidget(QLabel(f"{self.cal_kit_window_delete_text}"))
    layout.addWidget(list_widget)

    # --- Populate list ---
    groups = settings.childGroups()
    for g in groups:
        if g.startswith("Kit_"):
            name = settings.value(f"{g}/kit_name", "").strip()
            if name:
                item = QListWidgetItem(name)
                item.setData(Qt.UserRole, g)
                list_widget.addItem(item)

    # --- Selected tags area ---
    selected_names = set()
    selected_area = QHBoxLayout()
    selected_container = QWidget()
    selected_container.setLayout(selected_area)
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(selected_container)
    layout.addWidget(scroll)

    # --- Buttons ---
    btn_layout = QHBoxLayout()
    btn_cancel = QPushButton(f"{self.cal_kit_window_cancel}")
    btn_delete = QPushButton(f"{self.cal_kit_window_delete}")
    btn_layout.addWidget(btn_cancel)
    btn_layout.addWidget(btn_delete)
    layout.addLayout(btn_layout)

    from PySide6.QtGui import QIcon
    from PySide6 import QtCore

    # --- Add selected kit to tag area ---
    def add_selected(item):
        name = item.text()
        if name in selected_names:
            return
        selected_names.add(name)

        tag_widget = QWidget()
        tag_layout = QHBoxLayout(tag_widget)
        tag_layout.setContentsMargins(5, 2, 5, 2)
        label = QLabel(name)
        
        from PySide6.QtGui import QIcon

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        icon_path = os.path.join(project_root, "NanoVNA_UTN_Toolkit", "assets", "icons", "delete.svg")

        remove_btn = QPushButton()
        remove_btn.setIcon(QIcon(icon_path))
        remove_btn.setIconSize(QtCore.QSize(20, 20))
        remove_btn.setFixedSize(30, 30)
        remove_btn.setFlat(True)

        # Quitar fondo y borde, hacer hover más rojo
        remove_btn.setStyleSheet("""
            QPushButton {
                border: none;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: rgba(255, 0, 0, 50);  /* efecto hover rojo suave */
            }
        """)

        tag_layout.addWidget(label)
        tag_layout.addWidget(remove_btn)

        def remove_tag():
            tag_widget.setParent(None)
            selected_names.remove(name)

        remove_btn.clicked.connect(remove_tag)
        selected_area.addWidget(tag_widget)

    # --- Delete selected kits ---
    def delete_selected():
        if not selected_names:
            QMessageBox.warning(dialog, "No Selection", "Please select at least one kit to delete.")
            return

        confirm = QMessageBox.question(
            dialog,
            "Confirm Delete",
            f"Are you sure you want to delete these kits?\n\n" + "\n".join(selected_names),
            QMessageBox.Yes | QMessageBox.No
        )
        if confirm != QMessageBox.Yes:
            return
        
        # Load configuration for calibration settings
        settings = get_settings(
            "INI/dut_measurement/calibration_config/calibration_config.ini",
            "modules/dut_measurement/calibration/calibration_config/calibration_config.ini",
            Path(__file__).resolve()
        )

        # --- Read current calibration name ---
        current_full_name = settings.value("Calibration/Name", "")
        current_name_base = "_".join(current_full_name.split("_")[:-1]) if current_full_name else ""

        deleted_current_kit = False

        # --- Delete physical folders and mark if current kit is deleted ---
        kits_to_delete = []
        for g in settings.childGroups():
            if g.startswith("Kit_"):
                kit_name_ini = settings.value(f"{g}/kit_name", "").strip()
                if kit_name_ini in selected_names:
                    if kit_name_ini == current_name_base:
                        deleted_current_kit = True  # MARKER: current kit will be deleted

                    kit_path = get_calibration_path(
                        f"modules/dut_measurement/calibration/kits/{kit_name_ini}",
                        f"modules/dut_measurement/calibration/kits/{kit_name_ini}",
                        Path(__file__).resolve()
                    )

                    if os.path.exists(kit_path) and os.path.isdir(kit_path):
                        shutil.rmtree(kit_path)
                        logging.info(f"Deleted folder: {kit_path}")
                    else:
                        logging.warning(f"Folder not found: {kit_path}")
                    kits_to_delete.append(g)

        # --- Remove from ini ---
        for g in kits_to_delete:
            settings.remove(g)

        settings.sync()

        # --- Reorder remaining kits (same as before) ---
        remaining_kits = []
        for g in settings.childGroups():
            if g.startswith("Kit_"):
                kit_name = settings.value(f"{g}/kit_name", "").strip()
                method = settings.value(f"{g}/method", "")
                kit_id = int(settings.value(f"{g}/id", 0))
                date_time_Kits = settings.value(f"{g}/DateTime_Kits", "")
                remaining_kits.append((kit_id, g, kit_name, method))

        remaining_kits.sort(key=lambda x: x[0])

        # --- Clear old groups ---
        for _, g, _, _ in remaining_kits:
            settings.remove(g)

        # --- Save remaining kits with consecutive IDs ---
        for new_id, (_, _, kit_name, method) in enumerate(remaining_kits, start=1):
            group_name = f"Kit_{new_id}"
            settings.beginGroup(group_name)
            settings.setValue("kit_name", kit_name)
            settings.setValue("method", method)
            settings.setValue("id", new_id)
            settings.setValue("DateTime_Kits", date_time_Kits)
            settings.endGroup()

        kits_ok = settings.value("Calibration/Kits", False, type=bool)
        no_calibration = settings.value("Calibration/NoCalibration", False, type=bool)
        calibration_wizard = settings.value("Calibration/CalibrationWizard", False, type=bool)

        settings.sync()

        was_current_deleted = False

        # --- Update [Calibration] Name and id ---
        if remaining_kits:
            first_kit_name = remaining_kits[0][2]  # kit_name of first kit
            settings.beginGroup("Calibration")
            settings.setValue("Name", f"{first_kit_name}_1")
            settings.setValue("id", 1)
            settings.setValue("Kits", True)
            settings.setValue("NoCalibration", False)
            settings.endGroup()

            was_current_deleted = deleted_current_kit

        elif not no_calibration and calibration_wizard:
            # If no kits remain, fallback to a safe state

            print(f"CalibrationWizard1: {calibration_wizard}")

            settings.beginGroup("Calibration")
            settings.setValue("Kits", False)
            settings.setValue("NoCalibration", False)
            settings.setValue("CalibrationWizard", True)
            settings.remove("Name")
            settings.remove("id")
            settings.endGroup()
            settings.sync()

            was_current_deleted = "all"

        elif not no_calibration and not calibration_wizard:
            # No kits left, remove Name/id and reset flags
            settings.beginGroup("Calibration")
            settings.remove("Name")
            settings.remove("id")
            settings.setValue("Kits", False)
            settings.setValue("NoCalibration", True)
            settings.endGroup()

            was_current_deleted = "all"

        settings.sync()
        QMessageBox.information(dialog, "Deleted", "Selected kits have been deleted and IDs updated.")
        dialog.accept()

        # --- Now handle navigation AFTER user confirms ---
        if was_current_deleted == True:
            handle_deleted_current_kit(self)
        elif was_current_deleted == "all":
            handle_all_kits_deleted(self)

    # --- Connect signals ---
    list_widget.itemClicked.connect(add_selected)
    btn_cancel.clicked.connect(dialog.reject)
    btn_delete.clicked.connect(delete_selected)

    dialog.exec()