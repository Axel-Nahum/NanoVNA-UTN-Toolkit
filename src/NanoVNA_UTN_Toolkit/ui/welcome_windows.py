"""
Welcome setup window for NanoVNA devices.
"""
import os
import sys
import logging
from datetime import datetime

from pathlib import Path

# Suppress verbose matplotlib logging
logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.getLogger('matplotlib.pyplot').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)

from PySide6.QtCore import Qt, QSettings
from PySide6.QtWidgets import (
    QLabel, QMainWindow, QVBoxLayout, QWidget, QPushButton,
    QHBoxLayout, QGroupBox, QComboBox
)
from PySide6.QtGui import QIcon, QColor

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_window import NanoVNAGraphics
except ImportError as e:
    logging.error("Failed to import NanoVNAGraphics: %s", e)
    NanoVNAGraphics = None

try:
    from NanoVNA_UTN_Toolkit.ui.wizard_windows import CalibrationWizard
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# Import calibration data storage
try:
    from NanoVNA_UTN_Toolkit.calibration.calibration_manager import OSMCalibrationManager, THRUCalibrationManager
except ImportError as e:
    logging.error("Failed to import OSMCalibrationManager: %s", e)
    logging.error("Failed to import THRUCalibrationManager: %s", e)
    OSMCalibrationManager = None
    THRUCalibrationManager = None

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.dark_light_mode.light_dark_mode import dark_light_config
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# ----------------------------------------------------------------------------------------------------------------- #

class NanoVNAWelcome(QMainWindow):
    def __init__(self, s11=None, freqs=None, vna_device=None):
        super().__init__()

#------------------------------------------------------------------------------------------------------------------------------------------

        # Dark-Light mode settings

        dark_light_config(self)

#------------------------------------------------------------------------------------------------------------------------------------------

        # === Store VNA device reference ===
        self.vna_device = vna_device
        logging.info("[welcome_windows.__init__] Initializing welcome window")

        # Try to set application icon
        if getattr(sys, 'frozen', False):
            # ---- MODO EXE ----
            base_path = sys._MEIPASS
            icon_path = os.path.join(base_path, 'icon.ico')

            if os.path.exists(icon_path):
                self.setWindowIcon(QIcon(icon_path))
            else:
                logging.getLogger(__name__).warning(f"icon.ico not found in exe: {icon_path}")

        else:
            # ---- MODO PYTHON NORMAL ----
            base_path = os.path.dirname(__file__)

            icon_paths = [
                os.path.join(base_path, '..', '..', '..', 'icon.ico'),
                'icon.ico'
            ]

            for path in icon_paths:
                if os.path.exists(path):
                    self.setWindowIcon(QIcon(path))
                    break
            else:
                logging.getLogger(__name__).warning("icon.ico not found in dev mode")

        if OSMCalibrationManager:
            self.osm_calibration = OSMCalibrationManager()
            if vna_device and hasattr(vna_device, 'name'):
                self.osm_calibration.device_name = vna_device.name
            logging.info("[CalibrationWizard] OSM calibration manager initialized")
        else:
            self.osm_calibration = None
            logging.warning("[CalibrationWizard] OSMCalibrationManager not available")
        
        if THRUCalibrationManager:
            self.thru_calibration = THRUCalibrationManager()
            if vna_device and hasattr(vna_device, 'name'):
                self.thru_calibration.device_name = vna_device.name
            logging.info("[CalibrationWizard] THRU calibration manager initialized")
        else:
            self.thru_calibration = None
            logging.warning("[CalibrationWizard] THRUCalibrationManager not available")

        self.setWindowTitle("NanoVNA UTN Toolkit - Welcome Window")
        self.setGeometry(100, 100, 1000, 480)

        # === Central widget and main layout ===
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # === Create main content area ===
        self._create_calibration_group(main_layout)
        self._create_measurements_group(main_layout)
        
        main_layout.addStretch()

    def _create_calibration_group(self, parent_layout):
        """
        Create the calibration wizard group box with description.
        Provides information about VNA calibration importance and wizard access.
        """
        logging.info("[welcome_windows._create_calibration_group] Creating calibration group")

        # Load configuration for UI colors and styles
        settings = get_settings(
            "INI/dark_light_mode/dark_light_config.ini",
            "ui/utils/settings/dark_light_mode/dark_light_config.ini", 
            Path(__file__).resolve()
        ) 

        groupbox_border = settings.value("Dark_Light/QGroupBox/color", "1px solid #b0b0b0")
        groupbox_style = f"QGroupBox {{ border: {groupbox_border}; border-radius: 5px; margin-top: 1.3ex; padding-top: 6px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; font-size: 30pt;}}"
        
        calibration_group = QGroupBox("Calibration Wizard")
        calibration_group.setStyleSheet(groupbox_style)
        calibration_layout = QVBoxLayout(calibration_group)
        calibration_layout.setSpacing(15)

        # Calibration description
        description_text = (
            "Calibration is essential for accurate VNA measurements. It removes systematic errors "
            "from cables, connectors, and the VNA itself by measuring known reference standards. "
            "The Calibration Wizard guides you through this process step-by-step, ensuring your "
            "measurements are precise and reliable."
        )
        
        description_label = QLabel(description_text)
        description_label.setWordWrap(True)
        description_label.setStyleSheet("font-weight: normal; font-size: 14px; color: #cccccc; padding: 10px;")
        calibration_layout.addWidget(description_label)

        # Calibration wizard button
        self.calibration_wizard_button = QPushButton("Open Calibration Wizard")
        self.calibration_wizard_button.clicked.connect(self.open_calibration_wizard)
        self.calibration_wizard_button.setFixedHeight(50)
        self.calibration_wizard_button.setStyleSheet("font-size: 16px; margin: 10px;")
        calibration_layout.addWidget(self.calibration_wizard_button, alignment=Qt.AlignCenter)

        parent_layout.addWidget(calibration_group)
        logging.info("[welcome_windows._create_calibration_group] Calibration group created successfully")

    def _create_measurements_group(self, parent_layout):
        """
        Create the measurements group box with calibration kit selector and navigation buttons.
        Contains kit selection, graphics navigation, and calibration import functionality.
        """
        logging.info("[welcome_windows._create_measurements_group] Creating measurements group")

        # Load configuration for UI colors and styles
        settings = get_settings(
            "INI/dark_light_mode/dark_light_config.ini",
            "ui/utils/settings/dark_light_mode/dark_light_config.ini", 
            Path(__file__).resolve()
        ) 

        groupbox_border = settings.value("Dark_Light/QGroupBox/color", "1px solid #b0b0b0")
        groupbox_style = f"QGroupBox {{ border: {groupbox_border}; border-radius: 5px; margin-top: 1.3ex; padding-top: 6px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 3px 0 3px; }}"
        
        measurements_group = QGroupBox("Calibration")
        measurements_group.setStyleSheet(groupbox_style)
        measurements_layout = QVBoxLayout(measurements_group)
        measurements_layout.setSpacing(15)

        # Create calibration kit selector
        self._create_calibration_kit_selector(measurements_layout)
        
        # Create action buttons
        self._create_action_buttons(measurements_layout)

        parent_layout.addWidget(measurements_group)
        logging.info("[welcome_windows._create_measurements_group] Measurements group created successfully")

    def _create_calibration_kit_selector(self, parent_layout):
        """
        Create the calibration kit selector dropdown with available kits.
        Displays available calibration kits in a dropdown with None as default.
        """
        logging.info("[welcome_windows._create_calibration_kit_selector] Creating kit selector dropdown")

        # Add label for calibration kit selector
        kit_selector_label = QLabel("Calibration Kit Selection:")
        kit_selector_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        parent_layout.addWidget(kit_selector_label)

        # Load calibration kits first
        self._load_calibration_kits()

        # Create dropdown for kit selection
        self.kit_dropdown = QComboBox()
        self.kit_dropdown.setFixedHeight(40)
        self.kit_dropdown.setMinimumWidth(400)  # Set minimum width for better appearance
        self.kit_dropdown.setStyleSheet("""
            QComboBox {
                background-color: #3b3b3b;
                color: white;
                border: 2px solid white;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                min-width: 400px;
            }
            QComboBox:hover {
                background-color: #4d4d4d;
            }
            QComboBox::drop-down {
                width: 0px;
                border: none;
                background: transparent;
            }
            QComboBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
            }
            QComboBox QAbstractItemView {
                background-color: #3b3b3b;
                color: white;
                selection-background-color: #4d4d4d;
                selection-color: white;
                border: 1px solid white;
            }
        """)

        # Add None as default option
        self.kit_dropdown.addItem("None")
        
        # Add available calibration kits
        for kit_name in self.kit_names:
            self.kit_dropdown.addItem(kit_name)

        # Set current selection based on existing calibration
        self._set_current_kit_selection()

        # Connect selection change handler
        self.kit_dropdown.currentTextChanged.connect(self._on_kit_selection_changed)

        # Add dropdown to parent layout
        parent_layout.addWidget(self.kit_dropdown, alignment=Qt.AlignmentFlag.AlignLeft)

        # Display current selection info
        self.kit_info_label = QLabel("")
        self.kit_info_label.setStyleSheet("font-size: 12px; color: #cccccc; margin-top: 10px; margin-left: 0px; padding: 5px;")
        self.kit_info_label.setWordWrap(True)
        self.kit_info_label.setMinimumWidth(400)  # Ensure minimum width for better text display
        parent_layout.addWidget(self.kit_info_label, alignment=Qt.AlignmentFlag.AlignLeft)

        # Initialize selected_kit_name based on current dropdown selection
        current_text = self.kit_dropdown.currentText()
        if current_text.startswith("None"):
            self.selected_kit_name = None
        else:
            self.selected_kit_name = current_text

        self._update_kit_info_display()
        
        logging.info(f"[welcome_windows._create_calibration_kit_selector] Kit dropdown created with {len(self.kit_names)} kits available")

    def _set_current_kit_selection(self):
        """
        Set the current kit selection in the dropdown based on saved calibration.
        Updates dropdown to show currently active calibration kit.
        """
        calibration_name = self._get_current_calibration_name()
        
        if "_" in str(calibration_name):
            calibration_name_split = str(calibration_name).rsplit("_", 1)[0]
        else:
            calibration_name_split = str(calibration_name)

        # Find matching kit in dropdown
        if calibration_name_split in self.kit_names:
            kit_index = self.kit_names.index(calibration_name_split) + 1  # +1 because "None" is at index 0
            self.kit_dropdown.setCurrentIndex(kit_index)
            logging.info(f"[welcome_windows._set_current_kit_selection] Set dropdown to kit: {calibration_name_split}")
        else:
            # Set to "None" if no matching kit found
            self.kit_dropdown.setCurrentIndex(0)
            logging.info("[welcome_windows._set_current_kit_selection] Set dropdown to None - no matching kit found")

    def _on_kit_selection_changed(self, selected_text):
        """
        Handle calibration kit selection change from dropdown.
        Updates display and saves selection for graphics window navigation.
        """
        logging.info(f"[welcome_windows._on_kit_selection_changed] Kit selection changed to: {selected_text}")
        
        if selected_text.startswith("None"):
            self.selected_kit_name = None
            logging.info("[welcome_windows._on_kit_selection_changed] No kit selected")
        else:
            self.selected_kit_name = selected_text
            logging.info(f"[welcome_windows._on_kit_selection_changed] Selected kit: {selected_text}")
        
        self._update_kit_info_display()

    def _update_kit_info_display(self):
        """
        Update the information display below the kit selector.
        Shows details about the currently selected calibration kit.
        """
        if hasattr(self, 'selected_kit_name') and self.selected_kit_name:
            # Find kit details
            if self.selected_kit_name in self.kit_names:
                kit_index = self.kit_names.index(self.selected_kit_name)
                kit_id = self.kit_ids[kit_index] if kit_index < len(self.kit_ids) else "Unknown"
                
                # Load configuration for UI colors and styles
                if getattr(sys, 'frozen', False):
                    appdata = os.getenv("APPDATA")
                    config_path = os.path.join(
                        appdata,
                        "NanoVNA-UTN-Toolkit",
                        "INI",
                        "calibration_config",
                        "calibration_config.ini"
                    )
                    calibration_path = os.path.normpath(config_path)
                else:
                    ui_dir = os.path.dirname(os.path.dirname(__file__))
                    calibration_path = os.path.join(ui_dir, "calibration", "config", "calibration_config.ini")

                settings = QSettings(calibration_path, QSettings.IniFormat)
                
                kit_method = settings.value(f"Kit_{kit_id}/method", "Unknown")
                kit_datetime = settings.value(f"Kit_{kit_id}/DateTime_Kits", "Unknown")
                
                info_text = f"Selected Kit: {self.selected_kit_name}\nMethod: {kit_method}\nCreated: {kit_datetime}"
                self.kit_info_label.setText(info_text)
                logging.info(f"[welcome_windows._update_kit_info_display] Updated info for kit: {self.selected_kit_name}")
            else:
                self.kit_info_label.setText(f"Selected Kit: {self.selected_kit_name}\n(Kit details not found)")
        else:
            self.kit_info_label.setText("No calibration kit selected")
            logging.info("[welcome_windows._update_kit_info_display] Cleared kit info - no selection")

    def _create_action_buttons(self, parent_layout):
        """
        Create action buttons for graphics navigation and calibration import.
        Provides access to measurement graphics and external calibration import.
        """
        logging.info("[welcome_windows._create_action_buttons] Creating action buttons")

        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)

        # Graphics button
        self.graphics_button = QPushButton("Open Graphics Window")
        self.graphics_button.clicked.connect(self.graphics_clicked)
        self.graphics_button.setFixedHeight(50)
        self.graphics_button.setStyleSheet("font-size: 16px; margin: 10px;")
        button_layout.addWidget(self.graphics_button)

        # Import calibration button
        self.import_button = QPushButton("Import Calibration")
        self.import_button.clicked.connect(self.import_calibration)
        self.import_button.setFixedHeight(50)
        self.import_button.setStyleSheet("font-size: 16px; margin: 10px;")
        button_layout.addWidget(self.import_button)

        parent_layout.addLayout(button_layout)
        logging.info("[welcome_windows._create_action_buttons] Action buttons created successfully")

    def _load_calibration_kits(self):
        """
        Load available calibration kits from configuration.
        Reads kit information from calibration config file.
        """
        logging.info("[welcome_windows._load_calibration_kits] Loading calibration kits")
        
        # Load configuration for UI colors and styles
        if getattr(sys, 'frozen', False):
            appdata = os.getenv("APPDATA")  
            base = os.path.join(appdata, "NanoVNA-UTN-Toolkit")

            calibration_path = os.path.join(
                base, "INI", "calibration_config", "calibration_config.ini"
            )
        else:
            ui_dir = os.path.dirname(os.path.dirname(__file__))
            calibration_path = os.path.join(ui_dir, "calibration", "config", "calibration_config.ini")

        settings_calibration = QSettings(calibration_path, QSettings.IniFormat)
        
        kit_groups = [g for g in settings_calibration.childGroups() if g.startswith("Kit_")]

        # --- Get kit names and IDs ---
        self.kit_names = [settings_calibration.value(f"{g}/kit_name", "") for g in kit_groups]
        self.kit_ids = [int(settings_calibration.value(f"{g}/id", 0)) for g in kit_groups]
        
        logging.info(f"[welcome_windows._load_calibration_kits] Loaded {len(self.kit_names)} calibration kits")

    def _get_current_calibration_name(self):
        """
        Get the currently selected calibration name from settings.
        Returns the active calibration name or default value.
        """
        # Load configuration for UI colors and styles
        if getattr(sys, 'frozen', False):
            appdata = os.getenv("APPDATA")  
            base = os.path.join(appdata, "NanoVNA-UTN-Toolkit")

            calibration_path = os.path.join(
                base, "INI", "calibration_config", "calibration_config.ini"
            )
        else:
            ui_dir = os.path.dirname(os.path.dirname(__file__))
            calibration_path = os.path.join(ui_dir, "calibration", "config", "calibration_config.ini")

        settings_calibration = QSettings(calibration_path, QSettings.IniFormat)
        
        # --- Get current calibration ---
        calibration_name = settings_calibration.value("Calibration/Name", "No Calibration")
        logging.info(f"[welcome_windows._get_current_calibration_name] Current calibration: {calibration_name}")

        if "_" in calibration_name:
            calibration_name_split = calibration_name.rsplit("_", 1)[0]
        else:
            calibration_name_split = calibration_name

        matched_id = 0
        self.current_index = -1  

        if calibration_name_split in self.kit_names:
            self.current_index = self.kit_names.index(calibration_name_split)
            matched_id = self.kit_ids[self.current_index]
            logging.info(f"[welcome_windows._get_current_calibration_name] Found matching kit at index {self.current_index}")
        else:
            logging.warning(f"[welcome_windows._get_current_calibration_name] No matching kit found for {calibration_name_split}")

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
        if not found["open"]:
            missing.append("open")
        if not found["short"]:
            missing.append("short")
        if not has_load_or_match:
            missing.append("load or match")
        if not found["thru"]:
            missing.append("thru")

        if missing:
            QMessageBox.warning(self, "Missing Files", f"The following calibration files are missing: {', '.join(missing)}")
            return

        if len(files) != 4:
            QMessageBox.warning(self, "Invalid Selection", "You must select exactly 4 calibration files.")
            return

        QMessageBox.information(self, "Success", "All calibration files selected successfully!")
        print("Selected calibration files:")
        for f in files:
            print(f)

        # "Select Method"
        dialog = QDialog(self)
        dialog.setWindowTitle("NanoVNA UTN Toolkit - Select Calibration Method")

        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)  

        label = QLabel("Select Method", dialog)
        main_layout.addWidget(label)

        self.select_method = QComboBox()
        self.select_method.setEditable(False)

        # Placeholder
        self.select_method.addItem("Select Method")
        item = self.select_method.model().item(0)
        item.setEnabled(False)
        placeholder_color = QColor(120, 120, 120)
        item.setForeground(placeholder_color)

        methods = [
            "OSM (Open - Short - Match)",
            "Normalization",
            "1-Port+N",
            "Enhanced-Response"
        ]
        self.select_method.addItems(methods)

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
        """Shows a dialog to save the calibration without advancing to graphics window"""
        if not self.osm_calibration:
            return

        if not self.thru_calibration:
            return

        # Check which measurements are available
        osm_status = self.osm_calibration.is_complete_true()
        thru_status = self.thru_calibration.is_complete_true()
             
        # Dialog to enter calibration name
        from PySide6.QtWidgets import QInputDialog

        if selected_method == "OSM (Open - Short - Match)":
            prefix = "OSM"
        elif selected_method == "Normalization":
            prefix = "Normalization"
        elif selected_method == "1-Port+N":
            prefix = "1PortN"
        elif selected_method == "Enhanced-Response":
            prefix = "Enhanced Response"

        name, ok = QInputDialog.getText(
            self, 
            'Save Calibration', 
            f'Enter calibration name:',
            text=f'{prefix}_Calibration_{self.get_current_timestamp()}'
        )

        is_external_kit = True
        
        if ok and name:
            try:
                # Save calibration (it will save only the available measurements)
                success = self.osm_calibration.save_calibration_file(name, selected_method, is_external_kit, files)
                if success:
                    # Show success message
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.information(
                        self, 
                        "Success", 
                        f"Calibration '{name}' saved successfully!\n\nSaved measurements: \n\nFiles saved in:\n- Touchstone format\n- .cal format\n\nUse 'Finish' button to continue to graphics window."
                    )
                    
                    # Stay in wizard - do not advance to graphics window
                    logging.info(f"Calibration '{name}' saved successfully - staying in wizard")
                    
                else:
                    from PySide6.QtWidgets import QMessageBox
                    #QMessageBox.warning(self, "Error", "Failed to save calibration")

                success = self.thru_calibration.save_calibration_file(name, selected_method, is_external_kit, files, osm_instance=self.osm_calibration)
                if success:
                    # Show success message
                    from PySide6.QtWidgets import QMessageBox
                    QMessageBox.information(
                        self, 
                        "Success", 
                        f"Calibration '{name}' saved successfully!\n\nSaved measurements: \n\nFiles saved in:\n- Touchstone format\n- .cal format\n\nUse 'Finish' button to continue to graphics window."
                    )
                    
                    # Stay in wizard - do not advance to graphics window
                    logging.info(f"Calibration '{name}' saved successfully - staying in wizard")
                    
                else:
                    from PySide6.QtWidgets import QMessageBox
                    #QMessageBox.warning(self, "Error", "Failed to save calibration")

                # --- Read current calibration method ---
                # Use new calibration structure
                # Load configuration for UI colors and styles
                if getattr(sys, 'frozen', False):
                    appdata = os.getenv("APPDATA")
                    config_path = os.path.join(
                        appdata,
                        "NanoVNA-UTN-Toolkit",
                        "INI",
                        "calibration_config",
                        "calibration_config.ini"
                    )
                    calibration_path = os.path.normpath(config_path)
                else:
                    ui_dir = os.path.dirname(os.path.dirname(__file__))
                    calibration_path = os.path.join(ui_dir, "calibration", "config", "calibration_config.ini")

                settings_calibration = QSettings(calibration_path, QSettings.IniFormat)

                """     # --- If a kit was previously saved in this session, show its name ---
                if getattr(self, 'last_saved_kit_id', None):
                    last_id = self.last_saved_kit_id
                    last_name = settings_calibration.value(f"Kit_{last_id}/kit_name", "")
                    if last_name:
                        name_input.setText(last_name)

                if name is None:
                    name = name_input.text().strip()
                if not name:
                    name_input.setPlaceholderText("Please enter a valid name...")
                    return
                """
                # --- Check if name already exists in any Kit ---
                existing_groups = settings_calibration.childGroups()
                for g in existing_groups:
                    if g.startswith("Kit_"):
                        existing_name = settings_calibration.value(f"{g}/kit_name", "")
                        if existing_name == name:
                            # Show warning message box if name exists
                            QMessageBox.warning(dialog, "Duplicate Name",
                                                f"The kit name '{name}' already exists.\nPlease choose another name.",
                                                QMessageBox.Ok)
                            return

                # --- Determine ID: use last saved if exists ---
                if getattr(self, 'last_saved_kit_id', None):
                    next_id = self.last_saved_kit_id
                else:
                    # First save -> calculate next available ID
                    kit_ids = [int(g.split("_")[1]) for g in existing_groups if g.startswith("Kit_") and g.split("_")[1].isdigit()]
                    next_id = max(kit_ids, default=0) + 1
                    self.last_saved_kit_id = next_id  # store ID for overwriting next time

                calibration_entry_name = f"Kit_{next_id}"
                full_calibration_name = f"{name}_{next_id}"

                current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # --- Save data ---
                settings_calibration.beginGroup(calibration_entry_name)
                settings_calibration.setValue("kit_name", name)
                settings_calibration.setValue("method", selected_method)
                settings_calibration.setValue("id", next_id)
                settings_calibration.setValue("DateTime_Kits", current_datetime)
                settings_calibration.endGroup()

                # --- Update active calibration reference ---
                settings_calibration.beginGroup("Calibration")
                settings_calibration.setValue("Name", full_calibration_name)
                settings_calibration.endGroup()
                settings_calibration.sync()

                settings_calibration.setValue("Calibration/Kits", True)
                settings_calibration.setValue("Calibration/NoCalibration", False)
                settings_calibration.setValue("Calibration/CalibrationWizard", False)

                # Use new calibration structure
          
                if selected_method == "OSM (Open - Short - Match)":
                    parameter = "S11"
                elif selected_method == "Normalization":
                    parameter = "S21"
                else:
                    parameter = "S11, S21"

                settings_calibration.setValue("Calibration/Parameter", parameter)
                settings_calibration.sync()

                logging.info(f"[welcome_windows.open_save_calibration] Saved calibration {full_calibration_name}")

            except Exception as e:
                logging.error(f"[CalibrationWelcome] Error saving calibration: {e}")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"Error saving calibration: {str(e)}")

    def get_current_timestamp(self):
        """Generate timestamp for filenames"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def open_calibration_wizard(self):

        # Load configuration for UI colors and styles
        if getattr(sys, 'frozen', False):
            appdata = os.getenv("APPDATA")  
            base = os.path.join(appdata, "NanoVNA-UTN-Toolkit")

            calibration_path = os.path.join(
                base, "INI", "calibration_config", "calibration_config.ini"
            )
        else:
            ui_dir = os.path.dirname(os.path.dirname(__file__))
            calibration_path = os.path.join(ui_dir, "calibration", "config", "calibration_config.ini")

        settings_calibration = QSettings(calibration_path, QSettings.IniFormat)

        settings_calibration.setValue("Calibration/Kits", False)
        settings_calibration.setValue("Calibration/NoCalibration", False)
        settings_calibration.setValue("Calibration/CalibrationWizard", True)
        settings_calibration.sync()

        logging.info("[welcome_windows.open_calibration_wizard] Opening calibration wizard")
        if self.vna_device:
            self.welcome_windows = CalibrationWizard(self.vna_device, caller="welcome")
        else:
            self.welcome_windows = CalibrationWizard()
        self.welcome_windows.show()
        self.close()

    def graphics_clicked(self):
        """
        Navigate to graphics window with selected calibration kit.
        Applies the selected calibration kit before opening graphics.
        """
        logging.info("[welcome_windows.graphics_clicked] Opening graphics window")

        # Load configuration for UI colors and styles
        if getattr(sys, 'frozen', False):
            appdata = os.getenv("APPDATA")  
            base = os.path.join(appdata, "NanoVNA-UTN-Toolkit")

            calibration_path = os.path.join(
                base, "INI", "calibration_config", "calibration_config.ini"
            )
        else:
            ui_dir = os.path.dirname(os.path.dirname(__file__))
            calibration_path = os.path.join(ui_dir, "calibration", "config", "calibration_config.ini")

        settings_calibration = QSettings(calibration_path, QSettings.IniFormat)

        # Get currently selected kit from dropdown
        current_selection = self.kit_dropdown.currentText()
        logging.info(f"[welcome_windows.graphics_clicked] Current dropdown selection: {current_selection}")

        # Check if a kit is selected in the dropdown (not "None")
        if current_selection and not current_selection.startswith("None"):
            # Apply the selected calibration kit
            self._apply_selected_kit_calibration(current_selection)
            logging.info(f"[welcome_windows.graphics_clicked] Applied selected kit: {current_selection}")
        else:
            # No calibration kit selected
            settings_calibration.setValue("Calibration/Kits", False)
            settings_calibration.setValue("Calibration/NoCalibration", True)
            settings_calibration.setValue("Calibration/CalibrationWizard", False)
            settings_calibration.sync()
            logging.info("[welcome_windows.graphics_clicked] No calibration kit selected - proceeding without calibration")

        # Open graphics window
        if self.vna_device:
            graphics_window = NanoVNAGraphics(vna_device=self.vna_device)
        else:
            graphics_window = NanoVNAGraphics()
        graphics_window.show()
        self.close()

    def _apply_selected_kit_calibration(self, kit_name):
        """
        Apply the selected calibration kit settings.
        Updates configuration to use the specified kit for measurements.
        """
        logging.info(f"[welcome_windows._apply_selected_kit_calibration] Applying kit: {kit_name}")

        # Load configuration for UI colors and styles
        if getattr(sys, 'frozen', False):
            appdata = os.getenv("APPDATA")  
            base = os.path.join(appdata, "NanoVNA-UTN-Toolkit")

            calibration_path = os.path.join(
                base, "INI", "calibration_config", "calibration_config.ini"
            )
        else:
            ui_dir = os.path.dirname(os.path.dirname(__file__))
            calibration_path = os.path.join(ui_dir, "calibration", "config", "calibration_config.ini")

        settings_calibration = QSettings(calibration_path, QSettings.IniFormat)

        # --- Get all kit names, IDs, and methods ---
        kit_groups = [g for g in settings_calibration.childGroups() if g.startswith("Kit_")]
        kit_names = [settings_calibration.value(f"{g}/kit_name", "") for g in kit_groups]
        kit_ids = [int(settings_calibration.value(f"{g}/id", 0)) for g in kit_groups]
        kit_methods = [settings_calibration.value(f"{g}/method", "") for g in kit_groups]
        kit_date_times = [settings_calibration.value(f"{g}/DateTime_Kits", "") for g in kit_groups]

        # --- Find the matching kit ---
        if kit_name in kit_names:
            idx = kit_names.index(kit_name)
            matched_id = kit_ids[idx]
            matched_method = kit_methods[idx]
            matched_date_time_kit = kit_date_times[idx]

            # --- Append ID to the kit_name ---
            kit_name_with_id = f"{kit_name}_{matched_id}"

            # --- Save updated values in [Calibration] ---
            settings_calibration.setValue("Calibration/Name", kit_name_with_id)
            settings_calibration.setValue("Calibration/id", matched_id)
            settings_calibration.setValue("Calibration/Method", matched_method)
            settings_calibration.setValue("Calibration/DateTime_Kits", matched_date_time_kit)

            if matched_method == "OSM (Open - Short - Match)":
                parameter = "S11"
            elif matched_method == "Normalization":
                parameter = "S21"
            else:
                parameter = "S11, S21"

            settings_calibration.setValue("Calibration/Parameter", parameter)
            settings_calibration.setValue("Calibration/Kits", True)
            settings_calibration.setValue("Calibration/NoCalibration", False)
            settings_calibration.setValue("Calibration/CalibrationWizard", False)
            settings_calibration.sync()

            logging.info(f"[welcome_windows._apply_selected_kit_calibration] Applied calibration: {kit_name_with_id} (ID {matched_id}, Method {matched_method})")
        else:
            logging.warning(f"[welcome_windows._apply_selected_kit_calibration] No matching kit found for '{kit_name}'")

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    app = QApplication(sys.argv)
    ventana = NanoVNAWelcome()
    ventana.show()
    sys.exit(app.exec())
