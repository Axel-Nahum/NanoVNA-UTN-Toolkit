"""
Graphic view window for NanoVNA devices with dual info panels and cursors.
"""

#-------------------- IMPORTS -------------------------------------------------------------------------#  

import os
import sys
import logging

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

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QMainWindow, QApplication
from PySide6.QtGui import QIcon

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
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_window_body import setup_graphics_window_body 
except ImportError as e:
    logging.error("Failed to import setup_graphics_window_body: %s", e)
    setup_graphics_window_body = None

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
    from NanoVNA_UTN_Toolkit.ui.utils.menu.help_menu.help_menu import show_about_dialog
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
    from NanoVNA_UTN_Toolkit.ui.graphics_windows.graphics_utils.graphics_refresh import run_sweep
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.utils.menu.help_menu.help_menu import open_report_url
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
        report_action.triggered.connect(lambda: open_report_url(self))

        about_en_action = help_menu.addAction("About [EN]")
        about_en_action.triggered.connect(lambda: show_about_dialog(self, 'en'))

        about_es_action = help_menu.addAction("About [ES]")
        about_es_action.triggered.connect(lambda: show_about_dialog(self, 'es'))

#-------- Lock Markers ----------------------------------------------------------------------------#

        # Load configuration for calibration

        settings = get_settings(
            "INI/dark_light_config/dark_light_config.ini",
            "ui/utils/settings/dark_light_mode/dark_light_config.ini", 
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

        # Load configuration for graphics settings and visualization parameters
        settings = get_settings(
            "INI/graphics_config/graphics_config.ini",
            "ui/graphics_windows/graphics_config/graphics_config.ini", 
            Path(__file__).resolve()
        )

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

    # =================== MENU FUNCTION ==================

    def open_connection_window(self):
        from NanoVNA_UTN_Toolkit.ui.connection_window import NanoVNAStatusApp

        logging.info("[connection_windows.open_connection_window] Opening connection")
        
        self.connection_window = NanoVNAStatusApp()
        self.connection_window.show()
        self.close()
        self.deleteLater()

    # =================== RIGHT CLICK ==================

    def contextMenuEvent(self, event):

        handle_contextMenuEvent(self, event)

    # =================== CLEAR FREQ ==================

    def clear_freq_edit(self, edit_widget):
        edit_widget.blockSignals(True) 
        edit_widget.setText("--")
        edit_widget.setFixedWidth(edit_widget.fontMetrics().horizontalAdvance(edit_widget.text()) + 4)
        edit_widget.blockSignals(False)

# =================== TIME ===================

    def get_current_timestamp(self):
        """Generate timestamp for filenames"""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NanoVNAGraphics()
    window.show()
    sys.exit(app.exec())