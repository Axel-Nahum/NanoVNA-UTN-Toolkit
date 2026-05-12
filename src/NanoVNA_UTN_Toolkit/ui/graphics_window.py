"""
Graphic view window for NanoVNA devices with dual info panels and cursors.
"""

#-------------------- IMPORTS -------------------------------------------------------------------------#  

import os
import sys
import shutil
import re
import logging
import webbrowser
import numpy as np
import skrf as rf
from skrf import Network
from datetime import datetime

# Matplotlib imports for plotting and interactive features

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider
from matplotlib.backends.backend_pdf import PdfPages

# Configure matplotlib for better integration with PySide6 and improved aesthetics

plt.rcParams['mathtext.fontset'] = 'cm'  
plt.rcParams['text.usetex'] = False       
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['font.family'] = 'serif'    
plt.rcParams['mathtext.rm'] = 'serif'  

# Suppress matplotlib debug logs to keep console output clean, while allowing warnings and errors to be visible

logging.getLogger('matplotlib.font_manager').setLevel(logging.WARNING)
logging.getLogger('matplotlib.pyplot').setLevel(logging.WARNING)
logging.getLogger('matplotlib').setLevel(logging.WARNING)

# Suppress matplotlib debug logs

from pathlib import Path

# PySide6 imports for GUI components, with error handling to log issues without crashing the application

from PySide6.QtCore import QTimer, QThread, Qt, QSettings
from PySide6.QtWidgets import (
    QLabel, QMainWindow, QVBoxLayout, QWidget, QFileDialog,
    QPushButton, QHBoxLayout, QSizePolicy, QApplication, QGroupBox, QGridLayout,
    QMenu, QFileDialog, QMessageBox, QProgressBar, QDialog, QLineEdit, QTextEdit, QScrollArea, 
    QFileDialog, QMessageBox
)
from PySide6.QtGui import QIcon, QPixmap, QColor

# Import exporters for saving data in different formats, with error handling to log issues without crashing the application

from ..exporters.latex_exporter import LatexExporter
from ..exporters.touchstone_exporter import TouchstoneExporter
from .export import ExportDialog

# Import dark-light mode toggle function with error handling to log issues without crashing the application

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.dark_light_mode.light_dark_mode import toggle_menu_dark_mode, dark_light_config
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# Import get_settings 

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.settings_utils import get_settings
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# Import graphics utilities for creating panels and handling interactions

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.graphics_utils import create_left_panel, create_right_panel
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# Import load graph configuration

try:
    from NanoVNA_UTN_Toolkit.ui.utils.settings.load_graph_config.load_graph_config import load_graph_configuration
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from src.NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.reset.panels_utils import _clear_all_marker_fields
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.utils.calibration.calibration import handle_save_calibration
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

# Import calibration managers for handling OSM and THRU calibrations, with error handling to log issues without crashing the application

try:
    from NanoVNA_UTN_Toolkit.calibration.calibration_manager import OSMCalibrationManager, THRUCalibrationManager
except ImportError as e:
    logging.error("Failed to import OSMCalibrationManager: %s", e)
    logging.error("Failed to import THRUCalibrationManager: %s", e)
    OSMCalibrationManager = None
    THRUCalibrationManager = None

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_window_body import (
        setup_graphics_window_body
    )

except ImportError as e:
    logging.error(
        "Failed to import setup_graphics_window_body: %s",
        e
    )
    setup_graphics_window_body = None

try:
    from src.NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.graphics_refresh import run_sweep, update_reconnect_button_state
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.updates.graphics_update import update_plots_with_new_data
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.reset.sliders_reset import _reset_sliders_after_reconnect
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.utils.file_menu.file_menu import export_errors, export_latex_pdf, export_touchstone_data
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

#-------------------- ABOUT DIALOG -------------------------------------------------------------------------#

class AboutDialog(QDialog):
    """
    About dialog that displays the project README.md file in a scrollable window.
    Supports both English and Spanish versions.
    """
    
    def __init__(self, parent=None, language='en'):
        """
        Initialize the About dialog.
        
        Args:
            parent: Parent widget
            language: Language code ('en' for English, 'es' for Spanish)
        """
        super().__init__(parent)
        self.language = language
        
        if language == 'es':
            self.setWindowTitle("NanoVNA UTN Toolkit - Acerca de NanoVNA UTN Toolkit")
        else:
            self.setWindowTitle("NanoVNA UTN Toolkit - About NanoVNA UTN Toolkit")

        self.setModal(True)
        self.setMinimumSize(700, 500)
        self.resize(800, 600)
        
        self._setup_ui()
        self._load_readme()
    
    def _setup_ui(self):
        """Set up the user interface."""
        layout = QVBoxLayout(self)
        
        # Create a text widget with scroll capability
        self.text_widget = QTextEdit()
        self.text_widget.setReadOnly(True)
        
        # Configure scrolling: vertical only, no horizontal scroll
        self.text_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Enable word wrap to fit content to window width
        self.text_widget.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        
        # Apply comprehensive CSS to force ALL code elements to wrap
        css_style = """
        QTextEdit {
            font-family: system-ui, -apple-system, sans-serif;
            line-height: 1.4;
        }
        pre, code, .codehilite, .highlight {
            white-space: pre-wrap !important;
            word-wrap: break-word !important;
            overflow-wrap: break-word !important;
            word-break: break-all !important;
            max-width: 100% !important;
            font-family: 'Consolas', 'Monaco', 'Courier New', monospace !important;
            background-color: #f5f5f5 !important;
            padding: 8px !important;
            border-radius: 4px !important;
            border: 1px solid #e0e0e0 !important;
            overflow-x: hidden !important;
        }
        pre code {
            white-space: pre-wrap !important;
            word-wrap: break-word !important;
            overflow-wrap: break-word !important;
            word-break: break-all !important;
        }
        """
        self.text_widget.setStyleSheet(css_style)
        
        # Enable markdown rendering
        self.text_widget.setMarkdown("")
        
        layout.addWidget(self.text_widget)
    
    def _load_readme(self):
        """Load and display the appropriate README file based on language."""
        
        try:
            # Get the project root directory (go up from ui/graphics_window.py to project root)
            if hasattr(sys, '_MEIPASS'):
                project_root = sys._MEIPASS
            else:
                current_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
            
            if self.language == 'es':
                readme_path = os.path.join(project_root, "README_ES.md")
                fallback_text = (
                    "Archivo README_ES.md no encontrado.\n\n"
                    f"Ubicación esperada: {readme_path}\n\n"
                    "NanoVNA UTN Toolkit\n"
                    "Un toolkit integral para mediciones y análisis con NanoVNA."
                )
            else:
                readme_path = os.path.join(project_root, "README.md")
                fallback_text = (
                    "README.md file not found.\n\n"
                    f"Expected location: {readme_path}\n\n"
                    "NanoVNA UTN Toolkit\n"
                    "A comprehensive toolkit for NanoVNA measurements and analysis."
                )
            
            if os.path.exists(readme_path):
                with open(readme_path, 'r', encoding='utf-8') as f:
                    readme_content = f.read()
                
                # Process content to ensure code blocks wrap properly
                processed_content = self._process_content_for_wrapping(readme_content)
                self.text_widget.setMarkdown(processed_content)
            else:
                self.text_widget.setPlainText(fallback_text)
                
        except Exception as e:
            if self.language == 'es':
                error_text = (
                    f"Error cargando README_ES.md: {str(e)}\n\n"
                    "NanoVNA UTN Toolkit\n"
                    "Un toolkit integral para mediciones y análisis con NanoVNA."
                )
            else:
                error_text = (
                    f"Error loading README.md: {str(e)}\n\n"
                    "NanoVNA UTN Toolkit\n"
                    "A comprehensive toolkit for NanoVNA measurements and analysis."
                )
            self.text_widget.setPlainText(error_text)

    def _process_content_for_wrapping(self, content):
        """Process markdown content to ensure code blocks wrap properly."""
        import re
        
        # Find all code blocks (both ``` and indented)
        # Pattern for fenced code blocks
        fenced_pattern = r'```(\w*)\n(.*?)\n```'
        
        def replace_fenced_code(match):
            lang = match.group(1)
            code = match.group(2)
            # Break long lines in code blocks
            lines = code.split('\n')
            processed_lines = []
            for line in lines:
                if len(line) > 80:  # Break lines longer than 80 characters
                    # For command lines, try to break at logical points
                    if line.strip().startswith('python') and '--' in line:
                        # Break at command line arguments
                        parts = line.split(' --')
                        if len(parts) > 1:
                            reconstructed = parts[0]
                            for i, part in enumerate(parts[1:], 1):
                                reconstructed += ' \\\n    --' + part
                            processed_lines.append(reconstructed)
                        else:
                            processed_lines.append(line)
                    else:
                        processed_lines.append(line)
                else:
                    processed_lines.append(line)
            
            processed_code = '\n'.join(processed_lines)
            return f'```{lang}\n{processed_code}\n```'
        
        # Apply the replacement
        content = re.sub(fenced_pattern, replace_fenced_code, content, flags=re.DOTALL)
        
        return content

class NanoVNAGraphics(QMainWindow):
    def __init__(self, s11=None, s21=None, freqs=None, left_graph_type="Smith Diagram", left_s_param="S11", vna_device=None, dut=None):
        super().__init__()

        self.setWindowTitle("NanoVNA UTN Toolkit - Graphics Window")
        self.setGeometry(100, 100, 1300, 700)

        # Store VNA device reference
        self.dut = dut
        self.vna_device = vna_device

        # Log graphics window initialization

        logging.info("[graphics_window.__init__] Initializing graphics window")
        if vna_device:
            device_type = type(vna_device).__name__
            logging.info(f"[graphics_window.__init__] VNA device provided: {device_type}")
        else:
            logging.warning("[graphics_window.__init__] No VNA device provided")

#------------------------------------------------------------------------------------------------------------------------------------------

        # Dark-Light mode settings

        dark_light_config(self)

#------------------------------------------------------------------------------------------------------------------------------------------

        # Load graphics configuration data from ini file

        config = load_graph_configuration()

        self.left_graph_type  = config['graph_type_tab1']
        self.left_s_param     = config['s_param_tab1']
        self.right_graph_type = config['graph_type_tab2']
        self.right_s_param    = config['s_param_tab2']

#-------- Menu ---------------------------------------------------------------------------------------- #

        # --- Marker visibility flags ---

        self.show_graphic1_marker1 = True
        self.show_graphic2_marker1 = True

        self.show_graphic1_marker2 = False
        self.show_graphic2_marker2 = False

        # --- Menu ---

        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("File")
        edit_menu = menu_bar.addMenu("Edit")
        view_menu = menu_bar.addMenu("View")
        sweep_menu = menu_bar.addMenu("Sweep")
        calibration_menu = menu_bar.addMenu("Calibration")
        help_menu = menu_bar.addMenu("Help")

        # --- File menu actions ---

        import_touchstone_action = file_menu.addAction("Import Touchstone Data (Calibration)")
        import_touchstone_action.triggered.connect(lambda: self.import_touchstone_data_calibration())

        import_touchstone_action = file_menu.addAction("Import Touchstone Data (DUT)")
        import_touchstone_action.triggered.connect(lambda: self.import_touchstone_data_dut())

        file_menu.addSeparator()

        export_pdf_action =  file_menu.addAction("Export Latex PDF")
        export_pdf_action.triggered.connect(lambda: export_latex_pdf(self))

        export_touchstone_action = file_menu.addAction("Export Touchstone Data")
        export_touchstone_action.triggered.connect(lambda: export_touchstone_data(self))

        export_touchstone_action = file_menu.addAction("Export Errors")
        export_touchstone_action.triggered.connect(lambda: export_errors(self))

        graphics_markers = edit_menu.addAction("Graphics/Markers")
        graphics_markers.triggered.connect(lambda: self.edit_graphics_markers())

        # --- Help menu actions ---

        report_action = help_menu.addAction("Report")
        report_action.triggered.connect(lambda: self.open_report_url())

        about_en_action = help_menu.addAction("About [EN]")
        about_en_action.triggered.connect(lambda: self.show_about_dialog('en'))

        about_es_action = help_menu.addAction("About [ES]")
        about_es_action.triggered.connect(lambda: self.show_about_dialog('es'))

#-------- Lock Markers ----------------------------------------------------------------------------#

        # Load configuration for UI colors and styles

        settings = get_settings(
            "INI/colors_config/config.ini",
            "ui/graphics_windows/ini/config.ini", 
            Path(__file__).resolve()
        )

        self.markers_locked = settings.value("Markers/locked", False, type=bool)

        #self.lock_markers = edit_menu.addAction("Lock Markers ✓" if self.markers_locked else "Lock Markers")

        def toggle_markers_lock():
            self.markers_locked = not self.markers_locked
            lock_markers.setText("Lock Markers ✓" if self.markers_locked else "Lock Markers")
            settings.setValue("Markers/locked", self.markers_locked)

        #self.lock_markers.triggered.connect(toggle_markers_lock) 

#-------- Dark-light Mode --------------------------------------------------------------------------- #

        text_light_dark = settings.value("Dark_Light/text_light_dark", "text_light_dark")

        light_dark_mode = edit_menu.addAction(text_light_dark)

        self.is_dark_mode = settings.value("Dark_Light/is_dark_mode", False, type=bool)

        light_dark_mode.triggered.connect(lambda: toggle_menu_dark_mode(self, light_dark_mode))

#-------- Other options ---------------------------------------------------------------------------- #

        choose_graphics = view_menu.addAction("Graphics")
        choose_graphics.triggered.connect(self.open_view)  

        sweep_options = sweep_menu.addAction("Options")
        sweep_options.triggered.connect(lambda: self.open_sweep_options())
 
        sweep_run = sweep_menu.addAction("Run Sweep")
        sweep_run.triggered.connect(lambda: run_sweep(self))

        calibrate_option = calibration_menu.addAction("Calibration Wizard")
        calibrate_option.triggered.connect(lambda: self.open_calibration_wizard())

        calibrate_option = calibration_menu.addAction("No Calibration")
        calibrate_option.triggered.connect(lambda: self.open_no_calibration())

        calibration_menu.addSeparator()

        select_calibration = calibration_menu.addAction("Select Calibration (Kit)")
        select_calibration.triggered.connect(lambda: self.select_kit_dialog())

        sweep_load_calibration = calibration_menu.addAction("Save Calibration (Kit)")

        # Connect the action to the handler
        sweep_load_calibration.triggered.connect(lambda: handle_save_calibration(self))

        delete_calibration = calibration_menu.addAction("Delete Calibration (Kit)")
        delete_calibration.triggered.connect(lambda: self.delete_kit_dialog())

        # Try to set application icon
        if getattr(sys, 'frozen', False):       # ICONO (VER)
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

# ------- Calibration Manager ------------------------------------------------------------------------------------------------- #
        
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

# ------- VNA Connection ---------------------------------------------------------------------------------------------------- #

        # Auto-run sweep if device is available and connected
        if self.vna_device:
            device_type = type(self.vna_device).__name__
            is_connected = self.vna_device.connected()
            logging.info(f"[graphics_window.__init__] Device {device_type} connection status: {is_connected}")
            
            if not is_connected:
                logging.warning(f"[graphics_window.__init__] Device {device_type} not connected, attempting to reconnect...")
                try:
                    self.vna_device.connect()
                    is_connected = self.vna_device.connected()
                    logging.info(f"[graphics_window.__init__] Reconnection result: {is_connected}")
                except Exception as e:
                    logging.error(f"[graphics_window.__init__] Failed to reconnect device: {e}")
                    
            if is_connected:
                logging.info("[graphics_window.__init__] Device ready - scheduling auto-sweep")
                QTimer.singleShot(1000, lambda: run_sweep(self))  # Delay to allow UI to load
            else:
                logging.warning("[graphics_window.__init__] Device not available for auto-sweep")
        else:
            logging.warning("[graphics_window.__init__] No VNA device provided for auto-sweep")

# ------- WIDGETS --------------------------------------------------------------------------------------------------------- #

        setup_graphics_window_body(         # Widgets Body of graphics_window
            self,
            settings,
            config,
            left_graph_type,
            left_s_param
        )

        self.markers = [
            {"cursor": self.cursor_left, "cursor_2": self.cursor_left_2, "slider": self.slider_left, "slider_2": self.slider_left_2, "label": self.labels_left, "label_2": self.labels_left_2, "update_cursor": self.update_cursor, "update_cursor_2": self.update_cursor_2},
            {"cursor": self.cursor_right, "cursor_2": self.cursor_right_2, "slider": self.slider_right, "slider_2": self.slider_right_2, "label": self.labels_right, "label_2": self.labels_right_2, "update_cursor": self.update_right_cursor, "update_cursor_2": self.update_right_cursor_2}
        ]
        
        self.markers_button.clicked.connect(self.show_frequency_difference_dialog)
        self.markers_button.hide()
        
        # Clear all marker information fields until first sweep is completed
        _clear_all_marker_fields(self)
        
        # Initialize exporters
        self.latex_exporter = LatexExporter(parent_widget=self)
        self.touchstone_exporter = TouchstoneExporter(parent_widget=self)

# ------------------------------------------------------------------------------------------------------------------------------------------------------------ #

    def update_calibration_label_from_method(self, method=None):

        import configparser
    
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
        else:
            ui_dir = os.path.dirname(os.path.dirname(__file__))
            config_path = os.path.join(ui_dir, "calibration", "config", "calibration_config.ini")

        parser = configparser.ConfigParser()
        parser.read(config_path)  

        kits_ok = parser.getboolean("Calibration", "Kits", fallback=False)
        no_calibration = parser.getboolean("Calibration", "NoCalibration", fallback=False)
        calibration_method = method or parser.get("Calibration", "Method", fallback="---")

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
        else:
            ui_dir = os.path.dirname(os.path.dirname(__file__))
            config_path = os.path.join(ui_dir, "calibration", "config", "calibration_config.ini")

        settings_calibration = QSettings(config_path, QSettings.IniFormat)

        is_import_dut = settings_calibration.value("Calibration/isImportDut", False, type=bool)

        if no_calibration and method == None and not is_import_dut:
            text = "No Calibration"
        elif kits_ok and not no_calibration and method == None and not is_import_dut:
            selected_full_name = parser.get("Calibration", "Name", fallback="Unknown")
            selected_kit_name = "_".join(selected_full_name.split("_")[:-1])
            kit_found = False
            i = 1
            while f"Kit_{i}" in parser:
                kit_name = parser.get(f"Kit_{i}", "kit_name", fallback=None)
                method_kit = parser.get(f"Kit_{i}", "method", fallback=None)
                if kit_name == selected_kit_name:
                    text = f"Calibration Kit | Name: {kit_name} and Method: {method_kit}"
                    kit_found = True
                    break
                i += 1
            if not kit_found:
                text = f"Calibration Kit: {selected_kit_name or 'Unknown'} (method not found)"
        elif not is_import_dut:
            text = f"Calibration Wizard | Method: {calibration_method}"
        elif is_import_dut:
            text = f"DUT"

        self.calibration_label.setText(text)

    def load_latest_osm_calibration(self):
        # OSM
        try:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_dir = os.path.join(base_dir, "calibration", "config")
            
            if not os.path.exists(config_dir):
                return
            
            # Buscar archivos .cal
            cal_files = []
            for file in os.listdir(config_dir):
                if file.endswith('.cal') and 'OSM' in file:
                    file_path = os.path.join(config_dir, file)
                    cal_files.append((file_path, os.path.getmtime(file_path), file))
            
            if cal_files:
                # Ordenar por fecha de modificación (más reciente primero)
                cal_files.sort(key=lambda x: x[1], reverse=True)
                latest_file = cal_files[0]
                
                # Extraer nombre de calibración del archivo
                cal_name = os.path.splitext(latest_file[2])[0]
                
                # Actualizar la label
                self.update_calibration_label_from_method("OSM", cal_name)
                
                logging.info(f"[GraphicsWindow] Loaded latest OSM calibration: {cal_name}")
                
        except Exception as e:
            logging.error(f"[GraphicsWindow] Error loading latest calibration: {e}")

    def left_slider_moved(self, val):
        if self.markers_locked:
            if self.slider_right.val != val:
                self.slider_right.set_val(val)
                self.update_right_cursor(val)

    def right_slider_moved(self, val):
        if self.markers_locked:
            if self.slider_left.val != val:
                self.slider_left.set_val(val)
                self.update_cursor(val)

    def left_slider_moved_2(self, val):
        if self.markers_locked:
            if self.slider_right_2.val != val:
                self.slider_right_2.set_val(val)
                self.update_right_cursor_2(val)

    def right_slider_moved_2(self, val):
        if self.markers_locked:
            if self.slider_left_2.val != val:
                self.slider_left_2.set_val(val)
                self.update_cursor_2(val)

    def _force_marker_visibility_2(self, marker_color_left, marker_color_right, marker_size_left, marker_size_right):
        """Force markers to be visible by recreating them directly on axes"""
        logging.info(f"entre wey: {marker_color_left}")
        # Load configuration for UI colors and styles
        if getattr(sys, 'frozen', False):
            appdata = os.getenv("APPDATA")
            base = os.path.join(appdata, "NanoVNA-UTN-Toolkit")
            ruta_colors = os.path.join(base, "INI", "colors_config", "config.ini")
        else:
            ui_dir = os.path.dirname(os.path.dirname(__file__))
            ruta_colors = os.path.join(ui_dir, "ui", "graphics_windows", "ini", "config.ini")

        settings = QSettings(ruta_colors, QSettings.IniFormat)

        unit_mode_left = settings.value("Graphic1/db_times", "dB") 
        unit_mode_right  = settings.value("Graphic2/db_times", "dB")

        logging.info(f"[graphics_window] Left panel unit mode: {unit_mode_left}")
        logging.info(f"[graphics_window] Right panel unit mode: {unit_mode_right}")
        
        if hasattr(self, 'cursor_left_2') and hasattr(self, 'ax_left') and self.cursor_left_2 and self.ax_left:
            try:
                # Remove the old cursor first to avoid duplicates
                try:
                    if self.cursor_left_2:
                        self.cursor_left_2.remove()
                        logging.info("[graphics_window._force_marker_visibility] Removed old left cursor to prevent duplicates")
                except:
                    pass  # Ignore errors if cursor can't be removed
                
                # Get current data from the old cursor if possible, otherwise use defaults
                x_val, y_val = 0.0, 0.0
                try:
                    x_data_2 = self.cursor_left_2.get_xdata()
                    y_data_2 = self.cursor_left_2.get_ydata()

                    if hasattr(x_data_2, '__len__') and hasattr(y_data_2, '__len__') and len(x_data_2) > 0 and len(y_data_2) > 0:
                        x_val_2 = float(y_data_2[0])
                        y_val_2 = float(y_data_2[0])
                except:
                    pass  # Use defaults
                
                # Create new cursor directly on the axes
                new_cursor_2 = self.ax_left.plot(x_val_2, y_val_2, 'o', color=marker_color_left, markersize=marker_size_left, markeredgewidth=2, visible=self.show_graphic1_marker2)[0]
                self.cursor_left_2 = new_cursor_2
                logging.info(f"[graphics_window._force_marker_visibility] Created new left cursor at ({x_val_2}, {y_val_2})")

                if hasattr(self, 'slider_left_2') and self.slider_left_2:
                    self.slider_left_2.on_changed(lambda val: self.update_cursor_2(int(val), from_slider=True))
                
                # Also update in markers list if it exists
                if hasattr(self, 'markers') and self.markers:
                    for i, marker in enumerate(self.markers):
                        if marker and marker.get('cursor_2') and i == 0:  # First marker
                            marker['cursor_2'] = new_cursor_2
                                
                    # Store the original update_cursor function and replace with a wrapper
                    if hasattr(self, 'update_cursor_2') and not hasattr(self, '_original_update_cursor_2'):
                        self._original_update_cursor_2 = self.update_cursor_2
                        
                        def cursor_left_wrapper_2(index, from_slider=False):
                            # Call the original function first to update labels
                            result = self._original_update_cursor_2(index, from_slider)
                            
                            # Then update our visible cursor position 
                    
                            if hasattr(self, 'cursor_left') and self.cursor_left and hasattr(self.cursor_left, 'set_data'):
                                try:

                                    # Load configuration for UI colors and styles
                                    if getattr(sys, 'frozen', False):
                                        appdata = os.getenv("APPDATA")
                                        ruta_colors = os.path.join(
                                            appdata,
                                            "NanoVNA-UTN-Toolkit",
                                            "INI",
                                            "colors_config",
                                            "config.ini"
                                        )
                                    else:
                                        ui_dir = os.path.dirname(os.path.dirname(__file__))
                                        ruta_colors = os.path.join(ui_dir, "ui", "graphics_windows", "ini", "config.ini")

                                    settings = QSettings(ruta_colors, QSettings.IniFormat)

                                    graph_type_left = settings.value("Tab1/GraphType1", "Smith Diagram")
                                    s_param_left = settings.value("Tab1/SParameter", "S11")
                                    
                                    # Determine which S parameter data to use
                                    s_data = None
                                    if s_param_left == "S21" and hasattr(self, 's21') and self.s21 is not None:
                                        s_data = self.s21
                                    elif s_param_left == "S11" and hasattr(self, 's11') and self.s11 is not None:
                                        s_data = self.s11
                                    elif hasattr(self, 's21') and self.s21 is not None:
                                        s_data = self.s21  # Default fallback to S21
                                    elif hasattr(self, 's11') and self.s11 is not None:
                                        s_data = self.s11  # Final fallback to S11
                                    
                                    if s_data is not None and hasattr(self, 'freqs') and self.freqs is not None and index < len(s_data) and index < len(self.freqs):
                                        val_complex = s_data[index]
                                        
                                        # Use appropriate coordinates based on graph type
                                        if graph_type_left == "Smith Diagram":
                                            # Smith diagram coordinates (real/imag)
                                            real_part = float(np.real(val_complex))
                                            imag_part = float(np.imag(val_complex))
                                            self.cursor_left_2.set_data([real_part], [imag_part])
                                        elif graph_type_left == "Magnitude":
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            if unit_mode_left == "dB":
                                                mag_val = float(20 * np.log10(np.abs(val_complex)))
                                            elif unit_mode_left == "Power ratio":
                                                mag_val = float(np.abs(val_complex)**2)
                                            elif unit_mode_left == "Voltage ratio":
                                                mag_val = float(np.abs(val_complex))
                                            else:
                                                mag_val = float(np.abs(val_complex))
                                            self.cursor_left_2.set_data([freq_mhz], [mag_val])
                                        elif graph_type_left == "Phase":
                                            # Phase plot coordinates (freq in MHz, phase in degrees)
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            phase_deg = float(np.angle(val_complex) * 180 / np.pi)
                                            self.cursor_left_2.set_data([freq_mhz], [phase_deg])
                                        elif graph_type_left == "VSWR":
                                            # VSWR plot coordinates (freq in MHz, VSWR value)
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            s_magnitude = np.abs(val_complex)
                                            vswr_val = (1 + s_magnitude) / (1 - s_magnitude) if s_magnitude < 1 else 999
                                            self.cursor_left_2.set_data([freq_mhz], [float(vswr_val)])
                                        
                                        # Force redraw
                                        if hasattr(self, 'canvas_left') and self.canvas_left:
                                            self.canvas_left.draw_idle()
                                except Exception as e:
                                    print(f"Error updating cursor_left position: {e}")
                        
                            return result
                
                        self.update_cursor_2 = cursor_left_wrapper_2

                        if hasattr(self, 'slider_left_2') and self.slider_left_2:
                            try:
                                self.slider_left_2.observers.clear()
                            except:
                                pass
                            self.slider_left_2.on_changed(self.left_slider_moved_2)
                        
                        # Reconnect the slider to use our wrapper
                        if hasattr(self, 'slider_left_2') and self.slider_left_2:
                            try:
                                self.slider_left_2.observers.clear()
                            except:
                                try:
                                    self.slider_left_2.disconnect()
                                except:
                                    pass
                            self.slider_left_2.on_changed(lambda val: cursor_left_wrapper_2(int(val), from_slider=True))

            except Exception as e:
                print(f"Error forcing cursor_left to ax_left: {e}")

        if hasattr(self, 'cursor_right_2') and hasattr(self, 'ax_right') and self.cursor_right_2 and self.ax_right:
            try:
                # Remove the old cursor first to avoid duplicates
                try:
                    if self.cursor_right_2:
                        self.cursor_right_2.remove()
                        logging.info("[graphics_window._force_marker_visibility] Removed old right cursor to prevent duplicates")
                except:
                    pass  # Ignore errors if cursor can't be removed
                
                # Get current data from the old cursor if possible, otherwise use defaults
                x_val, y_val = 0.0, 0.0
                try:
                    x_data = self.cursor_right_2.get_xdata()
                    y_data = self.cursor_right_2.get_ydata()
                    if hasattr(x_data, '__len__') and hasattr(y_data, '__len__') and len(x_data) > 0 and len(y_data) > 0:
                        x_val = float(x_data[0])
                        y_val = float(y_data[0])
                except:
                    pass  # Use defaults
                
                # Create new cursor directly on the axes
                new_cursor = self.ax_right.plot(x_val, y_val, 'o', color=marker_color_right, markersize=marker_size_right, markeredgewidth=2, visible=self.show_graphic2_marker2)[0]
                self.cursor_right_2 = new_cursor
                logging.info(f"[graphics_window._force_marker_visibility] Created new right cursor at ({x_val}, {y_val})")
                
                if hasattr(self, 'slider_right_2') and self.slider_right_2:
                    self.slider_right_2.on_changed(lambda val: self.update_right_cursor_2(int(val), from_slider=True))

                # Also update in markers list if it exists
                if hasattr(self, 'markers') and self.markers:
                    for i, marker in enumerate(self.markers):
                        if marker and marker.get('cursor_2') and i == 1:  # Second marker
                            marker['cursor_2'] = new_cursor
                                
                    # Store the original update_right_cursor function and replace with a wrapper
                    if hasattr(self, 'update_right_cursor_2') and not hasattr(self, '_original_update_right_cursor_2'):
                        self._original_update_right_cursor_2 = self.update_right_cursor_2
                        
                        def cursor_right_wrapper_2(index, from_slider=False):
                            # Call the original function first to update labels
                            result = self._original_update_right_cursor_2(index, from_slider)
                            
                            # Then update our visible cursor position 
                            if hasattr(self, 'cursor_right_2') and self.cursor_right_2 and hasattr(self.cursor_right_2, 'set_data'):
                                try:
 
                                    # Load configuration for UI colors and styles
                                    if getattr(sys, 'frozen', False):
                                        appdata = os.getenv("APPDATA")
                                        ruta_colors = os.path.join(
                                            appdata,
                                            "NanoVNA-UTN-Toolkit",
                                            "INI",
                                            "colors_config",
                                            "config.ini"
                                        )
                                    else:
                                        ui_dir = os.path.dirname(os.path.dirname(__file__))
                                        ruta_colors = os.path.join(ui_dir, "ui", "graphics_windows", "ini", "config.ini")

                                    settings = QSettings(ruta_colors, QSettings.IniFormat)

                                    graph_type_right = settings.value("Tab2/GraphType2", "Magnitude")
                                    s_param_right = settings.value("Tab2/SParameter", "S11")
                                    
                                    # Determine which S parameter data to use
                                    s_data = None
                                    if s_param_right == "S21" and hasattr(self, 's21') and self.s21 is not None:
                                        s_data = self.s21
                                    elif s_param_right == "S11" and hasattr(self, 's11') and self.s11 is not None:
                                        s_data = self.s11
                                    elif hasattr(self, 's21') and self.s21 is not None:
                                        s_data = self.s21  # Default fallback to S21
                                    elif hasattr(self, 's11') and self.s11 is not None:
                                        s_data = self.s11  # Final fallback to S11
                                    
                                    if s_data is not None and hasattr(self, 'freqs') and self.freqs is not None and index < len(s_data) and index < len(self.freqs):
                                        val_complex = s_data[index]
                                        
                                        # Use appropriate coordinates based on graph type
                                        if graph_type_right == "Smith Diagram":
                                            # Smith diagram coordinates (real/imag)
                                            real_part = float(np.real(val_complex))
                                            imag_part = float(np.imag(val_complex))
                                            self.cursor_right_2.set_data([real_part], [imag_part])
                                        elif graph_type_right == "Magnitude":
                                            # Magnitude plot coordinates (freq in MHz, magnitude in dB)
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            if unit_mode_right == "dB":
                                                mag_val = float(20 * np.log10(np.abs(val_complex)))
                                            elif unit_mode_right == "Power ratio":
                                                mag_val = float(np.abs(val_complex)**2)
                                            elif unit_mode_right == "Voltage ratio":
                                                mag_val = float(np.abs(val_complex))
                                            else:
                                                mag_val = float(np.abs(val_complex))
                                            self.cursor_right_2.set_data([freq_mhz], [mag_val])
                                        elif graph_type_right == "Phase":
                                            # Phase plot coordinates (freq in MHz, phase in degrees)
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            phase_deg = float(np.angle(val_complex) * 180 / np.pi)
                                            self.cursor_right_2.set_data([freq_mhz], [phase_deg])
                                        elif graph_type_right == "VSWR":
                                            # VSWR plot coordinates (freq in MHz, VSWR value)
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            s_magnitude = np.abs(val_complex)
                                            vswr_val = (1 + s_magnitude) / (1 - s_magnitude) if s_magnitude < 1 else 999
                                            self.cursor_right_2.set_data([freq_mhz], [float(vswr_val)])
                                        
                                        # Force redraw
                                        if hasattr(self, 'canvas_right') and self.canvas_right:
                                            self.canvas_right.draw_idle()
                                except Exception as e:
                                    print(f"Error updating cursor_right position: {e}")
                            
                            return result
                        
                        self.update_right_cursor_2 = cursor_right_wrapper_2

                        if hasattr(self, 'slider_right_2') and self.slider_right_2:
                            try:
                                self.slider_right_2.observers.clear()
                            except:
                                pass
                            self.slider_right_2.on_changed(self.right_slider_moved_2)
                            self.right_slider_moved_2(int(val))
                        
                        # Reconnect the slider to use our wrapper
                        if hasattr(self, 'slider_right_2') and self.slider_right_2:
                            try:
                                self.slider_right_2.observers.clear()
                            except:
                                try:
                                    self.slider_right_2.disconnect()
                                except:
                                    pass
                            self.slider_right_2.on_changed(lambda val: cursor_right_wrapper_2(int(val), from_slider=True))
                
            except Exception as e:
                print(f"Error forcing cursor_right to ax_right: {e}")
 
    def _force_marker_visibility(self, marker_color_left, marker_color_right, marker1_size_left, marker1_size_right):
        """Force markers to be visible by recreating them directly on axes"""

        # Load configuration for UI colors and styles
        if getattr(sys, 'frozen', False):
            appdata = os.getenv("APPDATA")
            base = os.path.join(appdata, "NanoVNA-UTN-Toolkit")
            ruta_colors = os.path.join(base, "INI", "colors_config", "config.ini")
        else:
            ui_dir = os.path.dirname(os.path.dirname(__file__))
            ruta_colors = os.path.join(ui_dir, "ui", "graphics_windows", "ini", "config.ini")

        settings = QSettings(ruta_colors, QSettings.IniFormat)

        unit_mode_left = settings.value("Graphic1/db_times", "dB") 
        unit_mode_right  = settings.value("Graphic2/db_times", "dB")

        logging.info(f"[graphics_window] Left panel unit mode: {unit_mode_left}")
        logging.info(f"[graphics_window] Right panel unit mode: {unit_mode_right}")
        
        if (hasattr(self, 'cursor_left') or hasattr(self, 'cursor_left_2')) and hasattr(self, 'ax_left') and (self.cursor_left or self.cursor_left_2) and self.ax_left:
            try:
                # Remove the old cursor first to avoid duplicates
                try:
                    if self.cursor_left:
                        self.cursor_left.remove()
                        logging.info("[graphics_window._force_marker_visibility] Removed old left cursor to prevent duplicates")
                except:
                    pass  # Ignore errors if cursor can't be removed
                
                # Get current data from the old cursor if possible, otherwise use defaults
                x_val, y_val = 0.0, 0.0
                try:
                    x_data = self.cursor_left.get_xdata()
                    y_data = self.cursor_left.get_ydata()

                    if hasattr(x_data, '__len__') and hasattr(y_data, '__len__') and len(x_data) > 0 and len(y_data) > 0:
                        x_val = float(x_data[0])
                        y_val = float(y_data[0])
                except:
                    pass  # Use defaults
                
                # Create new cursor directly on the axes
                new_cursor = self.ax_left.plot(x_val, y_val, 'o', color=marker_color_left, markersize=marker1_size_left, markeredgewidth=2)[0]
                self.cursor_left = new_cursor
                logging.info(f"[graphics_window._force_marker_visibility] Created new left cursor at ({x_val}, {y_val})")

                if self.cursor_left:
                    self.cursor_left.set_visible(self.show_graphic1_marker1)
                    self.fig_left.canvas.draw_idle()

                # Also update in markers list if it exists
                if hasattr(self, 'markers') and self.markers:
                    for i, marker in enumerate(self.markers):
                        if marker and marker.get('cursor') and i == 0:  # First marker
                            marker['cursor'] = new_cursor
                                
                    # Store the original update_cursor function and replace with a wrapper
                    if hasattr(self, 'update_cursor') and not hasattr(self, '_original_update_cursor'):
                        self._original_update_cursor = self.update_cursor
                        
                        def cursor_left_wrapper(index, from_slider=False):
                            # Call the original function first to update labels
                            result = self._original_update_cursor(index, from_slider)
                            
                            # Then update our visible cursor position 
                            if hasattr(self, 'cursor_left') and self.cursor_left and hasattr(self.cursor_left, 'set_data'):
                                try:

                                    # Load configuration for UI colors and styles
                                    if getattr(sys, 'frozen', False):
                                        appdata = os.getenv("APPDATA")
                                        ruta_colors = os.path.join(
                                            appdata,
                                            "NanoVNA-UTN-Toolkit",
                                            "INI",
                                            "colors_config",
                                            "config.ini"
                                        )
                                    else:
                                        ui_dir = os.path.dirname(os.path.dirname(__file__))
                                        ruta_colors = os.path.join(ui_dir, "ui", "graphics_windows", "ini", "config.ini")

                                    settings = QSettings(ruta_colors, QSettings.IniFormat)

                                    graph_type_left = settings.value("Tab1/GraphType1", "Smith Diagram")
                                    s_param_left = settings.value("Tab1/SParameter", "S11")
                                    
                                    # Determine which S parameter data to use
                                    s_data = None
                                    if s_param_left == "S21" and hasattr(self, 's21') and self.s21 is not None:
                                        s_data = self.s21
                                    elif s_param_left == "S11" and hasattr(self, 's11') and self.s11 is not None:
                                        s_data = self.s11
                                    elif hasattr(self, 's21') and self.s21 is not None:
                                        s_data = self.s21  # Default fallback to S21
                                    elif hasattr(self, 's11') and self.s11 is not None:
                                        s_data = self.s11  # Final fallback to S11
                                    
                                    if s_data is not None and hasattr(self, 'freqs') and self.freqs is not None and index < len(s_data) and index < len(self.freqs):
                                        val_complex = s_data[index]
                                        
                                        # Use appropriate coordinates based on graph type
                                        if graph_type_left == "Smith Diagram":
                                            # Smith diagram coordinates (real/imag)
                                            real_part = float(np.real(val_complex))
                                            imag_part = float(np.imag(val_complex))
                                            self.cursor_left.set_data([real_part], [imag_part])
                                        elif graph_type_left == "Magnitude":
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            if unit_mode_left == "dB":
                                                mag_val = float(20 * np.log10(np.abs(val_complex)))
                                            elif unit_mode_left == "Power ratio":
                                                mag_val = float(np.abs(val_complex)**2)
                                            elif unit_mode_left == "Voltage ratio":
                                                mag_val = float(np.abs(val_complex))
                                            else:
                                                mag_val = float(np.abs(val_complex))
                                            self.cursor_left.set_data([freq_mhz], [mag_val])
                                        elif graph_type_left == "Phase":
                                            # Phase plot coordinates (freq in MHz, phase in degrees)
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            phase_deg = float(np.angle(val_complex) * 180 / np.pi)
                                            self.cursor_left.set_data([freq_mhz], [phase_deg])
                                        elif graph_type_left == "VSWR":
                                            # VSWR plot coordinates (freq in MHz, VSWR value)
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            s_magnitude = np.abs(val_complex)
                                            vswr_val = (1 + s_magnitude) / (1 - s_magnitude) if s_magnitude < 1 else 999
                                            self.cursor_left.set_data([freq_mhz], [float(vswr_val)])
                                        
                                        # Force redraw
                                        if hasattr(self, 'canvas_left') and self.canvas_left:
                                            self.canvas_left.draw_idle()
                                except Exception as e:
                                    print(f"Error updating cursor_left position: {e}")
                            
                            return result
                        
                        self.update_cursor = cursor_left_wrapper

                        if hasattr(self, 'slider_left') and self.slider_left:
                            try:
                                self.slider_left.observers.clear()
                            except:
                                pass
                            self.slider_left.on_changed(self.left_slider_moved)
                        
                        # Reconnect the slider to use our wrapper
                        if hasattr(self, 'slider_left') and self.slider_left:
                            try:
                                self.slider_left.observers.clear()
                            except:
                                try:
                                    self.slider_left.disconnect()
                                except:
                                    pass
                            self.slider_left.on_changed(lambda val: cursor_left_wrapper(int(val), from_slider=True))

            except Exception as e:
                print(f"Error forcing cursor_left to ax_left: {e}")
                
        if hasattr(self, 'cursor_right') and hasattr(self, 'ax_right') and self.cursor_right and self.ax_right:
            try:
                # Remove the old cursor first to avoid duplicates
                try:
                    if self.cursor_right:
                        self.cursor_right.remove()
                        logging.info("[graphics_window._force_marker_visibility] Removed old right cursor to prevent duplicates")
                except:
                    pass  # Ignore errors if cursor can't be removed
                
                # Get current data from the old cursor if possible, otherwise use defaults
                x_val, y_val = 0.0, 0.0
                try:
                    x_data = self.cursor_right.get_xdata()
                    y_data = self.cursor_right.get_ydata()
                    if hasattr(x_data, '__len__') and hasattr(y_data, '__len__') and len(x_data) > 0 and len(y_data) > 0:
                        x_val = float(x_data[0])
                        y_val = float(y_data[0])
                except:
                    pass  # Use defaults
                
                # Create new cursor directly on the axes
                new_cursor = self.ax_right.plot(x_val, y_val, 'o', color=marker_color_right, markersize=marker1_size_right, markeredgewidth=2)[0]
                self.cursor_right = new_cursor
                logging.info(f"[graphics_window._force_marker_visibility] Created new right cursor at ({x_val}, {y_val})")

                if self.cursor_right:
                    self.cursor_right.set_visible(self.show_graphic2_marker1)
                    self.fig_right.canvas.draw_idle()
                
                if hasattr(self, 'slider_right') and self.slider_right:
                    self.slider_right.on_changed(lambda val: self.update_right_cursor(int(val), from_slider=True))

                # Also update in markers list if it exists
                if hasattr(self, 'markers') and self.markers:
                    for i, marker in enumerate(self.markers):
                        if marker and marker.get('cursor') and i == 1:  # Second marker
                            marker['cursor'] = new_cursor
                                
                    # Store the original update_right_cursor function and replace with a wrapper
                    if hasattr(self, 'update_right_cursor') and not hasattr(self, '_original_update_right_cursor'):
                        self._original_update_right_cursor = self.update_right_cursor
                        
                        def cursor_right_wrapper(index, from_slider=False):
                            # Call the original function first to update labels
                            result = self._original_update_right_cursor(index, from_slider)
                            
                            # Then update our visible cursor position 
                            if hasattr(self, 'cursor_right') and self.cursor_right and hasattr(self.cursor_right, 'set_data'):
                                try:

                                    # Load configuration for UI colors and styles
                                    if getattr(sys, 'frozen', False):
                                        appdata = os.getenv("APPDATA")
                                        ruta_colors = os.path.join(
                                            appdata,
                                            "NanoVNA-UTN-Toolkit",
                                            "INI",
                                            "colors_config",
                                            "config.ini"
                                        )
                                    else:
                                        ui_dir = os.path.dirname(os.path.dirname(__file__))
                                        ruta_colors = os.path.join(ui_dir, "ui", "graphics_windows", "ini", "config.ini")

                                    settings = QSettings(ruta_colors, QSettings.IniFormat)

                                    graph_type_right = settings.value("Tab2/GraphType2", "Magnitude")
                                    s_param_right = settings.value("Tab2/SParameter", "S11")
                                    
                                    # Determine which S parameter data to use
                                    s_data = None
                                    if s_param_right == "S21" and hasattr(self, 's21') and self.s21 is not None:
                                        s_data = self.s21
                                    elif s_param_right == "S11" and hasattr(self, 's11') and self.s11 is not None:
                                        s_data = self.s11
                                    elif hasattr(self, 's21') and self.s21 is not None:
                                        s_data = self.s21  # Default fallback to S21
                                    elif hasattr(self, 's11') and self.s11 is not None:
                                        s_data = self.s11  # Final fallback to S11
                                    
                                    if s_data is not None and hasattr(self, 'freqs') and self.freqs is not None and index < len(s_data) and index < len(self.freqs):
                                        val_complex = s_data[index]
                                        
                                        # Use appropriate coordinates based on graph type
                                        if graph_type_right == "Smith Diagram":
                                            # Smith diagram coordinates (real/imag)
                                            real_part = float(np.real(val_complex))
                                            imag_part = float(np.imag(val_complex))
                                            self.cursor_right.set_data([real_part], [imag_part])
                                        elif graph_type_right == "Magnitude":
                                            # Magnitude plot coordinates (freq in MHz, magnitude in dB)
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            if unit_mode_right == "dB":
                                                mag_val = float(20 * np.log10(np.abs(val_complex)))
                                            elif unit_mode_right == "Power ratio":
                                                mag_val = float(np.abs(val_complex)**2)
                                            elif unit_mode_right == "Voltage ratio":
                                                mag_val = float(np.abs(val_complex))
                                            else:
                                                mag_val = float(np.abs(val_complex))
                                            self.cursor_right.set_data([freq_mhz], [mag_val])
                                        elif graph_type_right == "Phase":
                                            # Phase plot coordinates (freq in MHz, phase in degrees)
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            phase_deg = float(np.angle(val_complex) * 180 / np.pi)
                                            self.cursor_right.set_data([freq_mhz], [phase_deg])
                                        elif graph_type_right == "VSWR":
                                            # VSWR plot coordinates (freq in MHz, VSWR value)
                                            freq_mhz = float(self.freqs[index] / 1e6)
                                            s_magnitude = np.abs(val_complex)
                                            vswr_val = (1 + s_magnitude) / (1 - s_magnitude) if s_magnitude < 1 else 999
                                            self.cursor_right.set_data([freq_mhz], [float(vswr_val)])
                                        
                                        # Force redraw
                                        if hasattr(self, 'canvas_right') and self.canvas_right:
                                            self.canvas_right.draw_idle()
                                except Exception as e:
                                    print(f"Error updating cursor_right position: {e}")
                            
                            return result
                        
                        self.update_right_cursor = cursor_right_wrapper

                        if hasattr(self, 'slider_right') and self.slider_right:
                            try:
                                self.slider_right.observers.clear()
                            except:
                                pass
                            self.slider_right.on_changed(self.right_slider_moved)
                            #self.right_slider_moved()
                        
                        # Reconnect the slider to use our wrapper
                        if hasattr(self, 'slider_right') and self.slider_right:
                            try:
                                self.slider_right.observers.clear()
                            except:
                                try:
                                    self.slider_right.disconnect()
                                except:
                                    pass
                            self.slider_right.on_changed(lambda val: cursor_right_wrapper(int(val), from_slider=True))
                
            except Exception as e:
                print(f"Error forcing cursor_right to ax_right: {e}")

    def _clear_marker_fields_only(self):
        """Clear only marker information fields without affecting the graphs."""
        logging.info("[graphics_window._clear_marker_fields_only] Clearing marker information fields only")
        
        # --- Clear left panel marker information ---
        if hasattr(self, 'labels_left') and self.labels_left:
            freq_left = self.labels_left.get("freq")
            if freq_left:
                freq_left.setText("--")
                freq_left.setSelection(0, 0)  
                freq_left.setCursorPosition(0) 
                freq_left.deselect()
                freq_left.clearFocus()
            self.labels_left.get("val") and self.labels_left["val"].setText("S11: -- + j--")
            self.labels_left.get("mag") and self.labels_left["mag"].setText("|S11|: --")
            self.labels_left.get("phase") and self.labels_left["phase"].setText("Phase: --")
            self.labels_left.get("z") and self.labels_left["z"].setText("Zin (Z0): -- + j--")
            self.labels_left.get("il") and self.labels_left["il"].setText("IL: --")
            self.labels_left.get("vswr") and self.labels_left["vswr"].setText("VSWR: --")

        # --- Clear right panel marker information ---
        if hasattr(self, 'labels_right') and self.labels_right:
            freq_right = self.labels_right.get("freq")
            if freq_right:
                freq_right.setText("--")   # set "--"
                freq_right.setSelection(0, 0)  
                freq_right.setCursorPosition(0) 
                freq_right.deselect()
                freq_right.clearFocus()
            self.labels_right.get("val") and self.labels_right["val"].setText("S21: -- + j--")
            self.labels_right.get("mag") and self.labels_right["mag"].setText("|S21|: --")
            self.labels_right.get("phase") and self.labels_right["phase"].setText("Phase: --")
            self.labels_right.get("z") and self.labels_right["z"].setText("Zin (Z0): -- + j--")
            self.labels_right.get("il") and self.labels_right["il"].setText("IL: --")
            self.labels_right.get("vswr") and self.labels_right["vswr"].setText("VSWR: --")

        # --- Clear left panel marker information ---
        if hasattr(self, 'labels_left_2') and self.labels_left_2:
            freq_left = self.labels_left_2.get("freq")
            if freq_left:
                freq_left.setText("--")    # set "--"
                freq_left.deselect()       # remove selection
                freq_left.clearFocus()     # remove focus so it's not blue
            self.labels_left_2.get("val") and self.labels_left_2["val"].setText("S11: -- + j--")
            self.labels_left_2.get("mag") and self.labels_left_2["mag"].setText("|S11|: --")
            self.labels_left_2.get("phase") and self.labels_left_2["phase"].setText("Phase: --")
            self.labels_left_2.get("z") and self.labels_left_2["z"].setText("Zin (Z0): -- + j--")
            self.labels_left_2.get("il") and self.labels_left_2["il"].setText("IL: --")
            self.labels_left_2.get("vswr") and self.labels_left_2["vswr"].setText("VSWR: --")

        # --- Clear right panel marker information ---
        if hasattr(self, 'labels_right_2') and self.labels_right_2:
            freq_right = self.labels_right_2.get("freq")
            if freq_right:
                freq_right.setText("--")   # set "--"
                freq_right.deselect()      # remove selection
                freq_right.clearFocus()    # remove focus so it's not blue
            self.labels_right_2.get("val") and self.labels_right_2["val"].setText("S21: -- + j--")
            self.labels_right_2.get("mag") and self.labels_right_2["mag"].setText("|S21|: --")
            self.labels_right_2.get("phase") and self.labels_right_2["phase"].setText("Phase: --")
            self.labels_right_2.get("z") and self.labels_right_2["z"].setText("Zin (Z0): -- + j--")
            self.labels_right_2.get("il") and self.labels_right_2["il"].setText("IL: --")
            self.labels_right_2.get("vswr") and self.labels_right_2["vswr"].setText("VSWR: --")

        # Do NOT clear the graphs - leave them with the actual data
        logging.info("[graphics_window._clear_marker_fields_only] Marker fields cleared, graphs preserved")

    def _update_slider_ranges(self):
        """Update slider ranges and steps to match the current sweep data."""
        if not hasattr(self, 'freqs') or self.freqs is None or len(self.freqs) == 0:
            logging.warning("[graphics_window._update_slider_ranges] No frequency data available, cannot update sliders")
            return
            
        try:
            num_points = len(self.freqs)
            max_index = num_points - 1
            middle_index = max_index // 2
            
            logging.info(f"[graphics_window._update_slider_ranges] Updating sliders for {num_points} frequency points (indices 0 to {max_index})")
            logging.info(f"[graphics_window._update_slider_ranges] Frequency range: {self.freqs[0]/1e6:.3f} - {self.freqs[-1]/1e6:.3f} MHz")
            
            # Update left slider range if it exists and make it visible
            if hasattr(self, 'slider_left') and self.slider_left:
                try:
                    # Update slider range to match frequency data indices
                    self.slider_left.valmin = 0
                    self.slider_left.valmax = max_index
                    self.slider_left.valstep = 1
                    
                    # Set slider to middle position
                    self.slider_left.set_val(middle_index)
                    
                    # Make sure the slider is visible and active
                    if hasattr(self.slider_left, 'ax'):
                        self.slider_left.ax.set_visible(True)
                    if hasattr(self.slider_left, 'set_active'):
                        self.slider_left.set_active(True)
                    
                    logging.info(f"[graphics_window._update_slider_ranges] Left slider updated: range 0-{max_index}, positioned at index {middle_index} ({self.freqs[middle_index]/1e6:.3f} MHz)")
                except Exception as e:
                    logging.warning(f"[graphics_window._update_slider_ranges] Could not update left slider: {e}")
            
            # Update right slider range if it exists and make it visible
            if hasattr(self, 'slider_right') and self.slider_right:
                try:
                    # Update slider range to match frequency data indices  
                    self.slider_right.valmin = 0
                    self.slider_right.valmax = max_index
                    self.slider_right.valstep = 1
                    
                    # Set slider to middle position
                    self.slider_right.set_val(middle_index)
                    
                    # Make sure the slider is visible and active
                    if hasattr(self.slider_right, 'ax'):
                        self.slider_right.ax.set_visible(True)
                    if hasattr(self.slider_right, 'set_active'):
                        self.slider_right.set_active(True)
                    
                    logging.info(f"[graphics_window._update_slider_ranges] Right slider updated: range 0-{max_index}, positioned at index {middle_index} ({self.freqs[middle_index]/1e6:.3f} MHz)")
                except Exception as e:
                    logging.warning(f"[graphics_window._update_slider_ranges] Could not update right slider: {e}")

            # Force canvas redraw to show updated markers
            if hasattr(self, 'canvas_left') and self.canvas_left:
                self.canvas_left.draw_idle()
            if hasattr(self, 'canvas_right') and self.canvas_right:
                self.canvas_right.draw_idle()
                    
            logging.info("[graphics_window._update_slider_ranges] Slider ranges updated successfully")
            
        except Exception as e:
            logging.error(f"[graphics_window._update_slider_ranges] Error updating slider ranges: {e}")

    # =================== CONNECTION FUNCTION ==================

    def open_connection_window(self):
        from NanoVNA_UTN_Toolkit.ui.connection_window import NanoVNAStatusApp

        logging.info("[connection_windows.open_connection_window] Opening connection")
        
        self.connection_window = NanoVNAStatusApp()
        self.connection_window.show()
        self.close()
        self.deleteLater()

    # =================== CALIBRATION WIZARD FUNCTION ==================

    def open_calibration_wizard(self):
        from NanoVNA_UTN_Toolkit.ui.wizard_windows import CalibrationWizard

        logging.info("[wizard_windows.open_calibration_wizard] Opening calibration wizard")
        
        if self.vna_device:
            self.welcome_windows = CalibrationWizard(self.vna_device, caller="graphics")
        else:
            self.welcome_windows = CalibrationWizard(caller="graphics")
        self.welcome_windows.show()
        self.close()
        self.deleteLater()

    # =================== NO CALIBRATION FUNCTION ==================

    def open_no_calibration(self):
        from NanoVNA_UTN_Toolkit.ui.graphics_window import NanoVNAGraphics

        logging.info("[graphics_window.open_no_calibration] Opening no calibration")

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

    # =================== KITS OPTIONS FUNCTION ==================

    def select_kit_dialog(self): 
        from PySide6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
            QLabel, QPushButton, QWidget, QScrollArea
        )
        from PySide6.QtCore import Qt, QSettings
        from PySide6.QtGui import QIcon
        from PySide6 import QtCore
        import os

        # --- Create dialog ---
        dialog = QDialog(self)
        dialog.setWindowTitle("NanoVNA UTN Toolkit - Calibration Wizard - Select a Calibration Kit")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

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

        settings = QSettings(calibration_path, QSettings.IniFormat)

        # --- List widget for kits ---
        list_widget = QListWidget()
        layout.addWidget(QLabel("Select a kit:"))
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
        btn_cancel = QPushButton("Cancel")
        btn_select = QPushButton("Select")
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_select)
        layout.addLayout(btn_layout)

        # --- Connect signals ---
        list_widget.itemClicked.connect(add_selected)
        btn_cancel.clicked.connect(dialog.reject)
        btn_select.clicked.connect(select_kit)  # <--- sin paréntesis

        dialog.exec()

    # Method to show a warning message
    def show_calibration_warning(self):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Warning)
        msg.setWindowTitle("NanoVNA UTN Toolkit - Calibration Warning")
        msg.setText(
            "Save operation is disabled because calibration was not performed from scratch.\n"
            "Please use the calibration wizard to create a new calibration before saving."
        )
        msg.exec()

    def save_kit_dialog(self):
        from PySide6.QtWidgets import QMessageBox
        """Shows a dialog to save the calibration without advancing to graphics window"""

        self.osm_calibration.is_complete_true()
        self.thru_calibration.is_complete_true()

        if getattr(sys, 'frozen', False):
            appdata = os.getenv("APPDATA")  
            base_dir = os.path.join(appdata, "NanoVNA-UTN-Toolkit")

            osm_dir = os.path.join(base_dir, "Calibration", "osm_results")
            thru_dir = os.path.join(base_dir, "Calibration", "thru_results")

        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
            osm_dir = os.path.join(base_dir, "Calibration", "osm_results")
            thru_dir = os.path.join(base_dir, "Calibration", "thru_results")

        files = [
            os.path.join(osm_dir, "open.s1p"),
            os.path.join(osm_dir, "short.s1p"),
            os.path.join(osm_dir, "match.s1p"),
            os.path.join(thru_dir, "thru.s2p")
        ]

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

        settings = QSettings(calibration_path, QSettings.IniFormat)

        # Method
        selected_method = settings.value("Calibration/Method", "No Kit")

        # Dialog to enter calibration name
        from PySide6.QtWidgets import QInputDialog

        logging.info(f"[Calibration_Kit] Selected Method: {selected_method}")

        if selected_method == "OSM (Open - Short - Match)":
            prefix = "OSM"
        elif selected_method == "Normalization":
            prefix = "Normalization"
        elif selected_method== "1-Port+N":
            prefix = "1PortN"
        elif selected_method == "Enhanced-Response":
            prefix = "Enhanced Response"

        name, ok = QInputDialog.getText(
            self, 
            'Save Calibration', 
            f'Enter calibration name:\n\nMeasurements to save:',
            text=f'{prefix}_Calibration_{self.get_current_timestamp()}'
        )
        
        if ok and name:
            try:
                # Save calibration (it will save only the available measurements)
                if selected_method != "Normalization": 
                    success = self.osm_calibration.save_calibration_file(name, selected_method, False, files)
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
                        #QMessageBox.warning(self, "Error", "Failed to save calibration") hay un error aca y entra primero

                success = self.thru_calibration.save_calibration_file(name, selected_method, True, files, osm_instance=self.osm_calibration)
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

                """
                # --- If a kit was previously saved in this session, show its name ---
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

                logging.info(f"[welcome_windows.open_save_calibration] Saved calibration {full_calibration_name}")

            except Exception as e:
                logging.error(f"[CalibrationKit] Error saving calibration: {e}")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"Error saving calibration: {str(e)}")

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
        dialog.setWindowTitle("NanoVNA UTN Toolkit - Delete Calibration Kits")
        dialog.setMinimumWidth(400)

        layout = QVBoxLayout(dialog)

        # --- Base directory and ini path ---
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

        settings = QSettings(calibration_path, QSettings.IniFormat)

        # --- List widget for kits ---
        list_widget = QListWidget()
        layout.addWidget(QLabel("Select kits to delete:"))
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
        btn_cancel = QPushButton("Cancel")
        btn_delete = QPushButton("Delete")
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

            # --- Read current calibration name ---
            current_full_name = settings.value("Calibration/Name", "")
            current_name_base = "_".join(current_full_name.split("_")[:-1]) if current_full_name else ""

            deleted_current_kit = False

            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

            # --- Delete physical folders and mark if current kit is deleted ---
            kits_to_delete = []
            for g in settings.childGroups():
                if g.startswith("Kit_"):
                    kit_name_ini = settings.value(f"{g}/kit_name", "").strip()
                    if kit_name_ini in selected_names:
                        if kit_name_ini == current_name_base:
                            deleted_current_kit = True  # MARKER: current kit will be deleted

                        if getattr(sys, 'frozen', False):
                            appdata = os.getenv("APPDATA")  
                            base = os.path.join(appdata, "NanoVNA-UTN-Toolkit")

                            kit_path = os.path.join(
                                base, "Calibration", "kits",
                            )
                        else:
                            ui_dir = os.path.dirname(os.path.dirname(__file__))
                            kit_path = os.path.join(ui_dir, "calibration", "kits", kit_name_ini)

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
                self.handle_deleted_current_kit()
            elif was_current_deleted == "all":
                self.handle_all_kits_deleted()
 
        # --- Connect signals ---
        list_widget.itemClicked.connect(add_selected)
        btn_cancel.clicked.connect(dialog.reject)
        btn_delete.clicked.connect(delete_selected)

        dialog.exec()

    def handle_deleted_current_kit(self):
        from PySide6.QtCore import QSettings
        import os

        if getattr(sys, 'frozen', False):
            appdata = os.getenv("APPDATA")  
            base = os.path.join(appdata, "NanoVNA-UTN-Toolkit")

            calibration_path = os.path.join(
                base, "INI", "calibration_config", "calibration_config.ini"
            )
        else:
            ui_dir = os.path.dirname(os.path.dirname(__file__))
            calibration_path = os.path.join(ui_dir, "calibration", "config", "calibration_config.ini")

        settings = QSettings(calibration_path, QSettings.IniFormat)
        settings.sync()

        # --- Check if there's still a Kit_1 ---
        if settings.contains("Kit_1/kit_name"):
            first_kit_name = settings.value("Kit_1/kit_name", "").strip()
            method = settings.value("Kit_1/method", "")
            
            # Get previous method/parameter if they exist
            prev_method = settings.value("Calibration/Method", method)
            prev_parameter = settings.value("Calibration/Parameter", "S21")

            # --- Update Calibration section ---
            settings.beginGroup("Calibration")
            settings.setValue("Kits", True)
            settings.setValue("NoCalibration", False)
            settings.setValue("Method", prev_method)
            settings.setValue("Parameter", prev_parameter)
            settings.setValue("Name", f"{first_kit_name}_1")
            settings.setValue("id", 1)
            settings.endGroup()

        settings.sync()

        if self.vna_device:
            graphics_window = NanoVNAGraphics(vna_device=self.vna_device)
        else:
            graphics_window = NanoVNAGraphics()
        graphics_window.show()
        self.close()

    def handle_all_kits_deleted(self):
        from PySide6.QtCore import QSettings
        import os

        if getattr(sys, 'frozen', False):
            appdata = os.getenv("APPDATA")  
            base = os.path.join(appdata, "NanoVNA-UTN-Toolkit")

            calibration_path = os.path.join(
                base, "INI", "calibration_config", "calibration_config.ini"
            )
        else:
            ui_dir = os.path.dirname(os.path.dirname(__file__))
            calibration_path = os.path.join(ui_dir, "calibration", "config", "calibration_config.ini")

        settings = QSettings(calibration_path, QSettings.IniFormat)

        kits_ok = settings.value("Calibration/Kits", False, type=bool)
        no_calibration = settings.value("Calibration/NoCalibration", False, type=bool)
        calibration_wizard = settings.value("Calibration/CalibrationWizard", False, type=bool)

        settings.sync()

        if not no_calibration and calibration_wizard:
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

        elif not no_calibration and not calibration_wizard:

            # --- Set calibration state to NoCalibration ---
            settings.beginGroup("Calibration")
            settings.setValue("Kits", False)
            settings.setValue("NoCalibration", True)
            settings.setValue("CalibrationWizard", False)
            settings.remove("Name")
            settings.remove("id")
            settings.endGroup()
            settings.sync()

        # --- Reopen graphics window in no-calibration mode ---
        if self.vna_device:
            graphics_window = NanoVNAGraphics(vna_device=self.vna_device)
        else:
            graphics_window = NanoVNAGraphics()

        graphics_window.show()

        self.close()

    # =================== SWEEP OPTIONS FUNCTION ==================

    def open_sweep_options(self):
        from NanoVNA_UTN_Toolkit.ui.sweep_window import SweepOptionsWindow

        # Log sweep options opening
        logging.info("[graphics_window.open_sweep_options] Opening sweep options window")

        # Try to get the current VNA device (this is a placeholder for now)
        vna_device = self.get_current_vna_device()

        # Log device information being passed to sweep options
        if vna_device:
            device_type = type(vna_device).__name__
            logging.info(f"[graphics_window.open_sweep_options] Device found: {device_type}")
            if hasattr(vna_device, 'sweep_points_min') and hasattr(vna_device, 'sweep_points_max'):
                logging.info(f"[graphics_window.open_sweep_options] Device sweep limits: {vna_device.sweep_points_min} to {vna_device.sweep_points_max}")
            else:
                logging.info("[graphics_window.open_sweep_options] Device has no sweep_points limits")
        else:
            logging.warning("[graphics_window.open_sweep_options] No VNA device available - using default limits")

        if hasattr(self, 'sweep_options_window') and self.sweep_options_window is not None:
            self.sweep_options_window.close()
            self.sweep_options_window.deleteLater()
            self.sweep_options_window = None

        logging.info("[graphics_window.open_sweep_options] Creating new sweep options window")
        self.sweep_options_window = SweepOptionsWindow(parent=self, vna_device=self.vna_device)

        self.sweep_options_window.show()
        self.sweep_options_window.raise_()
        self.sweep_options_window.activateWindow()
        
    def get_current_vna_device(self):
        """Try to get the current VNA device."""
        logging.info("[graphics_window.get_current_vna_device] Searching for current VNA device")
        
        try:
            # Check if we have device stored in this graphics window
            if hasattr(self, 'vna_device') and self.vna_device is not None:
                device_type = type(self.vna_device).__name__
                logging.info(f"[graphics_window.get_current_vna_device] Found stored device: {device_type}")
                return self.vna_device
                
            # Check if we can access the connection window device
            # This is a more advanced implementation for future development
            logging.warning("[graphics_window.get_current_vna_device] No VNA device found in graphics window")
            logging.warning("[graphics_window.get_current_vna_device] Device wasn't passed from previous window")
            
            return None
        except Exception as e:
            logging.error(f"[graphics_window.get_current_vna_device] Error getting current VNA device: {e}")
            return None

    # =================== RIGHT CLICK ==================

    def contextMenuEvent(self, event):
        menu = QMenu(self)

        view_menu = menu.addAction("View")

        menu.addSeparator()
        
        marker1_graphic1_action = menu.addAction("Marker 1 - Graphic 1")
        marker1_graphic1_action.setCheckable(True)
        marker1_graphic1_action.setChecked(self.show_graphic1_marker1)

        marker1_graphic2_action = menu.addAction("Marker 1 - Graphic 2")
        marker1_graphic2_action.setCheckable(True)
        marker1_graphic2_action.setChecked(self.show_graphic2_marker1)

        marker2_graphic1_action = menu.addAction("Marker 2 -Graphic 1")
        marker2_graphic1_action.setCheckable(True)
        marker2_graphic1_action.setChecked(False)
        marker2_graphic1_action.setChecked(self.show_graphic1_marker2)

        marker2_graphic2_action = menu.addAction("Marker 2 -Graphic 2")
        marker2_graphic2_action.setCheckable(True)
        marker2_graphic2_action.setChecked(False)
        marker2_graphic2_action.setChecked(self.show_graphic2_marker2)

        # --- Lock markers action ---
        lock_markers_action = menu.addAction("Lock Markers ✓" if self.markers_locked else "Lock Markers")
        lock_markers_action.setCheckable(True)
        lock_markers_action.setChecked(self.markers_locked)

        # --- Determine which graph was clicked ---
        widget_under_cursor = QApplication.widgetAt(event.globalPos())
        graph_number = 1  # default left
        current_widget = widget_under_cursor
        while current_widget:
            if hasattr(self, "canvas_right") and current_widget == self.canvas_right:
                graph_number = 2
                break
            elif hasattr(self, "canvas_left") and current_widget == self.canvas_left:
                graph_number = 1
                break
            current_widget = current_widget.parent()

        # --- Read the current unit from INI ---
        import os
        from PySide6.QtCore import QSettings

        # Load configuration for UI colors and styles
        if getattr(sys, 'frozen', False):
            appdata = os.getenv("APPDATA")
            base = os.path.join(appdata, "NanoVNA-UTN-Toolkit")
            ruta_colors = os.path.join(base, "INI", "colors_config", "config.ini")
        else:
            ui_dir = os.path.dirname(os.path.dirname(__file__))
            ruta_colors = os.path.join(ui_dir, "ui", "graphics_windows", "ini", "config.ini")

        settings = QSettings(ruta_colors, QSettings.IniFormat)

        ini_section = "Graphic1" if graph_number == 1 else "Graphic2"

        tab_section = "Tab1" if graph_number == 1 else "Tab2"

        settings.beginGroup(ini_section)
        current_unit = settings.value("db_times", "dB")
        settings.endGroup()

        settings.beginGroup(tab_section)
        s_param = settings.value("SParameter", "S11")
        graph_type = settings.value("GraphType1" if graph_number == 1 else "GraphType2", "Smith Diagram")
        settings.endGroup()

        # Check if current graph is Smith Diagram
        is_smith_diagram = graph_type == "Smith Diagram"

        # --- Unit submenu (disabled for Smith Diagram) ---
        menu.addSeparator()
        unit_menu = QMenu(f"Unit", self)
        unit_menu.setEnabled(not is_smith_diagram)
        
        # Initialize unit actions as None
        voltage_action = None
        db_action = None
        
        if current_unit == "dB":
            voltage_action = unit_menu.addAction(f"Times ({s_param})")
        else:
            db_action = unit_menu.addAction(f"dB({s_param})")
        menu.addMenu(unit_menu)

        # ---- grid ----

        menu.addSeparator()

        # --- Grid action ---
        widget_under_cursor = QApplication.widgetAt(event.globalPos())
        target_ax = None
        target_fig = None
        target_attr = None

        current_widget = widget_under_cursor
        while current_widget:
            if hasattr(self, "canvas_right") and current_widget == self.canvas_right:
                target_ax = self.ax_right
                target_fig = self.fig_right
                target_attr = "grid_enabled_right"
                selected_graph_name = "right"
                break
            elif hasattr(self, "canvas_left") and current_widget == self.canvas_left:
                target_ax = self.ax_left
                target_fig = self.fig_left
                target_attr = "grid_enabled_left"
                selected_graph_name = "left"
                break
            current_widget = current_widget.parent()

        current_state = getattr(self, target_attr, True) if target_attr else True
        if target_attr is not None:
            setattr(self, target_attr, current_state)

        if target_ax and target_fig:
            target_ax.grid(current_state)
            target_fig.canvas.draw_idle()

        # --- Grid action (disabled for Smith Diagram) ---
        grid_action = menu.addAction("Grid ✓" if current_state else "Grid")
        grid_action.setCheckable(True)
        grid_action.setChecked(current_state)
        grid_action.setEnabled(not is_smith_diagram)

        # --- Range action (disabled for Smith Diagram) ---
        range_action = menu.addAction("Set range")
        range_action.setEnabled(not is_smith_diagram)

        smith_action = None

        #smith_action = menu.addAction("Smith Normalized")

        # --- Export ---
        menu.addSeparator()
        export_action = menu.addAction("Export...")

        selected_action = menu.exec(event.globalPos())

        self.ax_to_network = {
            self.ax_left: rf.Network(frequency=self.freqs, s=self.s11, z0=50),
            self.ax_right: rf.Network(frequency=self.freqs, s=self.s11, z0=50)
        }

        # --- Handle actions ---
        if selected_action == view_menu:
            self.open_view()

        # --- Markers ---

        elif selected_action == marker1_graphic1_action:
            self.show_graphic1_marker1 = not self.show_graphic1_marker1
            self.toggle_marker_visibility(0, self.show_graphic1_marker1)

            if self.show_graphic1_marker1:
                self.info_panel_left.show()
            if not self.show_graphic1_marker1 and self.show_graphic1_marker2:
                self.info_panel_left.hide()

            if self.show_graphic1_marker1 and not self.show_graphic1_marker2:
                self.info_panel_left.show()
                self.info_panel_left_2.hide()

        elif selected_action == marker1_graphic2_action:
            self.show_graphic2_marker1 = not self.show_graphic2_marker1
            self.toggle_marker_visibility(1, self.show_graphic2_marker1)

            if self.show_graphic2_marker1:
                self.info_panel_right.show()
            if not self.show_graphic2_marker1 and self.show_graphic2_marker2:
                self.info_panel_right.hide()
            if self.show_graphic2_marker1 and not self.show_graphic2_marker2:
                self.info_panel_right.show()
                self.info_panel_right_2.hide()

        elif selected_action == marker2_graphic1_action:
            self.show_graphic1_marker2 = not self.show_graphic1_marker2
         
            self.toggle_marker2_visibility(0, self.show_graphic1_marker2)

            if self.show_graphic1_marker2:
                self.info_panel_left_2.show()
            if not self.show_graphic1_marker2 and self.show_graphic1_marker1:
                self.info_panel_left_2.hide()
            if self.show_graphic1_marker2 and not self.show_graphic1_marker1:
                self.info_panel_left.hide()
                self.info_panel_left_2.show()

        elif selected_action == marker2_graphic2_action:
            self.show_graphic2_marker2 = not self.show_graphic2_marker2
         
            self.toggle_marker2_visibility(1, self.show_graphic2_marker2)

            if self.show_graphic2_marker2:
                self.info_panel_right_2.show()
            if not self.show_graphic2_marker2 and self.show_graphic2_marker1:
                self.info_panel_right_2.hide()
            if not self.show_graphic2_marker1 and self.show_graphic2_marker2:
                self.info_panel_right.hide()
                self.info_panel_right_2.show()

        # --- Lock Markers ---

        elif selected_action == lock_markers_action:
            self.markers_locked = not self.markers_locked

            lock_markers_action.setChecked(self.markers_locked)

            settings.setValue("Markers/locked", self.markers_locked)
            
            if self.markers_locked:
                val = self.slider_left.val
                self.slider_right.set_val(val)
                self.update_right_cursor(val)

                val_2 = self.slider_left_2.val
                self.slider_right_2.set_val(val_2)
                self.update_right_cursor_2(val_2)

        # --- Grid ---
          
        elif selected_action == grid_action and target_ax and target_fig and target_attr and not is_smith_diagram:
            new_state = not getattr(self, target_attr, True)
            if target_attr is not None:
                setattr(self, target_attr, new_state)
            target_ax.grid(new_state)
            target_fig.canvas.draw_idle()
            grid_action.setText("Grid ✓" if new_state else "Grid")

        # --- Range ---

        elif selected_action == range_action and not is_smith_diagram:
            self.show_y_range_dialog(target_ax)

        # --- Smith Normalized ---
          
        # --- Toggle Smith Normalized ---
        elif smith_action is not None and selected_action == smith_action and target_ax and target_fig:
            # Determinar si el gráfico seleccionado es tipo Smith

            logging.info(f"selected_graph_name: {selected_graph_name}")
            logging.info(f"left_graph_type: {self.left_graph_type}")
            logging.info(f"right_graph_type: {self.right_graph_type}")
            logging.info(f"target_ax: {target_ax}")
            logging.info(f"target_fig: {target_fig}")

            is_smith = (selected_graph_name == "left" and self.left_graph_type.lower() == "smith diagram") or \
                    (selected_graph_name == "right" and self.right_graph_type.lower() == "smith diagram")

            if not is_smith:
                # Mostrar advertencia al usuario
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.information(self, "Smith Normalized",
                                        "The selected graph is not a Smith chart and cannot be normalized to Γ.")
                return

            # Tomar el Network asociado al ax
            net = self.ax_to_network.get(target_ax, None)
            if net is None:
                return

            # Dibujar Gamma normalizado
            gamma = net.s[:,0,0]
            target_ax.clear()
            target_ax.plot(gamma.real, gamma.imag, 'o-')
            target_ax.set_xlim(-1, 1)
            target_ax.set_ylim(-1, 1)
            target_ax.set_xlabel("Re(Γ)")
            target_ax.set_ylabel("Im(Γ)")
            target_ax.grid(True)
            target_fig.canvas.draw_idle()

        # --- Export ---

        elif selected_action == export_action:
            self.open_export_dialog(event)

        # --- Handle unit change (disabled for Smith Diagram) ---
        elif current_unit == "dB" and not is_smith_diagram:
            if selected_action == voltage_action:
                self.toggle_db_times(event, "Voltage ratio")
        elif current_unit in ("Power ratio", "Voltage ratio") and not is_smith_diagram:
            if selected_action == db_action:
                self.toggle_db_times(event, "dB")

        if self.show_graphic1_marker1 and self.show_graphic1_marker2 or self.show_graphic2_marker1 and self.show_graphic2_marker2:
            self.markers_button.show()
        else:
            self.markers_button.hide()

    def show_y_range_dialog(self, target_ax):
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox

        if target_ax is None:
            QMessageBox.warning(None, "Error", "No axis selected.")
            return

        if self.left_graph_type != "Smith Diagram" or self.right_graph_type != "Smith Diagram": 

            dlg = QDialog(self)
            dlg.setWindowTitle("NanoVNA UTN Toolkit - Set Y Range")
            dlg.setFixedSize(250, 150)

            layout = QVBoxLayout(dlg)

            # --- Inputs ---
            l1 = QHBoxLayout()
            l1.addWidget(QLabel("Y min:"))
            ymin_edit = QLineEdit()
            ymin_edit.setPlaceholderText(str(target_ax.get_ylim()[0]))
            l1.addWidget(ymin_edit)
            layout.addLayout(l1)

            l2 = QHBoxLayout()
            l2.addWidget(QLabel("Y max:"))
            ymax_edit = QLineEdit()
            ymax_edit.setPlaceholderText(str(target_ax.get_ylim()[1]))
            l2.addWidget(ymax_edit)
            layout.addLayout(l2)

            # --- Buttons ---
            btn_layout = QHBoxLayout()
            apply_btn = QPushButton("Apply")
            cancel_btn = QPushButton("Cancel")
            btn_layout.addWidget(apply_btn)
            btn_layout.addWidget(cancel_btn)
            layout.addLayout(btn_layout)

            # --- Logic ---
            def apply_clicked():
                try:
                    ymin_text = ymin_edit.text().strip()
                    ymax_text = ymax_edit.text().strip()

                    if not ymin_text and not ymax_text:
                        dlg.reject()
                        return

                    ymin = float(ymin_text) if ymin_text else target_ax.get_ylim()[0]
                    ymax = float(ymax_text) if ymax_text else target_ax.get_ylim()[1]

                    target_ax.set_ylim(ymin, ymax)
                    target_ax.figure.canvas.draw_idle()
                    dlg.accept()

                except ValueError:
                    QMessageBox.warning(dlg, "Invalid Input", "Please enter valid numbers for Y min and Y max.")

            apply_btn.clicked.connect(apply_clicked)
            cancel_btn.clicked.connect(dlg.reject)

            dlg.exec()

    def show_frequency_difference_dialog(self):
        import os
        from PySide6.QtWidgets import QDialog, QLabel, QHBoxLayout, QVBoxLayout
        from PySide6.QtCore import Qt, QSettings

        # --- Función auxiliar para formatear frecuencia ---
        def format_frequency_diff(freq_hz):
            """Return a string with appropriate unit (KHz, MHz, GHz) for frequency difference."""
            if 1e3 <= abs(freq_hz) < 1e6:
                return f"{freq_hz / 1e3:.3f} KHz"
            elif 1e6 <= abs(freq_hz) < 1e9:
                return f"{freq_hz / 1e6:.3f} MHz"
            else:
                return f"{freq_hz / 1e9:.3f} GHz"

        # --- Path to config.ini ---
        # Load configuration for UI colors and styles
        if getattr(sys, 'frozen', False):
            appdata = os.getenv("APPDATA")
            base = os.path.join(appdata, "NanoVNA-UTN-Toolkit")
            ruta_colors = os.path.join(base, "INI", "colors_config", "config.ini")
        else:
            ui_dir = os.path.dirname(os.path.dirname(__file__))
            ruta_colors = os.path.join(ui_dir, "ui", "graphics_windows", "ini", "config.ini")

        settings = QSettings(ruta_colors, QSettings.IniFormat)

        # --- Read cursor indices ---
        cursor_1_1_index = int(settings.value("Cursor_1_1/index", 0))
        cursor_1_2_index = int(settings.value("Cursor_1_2/index", 0))
        cursor_2_1_index = int(settings.value("Cursor_2_1/index", 0))
        cursor_2_2_index = int(settings.value("Cursor_2_2/index", 0))

        # --- LEFT PANEL VALUES ---
        left_marker1_vals = self._update_cursor_orig(index=cursor_1_1_index, from_slider=True, return_values=True)
        left_marker2_vals = self._update_cursor_2_orig(index=cursor_2_1_index, from_slider=True, return_values=True)
        left_diff = {key: left_marker2_vals[key] - left_marker1_vals[key] for key in ["freq", "mag", "phase"]}

        # --- RIGHT PANEL VALUES ---
        right_marker1_vals = self._update_cursor_right_orig(index=cursor_1_2_index, from_slider=True, return_values=True)
        right_marker2_vals = self._update_cursor_2_right_orig(index=cursor_2_2_index, from_slider=True, return_values=True)
        right_diff = {key: right_marker2_vals[key] - right_marker1_vals[key] for key in ["freq", "mag", "phase"]}

        # --- Determine which panels to show ---
        show_left = (self.show_graphic1_marker1 and self.show_graphic1_marker2)
        show_right = (self.show_graphic2_marker1 and self.show_graphic2_marker2)

        # --- CREATE DIALOG ---
        dialog = QDialog(self)
        dialog.setWindowTitle("NanoVNA UTN Toolkit - Marker Differences")
        dialog.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        layout = QHBoxLayout()

        # --- Adjust size based on panels shown ---
        if show_left and show_right:
            dialog.setFixedSize(500, 120)
        else:  # only one panel
            dialog.setFixedSize(260, 120)

        # --- LEFT PANEL DISPLAY ---
        if show_left:
            left_layout = QVBoxLayout()
            left_title = QLabel("Left Panel Differences")
            left_title.setAlignment(Qt.AlignCenter)
            left_layout.addWidget(left_title)
            for key in ["freq", "mag", "phase"]:
                row = QHBoxLayout()
                row.addWidget(QLabel(f"{key.capitalize()} Diff:"))
                if key == "freq":
                    text = format_frequency_diff(left_diff[key])
                else:
                    text = f"{left_diff[key]:.3f}"
                row.addWidget(QLabel(text))
                left_layout.addLayout(row)
            layout.addLayout(left_layout)

        # --- RIGHT PANEL DISPLAY ---
        if show_right:
            right_layout = QVBoxLayout()
            right_title = QLabel("Right Panel Differences")
            right_title.setAlignment(Qt.AlignCenter)
            right_layout.addWidget(right_title)
            for key in ["freq", "mag", "phase"]:
                row = QHBoxLayout()
                row.addWidget(QLabel(f"{key.capitalize()} Diff:"))
                if key == "freq":
                    text = format_frequency_diff(right_diff[key])
                else:
                    text = f"{right_diff[key]:.3f}"
                row.addWidget(QLabel(text))
                right_layout.addLayout(row)
            layout.addLayout(right_layout)

        # --- Set layout and show ---
        dialog.setLayout(layout)
        dialog.exec()

    def toggle_db_times(self, event, new_mode):
        """
        Toggle between dB and times for the clicked graph.
        Saves independently for Left (Graphic1) and Right (Graphic2) graph in the INI.
        """
        import os
        from PySide6.QtCore import QSettings

        try:
            # Detect the graph clicked
            widget_under_cursor = QApplication.widgetAt(event.globalPos())
            if widget_under_cursor is None:
                return

            graph_number = 1  # default left
            current_widget = widget_under_cursor
            while current_widget:
                if hasattr(self, "canvas_right") and current_widget == self.canvas_right:
                    graph_number = 2
                    break
                elif hasattr(self, "canvas_left") and current_widget == self.canvas_left:
                    graph_number = 1
                    break
                current_widget = current_widget.parent()

            # Decide INI section based on graph
            ini_section = "Graphic1" if graph_number == 1 else "Graphic2"

            # Load configuration for UI colors and styles
            if getattr(sys, 'frozen', False):
                appdata = os.getenv("APPDATA")
                ruta_colors = os.path.join(
                    appdata,
                    "NanoVNA-UTN-Toolkit",
                    "INI",
                    "colors_config",
                    "config.ini"
                )
            else:
                ui_dir = os.path.dirname(os.path.dirname(__file__))
                ruta_colors = os.path.join(ui_dir, "ui", "graphics_windows", "ini", "config.ini")

            settings = QSettings(ruta_colors, QSettings.IniFormat)

            settings.beginGroup(ini_section)

            # Guardar la unidad seleccionada
            settings.setValue("db_times", new_mode)

            # Guardar número de gráfico
            settings.setValue("graph_number", graph_number)

            settings.endGroup()
            settings.sync()

            logging.info(f"Unit {new_mode} saved for {ini_section}")

            update_plots_with_new_data(self, skip_reset=False)

            self.update_cursor()
            self.update_right_cursor()

            self.update_cursor_2()
            self.update_right_cursor_2()

        except Exception as e:
            logging.error(f"Error toggling db/times: {e}")

    def open_export_dialog(self, event):
        """Open the export dialog for the clicked graph."""
        # Determine which graph was clicked based on event position
        widget_under_cursor = QApplication.widgetAt(event.globalPos())
        
        try:
            # Default to left figure
            figure_to_export = self.fig_left
            panel_name = "Left Panel"
            
            # Try to determine which canvas was clicked
            if hasattr(self, 'canvas_right') and widget_under_cursor:
                # Walk up the widget hierarchy to find the canvas
                current_widget = widget_under_cursor
                while current_widget:
                    if current_widget == self.canvas_right:
                        figure_to_export = self.fig_right
                        panel_name = "Right Panel"
                        break
                    elif current_widget == self.canvas_left:
                        figure_to_export = self.fig_left
                        panel_name = "Left Panel"
                        break
                    current_widget = current_widget.parent()

            # Close previous export dialog if it exists
            if hasattr(self, 'export_dialog') and self.export_dialog is not None:
                self.export_dialog.close()
                self.export_dialog.deleteLater()
                self.export_dialog = None

            # Create and show new export dialog
            show_left_markers = [self.show_graphic1_marker1, self.show_graphic1_marker2]
            show_right_markers = [self.show_graphic2_marker1, self.show_graphic2_marker2]

            update_cursor_left = [self.update_cursor, self.update_cursor_2]
            update_cursor_right = [self.update_right_cursor, self.update_right_cursor_2]

            self.export_dialog = ExportDialog(
                self,
                figure_to_export,
                left_graph=self.left_graph_type,
                right_graph=self.right_graph_type,
                freqs=self.freqs,
                show_markers_left = show_left_markers,
                show_markers_right = show_right_markers,
                update_cursor_left = update_cursor_left,
                update_cursor_right = update_cursor_right
            )

            self.export_dialog.setWindowTitle(f"NanoVNA UTN Toolkit - Export Graph - {panel_name}")
            self.export_dialog.exec()
            
        except Exception as e:
            logging.error(f"Error opening export dialog: {e}")
            QMessageBox.warning(self, "Export Error", f"Failed to open export dialog: {str(e)}")

    # =================== MARKERS ==================

    def edit_graphics_markers(self):
        from NanoVNA_UTN_Toolkit.ui.graphics_windows.edit_graphics_window import EditGraphics
        self.edit_graphics_window = EditGraphics(nano_window=self) 
        self.edit_graphics_window.show()

    # =================== VIEW ==================

    def open_view(self):
        from NanoVNA_UTN_Toolkit.ui.graphics_windows.view_window import View
        
        # Cerrar la instancia anterior si existe
        if hasattr(self, 'view_window') and self.view_window is not None:
            self.view_window.close()
            self.view_window.deleteLater()
            self.view_window = None

        # Crear nueva instancia de View
        self.view_window = View(nano_window=self)
        self.view_window.show()
        self.view_window.raise_()
        self.view_window.activateWindow()

    # =================== TOGGLE MARKERS==================

    def clear_freq_edit(self, edit_widget):
        edit_widget.blockSignals(True) 
        edit_widget.setText("--")
        edit_widget.setFixedWidth(edit_widget.fontMetrics().horizontalAdvance(edit_widget.text()) + 4)
        edit_widget.blockSignals(False)

    def toggle_marker_visibility(self, marker_index, show=True):
        marker = self.markers[marker_index]
        cursor = marker["cursor"]
        slider = marker["slider"]
        labels = marker["label"]
        update_cursor_func = marker.get("update_cursor", None)

        logging.info(f"cursor data: {cursor.get_data()}")

        # Check if cursor is valid before using it
        if cursor is None or cursor.figure is None:
            logging.warning(f"[graphics_window.toggle_marker_visibility] Cursor {marker_index} is invalid, skipping toggle")
            return

        cursor.set_visible(show)

        if marker_index == 0:  
            slider = self.slider_left
            slider_2 = self.slider_left_2
            fig = self.fig_left
        elif marker_index == 1: 
            slider = self.slider_right
            slider_2 = self.slider_right_2
            fig = self.fig_right
        else:
            logging.warning(f"[move_marker2_slider_left] Invalid marker_index {marker_index}")
            return

        if show:
            slider_2.ax.set_position([0.55,0.04,0.35,0.03])

            slider.ax.set_visible(True)
            slider.set_active(True)
            if hasattr(marker, "slider_callback"):
                slider.on_changed(marker.slider_callback)

            if update_cursor_func:
                update_cursor_func(0)

            edit_value = labels["freq"]
            edit_value.setEnabled(True)
            if self.freqs is not None and len(self.freqs) > 0:
                if self.freqs[0] < 1e6:  
                    edit_value.setText(f"{self.freqs[0]/1e3:.3f}")
                elif self.freqs[0] < 1e9:  
                    edit_value.setText(f"{self.freqs[0]/1e6:.3f}")
                else: 
                    edit_value.setText(f"{self.freqs[0]/1e9:.3f}")
            else:
                edit_value.setText("--") 

        else:
            slider.set_val(0)
            slider.ax.set_visible(False)
            slider.set_active(False)

            edit_value = labels["freq"]
            edit_value.setEnabled(False)
            edit_value.setText("0")

            # --- Limpiar otros labels ---
            labels["val"].setText(f"{self.left_s_param if marker_index==0 else 'S11'}: -- + j--")
            labels["mag"].setText("|S11|: --")
            labels["phase"].setText("Phase: --")
            labels["z"].setText("Z: -- + j--")
            labels["il"].setText("IL: --")
            labels["vswr"].setText("VSWR: --")

            slider_2.ax.set_position([0.25,0.04,0.5,0.03])

        # Only draw if cursor and figure are valid
        if cursor is not None and cursor.figure is not None and cursor.figure.canvas is not None:
            cursor.figure.canvas.draw_idle()
        else:
            logging.warning(f"[graphics_window.toggle_marker_visibility] Cannot draw cursor {marker_index}, figure or canvas is None")

    def toggle_marker2_visibility(self, marker_index, show_markers):
        """
        Move Marker 2 slider to the left of the corresponding canvas
        without hiding or deactivating it.
        """
        marker_2 = self.markers[marker_index]

        cursor_2 = marker_2["cursor_2"]
        slider_2 = marker_2["slider_2"]
        labels_2 = marker_2["label_2"]

        update_cursor_func_2 = marker_2.get("update_cursor_2", None)

        logging.info(f"cursor_2 data: {cursor_2.get_data()}")

        if cursor_2 is None or cursor_2.figure is None:
            logging.warning(f"[graphics_window.toggle_marker_visibility_2] Cursor {marker_index} is invalid, skipping toggle")
            return

        cursor_2.set_visible(show_markers)

        if marker_index == 0:  
            slider = self.slider_left
            slider_2 = self.slider_left_2
            fig = self.fig_left
        elif marker_index == 1: 
            slider = self.slider_right
            slider_2 = self.slider_right_2
            fig = self.fig_right
        else:
            logging.warning(f"[move_marker2_slider_left] Invalid marker_index {marker_index}")
            return

        if show_markers:

            slider_2.ax.set_visible(True)
            slider_2.set_active(True)

            slider.ax.set_position([0.1, 0.04, 0.35, 0.03])

            #slider_2.on_changed(lambda val: update_cursor(int(val), from_slider=True))

            if slider.ax.figure is not None:
                slider.ax.figure.canvas.draw_idle()

            if update_cursor_func_2:
                update_cursor_func_2(0)

            edit_value_2 = labels_2["freq"]
            edit_value_2.setEnabled(True)
            if self.freqs is not None and len(self.freqs) > 0:
                if self.freqs[0] < 1e6:  
                    edit_value_2.setText(f"{self.freqs[0]/1e3:.3f}")
                elif self.freqs[0] < 1e9:  
                    edit_value_2.setText(f"{self.freqs[0]/1e6:.3f}")
                else: 
                    edit_value_2.setText(f"{self.freqs[0]/1e9:.3f}")
            else:
                edit_value_2.setText("--") 
   
        elif not show_markers:

            slider_2.set_val(0)
            slider_2.ax.set_visible(False)
            slider_2.set_active(False) 

            # --- Limpiar otros labels ---
            labels_2["val"].setText(f"{self.left_s_param if marker_index==0 else 'S11'}: -- + j--")
            labels_2["mag"].setText("|S11|: --")
            labels_2["phase"].setText("Phase: --")
            labels_2["z"].setText("Z: -- + j--")
            labels_2["il"].setText("IL: --")
            labels_2["vswr"].setText("VSWR: --")

            slider.ax.set_position([0.25,0.04,0.5,0.03])

        # Only draw if cursor and figure are valid
        if cursor_2 is not None and cursor_2.figure is not None and cursor_2.figure.canvas is not None:
            cursor_2.figure.canvas.draw_idle()
        else:
            logging.warning(f"[graphics_window.toggle_marker_visibility] Cannot draw cursor {marker_index}, figure or canvas is None")

    # =================== SWEEP FUNCTIONALITY ===================
    
    def load_sweep_configuration(self):
        """Load sweep configuration from sweep options config file."""
        
        try:

            # Load configuration for UI colors and styles
            if getattr(sys, 'frozen', False):
                appdata = os.getenv("APPDATA")
                sweep_config_path = os.path.join(
                    appdata,
                    "NanoVNA-UTN-Toolkit",
                    "INI",
                    "sweep_config",
                    "config.ini"
                )
                sweep_config_path = os.path.normpath(sweep_config_path)
            else:
                ui_dir = os.path.dirname(os.path.dirname(__file__))
                sweep_config_path = os.path.join(ui_dir, "ui", "sweep_window", "config", "config.ini")
                sweep_config_path = os.path.normpath(sweep_config_path)

            # Debug: log the config path to verify it matches sweep_options_window.py
            logging.info(f"[graphics_window.load_sweep_configuration] Config path: {sweep_config_path}")

            settings = QSettings(sweep_config_path, QSettings.IniFormat)

            if os.path.exists(sweep_config_path):
                settings = QSettings(sweep_config_path, QSettings.Format.IniFormat)
                logging.info(f"[graphics_window.load_sweep_configuration] Config file found and opened successfully")

                # Use consistent defaults with sweep_options_window.py
                default_start_hz = 50e3   # 50 kHz
                default_stop_hz = 1.5e9   # 1.5 GHz 
                default_segments = 101    # Default segments
                
                # Read values with proper defaults
                start_freq_val = settings.value("Frequency/StartFreqHz", default_start_hz)
                stop_freq_val = settings.value("Frequency/StopFreqHz", default_stop_hz)
                segments_val = settings.value("Frequency/Segments", default_segments)

                # Debug: log what we read from file
                logging.info(f"[graphics_window.load_sweep_configuration] Raw values from config: "
                            f"StartFreqHz={start_freq_val}, StopFreqHz={stop_freq_val}, Segments={segments_val}")

                try:
                    self.start_freq_hz = int(float(str(start_freq_val)))
                    self.stop_freq_hz = int(float(str(stop_freq_val)))
                    self.segments = int(str(segments_val))
                except (ValueError, TypeError) as e:
                    logging.error(f"[graphics_window.load_sweep_configuration] Error parsing values: {e}")
                    self.start_freq_hz = int(default_start_hz)
                    self.stop_freq_hz = int(default_stop_hz)
                    self.segments = default_segments

                logging.info(f"[graphics_window.load_sweep_configuration] Loaded sweep config: "
                            f"{self.start_freq_hz/1e6:.3f} MHz - {self.stop_freq_hz/1e6:.3f} MHz, "
                            f"{self.segments} points")

                self.start_unit = settings.value("Frequency/StartUnit", "kHz")
                self.stop_unit = settings.value("Frequency/StopUnit", "GHz")

                # Update info label if it exists
                if hasattr(self, 'sweep_info_label'):
                    self.update_sweep_info_label()

            else:
                # Default values if config file doesn't exist
                self.start_freq_hz = 50000
                self.stop_freq_hz = int(1.5e9)
                self.segments = 101
                logging.warning("[graphics_window.load_sweep_configuration] Config file not found, using defaults")

        except Exception as e:
            logging.error(f"[graphics_window.load_sweep_configuration] Error loading sweep config: {e}")
            # Fallback defaults
            self.start_freq_hz = 50000
            self.stop_freq_hz = int(1.5e9)
            self.segments = 101

    def update_sweep_info_label(self):
        """Update the sweep information label with current configuration."""
        try:
            start_val = self.start_freq_hz
            stop_val  = self.stop_freq_hz

            logging.info(f"[update_sweep_info_label] start_val={start_val} Hz")
            logging.info(f"[update_sweep_info_label] stop_val={stop_val} Hz")

            start_unit = self.start_unit
            stop_unit = self.stop_unit

            logging.info(f"[update_sweep_info_label] start_val={start_val}, stop_val={stop_val}")
            logging.info(f"[update_sweep_info_label] start_unit={start_unit}, stop_unit={stop_unit}")

            # Convert to proper units
            if start_unit.lower() == "khz":
                freq_start_str = f"{start_val/1e3:.1f} kHz"
            elif start_unit.lower() == "mhz":
                freq_start_str = f"{start_val/1e6:.3f} MHz"
            elif start_unit.lower() == "ghz":
                freq_start_str = f"{start_val/1e9:.3f} GHz"
            else:
                freq_start_str = f"{start_val} Hz"

            if stop_unit.lower() == "khz":
                freq_stop_str = f"{stop_val/1e3:.1f} kHz"
            elif stop_unit.lower() == "mhz":
                freq_stop_str = f"{stop_val/1e6:.3f} MHz"
            elif stop_unit.lower() == "ghz":
                freq_stop_str = f"{stop_val/1e9:.3f} GHz"
            else:
                freq_stop_str = f"{stop_val} Hz"

            info_text = f"Sweep: {freq_start_str} - {freq_stop_str}, {self.segments} points"
            self.sweep_info_label.setText(info_text)
            logging.info(f"[graphics_window.update_sweep_info_label] Updated info: {info_text}")
        except Exception as e:
            logging.error(f"[graphics_window.update_sweep_info_label] Error updating label: {e}")

    def import_touchstone_data_dut(self):
        from PySide6.QtWidgets import QFileDialog, QMessageBox
        import os

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select DUT Touchstone File",
            "",
            "Touchstone Files (*.s2p);;All Files (*)"
        )

        if not file_path:
            QMessageBox.warning(self, "No File Selected", "Please select a Touchstone .s2p file.")
            return

        files = file_path

        QMessageBox.information(self, "File Loaded", "Touchstone file loaded successfully!")
        print("Selected DUT file:", file_path)

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

        settings_calibration.setValue("Calibration/isImportDut", True)

        if self.vna_device:
            graphics_window = NanoVNAGraphics(vna_device=self.vna_device, dut=files)
        else:
            graphics_window = NanoVNAGraphics()

        graphics_window.show()

        self.close()

    def import_touchstone_data_calibration(self):
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

        # --- TRUNCADO A 101 PUNTOS
        truncated_files = []
        max_points = 101

        for f in files:
            try:
                ntw = rf.Network(f)
                if len(ntw.f) > max_points:
                    idx = np.linspace(0, len(ntw.f) - 1, max_points, dtype=int)
                    f_trunc = ntw.f[idx]
                    s_trunc = ntw.s[idx]
                    z0_trunc = ntw.z0[idx]
                    ntw_trunc = rf.Network(f=f_trunc, s=s_trunc, z0=z0_trunc)

                    base, ext = os.path.splitext(f)
                    new_path = f"{base}_trunc{ext}"
                    ntw_trunc.write_touchstone(new_path)
                    truncated_files.append(new_path)
                    print(f"Truncated {os.path.basename(f)} → {os.path.basename(new_path)} ({max_points} points)")
                else:
                    truncated_files.append(f)
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Error processing {f}:\n{str(e)}")
                return

        # "Select Method"
        dialog = QDialog(self)
        dialog.setWindowTitle("NanoVNA UTN Toolkit - Select Method")

        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)  

        label = QLabel("Select Method", dialog)
        main_layout.addWidget(label)

        self.select_method = QComboBox()
        self.select_method.setStyleSheet("""
            QComboBox {
                background-color: #3b3b3b;
                color: white;
                border: 2px solid white;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
                min-width: 200px;
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
            QComboBox:focus {
                background-color: #4d4d4d;
            }
            QComboBox::placeholder {
                color: #cccccc;
            }
        """)

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
        calibrate_button.clicked.connect(lambda: self.start_calibration(truncated_files, self.select_method.currentText(), dialog))
        button_layout.addWidget(calibrate_button)

        main_layout.addLayout(button_layout)

        dialog.exec()

    def get_current_timestamp(self):
        """Generate timestamp for filenames"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")

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

                # --- Save data ---
                settings_calibration.beginGroup(calibration_entry_name)
                settings_calibration.setValue("kit_name", name)
                settings_calibration.setValue("method", selected_method)
                settings_calibration.setValue("id", next_id)
                settings_calibration.endGroup()

                # --- Update active calibration reference ---
                settings_calibration.beginGroup("Calibration")
                settings_calibration.setValue("Name", full_calibration_name)
                settings_calibration.endGroup()
                settings_calibration.sync()

                settings_calibration.setValue("Calibration/Kits", True)
                settings_calibration.setValue("Calibration/NoCalibration", False)

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
                logging.error(f"[CalibrationGraphics] Error saving calibration: {e}")
                from PySide6.QtWidgets import QMessageBox
                QMessageBox.critical(self, "Error", f"Error saving calibration: {str(e)}")

    def _show_touchstone_format_dialog(self):
        """
        Show a simple dialog to choose between S1P and S2P export formats.
        
        Returns:
            str: "s1p" or "s2p" if user selects, None if cancelled
        """
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QButtonGroup, QRadioButton
        from PySide6.QtCore import Qt
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Touchstone Format")
        dialog.setFixedSize(350, 200)
        dialog.setModal(True)
        
        # Main layout
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title label
        title_label = QLabel("Choose Touchstone export format:")
        title_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(title_label)
        
        # Radio button group
        button_group = QButtonGroup(dialog)
        
        # S1P option
        s1p_radio = QRadioButton("S1P Format - Single Port (S11 only)")
        s1p_radio.setChecked(True)  # Default selection
        button_group.addButton(s1p_radio, 1)
        layout.addWidget(s1p_radio)
        
        # S2P option  
        s2p_radio = QRadioButton("S2P Format - Two Port (S11 and S21)")
        button_group.addButton(s2p_radio, 2)
        layout.addWidget(s2p_radio)
        
        # Info label
        info_label = QLabel("S1P files contain only S11 reflection data.\nS2P files contain both S11 and S21 transmission data.")
        info_label.setStyleSheet("font-size: 11px; color: #D0D0D0;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Cancel button
        cancel_button = QPushButton("Cancel")
        cancel_button.setMinimumWidth(80)
        cancel_button.clicked.connect(dialog.reject)
        button_layout.addWidget(cancel_button)
        
        # Export button
        export_button = QPushButton("Export")
        export_button.setMinimumWidth(80)
        export_button.setDefault(True)
        export_button.clicked.connect(dialog.accept)
        button_layout.addWidget(export_button)
        
        layout.addStretch()
        layout.addLayout(button_layout)
        
        # Show dialog and get result
        result = dialog.exec()
        if result == QDialog.DialogCode.Accepted:
            if s1p_radio.isChecked():
                return "s1p"
            else:
                return "s2p"
        else:
            return None

    def open_report_url(self):
        """
        Open the GitHub issues page for reporting bugs or feature requests.
        """
        try:
            webbrowser.open("https://github.com/fcascan/NanoVNA-UTN-Toolkit/issues")
        except Exception as e:
            # Fallback if webbrowser fails
            QMessageBox.information(
                self, 
                "Report Issues", 
                "Please visit: https://github.com/fcascan/NanoVNA-UTN-Toolkit/issues\n"
                "to report bugs or request features."
            )
    
    def show_about_dialog(self, language='en'):
        """
        Show the About dialog with the project README.
        
        Args:
            language: Language code ('en' for English, 'es' for Spanish)
        """
        try:
            about_dialog = AboutDialog(self, language)
            about_dialog.exec()
        except Exception as e:
            # Fallback if dialog creation fails
            if language == 'es':
                QMessageBox.about(
                    self,
                    "Acerca de NanoVNA UTN Toolkit",
                    "NanoVNA UTN Toolkit\n\n"
                    "Un toolkit integral para mediciones y análisis con NanoVNA.\n\n"
                    "UTN FRBA 2025 - MEDIDAS ELECTRÓNICAS II - Curso R5052\n\n"
                    "Para más información, visite:\n"
                    "https://github.com/fcascan/NanoVNA-UTN-Toolkit"
                )
            else:
                QMessageBox.about(
                    self,
                    "About NanoVNA UTN Toolkit",
                    "NanoVNA UTN Toolkit\n\n"
                    "A comprehensive toolkit for NanoVNA measurements and analysis.\n\n"
                    "UTN FRBA 2025 - ELECTRONIC MEASUREMENTS II - Course R5052\n\n"
                    "For more information, visit:\n"
                    "https://github.com/fcascan/NanoVNA-UTN-Toolkit"
                )

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NanoVNAGraphics()
    window.show()
    sys.exit(app.exec())