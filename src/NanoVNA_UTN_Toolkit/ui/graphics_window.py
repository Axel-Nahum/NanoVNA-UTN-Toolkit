"""
Graphic view window for NanoVNA devices with dual info panels and cursors.
"""

#-------------------- IMPORTS -------------------------------------------------------------------------#  

import os
import sys
import logging
import webbrowser
import numpy as np
import skrf as rf

# Matplotlib imports for plotting and interactive features

import matplotlib.pyplot as plt
import matplotlib.pyplot as plt

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
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.reset.panels_utils import _clear_all_marker_fields
except ImportError as e:
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
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.graphics_refresh import run_sweep, update_reconnect_button_state
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
    from NanoVNA_UTN_Toolkit.ui.utils.menu.file_menu.file_menu import export_errors, export_latex_pdf, export_touchstone_data
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.utils.menu.file_menu.file_menu import import_touchstone_data_dut, import_touchstone_data_calibration
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.utils.menu.calibration_menu.calibration_menu import open_calibration_wizard, open_no_calibration, select_kit_dialog, handle_save_calibration, delete_kit_dialog
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.utils.menu.view_edit_menu.view_edit_menu import open_view, edit_graphics_markers
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.utils.menu.sweep_menu.sweep_menu import open_sweep_options
except ImportError as e:
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.utils.menu.help_menu.help_menu import show_about_dialog, open_report_url
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.utils.context_menu.context_menu import handle_contextMenuEvent
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.frequency_difference.frequency_difference import show_frequency_difference_dialog
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.updates.sliders_update import left_slider_moved, left_slider_moved_2, right_slider_moved, right_slider_moved_2
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

#-------------------- ABOUT DIALOG -------------------------------------------------------------------------#

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
        import_touchstone_action.triggered.connect(lambda: import_touchstone_data_calibration(self))

        import_touchstone_action = file_menu.addAction("Import Touchstone Data (DUT)")
        import_touchstone_action.triggered.connect(lambda: import_touchstone_data_dut(self))

        file_menu.addSeparator()

        export_pdf_action =  file_menu.addAction("Export Latex PDF")
        export_pdf_action.triggered.connect(lambda: export_latex_pdf(self))

        export_touchstone_action = file_menu.addAction("Export Touchstone Data")
        export_touchstone_action.triggered.connect(lambda: export_touchstone_data(self))

        export_touchstone_action = file_menu.addAction("Export Errors")
        export_touchstone_action.triggered.connect(lambda: export_errors(self))

        graphics_markers = edit_menu.addAction("Graphics/Markers")
        graphics_markers.triggered.connect(lambda: edit_graphics_markers(self))

        # --- Help menu actions ---

        report_action = help_menu.addAction("Report")
        report_action.triggered.connect(lambda: self.open_report_url())

        about_en_action = help_menu.addAction("About [EN]")
        about_en_action.triggered.connect(lambda: show_about_dialog(self, 'en'))

        about_es_action = help_menu.addAction("About [ES]")
        about_es_action.triggered.connect(lambda: show_about_dialog(self, 'es'))

#-------- Lock Markers ----------------------------------------------------------------------------#

        # Load configuration for calibration

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
        choose_graphics.triggered.connect(lambda: open_view(self))  

        sweep_options = sweep_menu.addAction("Options")
        sweep_options.triggered.connect(lambda: open_sweep_options(self))
 
        sweep_run = sweep_menu.addAction("Run Sweep")
        sweep_run.triggered.connect(lambda: run_sweep(self))

        calibrate_option = calibration_menu.addAction("Calibration Wizard")
        calibrate_option.triggered.connect(lambda: open_calibration_wizard(self))

        calibrate_option = calibration_menu.addAction("No Calibration")
        calibrate_option.triggered.connect(lambda: open_no_calibration(self))

        calibration_menu.addSeparator()

        select_calibration = calibration_menu.addAction("Select Calibration (Kit)")
        select_calibration.triggered.connect(lambda: select_kit_dialog(self))

        save_calibration = calibration_menu.addAction("Save Calibration (Kit)")

        # Connect the action to the handler
        save_calibration.triggered.connect(lambda: handle_save_calibration(self))

        delete_calibration = calibration_menu.addAction("Delete Calibration (Kit)")
        delete_calibration.triggered.connect(lambda: delete_kit_dialog(self))

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
        
        self.markers_button.clicked.connect(lambda: show_frequency_difference_dialog(self))
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
                            self.slider_left_2.on_changed(lambda: left_slider_moved_2(self))
                        
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
                            self.slider_right_2.on_changed(lambda: right_slider_moved_2(self))
                            self.right_slider_moved_2(int(0))   # antes val
                        
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
                            self.slider_left.on_changed(lambda: left_slider_moved(self))
                        
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
                            self.slider_right.on_changed(lambda: right_slider_moved(self))
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

    # =================== CONNECTION FUNCTION ==================

    def open_connection_window(self):
        from NanoVNA_UTN_Toolkit.ui.connection_window import NanoVNAStatusApp

        logging.info("[connection_windows.open_connection_window] Opening connection")
        
        self.connection_window = NanoVNAStatusApp()
        self.connection_window.show()
        self.close()
        self.deleteLater()

    # =================== SWEEP OPTIONS FUNCTION ==================

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

        handle_contextMenuEvent(self, event)

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

    def get_current_timestamp(self):
        """Generate timestamp for filenames"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NanoVNAGraphics()
    window.show()
    sys.exit(app.exec())