import logging
import sys
import os

import matplotlib.pyplot as plt

plt.rcParams['mathtext.fontset'] = 'cm'   
plt.rcParams['text.usetex'] = False      
plt.rcParams['axes.labelsize'] = 12
plt.rcParams['font.family'] = 'serif'    
plt.rcParams['mathtext.rm'] = 'serif'   

from pathlib import Path

from PySide6.QtWidgets import(QApplication, QMainWindow, QWidget, 
                                QVBoxLayout, QHBoxLayout, QPushButton,
                             )
from PySide6.QtGui import QIcon

try:
    from NanoVNA_UTN_Toolkit.ui.wizard_cal_windows.wizard_cal_utils.calibration_dialog import save_calibration_dialog
except ImportError as e:
    import logging, sys
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
    from NanoVNA_UTN_Toolkit.ui.utils.settings.dark_light_mode.light_dark_mode import dark_light_config
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.utils.calibration.calibration_path_utils import get_calibration_path
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)

try:
    from NanoVNA_UTN_Toolkit.ui.wizard_cal_windows.wizard_cal_utils.screens import show_first_screen, next_step, previous_step
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1) 

try:
    from NanoVNA_UTN_Toolkit.ui.wizard_cal_windows.wizard_cal_utils.sweep_cal import update_device_limits
except ImportError as e:
    import logging, sys
    logging.error("Failed to import required modules: %s", e)
    logging.info("Please make sure you're running from the correct directory and all dependencies are installed.")
    sys.exit(1)   

# ------------------------------------------------------------------------------------------------------------------- #

class CalibrationWizard(QMainWindow):
    def __init__(self, vna_device=None, parent=None, caller="welcome"):
        super().__init__()

        base_path = get_calibration_path(
            "calibration",
            "calibration",
            Path(__file__).resolve()
        )

        # Inicializar el manager pasándole la ruta
        self.osm_calibration = OSMCalibrationManager(base_path=None)
        self.thru_calibration = THRUCalibrationManager(base_path=None)

        self.last_start_value = 50   
        self.last_stop_value  = 1.5   

        self.parent = parent

        self.caller = caller

 #------------------------------------------------------------------------------------------------------------------------------------------

        # Dark-Light mode settings

        dark_light_config(self)

#------------------------------------------------------------------------------------------------------------------------------------------

        self.setWindowTitle("NanoVNA UTN Toolkit - Calibration Wizard")
        self.setGeometry(150, 150, 1000, 600)

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

        self.vna_device = vna_device
        
        # Initialize OSM calibration storage with new manager
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

        # Store measured data state for UI consistency
        self.measured_data = {
            'open': None,
            'short': None, 
            'match': None
        }
        
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)

        # Content area (this is where screens are placed)
        self.content_layout = QVBoxLayout()
        self.main_layout.addLayout(self.content_layout)

        # Step tracking
        self.current_step = 0
        self.selected_method = None
        
        # Sweep configuration (persistent across screens)
        self.sweep_start_freq = 50000  # 50 kHz default
        self.sweep_stop_freq = 1500000000  # 1.5 GHz default
        self.sweep_steps = 101  # Default steps

        # Bottom button layout
        self.button_layout = QHBoxLayout()
        self.button_layout.setContentsMargins(0, 10, 0, 0)

        # Back button (left)
        self.back_button = QPushButton("◀◀")
        self.back_button.setFixedSize(100, 30)
        self.back_button.setStyleSheet("font-size: 14px;")
        self.back_button.clicked.connect(lambda: previous_step(self))
        self.button_layout.addWidget(self.back_button)

        self.button_layout.addStretch()

        # Save Calibration button (will be shown only in final step)
        self.save_button = QPushButton("Save Calibration")
        self.save_button.setFixedSize(130, 30)
        self.save_button.setStyleSheet("font-size: 12px; background-color: #4CAF50; color: white; font-weight: bold;")
        self.save_button.clicked.connect(lambda: save_calibration_dialog(self))
        self.save_button.setVisible(False)  # Hidden by default
        self.button_layout.addWidget(self.save_button)

        # Next button (right)
        self.next_button = QPushButton("▶▶")
        self.next_button.setFixedSize(100, 30)
        self.next_button.setStyleSheet("font-size: 14px;")
        self.next_button.clicked.connect(lambda: next_step(self, parent = parent))
        self.next_button.setEnabled(False)  # start locked until user selects
        self.button_layout.addWidget(self.next_button)

        self.main_layout.addLayout(self.button_layout)

        # Show first screen
        show_first_screen(self)

    from PySide6.QtWidgets import QToolTip

# --- screens --------------------------------------------------------------

    def on_method_activated(self, index):
        """Called when user selects a method from the combo box."""

        if index == 0:
            self.selected_method = None
            self.next_button.setEnabled(False)
        else:
            self.selected_method = self.freq_dropdown.itemText(index)
            self.next_button.setEnabled(True)
            # Update device limits when method is selected
            update_device_limits(self)

    # You can add unique steps for Enhanced-Response and 1-Path 2-Port in the same way
    #  
    def show_existing_measurements_on_chart(self):
        """Show all existing measurements on Smith chart to preserve state"""
        from ...utils.smith_chart_utils import SmithChartManager
        from ...utils.magnitude_chat_utils import MagnitudeChartManager
        
        if not self.osm_calibration or not hasattr(self, 'current_ax'):
            return

        if not self.thru_calibration or not hasattr(self, 'current_ax'):
            return
            
        try:
            # Collect all existing measurements
            measurements = {}
            for standard_name in ['open', 'short', 'match']:
                if self.osm_calibration.is_standard_measured(standard_name):
                    measurement = self.osm_calibration.get_measurement(standard_name)
                    if measurement:
                        measurements[standard_name] = measurement
            
            # Use consolidated Smith chart functionality
            manager = SmithChartManager()
            manager.show_multiple_measurements(
                ax=self.current_ax,
                measurements_dict=measurements,
                canvas=self.current_canvas,
                start_freq=self.get_sweep_start_frequency(),
                stop_freq=self.get_sweep_stop_frequency(),
                num_points=self.get_sweep_steps()
            )
            
        except Exception as e:
            logging.error(f"[CalibrationWizard] Error showing existing measurements: {e}")

        try:
            # Collect all existing measurements
            measurements = {}
            for standard_name in ['thru']:
                if self.thru_calibration.is_standard_measured(standard_name):
                    measurement = self.thru_calibration.get_measurement(standard_name)
                    if measurement:
                        measurements[standard_name] = measurement

            # Use consolidated Magnitude chart functionality
            manager = MagnitudeChartManager()
            manager.show_multiple_measurements(
                ax=self.current_ax,
                measurements_dict=measurements,
                canvas=self.current_canvas,
                start_freq=self.get_sweep_start_frequency(),
                stop_freq=self.get_sweep_stop_frequency(),
                num_points=self.get_sweep_steps()
            )
            
        except Exception as e:
            logging.error(f"[CalibrationWizard] Error showing existing measurements: {e}")
    
    def get_sweep_start_frequency(self):
        """Get start frequency in Hz from instance variable"""
        return self.sweep_start_freq
    
    def get_sweep_stop_frequency(self):
        """Get stop frequency in Hz from instance variable"""
        return self.sweep_stop_freq
    
    def get_sweep_steps(self):
        """Get number of sweep steps from instance variable"""
        return self.sweep_steps
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    wizard = CalibrationWizard()
    wizard.show()
    sys.exit(app.exec())
