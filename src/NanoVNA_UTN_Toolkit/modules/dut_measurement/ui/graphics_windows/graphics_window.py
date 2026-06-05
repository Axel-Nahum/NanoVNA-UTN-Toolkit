"""
Graphic view window for NanoVNA devices with dual info panels and cursors.
"""

#-------------------- IMPORTS -------------------------------------------------------------------------#  

from NanoVNA_UTN_Toolkit.utils import safe_import
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
from PySide6.QtGui import QGuiApplication

# Import exporters for saving data in different formats, with error handling to log issues without crashing the application

from ...exporters.latex_exporter import LatexExporter
from ...exporters.touchstone_exporter import TouchstoneExporter

# Import dark-light mode toggle function with error handling to log issues without crashing the application

toggle_menu_dark_mode, dark_light_config = safe_import("NanoVNA_UTN_Toolkit.shared.utils.dark_light_mode.light_dark_mode", "toggle_menu_dark_mode", "dark_light_config")

# Import get_settings 

get_settings = safe_import("NanoVNA_UTN_Toolkit.shared.utils.resources.settings_utils", "get_settings")

# Import load graph configuration

load_graph_configuration = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.settings.load_graph_config.load_graph_config", "load_graph_configuration")

_clear_all_marker_fields = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.reset.panels_utils", "_clear_all_marker_fields")

# Import calibration managers for handling OSM and THRU calibrations, with error handling to log issues without crashing the application

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.calibration.calibration_manager import OSMCalibrationManager, THRUCalibrationManager
except ImportError as e:
    logging.error("Failed to import OSMCalibrationManager: %s", e)
    logging.error("Failed to import THRUCalibrationManager: %s", e)
    OSMCalibrationManager = None
    THRUCalibrationManager = None

try:
    from NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_windows_body.graphics_window_body import setup_graphics_window_body 
except ImportError as e:
    logging.error("Failed to import setup_graphics_window_body: %s", e)
    setup_graphics_window_body = None

export_errors, export_latex_pdf, export_touchstone_data = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.file_menu.file_menu", "export_errors", "export_latex_pdf", "export_touchstone_data")

import_touchstone_data_dut, import_touchstone_data_calibration = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.file_menu.file_menu", "import_touchstone_data_dut", "import_touchstone_data_calibration")

open_calibration_wizard, open_no_calibration, select_kit_dialog, handle_save_calibration, delete_kit_dialog = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.calibration_menu.calibration_menu", "open_calibration_wizard", "open_no_calibration", "select_kit_dialog", "handle_save_calibration", "delete_kit_dialog")

open_view, edit_graphics_markers = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.view_edit_menu.view_edit_menu", "open_view", "edit_graphics_markers")

open_plot_settings = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.plot_menu.plot_menu", "open_plot_manager")

open_signal_filters = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.plot_menu.plot_menu", "open_signal_filter")

open_sweep_options = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.sweep_menu.sweep_menu", "open_sweep_options")

show_about_dialog = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.help_menu.help_menu", "show_about_dialog")

handle_contextMenuEvent = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.context_menu.context_menu", "handle_contextMenuEvent")

show_frequency_difference_dialog = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.frequency_difference.frequency_difference", "show_frequency_difference_dialog")
    
#run_sweep = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.graphics_refresh", "run_sweep")
run_sweep = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.graphics_windows.graphics_utils.graphics_refresh_thread", "run_sweep")

open_report_url = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.menu.help_menu.help_menu", "open_report_url")

apply_window_icon = safe_import("NanoVNA_UTN_Toolkit.shared.utils.icon.app_icon", "apply_window_icon")

read_auto_scale_data = safe_import("NanoVNA_UTN_Toolkit.modules.dut_measurement.ui.utils.context_menu.auto_scale.auto_scale", "read_auto_scale_data")

JsonResourceLoader = safe_import("NanoVNA_UTN_Toolkit.shared.resources.json_resource_loader", "JsonResourceLoader")

ComplexKalman = safe_import("NanoVNA_UTN_Toolkit.shared.utils.real_time.kalman_filter.kalman_filter", "ComplexKalman")

on_realtime_toggled = safe_import("NanoVNA_UTN_Toolkit.shared.utils.real_time.real_time", "on_realtime_toggled")

#-------------------- ABOUT DIALOG -------------------------------------------------------------------------#

class NanoVNAGraphics(QMainWindow):
    def __init__(self, s11=None, s21=None, freqs=None, left_graph_type="Smith Diagram", left_s_param="S11", vna_device=None, dut=None):
        super().__init__()

        self.setWindowTitle("NanoVNA Toolkit - Graphics Window")
        self.setGeometry(100, 100, 1310, 710)

        screen = QGuiApplication.primaryScreen().availableGeometry()
        window_geometry = self.frameGeometry()

        center_point = screen.center()
        window_geometry.moveCenter(center_point)

        self.move(window_geometry.topLeft())

        self.is_real_time_init = False
        self._initial_sweep_done = False

        # Store VNA device reference
        self.dut = dut
        self.vna_device = vna_device

        settings = get_settings(
            "INI/dut_measurement/signal_filters/plot_config.ini",
            "modules/dut_measurement/ui/utils/menu/plot_menu/signal_filters/signal_filters.ini",
            Path(__file__).resolve()
        )

        is_kalman_enabled = settings.value("Kalman/enabled", False, type=bool)

        preset = settings.value("Kalman/preset", "default")

        if preset == "Custom":
            process_noise = settings.value("Kalman/custom_Q", 0.0001, type=float)
            measurement_noise = settings.value("Kalman/custom_R", 10.0, type=float)
        elif preset == "Light":
            process_noise = settings.value("Kalman/Q", 0.01, type=float)
            measurement_noise = settings.value("Kalman/R", 1.0, type=float)
        elif preset == "Medium":
            process_noise = settings.value("Kalman/Q", 0.001, type=float)
            measurement_noise = settings.value("Kalman/R", 0.1, type=float)
        elif preset == "Strong":
            process_noise = settings.value("Kalman/Q", 0.0001, type=float)
            measurement_noise = settings.value("Kalman/R", 0.01, type=float)

        # kalman filters for real-time data smoothing
        if is_kalman_enabled:
            self.kf_s11 = ComplexKalman(process_noise=process_noise, measurement_noise=measurement_noise)
            self.kf_s21 = ComplexKalman(process_noise=process_noise, measurement_noise=measurement_noise)

        # Auto Scale

        data_config = read_auto_scale_data(self)

        self.auto_scale_enabled_left = data_config[0]
        self.auto_scale_enabled_right= data_config[1]

        # Log graphics window initialization

        logging.info("[graphics_window.__init__] Initializing graphics window")
        if vna_device:
            device_type = type(vna_device).__name__
            logging.info(f"[graphics_window.__init__] VNA device provided: {device_type}")
        else:
            logging.warning("[graphics_window.__init__] No VNA device provided")

# ------------------------------------------------------------------------------------------------------------------- #
# Load JSON 
# ------------------------------------------------------------------------------------------------------------------- #

        settings = get_settings(
            "INI/dut_measurement/preferences/preferences.ini",
            "shared/utils/preferences/preferences.ini", 
            Path(__file__).resolve()
        )

        current_lang = settings.value("Preferences/language", "en")

        self.resourceLoader = JsonResourceLoader(
            self_window = self, 
            module = "dut_measurement", 
            lang = current_lang, 
            json_resource = "dut_measurement_graphics.json"
        )

        self.resourceLoader.load_measurement_graphics_resources()
        self.resourceLoader.load_measurement_menu_resources()

        self.resourceLoader = JsonResourceLoader(
            self_window = self, 
            module = "dut_measurement", 
            lang = current_lang, 
            json_resource = "dut_measurement_features.json"
        )

        self.resourceLoader.load_export_touchstone_resources()
        self.resourceLoader.load_set_range_resources()

        self.resourceLoader = JsonResourceLoader(
            self_window = self, 
            module = "dut_measurement", 
            lang = current_lang, 
            json_resource = "dut_measurement_kits.json"
        )

        self.resourceLoader.load_cal_kits_resources()

        self.resourceLoader = JsonResourceLoader(
            self_window = self, 
            module = "dut_measurement", 
            lang = current_lang, 
            json_resource = "dut_measurement_plot_manager.json"
        )

        self.resourceLoader.load_plot_manager_resources()

        self.resourceLoader = JsonResourceLoader(
            self_window = self, 
            module = "dut_measurement", 
            lang = current_lang, 
            json_resource = "dut_measurement_signal_filters.json"
        )

        self.resourceLoader.load_signal_filters_resources()

# ------------------------------------------------------------------------------------------------------------------- #
# Dark light Mode
# ------------------------------------------------------------------------------------------------------------------- #

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
        file_menu = menu_bar.addMenu(f"{self.measurement_ui_menu_file}")
        plot_menu = menu_bar.addMenu(f"{self.measurement_ui_menu_plot}")
        sweep_menu = menu_bar.addMenu(f"{self.measurement_ui_menu_sweep}")
        calibration_menu = menu_bar.addMenu(f"{self.measurement_ui_menu_calibration}")
        help_menu = menu_bar.addMenu(f"{self.measurement_ui_menu_help}")

        # --- File menu actions ---

        import_touchstone_action = file_menu.addAction(f"{self.measurement_menu_import_touchstone_cal}")
        import_touchstone_action.triggered.connect(lambda: import_touchstone_data_calibration(self))

        import_touchstone_action = file_menu.addAction(f"{self.measurement_menu_import_touchstone_dut}")
        import_touchstone_action.triggered.connect(lambda: import_touchstone_data_dut(self))

        file_menu.addSeparator()

        export_pdf_action =  file_menu.addAction(f"{self.measurement_menu_export_pdf}")
        export_pdf_action.triggered.connect(lambda: export_latex_pdf(self))

        export_touchstone_action = file_menu.addAction(f"{self.measurement_menu_export_touchstone}")
        export_touchstone_action.triggered.connect(lambda: export_touchstone_data(self))

        export_touchstone_action = file_menu.addAction(f"{self.measurement_menu_export_errors}")
        export_touchstone_action.triggered.connect(lambda: export_errors(self))

        file_menu.addSeparator()

        exit_action = file_menu.addAction(f"{self.measurement_menu_back_to_menu}")
        exit_action.triggered.connect(lambda: self.return_to_menu_window())

        #graphics_markers = edit_menu.addAction(f"{self.measurement_menu_graphics_markers}")
        #graphics_markers.triggered.connect(lambda: edit_graphics_markers(self))

        # --- Plot menu actions ---

        plot_manager = plot_menu.addAction(f"{self.measurement_menu_plot_settings}")  
        plot_manager.triggered.connect(lambda: open_plot_settings(self))

        signal_filter = plot_menu.addAction(f"{self.measurement_menu_signal_filters}")  
        signal_filter.triggered.connect(lambda: open_signal_filters(self))

        # --- Help menu actions ---

        report_action = help_menu.addAction(f"{self.measurement_menu_report}")
        report_action.triggered.connect(lambda: open_report_url(self))

        about_en_action = help_menu.addAction(f"{self.measurement_menu_about_en}")
        about_en_action.triggered.connect(lambda: show_about_dialog(self, 'en'))

        about_es_action = help_menu.addAction(f"{self.measurement_menu_about_es}")
        about_es_action.triggered.connect(lambda: show_about_dialog(self, 'es'))

#-------- Lock Markers ----------------------------------------------------------------------------#

        # Load configuration for calibration

        settings = get_settings(
            "INI/dut_measurement/dark_light_config/dark_light_config.ini",
            "shared/utils/dark_light_mode/dark_light_config.ini", 
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

        #light_dark_mode = edit_menu.addAction(text_light_dark)

        self.is_dark_mode = settings.value("Dark_Light/is_dark_mode", False, type=bool)

        #light_dark_mode.triggered.connect(lambda: toggle_menu_dark_mode(self, light_dark_mode))

#-------- Other options ---------------------------------------------------------------------------- #

        #choose_graphics = view_menu.addAction(f"{self.measurement_menu_graphics}")
        #choose_graphics.triggered.connect(lambda: open_view(self))  

        sweep_options = sweep_menu.addAction(f"{self.measurement_menu_sweep_option}")
        sweep_options.triggered.connect(lambda: open_sweep_options(self))
 
        sweep_run = sweep_menu.addAction(f"{self.measurement_menu_run_sweep}")
        sweep_run.triggered.connect(lambda: run_sweep(self))

        calibrate_option = calibration_menu.addAction(f"{self.measurement_menu_cal_wizard}")
        calibrate_option.triggered.connect(lambda: open_calibration_wizard(self))

        calibrate_option = calibration_menu.addAction(f"{self.measurement_menu_no_calibration}")
        calibrate_option.triggered.connect(lambda: open_no_calibration(self))

        calibration_menu.addSeparator()

        select_calibration = calibration_menu.addAction(f"{self.measurement_menu_select_kit}")
        select_calibration.triggered.connect(lambda: select_kit_dialog(self))

        save_calibration = calibration_menu.addAction(f"{self.measurement_menu_save_kit}")

        # Connect the action to the handler
        save_calibration.triggered.connect(lambda: handle_save_calibration(self))

        delete_calibration = calibration_menu.addAction(f"{self.measurement_menu_delete_kit}")
        delete_calibration.triggered.connect(lambda: delete_kit_dialog(self))

        apply_window_icon(self)

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
            "INI/dut_measurement/graphics_config/graphics_config.ini",
            "modules/dut_measurement/ui/graphics_windows/graphics_config/graphics_config.ini", 
            Path(__file__).resolve()
        )

        setup_graphics_window_body(         # Widgets Body of graphics_window
            self,
            settings,
            config,
            left_graph_type,
            left_s_param
        )

        # ---------------- INIT REALTIME STATE ----------------

        QTimer.singleShot(2000, lambda: on_realtime_toggled(self, False))

        self.markers = [
            {"cursor": self.cursor_left, "cursor_2": self.cursor_left_2, "slider": self.slider_left, "slider_2": self.slider_left_2, "label": self.labels_left, "label_2": self.labels_left_2, "update_cursor": self.update_cursor, "update_cursor_2": self.update_cursor_2},
            {"cursor": self.cursor_right, "cursor_2": self.cursor_right_2, "slider": self.slider_right, "slider_2": self.slider_right_2, "label": self.labels_right, "label_2": self.labels_right_2, "update_cursor": self.update_right_cursor, "update_cursor_2": self.update_right_cursor_2}
        ]
        
        self.markers_button.clicked.connect(lambda: show_frequency_difference_dialog(self))
        self.markers_button.hide()
        
        # Clear all marker information fields until first sweep is completed
        _clear_all_marker_fields(self)
        
        # Initialize exporters
        self.latex_exporter = LatexExporter(measurement_self = self, parent_widget=self)
        self.touchstone_exporter = TouchstoneExporter(parent_widget=self)

        self.sweep_button.setEnabled(False)

        #self._initial_sweep_done = True

# ------------------------------------------------------------------------------------------------------------------------------------------------------------ #

# =================== MENU FUNCTION ==================

    def open_connection_window(self):
        from NanoVNA_UTN_Toolkit.shared.ui.connection_window.connection_window import NanoVNAStatusApp

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
    
    def return_to_menu_window(self):

        from NanoVNA_UTN_Toolkit.modules.menu_window import ModuleSelectionWindow

        if self.vna_device:
            self.menu_windows = (
                ModuleSelectionWindow(vna_device=self.vna_device)
            )
        else:
            self.menu_windows = (
                ModuleSelectionWindow()
            )

        self.menu_windows.show()

        self.close()

    def reload_graphics_resources(self):

        settings = get_settings(
            "INI/dut_measurement/preferences/preferences.ini",
            "shared/utils/preferences/preferences.ini", 
            Path(__file__).resolve()
        )

        current_lang = settings.value("Preferences/language", "en")

        self.resourceLoader = JsonResourceLoader(
            self_window=self,
            module="dut_measurement",
            lang=current_lang,
            json_resource="dut_measurement_graphics.json"
        )

        self.resourceLoader.load_measurement_graphics_resources()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = NanoVNAGraphics()
    window.show()
    sys.exit(app.exec())